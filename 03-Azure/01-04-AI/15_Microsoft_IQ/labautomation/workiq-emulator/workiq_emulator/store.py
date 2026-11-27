"""Scenario pack loading, strict validation and the in-memory item store."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ranking

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
DEFAULT_SEED = "strandvik"
SEED_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,40}$")

MAX_ITEMS = 500
MAX_ITEM_BYTES = 64 * 1024
MAX_PERSONAS = 20
MAX_SITES = 20
MAX_CHAT_MESSAGES = 200
CHAT_MESSAGE_KEYS = {"date", "from", "text"}
CHAT_MESSAGE_VIA = ("agent",)
ITEM_TYPES = ("email", "event", "chat", "file", "person")
PERSONA_ID_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$")
GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

COMMON_KEYS = {"id", "type", "date", "visibleTo", "scenarioRef", "distractor", "note"}
TYPE_KEYS: dict[str, tuple[set[str], set[str]]] = {
    # type: (required keys, optional keys)
    "email": ({"subject", "from", "to", "body"}, {"cc", "importance", "isRead", "conversation", "folder", "isDraft"}),
    "event": ({"subject", "end", "organizer", "attendees"}, {"location", "body", "isOnlineMeeting", "transcriptFile"}),
    "chat": ({"chatType", "members", "messages"}, {"topic"}),
    "file": ({"name", "mimeType", "drive", "createdBy", "content"}, {"relatedEvent"}),
    "person": ({"displayName", "mail", "jobTitle", "companyName"}, {"department", "phone"}),
}
EMAIL_FOLDERS = ("inbox", "sentitems", "drafts")
PERSONA_DOC_PREFIX = "persona:"


class PackError(ValueError):
    """Raised when a scenario pack does not pass validation."""


def _fail(where: str, msg: str) -> None:
    raise PackError(f"{where}: {msg}")


def has_control_chars(value: str) -> bool:
    return bool(_CTRL_RE.search(value))


def _check_str(where: str, value: Any, max_len: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        _fail(where, "must be a string")
    if not allow_empty and not value.strip():
        _fail(where, "must not be empty")
    if len(value) > max_len:
        _fail(where, f"is longer than {max_len} characters")
    if has_control_chars(value):
        _fail(where, "contains control characters")
    return value


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("missing time zone offset")
    return dt


def _check_dt(where: str, value: Any) -> datetime:
    _check_str(where, value, 40)
    try:
        return parse_dt(value)
    except ValueError:
        _fail(where, "must be an ISO 8601 date and time with an offset, for example 2026-12-07T08:00:00+01:00")
    raise AssertionError  # pragma: no cover


def _check_addr(where: str, value: Any) -> None:
    if not isinstance(value, dict) or set(value) - {"name", "address"} or "address" not in value:
        _fail(where, "must be an object with 'name' and 'address'")
    _check_str(f"{where}.name", value.get("name", ""), 200, allow_empty=True)
    if not EMAIL_RE.match(_check_str(f"{where}.address", value["address"], 254)):
        _fail(f"{where}.address", "is not a valid mail address")


def _check_addr_list(where: str, value: Any, max_len: int = 50) -> None:
    if not isinstance(value, list) or len(value) > max_len:
        _fail(where, f"must be a list with at most {max_len} entries")
    for i, a in enumerate(value):
        _check_addr(f"{where}[{i}]", a)


def validate_persona(where: str, p: Any) -> None:
    allowed = {"id", "displayName", "jobTitle", "mail", "userId", "department", "officeLocation"}
    if not isinstance(p, dict):
        _fail(where, "must be an object")
    if set(p) - allowed:
        _fail(where, f"unknown keys {sorted(set(p) - allowed)}")
    for key in ("id", "displayName", "jobTitle", "mail", "userId"):
        if key not in p:
            _fail(where, f"missing '{key}'")
    if not PERSONA_ID_RE.match(_check_str(f"{where}.id", p["id"], 31)):
        _fail(f"{where}.id", "must match ^[a-z][a-z0-9-]{1,30}$")
    _check_str(f"{where}.displayName", p["displayName"], 100)
    _check_str(f"{where}.jobTitle", p["jobTitle"], 100)
    if not EMAIL_RE.match(_check_str(f"{where}.mail", p["mail"], 254)):
        _fail(f"{where}.mail", "is not a valid mail address")
    if not GUID_RE.match(_check_str(f"{where}.userId", p["userId"], 36)):
        _fail(f"{where}.userId", "must be a GUID")
    for key in ("department", "officeLocation"):
        if key in p:
            _check_str(f"{where}.{key}", p[key], 100)


def validate_item(item: Any, persona_ids: set[str], site_ids: set[str], where: str = "item") -> None:
    """Strictly validate one item. Cross references between items are checked by validate_pack."""
    if not isinstance(item, dict):
        _fail(where, "must be an object")
    size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
    if size > MAX_ITEM_BYTES:
        _fail(where, f"is {size} bytes, the limit is {MAX_ITEM_BYTES}")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not ITEM_ID_RE.match(item_id):
        _fail(where, "id must match ^[A-Za-z0-9._-]{1,64}$")
    where = f"item '{item_id}'"
    itype = item.get("type")
    if itype not in TYPE_KEYS:
        _fail(where, f"type must be one of {list(ITEM_TYPES)}")
    required, optional = TYPE_KEYS[itype]
    keys = set(item)
    missing = (required | {"date", "visibleTo"}) - keys
    if missing:
        _fail(where, f"missing keys {sorted(missing)}")
    unknown = keys - required - optional - COMMON_KEYS
    if unknown:
        _fail(where, f"unknown keys {sorted(unknown)}")
    start = _check_dt(f"{where}.date", item["date"])
    vis = item["visibleTo"]
    if not isinstance(vis, list) or not vis or len(vis) > MAX_PERSONAS:
        _fail(f"{where}.visibleTo", "must be a non-empty list of persona ids")
    for p in vis:
        if p not in persona_ids:
            _fail(f"{where}.visibleTo", f"unknown persona '{p}'")
    for key in ("scenarioRef", "note"):
        if key in item:
            _check_str(f"{where}.{key}", item[key], 500)
    if "distractor" in item and not isinstance(item["distractor"], bool):
        _fail(f"{where}.distractor", "must be true or false")

    if itype == "email":
        _check_str(f"{where}.subject", item["subject"], 300)
        _check_addr(f"{where}.from", item["from"])
        _check_addr_list(f"{where}.to", item["to"])
        if "cc" in item:
            _check_addr_list(f"{where}.cc", item["cc"])
        _check_str(f"{where}.body", item["body"], 20000, allow_empty=True)
        if item.get("importance", "normal") not in ("low", "normal", "high"):
            _fail(f"{where}.importance", "must be low, normal or high")
        for key in ("isRead", "isDraft"):
            if key in item and not isinstance(item[key], bool):
                _fail(f"{where}.{key}", "must be true or false")
        if "conversation" in item:
            _check_str(f"{where}.conversation", item["conversation"], 100)
        if item.get("folder", "inbox") not in EMAIL_FOLDERS:
            _fail(f"{where}.folder", f"must be one of {list(EMAIL_FOLDERS)}")
    elif itype == "event":
        _check_str(f"{where}.subject", item["subject"], 300)
        end = _check_dt(f"{where}.end", item["end"])
        if end <= start:
            _fail(f"{where}.end", "must be after date")
        _check_addr(f"{where}.organizer", item["organizer"])
        _check_addr_list(f"{where}.attendees", item["attendees"])
        for key in ("location", "body"):
            if key in item:
                _check_str(f"{where}.{key}", item[key], 5000, allow_empty=True)
        if "isOnlineMeeting" in item and not isinstance(item["isOnlineMeeting"], bool):
            _fail(f"{where}.isOnlineMeeting", "must be true or false")
        if "transcriptFile" in item:
            _check_str(f"{where}.transcriptFile", item["transcriptFile"], 64)
    elif itype == "chat":
        if item["chatType"] not in ("oneOnOne", "group"):
            _fail(f"{where}.chatType", "must be oneOnOne or group")
        if item.get("topic") is not None:
            _check_str(f"{where}.topic", item["topic"], 200)
        members = item["members"]
        if not isinstance(members, list) or not 2 <= len(members) <= MAX_PERSONAS:
            _fail(f"{where}.members", "must list 2 or more persona ids")
        for m in members:
            if m not in persona_ids:
                _fail(f"{where}.members", f"unknown persona '{m}'")
        msgs = item["messages"]
        if not isinstance(msgs, list) or not 1 <= len(msgs) <= MAX_CHAT_MESSAGES:
            _fail(f"{where}.messages", f"must have 1 to {MAX_CHAT_MESSAGES} messages")
        for i, m in enumerate(msgs):
            w = f"{where}.messages[{i}]"
            if not isinstance(m, dict) or not CHAT_MESSAGE_KEYS <= set(m) <= CHAT_MESSAGE_KEYS | {"via"}:
                _fail(w, "must be an object with 'date', 'from' and 'text' (and optionally 'via')")
            if "via" in m and m["via"] not in CHAT_MESSAGE_VIA:
                _fail(f"{w}.via", "must be 'agent'")
            _check_dt(f"{w}.date", m["date"])
            if m["from"] not in members:
                _fail(f"{w}.from", "must be one of the chat members")
            _check_str(f"{w}.text", m["text"], 4000)
    elif itype == "file":
        _check_str(f"{where}.name", item["name"], 200)
        if "/" in item["name"] or "\\" in item["name"]:
            _fail(f"{where}.name", "must not contain path separators")
        _check_str(f"{where}.mimeType", item["mimeType"], 120)
        drive = _check_str(f"{where}.drive", item["drive"], 80)
        kind, _, key = drive.partition(":")
        if kind == "onedrive":
            if key not in persona_ids:
                _fail(f"{where}.drive", f"unknown persona '{key}'")
        elif kind == "site":
            if key not in site_ids:
                _fail(f"{where}.drive", f"unknown site '{key}'")
        else:
            _fail(f"{where}.drive", "must be 'onedrive:<persona>' or 'site:<site id>'")
        _check_addr(f"{where}.createdBy", item["createdBy"])
        _check_str(f"{where}.content", item["content"], 60000, allow_empty=True)
        if "relatedEvent" in item:
            _check_str(f"{where}.relatedEvent", item["relatedEvent"], 64)
    elif itype == "person":
        _check_str(f"{where}.displayName", item["displayName"], 200)
        if not EMAIL_RE.match(_check_str(f"{where}.mail", item["mail"], 254)):
            _fail(f"{where}.mail", "is not a valid mail address")
        _check_str(f"{where}.jobTitle", item["jobTitle"], 200)
        _check_str(f"{where}.companyName", item["companyName"], 200)
        for key in ("department", "phone"):
            if key in item:
                _check_str(f"{where}.{key}", item[key], 100)


def validate_pack(pack: Any) -> None:
    if not isinstance(pack, dict):
        _fail("pack", "must be a JSON object")
    allowed = {"schemaVersion", "scenario", "description", "now", "tenant", "personas", "sites", "items"}
    if set(pack) - allowed:
        _fail("pack", f"unknown keys {sorted(set(pack) - allowed)}")
    if pack.get("schemaVersion") != 1:
        _fail("pack.schemaVersion", "must be 1")
    _check_str("pack.scenario", pack.get("scenario"), 100)
    if "description" in pack:
        _check_str("pack.description", pack["description"], 2000)
    if "now" in pack:
        _check_dt("pack.now", pack["now"])
    tenant = pack.get("tenant")
    if not isinstance(tenant, dict) or set(tenant) - {"name", "domain", "tenantId"}:
        _fail("pack.tenant", "must be an object with name, domain and tenantId")
    _check_str("pack.tenant.name", tenant.get("name"), 200)
    _check_str("pack.tenant.domain", tenant.get("domain"), 200)
    if not GUID_RE.match(_check_str("pack.tenant.tenantId", tenant.get("tenantId"), 36)):
        _fail("pack.tenant.tenantId", "must be a GUID")
    personas = pack.get("personas")
    if not isinstance(personas, list) or not 1 <= len(personas) <= MAX_PERSONAS:
        _fail("pack.personas", f"must have 1 to {MAX_PERSONAS} entries")
    persona_ids: set[str] = set()
    for i, p in enumerate(personas):
        validate_persona(f"pack.personas[{i}]", p)
        if p["id"] in persona_ids:
            _fail(f"pack.personas[{i}]", "duplicate id")
        persona_ids.add(p["id"])
    sites = pack.get("sites", [])
    if not isinstance(sites, list) or len(sites) > MAX_SITES:
        _fail("pack.sites", f"must be a list with at most {MAX_SITES} entries")
    site_ids: set[str] = set()
    for i, s in enumerate(sites):
        if not isinstance(s, dict) or set(s) != {"id", "displayName"}:
            _fail(f"pack.sites[{i}]", "must be an object with exactly 'id' and 'displayName'")
        if not PERSONA_ID_RE.match(_check_str(f"pack.sites[{i}].id", s["id"], 31)):
            _fail(f"pack.sites[{i}].id", "must match ^[a-z][a-z0-9-]{1,30}$")
        _check_str(f"pack.sites[{i}].displayName", s["displayName"], 100)
        site_ids.add(s["id"])
    items = pack.get("items")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        _fail("pack.items", f"must be a list with at most {MAX_ITEMS} entries")
    ids: set[str] = set()
    for i, item in enumerate(items):
        validate_item(item, persona_ids, site_ids, where=f"pack.items[{i}]")
        if item["id"] in ids:
            _fail(f"pack.items[{i}]", f"duplicate id '{item['id']}'")
        ids.add(item["id"])
    by_id = {it["id"]: it for it in items}
    for it in items:
        for ref_key, ref_type in (("transcriptFile", "file"), ("relatedEvent", "event")):
            ref = it.get(ref_key)
            if ref is not None and (ref not in by_id or by_id[ref]["type"] != ref_type):
                _fail(f"item '{it['id']}'.{ref_key}", f"must reference a {ref_type} item")


def seed_file(name: str | None = None) -> Path:
    """Path of a bundled scenario pack, for example 'strandvik' for seed/strandvik.json."""
    name = (name or DEFAULT_SEED).strip().lower()
    if not SEED_NAME_RE.match(name):
        raise PackError(f"WORKIQ_SEED '{name}' is not a valid seed name")
    return SEED_DIR / f"{name}.json"


def load_pack_file(path: str | Path | None = None, seed: str | None = None) -> dict:
    p = Path(path) if path else seed_file(seed)
    with p.open("r", encoding="utf-8") as fh:
        pack = json.load(fh)
    validate_pack(pack)
    return pack


# ---------------------------------------------------------------------------
# Derived identifiers. Deterministic, so links stay stable across restarts.


def _h(*parts: str) -> bytes:
    return hashlib.sha256("|".join(parts).encode("utf-8")).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def graph_message_id(item_id: str) -> str:
    return "AAMkADc2" + _b64(_h("msg", item_id))[:40]


def graph_event_id(item_id: str) -> str:
    return "AAMkADc2" + _b64(_h("evt", item_id))[:36] + "AE"


def conversation_id(key: str) -> str:
    return "AAQkADc2" + _b64(_h("conv", key))[:32]


def chat_id(item_id: str) -> str:
    return "19:" + _h("chat", item_id).hex()[:32] + "@thread.v2"


def drive_item_id(item_id: str) -> str:
    return "01" + base64.b32encode(_h("file", item_id)).decode("ascii")[:32]


def drive_id(drive_key: str) -> str:
    return "b!" + _b64(_h("drive", drive_key))[:64]


def stable_guid(*parts: str) -> str:
    return str(uuid.UUID(bytes=_h("guid", *parts)[:16], version=4))


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


@dataclass(frozen=True)
class Persona:
    id: str
    display_name: str
    job_title: str
    mail: str
    user_id: str
    department: str = ""
    office_location: str = ""


@dataclass
class Entry:
    item: dict
    kind: str
    gid: str
    dt: datetime
    visible: frozenset[str]
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.item["id"]


class Store:
    """Immutable snapshot of a validated pack plus a search index. Replace it as a whole."""

    def __init__(self, pack: dict):
        validate_pack(pack)
        self.pack = pack
        self.now = parse_dt(pack.get("now", "2026-12-07T08:00:00+01:00"))
        self.tenant = pack["tenant"]
        self.personas: dict[str, Persona] = {
            p["id"]: Persona(
                id=p["id"],
                display_name=p["displayName"],
                job_title=p["jobTitle"],
                mail=p["mail"],
                user_id=p["userId"],
                department=p.get("department", ""),
                office_location=p.get("officeLocation", ""),
            )
            for p in pack["personas"]
        }
        self.persona_by_mail = {p.mail.lower(): p for p in self.personas.values()}
        domain = self.tenant["domain"].split(".")[0]
        self.sites: dict[str, dict] = {}
        for s in pack.get("sites", []):
            self.sites[s["id"]] = {
                "key": s["id"],
                "displayName": s["displayName"],
                "siteId": f"{domain}.sharepoint.com,{stable_guid('site', s['id'])},{stable_guid('web', s['id'])}",
                "driveId": drive_id("site:" + s["id"]),
            }
        self.entries: list[Entry] = []
        self.by_gid: dict[str, Entry] = {}
        self.by_item_id: dict[str, Entry] = {}
        for item in pack["items"]:
            self._add_entry(item)
        self.index = ranking.Index([self._doc(e) for e in self.entries] + [self._persona_doc(p) for p in self.personas.values()])

    # -- construction -------------------------------------------------------

    def _add_entry(self, item: dict) -> None:
        kind = item["type"]
        dt = parse_dt(item["date"])
        extra: dict[str, Any] = {}
        if kind == "email":
            gid = graph_message_id(item["id"])
            extra["conversationId"] = conversation_id(item.get("conversation", item["id"]))
        elif kind == "event":
            gid = graph_event_id(item["id"])
            extra["end"] = parse_dt(item["end"])
        elif kind == "chat":
            gid = chat_id(item["id"])
            msgs = []
            for m in item["messages"]:
                mdt = parse_dt(m["date"])
                msgs.append({"id": str(epoch_ms(mdt)), "dt": mdt, "from": m["from"], "text": m["text"], "via": m.get("via")})
            msgs.sort(key=lambda m: m["dt"])
            extra["messages"] = msgs
        elif kind == "file":
            gid = drive_item_id(item["id"])
            extra["driveKey"] = item["drive"]
            extra["driveId"] = drive_id(item["drive"])
            extra["sizeBytes"] = len(item["content"].encode("utf-8"))
        else:
            gid = stable_guid("person", item["id"])
        entry = Entry(item=item, kind=kind, gid=gid, dt=dt, visible=frozenset(item["visibleTo"]), extra=extra)
        self.entries.append(entry)
        self.by_gid[gid] = entry
        self.by_item_id[item["id"]] = entry

    def _doc(self, e: Entry) -> ranking.Doc:
        it = e.item
        if e.kind == "email":
            people = " ".join(a.get("name", "") for a in [it["from"], *it["to"], *it.get("cc", [])])
            fields = {"title": it["subject"], "body": it["body"], "people": people}
        elif e.kind == "event":
            people = " ".join(a.get("name", "") for a in [it["organizer"], *it["attendees"]])
            fields = {"title": it["subject"], "body": it.get("body", "") + " " + it.get("location", ""), "people": people}
        elif e.kind == "chat":
            body = "\n".join(f"{self.sender_label(m)}: {m['text']}" for m in e.extra["messages"])
            fields = {"title": self.chat_title(e), "body": body}
        elif e.kind == "file":
            fields = {"title": it["name"].rsplit(".", 1)[0], "body": transcript_text(it["content"]) if is_transcript(it) else it["content"]}
        else:
            fields = {"title": it["displayName"], "body": f"{it['jobTitle']} {it['companyName']} {it.get('department', '')} {it['mail']}"}
        return ranking.Doc(doc_id=e.id, fields=fields, timestamp=e.dt.timestamp())

    @staticmethod
    def _persona_doc(p: Persona) -> ranking.Doc:
        body = f"{p.job_title} {p.department} {p.office_location} {p.mail}"
        return ranking.Doc(doc_id=PERSONA_DOC_PREFIX + p.id, fields={"title": p.display_name, "body": body})

    # -- helpers ------------------------------------------------------------

    def display_name(self, persona_id: str) -> str:
        p = self.personas.get(persona_id)
        return p.display_name if p else persona_id

    def sender_label(self, m: dict) -> str:
        """Display name of a chat message sender. Agent posts say whose agent wrote them."""
        name = self.display_name(m["from"])
        if m.get("via") == "agent":
            return f"{name}'s agent (on behalf of {name})"
        return name

    def chat_title(self, e: Entry) -> str:
        topic = e.item.get("topic")
        if topic:
            return topic
        return ", ".join(sorted(self.display_name(m) for m in e.item["members"]))

    def can_see(self, e: Entry, persona_id: str) -> bool:
        return persona_id in e.visible

    def visible(self, persona_id: str, kind: str | None = None) -> list[Entry]:
        return [e for e in self.entries if persona_id in e.visible and (kind is None or e.kind == kind)]

    def get_visible(self, gid: str, persona_id: str, kind: str | None = None) -> Entry | None:
        e = self.by_gid.get(gid)
        if e is None or persona_id not in e.visible or (kind and e.kind != kind):
            return None
        return e

    def email_folder(self, e: Entry, persona_id: str) -> str:
        if e.item.get("folder") == "drafts" or e.item.get("isDraft"):
            return "drafts"
        if e.item["from"]["address"].lower() == self.personas[persona_id].mail.lower():
            return "sentitems"
        return "inbox"

    def site_by_ref(self, ref: str) -> dict | None:
        for s in self.sites.values():
            if ref in (s["key"], s["siteId"]):
                return s
        return None

    def drive_owner_label(self, e: Entry) -> str:
        kind, _, key = e.extra["driveKey"].partition(":")
        if kind == "onedrive":
            return f"OneDrive of {self.display_name(key)}"
        site = self.sites.get(key)
        return f"SharePoint site {site['displayName']}" if site else "SharePoint"

    def item_count(self) -> int:
        return len(self.entries)


def is_transcript(item: dict) -> bool:
    return item.get("type") == "file" and item.get("mimeType") == "text/vtt"


_VTT_TIMING = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3} --> .*$")
_VTT_VOICE = re.compile(r"<v ([^>]+)>(.*?)(?:</v>)?$")


def transcript_lines(content: str) -> list[tuple[str, str]]:
    """Parse a WebVTT-like transcript into (speaker, text) pairs."""
    lines: list[tuple[str, str]] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT" or _VTT_TIMING.match(line) or line.isdigit():
            continue
        m = _VTT_VOICE.match(line)
        if m:
            lines.append((m.group(1).strip(), m.group(2).strip()))
        elif ":" in line:
            speaker, _, text = line.partition(":")
            lines.append((speaker.strip(), text.strip()))
        else:
            lines.append(("", line))
    return lines


def transcript_text(content: str) -> str:
    return "\n".join(f"{s}: {t}" if s else t for s, t in transcript_lines(content))
