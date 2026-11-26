"""Persona trimming: the key teaching point. Each persona sees only its own items."""

import base64
import json

from conftest import KEYS, ids_of

M3_MARKERS = ("L-7731", "pressure test", "QR-2026-118", "quality hold")
M4_MARKERS = ("Danish Maritime Authority", "port of Esbjerg", "Esbjerg closed", "Earliest departure")


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def test_sales_lead_cannot_retrieve_m3_or_m4(as_persona, state):
    m = as_persona("sales-lead")
    hidden = ids_of(state, "M3", "M4", "M6")
    for query in ("Teglbruk lot L-7731 pressure test quality hold", "Esbjerg port closed storm PO-7781", "HX-220 backup supplier Teglbruk deviation", "Brennmark Friday"):
        res = m.call("retrieve", query=query)
        assert res["isError"] is False
        # Check only returned content; searchMetadata echoes the query terms.
        text = _dump(res["structuredContent"]["application/vnd.ms-workiq.retrieval"]["results"])
        for gid in hidden.values():
            assert gid not in text
        for marker in M3_MARKERS + M4_MARKERS:
            assert marker not in text, (query, marker)


def test_sales_lead_cannot_fetch_m3_or_m4(as_persona, state):
    m = as_persona("sales-lead")
    g = ids_of(state, "M3", "M4")
    results = m.fetch("/me/chats", "/me/messages?$top=100", f"/chats/{g['M3']}/messages", f"/me/messages/{g['M4']}", f"/chats/{g['M3']}")
    assert results[0]["statusCode"] == 200 and g["M3"] not in _dump(results[0])
    assert results[1]["statusCode"] == 200 and g["M4"] not in _dump(results[1])
    assert [r["statusCode"] for r in results[2:]] == [404, 404, 404]


def test_sales_lead_ask_does_not_leak(as_persona):
    res = as_persona("sales-lead").call("ask", question="Is Teglbruk on quality hold, and is the port of Esbjerg closed?")
    assert res["isError"] is False
    answer = json.loads(res["content"][0]["text"])["response"]
    for marker in M3_MARKERS + M4_MARKERS:
        assert marker not in answer


def test_plant_manager_sees_everything_the_answer_needs(as_persona, state):
    m = as_persona("plant-manager")
    g = ids_of(state, "M1", "M2", "M2-transcript", "M3", "M5-fwd", "M6", "M7", "M8")
    msgs = _dump(m.fetch("/me/messages?$top=100"))
    assert g["M1"] in msgs and g["M5-fwd"] in msgs
    assert "We could accept 2,000 by Friday" in msgs
    chats = _dump(m.fetch("/me/chats"))
    assert g["M3"] in chats and g["M6"] in chats
    events = _dump(m.fetch("/me/events"))
    assert g["M2"] in events and g["M8"] in events
    r = m.retrieve("Key account plan Brennmark renewal", capabilities=[{"name": "OneDriveAndSharePoint"}])
    assert r["results"][0]["resourceId"] == g["M7"]
    assert r["results"][0]["resourceMetadata"]["document"]["title"] == "Key account plan FY27, Brennmark.docx"
    m3 = m.retrieve("Teglbruk L-7731 pressure test")
    assert g["M3"] in {x.get("chatId") for x in m3["results"]}
    # Plant Manager does not get the freight forwarder email M4.
    assert ids_of(state, "M4")["M4"] not in msgs


def test_m6_has_updated_eta(as_persona, state):
    gid = ids_of(state, "M6")["M6"]
    data = as_persona("supply-planner").fetch(f"/chats/{gid}/messages")[0]["data"]["value"]
    assert any("arrives in Borås around 16 Dec" in x["body"]["content"] for x in data)


def test_supply_planner_sees_m3_m4(as_persona, state):
    m = as_persona("supply-planner")
    g = ids_of(state, "M3", "M4")
    assert [r["statusCode"] for r in m.fetch(f"/chats/{g['M3']}/messages", f"/me/messages/{g['M4']}")] == [200, 200]


def test_fetch_blob_trimming(as_persona, state):
    e = state.store.by_item_id["M7"]
    path = f"/drives/{e.extra['driveId']}/items/{e.gid}/content"
    ok = as_persona("plant-manager").call("fetch_blob", path=path)
    sc = ok["structuredContent"]
    assert ok["isError"] is False and sc["statusCode"] == 200 and sc["blobName"] == "Key account plan FY27, Brennmark.docx"
    raw = base64.b64decode(sc["base64Content"])
    assert len(raw) == sc["sizeBytes"] and b"6.5 M EUR" in raw
    assert "base64Content" not in ok["content"][0]["text"] or sc["base64Content"] not in ok["content"][0]["text"]
    denied = as_persona("quality-head").call("fetch_blob", path=path)
    assert denied["isError"] is True and denied["structuredContent"]["statusCode"] == 404


def test_viewer_trimming(client, state):
    g = ids_of(state, "M3", "M4", "M1")
    r = client.post("/viewer/login", data={"key": KEYS["sales-lead"], "next": "/viewer/mail"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get(f"/viewer/chats/{g['M3']}").status_code == 404
    assert client.get(f"/viewer/mail/{g['M4']}").status_code == 404
    assert client.get(f"/viewer/mail/{g['M1']}").status_code == 200
    chats = client.get("/viewer/chats").text
    assert "HX-220 supply and quality" not in chats
    for page in ("/viewer/mail", "/viewer/chats", "/viewer/calendar", "/viewer/files", "/viewer/people"):
        text = client.get(page).text
        for marker in M3_MARKERS + M4_MARKERS:
            assert marker not in text, (page, marker)


def test_scores_are_not_influenced_by_hidden_items(state):
    """BM25 statistics are computed only over the caller's visible items."""
    from workiq_emulator.state import ToolContext
    from workiq_emulator.tools.retrieve import run_retrieve

    ctx = ToolContext(state, state.store, state.store.personas["sales-lead"], "http://t")
    before = run_retrieve(ctx, "Brennmark Friday", None)
    state.append_item(
        {
            "id": "hidden-noise", "type": "email", "date": "2026-12-06T10:00:00+01:00", "visibleTo": ["quality-head"],
            "subject": "Brennmark Friday Brennmark Friday", "from": {"name": "X", "address": "x@caldova.example"},
            "to": [{"name": "Quality Head", "address": "quality.head@caldova.example"}], "body": "Brennmark Friday",
        }
    )
    ctx = ToolContext(state, state.store, state.store.personas["sales-lead"], "http://t")
    after = run_retrieve(ctx, "Brennmark Friday", None)
    assert before == after
