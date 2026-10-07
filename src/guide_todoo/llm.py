from datetime import date, datetime, time, timedelta
from typing import Any

from openai import OpenAI

from guide_todoo.config import settings
from guide_todoo.models import DailyPlanItem, DailyPlanResult, ParsedTask
from guide_todoo.scheduling import normalize_due_date, workload_summary
from guide_todoo.user_context import build_llm_context


def _client() -> OpenAI:
    return OpenAI(
        api_key=settings.resolved_api_key or "not-set",
        base_url=settings.resolved_base_url,
    )


def _chat_json(system: str, user: str) -> Any:
    if not settings.resolved_api_key:
        raise RuntimeError(
            "LLM API key missing. Set LLM_API_KEY in .env "
            "(free: Groq at console.groq.com, Gemini at aistudio.google.com, OpenRouter at openrouter.ai)."
        )
    system = f"{build_llm_context()}\n\n{system}"
    response = _client().chat.completions.create(
        model=settings.resolved_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    import json

    return json.loads(response.choices[0].message.content or "{}")


def _today() -> date:
    return date.today()


def _date_rules() -> str:
    today = _today()
    end = today + timedelta(weeks=settings.planning_horizon_weeks)
    return f"""DATE RULES (critical):
- TODAY is {today.isoformat()} ({today.strftime('%A')}).
- All due_date values MUST be between {today.isoformat()} and {end.isoformat()}.
- NEVER use 2024, 2025, or any date before today.
- Map "Week 1", "Day 1", "Monday" relative to TODAY.
- Spread multi-week plans across the full horizon — max {settings.max_tasks_per_day} tasks per day.
- Use ISO format YYYY-MM-DD only."""


def parse_text_to_tasks(text: str, context: str = "") -> list[ParsedTask]:
    payload = _chat_json(
        f"""You break work into small actionable tasks for a personal todo system.
Return JSON: {{"tasks": [{{"title": str, "description": str, "priority": 1-3, "due_date": "YYYY-MM-DD" or null, "subtasks": [...]}}]}}

{_date_rules()}

Rules:
- Each task completable in under 2 hours.
- Break large weekly/monthly plans into daily-sized subtasks.
- priority: 1=urgent, 2=normal, 3=low
- Schedule ONLY outside user's work hours unless task is work-related.
- Put study/DSA tasks in deep work window or side-goal hours.
- Respect max tasks/day from user profile — don't overload.""",
        f"Context: {context or 'general work'}\n\nContent:\n{text[:30000]}",
    )
    return [ParsedTask.model_validate(t) for t in payload.get("tasks", [])]


def parse_pdf_tasks(text: str, filename: str = "") -> list[ParsedTask]:
    today = _today()
    return parse_text_to_tasks(
        text,
        context=f"""Multi-week study or work plan PDF: "{filename}".
This PDF may cover several weeks of tasks. Schedule them across multiple weeks starting from {today.isoformat()}.
Group related items (e.g. DSA topics, coding patterns, weekly modules) with subtasks.
If the document lists weeks/days/modules, map each to real calendar dates from today forward.""",
    )


def build_daily_plan(tasks: list[dict[str, Any]], today: date | None = None) -> DailyPlanResult:
    today = today or _today()
    workload = workload_summary(tasks, today)
    workload_lines = "\n".join(f"  {d}: {c} tasks" for d, c in sorted(workload.items())[:14])
    task_lines = "\n".join(
        f"- id={t['id']} [{t.get('source','?')}] p{t['priority']} {t['title']} due={t.get('due_date')}"
        for t in tasks
    )
    payload = _chat_json(
        f"""Create a focused, realistic daily plan based on workload.
Return JSON:
{{"summary": str, "focus": str, "items": [{{"task_id": int|null, "title": str, "scheduled_time": "HH:MM"|null, "reason": str}}]}}

Rules:
- Schedule only {settings.max_tasks_per_day} tasks max for today — user cannot do more.
- Prioritize overdue and due-today tasks first.
- Morning deep work window = hard tasks (DSA, coding). Afternoon = lighter/admin.
- Tie each task reason to user's main goal when possible.
- Skip tasks not due today unless overdue or light workload day.
- Consider existing workload per day when picking tasks.""",
        f"Today: {today.isoformat()}\n\nWorkload next 2 weeks:\n{workload_lines or '(light)'}\n\nCandidate tasks:\n{task_lines or '(none)'}",
    )
    return DailyPlanResult.model_validate(payload)


def score_day(
    completed: list[dict[str, Any]],
    planned: list[dict[str, Any]],
    plan_content: str,
) -> tuple[float, str]:
    payload = _chat_json(
        """Score productivity 0-100 for the day. Return JSON:
{"score": float, "summary": str}
Consider: completion rate, priority tasks done, plan adherence. Be encouraging but honest.""",
        f"Plan:\n{plan_content}\n\nPlanned count: {len(planned)}\nCompleted: {[t['title'] for t in completed]}",
    )
    return float(payload.get("score", 0)), str(payload.get("summary", ""))


def monthly_analysis(stats: dict[str, Any], sample_tasks: list[dict[str, Any]]) -> str:
    payload = _chat_json(
        """Write a monthly productivity analysis in markdown. Return JSON: {"report": str}
Include: completion rate, sources breakdown, wins, bottlenecks, 3 recommendations for next month.""",
        f"Stats: {stats}\n\nSample tasks: {sample_tasks[:30]}",
    )
    return str(payload.get("report", "No report generated."))


def extract_day_memories(
    completed: list[dict[str, Any]],
    rolled: list[dict],
    score: float,
    summary: str,
) -> list[str]:
    payload = _chat_json(
        """Extract 1-2 short learnings about this user's work habits to remember for future planning.
Return JSON: {"memories": ["fact1", "fact2"]}
Only include actionable insights (preferred times, what they skip, what they finish). Max 2 items.""",
        f"Score: {score}\nSummary: {summary}\nCompleted: {[t.get('title') for t in completed]}\nRolled: {[t.get('title') for t in rolled]}",
    )
    return [str(m) for m in payload.get("memories", []) if m]



def parse_due_date(value: str | None) -> date | None:
    return normalize_due_date(value, _today())


def parse_scheduled_time(value: str | None, base: date | None = None) -> datetime | None:
    if not value:
        return None
    base = base or _today()
    try:
        hour, minute = map(int, value.split(":")[:2])
        return datetime.combine(base, time(hour, minute))
    except (ValueError, TypeError):
        return None
