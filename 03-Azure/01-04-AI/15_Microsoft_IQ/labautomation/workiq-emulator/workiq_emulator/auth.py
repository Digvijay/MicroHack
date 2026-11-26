"""Bearer key authentication and signed viewer sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from .config import Settings

SESSION_COOKIE = "wiq_session"
SESSION_TTL_SECONDS = 8 * 3600


def parse_bearer(header: str | None) -> str | None:
    if not header:
        return None
    scheme, _, token = header.strip().partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def persona_for_key(settings: Settings, presented: str | None) -> str | None:
    """Return the persona whose key matches. Compares against every key with a
    constant-time comparison and does not stop at the first match."""
    if not presented:
        return None
    candidate = presented.encode("utf-8")
    match: str | None = None
    for pid, key in settings.persona_keys.items():
        if hmac.compare_digest(candidate, key.encode("utf-8")):
            match = pid
    return match


def is_admin(settings: Settings, presented: str | None) -> bool:
    if not settings.admin_key or not presented:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), settings.admin_key.encode("utf-8"))


def session_secret(settings: Settings, _cache: dict = {}) -> bytes:  # noqa: B006 - process cache
    if settings.session_secret:
        return settings.session_secret.encode("utf-8")
    if settings.admin_key:
        return hmac.new(settings.admin_key.encode("utf-8"), b"workiq-viewer-session", hashlib.sha256).digest()
    # Local development without secrets: random per process.
    return _cache.setdefault("secret", secrets.token_bytes(32))


def _key_fingerprint(settings: Settings, persona_id: str) -> str:
    key = settings.persona_keys.get(persona_id, "dev:" + persona_id)
    return hmac.new(session_secret(settings), key.encode("utf-8"), hashlib.sha256).hexdigest()[:24]


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_session(settings: Settings, persona_id: str, now: float | None = None) -> str:
    payload = {"p": persona_id, "e": int((now or time.time()) + SESSION_TTL_SECONDS), "k": _key_fingerprint(settings, persona_id)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64(hmac.new(session_secret(settings), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_session(settings: Settings, cookie: str | None, now: float | None = None) -> str | None:
    """Return the persona id of a valid session cookie. Sessions die when the key rotates."""
    if not cookie or "." not in cookie or len(cookie) > 1024:
        return None
    body, _, sig = cookie.partition(".")
    expected = _b64(hmac.new(session_secret(settings), body.encode("ascii", "ignore"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or int(payload.get("e", 0)) < (now or time.time()):
        return None
    pid = payload.get("p")
    if not isinstance(pid, str):
        return None
    if settings.auth_mode == "keys" and pid not in settings.persona_keys:
        return None
    if not hmac.compare_digest(str(payload.get("k", "")), _key_fingerprint(settings, pid)):
        return None
    return pid
