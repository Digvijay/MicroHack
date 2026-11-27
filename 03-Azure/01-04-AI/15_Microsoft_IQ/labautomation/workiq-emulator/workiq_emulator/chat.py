"""Chat write support for the lab: who is who in the Kolvo thread, and the deterministic auto-Sam."""

from __future__ import annotations

import html
import re
from datetime import datetime

from .store import Entry, Store

SAM_YES_REPLY = (
    "Yes, it is moving two weeks. Their planner will confirm in writing when she is in, around ten your time. "
    "Fine by me, as long as Poliden gets the new unit in time."
)
SAM_BUSY_REPLY = "I am at a trade fair in Singapore this week. Please keep it short: what do you need from me?"

MAX_POST_CHARS = 4000
_SAM_MENTION = re.compile(r"(?<![a-z0-9])@?sam(?![a-z0-9])", re.I)
_POLIDEN_TOPIC = re.compile(
    r"poliden|reserv|rsv-?2291|sd9-r-0733|rotterdam|maintenance|\bstop\b|\bunit\b|\brelease|\bswap", re.I
)
_TAG = re.compile(r"<[^>]{0,500}>")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def find_persona(store: Store, wanted: str) -> str | None:
    """Persona id by id, or by the first word of the display name (case-insensitive)."""
    if wanted in store.personas:
        return wanted
    for p in store.personas.values():
        first = (p.display_name.split() or [""])[0].lower()
        if first == wanted.lower():
            return p.id
    return None


def kolvo_thread(store: Store, preferred_item_id: str) -> Entry | None:
    """The live Kolvo thread: the configured chat item, else the first chat about Kolvo that Sam is in."""
    e = store.by_item_id.get(preferred_item_id)
    if e is not None and e.kind == "chat":
        return e
    sam = find_persona(store, "sam")
    for e in store.entries:
        if e.kind == "chat" and "kolvo" in (e.item.get("topic") or "").lower() and (sam is None or sam in e.item["members"]):
            return e
    return None


_HHMM = re.compile(r"^([01]?\d|2[0-3])[:.]([0-5]\d)$")


def parse_story_time(value: object, now: datetime) -> datetime:
    """'HH:MM' on the story day (the pack's "now" date and time zone), or a full ISO 8601 time with an offset."""
    if not isinstance(value, str) or not value.strip() or len(value) > 40:
        raise ValueError("Give the story time as HH:MM, for example 07:30, or as an ISO 8601 time with an offset.")
    text = value.strip()
    m = _HHMM.match(text)
    if m:
        return now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Give the story time as HH:MM, for example 07:30, or as an ISO 8601 time with an offset.") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now.tzinfo)
    return dt.astimezone(now.tzinfo)


def auto_sam_reply(text: str) -> str | None:
    """Sam's scripted answer to a message, or None when the message does not mention Sam."""
    if not _SAM_MENTION.search(text):
        return None
    if _POLIDEN_TOPIC.search(text):
        return SAM_YES_REPLY
    return SAM_BUSY_REPLY


def clean_text(raw: object, content_type: str = "text") -> str:
    """Normalise posted text. HTML bodies are reduced to plain text, control characters are rejected."""
    if not isinstance(raw, str):
        raise ValueError("The message text must be a string.")
    text = raw
    if content_type.lower() == "html":
        text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", text, flags=re.I)
        text = html.unescape(_TAG.sub("", text))
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise ValueError("The message text is empty.")
    if len(text) > MAX_POST_CHARS:
        raise ValueError(f"The message text is longer than {MAX_POST_CHARS} characters.")
    if _CTRL.search(text):
        raise ValueError("The message text contains control characters.")
    return text
