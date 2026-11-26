"""search_paths, get_schema, list_agents and the policy-gated mutation tools."""

from __future__ import annotations

import json
import re
from datetime import datetime

from .. import graph
from ..state import MAX_DRAFTS_PER_PERSONA, ToolContext
from ..store import PackError
from .common import DEFAULT_AGENT_ID, POLICY_BLOCKED, ToolError, error_result, json_result, opt_str, text_result
from .fetch import GraphError, check_policy, split_url

PATHS: list[tuple[str, list[str]]] = [
    ("/me", ["fetch"]),
    ("/me/messages", ["fetch", "create"]),
    ("/me/messages/{message-id}", ["fetch", "update"]),
    ("/me/mailFolders/inbox/messages", ["fetch"]),
    ("/me/mailFolders/sentitems/messages", ["fetch"]),
    ("/me/mailFolders/drafts/messages", ["fetch"]),
    ("/me/messages/{message-id}/send", ["action"]),
    ("/me/sendMail", ["action"]),
    ("/me/events", ["fetch", "create"]),
    ("/me/events/{event-id}", ["fetch", "update"]),
    ("/me/calendarView", ["fetch", "function"]),
    ("/me/chats", ["fetch"]),
    ("/chats/{chat-id}", ["fetch"]),
    ("/chats/{chat-id}/messages", ["fetch", "create"]),
    ("/chats/{chat-id}/messages/{chatMessage-id}", ["fetch"]),
    ("/me/drive", ["fetch"]),
    ("/me/drive/root/children", ["fetch"]),
    ("/me/drive/recent", ["fetch"]),
    ("/me/drive/sharedWithMe", ["fetch"]),
    ("/me/drive/root/search(q='{q}')", ["fetch", "function"]),
    ("/me/drive/items/{driveItem-id}", ["fetch"]),
    ("/me/drive/items/{driveItem-id}/content", ["fetch"]),
    ("/drives/{drive-id}/root/children", ["fetch"]),
    ("/drives/{drive-id}/items/{driveItem-id}", ["fetch"]),
    ("/drives/{drive-id}/items/{driveItem-id}/content", ["fetch"]),
    ("/sites/{site-id}", ["fetch"]),
    ("/sites/{site-id}/drive/root/children", ["fetch"]),
    ("/me/people", ["fetch"]),
    ("/me/people/{person-id}", ["fetch"]),
    ("/users", ["fetch"]),
    ("/users/{user-id}", ["fetch"]),
]

_STR = {"type": ["string", "null"]}
_DT = {"type": ["string", "null"], "format": "date-time"}
_ADDR = {"type": "object", "properties": {"emailAddress": {"type": "object", "properties": {"name": _STR, "address": _STR}}}}
_DTTZ = {"type": "object", "properties": {"dateTime": _STR, "timeZone": _STR}}
_BODY = {"type": "object", "properties": {"contentType": {"enum": ["text", "html"]}, "content": _STR}}
SCHEMAS = {
    "message": {
        "type": "object",
        "properties": {
            "id": _STR, "subject": _STR, "bodyPreview": _STR, "body": _BODY, "from": _ADDR, "sender": _ADDR,
            "toRecipients": {"type": "array", "items": _ADDR}, "ccRecipients": {"type": "array", "items": _ADDR},
            "bccRecipients": {"type": "array", "items": _ADDR}, "receivedDateTime": _DT, "sentDateTime": _DT,
            "conversationId": _STR, "isRead": {"type": "boolean"}, "isDraft": {"type": "boolean"},
            "importance": {"enum": ["low", "normal", "high"]}, "parentFolderId": _STR, "webLink": _STR,
        },
    },
    "event": {
        "type": "object",
        "properties": {
            "id": _STR, "subject": _STR, "bodyPreview": _STR, "body": _BODY, "start": _DTTZ, "end": _DTTZ,
            "location": {"type": "object", "properties": {"displayName": _STR}}, "organizer": _ADDR,
            "attendees": {"type": "array", "items": {"type": "object", "properties": {"type": _STR, "emailAddress": _ADDR["properties"]["emailAddress"]}}},
            "isOnlineMeeting": {"type": "boolean"}, "onlineMeeting": {"type": ["object", "null"], "properties": {"joinUrl": _STR}},
            "isAllDay": {"type": "boolean"}, "webLink": _STR,
        },
    },
    "chat": {"type": "object", "properties": {"id": _STR, "topic": _STR, "chatType": {"enum": ["oneOnOne", "group", "meeting"]}, "createdDateTime": _DT, "lastUpdatedDateTime": _DT, "webUrl": _STR}},
    "chatMessage": {
        "type": "object",
        "properties": {
            "id": _STR, "chatId": _STR, "createdDateTime": _DT, "messageType": _STR, "body": _BODY,
            "from": {"type": "object", "properties": {"user": {"type": "object", "properties": {"id": _STR, "displayName": _STR}}}},
        },
    },
    "driveItem": {
        "type": "object",
        "properties": {
            "id": _STR, "name": _STR, "webUrl": _STR, "size": {"type": "integer"}, "createdDateTime": _DT, "lastModifiedDateTime": _DT,
            "createdBy": {"type": "object"}, "parentReference": {"type": "object", "properties": {"driveId": _STR, "siteId": _STR}},
            "file": {"type": "object", "properties": {"mimeType": _STR}},
        },
    },
    "person": {"type": "object", "properties": {"id": _STR, "displayName": _STR, "jobTitle": _STR, "companyName": _STR, "scoredEmailAddresses": {"type": "array"}}},
    "user": {"type": "object", "properties": {"id": _STR, "displayName": _STR, "mail": _STR, "userPrincipalName": _STR, "jobTitle": _STR, "department": _STR}},
}
SCHEMA_RULES = [
    (r"^/me/(mailFolders/[^/]+/)?messages(/\{?[^/]+\}?)?$", "message"),
    (r"^/me/(events|calendarView|calendar/events)(/[^/]+)?$", "event"),
    (r"^/(me/)?chats(/[^/]+)?$", "chat"),
    (r"^/(me/)?chats/[^/]+/messages(/[^/]+)?$", "chatMessage"),
    (r"^/(me/drive|drives/[^/]+|sites/[^/]+/drive)/(root/children|items/[^/]+|recent|sharedWithMe)$", "driveItem"),
    (r"^/me/people(/[^/]+)?$", "person"),
    (r"^/(me|users(/[^/]+)?)$", "user"),
]
OPERATION_IDS = {
    "me.ListMessages": "/me/messages", "me.CreateMessages": "/me/messages", "me.GetMessages": "/me/messages/{message-id}",
    "me.ListEvents": "/me/events", "me.ListCalendarView": "/me/calendarView", "me.ListChats": "/me/chats",
    "chats.ListMessages": "/chats/{chat-id}/messages", "me.drive.root.ListChildren": "/me/drive/root/children",
    "me.ListPeople": "/me/people", "users.GetUser": "/users/{user-id}",
}
_COLLECTION_RE = re.compile(r"(messages|events|calendarView|chats|children|recent|sharedWithMe|people|users)$", re.I)


def tool_search_paths(ctx: ToolContext, args: dict) -> dict:
    # The documented parameter is 'filter'; some clients send 'query'.
    flt = opt_str(args, "filter", 100) or opt_str(args, "query", 100)
    if not flt:
        raise ToolError("Invalid input: 'filter' is required.")
    if re.search(r"[\\^$.*+?()\[\]{}|]", flt):
        try:
            rx = re.compile(flt, re.I)
        except re.error:
            raise ToolError("Invalid input: 'filter' is not a valid regular expression.") from None
        match = lambda p: bool(rx.search(p))  # noqa: E731
    else:
        needle = flt.lower().strip()
        match = lambda p: needle in p.lower()  # noqa: E731
    paths = [{"path": p, "operations": ops} for p, ops in PATHS if match(p)]
    return json_result({"paths": paths})


def _schema_for(path: str) -> tuple[str, dict]:
    for rule, name in SCHEMA_RULES:
        if re.match(rule, path, re.I):
            return name, SCHEMAS[name]
    raise ToolError(f"No schema is available in the emulator for path '{path}'. Call search_paths to list supported paths.")


def _ts_type(schema: dict) -> str:
    if "enum" in schema:
        return " | ".join(json.dumps(v) for v in schema["enum"])
    t = schema.get("type")
    types = t if isinstance(t, list) else [t]
    base = types[0]
    if base == "object" and "properties" in schema:
        inner = "; ".join(f"{k}?: {_ts_type(v)}" for k, v in schema["properties"].items())
        out = "{ " + inner + " }"
    elif base == "array":
        out = _ts_type(schema.get("items", {"type": "object"})) + "[]"
    else:
        out = {"string": "string", "integer": "number", "number": "number", "boolean": "boolean", "object": "Record<string, unknown>"}.get(base, "unknown")
    return out + (" | null" if "null" in types else "")


def tool_get_schema(ctx: ToolContext, args: dict) -> dict:
    op = opt_str(args, "operationType", 20)
    if op not in ("fetch", "create", "update"):
        raise ToolError("Invalid input: 'operationType' is required and must be fetch, create or update.")
    path = opt_str(args, "path", 300)
    op_ids = opt_str(args, "operationIds", 200)
    if bool(path) == bool(op_ids):
        raise ToolError("Invalid input: use either 'path' or 'operationIds', but not both.")
    if op_ids:
        path = OPERATION_IDS.get(op_ids.split(",")[0].strip())
        if not path:
            raise ToolError(f"Unknown operation id '{op_ids}'.")
    fmt = opt_str(args, "format", 20) or "jsonschema"
    if fmt not in ("jsonschema", "typescript"):
        raise ToolError("Invalid input: 'format' must be jsonschema or typescript.")
    path = path.split("?", 1)[0].rstrip("/")
    name, item_schema = _schema_for(path)
    collection = op == "fetch" and bool(_COLLECTION_RE.search(path))
    title = f"microsoft.graph.{name}" + ("CollectionResponse" if collection else "")
    if fmt == "typescript":
        if collection:
            text = f"// {title}\ninterface {name[0].upper() + name[1:]}CollectionResponse {{ value: {_ts_type(item_schema)}[] }}"
        else:
            text = f"// {title}\ninterface {name[0].upper() + name[1:]} {_ts_type(item_schema).replace(' | null', '')}"
        return text_result(text)
    schema: dict = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title}
    if collection:
        schema |= {"type": "object", "properties": {"value": {"type": "array", "items": {"$ref": f"#/$defs/microsoft.graph.{name}"}}}}
    else:
        schema |= {"$ref": f"#/$defs/microsoft.graph.{name}"}
    schema["$defs"] = {f"microsoft.graph.{name}": item_schema}
    return text_result(json.dumps(schema, indent=2))


def tool_list_agents(ctx: ToolContext, args: dict) -> dict:
    return text_result(json.dumps([{"agentId": DEFAULT_AGENT_ID, "name": "Microsoft Copilot", "provider": "Microsoft"}]))


def _policy_denied(path_arg: str | None, tool: str) -> dict:
    return error_result(f"{POLICY_BLOCKED} Tool '{tool}' was not run.", {"statusCode": 403})


def _check_path(raw: str | None, name: str) -> str:
    if not raw:
        raise ToolError(f"Invalid input: '{name}' is required.")
    try:
        path, _ = split_url(raw)
        check_policy(path)
    except GraphError as err:
        raise ToolError(f"{err.status} {err.code}: {err.message}") from None
    return path


def _json_body(args: dict, required: bool = True) -> dict:
    raw = args.get("jsonBody")
    if raw is None or raw == "":
        if required:
            raise ToolError("Invalid input: 'jsonBody' is required and must be a JSON-encoded string.")
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or len(raw) > 64 * 1024:
        raise ToolError("Invalid input: 'jsonBody' must be a JSON-encoded string of at most 64 KB.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        raise ToolError("Invalid input: 'jsonBody' is not valid JSON.") from None
    if not isinstance(value, dict):
        raise ToolError("Invalid input: 'jsonBody' must encode a JSON object.")
    return value


def tool_create_entity(ctx: ToolContext, args: dict) -> dict:
    path = _check_path(opt_str(args, "parentUrl", 2048), "parentUrl")
    body = _json_body(args)
    if not ctx.state.settings.allow_mutations:
        return _policy_denied(path, "create_entity")
    if path.lower() != "/me/messages":
        return error_result(f"{POLICY_BLOCKED} Only draft messages under /me/messages can be created when WORKIQ_ALLOW_MUTATIONS is true.", {"statusCode": 403})
    return _create_draft(ctx, body)


def _addr_list(value, where: str) -> list[dict]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 20:
        raise ToolError(f"Invalid input: '{where}' must be a list of recipients.")
    out = []
    for r in value:
        ea = r.get("emailAddress") if isinstance(r, dict) else None
        if not isinstance(ea, dict) or not isinstance(ea.get("address"), str):
            raise ToolError(f"Invalid input: each entry in '{where}' needs emailAddress.address.")
        out.append({"name": str(ea.get("name") or ""), "address": ea["address"]})
    return out


def _create_draft(ctx: ToolContext, body: dict) -> dict:
    pid = ctx.persona.id
    if ctx.state.count_drafts(pid) >= MAX_DRAFTS_PER_PERSONA:
        return error_result(f"Draft limit of {MAX_DRAFTS_PER_PERSONA} reached for this persona.", {"statusCode": 429})
    content = body.get("body", {})
    text = content.get("content", "") if isinstance(content, dict) else str(content)
    now = datetime.now(ctx.store.now.tzinfo).replace(microsecond=0)
    item_id = "draft-" + now.strftime("%Y%m%d%H%M%S") + "-" + str(len(ctx.store.entries))
    item = {
        "id": item_id,
        "type": "email",
        "date": now.isoformat(),
        "visibleTo": [pid],
        "subject": str(body.get("subject") or "(no subject)")[:300],
        "from": {"name": ctx.persona.display_name, "address": ctx.persona.mail},
        "to": _addr_list(body.get("toRecipients"), "toRecipients"),
        "cc": _addr_list(body.get("ccRecipients"), "ccRecipients"),
        "body": str(text)[:20000],
        "folder": "drafts",
        "isDraft": True,
        "isRead": True,
        "note": "Draft created through create_entity.",
    }
    try:
        store = ctx.state.append_item(item)
    except PackError as err:
        raise ToolError(f"Invalid draft: {err}") from None
    e = store.by_item_id[item_id]
    data = graph.message(store, e, pid, ctx.base_url)
    out = json_result({"statusCode": 201, "data": data})
    out["_resultIds"] = [e.gid]
    return out


def tool_update_entity(ctx: ToolContext, args: dict) -> dict:
    path = _check_path(opt_str(args, "entityUrl", 2048), "entityUrl")
    _json_body(args)
    return _policy_denied(path, "update_entity")


def tool_delete_entity(ctx: ToolContext, args: dict) -> dict:
    path = _check_path(opt_str(args, "entityUrl", 2048), "entityUrl")
    return _policy_denied(path, "delete_entity")


def tool_do_action(ctx: ToolContext, args: dict) -> dict:
    path = _check_path(opt_str(args, "actionUrl", 2048), "actionUrl")
    _json_body(args, required=False)
    return _policy_denied(path, "do_action")

