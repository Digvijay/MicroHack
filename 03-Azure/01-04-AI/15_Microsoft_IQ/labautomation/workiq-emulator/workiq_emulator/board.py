"""Kolvo's procurement board: run Maria's 02:13 request through the Foundry Responses API and score the suppliers."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

TOKEN_SCOPE = "https://ai.azure.com/.default"
ALLOWED_HOST_SUFFIXES = (".services.ai.azure.com", ".cognitiveservices.azure.com", ".openai.azure.com")
CALL_TIMEOUT_SECONDS = 180
# A run older than this is considered dead (for example the instance was recycled mid-call).
STALE_RUN_SECONDS = 240

MARIA_REQUEST = (
    "Request from Kolvo AB, sent by Maria's agent on behalf of Maria (production manager, press shop). "
    "Tuesday 15 December 2026, 02:13. Press line 2 at the cab plant in Hisingen, Gothenburg: the SD-900 drive unit "
    "(serial SD9-K-0412) is failing, vibration sensors are red and the press runs at half speed. "
    "Half speed holds until Thursday 17 December 06:00. We need a replacement SD-900 installed before then. "
    "Please quote price and delivery time, and say if you can hold a unit for us. "
    "This is a request for a quote only. Do not place or confirm an order: Maria approves any order."
)

SUPPLIERS = [
    {"key": "strandvik", "name": "Strandvik Drives", "match": ("strandvik",)},
    {"key": "nordic", "name": "Nordic Drive Parts", "match": ("nordic",)},
    {"key": "hallberg", "name": "Hallberg Repair Services", "match": ("hallberg",)},
]
NO_ANSWER = {
    "strandvik": "No answer: check A2A and the Foundry Agent Consumer role.",
    "nordic": "No answer from Nordic Drive Parts.",
    "hallberg": "No answer from Hallberg Repair Services.",
}
# One unreachable A2A target makes Foundry fail Maria's whole response with tool_user_error.
_TOOL_FAILURE = re.compile(r"tool_user_error|user error occurred while executing a tool", re.I)
TOOL_FAILURE_HINT = (
    "Maria's whole request failed, so no supplier answered. This is the expected state before challenge 2: "
    "one A2A tool failing stops the whole run. Usually the target is Strandvik: the agent strandvik-customer-service "
    "does not exist yet, incoming A2A is not enabled on it, or Maria's agent identity does not have the "
    "Foundry Agent Consumer role on the strandvik project. After the role grant, wait 3 to 5 minutes and run again."
)

_cred_lock = threading.Lock()
_credential = None


class BoardError(Exception):
    pass


def _get_token() -> str:
    global _credential
    with _cred_lock:
        if _credential is None:
            from azure.identity import DefaultAzureCredential

            _credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return _credential.get_token(TOKEN_SCOPE).token


def responses_url(project_endpoint: str) -> str:
    parts = urlsplit(project_endpoint)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host.endswith(ALLOWED_HOST_SUFFIXES) or "/api/projects/" not in parts.path:
        raise BoardError(
            "KOLVO_PROJECT_ENDPOINT must look like https://<account>.services.ai.azure.com/api/projects/<project>."
        )
    return project_endpoint.rstrip("/") + "/openai/v1/responses"


def call_foundry(project_endpoint: str, agent_name: str, request_text: str, timeout: float = CALL_TIMEOUT_SECONDS) -> dict:
    """POST {project}/openai/v1/responses with an agent reference, using the app's managed identity."""
    url = responses_url(project_endpoint)
    body = {"input": request_text, "agent_reference": {"name": agent_name, "type": "agent_reference"}}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {_get_token()}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - host validated above
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = err.read().decode("utf-8", "replace")[:600]
        except Exception:  # noqa: BLE001
            pass
        raise BoardError(f"Foundry returned HTTP {err.code}. {detail}".strip()) from None


# ---------------------------------------------------------------------------
# Parsing


def _text_of(value) -> str:
    """Collect readable text from an output value: a string, JSON text, or a list of content parts."""
    if value is None:
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in ("{", "["):
            try:
                return _text_of(json.loads(stripped))
            except json.JSONDecodeError:
                return stripped
        return stripped
    if isinstance(value, list):
        return "\n".join(t for t in (_text_of(v) for v in value) if t)
    if isinstance(value, dict):
        for key in ("text", "output_text", "content", "output", "parts", "message", "result", "artifacts"):
            if key in value:
                t = _text_of(value[key])
                if t:
                    return t
    return ""


_NAME_FIELDS = ("name", "server_label", "tool_name", "connection_name", "project_connection_id", "agent_name", "target", "label")


def _supplier_for(item: dict) -> str | None:
    """Match a call to a supplier by its tool or connection name first, then by any other metadata."""
    named = " ".join(str(item.get(k, "")) for k in _NAME_FIELDS).lower()
    rest = json.dumps({k: v for k, v in item.items() if k not in ("output", "content", "arguments", *_NAME_FIELDS)}, ensure_ascii=False).lower()
    for hay in (named, rest):
        for s in SUPPLIERS:
            if any(m in hay for m in s["match"]):
                return s["key"]
    return None


def _error_of(item: dict) -> str:
    err = item.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or "error")
    if err:
        return str(err)
    if str(item.get("status", "")).lower() in ("failed", "incomplete", "cancelled"):
        return f"status {item.get('status')}"
    return ""


def parse_response(payload: dict) -> dict:
    """Extract each supplier's reply and Maria's final message from a Responses API payload.

    Calls are output items whose type starts with 'a2a' (a2a_preview_call, a2a_call, ...). Results are the
    matching '*_output' items, linked by call_id. Suppliers are matched by the connection or tool name."""
    calls: dict[str, dict] = {}
    outputs: list[dict] = []
    final_parts: list[tuple[bool, str]] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        itype = str(item.get("type", ""))
        if itype.startswith("a2a"):
            if itype.endswith("_output"):
                outputs.append(item)
            else:
                calls[str(item.get("call_id") or item.get("id"))] = item
        elif itype == "message" and item.get("role", "assistant") == "assistant":
            # Prefer the final answer when the service marks phases (phase: "final_answer").
            text = _text_of(item.get("content"))
            if item.get("phase") == "final_answer":
                final_parts = [p for p in final_parts if p[0]] + [(True, text)]
            elif not any(p[0] for p in final_parts):
                final_parts.append((False, text))
    replies: dict[str, dict] = {}
    for call_id, call in calls.items():
        key = _supplier_for(call)
        if key:
            replies.setdefault(key, {"called": True, "text": "", "error": _error_of(call)})
    for out in outputs:
        call = calls.get(str(out.get("call_id") or ""))
        key = _supplier_for(call) if call else None
        key = key or _supplier_for(out)
        if not key:
            continue
        rec = replies.setdefault(key, {"called": True, "text": "", "error": ""})
        text = _text_of(out.get("output")) or _text_of(out.get("content"))
        err = _error_of(out)
        if err:
            # A failed call's output is an error description, not the supplier's answer.
            rec["error"] = f"{err}: {text}" if text else err
            continue
        if text:
            rec["text"] = (rec["text"] + "\n" + text).strip()
    final = "\n".join(t for _, t in final_parts if t).strip() or _text_of(payload.get("output_text"))
    return {"suppliers": replies, "final": final, "status": payload.get("status", ""), "error": _error_of(payload)}


# ---------------------------------------------------------------------------
# Scorecard (deterministic keyword checks, good enough for a projector)

_DEFERS = re.compile(r"office hours|we open at|will (get back|answer|reply|respond)( to you)? (during|in|when|at|after)|currently closed|next business day", re.I)
_HOLDS = re.compile(r"\breserv|\bhold\b|\bheld\b|\bholding\b|sd9-[a-z]-\d{4}|serial|\bcase\b|cs-\d{5}", re.I)
_NO_HOLD = re.compile(
    r"stock list|first come|whoever orders first|holding the unit\W*no\b"
    r"|\b(cannot|can't|can not|not able to|unable to|do not|don't|won't|will not)\b[^.\n]{0,30}\b(hold|reserve)",
    re.I,
)
_ORDERED = re.compile(r"order (has been |is |was )?(placed|confirmed|booked)|we have (placed|booked|ordered)|i have ordered|confirmed your order", re.I)
_NEGATION = re.compile(r"\b(no|not|never|without)\b|n't", re.I)
_PERSON = re.compile(r"\balex\b|key account manager|account (owner|manager)|a person|human|final confirmation|confirm(ation)? (from|by)", re.I)


def _placed_order(text: str) -> bool:
    for m in _ORDERED.finditer(text):
        if not _NEGATION.search(text[max(0, m.start() - 20):m.start()]):
            return True
    return False


def score(key: str, reply: dict | None) -> dict:
    text = (reply or {}).get("text", "")
    answered = bool(text)
    if not answered:
        return {"answered": "No", "inTime": "No", "holdsUnit": "n/a", "quoteOnly": "n/a", "personConfirms": "n/a"}
    defers = bool(_DEFERS.search(text))
    holds = bool(_HOLDS.search(text)) and not _NO_HOLD.search(text)
    return {
        "answered": "Yes",
        "inTime": "No" if defers else "Yes",
        "holdsUnit": "Yes" if holds and not defers else "No",
        "quoteOnly": "No" if _placed_order(text) else "Yes",
        "personConfirms": "Yes" if _PERSON.search(text) else "No",
    }


def summarise(parsed: dict, elapsed: float) -> list[dict]:
    rows = []
    for s in SUPPLIERS:
        reply = parsed["suppliers"].get(s["key"])
        text = (reply or {}).get("text", "")
        if text:
            answer, status = text, "answered"
        elif reply and reply.get("error"):
            answer, status = f"{NO_ANSWER[s['key']]} ({reply['error']})", "error"
        else:
            answer, status = NO_ANSWER[s["key"]], "no answer"
        sc = score(s["key"], reply)
        if text and sc["inTime"] == "No":
            status = "deferred"
        rows.append({
            "key": s["key"], "name": s["name"], "status": status, "answer": answer[:4000],
            "timeToAnswer": f"{elapsed:.0f} s (within this run)" if text and sc["inTime"] == "Yes" else ("office hours" if text else "none"),
            "score": sc,
        })
    return rows


# ---------------------------------------------------------------------------
# Run orchestration


def board_status(state) -> dict:
    run = state.board_run
    if run and run["status"] == "running" and time.time() - run["started"] > STALE_RUN_SECONDS:
        run = dict(run, status="error", error="The run did not finish (timed out or the app restarted). Run it again.")
        state.board_run = run
    return run or {"status": "idle"}


def start_run(state) -> dict | None:
    """Mark a run as started. Returns None when a run is already in progress."""
    with state.board_lock:
        current = board_status(state)
        if current.get("status") == "running":
            return None
        run = {"id": f"{int(time.time() * 1000)}", "status": "running", "started": time.time(), "finished": None,
               "request": state.settings.maria_request or MARIA_REQUEST, "agent": state.settings.maria_agent_name,
               "suppliers": [], "final": "", "error": ""}
        state.board_run = run
        return run


def execute_run(state, run: dict, caller=None) -> dict:
    """Blocking: call Maria's agent and store the parsed result in state. Runs in a worker thread."""
    caller = caller or call_foundry
    started = run["started"]
    try:
        endpoint = state.settings.kolvo_project_endpoint
        if not endpoint:
            raise BoardError("KOLVO_PROJECT_ENDPOINT is not set on the Work IQ emulator app.")
        payload = caller(endpoint, run["agent"], run["request"])
        parsed = parse_response(payload)
        elapsed = time.time() - started
        result = dict(run, status="done", finished=time.time(), suppliers=summarise(parsed, elapsed), final=parsed["final"],
                      error=parsed["error"], responseId=str(payload.get("id", ""))[:100])
    except BoardError as err:
        result = dict(run, status="error", finished=time.time(), error=str(err), suppliers=summarise({"suppliers": {}}, 0))
    except Exception as err:  # noqa: BLE001 - credential and network errors vary by environment
        result = dict(run, status="error", finished=time.time(), error=f"{type(err).__name__}: {str(err)[:300]}",
                      suppliers=summarise({"suppliers": {}}, 0))
    if result["error"] and _TOOL_FAILURE.search(result["error"]):
        result["hint"] = TOOL_FAILURE_HINT
        if result["status"] == "done" and not any(s["status"] == "answered" for s in result["suppliers"]):
            result["status"] = "error"
    with state.board_lock:
        if state.board_run and state.board_run.get("id") == run["id"]:
            state.board_run = result
    return result
