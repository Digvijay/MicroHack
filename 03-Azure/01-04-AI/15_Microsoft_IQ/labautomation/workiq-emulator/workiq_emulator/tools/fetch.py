"""The fetch, fetch_blob and call_function read paths, emulating Microsoft Graph v1.0."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import parse_qsl, unquote, urlsplit

from .. import graph
from ..ranking import normalize
from ..state import ToolContext
from ..store import Entry, parse_dt
from .common import MAX_ENTITY_URLS, MAX_PATH_CHARS, POLICY_BLOCKED, ToolError, error_result, json_result, opt_str, req_str

DEFAULT_TOP = 25
MAX_TOP = 100
CHAT_MESSAGE_CAP = 10
ALLOWED_PREFIXES = ("/me/", "/users/", "/sites/", "/chats/", "/drives/")
ALLOWED_EXACT = ("/me", "/users")
BLOCKED_SEGMENTS = ("authentication", "serviceprincipals")
GRAPH_ABSOLUTE = ("https://graph.microsoft.com/v1.0", "https://graph.microsoft.com/beta")
SUPPORTED_PARAMS = {"$top", "$select", "$filter", "$orderby", "$search", "$count", "startdatetime", "enddatetime"}


class GraphError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def as_result(self) -> dict:
        return {"data": {"error": {"code": self.code, "message": self.message}}, "statusCode": self.status}


# ---------------------------------------------------------------------------
# Path policy


def split_url(raw: str) -> tuple[str, dict[str, str]]:
    if not isinstance(raw, str) or not raw.strip():
        raise GraphError(400, "BadRequest", "Entity path must be a non-empty string.")
    if len(raw) > MAX_PATH_CHARS:
        raise GraphError(400, "BadRequest", "Entity path is too long.")
    url = raw.strip()
    for prefix in GRAPH_ABSOLUTE:
        if url.lower().startswith(prefix):
            url = url[len(prefix):]
            break
    if "://" in url.split("?", 1)[0]:
        raise GraphError(400, "BadRequest", "Use a relative Work IQ path such as /me/messages, not an external URL.")
    parts = urlsplit(url)
    path = parts.path
    for enc, dec in (("%27", "'"), ("%28", "("), ("%29", ")")):
        path = path.replace(enc, dec).replace(enc.lower(), dec)
    if not path.startswith("/"):
        path = "/" + path
    if len(path) > 1:
        path = path.rstrip("/")
    decoded_segments = [unquote(s) for s in path.split("/")]
    if any(s in ("..", ".") for s in decoded_segments):
        raise GraphError(400, "BadRequest", "Relative path segments are not allowed.")
    params: dict[str, str] = {}
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        params[key.strip().lower()] = value
    return path, params


def check_policy(path: str) -> None:
    lower = path.lower()
    segments = [unquote(s).lower() for s in lower.split("/")]
    if any(s in BLOCKED_SEGMENTS for s in segments):
        raise GraphError(403, "Forbidden", f"Access denied for path '{path}' by Work IQ tenant policy.")
    if lower in ALLOWED_EXACT or lower.startswith(ALLOWED_PREFIXES):
        return
    raise GraphError(
        403,
        "Forbidden",
        f"Access denied for path '{path}' by Work IQ tenant policy. Allowed prefixes: /me/, /users/, /sites/, /chats/, /drives/.",
    )


def check_params(params: dict[str, str], chat_messages: bool = False) -> None:
    for key in ("$skip", "$skiptoken"):
        if key in params:
            raise GraphError(400, "BadRequest", f"The {key} query parameter is blocked by Work IQ tenant policy.")
    unknown = [k for k in params if k not in SUPPORTED_PARAMS]
    if unknown:
        raise GraphError(400, "BadRequest", f"Query parameter(s) not supported by the emulator: {', '.join(sorted(unknown))}.")


# ---------------------------------------------------------------------------
# OData helpers


def _get_path(obj: Any, field: str) -> Any:
    cur = obj
    for part in field.split("/"):
        if isinstance(cur, dict):
            # Graph property names are case-insensitive.
            match = next((k for k in cur if k.lower() == part.lower()), None)
            cur = cur.get(match) if match else None
        else:
            return None
    return cur


_FILTER_FUNC = re.compile(r"^(contains|startswith|endswith)\(\s*([\w/]+)\s*,\s*'((?:[^']|'')*)'\s*\)$", re.I)
_FILTER_CMP = re.compile(r"^([\w/]+)\s+(eq|ne|gt|ge|lt|le)\s+(.+)$", re.I)


def _literal(text: str) -> Any:
    text = text.strip()
    if text.startswith("'") and text.endswith("'") and len(text) >= 2:
        return text[1:-1].replace("''", "'")
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    if low == "null":
        return None
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        pass
    try:
        return parse_dt(text)
    except ValueError:
        raise GraphError(400, "BadRequest", f"Invalid literal in $filter: {text}") from None


def _as_comparable(value: Any, literal: Any) -> tuple[Any, Any]:
    if isinstance(literal, datetime) and isinstance(value, str):
        try:
            return parse_dt(value), literal
        except ValueError:
            return value, literal.isoformat()
    if isinstance(value, dict) and "dateTime" in value and isinstance(literal, datetime):
        return datetime.fromisoformat(value["dateTime"][:19]).replace(tzinfo=timezone.utc), literal
    if isinstance(literal, str) and isinstance(value, str):
        return value.lower(), literal.lower()
    return value, literal


def build_filter(expr: str) -> Callable[[dict], bool]:
    if len(expr) > 500:
        raise GraphError(400, "BadRequest", "$filter is too long.")
    clauses = re.split(r"\s+and\s+", expr.strip(), flags=re.I)
    preds: list[Callable[[dict], bool]] = []
    for clause in clauses:
        clause = clause.strip()
        while clause.startswith("(") and clause.endswith(")") and not _FILTER_FUNC.match(clause):
            clause = clause[1:-1].strip()
        m = _FILTER_FUNC.match(clause)
        if m:
            fn, field, needle = m.group(1).lower(), m.group(2), m.group(3).replace("''", "'").lower()

            def pred(obj: dict, fn=fn, field=field, needle=needle) -> bool:
                value = _get_path(obj, field)
                if not isinstance(value, str):
                    return False
                v = normalize(value)
                n = normalize(needle)
                return {"contains": n in v, "startswith": v.startswith(n), "endswith": v.endswith(n)}[fn]

            preds.append(pred)
            continue
        m = _FILTER_CMP.match(clause)
        if m:
            field, op, literal = m.group(1), m.group(2).lower(), _literal(m.group(3))

            def pred(obj: dict, field=field, op=op, literal=literal) -> bool:
                value, lit = _as_comparable(_get_path(obj, field), literal)
                try:
                    if op == "eq":
                        return value == lit
                    if op == "ne":
                        return value != lit
                    if value is None:
                        return False
                    return {"gt": value > lit, "ge": value >= lit, "lt": value < lit, "le": value <= lit}[op]
                except TypeError:
                    return False

            preds.append(pred)
            continue
        raise GraphError(
            400,
            "BadRequest",
            f"Unsupported $filter expression: '{clause}'. The emulator supports eq, ne, gt, ge, lt, le, contains, startswith, endswith joined with 'and'.",
        )
    return lambda obj: all(p(obj) for p in preds)


def _search_text(obj: dict) -> str:
    parts: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for k, x in v.items():
                if not k.startswith("@"):
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(obj)
    return normalize(" ".join(parts))


def apply_collection(
    items: list[dict], params: dict[str, str], context: str, default_order: tuple[str, bool] | None, cap: int = MAX_TOP
) -> dict:
    if "$filter" in params:
        pred = build_filter(params["$filter"])
        items = [i for i in items if pred(i)]
    if "$search" in params:
        terms = [normalize(t) for t in re.findall(r"[\w-]+", params["$search"].strip().strip('"'))]
        if terms:
            items = [i for i in items if all(t in _search_text(i) for t in terms)]
    order = params.get("$orderby")
    if order:
        for clause in reversed([c.strip() for c in order.split(",") if c.strip()]):
            field, _, direction = clause.partition(" ")
            desc = direction.strip().lower() == "desc"
            items = sorted(items, key=lambda i, f=field: _sort_key(_get_path(i, f)), reverse=desc)
    elif default_order:
        field, desc = default_order
        items = sorted(items, key=lambda i: _sort_key(_get_path(i, field)), reverse=desc)
    top_raw = params.get("$top")
    top = min(DEFAULT_TOP, cap)
    if top_raw is not None:
        try:
            top = int(top_raw)
        except ValueError:
            raise GraphError(400, "BadRequest", "$top must be an integer.") from None
        if top < 1:
            raise GraphError(400, "BadRequest", "$top must be 1 or greater.")
        top = min(top, cap)
    total = len(items)
    items = items[:top]
    select = params.get("$select")
    if select:
        fields = [f.strip() for f in select.split(",") if f.strip()]
        items = [_select(i, fields) for i in items]
    data: dict[str, Any] = {"@odata.context": graph.GRAPH_CONTEXT + context, "value": items}
    if params.get("$count", "").lower() == "true":
        data["@odata.count"] = total
    return data


def _sort_key(value: Any) -> tuple:
    if isinstance(value, dict) and "dateTime" in value:
        value = value["dateTime"]
    if value is None:
        return (0, "")
    return (1, str(value).lower())


def _select(obj: dict, fields: list[str]) -> dict:
    out = {k: v for k, v in obj.items() if k.startswith("@") or k == "id"}
    lower = {k.lower(): k for k in obj}
    for f in fields:
        key = lower.get(f.lower())
        if key:
            out[key] = obj[key]
    return out


def _single(obj: dict, params: dict[str, str], context: str) -> dict:
    select = params.get("$select")
    if select:
        obj = _select(obj, [f.strip() for f in select.split(",") if f.strip()])
    return {"@odata.context": graph.GRAPH_CONTEXT + context, **obj}


# ---------------------------------------------------------------------------
# Route handlers. Each returns the Graph JSON body or raises GraphError.


def _not_found(what: str) -> GraphError:
    return GraphError(404, "ErrorItemNotFound", f"The {what} was not found or you do not have access to it.")


def _messages(ctx: ToolContext, params: dict, folder: str | None) -> dict:
    s, pid = ctx.store, ctx.persona.id
    items = [
        graph.message(s, e, pid, ctx.base_url)
        for e in s.visible(pid, "email")
        if folder is None or s.email_folder(e, pid) == folder
    ]
    return apply_collection(items, params, f"users('{ctx.persona.user_id}')/messages", ("receivedDateTime", True))


def _message(ctx: ToolContext, params: dict, gid: str) -> dict:
    e = ctx.store.get_visible(gid, ctx.persona.id, "email")
    if not e:
        raise _not_found("message")
    return _single(graph.message(ctx.store, e, ctx.persona.id, ctx.base_url), params, f"users('{ctx.persona.user_id}')/messages/$entity")


def _events(ctx: ToolContext, params: dict) -> dict:
    items = [graph.event(ctx.store, e, ctx.persona.id, ctx.base_url) for e in ctx.store.visible(ctx.persona.id, "event")]
    return apply_collection(items, params, f"users('{ctx.persona.user_id}')/events", ("start/dateTime", False))


def _event(ctx: ToolContext, params: dict, gid: str) -> dict:
    e = ctx.store.get_visible(gid, ctx.persona.id, "event")
    if not e:
        raise _not_found("event")
    return _single(graph.event(ctx.store, e, ctx.persona.id, ctx.base_url), params, f"users('{ctx.persona.user_id}')/events/$entity")


def _calendar_view(ctx: ToolContext, params: dict) -> dict:
    start_raw, end_raw = params.get("startdatetime"), params.get("enddatetime")
    if not start_raw or not end_raw:
        raise GraphError(400, "ErrorInvalidParameter", "This request requires a time window specified by the query string parameters StartDateTime and EndDateTime.")
    try:
        start = _parse_window(start_raw)
        end = _parse_window(end_raw)
    except ValueError:
        raise GraphError(400, "ErrorInvalidParameter", "StartDateTime and EndDateTime must be ISO 8601 date and time values.") from None
    entries = [e for e in ctx.store.visible(ctx.persona.id, "event") if e.dt < end and e.extra["end"] > start]
    items = [graph.event(ctx.store, e, ctx.persona.id, ctx.base_url) for e in entries]
    filtered = {k: v for k, v in params.items() if k not in ("startdatetime", "enddatetime")}
    return apply_collection(items, filtered, f"users('{ctx.persona.user_id}')/calendarView", ("start/dateTime", False))


def _parse_window(value: str) -> datetime:
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _chats(ctx: ToolContext, params: dict) -> dict:
    items = [graph.chat(ctx.store, e, ctx.base_url) for e in ctx.store.visible(ctx.persona.id, "chat")]
    return apply_collection(items, params, "chats", ("lastUpdatedDateTime", True))


def _chat_entry(ctx: ToolContext, chat_id: str) -> Entry:
    e = ctx.store.get_visible(chat_id, ctx.persona.id, "chat")
    if not e:
        raise _not_found("chat")
    return e


def _chat(ctx: ToolContext, params: dict, chat_id: str) -> dict:
    return _single(graph.chat(ctx.store, _chat_entry(ctx, chat_id), ctx.base_url), params, "chats/$entity")


def _chat_messages(ctx: ToolContext, params: dict, chat_id: str) -> dict:
    e = _chat_entry(ctx, chat_id)
    items = [graph.chat_message(ctx.store, e, m) for m in e.extra["messages"]]
    return apply_collection(items, params, f"chats('{chat_id}')/messages", ("createdDateTime", True), cap=CHAT_MESSAGE_CAP)


def _chat_message(ctx: ToolContext, params: dict, chat_id: str, msg_id: str) -> dict:
    e = _chat_entry(ctx, chat_id)
    for m in e.extra["messages"]:
        if m["id"] == msg_id:
            return _single(graph.chat_message(ctx.store, e, m), params, f"chats('{chat_id}')/messages/$entity")
    raise _not_found("chat message")


def _drive(ctx: ToolContext, params: dict) -> dict:
    return _single(graph.drive(ctx.store, f"onedrive:{ctx.persona.id}", ctx.base_url), params, "drives/$entity")


def _files(ctx: ToolContext, drive_key: str | None = None, drive_id: str | None = None) -> list[Entry]:
    out = []
    for e in ctx.store.visible(ctx.persona.id, "file"):
        if drive_key and e.extra["driveKey"] != drive_key:
            continue
        if drive_id and e.extra["driveId"] != drive_id:
            continue
        out.append(e)
    return out


def _children(ctx: ToolContext, params: dict, entries: list[Entry]) -> dict:
    items = [graph.drive_item(ctx.store, e, ctx.base_url) for e in entries]
    return apply_collection(items, params, "driveItems", ("name", False))


def _my_children(ctx: ToolContext, params: dict) -> dict:
    return _children(ctx, params, _files(ctx, drive_key=f"onedrive:{ctx.persona.id}"))


def _shared_with_me(ctx: ToolContext, params: dict) -> dict:
    own = f"onedrive:{ctx.persona.id}"
    return _children(ctx, params, [e for e in _files(ctx) if e.extra["driveKey"] != own])


def _recent(ctx: ToolContext, params: dict) -> dict:
    items = [graph.drive_item(ctx.store, e, ctx.base_url) for e in _files(ctx)]
    return apply_collection(items, params, "driveItems", ("lastModifiedDateTime", True))


def _drive_search(ctx: ToolContext, params: dict, q: str) -> dict:
    terms = [normalize(t) for t in re.findall(r"[\w-]+", unquote(q))]
    hits = []
    for e in _files(ctx):
        text = normalize(e.item["name"] + " " + e.item["content"])
        if all(t in text for t in terms):
            hits.append(graph.drive_item(ctx.store, e, ctx.base_url))
    return apply_collection(hits, params, "driveItems", ("lastModifiedDateTime", True))


def _drive_item_entry(ctx: ToolContext, item_id: str, drive_id: str | None = None) -> Entry:
    e = ctx.store.get_visible(item_id, ctx.persona.id, "file")
    if not e or (drive_id and e.extra["driveId"] != drive_id):
        raise _not_found("item")
    return e


def _drive_item(ctx: ToolContext, params: dict, item_id: str, drive_id: str | None = None) -> dict:
    return _single(graph.drive_item(ctx.store, _drive_item_entry(ctx, item_id, drive_id), ctx.base_url), params, "driveItems/$entity")


def _drive_children(ctx: ToolContext, params: dict, drive_id: str) -> dict:
    return _children(ctx, params, _files(ctx, drive_id=drive_id))


def _site(ctx: ToolContext, params: dict, site_ref: str) -> dict:
    site = ctx.store.site_by_ref(site_ref)
    if not site:
        raise _not_found("site")
    return _single(
        {"id": site["siteId"], "name": site["key"], "displayName": site["displayName"], "webUrl": f"{ctx.base_url}/viewer/files"},
        params,
        "sites/$entity",
    )


def _site_children(ctx: ToolContext, params: dict, site_ref: str) -> dict:
    site = ctx.store.site_by_ref(site_ref)
    if not site:
        raise _not_found("site")
    return _children(ctx, params, _files(ctx, drive_key=f"site:{site['key']}"))


def _people(ctx: ToolContext, params: dict) -> dict:
    s = ctx.store
    items = [graph.person_from_persona(s, p) for p in s.personas.values() if p.id != ctx.persona.id]
    items += [graph.person_from_entry(s, e) for e in s.visible(ctx.persona.id, "person")]
    return apply_collection(items, params, f"users('{ctx.persona.user_id}')/people", None)


def _person(ctx: ToolContext, params: dict, ref: str) -> dict:
    for item in _people(ctx, {"$top": "100"})["value"]:
        if item["id"].lower() == ref.lower():
            return _single(item, params, f"users('{ctx.persona.user_id}')/people/$entity")
    raise _not_found("person")


def _users(ctx: ToolContext, params: dict) -> dict:
    items = [graph.user(ctx.store, p) for p in ctx.store.personas.values()]
    for i in items:
        i.pop("@odata.context", None)
    return apply_collection(items, params, "users", ("displayName", False))


def _user(ctx: ToolContext, params: dict, ref: str) -> dict:
    ref_l = ref.lower()
    for p in ctx.store.personas.values():
        if ref_l in (p.user_id.lower(), p.mail.lower()):
            data = graph.user(ctx.store, p)
            data.pop("@odata.context", None)
            return _single(data, params, "users/$entity")
    raise GraphError(404, "Request_ResourceNotFound", f"Resource '{ref}' does not exist or one of its queried reference-property objects are not present.")


def _me(ctx: ToolContext, params: dict) -> dict:
    data = graph.user(ctx.store, ctx.persona)
    data.pop("@odata.context", None)
    return _single(data, params, "users/$entity")


SEG = r"([^/]+)"
ROUTES: list[tuple[re.Pattern, Callable[..., dict], str]] = [
    (re.compile(p, re.I), h, kind)
    for p, h, kind in [
        (r"^/me$", _me, "single"),
        (r"^/me/messages$", lambda c, q: _messages(c, q, None), "collection"),
        (r"^/me/messages/" + SEG + "$", _message, "single"),
        (r"^/me/mailFolders/inbox/messages$", lambda c, q: _messages(c, q, "inbox"), "collection"),
        (r"^/me/mailFolders/sentitems/messages$", lambda c, q: _messages(c, q, "sentitems"), "collection"),
        (r"^/me/mailFolders/drafts/messages$", lambda c, q: _messages(c, q, "drafts"), "collection"),
        (r"^/me/mailFolders/[^/]+/messages/" + SEG + "$", _message, "single"),
        (r"^/me/(?:events|calendar/events)$", _events, "collection"),
        (r"^/me/(?:events|calendar/events)/" + SEG + "$", _event, "single"),
        (r"^/me/(?:calendarView|calendar/calendarView)$", _calendar_view, "collection"),
        (r"^/me/chats$", _chats, "collection"),
        (r"^/(?:me/)?chats/" + SEG + "$", _chat, "single"),
        (r"^/(?:me/)?chats/" + SEG + "/messages$", _chat_messages, "collection"),
        (r"^/(?:me/)?chats/" + SEG + "/messages/" + SEG + "$", _chat_message, "single"),
        (r"^/me/drive$", _drive, "single"),
        (r"^/me/drive/root/children$", _my_children, "collection"),
        (r"^/me/drive/sharedWithMe$", _shared_with_me, "collection"),
        (r"^/me/drive/recent$", _recent, "collection"),
        (r"^/me/drive/root/search\(q='(.*)'\)$", _drive_search, "collection"),
        (r"^/me/drive/items/" + SEG + "$", _drive_item, "single"),
        (r"^/drives/" + SEG + "/items/" + SEG + "$", lambda c, q, d, i: _drive_item(c, q, i, d), "single"),
        (r"^/drives/" + SEG + "/root/children$", _drive_children, "collection"),
        (r"^/sites/" + SEG + "$", _site, "single"),
        (r"^/sites/" + SEG + "/drive/root/children$", _site_children, "collection"),
        (r"^/sites/" + SEG + "/drive/items/" + SEG + "$", lambda c, q, s, i: _drive_item(c, q, i), "single"),
        (r"^/me/people$", _people, "collection"),
        (r"^/me/people/" + SEG + "$", _person, "single"),
        (r"^/users$", _users, "collection"),
        (r"^/users/" + SEG + "$", _user, "single"),
    ]
]


def fetch_one(ctx: ToolContext, raw: str) -> dict:
    try:
        path, params = split_url(raw)
        check_policy(path)
        check_params(params)
        for pattern, handler, _kind in ROUTES:
            m = pattern.match(path)
            if m:
                args = [unquote(g) for g in m.groups()]
                return {"data": handler(ctx, params, *args), "statusCode": 200}
        raise GraphError(404, "NotFound", f"The path '{path}' is not available in the Work IQ emulator. Call search_paths to list supported paths.")
    except GraphError as err:
        return err.as_result()


def result_ids(results: list[dict]) -> list[str]:
    ids: list[str] = []
    for r in results:
        data = r.get("data") or {}
        if isinstance(data.get("value"), list):
            ids += [str(v.get("id")) for v in data["value"] if isinstance(v, dict)]
        elif data.get("id"):
            ids.append(str(data["id"]))
    return ids


# ---------------------------------------------------------------------------
# Tool entry points


def tool_fetch(ctx: ToolContext, args: dict) -> dict:
    urls = args.get("entityUrls")
    if not isinstance(urls, list) or not urls or not all(isinstance(u, str) for u in urls):
        raise ToolError("Invalid input: 'entityUrls' must be a non-empty array of strings.")
    if len(urls) > MAX_ENTITY_URLS:
        raise ToolError(f"Invalid input: 'entityUrls' has {len(urls)} entries, the limit is {MAX_ENTITY_URLS}.")
    opt_str(args, "query", 2000)
    results = [fetch_one(ctx, u) for u in urls]
    out = json_result({"results": results})
    out["_resultIds"] = result_ids(results)
    return out


_BLOB_ROUTES = [
    re.compile(r"^/drives/([^/]+)/items/([^/]+)/content$", re.I),
    re.compile(r"^/me/drive/items/()([^/]+)/content$", re.I),
    re.compile(r"^/sites/[^/]+/drive/items/()([^/]+)/content$", re.I),
]


def tool_fetch_blob(ctx: ToolContext, args: dict) -> dict:
    raw = req_str(args, "path", MAX_PATH_CHARS)
    fmt = opt_str(args, "format", 20)
    try:
        path, params = split_url(raw)
        check_policy(path)
        if fmt:
            raise GraphError(400, "BadRequest", f"Format conversion '{fmt}' is not supported by the emulator. Omit 'format'.")
        for pattern in _BLOB_ROUTES:
            m = pattern.match(path)
            if m:
                drive_id, item_id = unquote(m.group(1)) or None, unquote(m.group(2))
                e = _drive_item_entry(ctx, item_id, drive_id)
                raw_bytes = e.item["content"].encode("utf-8")
                structured = {
                    "statusCode": 200,
                    "contentType": blob_content_type(e.item),
                    "blobName": e.item["name"],
                    "sizeBytes": len(raw_bytes),
                    "base64Content": base64.b64encode(raw_bytes).decode("ascii"),
                }
                out = {
                    "content": [{"type": "text", "text": f"Fetched '{e.item['name']}' ({len(raw_bytes)} bytes). Read base64Content from structuredContent."}],
                    "structuredContent": structured,
                    "isError": False,
                    "_resultIds": [e.gid],
                }
                return out
        raise GraphError(404, "NotFound", "fetch_blob supports drive item content paths such as /drives/{drive-id}/items/{item-id}/content.")
    except GraphError as err:
        return error_result(f"{err.status} {err.code}: {err.message}", {"statusCode": err.status})


def blob_content_type(item: dict) -> str:
    # The emulator stores extracted text, not binary Office files.
    if item["mimeType"].startswith("text/"):
        return item["mimeType"] + "; charset=utf-8"
    return "text/plain; charset=utf-8"


READ_FUNCTIONS = (
    re.compile(r"^/me/(?:calendarView|calendar/calendarView)$", re.I),
    re.compile(r"^/me/drive/root/search\(q='.*'\)$", re.I),
)


def tool_call_function(ctx: ToolContext, args: dict) -> dict:
    # The documented example uses 'parentUrl'; accept both names.
    raw = opt_str(args, "functionUrl", MAX_PATH_CHARS) or opt_str(args, "parentUrl", MAX_PATH_CHARS)
    if not raw:
        raise ToolError("Invalid input: 'functionUrl' is required.")
    body = args.get("jsonBody")
    if isinstance(body, str) and body.strip():
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            raise ToolError("Invalid input: 'jsonBody' is not valid JSON.") from None
    try:
        path, _ = split_url(raw)
        check_policy(path)
    except GraphError as err:
        return error_result(f"{err.status} {err.code}: {err.message}", {"statusCode": err.status})
    if any(p.match(path) for p in READ_FUNCTIONS):
        result = fetch_one(ctx, raw)
        out = json_result(result)
        out["isError"] = result["statusCode"] >= 400
        out["_resultIds"] = result_ids([result])
        return out
    return error_result(f"{POLICY_BLOCKED} The function '{path}' is not an allowed read function.", {"statusCode": 403})
