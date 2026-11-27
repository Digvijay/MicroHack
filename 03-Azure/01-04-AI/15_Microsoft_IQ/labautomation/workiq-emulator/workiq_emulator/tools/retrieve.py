"""The retrieve tool: BM25 search over the persona's visible items, shaped like Work IQ retrieval."""

from __future__ import annotations

from urllib.parse import quote

from .. import graph, ranking
from ..state import ToolContext
from ..store import PERSONA_DOC_PREFIX, Entry, Persona, is_transcript, iso_utc, transcript_lines
from .common import DEFAULT_AGENT_ID, MAX_QUERY_CHARS, UNTRUSTED, ToolError, check_agent, json_result, opt_str, req_str

RETRIEVAL_KEY = "application/vnd.ms-workiq.retrieval"
TOP = 10
SNIPPET_CHARS = 2500
CAPABILITY_KINDS = {
    "Email": {"email"},
    "TeamsMessages": {"chat"},
    "Meetings": {"event", "transcript"},
    "OneDriveAndSharePoint": {"file", "transcript"},
    "People": {"person"},
    "GraphConnectors": set(),
}
ALL_KINDS = {"email", "chat", "event", "transcript", "file", "person"}


def kind_of(e: Entry) -> str:
    return "transcript" if e.kind == "file" and is_transcript(e.item) else e.kind


def parse_capabilities(args: dict, strategy: str) -> set[str] | None:
    caps = args.get("capabilities")
    if caps is None or caps == []:
        return None
    if not isinstance(caps, list) or len(caps) > 10:
        raise ToolError("Invalid input: 'capabilities' must be an array of objects with a 'name'.")
    kinds: set[str] = set()
    for cap in caps:
        if not isinstance(cap, dict) or not isinstance(cap.get("name"), str):
            raise ToolError("Invalid input: each capability must be an object with a 'name'.")
        name = cap["name"]
        if name == "Dataverse":
            raise ToolError("The Dataverse capability isn't currently a supported retrieval source.")
        if name not in CAPABILITY_KINDS:
            raise ToolError(f"Unsupported capability '{name}'. Supported: {', '.join(CAPABILITY_KINDS)}.")
        if name == "GraphConnectors" and strategy == "grounding":
            raise ToolError("The GraphConnectors capability isn't supported with the grounding strategy. Use strategy 'copilot'.")
        kinds |= CAPABILITY_KINDS[name]
    return kinds


def search(ctx: ToolContext, query: str, kinds: set[str] | None = None, top: int = TOP) -> list[tuple[Entry | Persona, float]]:
    """Ranked hits, only from items the calling persona can see."""
    kinds = ALL_KINDS if kinds is None else kinds
    store = ctx.store
    allowed = {e.id for e in store.visible(ctx.persona.id) if kind_of(e) in kinds}
    if "person" in kinds:
        allowed |= {PERSONA_DOC_PREFIX + pid for pid in store.personas}
    hits: list[tuple[Entry | Persona, float]] = []
    for doc_id, score in store.index.search(query, allowed, top):
        if doc_id.startswith(PERSONA_DOC_PREFIX):
            hits.append((store.personas[doc_id[len(PERSONA_DOC_PREFIX):]], score))
        else:
            hits.append((store.by_item_id[doc_id], score))
    return hits


def _flat(text: str) -> str:
    return " ".join(text.split())


def _local(dt) -> str:
    return dt.isoformat()


def _addr(a: dict) -> str:
    name = a.get("name") or ""
    return f"{name} <{a['address']}>" if name else a["address"]


def _best_units(units: list[str], q_tokens: set[str], limit: int = SNIPPET_CHARS) -> list[str]:
    """Pick the units that mention query terms, plus one neighbour on each side, in document order."""
    if sum(len(u) for u in units) <= limit:
        return units
    hit_idx = [i for i, u in enumerate(units) if q_tokens & set(ranking.tokenize(u))]
    keep: set[int] = set()
    for i in hit_idx:
        keep |= {i - 1, i, i + 1}
    chosen = [units[i] for i in sorted(k for k in keep if 0 <= k < len(units))] or units
    out, total = [], 0
    for u in chosen:
        if total + len(u) > limit:
            break
        out.append(u)
        total += len(u)
    return out or [units[0][:limit]]


def _chat_best_message(e: Entry, q_tokens: set[str]) -> dict:
    best, best_score = e.extra["messages"][0], -1
    for m in e.extra["messages"]:
        s = len(q_tokens & set(ranking.tokenize(m["text"])))
        if s > best_score:
            best, best_score = m, s
    return best


def build_result(ctx: ToolContext, hit: Entry | Persona, n: int, score: float, max_score: float, q_tokens: set[str]) -> dict:
    store, base = ctx.store, ctx.base_url
    lines: list[str]
    result: dict
    if isinstance(hit, Persona):
        lines = [f"- **{hit.display_name}**", f"  - **job title:** {hit.job_title}", f"  - **company:** {store.tenant['name']}", f"  - **email:** {hit.mail}"]
        result = {
            "resourceId": hit.user_id,
            "webUrl": f"{base}/viewer/people",
            "entityUrl": f"/users/{hit.user_id}",
            "entityType": "Person",
            "resourceMetadata": {"person": {"displayName": hit.display_name, "jobTitle": hit.job_title, "companyName": store.tenant["name"]}},
        }
    else:
        e, it = hit, hit.item
        if e.kind == "email":
            lines = [f"- **{it['subject']}**", f"  - **from:** {_addr(it['from'])}", "  - **to:** " + "; ".join(_addr(a) for a in it["to"])]
            if it.get("cc"):
                lines.append("  - **cc:** " + "; ".join(_addr(a) for a in it["cc"]))
            lines += [f"  - **sent:** {_local(e.dt)}", f"  - **snippet:** {_flat(it['body'])[:SNIPPET_CHARS]}"]
            result = {
                "resourceId": e.gid,
                "webUrl": graph.viewer_url(base, "email", e.gid),
                "entityUrl": f"/me/messages/{e.gid}",
                "entityType": "Message",
                "resourceMetadata": {"message": {"subject": it["subject"], "from": it["from"].get("name", ""), "receivedDateTime": iso_utc(e.dt)}},
            }
        elif e.kind == "chat":
            title = store.chat_title(e)
            best = _chat_best_message(e, q_tokens)
            msgs = e.extra["messages"]
            idx = msgs.index(best)
            window = msgs[max(0, idx - 4): idx + 6]
            lines = [f"- **{title}**", "  - **snippet:**"] + [
                f"    - {store.sender_label(m)} ({_local(m['dt'])}): {_flat(m['text'])}" for m in window
            ]
            result = {
                "resourceId": f"{e.gid}/{best['id']}",
                "webUrl": graph.viewer_url(base, "chat", e.gid),
                "entityUrl": f"/chats/{quote(e.gid, safe='')}/messages/{best['id']}",
                "entityType": "Chats",
                "chatId": e.gid,
                "messageId": best["id"],
                "resourceMetadata": {"chat": {"title": title}},
            }
        elif e.kind == "event":
            lines = [
                f"- **{it['subject']}**",
                f"  - **when:** {_local(e.dt)} to {_local(e.extra['end'])}",
                f"  - **organizer:** {_addr(it['organizer'])}",
                "  - **attendees:** " + "; ".join(_addr(a) for a in it["attendees"]),
            ]
            if it.get("location"):
                lines.append(f"  - **location:** {it['location']}")
            if it.get("body"):
                lines.append(f"  - **snippet:** {_flat(it['body'])[:SNIPPET_CHARS]}")
            tref = it.get("transcriptFile")
            if tref and ctx.persona.id in store.by_item_id[tref].visible:
                te = store.by_item_id[tref]
                lines.append(f"  - **transcript:** {te.item['name']} (/drives/{te.extra['driveId']}/items/{te.gid})")
            result = {
                "resourceId": e.gid,
                "webUrl": graph.viewer_url(base, "event", e.gid),
                "entityUrl": f"/me/events/{e.gid}",
                "entityType": "Event",
                "resourceMetadata": {"meeting": {"title": it["subject"], "occurrenceTime": iso_utc(e.dt), "organizerName": it["organizer"].get("name", "")}},
            }
        elif e.kind == "file":
            if is_transcript(it):
                units = [f"{s}: {t}" if s else t for s, t in transcript_lines(it["content"])]
                snippet = "\n".join(f"    - {u}" for u in _best_units(units, q_tokens))
            else:
                units = [_flat(p) for p in it["content"].split("\n\n") if p.strip()]
                snippet = "\n".join(f"    - {u}" for u in _best_units(units, q_tokens))
            lines = [
                f"- **{it['name']}**",
                f"  - **location:** {store.drive_owner_label(e)}",
                f"  - **author:** {it['createdBy'].get('name') or it['createdBy']['address']}",
                f"  - **modified:** {_local(e.dt)}",
                "  - **snippet:**",
                snippet,
            ]
            meta: dict = {"document": {"title": it["name"], "authorName": it["createdBy"].get("name", ""), "occurrenceTime": iso_utc(e.dt)}}
            rel = it.get("relatedEvent")
            if rel and rel in store.by_item_id:
                ev = store.by_item_id[rel]
                meta["meeting"] = {"title": ev.item["subject"], "occurrenceTime": iso_utc(ev.dt)}
            result = {
                "resourceId": e.gid,
                "webUrl": graph.viewer_url(base, "file", e.gid),
                "entityUrl": f"/drives/{e.extra['driveId']}/items/{e.gid}",
                "entityType": "DriveItem",
                "driveId": e.extra["driveId"],
                "itemId": e.gid,
                "resourceMetadata": meta,
            }
        else:
            lines = [f"- **{it['displayName']}**", f"  - **job title:** {it['jobTitle']}", f"  - **company:** {it['companyName']}", f"  - **email:** {it['mail']}"]
            result = {
                "resourceId": e.gid,
                "webUrl": graph.viewer_url(base, "person", e.gid),
                "entityUrl": f"/me/people/{e.gid}",
                "entityType": "Person",
                "resourceMetadata": {"person": {"displayName": it["displayName"], "jobTitle": it["jobTitle"], "companyName": it["companyName"]}},
            }
    markdown = UNTRUSTED + "\n\n" + "\n".join(lines)
    ordered = {"markdown": markdown, "id": f"h{n}", **result, "contentProtection": "allowed"}
    ordered["relevanceScore"] = round(score / max_score, 3) if max_score else 0.0
    return ordered


def run_retrieve(ctx: ToolContext, query: str, kinds: set[str] | None, top: int = TOP) -> dict:
    hits = search(ctx, query, kinds, top)
    q_tokens = set(ranking.tokenize(query))
    max_score = max((s for _, s in hits), default=0.0)
    results = [build_result(ctx, h, i + 1, s, max_score, q_tokens) for i, (h, s) in enumerate(hits)]
    return {
        RETRIEVAL_KEY: {
            "results": results,
            "resultCount": len(results),
            "searchMetadata": {"searchTerms": ranking.search_terms(query)},
            "stoppedReason": "completed",
        },
        "@workiq.untrustedContent": UNTRUSTED,
    }


def tool_retrieve(ctx: ToolContext, args: dict) -> dict:
    query = req_str(args, "query", MAX_QUERY_CHARS)
    strategy = opt_str(args, "strategy", 20) or "grounding"
    if strategy not in ("grounding", "copilot"):
        raise ToolError("Invalid input: 'strategy' must be 'grounding' or 'copilot'.")
    agent = opt_str(args, "agentId", 200)
    if agent and agent != DEFAULT_AGENT_ID and args.get("capabilities"):
        raise ToolError("Don't combine a nondefault agentId with a nonempty capabilities array.")
    check_agent(args)
    opt_str(args, "timeZone", 64)
    kinds = parse_capabilities(args, strategy)
    structured = run_retrieve(ctx, query, kinds)
    out = json_result(structured)
    out["_resultIds"] = [r["resourceId"] for r in structured[RETRIEVAL_KEY]["results"]]
    return out
