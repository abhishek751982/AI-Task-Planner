"""Intelligent date normalization and workload-aware scheduling."""

from datetime import date, timedelta

from guide_todoo.config import settings
from guide_todoo.models import ParsedTask


def flatten_tasks(parsed: list[ParsedTask]) -> list[ParsedTask]:
    out: list[ParsedTask] = []
    for item in parsed:
        out.append(item)
        out.extend(flatten_tasks(item.subtasks))
    return out


def normalize_due_date(value: str | None, today: date | None = None) -> date | None:
    """Reject hallucinated or stale dates (e.g. 2024 when today is 2026)."""
    today = today or date.today()
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return None
    if parsed.year < today.year:
        return None
    if parsed < today - timedelta(days=1):
        return None
    return parsed


def schedule_task_tree(
    parsed: list[ParsedTask],
    *,
    today: date | None = None,
    max_per_day: int | None = None,
) -> list[ParsedTask]:
    """Spread tasks across days/weeks when dates are missing or invalid."""
    today = today or date.today()
    if max_per_day is None:
        try:
            from guide_todoo.intelligence import adaptive_max_tasks

            max_per_day = adaptive_max_tasks()
        except Exception:
            max_per_day = settings.max_tasks_per_day
    state = {"day_offset": 0, "count_today": 0}

    def assign(items: list[ParsedTask]) -> None:
        for item in items:
            valid = normalize_due_date(item.due_date, today)
            if valid:
                item.due_date = valid.isoformat()
            else:
                assigned = today + timedelta(days=state["day_offset"])
                item.due_date = assigned.isoformat()
                state["count_today"] += 1
                if state["count_today"] >= max_per_day:
                    state["day_offset"] += 1
                    state["count_today"] = 0
            if item.subtasks:
                assign(item.subtasks)

    assign(parsed)
    return parsed


def workload_summary(tasks: list[dict], start: date, days: int = 14) -> dict[str, int]:
    """Count pending tasks per due date in the next N days."""
    end = start + timedelta(days=days)
    counts: dict[str, int] = {}
    for task in tasks:
        if task.get("status") != "pending":
            continue
        due = task.get("due_date")
        if not due:
            continue
        due_str = str(due)[:10]
        try:
            due_date = date.fromisoformat(due_str)
        except ValueError:
            continue
        if start <= due_date <= end:
            counts[due_str] = counts.get(due_str, 0) + 1
    return counts


def tasks_eligible_for_day(pending: list[dict], plan_date: date, max_daily: int | None = None) -> list[dict]:
    """Pick tasks for today's plan: overdue + due today + light upcoming load."""
    max_daily = max_daily or settings.max_tasks_per_day
    overdue: list[dict] = []
    due_today: list[dict] = []
    upcoming: list[dict] = []

    for task in pending:
        due = task.get("due_date")
        if not due:
            upcoming.append(task)
            continue
        try:
            due_date = date.fromisoformat(str(due)[:10])
        except ValueError:
            upcoming.append(task)
            continue
        if due_date < plan_date:
            overdue.append(task)
        elif due_date == plan_date:
            due_today.append(task)
        elif due_date <= plan_date + timedelta(days=3):
            upcoming.append(task)

    overdue.sort(key=lambda t: (t.get("priority", 2), str(t.get("due_date"))))
    due_today.sort(key=lambda t: t.get("priority", 2))
    upcoming.sort(key=lambda t: (str(t.get("due_date")), t.get("priority", 2)))

    selected: list[dict] = []
    for bucket in (overdue, due_today, upcoming):
        for task in bucket:
            if len(selected) >= max_daily * 2:
                break
            selected.append(task)
    return selected
