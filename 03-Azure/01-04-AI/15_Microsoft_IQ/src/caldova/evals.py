"""Evaluation and leaderboard. Scores the agent on data/eval/questions.json (see data/eval/rubric.md)."""

from __future__ import annotations

import concurrent.futures as cf
import json
import re
import time
from datetime import datetime, timezone

from . import agent
from .config import DATA_DIR, STATE_DIR, settings

QUESTIONS = DATA_DIR / "eval" / "questions.json"
LEADERBOARD = STATE_DIR / "leaderboard.json"
URL = re.compile(r"https?://\S+")

JUDGE = """You grade answers from Caldova's operations agent. Compare the ANSWER with the GOLD answer.
Score 0 to 5: 5 correct and complete; 4 one minor fact missing; 3 a key fact or number missing or vague;
2 partly correct with an important error; 1 mostly wrong or confident without grounding; 0 wrong or empty.
For live web questions the gold describes what a good answer contains; judge recency and citation, not exact values.
An answer that only says it does not have the information scores at most 1, unless EXPECT_NO_ACCESS is true.
If EXPECT_NO_ACCESS is true, the best answer says it searched the person's emails and chats (TOOLS_USED shows
workiq) and found nothing newer; saying "I don't know" without searching scores at most 2.
Reply with JSON only: {"score": <0-5>, "reason": "<one short sentence>"}"""

# Which tool labels count as which IQ (see agent.tools()).
TOOL_IQ = {"web_search": "web", "caldova-data": "fabric", "caldova_documents": "foundry", "caldova_graph": "foundry",
           "workiq": "work"}


def iqs_used(tools: list[str]) -> set[str]:
    return {iq for t in tools for label, iq in TOOL_IQ.items() if t.split(".")[0] == label}


def load_questions(upto: int | None = None, only: set[str] | None = None) -> list[dict]:
    qs = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    return [q for q in qs if (upto is None or q["challenge"] <= upto) and (not only or q["id"] in only)]


def deterministic(q: dict, answer: str, tools: list[str]) -> tuple[float, bool, int]:
    low = answer.lower()
    gate = any(p.lower() in low for p in q.get("must_not_include", []))
    groups = q.get("must_include", [])
    passed = sum(any(alt.lower() in low for alt in g) for g in groups)
    include = 0.0 if gate else (4.0 * passed / len(groups) if groups else 4.0)
    # Grounding point: the agent must have called at least one IQ the question needs (web also needs a URL).
    needed = set(q.get("iqs", []))
    if not needed:
        grounded = 1
    else:
        grounded = 1 if needed & iqs_used(tools) else 0
        if q.get("web_citation_required") and not URL.search(answer):
            grounded = 0
    return include, gate, grounded


def judge(client, q: dict, answer: str, tools: list[str]) -> tuple[int, str]:
    prompt = (f"QUESTION ({q['persona']}): {q['question']}\nGOLD: {q['gold']}\n"
              f"EXPECT_NO_ACCESS: {bool(q.get('expect_no_access'))}\nTOOLS_USED: {', '.join(tools) or 'none'}\n"
              f"ANSWER: {answer or '(empty)'}")
    for _ in range(3):
        try:
            r = client.responses.create(model=settings.model, instructions=JUDGE, input=prompt)
            m = re.search(r"\{.*\}", r.output_text, re.S)
            data = json.loads(m.group(0)) if m else {}
            return max(0, min(5, int(data.get("score", 0)))), str(data.get("reason", ""))[:200]
        except Exception as e:  # noqa: BLE001 - retry judge hiccups
            err = str(e)
            time.sleep(3)
    return 0, f"judge failed: {err[:120]}"


def run(iqs: set[str], upto: int, label: str, workers: int = 4, only: set[str] | None = None) -> dict:
    questions = load_questions(upto, only)
    for persona in sorted({q["persona"] for q in questions}):
        agent.build(iqs, persona)

    by_id = {q["id"]: q for q in load_questions()}

    def one(q: dict) -> dict:
        t0 = time.time()
        try:
            previous = None
            if q.get("follows"):  # multi-turn: run the earlier question first in the same conversation
                previous = agent.ask(by_id[q["follows"]]["question"], q["persona"]).response_id
            a = agent.ask(q["question"], q["persona"], previous)
            text, calls, cites = a.text, a.tool_calls, a.citations
        except Exception as e:  # noqa: BLE001 - a failed call scores zero, the run continues
            text, calls, cites = f"(error: {str(e)[:300]})", [], []
        text_for_checks = text + "\n" + "\n".join(cites)
        inc, gate, web = deterministic(q, text_for_checks, calls)
        with agent.project() as p, p.get_openai_client() as client:
            j, reason = judge(client, q, text, calls)
        if gate:
            j = min(j, 1)
        return {"id": q["id"], "challenge": q["challenge"], "persona": q["persona"], "iqs_needed": q["iqs"],
                "score": round(inc + j + web, 1), "include": round(inc, 1), "gate": gate, "judge": j, "grounded": web,
                "reason": reason, "tools": calls, "answer": text, "seconds": round(time.time() - t0, 1)}

    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        results = sorted(pool.map(one, questions), key=lambda r: r["id"])
    total = round(sum(r["score"] for r in results), 1)
    entry = {"label": label, "iqs": sorted(iqs), "upto": upto, "score": total, "max": 10 * len(results),
             "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "results": results}
    STATE_DIR.mkdir(exist_ok=True)
    board = json.loads(LEADERBOARD.read_text()) if LEADERBOARD.exists() else []
    board.append(entry)
    LEADERBOARD.write_text(json.dumps(board, indent=2))
    return entry


def board() -> list[dict]:
    return json.loads(LEADERBOARD.read_text()) if LEADERBOARD.exists() else []
