"""Smoke test the emulator with the official MCP Python client (streamable HTTP).

Usage:
  python scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --key <persona key>
  python scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --persona sales-lead   (WORKIQ_DEV_MODE only)

Requires the dev dependencies (requirements-dev.txt)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _attr(obj, *names):
    # mcp 1.x uses camelCase attributes, mcp 2.x uses snake_case.
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    raise AttributeError(names[0])


def _sc(result) -> dict:
    return _attr(result, "structured_content", "structuredContent")


def _title(meta: dict) -> str:
    facet = next(iter(meta.values()), {})
    return facet.get("title") or facet.get("subject") or facet.get("displayName") or ""


async def run(url: str, headers: dict[str, str], query: str) -> dict:
    async with httpx2.AsyncClient(headers=headers, timeout=60) as http:
        async with streamable_http_client(url, http_client=http, terminate_on_close=False) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = await session.list_tools()
                retrieve = await session.call_tool("retrieve", {"query": query})
                payload = _sc(retrieve)["application/vnd.ms-workiq.retrieval"]
                fetch = await session.call_tool("fetch", {"entityUrls": ["/me", "/me/messages?$top=3&$select=subject"]})
                ask = await session.call_tool("ask", {"question": query})
                return {
                    "server": _attr(init, 'server_info', 'serverInfo').name,
                    "protocolVersion": _attr(init, 'protocol_version', 'protocolVersion'),
                    "tools": sorted(t.name for t in tools.tools),
                    "retrieve": {
                        "resultCount": payload["resultCount"],
                        "titles": [_title(r["resourceMetadata"]) for r in payload["results"]],
                    },
                    "fetch.me": _sc(fetch)["results"][0]["data"]["displayName"],
                    "fetch.subjects": [m["subject"] for m in _sc(fetch)["results"][1]["data"]["value"]],
                    "ask": json.loads(ask.content[0].text)["response"][:300],
                }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--key", default=os.environ.get("WORKIQ_KEY"))
    ap.add_argument("--persona")
    ap.add_argument("--query", default="Can we ship the Brennmark PV-400 order by Friday? Teglbruk Esbjerg")
    args = ap.parse_args()
    headers = {"Authorization": f"Bearer {args.key}"} if args.key else {"X-WorkIQ-Persona": args.persona or "sales-lead"}
    print(json.dumps(asyncio.run(run(args.url, headers, args.query)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
