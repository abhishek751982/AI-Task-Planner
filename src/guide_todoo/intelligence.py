"""Morning brief, weekly review, adaptive difficulty, LeetCode."""

from datetime import date, datetime, time, timedelta

from guide_todoo import db
from guide_todoo.config import settings
from guide_todoo.integrations.google_calendar import free_slots, is_connected
from guide_todoo.integrations.tasks_backend import notify
from guide_todoo.llm import _chat_json, build_daily_plan
from guide_todoo.scheduling import tasks_eligible_for_day
from guide_todoo.sync_todoist import run_full_sync
from guide_todoo.user_context import build_llm_context, get_profile


def adaptive_max_tasks(user_id: str | None = None) -> int:
    from guide_todoo.scope import active_user_id

    user_id = user_id or active_user_id()
    profile = get_profile(user_id) or {}
    base = profile.get("max_tasks_per_day", settings.max_tasks_per_day)
    memories = db.list_memories(user_id, limit=20)
    penalty = sum(1 for m in memories if "skip" in m["content"].lower() or "slower" in m["content"].lower())
    return max(1, base - min(penalty // 3, 2))


def generate_morning_brief(day: date | None = None, user_id: str | None = None) -> dict:
    from guide_todoo.scope import active_user_id

    user_id = user_id or active_user_id()
    day = day or date.today()
    run_full_sync()
    profile = get_profile(user_id) or {}
    if profile.get("focus_day") == day.isoformat():
        max_t = 1
    else:
        max_t = adaptive_max_tasks(user_id)

    pending = db.list_tasks(status="pending")
    eligible = tasks_eligible_for_day(pending, day, max_daily=max_t)
    plan = build_daily_plan(eligible, day)

    slots = free_slots(day, user_id) if is_connected(user_id) else []
    slot_text = ", ".join(f"{s[0].strftime('%H:%M')}-{s[1].strftime('%H:%M')}" for s in slots[:3])

    lines = [plan.summary, f"Focus: {plan.focus}"]
    for item in plan.items[:max_t]:
        lines.append(f"• {item.scheduled_time or 'anytime'} — {item.title}")
    if slot_text:
        lines.append(f"Free slots: {slot_text}")

    body = "\n".join(lines)
    brief_time = datetime.combine(day, time(profile.get("morning_plan_hour", settings.morning_plan_hour), 0))
    notify(f"☀️ Morning brief", body, at=brief_time)

    db.save_daily_plan(day, body)
    return {"date": day.isoformat(), "brief": body, "free_slots": slot_text, "max_tasks": max_t}


def generate_weekly_review(user_id: str | None = None) -> dict:
    from guide_todoo.scope import active_user_id

    user_id = user_id or active_user_id()
    today = date.today()
    year, week, _ = today.isocalendar()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    stats = db.task_stats_between(start, end)
    progress = db.goal_progress(user_id)
    payload = _chat_json(
        f"{build_llm_context()}\n\nWrite a weekly review. Return JSON: {{\"report\": str, \"focus_next_week\": str}}",
        f"Week {week} stats: {stats}\nProgress: {progress}\nLeetCode: {progress.get('leetcode')}",
    )
    report = str(payload.get("report", ""))
    db.save_weekly_report(year, week, report, progress_pct=progress.get("progress_pct"))
    notify(
        f"📅 Week {week} review — {progress.get('progress_pct', 0)}%",
        str(payload.get("focus_next_week", ""))[:400],
        at=datetime.combine(today, time(settings.eod_summary_hour, 0)),
    )
    return {"year": year, "week": week, "report": report, "progress": progress}


def log_leetcode(problem_slug: str, title: str, difficulty: str | None = None, user_id: str | None = None) -> dict:
    from guide_todoo.scope import active_user_id

    user_id = user_id or active_user_id()
    lid = db.log_leetcode_solve(user_id, problem_slug, title, difficulty)
    db.add_memory(user_id, "behavior", f"Solved LeetCode: {title} ({difficulty or 'unknown'})", source="leetcode")
    return {"id": lid, "stats": db.leetcode_stats(user_id)}
