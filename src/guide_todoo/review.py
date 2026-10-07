from calendar import monthrange
from datetime import date

from guide_todoo import db
from guide_todoo.config import settings
from guide_todoo.integrations.tasks_backend import notify
from guide_todoo.llm import monthly_analysis, score_day
from guide_todoo.sync_todoist import eod_notify_at, run_full_sync
from guide_todoo.user_context import extract_memories_from_day, notification_budget


def end_of_day_summary(day: date | None = None) -> dict:
    day = day or date.today()
    # Pull Todoist completions + rollover unfinished tasks first
    sync_result = run_full_sync(day)

    completed = db.tasks_completed_on(day)
    planned = db.tasks_due_on(day)
    plan = db.get_daily_plan(day)
    plan_content = plan["content"] if plan else "(no plan saved)"
    score, summary = score_day(completed, planned, plan_content)
    db.save_daily_plan(day, plan_content, score=score)

    report = (
        f"# Day summary — {day.isoformat()}\n\n"
        f"**Score:** {score}/100\n\n"
        f"{summary}\n\n"
        f"## Completed ({len(completed)})\n"
        + "\n".join(f"- {t['title']}" for t in completed)
        + f"\n\n## Rolled to tomorrow ({sync_result['rollover']['rolled']})\n"
        + "\n".join(f"- {t['title']}" for t in sync_result["rollover"]["tasks"])
    )

    # Learn from today → save to long-term memory
    new_memories = extract_memories_from_day(
        completed, sync_result["rollover"]["tasks"], score, summary
    )

    # Todoist push: task with due time = EOD hour triggers notification
    notify_at = eod_notify_at(day)
    notify(
        f"📊 Day score: {score}/100",
        f"{summary}\n\nCompleted: {len(completed)} | Rolled: {sync_result['rollover']['rolled']}",
        at=notify_at,
    )

    return {
        "date": day.isoformat(),
        "score": score,
        "summary": summary,
        "report": report,
        "sync": sync_result,
        "notify_at": notify_at.isoformat(),
        "memories_learned": new_memories,
        "notification_budget": notification_budget(),
    }


def generate_monthly_report(year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    stats = db.task_stats_between(start, end)
    sample = db.list_tasks()
    report_md = monthly_analysis(stats, sample)
    db.save_monthly_report(year, month, report_md)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    path = settings.reports_dir / f"monthly-{year}-{month:02d}.md"
    path.write_text(report_md, encoding="utf-8")
    notify(
        f"📅 Monthly report — {year}-{month:02d}",
        f"Completion rate: {stats['completion_rate']}%",
        at=eod_notify_at(today),
    )
    return {"year": year, "month": month, "stats": stats, "report": report_md, "path": str(path)}
