"""Email and password accounts stored in Neon Postgres."""

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any

from fastapi import HTTPException, Request, Response

from guide_todoo import db
from guide_todoo.config import settings
from guide_todoo.scope import current_user_id

_COOKIE = "gt_session"
_MAX_AGE = 60 * 60 * 24 * 14


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + _b64(salt) + "$" + _b64(digest)


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, digest_b64 = stored.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = _b64decode(salt_b64)
        expected = _b64decode(digest_b64)
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register_user(email: str, password: str, name: str) -> dict[str, Any]:
    email = _normalize_email(email)
    _check_password(password)
    if db.get_user_by_email(email):
        raise HTTPException(409, "An account with this email already exists")
    display = name.strip() or email.split("@", 1)[0]
    user = db.create_user(str(uuid.uuid4()), email, display, hash_password(password))
    return _public_user(user)


def login_user(email: str, password: str) -> dict[str, Any]:
    email = _normalize_email(email)
    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect")
    return _public_user(user)


def user_from_request(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(_COOKIE)
    if not token:
        return None
    user_id = _read_session(token)
    if not user_id:
        return None
    user = db.get_user_by_id(user_id)
    return _public_user(user) if user else None


def bind_request_user(request: Request) -> dict[str, Any]:
    user = user_from_request(request)
    if not user:
        raise HTTPException(401, "Sign in required")
    current_user_id.set(user["id"])
    return user


def write_session(response: Response, user_id: str) -> None:
    response.set_cookie(
        _COOKIE,
        _sign_session(user_id),
        httponly=True,
        samesite="lax",
        max_age=_MAX_AGE,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(_COOKIE, path="/")


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


def _normalize_email(email: str) -> str:
    cleaned = email.strip().lower()
    if "@" not in cleaned or len(cleaned) > 254:
        raise HTTPException(400, "Enter a valid email")
    return cleaned


def _check_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")


def _secret() -> bytes:
    secret = settings.session_secret.strip()
    if not secret or secret.startswith("change-me"):
        raise HTTPException(500, "Set SESSION_SECRET in .env before signing in")
    return secret.encode()


def _sign_session(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + _MAX_AGE}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _read_session(token: str) -> str | None:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64decode(body))
        if int(payload["exp"]) < int(time.time()):
            return None
        uid = str(payload["uid"])
        return uid or None
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)
