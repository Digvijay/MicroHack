"""Server-rendered, read-only HTML views. Every piece of seeded content is escaped."""

from __future__ import annotations

import time
from html import escape
from urllib.parse import quote

from ..store import Entry, Persona, Store, is_transcript, transcript_lines

BANNER = "Work IQ emulator: simulated Microsoft 365 data for the Caldova hack. Not Microsoft 365."
NAV = [("mail", "Inbox"), ("chats", "Chats"), ("calendar", "Calendar"), ("files", "Files"), ("people", "People"), ("activity", "Agent activity")]


def h(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _q(gid: str) -> str:
    return quote(gid, safe="")


def _when(dt) -> str:
    return dt.strftime("%a %d %b %Y, %H:%M")


def page(title: str, body: str, persona: Persona | None = None, section: str = "") -> str:
    nav = ""
    who = ""
    if persona:
        links = "".join(
            f'<a href="/viewer/{key}"{" aria-current=\"page\"" if key == section else ""}>{h(label)}</a>' for key, label in NAV
        )
        nav = f'<nav class="nav" aria-label="Sections">{links}</nav>'
        who = (
            f'<div class="who"><span>You are signed in as <strong>{h(persona.display_name)}</strong></span>'
            '<form method="post" action="/viewer/logout"><button type="submit" class="link">Sign out</button></form></div>'
        )
    return (
        "<!doctype html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{h(title)} | Work IQ emulator</title>"
        '<link rel="stylesheet" href="/viewer/static/style.css"></head><body>'
        f'<div class="banner" role="note">{h(BANNER)}</div>'
        f'<header class="top"><div class="brand">Caldova Components AB <span class="muted">Work IQ emulator</span></div>{who}</header>'
        f'{nav}<main id="main">{body}</main></body></html>'
    )


def login_page(error: str = "", next_url: str = "/viewer/mail", dev_hint: bool = False) -> str:
    err = f'<p class="error" role="alert">{h(error)}</p>' if error else ""
    hint = (
        '<p class="muted">Local development mode: enter a persona id such as <code>sales-lead</code>.</p>' if dev_hint else ""
    )
    body = (
        '<section class="card narrow"><h1>Sign in</h1>'
        "<p>Paste the Work IQ key you received for your persona. The key decides which mailbox, chats and files you see.</p>"
        f"{err}{hint}"
        '<form method="post" action="/viewer/login">'
        f'<input type="hidden" name="next" value="{h(next_url)}">'
        '<label for="key">Persona key</label>'
        '<input id="key" name="key" type="password" autocomplete="off" required maxlength="512">'
        '<button type="submit">Sign in</button></form></section>'
    )
    return page("Sign in", body)


def _two_pane(list_html: str, detail_html: str) -> str:
    return f'<div class="panes"><div class="list">{list_html}</div><div class="detail">{detail_html}</div></div>'


def _addr(a: dict) -> str:
    name = a.get("name") or a["address"]
    return f'{h(name)} <span class="muted">&lt;{h(a["address"])}&gt;</span>'


def mail_page(store: Store, persona: Persona, selected: Entry | None) -> str:
    entries = sorted(store.visible(persona.id, "email"), key=lambda e: e.dt, reverse=True)
    rows = []
    for e in entries:
        folder = store.email_folder(e, persona.id)
        tag = {"sentitems": "Sent", "drafts": "Draft"}.get(folder, "")
        other = e.item["to"][0] if folder != "inbox" and e.item["to"] else e.item["from"]
        cur = ' aria-current="true"' if selected is e else ""
        rows.append(
            f'<li><a href="/viewer/mail/{_q(e.gid)}"{cur}>'
            f'<span class="row1"><span class="from">{h(other.get("name") or other["address"])}</span>'
            f'<span class="muted">{h(e.dt.strftime("%d %b %H:%M"))}</span></span>'
            f'<span class="subject">{(f"<span class=tag>{tag}</span> " if tag else "")}{h(e.item["subject"])}</span></a></li>'
        )
    list_html = f'<h1>Mail</h1><ul class="items">{"".join(rows) or "<li class=muted>No mail.</li>"}</ul>'
    if selected:
        it = selected.item
        cc = f'<div><span class="label">Cc</span> {"; ".join(_addr(a) for a in it["cc"])}</div>' if it.get("cc") else ""
        detail = (
            f'<article><h2>{h(it["subject"])}</h2>'
            f'<div class="meta"><div><span class="label">From</span> {_addr(it["from"])}</div>'
            f'<div><span class="label">To</span> {"; ".join(_addr(a) for a in it["to"])}</div>{cc}'
            f'<div><span class="label">Date</span> {h(_when(selected.dt))}</div></div>'
            f'<div class="body">{h(it["body"])}</div></article>'
        )
    else:
        detail = '<p class="muted">Select a message to read it.</p>'
    return page("Mail", _two_pane(list_html, detail), persona, "mail")


def chats_page(store: Store, persona: Persona, selected: Entry | None) -> str:
    entries = sorted(store.visible(persona.id, "chat"), key=lambda e: e.extra["messages"][-1]["dt"], reverse=True)
    rows = []
    for e in entries:
        last = e.extra["messages"][-1]
        cur = ' aria-current="true"' if selected is e else ""
        rows.append(
            f'<li><a href="/viewer/chats/{_q(e.gid)}"{cur}><span class="row1"><span class="from">{h(store.chat_title(e))}</span>'
            f'<span class="muted">{h(last["dt"].strftime("%d %b %H:%M"))}</span></span>'
            f'<span class="subject">{h(store.display_name(last["from"]))}: {h(last["text"][:80])}</span></a></li>'
        )
    list_html = f'<h1>Chats</h1><ul class="items">{"".join(rows) or "<li class=muted>No chats.</li>"}</ul>'
    if selected:
        members = ", ".join(store.display_name(m) for m in selected.item["members"])
        msgs = "".join(
            f'<li class="msg"><div class="meta"><strong>{h(store.display_name(m["from"]))}</strong> '
            f'<span class="muted">{h(_when(m["dt"]))}</span></div><div class="body">{h(m["text"])}</div></li>'
            for m in selected.extra["messages"]
        )
        detail = f'<article><h2>{h(store.chat_title(selected))}</h2><p class="muted">Members: {h(members)}</p><ul class="thread">{msgs}</ul></article>'
    else:
        detail = '<p class="muted">Select a chat to read the thread.</p>'
    return page("Chats", _two_pane(list_html, detail), persona, "chats")


def calendar_page(store: Store, persona: Persona, selected: Entry | None) -> str:
    entries = sorted(store.visible(persona.id, "event"), key=lambda e: e.dt)
    rows = []
    for e in entries:
        cur = ' aria-current="true"' if selected is e else ""
        rows.append(
            f'<li><a href="/viewer/calendar/{_q(e.gid)}"{cur}><span class="row1"><span class="from">{h(e.item["subject"])}</span></span>'
            f'<span class="subject">{h(_when(e.dt))} to {h(e.extra["end"].strftime("%H:%M"))}</span></a></li>'
        )
    list_html = f'<h1>Calendar</h1><ul class="items">{"".join(rows) or "<li class=muted>No events.</li>"}</ul>'
    if selected:
        it = selected.item
        attendees = "; ".join(_addr(a) for a in it["attendees"])
        transcript = ""
        tref = it.get("transcriptFile")
        if tref and tref in store.by_item_id and persona.id in store.by_item_id[tref].visible:
            te = store.by_item_id[tref]
            transcript = f'<p><a href="/viewer/files/{_q(te.gid)}">Open the meeting transcript ({h(te.item["name"])})</a></p>'
        detail = (
            f'<article><h2>{h(it["subject"])}</h2><div class="meta">'
            f'<div><span class="label">When</span> {h(_when(selected.dt))} to {h(selected.extra["end"].strftime("%H:%M"))}</div>'
            f'<div><span class="label">Organizer</span> {_addr(it["organizer"])}</div>'
            f'<div><span class="label">Attendees</span> {attendees}</div>'
            f'<div><span class="label">Location</span> {h(it.get("location", ""))}</div></div>'
            f'<div class="body">{h(it.get("body", ""))}</div>{transcript}</article>'
        )
    else:
        detail = '<p class="muted">Select an event to see the details.</p>'
    return page("Calendar", _two_pane(list_html, detail), persona, "calendar")


def files_page(store: Store, persona: Persona, selected: Entry | None) -> str:
    entries = sorted(store.visible(persona.id, "file"), key=lambda e: e.item["name"].lower())
    rows = "".join(
        f'<tr><td><a href="/viewer/files/{_q(e.gid)}">{h(e.item["name"])}</a></td><td>{h(store.drive_owner_label(e))}</td>'
        f'<td>{h(e.dt.strftime("%d %b %Y"))}</td><td class="num">{e.extra["sizeBytes"]:,}</td></tr>'
        for e in entries
    )
    table = (
        '<table><caption class="sr-only">Files you can access</caption><thead><tr><th scope="col">Name</th>'
        '<th scope="col">Location</th><th scope="col">Modified</th><th scope="col" class="num">Size (bytes)</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
    )
    body = f"<h1>Files</h1>{table}"
    if selected:
        it = selected.item
        if is_transcript(it):
            content = "".join(
                f'<p><strong>{h(s)}</strong>: {h(t)}</p>' if s else f"<p>{h(t)}</p>" for s, t in transcript_lines(it["content"])
            )
            content = f'<div class="transcript">{content}</div>'
        else:
            content = f'<div class="body doc">{h(it["content"])}</div>'
        body += (
            f'<article class="card"><h2>{h(it["name"])}</h2><p class="muted">{h(store.drive_owner_label(selected))}, '
            f'author {h(it["createdBy"].get("name") or it["createdBy"]["address"])}, modified {h(_when(selected.dt))}. '
            "The emulator stores the extracted text of each file.</p>"
            f"{content}</article>"
        )
    return page("Files", body, persona, "files")


def people_page(store: Store, persona: Persona) -> str:
    rows = [
        (p.display_name, p.job_title, store.tenant["name"], p.mail) for p in store.personas.values() if p.id != persona.id
    ]
    rows += [
        (e.item["displayName"], e.item["jobTitle"], e.item["companyName"], e.item["mail"]) for e in store.visible(persona.id, "person")
    ]
    body = "".join(f"<tr><td>{h(a)}</td><td>{h(b)}</td><td>{h(c)}</td><td>{h(d)}</td></tr>" for a, b, c, d in rows)
    table = (
        '<table><caption class="sr-only">People</caption><thead><tr><th scope="col">Name</th><th scope="col">Job title</th>'
        f'<th scope="col">Company</th><th scope="col">Email</th></tr></thead><tbody>{body}</tbody></table>'
    )
    return page("People", f"<h1>People</h1>{table}", persona, "people")


def activity_page(persona: Persona, activity: list[dict]) -> str:
    rows = "".join(
        f'<tr><td>{h(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(a["time"])))} UTC</td><td><code>{h(a["tool"])}</code></td>'
        f'<td>{h(a["detail"])}</td><td>{"OK" if a["ok"] else "Error"}</td>'
        f'<td class="ids">{h(", ".join(a["resultIds"][:10]))}</td></tr>'
        for a in activity
    )
    table = (
        '<table><caption class="sr-only">Recent MCP tool calls</caption><thead><tr><th scope="col">Time</th><th scope="col">Tool</th>'
        '<th scope="col">Query or paths</th><th scope="col">Result</th><th scope="col">Result ids</th></tr></thead>'
        f'<tbody>{rows or "<tr><td colspan=5 class=muted>No tool calls yet for this persona.</td></tr>"}</tbody></table>'
    )
    intro = "<p class=\"muted\">The last 50 MCP tool calls made with your persona key. Only metadata is kept, no content.</p>"
    return page("Agent activity", f"<h1>Agent activity</h1>{intro}{table}", persona, "activity")


def message_page(title: str, text: str, status_persona: Persona | None = None) -> str:
    return page(title, f'<section class="card narrow"><h1>{h(title)}</h1><p>{h(text)}</p><p><a href="/viewer">Back</a></p></section>', status_persona)
