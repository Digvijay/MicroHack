import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from workiq_emulator.app import create_app
from workiq_emulator.config import Settings
from workiq_emulator.state import AppState
from workiq_emulator.store import load_pack_file

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "strandvik_test.json"
KEYS = {
    "alex": "alex-key-0123456789abcdef",
    "sam": "sam-key-0123456789abcdef",
    "sales-leadership": "sl-key-0123456789abcdef",
}
ADMIN_KEY = "admin-key-0123456789abcdef"


class Clock:
    """Controllable time source for auto-Sam delays."""

    def __init__(self, start: float = 1_800_000_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(scope="session")
def pack():
    return load_pack_file(FIXTURE)


def make_state(pack, clock=None, **overrides) -> AppState:
    settings = Settings(persona_keys=dict(KEYS), admin_key=ADMIN_KEY, session_secret="test-session-secret")
    for k, v in overrides.items():
        setattr(settings, k, v)
    kwargs = {"clock": clock} if clock else {}
    return AppState(settings=settings, pack=json.loads(json.dumps(pack)), **kwargs)


@pytest.fixture
def state(pack):
    return make_state(pack)


@pytest.fixture
def client(state):
    return TestClient(create_app(state))


class Mcp:
    """Tiny JSON-RPC helper bound to one persona key."""

    def __init__(self, client: TestClient, key: str | None):
        self.client = client
        self.key = key
        self._id = 0

    def headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    def rpc(self, method: str, params: dict | None = None):
        self._id += 1
        body = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            body["params"] = params
        return self.client.post("/mcp", json=body, headers=self.headers())

    def call(self, name: str, **arguments) -> dict:
        resp = self.rpc("tools/call", {"name": name, "arguments": arguments})
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert "result" in payload, payload
        return payload["result"]

    def retrieve(self, query: str, **kw) -> dict:
        res = self.call("retrieve", query=query, **kw)
        assert res["isError"] is False, res
        return res["structuredContent"]["application/vnd.ms-workiq.retrieval"]

    def fetch(self, *urls: str) -> list[dict]:
        res = self.call("fetch", entityUrls=list(urls))
        assert res["isError"] is False, res
        return res["structuredContent"]["results"]


@pytest.fixture
def as_persona(client):
    return lambda persona: Mcp(client, KEYS[persona])


def ids_of(state: AppState, *item_ids: str) -> dict[str, str]:
    return {i: state.store.by_item_id[i].gid for i in item_ids}
