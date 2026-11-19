"""Configuration for the Listing Gate, read from environment variables (src/.env).

Copy `.env.example` to `src/.env` (post-create.sh does this) and paste the values from
your Hackbox. Everything else has a sensible default.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    # Load src/.env (next to this file) so values load no matter where you start from.
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:  # pragma: no cover - dotenv is optional
    pass

SRC = Path(__file__).resolve().parent
DATA = SRC / "data"
RUNS = SRC / "runs"
STATE = SRC / "state"

# Microsoft-Decision-1.1: https://<resource>.services.ai.azure.com
DECISION_ENDPOINT = os.getenv("DECISION_ENDPOINT", "").strip().rstrip("/")
DECISION_DEPLOYMENT = os.getenv("DECISION_DEPLOYMENT", "decision").strip()

# gpt-6-luna (Decisions API + Responses API): https://<resource>.openai.azure.com
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "").strip().rstrip("/")
LUNA_DEPLOYMENT = os.getenv("LUNA_DEPLOYMENT", "gpt-6-luna").strip()

# Challenge 6: Microsoft-Decision-1 as the judge in Foundry evaluations. (Microsoft-Decision-1.1
# is not supported as an evaluation judge yet, so the lab deploys Decision-1 for this.)
JUDGE_DEPLOYMENT = os.getenv("JUDGE_DEPLOYMENT", "decision-judge").strip()

# Optional: your Foundry project endpoint, to also log Challenge 6 evaluations to the portal.
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "").strip()

# Requests in flight at once during an evaluation. Your deployments are sized for one
# person and the whole room shares the subscription's quota, so keep this small.
MAX_CONCURRENCY = max(1, int(os.getenv("GATE_MAX_CONCURRENCY", "2")))

# Give up on a listing after this many seconds of retries (429 / 5xx / timeouts).
MAX_RETRY_SECONDS = float(os.getenv("GATE_MAX_RETRY_SECONDS", "90"))

# Capacity of each deployment (Hackbox: DecisionCapacity / LunaCapacity). For both models one
# capacity unit = 1 request per minute + 1,000 tokens per minute. The client paces itself to
# stay under both limits instead of waiting on "429 Too Many Requests".
#
# Careful: Azure's rate limiter counts the *size of the request*, not the tokens you are billed
# for. A photo sent as base64 counts as roughly (bytes x 4/3) / 4 tokens — a 10 KB JPEG costs
# about 3,500 tokens of rate limit, even though usage reports a few hundred.
DECISION_CAPACITY = float(os.getenv("DECISION_CAPACITY", "500"))
LUNA_CAPACITY = float(os.getenv("LUNA_CAPACITY", "40"))

# USD per 1 million tokens, used only for cost estimates. Not read from Azure.
PRICES = {
    "decision": {"input": float(os.getenv("PRICE_DECISION_INPUT", "0.05")), "output": 0.0},
    "luna": {"input": float(os.getenv("PRICE_LUNA_DECISIONS_INPUT", "0.10")), "output": 0.0},
    "llm": {
        "input": float(os.getenv("PRICE_LUNA_RESPONSES_INPUT", "0.10")),
        "output": float(os.getenv("PRICE_LUNA_RESPONSES_OUTPUT", "0.50")),
    },
}

TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


def require(name: str, value: str) -> str:
    if not value or "xxxxxxxx" in value:
        raise RuntimeError(
            f"{name} is not set. Open src/.env and paste the value from your Hackbox "
            "(see Challenge 1)."
        )
    return value
