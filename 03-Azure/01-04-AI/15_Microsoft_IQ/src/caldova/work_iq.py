"""Work IQ: connect the agent to the Work IQ MCP server (the emulator in this lab).

The emulator speaks the same MCP contract as https://workiq.svc.cloud.microsoft/mcp. In a tenant with
Microsoft 365 Copilot, point WORKIQ_ENDPOINT at the real server and use an Entra user connection instead
of a key. Your agent code does not change."""

from __future__ import annotations

import json

import httpx

from .azure import arm, save_state
from .config import CONNECTIONS_API, PERSONAS, settings


def connection_name(persona: str) -> str:
    return f"caldova-workiq-{persona}"


def connect(persona: str) -> str:
    settings.require("workiq_endpoint", "subscription_id", "resource_group", "project_endpoint")
    if persona not in PERSONAS:
        raise SystemExit(f"Unknown persona {persona}. Use one of: {', '.join(PERSONAS)}")
    key = settings.workiq_key(persona)
    if not key:
        raise SystemExit(f"WORKIQ_KEY_{persona.upper().replace('-', '_')} is missing in src/.env")
    name = connection_name(persona)
    arm("PUT", f"{settings.project_arm_id}/connections/{name}?api-version={CONNECTIONS_API}", {"properties": {
        "category": "RemoteTool", "authType": "CustomKeys", "target": settings.workiq_endpoint,
        "credentials": {"keys": {"Authorization": f"Bearer {key}"}}, "isSharedToAll": True}})
    save_state(**{f"workiq_connection_{persona}": name})
    return name


def call(persona: str, tool: str, arguments: dict) -> dict:
    """Call a Work IQ MCP tool directly (no agent), the way any MCP client would."""
    settings.require("workiq_endpoint")
    headers = {"Authorization": f"Bearer {settings.workiq_key(persona)}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    with httpx.Client(timeout=120) as c:
        init = c.post(settings.workiq_endpoint, headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "caldova", "version": "1"}}})
        init.raise_for_status()
        if sid := init.headers.get("mcp-session-id"):
            headers["mcp-session-id"] = sid
        c.post(settings.workiq_endpoint, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
        r = c.post(settings.workiq_endpoint, headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": tool, "arguments": arguments}})
        r.raise_for_status()
        text = r.text
        if text.startswith("event:") or "data:" in text[:20]:
            text = next(line[5:].strip() for line in text.splitlines() if line.startswith("data:"))
        return json.loads(text)["result"]
