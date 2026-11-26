"""fetch paging and path rules, blocked mutations, call_function, ask."""

import json

import pytest
from conftest import KEYS, Mcp, ids_of, make_state
from starlette.testclient import TestClient

from workiq_emulator.app import create_app
from workiq_emulator.tools.fetch import GraphError, apply_collection


def test_skip_and_skiptoken_rejected(as_persona):
    r = as_persona("sales-lead").fetch("/me/messages?$skip=10", "/me/messages?$skiptoken=abc")
    assert [x["statusCode"] for x in r] == [400, 400]
    assert "blocked" in r[0]["data"]["error"]["message"]


def test_top_default_and_cap():
    items = [{"id": str(i), "n": i} for i in range(150)]
    assert len(apply_collection(items, {}, "x", None)["value"]) == 25
    assert len(apply_collection(items, {"$top": "500"}, "x", None)["value"]) == 100
    assert len(apply_collection(items, {"$top": "7"}, "x", None)["value"]) == 7
    with pytest.raises(GraphError):
        apply_collection(items, {"$top": "abc"}, "x", None)


def test_chat_messages_capped_at_10(client, state):
    msgs = [{"date": f"2026-12-05T10:{i:02d}:00+01:00", "from": "sales-lead", "text": f"message {i}"} for i in range(15)]
    state.append_item(
        {"id": "long-chat", "type": "chat", "date": "2026-12-05T10:00:00+01:00", "visibleTo": ["sales-lead", "plant-manager"],
         "chatType": "oneOnOne", "members": ["sales-lead", "plant-manager"], "messages": msgs}
    )
    gid = state.store.by_item_id["long-chat"].gid
    r = Mcp(client, KEYS["sales-lead"]).fetch(f"/chats/{gid}/messages?$top=50", f"/me/chats/{gid}/messages")
    assert len(r[0]["data"]["value"]) == 10 and len(r[1]["data"]["value"]) == 10
    assert r[0]["data"]["value"][0]["body"]["content"] == "message 14"  # newest first


def test_path_policy(as_persona):
    r = as_persona("sales-lead").fetch(
        "/groups", "/me/authentication/methods", "/servicePrincipals", "/users/x/authentication/methods", "/me/nothing", "https://evil.example/me"
    )
    assert [x["statusCode"] for x in r] == [403, 403, 403, 403, 404, 400]


def test_fetch_graph_shapes_and_odata(as_persona, state):
    m = as_persona("sales-lead")
    me, msgs, filtered, searched, sel, view, noview = m.fetch(
        "/me",
        "/me/mailFolders/inbox/messages",
        "/me/messages?$filter=contains(subject,'SO-9001')&$orderby=receivedDateTime asc",
        "/me/messages?$search=\"partial deliveries\"",
        "/me/messages?$select=subject,from&$top=2",
        "/me/calendarView?startDateTime=2026-12-07T00:00:00Z&endDateTime=2026-12-08T00:00:00Z",
        "/me/calendarView",
    )
    assert me["data"]["displayName"] == "Sales Lead" and me["data"]["mail"] == "sales.lead@caldova.example"
    first = msgs["data"]["value"][0]
    for key in ("id", "subject", "from", "toRecipients", "ccRecipients", "receivedDateTime", "bodyPreview", "body", "conversationId", "isRead", "importance"):
        assert key in first
    assert first["from"]["emailAddress"]["address"]
    assert all(v["parentFolderId"] == "inbox" for v in msgs["data"]["value"])
    subjects = [v["subject"] for v in filtered["data"]["value"]]
    assert subjects and all("SO-9001" in s for s in subjects)
    dates = [v["receivedDateTime"] for v in filtered["data"]["value"]]
    assert dates == sorted(dates)
    assert set(sel["data"]["value"][0]) <= {"@odata.etag", "id", "subject", "from"} and len(sel["data"]["value"]) == 2
    assert searched["statusCode"] == 200
    assert [e["subject"] for e in view["data"]["value"]] == ["Brennmark escalation call"]
    assert view["data"]["value"][0]["start"] == {"dateTime": "2026-12-07T10:00:00.0000000", "timeZone": "UTC"}
    assert noview["statusCode"] == 400


def test_chat_and_drive_shapes(as_persona, state):
    m = as_persona("plant-manager")
    g = ids_of(state, "M6", "M7")
    chats, msgs, drive, children, item = m.fetch(
        "/me/chats", f"/chats/{g['M6']}/messages", "/me/drive", "/me/drive/root/children", f"/me/drive/items/{g['M7']}"
    )
    msg = msgs["data"]["value"][0]
    assert msg["chatId"] == g["M6"] and msg["from"]["user"]["displayName"] and msg["body"]["content"]
    assert drive["data"]["driveType"] == "business"
    assert [x["name"] for x in children["data"]["value"]] == ["Weekly S&OP 2026-12-02 transcript.vtt"]
    d = item["data"]
    assert d["name"] == "Key account plan FY27, Brennmark.docx" and d["file"]["mimeType"].endswith("document")
    assert d["createdBy"]["user"]["displayName"] == "Sales Lead" and d["size"] > 0


@pytest.mark.parametrize(
    "tool,args",
    [
        ("create_entity", {"parentUrl": "/me/messages", "jsonBody": "{\"subject\": \"x\"}"}),
        ("update_entity", {"entityUrl": "/me/messages/abc", "jsonBody": "{\"subject\": \"x\"}"}),
        ("delete_entity", {"entityUrl": "/me/messages/abc"}),
        ("do_action", {"actionUrl": "/me/sendMail", "jsonBody": "{}"}),
        ("call_function", {"functionUrl": "/me/findMeetingTimes"}),
    ],
)
def test_mutations_blocked_by_policy(as_persona, tool, args):
    res = as_persona("sales-lead").call(tool, **args)
    assert res["isError"] is True
    assert "Blocked by Work IQ tenant policy: mutation operations are disabled (emulator default)" in res["content"][0]["text"]


def test_call_function_read_paths(as_persona):
    m = as_persona("sales-lead")
    res = m.call("call_function", functionUrl="/me/calendarView?startDateTime=2026-12-07T00:00:00Z&endDateTime=2026-12-09T00:00:00Z")
    assert res["isError"] is False and res["structuredContent"]["statusCode"] == 200
    assert len(res["structuredContent"]["data"]["value"]) == 2
    s = m.call("call_function", functionUrl="/me/drive/root/search(q='Brennmark')")
    assert s["isError"] is False and s["structuredContent"]["data"]["value"]


def test_drafts_when_mutations_allowed(pack):
    state = make_state(pack, allow_mutations=True)
    client = TestClient(create_app(state))
    sl, pm = Mcp(client, KEYS["sales-lead"]), Mcp(client, KEYS["plant-manager"])
    body = json.dumps({"subject": "Draft to Brennmark", "toRecipients": [{"emailAddress": {"address": "purchasing.manager@brennmark.example"}}], "body": {"contentType": "text", "content": "Hello"}})
    res = sl.call("create_entity", parentUrl="/me/messages", jsonBody=body)
    assert res["isError"] is False and res["structuredContent"]["statusCode"] == 201
    gid = res["structuredContent"]["data"]["id"]
    assert res["structuredContent"]["data"]["isDraft"] is True
    assert sl.fetch(f"/me/messages/{gid}")[0]["statusCode"] == 200
    assert pm.fetch(f"/me/messages/{gid}")[0]["statusCode"] == 404
    assert sl.call("create_entity", parentUrl="/me/events", jsonBody="{}")["isError"] is True
    assert sl.call("delete_entity", entityUrl=f"/me/messages/{gid}")["isError"] is True


def test_ask_extractive_and_conversation(as_persona):
    m = as_persona("plant-manager")
    first = m.call("ask", question="What did Brennmark ask for in their last email?")
    data = json.loads(first["content"][0]["text"])
    assert set(data) == {"response", "conversationId"} and "2,000" in data["response"]
    second = m.call("ask", question="And who is on quality hold?", conversationId=data["conversationId"])
    data2 = json.loads(second["content"][0]["text"])
    assert data2["conversationId"] == data["conversationId"]
    assert m.call("ask", question="x", agentId="other-agent")["isError"] is True


def test_input_limits(client, as_persona):
    m = as_persona("sales-lead")
    assert m.call("retrieve", query="a" * 2001)["isError"] is True
    assert m.call("fetch", entityUrls=["/me"] * 21)["isError"] is True
    assert m.call("retrieve", query="hello\x07world")["isError"] is True
    big = client.post("/mcp", content=b"{" + b" " * (257 * 1024) + b"}", headers=m.headers())
    assert big.status_code == 413
    cross = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"}, headers=m.headers() | {"Origin": "https://evil.example"})
    assert cross.status_code == 403
    wrong_type = client.post("/mcp", content=b"{}", headers=m.headers() | {"Content-Type": "text/plain"})
    assert wrong_type.status_code == 415
