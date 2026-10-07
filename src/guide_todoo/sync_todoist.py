"""Bidirectional Todoist sync: import tasks in, completions in, rollover incomplete out."""

import logging
from datetime import date, datetime, time, timedelta
from typing import Any

import httpx

from guide_todoo import db
from guide_todoo.config import settings
from guide_todoo.integrations.tasks_backend import update_external_task
from guide_todoo.integrations.todoist import _from_todoist_priority, get_client
from guide_todoo.scheduling import workload_summary

logger = logging.getLogger(__name__)


def _is_todoist_completed(remote: dict[str, Any]) -> bool:
    """Todoist REST v1 uses checked/completed_at; older payloads use is_completed/completed."""
    if remote.get("checked"):
        return True
    if remote.get("is_completed"):
        return True
    if remote.get("completed"):
        return True
    if remote.get("completed_at"):
        return True
    return False


def _mark_completed(task: dict[str, Any], reason: str, completed: list[dict[str, Any]]) -> None:
    db.update_task_status(task["id"], "done")
    completed.append({"id": task["id"], "title": task["title"], "reason": reason})


def _parse_due(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_todoist_due(due: Any) -> date | None:
    if not due:
        return None
    if isinstance(due, dict):
        raw = due.get("date") or due.get("datetime")
        return _parse_due(raw)
    return _parse_due(due)


def _todoist_title(remote: dict[str, Any]) -> str:
    return str(remote.get("content") or remote.get("title") or "Untitled").strip()


def _existing_reminder_ids() -> set[str]:
    return db.list_reminder_ids()


def _import_remote_task(remote: dict[str, Any], *, as_done: bool) -> dict[str, Any] | None:
    todoist_id = str(remote.get("id") or remote.get("task_id") or "")
    if not todoist_id:
        return None

    existing = _existing_reminder_ids()
    if todoist_id in existing:
        return None

    title = _todoist_title(remote)
    task_id = db.insert_task(
        title,
        description=str(remote.get("description") or ""),
        source="todoist",
        source_ref=todoist_id,
        priority=_from_todoist_priority(int(remote.get("priority") or 2)),
        due_date=_parse_todoist_due(remote.get("due")),
        reminder_id=todoist_id,
        status="done" if as_done else "pending",
    )
    return {"id": task_id, "title": title, "todoist_id": todoist_id, "status": "done" if as_done else "pending"}


def _unwrap_completed_entry(entry: dict[str, Any]) -> dict[str, Any]:
    for key in ("item", "task", "content"):
        nested = entry.get(key)
        if isinstance(nested, dict) and (nested.get("id") or nested.get("content")):
            return nested
    return entry


def import_from_todoist() -> dict[str, Any]:
    """Pull active + recently completed Todoist tasks into the local DB."""
    if not settings.use_todoist:
        return {"imported": 0, "active": 0, "completed": 0, "tasks": [], "skipped_reason": "todoist_not_configured"}

    client = get_client()
    imported: list[dict[str, Any]] = []

    try:
        active = client.list_active_tasks()
        if not active:
            active = client.list_all_active_tasks()
        for remote in active:
            if _is_todoist_completed(remote):
                row = _import_remote_task(remote, as_done=True)
            else:
                row = _import_remote_task(remote, as_done=False)
            if row:
                imported.append(row)
    except Exception as exc:
        logger.exception("import active Todoist tasks failed: %s", exc)
        return {"imported": 0, "active": 0, "completed": 0, "tasks": [], "error": str(exc)}

    active_count = sum(1 for t in imported if t["status"] == "pending")

    today = date.today()
    try:
        for entry in client.list_completed_tasks(since=today - timedelta(days=30), until=today):
            remote = _unwrap_completed_entry(entry)
            row = _import_remote_task(remote, as_done=True)
            if row:
                imported.append(row)
    except Exception as exc:
        logger.warning("import completed Todoist tasks skipped: %s", exc)

    done_count = sum(1 for t in imported if t["status"] == "done")

    return {
        "imported": len(imported),
        "active": active_count,
        "completed": done_count,
        "tasks": imported,
    }


def sync_from_todoist() -> dict[str, Any]:
    """Mark DB tasks done when completed in Todoist."""
    if not settings.use_todoist:
        return {"synced": 0, "completed": [], "skipped_reason": "todoist_not_configured"}

    client = get_client()
    pending = pending_tasks_with_todoist()
    completed: list[dict[str, Any]] = []

    active_by_id: dict[str, dict[str, Any]] | None = None
    try:
        active_by_id = {str(t["id"]): t for t in client.list_active_tasks()}
    except Exception as exc:
        logger.warning("list_active_tasks failed, falling back to per-task GET: %s", exc)

    for task in pending:
        todoist_id = str(task["reminder_id"])
        remote: dict[str, Any] | None = None

        if active_by_id is not None:
            remote = active_by_id.get(todoist_id)
            if remote is None:
                try:
                    remote = client.get_task(todoist_id)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        _mark_completed(task, "closed in Todoist", completed)
                    continue
        else:
            try:
                remote = client.get_task(todoist_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    _mark_completed(task, "closed in Todoist", completed)
                continue

        if remote and _is_todoist_completed(remote):
            _mark_completed(task, "completed in Todoist", completed)

    return {"synced": len(pending), "completed": completed}


def rollover_incomplete_tasks(today: date | None = None) -> dict[str, Any]:
    """Move incomplete due/overdue tasks to future dates and update Todoist."""
    today = today or date.today()
    pending = db.list_tasks(status="pending")
    incomplete = []
    for task in pending:
        due = _parse_due(task.get("due_date"))
        if due and due <= today:
            incomplete.append(task)

    if not incomplete:
        return {"rolled": 0, "tasks": []}

    incomplete.sort(key=lambda t: (t.get("priority", 2), str(t.get("due_date"))))
    pending_all = db.list_tasks(status="pending")
    workload = workload_summary(pending_all, today + timedelta(days=1), days=30)

    rolled: list[dict[str, Any]] = []
    day_offset = 1
    count_on_day = 0
    max_per_day = settings.max_tasks_per_day

    for task in incomplete:
        while True:
            candidate = today + timedelta(days=day_offset)
            key = candidate.isoformat()
            if workload.get(key, 0) < max_per_day:
                break
            day_offset += 1
            count_on_day = 0

        new_due = today + timedelta(days=day_offset)
        db.update_task_due_date(task["id"], new_due)
        if task.get("reminder_id"):
            update_external_task(task["reminder_id"], due_date=new_due)

        workload[new_due.isoformat()] = workload.get(new_due.isoformat(), 0) + 1
        count_on_day += 1
        if count_on_day >= max_per_day:
            day_offset += 1
            count_on_day = 0

        rolled.append({
            "id": task["id"],
            "title": task["title"],
            "old_due": str(task.get("due_date")),
            "new_due": new_due.isoformat(),
        })

    return {"rolled": len(rolled), "tasks": rolled}


def run_full_sync(today: date | None = None) -> dict[str, Any]:
    """Import from Todoist, pull completions, then rollover incomplete tasks."""
    imported = import_from_todoist()
    pull = sync_from_todoist()
    roll = rollover_incomplete_tasks(today)
    return {"import": imported, "pull": pull, "rollover": roll}


def pending_tasks_with_todoist() -> list[dict[str, Any]]:
    return [t for t in db.list_tasks(status="pending") if t.get("reminder_id")]


def eod_notify_at(day: date | None = None) -> datetime:
    """When EOD summary should ping Todoist (uses EOD_SUMMARY_HOUR)."""
    day = day or date.today()
    return datetime.combine(day, time(settings.eod_summary_hour, 0))


if __name__ == "__main__":
    assert _is_todoist_completed({"checked": True})
    assert _is_todoist_completed({"completed_at": "2026-08-02T10:00:00Z"})
    assert _is_todoist_completed({"completed": True})
    assert not _is_todoist_completed({"checked": False, "completed_at": None})
    print("sync_todoist self-check ok")
