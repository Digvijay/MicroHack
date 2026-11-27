"""Shape store entries as Microsoft Graph v1.0 style JSON objects."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from .store import Entry, Persona, Store, drive_id, iso_utc, stable_guid

GRAPH_CONTEXT = "https://graph.microsoft.com/v1.0/$metadata#"


def _etag(gid: str) -> str:
    return f'W/"{gid[-24:]}"'


def viewer_url(base: str, kind: str, gid: str) -> str:
    section = {"email": "mail", "event": "calendar", "chat": "chats", "file": "files", "person": "people"}[kind]
    return f"{base}/viewer/{section}/{quote(gid, safe='')}"


def _addr(a: dict) -> dict:
    return {"emailAddress": {"name": a.get("name", ""), "address": a["address"]}}


def _preview(text: str, limit: int = 255) -> str:
    flat = " ".join(text.split())
    return flat[:limit]


def user(store: Store, p: Persona) -> dict:
    return {
        "@odata.context": GRAPH_CONTEXT + "users/$entity",
        "id": p.user_id,
        "displayName": p.display_name,
        "givenName": None,
        "surname": None,
        "jobTitle": p.job_title,
        "mail": p.mail,
        "userPrincipalName": p.mail,
        "department": p.department or None,
        "officeLocation": p.office_location or None,
        "businessPhones": [],
        "mobilePhone": None,
        "preferredLanguage": "en-US",
    }


def message(store: Store, e: Entry, persona_id: str, base: str) -> dict:
    it = e.item
    folder = store.email_folder(e, persona_id)
    is_draft = folder == "drafts"
    sent = iso_utc(e.dt)
    return {
        "@odata.etag": _etag(e.gid),
        "id": e.gid,
        "createdDateTime": sent,
        "lastModifiedDateTime": sent,
        "receivedDateTime": sent,
        "sentDateTime": None if is_draft else sent,
        "hasAttachments": False,
        "internetMessageId": f"<{e.gid[-20:]}@{store.tenant['domain']}>",
        "subject": it["subject"],
        "bodyPreview": _preview(it["body"]),
        "importance": it.get("importance", "normal"),
        "parentFolderId": folder,
        "conversationId": e.extra["conversationId"],
        "isRead": it.get("isRead", folder != "inbox"),
        "isDraft": is_draft,
        "webLink": viewer_url(base, "email", e.gid),
        "inferenceClassification": "focused",
        "body": {"contentType": "text", "content": it["body"]},
        "sender": _addr(it["from"]),
        "from": _addr(it["from"]),
        "toRecipients": [_addr(a) for a in it["to"]],
        "ccRecipients": [_addr(a) for a in it.get("cc", [])],
        "bccRecipients": [],
        "replyTo": [],
        "flag": {"flagStatus": "notFlagged"},
    }


def _graph_dt(dt: datetime) -> dict:
    return {"dateTime": dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000"), "timeZone": "UTC"}


def event(store: Store, e: Entry, persona_id: str, base: str) -> dict:
    it = e.item
    online = it.get("isOnlineMeeting", True)
    transcript = None
    tref = it.get("transcriptFile")
    if tref and tref in store.by_item_id:
        te = store.by_item_id[tref]
        if persona_id in te.visible:
            transcript = f"/drives/{te.extra['driveId']}/items/{te.gid}"
    data = {
        "@odata.etag": _etag(e.gid),
        "id": e.gid,
        "createdDateTime": iso_utc(e.dt),
        "lastModifiedDateTime": iso_utc(e.dt),
        "subject": it["subject"],
        "bodyPreview": _preview(it.get("body", "")),
        "body": {"contentType": "text", "content": it.get("body", "")},
        "importance": "normal",
        "isAllDay": False,
        "isCancelled": False,
        "isOrganizer": it["organizer"]["address"].lower() == store.personas[persona_id].mail.lower(),
        "start": _graph_dt(e.dt),
        "end": _graph_dt(e.extra["end"]),
        "location": {"displayName": it.get("location", ""), "locationType": "default"},
        "isOnlineMeeting": online,
        "onlineMeetingProvider": "teamsForBusiness" if online else "unknown",
        "onlineMeeting": {"joinUrl": f"{base}/viewer/calendar/{quote(e.gid, safe='')}"} if online else None,
        "organizer": _addr(it["organizer"]),
        "attendees": [
            {"type": "required", "status": {"response": "accepted", "time": iso_utc(e.dt)}, **_addr(a)}
            for a in it["attendees"]
        ],
        "webLink": viewer_url(base, "event", e.gid),
    }
    if transcript:
        # Emulator extension: where the meeting transcript file lives.
        data["transcriptEntityUrl"] = transcript
    return data


def chat(store: Store, e: Entry, base: str) -> dict:
    last = e.extra["messages"][-1]["dt"]
    return {
        "id": e.gid,
        "topic": e.item.get("topic"),
        "createdDateTime": iso_utc(e.dt),
        "lastUpdatedDateTime": iso_utc(last),
        "chatType": e.item["chatType"],
        "webUrl": viewer_url(base, "chat", e.gid),
        "tenantId": store.tenant["tenantId"],
        "members": [
            {"displayName": store.display_name(m), "userId": store.personas[m].user_id, "email": store.personas[m].mail}
            for m in e.item["members"]
        ],
    }


def chat_message(store: Store, e: Entry, m: dict) -> dict:
    p = store.personas[m["from"]]
    ts = iso_utc(m["dt"])
    application = None
    if m.get("via") == "agent":
        # Emulator convention for agent posts: the app is the agent, the user is the person it acts for.
        application = {
            "@odata.type": "#microsoft.graph.teamworkApplicationIdentity",
            "id": stable_guid("agent", m["from"]),
            "displayName": f"{p.display_name}'s agent",
            "applicationIdentityType": "bot",
        }
    return {
        "id": m["id"],
        "replyToId": None,
        "etag": m["id"],
        "messageType": "message",
        "createdDateTime": ts,
        "lastModifiedDateTime": ts,
        "lastEditedDateTime": None,
        "deletedDateTime": None,
        "subject": None,
        "summary": None,
        "chatId": e.gid,
        "importance": "normal",
        "locale": "en-us",
        "webUrl": None,
        "channelIdentity": None,
        "from": {
            "application": application,
            "device": None,
            "user": {
                "@odata.type": "#microsoft.graph.teamworkUserIdentity",
                "id": p.user_id,
                "displayName": store.sender_label(m),
                "userIdentityType": "aadUser",
                "tenantId": store.tenant["tenantId"],
            },
        },
        "body": {"contentType": "text", "content": m["text"]},
        "attachments": [],
        "mentions": [],
        "reactions": [],
    }


def drive(store: Store, drive_key: str, base: str) -> dict:
    kind, _, key = drive_key.partition(":")
    if kind == "onedrive":
        p = store.personas[key]
        return {
            "id": drive_id(drive_key),
            "driveType": "business",
            "name": "OneDrive",
            "owner": {"user": {"id": p.user_id, "displayName": p.display_name, "email": p.mail}},
            "webUrl": f"{base}/viewer/files",
        }
    site = store.sites[key]
    return {
        "id": site["driveId"],
        "driveType": "documentLibrary",
        "name": "Documents",
        "owner": {"group": {"displayName": site["displayName"]}},
        "webUrl": f"{base}/viewer/files",
    }


def drive_item(store: Store, e: Entry, base: str) -> dict:
    it = e.item
    kind, _, key = e.extra["driveKey"].partition(":")
    parent = {"driveId": e.extra["driveId"], "driveType": "business" if kind == "onedrive" else "documentLibrary", "path": "/drive/root:"}
    if kind == "site":
        parent["siteId"] = store.sites[key]["siteId"]
    by = {"user": {"displayName": it["createdBy"].get("name", ""), "email": it["createdBy"]["address"]}}
    ts = iso_utc(e.dt)
    return {
        "@odata.etag": _etag(e.gid),
        "id": e.gid,
        "name": it["name"],
        "webUrl": viewer_url(base, "file", e.gid),
        "size": e.extra["sizeBytes"],
        "createdDateTime": ts,
        "lastModifiedDateTime": ts,
        "createdBy": by,
        "lastModifiedBy": by,
        "parentReference": parent,
        "file": {"mimeType": it["mimeType"]},
        "fileSystemInfo": {"createdDateTime": ts, "lastModifiedDateTime": ts},
    }


def person_from_persona(store: Store, p: Persona) -> dict:
    return {
        "id": p.user_id,
        "displayName": p.display_name,
        "givenName": None,
        "surname": None,
        "jobTitle": p.job_title,
        "companyName": store.tenant["name"],
        "department": p.department or None,
        "officeLocation": p.office_location or None,
        "userPrincipalName": p.mail,
        "scoredEmailAddresses": [{"address": p.mail, "relevanceScore": 10.0}],
        "phones": [],
        "personType": {"class": "Person", "subclass": "OrganizationUser"},
    }


def person_from_entry(store: Store, e: Entry) -> dict:
    it = e.item
    return {
        "id": e.gid,
        "displayName": it["displayName"],
        "givenName": None,
        "surname": None,
        "jobTitle": it["jobTitle"],
        "companyName": it["companyName"],
        "department": it.get("department"),
        "officeLocation": None,
        "userPrincipalName": None,
        "scoredEmailAddresses": [{"address": it["mail"], "relevanceScore": 8.0}],
        "phones": [{"type": "business", "number": it["phone"]}] if it.get("phone") else [],
        "personType": {"class": "Person", "subclass": "PersonalContact"},
    }
