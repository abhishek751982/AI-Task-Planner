"""Mac bridge: pull tasks from cloud API → Apple Reminders (iPhone via iCloud)."""

import logging
import time
from datetime import datetime

import httpx

from guide_todoo.config import settings
from guide_todoo.integrations.reminders import create_reminder
from guide_todoo.llm import parse_scheduled_time

logger = logging.getLogger(__name__)


def sync_once() -> int:
    base = settings.bridge_api_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.bridge_secret}"}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{base}/bridge/pending", headers=headers)
        resp.raise_for_status()
        tasks = resp.json().get("tasks", [])

    synced = 0
    for task in tasks:
        due = None
        if task.get("due_date"):
            due = parse_scheduled_time("09:00", datetime.fromisoformat(task["due_date"]).date())
        reminder_id = create_reminder(
            task["title"],
            list_name=settings.reminders_list,
            body=task.get("description", ""),
            due=due,
        )
        with httpx.Client(timeout=30.0) as client:
            client.post(
                f"{base}/bridge/ack",
                headers=headers,
                json={"task_id": task["id"], "reminder_id": reminder_id},
            )
        synced += 1
        logger.info("Synced task %s → Reminders", task["id"])
    return synced


def run_loop(interval_seconds: int = 60) -> None:
    if not settings.bridge_secret:
        raise RuntimeError("Set BRIDGE_SECRET in .env (same value as on Vercel).")
    logger.info("Bridge running — polling %s every %ss", settings.bridge_api_url, interval_seconds)
    while True:
        try:
            count = sync_once()
            if count:
                logger.info("Synced %s reminders", count)
        except Exception:
            logger.exception("Bridge sync failed")
        time.sleep(interval_seconds)
