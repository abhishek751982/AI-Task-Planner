import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from guide_todoo.config import settings
from guide_todoo.scope import run_for_each_user
from guide_todoo.planner import generate_daily_plan, sync_jira
from guide_todoo.review import end_of_day_summary, generate_monthly_report
from guide_todoo.sync_todoist import run_full_sync, sync_from_todoist

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _morning_job() -> None:
    logger.info("Running morning plan job")
    try:
        run_for_each_user(lambda: (run_full_sync(), sync_jira(), generate_daily_plan(date.today())))
    except Exception:
        logger.exception("Morning plan job failed")


def _sync_job() -> None:
    logger.info("Running Todoist sync job")
    try:
        run_for_each_user(sync_from_todoist)
    except Exception:
        logger.exception("Todoist sync job failed")


def _eod_job() -> None:
    logger.info("Running end-of-day summary job")
    try:
        run_for_each_user(lambda: end_of_day_summary(date.today()))
    except Exception:
        logger.exception("EOD summary job failed")


def _monthly_job() -> None:
    logger.info("Running monthly report job")
    try:
        today = date.today()
        run_for_each_user(lambda: generate_monthly_report(today.year, today.month))
    except Exception:
        logger.exception("Monthly report job failed")


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone=settings.timezone)
    _scheduler.add_job(
        _sync_job,
        CronTrigger(minute=0, timezone=settings.timezone),
        id="todoist_sync",
        replace_existing=True,
    )
    _scheduler.add_job(
        _morning_job,
        CronTrigger(hour=settings.morning_plan_hour, minute=0, timezone=settings.timezone),
        id="morning_plan",
        replace_existing=True,
    )
    _scheduler.add_job(
        _eod_job,
        CronTrigger(hour=settings.eod_summary_hour, minute=0, timezone=settings.timezone),
        id="eod_summary",
        replace_existing=True,
    )
    _scheduler.add_job(
        _monthly_job,
        CronTrigger(day="last", hour=21, minute=0, timezone=settings.timezone),
        id="monthly_report",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started (timezone=%s)", settings.timezone)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
