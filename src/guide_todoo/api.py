import logging
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from guide_todoo import auth, db
from guide_todoo.config import settings
from guide_todoo.ingest.pdf import extract_text_from_pdf
from guide_todoo.integrations import google_calendar
from guide_todoo.integrations.jira import JiraClient
from guide_todoo.integrations.reminders import list_incomplete_reminders
from guide_todoo.integrations.tasks_backend import complete_external
from guide_todoo.intelligence import generate_morning_brief, generate_weekly_review, log_leetcode
from guide_todoo.models import OnboardingRequest
from guide_todoo.planner import generate_daily_plan, ingest_chat, ingest_pdf_text, reschedule_stale_tasks, sync_jira
from guide_todoo.review import end_of_day_summary, generate_monthly_report
from guide_todoo.scheduler import start_scheduler, stop_scheduler
from guide_todoo.sync_todoist import run_full_sync, sync_from_todoist
from guide_todoo.scope import current_user_id, run_for_each_user
from guide_todoo.user_context import get_memories, get_profile, is_onboarded, save_profile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ponytail: APScheduler only on local dev; Vercel uses cron routes
    if os.getenv("VERCEL") != "1" and (settings.push_reminders_locally or settings.use_todoist):
        start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Guide Todoo", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_bridge(authorization: str | None = Header(default=None)) -> None:
    if not settings.bridge_secret:
        raise HTTPException(500, "BRIDGE_SECRET not configured on server")
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != settings.bridge_secret:
        raise HTTPException(401, "Invalid bridge token")


class ChatRequest(BaseModel):
    message: str


class CompleteRequest(BaseModel):
    task_id: int | None = None
    title: str | None = None


class BridgeAck(BaseModel):
    task_id: int
    reminder_id: str


class LeetCodeRequest(BaseModel):
    problem_slug: str
    title: str
    difficulty: str | None = None


class AuthRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class ProfilePatch(BaseModel):
    focus_day: str | None = None
    max_tasks_per_day: int | None = Field(default=None, ge=1, le=10)
    main_goal: str | None = None
    notification_style: str | None = None


async def require_user(request: Request) -> dict:
    # Set the user on the request task. Sync handlers copy this context into their thread.
    return auth.bind_request_user(request)


def _require_onboarded() -> None:
    if not is_onboarded():
        raise HTTPException(
            400,
            "Complete onboarding first: POST /onboard with your work hours, goals, and preferences.",
        )


def _verify_cron(authorization: str | None = Header(default=None)) -> None:
    secret = settings.resolved_cron_secret
    if not secret:
        return
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != secret:
        raise HTTPException(401, "Invalid cron secret")


@app.post("/auth/register")
def register(body: AuthRequest):
    user = auth.register_user(body.email, body.password, body.name)
    return {"ok": True, "user": user}


@app.post("/auth/login")
def login(body: AuthRequest):
    user = auth.login_user(body.email, body.password)
    response = JSONResponse({"ok": True, "user": user})
    auth.write_session(response, user["id"])
    return response


@app.post("/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    auth.clear_session(response)
    return response


@app.get("/auth/me")
def me(request: Request):
    user = auth.user_from_request(request)
    if not user:
        raise HTTPException(401, "Sign in required")
    current_user_id.set(user["id"])
    return {"user": user, "onboarded": is_onboarded()}


@app.get("/onboard/status")
def onboard_status(_user: dict = Depends(require_user)):
    return {"onboarded": is_onboarded()}


@app.post("/onboard")
def onboard(body: OnboardingRequest, _user: dict = Depends(require_user)):
    profile = save_profile(body)
    return {"ok": True, "profile": profile}


@app.get("/profile")
def profile(_user: dict = Depends(require_user)):
    p = get_profile()
    if not p:
        raise HTTPException(404, "Not onboarded. POST /onboard first.")
    return {"profile": p, "memories": get_memories()}


@app.get("/health")
def health(request: Request):
    db_ok = False
    try:
        db_ok = db.ping()
    except Exception:
        logger.exception("Database health check failed")
    user = auth.user_from_request(request)
    if user:
        current_user_id.set(user["id"])
    signed_in = user is not None
    return {
        "ok": db_ok,
        "database": "neon" if db_ok else "unavailable",
        "tasks_backend": settings.tasks_backend,
        "todoist_configured": settings.use_todoist,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.resolved_model,
        "llm_configured": bool(settings.resolved_api_key),
        "reminders_mode": settings.reminders_mode,
        "jira_enabled": JiraClient().enabled,
        "authenticated": signed_in,
        "user": user,
        "onboarded": is_onboarded() if signed_in else False,
        "google_calendar": google_calendar.is_connected() if signed_in else False,
        "google_oauth_configured": bool(settings.google_client_id and settings.google_client_secret),
    }


@app.get("/bridge/pending")
def bridge_pending(_: None = Depends(verify_bridge)):
    return {"tasks": db.list_unsynced_tasks()}


@app.post("/bridge/ack")
def bridge_ack(body: BridgeAck, _: None = Depends(verify_bridge)):
    db.set_reminder_id(body.task_id, body.reminder_id)
    return {"ok": True, "task_id": body.task_id}


@app.post("/ingest/pdf")
async def upload_pdf(file: UploadFile = File(...), _user: dict = Depends(require_user)):
    _require_onboarded()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Upload a PDF file")
    data = await file.read()
    text = extract_text_from_pdf(data)
    if not text:
        raise HTTPException(400, "Could not extract text from PDF")
    try:
        tasks = ingest_pdf_text(text, file.filename)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"filename": file.filename, "tasks_created": len(tasks), "tasks": tasks}


@app.post("/ingest/chat")
def chat_tasks(body: ChatRequest, _user: dict = Depends(require_user)):
    _require_onboarded()
    try:
        tasks = ingest_chat(body.message)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"tasks_created": len(tasks), "tasks": tasks}


@app.post("/jira/sync")
def jira_sync(_user: dict = Depends(require_user)):
    try:
        created = sync_jira()
    except Exception as exc:
        raise HTTPException(500, f"Jira sync failed: {exc}") from exc
    if not JiraClient().enabled:
        raise HTTPException(400, "Jira not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN in .env")
    return {"synced": len(created), "tasks": created}


@app.post("/sync/todoist")
def sync_todoist(_user: dict = Depends(require_user)):
    try:
        return run_full_sync()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/cron/sync-todoist")
def cron_sync_todoist(_: None = Depends(_verify_cron)):
    return run_for_each_user(run_full_sync)


@app.post("/plan/reschedule")
def reschedule_tasks(_user: dict = Depends(require_user)):
    try:
        updated = reschedule_stale_tasks()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
    return {"rescheduled": len(updated), "tasks": updated}


@app.post("/plan/daily")
def daily_plan(plan_date: date | None = None, _user: dict = Depends(require_user)):
    try:
        return generate_daily_plan(plan_date)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/tasks")
def list_all_tasks(status: str | None = None, _user: dict = Depends(require_user)):
    return {"tasks": db.list_tasks(status=status)}


@app.post("/tasks/complete")
def complete_task(body: CompleteRequest, _user: dict = Depends(require_user)):
    if body.task_id:
        task = db.get_task(body.task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        db.update_task_status(body.task_id, "done")
        complete_external(task.get("reminder_id"))
        return {"completed": body.task_id}
    if body.title:
        matches = [t for t in db.list_tasks() if t["title"] == body.title and t["status"] != "done"]
        for task in matches:
            db.update_task_status(task["id"], "done")
            complete_external(task.get("reminder_id"))
        return {"completed_by_title": body.title, "rows": len(matches)}
    raise HTTPException(400, "Provide task_id or title")


@app.get("/review/daily")
def daily_review(day: date | None = None, _user: dict = Depends(require_user)):
    try:
        return end_of_day_summary(day)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/review/monthly")
def monthly_review(year: int | None = None, month: int | None = None, _user: dict = Depends(require_user)):
    try:
        return generate_monthly_report(year, month)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/review/weekly")
def weekly_review(_user: dict = Depends(require_user)):
    try:
        return generate_weekly_review()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/stats/progress")
def progress(_user: dict = Depends(require_user)):
    return db.goal_progress()


@app.get("/calendar/status")
def calendar_status(_user: dict = Depends(require_user)):
    return {"connected": google_calendar.is_connected()}


@app.get("/calendar/slots")
def calendar_slots(day: date | None = None, _user: dict = Depends(require_user)):
    day = day or date.today()
    slots = google_calendar.free_slots(day)
    return {
        "date": day.isoformat(),
        "connected": google_calendar.is_connected(),
        "slots": [{"start": s[0].strftime("%H:%M"), "end": s[1].strftime("%H:%M")} for s in slots],
    }


@app.get("/auth/google")
def google_auth_start(user: dict = Depends(require_user)):
    try:
        return {"url": google_calendar.auth_url(user["id"])}
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/auth/google/callback")
def google_auth_callback(code: str, state: str = ""):
    if not state or not db.get_user_by_id(state):
        raise HTTPException(400, "Sign in before connecting Google Calendar")
    current_user_id.set(state)
    try:
        result = google_calendar.handle_callback(code, user_id=state)
    except Exception as exc:
        raise HTTPException(400, f"Google OAuth failed: {exc}") from exc
    return RedirectResponse(f"{settings.app_base_url}/settings?google=connected&email={result.get('email', '')}")


@app.patch("/profile")
def patch_profile(body: ProfilePatch, user: dict = Depends(require_user)):
    profile = get_profile()
    if not profile:
        raise HTTPException(404, "Not onboarded")
    for key, value in body.model_dump(exclude_none=True).items():
        profile[key] = value
    db.upsert_user_profile(user["id"], profile)
    return {"ok": True, "profile": profile}


@app.post("/leetcode/log")
def leetcode_log(body: LeetCodeRequest, _user: dict = Depends(require_user)):
    return log_leetcode(body.problem_slug, body.title, body.difficulty)


@app.get("/leetcode/stats")
def leetcode_stats(_user: dict = Depends(require_user)):
    return db.leetcode_stats()


@app.post("/webhooks/todoist")
async def todoist_webhook(request: Request):
    payload = await request.json()
    event = payload.get("event_name", "")
    if event == "item:completed":
        todoist_id = str(payload.get("event_data", {}).get("id", ""))
        task = db.find_task_by_reminder(todoist_id) if todoist_id else None
        if task and task.get("user_id") and task["status"] != "done":
            db.update_task_status(task["id"], "done", user_id=task["user_id"])
            return {"ok": True, "completed": task["id"]}
    elif event in ("item:updated", "item:added"):
        run_for_each_user(sync_from_todoist)
    return {"ok": True, "event": event}


@app.get("/brief/morning")
def morning_brief(day: date | None = None, _user: dict = Depends(require_user)):
    try:
        return generate_morning_brief(day)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/reminders/incomplete")
def reminders_incomplete(_user: dict = Depends(require_user)):
    if not settings.push_reminders_locally:
        raise HTTPException(400, "Reminders only available in local mode on Mac")
    return {"reminders": list_incomplete_reminders(settings.reminders_list)}


@app.get("/api/cron/morning")
def cron_morning(_: None = Depends(_verify_cron)):
    return run_for_each_user(generate_morning_brief)


@app.get("/api/cron/eod")
def cron_eod(_: None = Depends(_verify_cron)):
    return run_for_each_user(end_of_day_summary)


@app.get("/api/cron/monthly")
def cron_monthly(_: None = Depends(_verify_cron)):
    return run_for_each_user(generate_monthly_report)


@app.get("/api/cron/weekly")
def cron_weekly(_: None = Depends(_verify_cron)):
    return run_for_each_user(generate_weekly_review)
