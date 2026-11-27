"""Tool registry: names, descriptions, input schemas and handlers, following the Work IQ MCP tool reference."""

from __future__ import annotations

from typing import Callable

from ..state import ToolContext
from .ask import tool_ask
from .fetch import tool_call_function, tool_fetch, tool_fetch_blob
from .other import (
    tool_create_entity,
    tool_delete_entity,
    tool_do_action,
    tool_get_schema,
    tool_list_agents,
    tool_search_paths,
    tool_update_entity,
)
from .retrieve import tool_retrieve

_AGENT = {"type": "string", "description": "Reserved for future use."}
_JSON_BODY = {"type": "string", "description": "The entity data, matching the resource schema. This property must be a JSON-encoded string, not a JSON object."}
_RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def _schema(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


TOOLS: list[dict] = [
    {
        "name": "fetch",
        "title": "Fetch entities",
        "description": "Reads one or more entities by resource path. Supports fetching multiple paths in parallel. Collections default to $top 25 (maximum 100), chat messages are capped at 10, and $skip and $skiptoken are blocked.",
        "inputSchema": _schema(
            {
                "entityUrls": {"type": "array", "items": {"type": "string"}, "description": "The relative resource paths to fetch (for example, /me/messages, /me/events/{event-id})."},
                "query": {"type": "string", "description": "Natural-language intent for untrusted-content sanitization."},
                "agentId": _AGENT,
            },
            ["entityUrls"],
        ),
        "annotations": _RO,
    },
    {
        "name": "fetch_blob",
        "title": "Fetch binary content",
        "description": "Fetches binary content, such as documents, images, and Office files from a relative Work IQ path. The content is returned as a Base64-encoded string with metadata in structuredContent.",
        "inputSchema": _schema(
            {
                "path": {"type": "string", "description": "The relative path to the binary content (for example, /drives/{drive-id}/items/{item-id}/content)."},
                "format": {"type": "string", "description": "File conversion format (for example, pdf). Supported only by drive-content endpoints that accept the Microsoft Graph $format parameter."},
                "agentId": _AGENT,
            },
            ["path"],
        ),
        "annotations": _RO,
    },
    {
        "name": "create_entity",
        "title": "Create entity",
        "description": "Creates a new entity in a collection. Mutation operations are blocked by tenant policy by default. In this lab one write is allowed: post a message into a Teams chat you are a member of with parentUrl /chats/{chat-id}/messages and jsonBody {\"body\": {\"content\": \"...\"}}. The message is shown as written by your agent on your behalf. Find chat ids with fetch /me/chats.",
        "inputSchema": _schema(
            {"parentUrl": {"type": "string", "description": "The relative resource path for the collection (for example, /me/events, /me/messages)."}, "jsonBody": _JSON_BODY, "agentId": _AGENT},
            ["parentUrl", "jsonBody"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "update_entity",
        "title": "Update entity",
        "description": "Updates an existing entity. Mutation operations are blocked by tenant policy by default.",
        "inputSchema": _schema(
            {"entityUrl": {"type": "string", "description": "The relative path to the entity (for example, /me/messages/{message-id})."}, "jsonBody": _JSON_BODY, "agentId": _AGENT},
            ["entityUrl", "jsonBody"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "delete_entity",
        "title": "Delete entity",
        "description": "Deletes an entity. Mutation operations are blocked by tenant policy by default.",
        "inputSchema": _schema(
            {
                "entityUrl": {"type": "string", "description": "The relative resource path to the entity to delete (for example, /me/messages/{id})."},
                "agentId": {"type": "string", "description": "The ID of a specific agent to route the question to. If omitted, defaults to the built-in Microsoft 365 Copilot agent."},
            },
            ["entityUrl"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "do_action",
        "title": "Run action",
        "description": "Runs a side-effect action such as sending mail, copying, or moving items, or a connector write operation. Blocked by tenant policy by default.",
        "inputSchema": _schema(
            {
                "actionUrl": {"type": "string", "description": "The relative path for the action (for example, /me/messages/{message-id}/send)."},
                "jsonBody": {"type": "string", "description": "The JSON body for the action, if required. This property must be a JSON-encoded string, not a JSON object."},
                "agentId": _AGENT,
            },
            ["actionUrl"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
    },
    {
        "name": "call_function",
        "title": "Call function",
        "description": "Calls a Microsoft Graph function to compute derived data such as schedules, deltas, or search results. In the emulator, read functions such as /me/calendarView and drive search succeed; others are blocked by policy.",
        "inputSchema": _schema(
            {
                "functionUrl": {"type": "string", "description": "The relative path for the function (for example, /me/calendarview)."},
                "jsonBody": {"anyOf": [{"type": "object"}, {"type": "string"}], "description": "The JSON body for the function, if required. Supply as a JSON object or JSON-encoded string."},
                "agentId": _AGENT,
            },
            ["functionUrl"],
        ),
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    {
        "name": "ask",
        "title": "Ask Microsoft 365 Copilot",
        "description": "Asks Microsoft 365 Copilot (or a specific agent) a natural-language question about your data. Returns a JSON string with 'response' and 'conversationId'.",
        "inputSchema": _schema(
            {
                "question": {"type": "string", "description": "The natural-language question to ask."},
                "agentId": {"type": "string", "description": "The ID of a specific agent to route the question to. If omitted, defaults to the built-in Microsoft 365 Copilot agent."},
                "fileUrls": {"type": "array", "items": {"type": "string"}, "description": "An array of OneDrive or SharePoint file URLs to use as context."},
                "conversationId": {"type": "string", "description": "A conversation ID from an existing conversation. If provided, this request continues the existing conversation."},
                "timeZone": {"type": "string", "description": "An IANA time zone identifier matching the user's current UTC offset. If omitted, times are returned in UTC."},
            },
            ["question"],
        ),
        "annotations": _RO | {"idempotentHint": False},
    },
    {
        "name": "retrieve",
        "title": "Retrieve grounding content",
        "description": "Searches Microsoft 365 data that the signed-in user can access. Returns model-friendly grounding Markdown and structured metadata for each source in structuredContent['application/vnd.ms-workiq.retrieval'].results. The grounding strategy is the default.",
        "inputSchema": _schema(
            {
                "query": {"type": "string", "description": "The natural-language query that describes what to search for."},
                "agentId": {"type": "string", "description": "The ID of an agent to use for retrieval. If you omit this parameter, retrieval uses the built-in Microsoft 365 Copilot agent. Don't combine a nondefault agent ID with a nonempty capabilities array."},
                "strategy": {"type": "string", "enum": ["grounding", "copilot"], "description": "The retrieval strategy. The default is grounding. Use copilot when you use the GraphConnectors capability."},
                "capabilities": {
                    "type": "array",
                    "description": "A source allow list for the request. Omit it or pass an empty array to search all sources.",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string", "enum": ["People", "Meetings", "OneDriveAndSharePoint", "Email", "TeamsMessages", "GraphConnectors", "Dataverse"]}},
                        "required": ["name"],
                        "additionalProperties": True,
                    },
                },
            },
            ["query"],
        ),
        "annotations": _RO,
    },
    {
        "name": "list_agents",
        "title": "List agents",
        "description": "Lists available agents that you can use with the ask tool. The built-in Microsoft 365 Copilot agent is always included.",
        "inputSchema": _schema({}, []),
        "annotations": _RO,
    },
    {
        "name": "get_schema",
        "title": "Get schema",
        "description": "Retrieves the schema for a specific operation, identified by path and operation type.",
        "inputSchema": _schema(
            {
                "operationIds": {"type": "string", "description": "The operation ID of the API to get the schema for (for example, me.CreateMessages). Use operationIds or path, but not both."},
                "path": {"type": "string", "description": "The API path to get the schema for (for example, /me/messages). Use operationIds or path, but not both."},
                "operationType": {"type": "string", "enum": ["fetch", "create", "update"], "description": "The operation type."},
                "format": {"type": "string", "enum": ["jsonschema", "typescript"], "description": "The desired output format. If omitted, JSON schema is returned."},
                "backend": {"type": "string", "description": "Reserved for future use."},
                "agentId": _AGENT,
            },
            ["operationType"],
        ),
        "annotations": _RO,
    },
    {
        "name": "search_paths",
        "title": "Search paths",
        "description": "Searches available API paths by prefix or regex filter. Use this tool to discover which resource paths are available before calling other tools.",
        "inputSchema": _schema(
            {
                "filter": {"type": "string", "description": "A prefix or regex pattern to search for matching API paths (for example, messages or .*calendar.*)."},
                "backend": {"type": "string", "description": "Reserved for future use."},
                "agentId": _AGENT,
            },
            ["filter"],
        ),
        "annotations": _RO,
    },
]

HANDLERS: dict[str, Callable[[ToolContext, dict], dict]] = {
    "fetch": tool_fetch,
    "fetch_blob": tool_fetch_blob,
    "create_entity": tool_create_entity,
    "update_entity": tool_update_entity,
    "delete_entity": tool_delete_entity,
    "do_action": tool_do_action,
    "call_function": tool_call_function,
    "ask": tool_ask,
    "retrieve": tool_retrieve,
    "list_agents": tool_list_agents,
    "get_schema": tool_get_schema,
    "search_paths": tool_search_paths,
}
