"""Request-scoped signed-in user. No hardcoded account."""

from contextvars import ContextVar
from collections.abc import Callable
from typing import Any

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def optional_user_id() -> str | None:
    return current_user_id.get()


def active_user_id() -> str:
    uid = current_user_id.get()
    if not uid:
        raise RuntimeError("Sign in required")
    return uid


def run_for_each_user(fn: Callable[[], Any]) -> dict[str, Any]:
    """Run a job once per account. Used by cron and the local scheduler."""
    from guide_todoo import db

    results: list[dict[str, Any]] = []
    for user in db.list_users():
        token = current_user_id.set(user["id"])
        try:
            results.append({"email": user["email"], "ok": True, "result": fn()})
        except Exception as exc:
            results.append({"email": user["email"], "ok": False, "error": str(exc)})
        finally:
            current_user_id.reset(token)
    return {"users": results}
