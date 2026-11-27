"""Server-rendered, read-only HTML views. Every piece of seeded content is escaped."""

from __future__ import annotations

import time
from html import escape
from urllib.parse import quote

from ..store import Entry, Persona, Store, is_transcript, transcript_lines

BANNER = "Work IQ emulator: simulated Microsoft 365 data for the Strandvik hack. Not Microsoft 365."
NAV = [("mail", "Inbox"), ("chats", "Chats"), ("calendar", "Calendar"), ("files", "Files"), ("people", "People"), ("activity", "Agent activity"), ("board", "Kolvo board")]


def h(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _q(gid: str) -> str:
    return quote(gid, safe="")


def _when(dt, store: Store) -> str:
    """Weekday and clock time, never a calendar date: the story is not tied to a date."""
    now = store.now
    d = dt.astimezone(now.tzinfo)
    days = (now.date() - d.date()).days
    label = d.strftime("%a %H:%M")
    if abs(days) < 7:
        return label
    weeks = max(1, round(abs(days) / 7))
    return f"{label}, {weeks} week{'s' if weeks != 1 else ''} {'ago' if days > 0 else 'ahead'}"


def _local(store: Store, dt):
    return dt.astimezone(store.now.tzinfo)


def page(title: str, body: str, persona: Persona | None = None, section: str = "", script: str = "") -> str:
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
        f'<header class="top"><div class="brand">Strandvik Drives AB <span class="muted">Work IQ emulator</span></div>{who}</header>'
        f'{nav}<main id="main">{body}</main>{script}</body></html>'
    )


def login_page(error: str = "", next_url: str = "/viewer/mail", dev_hint: bool = False) -> str:
    err = f'<p class="error" role="alert">{h(error)}</p>' if error else ""
    hint = (
        '<p class="muted">Local development mode: enter a persona id such as <code>alex</code> or <code>sam</code>.</p>' if dev_hint else ""
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
            f'<span class="muted">{h(_when(e.dt, store))}</span></span>'
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
            f'<div><span class="label">Date</span> {h(_when(selected.dt, store))}</div></div>'
            f'<div class="body">{h(it["body"])}</div></article>'
        )
    else:
        detail = '<p class="muted">Select a message to read it.</p>'
    return page("Mail", _two_pane(list_html, detail), persona, "mail")


def chats_page(store: Store, persona: Persona, selected: Entry | None, extras: dict | None = None) -> str:
    extras = extras or {}
    entries = sorted(store.visible(persona.id, "chat"), key=lambda e: e.extra["messages"][-1]["dt"], reverse=True)
    rows = []
    for e in entries:
        last = e.extra["messages"][-1]
        cur = ' aria-current="true"' if selected is e else ""
        rows.append(
            f'<li><a href="/viewer/chats/{_q(e.gid)}"{cur}><span class="row1"><span class="from">{h(store.chat_title(e))}</span>'
            f'<span class="muted">{h(_when(last["dt"], store))}</span></span>'
            f'<span class="subject">{h(store.sender_label(last))}: {h(last["text"][:80])}</span></a></li>'
        )
    list_html = f'<h1>Chats</h1><ul class="items">{"".join(rows) or "<li class=muted>No chats.</li>"}</ul>'
    script = ""
    if selected:
        members = ", ".join(store.display_name(m) for m in selected.item["members"])
        msgs = "".join(_chat_li(store, m) for m in selected.extra["messages"])
        options = "".join(
            f'<option value="{h(m)}"{" selected" if m == persona.id else ""}>{h(store.display_name(m))}</option>'
            for m in selected.item["members"]
        )
        is_kolvo = extras.get("kolvo_gid") == selected.gid
        auto = ""
        if is_kolvo:
            on = bool(extras.get("auto_sam"))
            auto = (
                '<form method="post" action="/viewer/auto-sam" class="inline">'
                f'<input type="hidden" name="next" value="/viewer/chats/{h(_q(selected.gid))}">'
                f'<input type="hidden" name="on" value="{"false" if on else "true"}">'
                f'<span>Auto-Sam is <strong id="auto-sam-state">{"on" if on else "off"}</strong>.</span> '
                f'<button type="submit" class="secondary">{"Turn auto-Sam off" if on else "Turn auto-Sam on"}</button></form>'
                f'<p class="muted">Story time: <strong id="story-time">{h(extras.get("story_time", ""))}</strong>. '
                'Coaches can set it on the <a href="/viewer/coach">coach page</a>.</p>'
            )
        reply = (
            '<form method="post" action="/viewer/reply" class="reply">'
            f'<input type="hidden" name="chat" value="{h(selected.gid)}">'
            '<label for="as">Post as</label>'
            f'<select id="as" name="as">{options}</select>'
            '<label for="text">Message</label>'
            '<textarea id="text" name="text" rows="3" maxlength="4000" required></textarea>'
            '<button type="submit">Post to the thread</button></form>'
        )
        detail = (
            f'<article><h2>{h(store.chat_title(selected))}</h2><p class="muted">Members: {h(members)}</p>{auto}'
            f'<ul class="thread" id="thread" aria-live="polite" data-src="/viewer/api/chat?id={h(_q(selected.gid))}">{msgs}</ul>'
            f'<p class="muted" id="thread-status">This thread refreshes every 4 seconds.</p>{reply}</article>'
        )
        script = '<script src="/viewer/static/viewer.js" defer></script>'
    else:
        detail = '<p class="muted">Select a chat to read the thread.</p>'
    return page("Chats", _two_pane(list_html, detail), persona, "chats", script)


def _chat_li(store: Store, m: dict) -> str:
    agent = ' agent' if m.get("via") == "agent" else ""
    return (
        f'<li class="msg{agent}"><div class="meta"><strong>{h(store.sender_label(m))}</strong> '
        f'<span class="muted">{h(_when(m["dt"], store))}</span></div><div class="body">{h(m["text"])}</div></li>'
    )


def chat_json(store: Store, e: Entry, auto_sam: bool, pending: bool, story_time: str = "") -> dict:
    return {
        "chatId": e.gid,
        "storyTime": story_time,
        "autoSam": auto_sam,
        "samTyping": pending,
        "messages": [
            {"id": m["id"], "from": store.sender_label(m), "agent": m.get("via") == "agent",
             "time": _when(m["dt"], store), "text": m["text"]}
            for m in e.extra["messages"]
        ],
    }


def calendar_page(store: Store, persona: Persona, selected: Entry | None) -> str:
    entries = sorted(store.visible(persona.id, "event"), key=lambda e: e.dt)
    rows = []
    for e in entries:
        cur = ' aria-current="true"' if selected is e else ""
        rows.append(
            f'<li><a href="/viewer/calendar/{_q(e.gid)}"{cur}><span class="row1"><span class="from">{h(e.item["subject"])}</span></span>'
            f'<span class="subject">{h(_when(e.dt, store))} to {h(e.extra["end"].strftime("%H:%M"))}</span></a></li>'
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
            f'<div><span class="label">When</span> {h(_when(selected.dt, store))} to {h(selected.extra["end"].strftime("%H:%M"))}</div>'
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
        f'<td>{h(_when(e.dt, store))}</td><td class="num">{e.extra["sizeBytes"]:,}</td></tr>'
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
            f'author {h(it["createdBy"].get("name") or it["createdBy"]["address"])}, modified {h(_when(selected.dt, store))}. '
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


SCORE_LABELS = [
    ("answered", "Answered"),
    ("inTime", "Answered in time"),
    ("holdsUnit", "Grounded, holds the unit"),
    ("quoteOnly", "Respects quote only"),
    ("personConfirms", "Final confirmation by a person"),
]
STATUS_LABELS = {"answered": "Answered", "deferred": "Deferred", "error": "Error", "no answer": "No answer"}


def _badge(value: str) -> str:
    cls = {"Yes": "yes", "No": "no"}.get(value, "na")
    return f'<span class="badge {cls}">{h(value)}</span>'


def board_page(persona: Persona, run: dict, configured: bool, agent_name: str, request_text: str) -> str:
    status = run.get("status", "idle")
    suppliers = run.get("suppliers") or []
    cards = []
    for s in suppliers:
        st = s["status"]
        cards.append(
            f'<section class="supplier {h(st.replace(" ", "-"))}" aria-labelledby="sup-{h(s["key"])}">'
            f'<h2 id="sup-{h(s["key"])}">{h(s["name"])}</h2>'
            f'<p class="status">Status: <strong>{h(STATUS_LABELS.get(st, st))}</strong>. Time to answer: {h(s["timeToAnswer"])}</p>'
            f'<div class="body answer">{h(s["answer"])}</div></section>'
        )
    if not cards:
        cards.append('<p class="muted">No run yet. Press "Run 02:13" to send Maria\'s request to the three suppliers.</p>')
    score_rows = "".join(
        f'<tr><th scope="row">{h(s["name"])}</th>' + "".join(f"<td>{_badge(s['score'][k])}</td>" for k, _ in SCORE_LABELS) + "</tr>"
        for s in suppliers
    )
    scorecard = ""
    if suppliers:
        heads = "".join(f'<th scope="col">{h(label)}</th>' for _, label in SCORE_LABELS)
        scorecard = (
            '<h2>Scorecard</h2><table class="scorecard"><caption class="sr-only">Supplier scorecard</caption>'
            f'<thead><tr><th scope="col">Supplier</th>{heads}</tr></thead><tbody>{score_rows}</tbody></table>'
            '<p class="muted">Scores are simple keyword checks on each answer. Judge them yourself, too.</p>'
        )
    final = f'<h2>Maria\'s agent, final message</h2><div class="card body">{h(run["final"])}</div>' if run.get("final") else ""
    error = f'<p class="error" role="alert">{h(run["error"])}</p>' if run.get("error") else ""
    if run.get("hint"):
        error += f'<p class="card hint"><strong>What this means:</strong> {h(run["hint"])}</p>'
    when = ""
    if run.get("started"):
        when = f' Last run started {h(time.strftime("%H:%M:%S", time.gmtime(run["started"])))} UTC.'
    state_text = {"idle": "No run yet.", "running": "Running: Maria's agent is asking the suppliers. This takes 30 to 90 seconds.",
                  "done": "Done.", "error": "The run failed."}.get(status, status)
    disabled = "" if configured and status != "running" else " disabled"
    hint = "" if configured else '<p class="error">KOLVO_PROJECT_ENDPOINT is not set, so the board cannot run.</p>'
    body = (
        '<div class="board">'
        "<h1>Kolvo AB, procurement board</h1>"
        f'<div class="card request"><h2>02:13, Maria\'s request</h2><p class="muted">Sent by agent <code>{h(agent_name)}</code> on behalf of Maria, production manager.</p>'
        f'<div class="body">{h(run.get("request") or request_text)}</div></div>'
        f'<form method="post" action="/viewer/board/run" id="run-form" class="run"><button type="submit" id="run-button"{disabled}>Run 02:13</button>'
        f'<span id="board-status" role="status" data-status="{h(status)}" data-run="{h(run.get("id", ""))}">{h(state_text)}{when}</span></form>'
        f"{hint}{error}"
        f'<div class="suppliers">{"".join(cards)}</div>{scorecard}{final}</div>'
    )
    return page("Kolvo board", body, persona, "board", '<script src="/viewer/static/viewer.js" defer></script>')


def coach_page(persona: Persona | None, story_time: str, running: bool, notice: str = "", error: str = "") -> str:
    note = f'<p class="card" role="status">{h(notice)}</p>' if notice else ""
    err = f'<p class="error" role="alert">{h(error)}</p>' if error else ""
    state = "running from the first live post" if running else "stopped, it starts at the first live post in the Kolvo thread"
    key_field = (
        '<label for="{id}">Admin key</label>'
        '<input id="{id}" name="admin_key" type="password" autocomplete="off" required maxlength="512">'
    )
    body = (
        '<section class="card narrow wide"><h1>Coach controls</h1>'
        f"{note}{err}"
        f'<p>Story time now: <strong>{h(story_time)}</strong> (clock {h(state)}).</p>'
        "<p class=\"muted\">Live posts in the Kolvo thread are stamped with the story time. Set it to 03:52 before Sam's challenge "
        "and to 07:30 before Alex makes the call. Both actions need the lab admin key (WORKIQ_ADMIN_KEY).</p>"
        '<form method="post" action="/viewer/coach/clock"><h2>Set the story clock</h2>'
        '<label for="time">Story time, HH:MM on the night of the story (Tuesday)</label>'
        '<input id="time" name="time" type="text" inputmode="numeric" placeholder="07:30" required maxlength="40">'
        + key_field.format(id="key-clock")
        + '<button type="submit">Set the story clock</button></form>'
        '<form method="post" action="/viewer/coach/reset-thread" class="reply"><h2>Reset the Kolvo thread</h2>'
        "<p>Removes every live post (agents and people), cancels a pending auto-Sam reply and stops the story clock.</p>"
        + key_field.format(id="key-reset")
        + '<button type="submit">Reset the thread</button></form></section>'
    )
    return page("Coach controls", body, persona, "")
