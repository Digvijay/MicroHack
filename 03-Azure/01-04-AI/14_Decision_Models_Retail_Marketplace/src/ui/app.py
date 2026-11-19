"""Listing Gate console — FastAPI + one static HTML page, no build step.

Run from src/:  uv run uvicorn ui.app:app --reload --port 8000

Every model call goes through the same code as the command line (gate.evaluate / gate.rules),
so what you see here is exactly what `python -m gate` measures.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from gate import clients, evaluate, evidence, metrics  # noqa: E402
from gate.questions import QUESTIONS  # noqa: E402
from gate.rules import Thresholds, decide  # noqa: E402
from gate.spec import Choice, Option, Score, YesNo, spec_signature  # noqa: E402

app = FastAPI(title="Zava Marketplace - Listing Gate")
STATIC = Path(__file__).parent / "static"
THRESHOLDS_FILE = config.STATE / "thresholds.json"
REVIEWS_FILE = config.STATE / "reviews.json"
QUEUE_FILE = config.STATE / "queue.json"
_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def thresholds() -> Thresholds:
    return Thresholds.load(THRESHOLDS_FILE if THRESHOLDS_FILE.exists() else None)


def _read(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")


def public(row: dict) -> dict:
    """A listing without its answer key."""
    return {k: row[k] for k in ("listing_id", "split", "seller", "seller_category", "title",
                                "description", "price_eur", "image", "gtin", "starter")}


def guarded(fn):
    try:
        return fn()
    except RuntimeError as exc:  # configuration problems: show the fix
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def get_config() -> dict:
    return {"decision_endpoint": config.DECISION_ENDPOINT, "openai_endpoint": config.OPENAI_ENDPOINT,
            "decision_deployment": config.DECISION_DEPLOYMENT, "luna_deployment": config.LUNA_DEPLOYMENT,
            "thresholds": thresholds().__dict__, "thresholds_file": THRESHOLDS_FILE.exists(),
            "questions": spec_signature(QUESTIONS)}


@app.get("/api/listings")
def listings(split: str = "dev", starter: bool = True) -> list[dict]:
    return [public(r) for r in evidence.select(split=split, starter=starter)]


@app.get("/api/listings/{listing_id}")
def one_listing(listing_id: str, answer: bool = False) -> dict:
    try:
        row = evidence.listing(listing_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    out = public(row)
    product = evidence.products_by_gtin().get(row.get("gtin") or "")
    out["manufacturer_facts"] = product["facts"] if product else None
    out["reference_price_eur"] = product["reference_price_eur"] if product else None
    if answer:
        out["answer_key"] = {"expected": row["expected"], "labels": row["labels"], "construction": row["construction"]}
    return out


class AskRequest(BaseModel):
    listing_id: str
    model: str = "decision"


@app.post("/api/ask")
def ask(req: AskRequest) -> Any:
    def run():
        row = evidence.listing(req.listing_id)
        call, cached = evaluate.ask_one(req.model, row, QUESTIONS)
        d = decide(row, call, thresholds())
        return {"call": call.to_dict(), "cached": cached, "decision": d.to_dict()}
    return guarded(run)


class CustomQuestion(BaseModel):
    listing_id: str
    model: str = "decision"
    kind: str = "yes_no"  # yes_no | choice | score
    instructions: str
    options: list[str] = []


@app.post("/api/custom")
def custom(req: CustomQuestion) -> Any:
    """Challenge 1: ask your own question about a listing and see the typed answer."""
    def run():
        if req.model not in ("decision", "luna"):
            raise RuntimeError("Custom questions go to a decision model: choose decision or luna.")
        opts = tuple(Option(o.strip(), o.strip()) for o in req.options if o.strip())
        if req.kind == "yes_no":
            q = YesNo(name="my_question", instructions=req.instructions)
        elif req.kind == "choice":
            if len(opts) < 2:
                raise RuntimeError("A choice question needs at least two options.")
            q = Choice(name="my_question", instructions=req.instructions, options=opts)
        else:
            if len(opts) < 2:
                raise RuntimeError("A score question needs at least two levels, lowest first.")
            q = Score(name="my_question", instructions=req.instructions, levels=opts)
        row = evidence.listing(req.listing_id)
        call = clients.ask(req.model, evidence.build(row), [q])
        return {"call": call.to_dict()}
    return guarded(run)


class BatchRequest(BaseModel):
    model: str = "decision"
    split: str = "dev"
    starter: bool = True


@app.post("/api/batch")
def batch(req: BatchRequest) -> dict:
    """Run the gate over a set of listings in the background and fill the reviewer queue."""
    rows = evidence.select(split=req.split, starter=req.starter)
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"done": 0, "total": len(rows), "status": "running", "model": req.model}

    def work():
        try:
            def progress(_msg):
                _jobs[job_id]["done"] = min(_jobs[job_id]["done"] + 10, len(rows))
            calls = evaluate.run(req.model, rows, progress=progress)
            t = thresholds()
            queue, outcomes = [], {}
            for row, call in zip(rows, calls):
                d = decide(row, call, t)
                outcomes[d.outcome] = outcomes.get(d.outcome, 0) + 1
                if d.outcome == "review":
                    queue.append({"listing_id": row["listing_id"], "title": row["title"], "model": req.model,
                                  "reasons": [r["message"] for r in d.to_dict()["reasons"]]})
            with _lock:
                _write(QUEUE_FILE, queue)
            _jobs[job_id].update(status="done", done=len(rows), outcomes=outcomes,
                                 report=metrics.report(req.model, rows, calls, t)["gate"])
        except Exception as exc:  # noqa: BLE001 - surface to the page
            _jobs[job_id].update(status="error", error=str(exc))

    threading.Thread(target=work, daemon=True).start()
    return {"job": job_id, "total": len(rows)}


@app.get("/api/batch/{job_id}")
def batch_status(job_id: str) -> dict:
    if job_id not in _jobs:
        raise HTTPException(404, "unknown job")
    return _jobs[job_id]


@app.get("/api/queue")
def queue() -> dict:
    return {"queue": _read(QUEUE_FILE, []), "reviews": _read(REVIEWS_FILE, {})}


class Verdict(BaseModel):
    verdict: str  # publish | reject
    note: str = ""


@app.post("/api/queue/{listing_id}")
def review(listing_id: str, v: Verdict) -> dict:
    with _lock:
        reviews = _read(REVIEWS_FILE, {})
        row = evidence.listing(listing_id)
        reviews[listing_id] = {"verdict": v.verdict, "note": v.note,
                               "answer_key": row["expected"]["outcome"]}
        _write(REVIEWS_FILE, reviews)
    return reviews[listing_id]


@app.get("/api/runs")
def runs() -> list[dict]:
    files = sorted((config.DATA / "recorded").glob("*.jsonl")) + sorted(config.RUNS.glob("*.jsonl"))
    return [{"name": f.name, "path": str(f), "recorded": f.parent.name == "recorded"} for f in files]


@app.get("/api/runs/report")
def run_report(path: str, split: str = "test") -> dict:
    p = Path(path)
    if p.parent not in (config.DATA / "recorded", config.RUNS) or p.suffix != ".jsonl":
        raise HTTPException(400, "not a run file")
    head, rows, calls = evaluate.load(p)
    if split != "all":
        keep = [i for i, r in enumerate(rows) if r["split"] == split]
        rows, calls = [rows[i] for i in keep], [calls[i] for i in keep]
    rep = metrics.report(head["mode"], rows, calls, thresholds(), questions=metrics.questions_for(head))
    if rep["gate"]:
        rep["gate"].pop("confusion", None)
    return rep


app.mount("/images", StaticFiles(directory=config.DATA / "images"), name="images")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
