"""User profile and long-term memory for personalized planning."""

import json
from typing import Any

from guide_todoo import db
from guide_todoo.models import OnboardingRequest
from guide_todoo.scope import active_user_id, optional_user_id


def _uid(user_id: str | None) -> str:
    return user_id or active_user_id()


def save_profile(data: OnboardingRequest, user_id: str | None = None) -> dict[str, Any]:
    user_id = _uid(user_id)
    profile = data.model_dump()
    db.upsert_user_profile(user_id, profile)
    # Seed initial memories from onboarding
    if data.main_goal:
        db.add_memory(user_id, "goal", data.main_goal, source="onboarding")
    db.add_memory(
        user_id,
        "preference",
        f"Role: {data.role}. Work {data.work_start}-{data.work_end} on {','.join(data.work_days)}. "
        f"Deep work {data.deep_work_start}-{data.deep_work_end}. "
        f"Side goals: {data.side_goal_hours_per_day}h/day. "
        f"Split: {data.activity_split.work}% work, {data.activity_split.study}% study, "
        f"{data.activity_split.personal}% personal.",
        source="onboarding",
    )
    db.add_memory(
        user_id,
        "preference",
        f"Notifications: {data.notification_style}. Quiet hours {data.quiet_hours_start}-{data.quiet_hours_end}. "
        f"Max {data.max_tasks_per_day} tasks/day.",
        source="onboarding",
    )
    return profile


def get_profile(user_id: str | None = None) -> dict[str, Any] | None:
    uid = user_id or optional_user_id()
    if not uid:
        return None
    return db.get_user_profile(uid)


def is_onboarded(user_id: str | None = None) -> bool:
    return get_profile(user_id) is not None


def get_memories(user_id: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    uid = user_id or optional_user_id()
    if not uid:
        return []
    return db.list_memories(uid, limit=limit)


def add_memory(user_id: str, kind: str, content: str, source: str = "system") -> None:
    db.add_memory(user_id, kind, content, source=source)


def build_llm_context(user_id: str | None = None) -> str:
    """Context block injected into every LLM call."""
    profile = get_profile(user_id)
    if not profile:
        return "USER PROFILE: Not onboarded yet. Use sensible defaults (max 4 tasks/day)."

    split = profile.get("activity_split", {})
    lines = [
        "USER PROFILE:",
        f"- Role: {profile.get('role', 'unknown')}",
        f"- Work hours: {profile.get('work_start')}-{profile.get('work_end')} ({', '.join(profile.get('work_days', []))})",
        f"- Deep work window: {profile.get('deep_work_start')}-{profile.get('deep_work_end')} (schedule hard tasks here)",
        f"- Side goal time: {profile.get('side_goal_hours_per_day')}h/day",
        f"- Activity split: {split.get('work', 50)}% work, {split.get('study', 30)}% study, {split.get('personal', 20)}% personal",
        f"- Main goal: {profile.get('main_goal', 'not set')}",
        f"- Notification style: {profile.get('notification_style', 'normal')} | Quiet: {profile.get('quiet_hours_start')}-{profile.get('quiet_hours_end')}",
        f"- Max tasks/day: {profile.get('max_tasks_per_day', 4)}",
        f"- Timezone: {profile.get('timezone', 'Asia/Kolkata')}",
    ]
    if profile.get("focus_day"):
        lines.append(f"- Focus day (max 1 side task): {profile.get('focus_day')}")
    memories = get_memories(user_id)
    if memories:
        lines.append("\nUSER MEMORY (learned over time):")
        for m in memories:
            lines.append(f"- [{m['kind']}] {m['content']}")
    return "\n".join(lines)


def extract_memories_from_day(
    completed: list[dict],
    rolled: list[dict],
    score: float,
    summary: str,
    user_id: str | None = None,
) -> list[str]:
    """Extract 1-2 learnings from EOD and save to memory."""
    user_id = _uid(user_id)
    from guide_todoo.llm import extract_day_memories

    facts = extract_day_memories(completed, rolled, score, summary)
    for fact in facts[:2]:
        add_memory(user_id, "insight", fact, source="eod")
    return facts


def notification_budget(user_id: str | None = None) -> int:
    profile = get_profile(user_id) or {}
    style = profile.get("notification_style", "normal")
    return {"gentle": 2, "normal": 3, "focused": 4}.get(style, 3)
