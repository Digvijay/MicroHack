"""Run the gate's questions over many listings, with a cache and a small number of parallel calls.

Results are cached in `src/runs/cache/`, keyed by model, deployment, evidence, photo and the
exact question wording. Re-running costs nothing; changing one question re-asks only what
changed. Each run is also saved as one JSON Lines file you can report on later.
"""

from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import threading
from pathlib import Path
from typing import Callable

import config
from gate import clients, evidence
from gate.questions import QUESTIONS
from gate.spec import GateCall, Question, spec_signature

CACHE = config.RUNS / "cache"


def deployment(mode: str) -> str:
    return config.DECISION_DEPLOYMENT if mode == "decision" else config.LUNA_DEPLOYMENT


def cache_key(mode: str, row: dict, questions: list[Question], layout: str) -> str:
    ev = evidence.build(row, layout)
    blob = json.dumps({
        "mode": mode,
        "endpoint": config.DECISION_ENDPOINT if mode == "decision" else config.OPENAI_ENDPOINT,
        "deployment": deployment(mode),
        "evidence": ev.text(),
        "photo": row.get("image"),
        "questions": spec_signature(questions),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def ask_one(mode: str, row: dict, questions: list[Question], layout: str = "structured",
            use_cache: bool = True) -> tuple[GateCall, bool]:
    key = cache_key(mode, row, questions, layout)
    path = CACHE / mode / f"{key}.json"
    if use_cache and path.exists():
        return GateCall.from_dict(json.loads(path.read_text(encoding="utf-8"))), True
    call = clients.ask(mode, evidence.build(row, layout), questions)
    if not call.error:  # never cache failures
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(call.to_dict()), encoding="utf-8")
    return call, False


def run(mode: str, rows: list[dict], questions: list[Question] | None = None, layout: str = "structured",
        use_cache: bool = True, progress: Callable[[str], None] | None = print) -> list[GateCall]:
    questions = questions or QUESTIONS
    results: list[GateCall | None] = [None] * len(rows)
    done = cached = 0
    lock = threading.Lock()

    def work(i: int) -> None:
        nonlocal done, cached
        call, hit = ask_one(mode, rows[i], questions, layout, use_cache)
        results[i] = call
        with lock:
            done += 1
            cached += hit
            if progress and (done % 10 == 0 or done == len(rows)):
                progress(f"  {mode}: {done}/{len(rows)} listings ({cached} from cache)")

    with cf.ThreadPoolExecutor(max_workers=config.MAX_CONCURRENCY) as pool:
        list(pool.map(work, range(len(rows))))
    return [r for r in results if r is not None]


def save(path: Path, mode: str, rows: list[dict], calls: list[GateCall], **meta) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    head = {"type": "run", "mode": mode, "deployment": deployment(mode),
            "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "questions": spec_signature(QUESTIONS), **meta}
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(head) + "\n")
        for row, call in zip(rows, calls):
            f.write(json.dumps({"listing_id": row["listing_id"], "call": call.to_dict()}) + "\n")
    return path


def load(path: str | Path) -> tuple[dict, list[dict], list[GateCall]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    head = json.loads(lines[0])
    rows, calls = [], []
    for line in lines[1:]:
        rec = json.loads(line)
        rows.append(evidence.listing(rec["listing_id"]))
        calls.append(GateCall.from_dict(rec["call"]))
    return head, rows, calls
