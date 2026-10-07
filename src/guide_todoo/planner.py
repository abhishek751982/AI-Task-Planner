from datetime import date

from guide_todoo import db
from guide_todoo.integrations.google_calendar import free_slots, is_connected
from guide_todoo.integrations.jira import JiraClient
from guide_todoo.integrations.tasks_backend import push_task, update_external_task
from guide_todoo.intelligence import adaptive_max_tasks
from guide_todoo.models import ParsedTask
from guide_todoo.llm import (
    build_daily_plan,
    parse_due_date,
    parse_pdf_tasks,
    parse_scheduled_time,
    parse_text_to_tasks,
)
from guide_todoo.scheduling import schedule_task_tree, tasks_eligible_for_day


def persist_parsed_tasks(
    parsed: list[ParsedTask],
    *,
    source: str,
    source_ref: str | None = None,
    parent_id: int | None = None,
) -> list[dict]:
    created: list[dict] = []
    for item in parsed:
        due = parse_due_date(item.due_date)
        external_id = push_task(
            item.title,
            description=item.description,
            due_date=due,
            priority=item.priority,
        )
        task_id = db.insert_task(
            item.title,
            description=item.description,
            source=source,
            source_ref=source_ref,
            parent_id=parent_id,
            priority=item.priority,
            due_date=due,
            reminder_id=external_id,
        )
        row = {
            "id": task_id,
            "title": item.title,
            "due_date": due.isoformat() if due else None,
            "todoist_id": external_id,
        }
        created.append(row)
        if item.subtasks:
            created.extend(
                persist_parsed_tasks(
                    item.subtasks,
                    source=source,
                    source_ref=source_ref,
                    parent_id=task_id,
                )
            )
    return created


def ingest_pdf_text(text: str, filename: str) -> list[dict]:
    parsed = parse_pdf_tasks(text, filename)
    scheduled = schedule_task_tree(parsed)
    return persist_parsed_tasks(scheduled, source="pdf", source_ref=filename)


def ingest_chat(message: str) -> list[dict]:
    parsed = parse_text_to_tasks(message, context="User described tasks in natural language.")
    scheduled = schedule_task_tree(parsed)
    return persist_parsed_tasks(scheduled, source="chat")


def sync_jira() -> list[dict]:
    client = JiraClient()
    if not client.enabled:
        return []
    created: list[dict] = []
    existing = {t.get("jira_key") for t in db.list_tasks() if t.get("jira_key")}
    for issue in client.fetch_my_issues():
        key = issue["key"]
        if key in existing:
            continue
        due = parse_due_date(issue.get("due_date"))
        title = f"[{key}] {issue['title']}"
        external_id = push_task(
            title,
            description=issue.get("description", ""),
            due_date=due,
            priority=issue.get("priority", 2),
        )
        task_id = db.insert_task(
            title,
            description=issue.get("description", ""),
            source="jira",
            source_ref=key,
            priority=issue.get("priority", 2),
            due_date=due,
            reminder_id=external_id,
            jira_key=key,
        )
        created.append({"id": task_id, "jira_key": key, "title": issue["title"], "todoist_id": external_id})
    return created


def generate_daily_plan(plan_date: date | None = None) -> dict:
    plan_date = plan_date or date.today()
    pending = db.list_tasks(status="pending")
    max_daily = adaptive_max_tasks()
    eligible = tasks_eligible_for_day(pending, plan_date, max_daily=max_daily)
    plan = build_daily_plan(eligible, plan_date)
    slots = free_slots(plan_date) if is_connected() else []
    lines = [f"## Daily plan — {plan_date.isoformat()}", "", plan.summary, "", f"**Focus:** {plan.focus}", ""]
    by_id = {t["id"]: t for t in pending}
    for idx, item in enumerate(plan.items):
        if slots and idx < len(slots):
            item.scheduled_time = slots[idx][0].strftime("%H:%M")
        due_dt = parse_scheduled_time(item.scheduled_time, plan_date)
        title = by_id[item.task_id]["title"] if item.task_id and item.task_id in by_id else item.title
        push_task(title, description=item.reason, due_date=plan_date, due_datetime=due_dt, priority=2)
        lines.append(f"- {item.scheduled_time or 'anytime'} — {title} ({item.reason})")
    content = "\n".join(lines)
    db.save_daily_plan(plan_date, content)
    slot_text = [f"{s[0].strftime('%H:%M')}-{s[1].strftime('%H:%M')}" for s in slots[:4]]
    return {
        "date": plan_date.isoformat(),
        "plan": content,
        "items": [i.model_dump() for i in plan.items],
        "free_slots": slot_text,
        "max_tasks": max_daily,
        "calendar_connected": is_connected(),
    }


def reschedule_stale_tasks() -> list[dict]:
    """Fix tasks with past/wrong-year due dates and sync to Todoist."""
    pending = db.list_tasks(status="pending")
    stale = []
    for task in pending:
        due = task.get("due_date")
        if not due:
            continue
        try:
            due_date = date.fromisoformat(str(due)[:10])
        except ValueError:
            stale.append(task)
            continue
        if due_date.year < date.today().year or due_date < date.today():
            stale.append(task)

    if not stale:
        return []

    # Rebuild as ParsedTask list and reschedule
    parsed = [
        ParsedTask(title=t["title"], description=t.get("description", ""), priority=t.get("priority", 2))
        for t in stale
    ]
    scheduled = schedule_task_tree(parsed)
    updated: list[dict] = []
    for task, item in zip(stale, scheduled):
        new_due = parse_due_date(item.due_date)
        db.update_task_due_date(task["id"], new_due)
        if task.get("reminder_id") and new_due:
            update_external_task(task["reminder_id"], due_date=new_due)
        updated.append({"id": task["id"], "title": task["title"], "old_due": str(task.get("due_date")), "new_due": item.due_date})
    return updated
