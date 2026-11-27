"""v2: chat write over MCP, viewer replies as Sam or Alex, auto-Sam and the Kolvo procurement board."""

import json
from pathlib import Path

import pytest
from conftest import ADMIN_KEY, KEYS, Clock, Mcp, make_state

ADMIN = {"Authorization": f"Bearer {ADMIN_KEY}"}
from starlette.testclient import TestClient

from workiq_emulator import board, chat
from workiq_emulator.app import create_app
from workiq_emulator.store import PackError, load_pack_file, seed_file

SAMPLE = json.loads((Path(__file__).resolve().parent / "fixtures" / "responses_sample.json").read_text(encoding="utf-8"))
ASK_SAM = "Sam, can we take the Rotterdam unit reserved for Poliden (RSV-2291)? Is the Poliden stop moving?"


def _thread(client, key, gid):
    return Mcp(client, key).fetch(f"/chats/{gid}/messages")[0]["data"]["value"]


def _login(client, persona):
    r = client.post("/viewer/login", data={"key": KEYS[persona], "next": "/viewer/chats"}, follow_redirects=False)
    assert r.status_code == 303


# -- chat write over MCP --------------------------------------------------------


def test_agent_posts_into_thread(client, state):
    gid = state.store.by_item_id["W3"].gid
    alex = Mcp(client, KEYS["alex"])
    body = json.dumps({"body": {"contentType": "text", "content": "Sam, quick question about Poliden."}})
    res = alex.call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=body)
    assert res["isError"] is False and res["structuredContent"]["statusCode"] == 201
    data = res["structuredContent"]["data"]
    assert data["from"]["user"]["displayName"] == "Alex's agent (on behalf of Alex)"
    assert data["from"]["application"]["displayName"] == "Alex's agent"
    # Sam sees the post, newest first, and so does retrieve.
    newest = _thread(client, KEYS["sam"], gid)[0]
    assert newest["body"]["content"] == "Sam, quick question about Poliden." and newest["id"] == data["id"]
    hits = Mcp(client, KEYS["sam"]).retrieve("quick question about Poliden")
    assert "Alex's agent (on behalf of Alex)" in json.dumps(hits["results"])


def test_chat_write_html_and_encoded_ids(client, state):
    gid = state.store.by_item_id["W3"].gid
    encoded = gid.replace(":", "%3A").replace("@", "%40")
    body = json.dumps({"body": {"contentType": "html", "content": "<p>Hello <b>Sam</b></p>"}})
    res = Mcp(client, KEYS["alex"]).call("create_entity", parentUrl=f"/me/chats/{encoded}/messages", jsonBody=body)
    assert res["isError"] is False
    assert res["structuredContent"]["data"]["body"]["content"] == "Hello Sam"


def test_chat_write_denied_for_non_members_and_other_paths(client, state):
    w3 = state.store.by_item_id["W3"].gid
    body = json.dumps({"body": {"content": "hi"}})
    outsider = Mcp(client, KEYS["sales-leadership"]).call("create_entity", parentUrl=f"/chats/{w3}/messages", jsonBody=body)
    assert outsider["isError"] is True and outsider["structuredContent"]["statusCode"] == 404
    empty = Mcp(client, KEYS["alex"]).call("create_entity", parentUrl=f"/chats/{w3}/messages", jsonBody=json.dumps({"body": {"content": "  "}}))
    assert empty["isError"] is True
    # Other writes stay blocked by tenant policy.
    blocked = Mcp(client, KEYS["alex"]).call("create_entity", parentUrl="/me/events", jsonBody="{}")
    assert blocked["isError"] is True and "Blocked by Work IQ tenant policy" in blocked["content"][0]["text"]
    assert len(state.store.by_item_id["W3"].extra["messages"]) == 1


def test_chat_write_can_be_switched_off(pack):
    st = make_state(pack, allow_chat_write=False)
    c = TestClient(create_app(st))
    gid = st.store.by_item_id["W3"].gid
    res = Mcp(c, KEYS["alex"]).call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": "hi"}}))
    assert res["isError"] is True and "Blocked by Work IQ tenant policy" in res["content"][0]["text"]


# -- viewer: play Sam and Alex ---------------------------------------------------


def test_viewer_post_as_sam_requires_session(client, state):
    gid = state.store.by_item_id["W3"].gid
    anon = client.post("/viewer/reply", data={"chat": gid, "as": "sam", "text": "Hi"}, follow_redirects=False)
    assert anon.status_code == 401
    assert len(state.store.by_item_id["W3"].extra["messages"]) == 1
    assert client.get(f"/viewer/api/chat?id={gid}").status_code == 401


def test_viewer_post_as_sam_with_session(client, state):
    gid = state.store.by_item_id["W3"].gid
    _login(client, "alex")
    page = client.get(f"/viewer/chats/{gid}").text
    assert '<option value="sam">Sam</option>' in page and '<option value="alex" selected>Alex</option>' in page
    assert 'src="/viewer/static/viewer.js"' in page and "Auto-Sam is" in page
    r = client.post("/viewer/reply", data={"chat": gid, "as": "sam", "text": "Yes, it is moving."}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/viewer/chats/")
    data = client.get(f"/viewer/api/chat?id={gid}").json()
    assert data["messages"][-1]["from"] == "Sam" and data["messages"][-1]["text"] == "Yes, it is moving." and not data["messages"][-1]["agent"]
    # Alex makes the call, as a person.
    client.post("/viewer/reply", data={"chat": gid, "as": "alex", "text": "Approved. Take the Rotterdam unit."}, follow_redirects=False)
    assert _thread(client, KEYS["sam"], gid)[0]["from"]["user"]["displayName"] == "Alex"


def test_viewer_post_rejects_non_members_foreign_origin_and_hidden_chats(client, state):
    w3 = state.store.by_item_id["W3"].gid
    w1 = state.store.by_item_id["W1"].gid
    _login(client, "alex")
    assert client.post("/viewer/reply", data={"chat": w3, "as": "sales-leadership", "text": "x"}).status_code == 403
    assert client.post("/viewer/reply", data={"chat": w3, "as": "sam", "text": "x"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/viewer/reply", data={"chat": w3, "as": "sam", "text": ""}).status_code == 400
    _login(client, "sales-leadership")
    assert client.post("/viewer/reply", data={"chat": w3, "as": "sam", "text": "x"}).status_code == 404
    assert client.post("/viewer/reply", data={"chat": w1, "as": "sam", "text": "ok"}, follow_redirects=False).status_code == 303
    assert len(state.store.by_item_id["W3"].extra["messages"]) == 1


# -- auto-Sam --------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        (ASK_SAM, chat.SAM_YES_REPLY),
        ("@Sam is the maintenance stop at Poliden still on 21 December?", chat.SAM_YES_REPLY),
        ("Sam, how is Singapore?", chat.SAM_BUSY_REPLY),
        ("Can we take the Poliden unit?", None),
        ("Samuel and Samantha say hi about the unit", None),
    ],
)
def test_auto_sam_reply_rules(text, expected):
    assert chat.auto_sam_reply(text) == expected


def test_auto_sam_replies_after_delay(pack):
    clock = Clock()
    st = make_state(pack, clock=clock, auto_sam=True, auto_sam_delay=30.0)
    c = TestClient(create_app(st))
    gid = st.store.by_item_id["W3"].gid
    alex = Mcp(c, KEYS["alex"])
    alex.call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": ASK_SAM}}))
    assert st.sam_pending("W3")
    clock.advance(10)
    assert _thread(c, KEYS["alex"], gid)[0]["body"]["content"] == ASK_SAM
    clock.advance(25)
    newest = _thread(c, KEYS["alex"], gid)[0]
    assert newest["body"]["content"] == chat.SAM_YES_REPLY and newest["from"]["user"]["displayName"] == "Sam"
    assert not st.sam_pending("W3")
    # Sam's own message does not trigger another reply, and a second question gets one reply.
    clock.advance(60)
    assert _thread(c, KEYS["alex"], gid)[0]["body"]["content"] == chat.SAM_YES_REPLY
    alex.call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": "Sam, are you there?"}}))
    alex.call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": "Sam, hello again?"}}))
    clock.advance(31)
    msgs = _thread(c, KEYS["alex"], gid)
    assert msgs[0]["body"]["content"] == chat.SAM_BUSY_REPLY and msgs[1]["body"]["content"] == "Sam, hello again?"


def test_auto_sam_off_by_default_and_toggle(client, state):
    gid = state.store.by_item_id["W3"].gid
    assert state.auto_sam is False
    Mcp(client, KEYS["alex"]).call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": ASK_SAM}}))
    assert not state.sam_pending("W3")
    assert client.post("/viewer/auto-sam", data={"on": "true", "next": "/viewer/chats"}, follow_redirects=False).status_code == 401
    _login(client, "alex")
    r = client.post("/viewer/auto-sam", data={"on": "true", "next": f"/viewer/chats/{gid}"}, follow_redirects=False)
    assert r.status_code == 303 and state.auto_sam is True
    assert client.get(f"/viewer/api/chat?id={gid}").json()["autoSam"] is True


def test_auto_sam_only_in_kolvo_thread(pack):
    st = make_state(pack, auto_sam=True, auto_sam_delay=0.0)
    st.post_chat_message("W1", "alex", ASK_SAM)
    assert not st.sam_pending("W1")
    with pytest.raises(PackError):
        st.post_chat_message("W3", "sales-leadership", "x")


# -- Kolvo procurement board -------------------------------------------------------


def test_parse_recorded_responses_payload():
    parsed = board.parse_response(SAMPLE)
    assert set(parsed["suppliers"]) == {"strandvik", "nordic", "hallberg"}
    assert "ships today" in parsed["suppliers"]["nordic"]["text"]
    assert "office hours" in parsed["suppliers"]["hallberg"]["text"]
    assert "CS-88412" in parsed["suppliers"]["strandvik"]["text"]
    assert parsed["final"].startswith("Three suppliers asked.")
    rows = {r["key"]: r for r in board.summarise(parsed, 42.0)}
    assert rows["strandvik"]["score"] == {"answered": "Yes", "inTime": "Yes", "holdsUnit": "Yes", "quoteOnly": "Yes", "personConfirms": "Yes"}
    assert rows["nordic"]["score"]["holdsUnit"] == "No" and rows["nordic"]["score"]["inTime"] == "Yes"
    assert rows["hallberg"]["status"] == "deferred" and rows["hallberg"]["score"]["inTime"] == "No"
    assert rows["strandvik"]["timeToAnswer"] == "42 s (within this run)"


def test_parse_strandvik_not_connected():
    failed = json.loads((Path(__file__).resolve().parent / "fixtures" / "responses_sample_failed.json").read_text(encoding="utf-8"))
    rows = {r["key"]: r for r in board.summarise(board.parse_response(failed), 5)}
    assert rows["strandvik"]["status"] == "error" and rows["strandvik"]["score"]["answered"] == "No"
    assert rows["strandvik"]["answer"].startswith("No answer: check A2A and the Foundry Agent Consumer role.")
    assert "A user error occurred" in rows["strandvik"]["answer"]
    assert rows["nordic"]["status"] == "answered"
    # Tolerant variants: a failed call without an output item, and the a2a_call type name.
    payload = {"output": [{"type": "a2a_preview_call", "call_id": "c9", "name": "strandvik-a2a", "status": "failed",
                           "error": {"code": "tool_user_error", "message": "A user error occurred while executing a tool call"}}]}
    assert board.parse_response(payload)["suppliers"]["strandvik"]["error"] == "A user error occurred while executing a tool call"
    alt = {"output": [{"type": "a2a_call", "id": "x1", "name": "nordic"}, {"type": "a2a_call_output", "call_id": "x1", "output": "in stock"}]}
    assert board.parse_response(alt)["suppliers"]["nordic"]["text"] == "in stock"
    # Whole response failed: the error is surfaced for the board.
    assert board.parse_response({"status": "failed", "error": {"code": "server_error", "message": "boom"}, "output": []})["error"] == "boom"


def test_responses_url_validation():
    assert board.responses_url("https://acct.services.ai.azure.com/api/projects/kolvo") == "https://acct.services.ai.azure.com/api/projects/kolvo/openai/v1/responses"
    for bad in ("http://acct.services.ai.azure.com/api/projects/kolvo", "https://evil.example/api/projects/kolvo", "https://acct.services.ai.azure.com/"):
        with pytest.raises(board.BoardError):
            board.responses_url(bad)


def test_board_run_with_mocked_foundry(pack, monkeypatch):
    calls = []

    def fake(endpoint, agent, request_text, timeout=180):
        calls.append((endpoint, agent, request_text))
        return SAMPLE

    monkeypatch.setattr(board, "call_foundry", fake)
    st = make_state(pack, kolvo_project_endpoint="https://acct.services.ai.azure.com/api/projects/kolvo")
    c = TestClient(create_app(st))
    assert c.get("/board", follow_redirects=False).headers["location"] == "/viewer/board"
    assert c.get("/viewer/board", follow_redirects=False).status_code == 303  # login first
    assert c.post("/viewer/board/run", headers={"Accept": "application/json"}).status_code == 401
    assert calls == []
    _login(c, "alex")
    page = c.get("/viewer/board").text
    assert "Run 02:13" in page and "No run yet" in page and "SD9-K-0412" in page
    r = c.post("/viewer/board/run", headers={"Accept": "application/json"})
    assert r.status_code == 200 and r.json()["status"] == "done"
    assert calls[0][0].endswith("/projects/kolvo") and calls[0][1] == "maria-procurement" and "quote only" in calls[0][2]
    page = c.get("/viewer/board").text
    assert "Hallberg Repair Services" in page and "CS-88412" in page and "Scorecard" in page
    assert c.get("/viewer/api/board").json()["status"] == "done"


def test_board_errors_are_visible(pack, monkeypatch):
    st = make_state(pack)
    c = TestClient(create_app(st))
    _login(c, "alex")
    assert "KOLVO_PROJECT_ENDPOINT is not set" in c.get("/viewer/board").text
    r = c.post("/viewer/board/run", follow_redirects=False)
    assert r.status_code == 303
    page = c.get("/viewer/board").text
    assert "The run failed." in page and "No answer: check A2A and the Foundry Agent Consumer role." in page

    def boom(*a, **k):
        raise board.BoardError("Foundry returned HTTP 403.")

    monkeypatch.setattr(board, "call_foundry", boom)
    st.settings.kolvo_project_endpoint = "https://acct.services.ai.azure.com/api/projects/kolvo"
    c.post("/viewer/board/run")
    assert "Foundry returned HTTP 403." in c.get("/viewer/board").text


def test_board_refuses_concurrent_runs(pack):
    st = make_state(pack)
    assert board.start_run(st) is not None
    assert board.start_run(st) is None
    st.board_run["started"] -= board.STALE_RUN_SECONDS + 1
    assert board.board_status(st)["status"] == "error"
    assert board.start_run(st) is not None


# -- seed selection ----------------------------------------------------------------


def test_seed_selection():
    assert seed_file().name == "strandvik.json"
    assert seed_file("Other-Pack").name == "other-pack.json"
    with pytest.raises(PackError):
        seed_file("../etc/passwd")


@pytest.mark.skipif(not seed_file().exists(), reason="seed/strandvik.json is written by the data workstream")
def test_bundled_strandvik_seed_trimming():
    pack = load_pack_file()
    keys = {"alex": KEYS["alex"], "sam": KEYS["sam"]}
    from workiq_emulator.config import Settings
    from workiq_emulator.state import AppState

    st = AppState(settings=Settings(persona_keys=keys, admin_key="a" * 20, session_secret="s"), pack=pack)
    c = TestClient(create_app(st))
    w1, w2 = st.store.by_item_id["W1"], st.store.by_item_id["W2"]
    alex = Mcp(c, keys["alex"])
    assert "alex" in w1.visible and "alex" not in w2.visible
    assert alex.fetch(f"/me/messages/{w2.gid}")[0]["statusCode"] == 404
    thread = chat.kolvo_thread(st.store, "W3")
    assert thread is not None and {"alex", "sam"} <= set(thread.item["members"])


def test_whole_run_failure_explains_a2a(pack, monkeypatch):
    def refused(*a, **k):
        raise board.BoardError('Foundry returned HTTP 400. {"error": {"code": "tool_user_error", "message": "A user error occurred while executing a tool call."}}')

    monkeypatch.setattr(board, "call_foundry", refused)
    st = make_state(pack, kolvo_project_endpoint="https://acct.services.ai.azure.com/api/projects/kolvo")
    c = TestClient(create_app(st))
    _login(c, "alex")
    data = c.post("/viewer/board/run", headers={"Accept": "application/json"}).json()
    assert data["status"] == "error" and "Foundry Agent Consumer" in data["hint"]
    assert all(s["status"] == "no answer" for s in data["suppliers"])
    assert "one A2A tool failing stops the whole run" in c.get("/viewer/board").text


def test_session_cookie_domain_on_functions(pack, monkeypatch):
    from http.cookies import SimpleCookie

    c = TestClient(create_app(make_state(pack)), base_url="https://wiq.azurewebsites.net")
    r = c.post("/viewer/login", data={"key": KEYS["alex"], "next": "/viewer/chats"}, follow_redirects=False)
    assert "domain" not in r.headers["set-cookie"].lower()
    monkeypatch.setenv("FUNCTIONS_WORKER_RUNTIME", "python")
    r = c.post("/viewer/login", data={"key": KEYS["alex"], "next": "/viewer/chats"}, follow_redirects=False)
    # The Functions worker re-parses Set-Cookie with SimpleCookie; the domain must survive non-empty.
    assert SimpleCookie(r.headers["set-cookie"])["wiq_session"]["domain"] == "wiq.azurewebsites.net"


# -- story clock and coach controls -------------------------------------------------


def _post(c, key, gid, text):
    return Mcp(c, key).call("create_entity", parentUrl=f"/chats/{gid}/messages", jsonBody=json.dumps({"body": {"content": text}}))


def test_story_clock_anchors_at_first_live_write(pack):
    clock = Clock()
    st = make_state(pack, clock=clock)
    c = TestClient(create_app(st))
    gid = st.store.by_item_id["W3"].gid
    clock.advance(3 * 24 * 3600)  # the lab was deployed days before the event
    assert st.story_now().isoformat() == "2026-12-15T03:45:00+01:00" and not st.story_clock_running()
    # A post in another chat does not start the clock.
    st.post_chat_message("W1", "alex", "hello")
    assert not st.story_clock_running()
    first = _post(c, KEYS["alex"], gid, "Sam, a question about the Poliden unit.")["structuredContent"]["data"]
    assert first["createdDateTime"] == "2026-12-15T02:45:00Z"
    clock.advance(7 * 60)
    _login(c, "sam")
    c.post("/viewer/reply", data={"chat": gid, "as": "sam", "text": "Yes, it is moving two weeks."})
    assert _thread(c, KEYS["alex"], gid)[0]["createdDateTime"] == "2026-12-15T02:52:00Z"
    assert "Tue 03:52" in c.get(f"/viewer/api/chat?id={gid}").json()["storyTime"]


def test_coach_sets_clock_for_alex_approval(pack):
    clock = Clock()
    st = make_state(pack, clock=clock)
    c = TestClient(create_app(st))
    gid = st.store.by_item_id["W3"].gid
    assert "Coach controls" in c.get("/viewer/coach").text
    assert c.post("/viewer/coach/clock", data={"time": "07:30", "admin_key": "wrong"}).status_code == 401
    assert c.post("/viewer/coach/clock", data={"time": "25:99", "admin_key": ADMIN_KEY}).status_code == 400
    r = c.post("/viewer/coach/clock", data={"time": "07:30", "admin_key": ADMIN_KEY}, follow_redirects=False)
    assert r.status_code == 303 and st.story_clock_running()
    clock.advance(30)
    _login(c, "alex")
    c.post("/viewer/reply", data={"chat": gid, "as": "alex", "text": "Approved: take the Rotterdam unit, keep the flight until 11:00."})
    newest = _thread(c, KEYS["sam"], gid)[0]
    assert newest["createdDateTime"] == "2026-12-15T06:30:30Z" and newest["from"]["user"]["displayName"] == "Alex"


def test_coach_reset_thread_and_admin_endpoints(pack):
    clock = Clock()
    st = make_state(pack, clock=clock, auto_sam=True)
    c = TestClient(create_app(st))
    gid = st.store.by_item_id["W3"].gid
    _post(c, KEYS["alex"], gid, "Sam, can we take the Poliden unit?")
    assert len(st.store.by_item_id["W3"].extra["messages"]) == 2 and st.sam_pending("W3")
    assert c.post("/admin/thread/reset").status_code == 401
    r = c.post("/admin/thread/reset", headers=ADMIN)
    assert r.json()["removed"] == 1 and r.json()["running"] is False and r.json()["storyTime"] == "2026-12-15T03:45:00+01:00"
    assert len(st.store.by_item_id["W3"].extra["messages"]) == 1 and not st.sam_pending("W3")
    assert c.post("/admin/clock", json={"time": "04:10"}).status_code == 401
    assert c.post("/admin/clock", json={"time": "noon"}, headers=ADMIN).status_code == 400
    assert c.post("/admin/clock", json={"time": "2026-12-15T04:10:00+01:00"}, headers=ADMIN).json() == {"storyTime": "2026-12-15T04:10:00+01:00", "running": True}
    clock.advance(60)
    assert c.get("/admin/clock", headers=ADMIN).json()["storyTime"] == "2026-12-15T04:11:00+01:00"
    _post(c, KEYS["alex"], gid, "Proposal sent.")
    assert c.post("/viewer/coach/reset-thread", data={"admin_key": ADMIN_KEY}, follow_redirects=False).status_code == 303
    assert len(st.store.by_item_id["W3"].extra["messages"]) == 1 and not st.story_clock_running()


@pytest.mark.parametrize("text", [
    "SD-900: in stock, ships today.\n- **Holding the unit:** **No**, we cannot reserve or hold stock; it is sold to whoever orders first",
    "We are unable to reserve a unit for you.",
    "We don't hold stock for customers.",
])
def test_score_no_hold_variants(text):
    assert board.score("nordic", {"text": text})["holdsUnit"] == "No"


def test_score_hold_still_recognised():
    s = board.score("strandvik", {"text": "Case CS-88412 opened; we can hold SD9-R-0733 pending Alex."})
    assert s["holdsUnit"] == "Yes"
