"""Google OAuth + Calendar free-busy slots."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from guide_todoo import db
from guide_todoo.config import settings
from guide_todoo.scope import active_user_id
from guide_todoo.user_context import get_profile


def _uid(user_id: str | None) -> str:
    return user_id or active_user_id()

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def _client_config() -> dict[str, Any]:
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.resolved_google_redirect_uri],
        }
    }


def auth_url(user_id: str | None = None) -> str:
    user_id = _uid(user_id)
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=user_id)
    flow.redirect_uri = settings.resolved_google_redirect_uri
    url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return url


def handle_callback(code: str, user_id: str | None = None) -> dict[str, str]:
    user_id = _uid(user_id)
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=user_id)
    flow.redirect_uri = settings.resolved_google_redirect_uri
    flow.fetch_token(code=code)
    creds = flow.credentials
    db.save_oauth_token(
        user_id,
        "google",
        creds.token,
        refresh_token=creds.refresh_token,
        expires_at=creds.expiry,
        scopes=",".join(SCOPES),
    )
    email = _fetch_email(creds.token)
    return {"status": "connected", "email": email}


def _fetch_email(access_token: str) -> str:
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json().get("email", "")


def _credentials(user_id: str | None = None) -> Credentials | None:
    user_id = _uid(user_id)
    row = db.get_oauth_token(user_id, "google")
    if not row:
        return None
    return Credentials(
        token=row["access_token"],
        refresh_token=row.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )


def is_connected(user_id: str | None = None) -> bool:
    user_id = _uid(user_id)
    return db.get_oauth_token(user_id, "google") is not None


def get_busy_blocks(day: date, user_id: str | None = None) -> list[tuple[datetime, datetime]]:
    user_id = _uid(user_id)
    creds = _credentials(user_id)
    if not creds:
        return []
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    events = (
        service.events()
        .list(calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(), singleEvents=True)
        .execute()
    )
    blocks: list[tuple[datetime, datetime]] = []
    for ev in events.get("items", []):
        s = ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date")
        e = ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")
        if not s or not e:
            continue
        blocks.append((datetime.fromisoformat(s.replace("Z", "+00:00")), datetime.fromisoformat(e.replace("Z", "+00:00"))))
    return blocks


def free_slots(day: date, user_id: str | None = None, slot_minutes: int = 45) -> list[tuple[time, time]]:
    user_id = _uid(user_id)
    profile = get_profile(user_id) or {}
    if profile.get("focus_day") == day.isoformat():
        max_tasks = 1
    else:
        max_tasks = profile.get("max_tasks_per_day", settings.max_tasks_per_day)

    work_start = _parse_hhmm(profile.get("work_start", "09:00"))
    work_end = _parse_hhmm(profile.get("work_end", "18:00"))
    deep_start = _parse_hhmm(profile.get("deep_work_start", "07:00"))
    deep_end = _parse_hhmm(profile.get("deep_work_end", "09:00"))

    windows = [(deep_start, deep_end), (time(18, 0), time(22, 0))]
    if profile.get("role") == "student":
        windows.append((time(10, 0), time(17, 0)))

    busy = get_busy_blocks(day, user_id)
    slots: list[tuple[time, time]] = []
    for w_start, w_end in windows:
        slots.extend(_subtract_busy(w_start, w_end, busy, day, slot_minutes))
    return slots[: max_tasks * 2]


def _parse_hhmm(value: str) -> time:
    h, m = map(int, value.split(":")[:2])
    return time(h, m)


def _subtract_busy(
    start: time,
    end: time,
    busy: list[tuple[datetime, datetime]],
    day: date,
    slot_minutes: int,
) -> list[tuple[time, time]]:
    free: list[tuple[time, time]] = []
    cursor = datetime.combine(day, start)
    end_dt = datetime.combine(day, end)
    while cursor + timedelta(minutes=slot_minutes) <= end_dt:
        slot_end = cursor + timedelta(minutes=slot_minutes)
        if not any(not (slot_end <= b[0] or cursor >= b[1]) for b in busy):
            free.append((cursor.time(), slot_end.time()))
        cursor += timedelta(minutes=slot_minutes)
    return free
