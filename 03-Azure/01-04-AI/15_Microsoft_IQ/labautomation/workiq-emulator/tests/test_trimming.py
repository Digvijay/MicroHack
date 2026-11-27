"""Persona trimming: the key teaching point. Alex sees Sam's channel note (W1) but not Sam's private planner email (W2)."""

import base64
import json

from conftest import KEYS, ids_of

W2_MARKERS = ("We will confirm any change in writing", "Maintenance stop crusher line C3", "planner@poliden.example")


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def test_alex_cannot_retrieve_w2(as_persona, state):
    m = as_persona("alex")
    hidden = ids_of(state, "W2")
    for query in ("Poliden maintenance stop 21 December", "confirm any change in writing", "Poliden planner crusher line C3"):
        res = m.call("retrieve", query=query)
        assert res["isError"] is False
        # Check only returned content; searchMetadata echoes the query terms.
        text = _dump(res["structuredContent"]["application/vnd.ms-workiq.retrieval"]["results"])
        assert hidden["W2"] not in text
        for marker in W2_MARKERS:
            assert marker not in text, (query, marker)


def test_alex_sees_w1_channel_note(as_persona, state):
    m = as_persona("alex")
    w1 = ids_of(state, "W1")["W1"]
    r = m.retrieve("Poliden stop move two weeks")
    assert w1 in {x.get("chatId") for x in r["results"]}
    assert "Poliden's stop will probably move two weeks" in _dump(r["results"])
    msgs = m.fetch(f"/chats/{w1}/messages")[0]
    assert msgs["statusCode"] == 200 and msgs["data"]["value"][0]["from"]["user"]["displayName"] == "Sam"


def test_alex_cannot_fetch_w2(as_persona, state):
    m = as_persona("alex")
    g = ids_of(state, "W2")
    results = m.fetch("/me/messages?$top=100", f"/me/messages/{g['W2']}")
    assert results[0]["statusCode"] == 200 and g["W2"] not in _dump(results[0])
    assert results[1]["statusCode"] == 404


def test_alex_ask_does_not_leak(as_persona):
    res = as_persona("alex").call("ask", question="Has the Poliden planner confirmed the maintenance stop in writing?")
    assert res["isError"] is False
    answer = json.loads(res["content"][0]["text"])["response"]
    for marker in W2_MARKERS:
        assert marker not in answer


def test_sam_sees_w2(as_persona, state):
    g = ids_of(state, "W2")
    assert as_persona("sam").fetch(f"/me/messages/{g['W2']}")[0]["statusCode"] == 200


def test_fetch_blob_trimming(as_persona, state):
    e = state.store.by_item_id["W6"]
    path = f"/drives/{e.extra['driveId']}/items/{e.gid}/content"
    ok = as_persona("alex").call("fetch_blob", path=path)
    sc = ok["structuredContent"]
    assert ok["isError"] is False and sc["statusCode"] == 200 and sc["blobName"] == "Kolvo account plan FY27.docx"
    raw = base64.b64decode(sc["base64Content"])
    assert len(raw) == sc["sizeBytes"] and b"Uptime matters more than price" in raw
    denied = as_persona("sam").call("fetch_blob", path=path)
    assert denied["isError"] is True and denied["structuredContent"]["statusCode"] == 404


def test_viewer_trimming(client, state):
    g = ids_of(state, "W1", "W2", "W5")
    r = client.post("/viewer/login", data={"key": KEYS["alex"], "next": "/viewer/mail"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get(f"/viewer/mail/{g['W2']}").status_code == 404
    assert client.get(f"/viewer/mail/{g['W5']}").status_code == 200
    assert client.get(f"/viewer/chats/{g['W1']}").status_code == 200
    for page in ("/viewer/mail", "/viewer/chats", "/viewer/calendar", "/viewer/files", "/viewer/people"):
        text = client.get(page).text
        for marker in W2_MARKERS:
            assert marker not in text, (page, marker)


def test_scores_are_not_influenced_by_hidden_items(state):
    """BM25 statistics are computed only over the caller's visible items."""
    from workiq_emulator.state import ToolContext
    from workiq_emulator.tools.retrieve import run_retrieve

    ctx = ToolContext(state, state.store, state.store.personas["alex"], "http://t")
    before = run_retrieve(ctx, "Kolvo press line", None)
    state.append_item(
        {
            "id": "hidden-noise", "type": "email", "date": "2026-12-06T10:00:00+01:00", "visibleTo": ["sam"],
            "subject": "Kolvo press line Kolvo press line", "from": {"name": "X", "address": "x@strandvik.example"},
            "to": [{"name": "Sam", "address": "sam@strandvik.example"}], "body": "Kolvo press line",
        }
    )
    ctx = ToolContext(state, state.store, state.store.personas["alex"], "http://t")
    after = run_retrieve(ctx, "Kolvo press line", None)
    assert before == after
