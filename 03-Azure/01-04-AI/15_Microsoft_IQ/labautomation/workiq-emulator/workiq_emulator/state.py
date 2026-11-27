"""Process-wide mutable state: the current store, agent activity and ask conversations.

All state is in memory. Deploy with maximumInstanceCount 1 so every request sees the same state."""

from __future__ import annotations

import copy
import os
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import chat
from .config import Settings
from .store import PackError, Persona, Store, load_pack_file, parse_dt, validate_item

ACTIVITY_PER_PERSONA = 50
MAX_CONVERSATIONS = 500
MAX_TURNS = 10
MAX_DRAFTS_PER_PERSONA = 50


@dataclass
class ToolContext:
    state: "AppState"
    store: Store
    persona: Persona
    base_url: str
    # Log records are buffered and emitted by the request handler on the event loop thread.
    # Logging from worker threads can block inside the Azure Functions Python worker.
    logs: list[tuple[int, str]] = field(default_factory=list)


class AppState:
    def __init__(self, settings: Settings | None = None, pack: dict | None = None, clock=time.time):
        self._lock = threading.RLock()
        self.clock = clock
        # Story clock anchor: (real time, story time). None until the first live write in the Kolvo thread.
        self._story_anchor: tuple[float, datetime] | None = None
        if pack is None:
            if settings:
                pack = load_pack_file(settings.seed_path, settings.seed)
            else:
                pack = load_pack_file(os.environ.get("WORKIQ_SEED_PATH") or None, os.environ.get("WORKIQ_SEED") or None)
        self._bundled_pack = copy.deepcopy(pack)
        self.store = Store(copy.deepcopy(pack))
        self.settings = settings or Settings.from_env(list(self.store.personas))
        self._activity: dict[str, deque] = {}
        self._conversations: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
        self.auto_sam = self.settings.auto_sam
        self._pending_sam: list[dict] = []
        self.board_run: dict | None = None
        self.board_lock = threading.Lock()

    # -- store management ---------------------------------------------------

    def replace_pack(self, pack: dict) -> Store:
        new_store = Store(copy.deepcopy(pack))
        with self._lock:
            self.store = new_store
        return new_store

    def reset(self) -> Store:
        with self._lock:
            self._pending_sam.clear()
            self._story_anchor = None
        return self.replace_pack(self._bundled_pack)

    def append_item(self, item: dict) -> Store:
        with self._lock:
            pack = copy.deepcopy(self.store.pack)
            validate_item(item, set(self.store.personas), set(self.store.sites))
            pack["items"].append(item)
            return self.replace_pack(pack)

    # -- chat write and auto-Sam ---------------------------------------------

    def post_chat_message(self, item_id: str, persona_id: str, text: str, via: str | None = None, trigger_auto_sam: bool = True) -> dict:
        """Append a message to a chat item and rebuild the store. Returns the stored message.

        Raises PackError when the thread is full or the message does not validate."""
        with self._lock:
            pack = copy.deepcopy(self.store.pack)
            item = next((it for it in pack["items"] if it["id"] == item_id and it["type"] == "chat"), None)
            if item is None:
                raise PackError(f"chat '{item_id}' does not exist")
            if persona_id not in item["members"]:
                raise PackError(f"'{persona_id}' is not a member of chat '{item_id}'")
            tz = self.store.now.tzinfo
            last = max(parse_dt(m["date"]) for m in item["messages"])
            thread = self._kolvo_thread()
            if self._story_anchor is None and thread is not None and thread.id == item_id:
                # The story clock starts at the first live write in the Kolvo thread, not when the app starts.
                self._story_anchor = (self.clock(), self.store.now)
            when = self.story_now().astimezone(tz).replace(microsecond=0)
            # Graph timestamps have second precision, so keep posts at least one second apart to keep the order.
            when = max(when, last.replace(microsecond=0) + timedelta(seconds=1))
            msg = {"date": when.isoformat(), "from": persona_id, "text": text}
            if via:
                msg["via"] = via
            item["messages"].append(msg)
            validate_item(item, set(self.store.personas), set(self.store.sites))
            store = self.replace_pack(pack)
            entry = store.by_item_id[item_id]
            stored = next(m for m in reversed(entry.extra["messages"]) if m["dt"] == parse_dt(msg["date"]))
            if trigger_auto_sam:
                self._maybe_queue_sam(entry, persona_id, text)
            return stored

    # -- story clock -----------------------------------------------------------

    def story_now(self) -> datetime:
        """Story time: the pack's "now" until the clock is anchored, then real time runs from the anchor."""
        with self._lock:
            if self._story_anchor is None:
                return self.store.now
            real, story = self._story_anchor
            return story + timedelta(seconds=max(0.0, self.clock() - real))

    def story_clock_running(self) -> bool:
        return self._story_anchor is not None

    def set_story_clock(self, when: datetime) -> None:
        """Coach control: the story time is 'when' now, and real time runs from here."""
        with self._lock:
            self._story_anchor = (self.clock(), when)

    def reset_thread(self) -> int:
        """Coach control: remove live posts from the Kolvo thread, cancel auto-Sam and stop the story clock.
        Returns the number of removed messages."""
        with self._lock:
            self._pending_sam.clear()
            self._story_anchor = None
            thread = self._kolvo_thread()
            if thread is None:
                return 0
            original = next((it for it in self._bundled_pack["items"] if it["id"] == thread.id), None)
            if original is None:
                return 0
            pack = copy.deepcopy(self.store.pack)
            removed = 0
            for i, it in enumerate(pack["items"]):
                if it["id"] == thread.id:
                    removed = len(it["messages"]) - len(original["messages"])
                    pack["items"][i] = copy.deepcopy(original)
            self.replace_pack(pack)
            return max(removed, 0)

    def _kolvo_thread(self):
        return chat.kolvo_thread(self.store, self.settings.kolvo_thread)

    def sam_persona(self) -> str | None:
        return chat.find_persona(self.store, "sam")

    def _maybe_queue_sam(self, entry, persona_id: str, text: str) -> None:
        sam = self.sam_persona()
        thread = self._kolvo_thread()
        if not self.auto_sam or sam is None or thread is None or entry.id != thread.id or persona_id == sam:
            return
        if sam not in entry.item["members"]:
            return
        reply = chat.auto_sam_reply(text)
        if reply is None or any(p["item"] == entry.id for p in self._pending_sam):
            return
        self._pending_sam.append({"item": entry.id, "due": self.clock() + self.settings.auto_sam_delay, "text": reply})

    def set_auto_sam(self, on: bool) -> None:
        with self._lock:
            self.auto_sam = on
            if not on:
                self._pending_sam.clear()

    def sam_pending(self, item_id: str) -> bool:
        with self._lock:
            return any(p["item"] == item_id for p in self._pending_sam)

    def tick(self) -> int:
        """Post auto-Sam replies that are due. Called lazily at the start of requests, so no timers are needed."""
        if not self._pending_sam:
            return 0
        posted = 0
        with self._lock:
            now = self.clock()
            due = [p for p in self._pending_sam if p["due"] <= now]
            self._pending_sam = [p for p in self._pending_sam if p["due"] > now]
            sam = self.sam_persona()
            for p in due:
                if sam is None:
                    continue
                try:
                    self.post_chat_message(p["item"], sam, p["text"], trigger_auto_sam=False)
                    posted += 1
                except PackError:
                    pass
        return posted

    def count_drafts(self, persona_id: str) -> int:
        return sum(
            1
            for e in self.store.visible(persona_id, "email")
            if e.item.get("folder") == "drafts" and e.visible == frozenset([persona_id])
        )

    # -- agent activity -----------------------------------------------------

    def record_activity(self, persona_id: str, tool: str, detail: str, result_ids: list[str], ok: bool) -> None:
        with self._lock:
            log = self._activity.setdefault(persona_id, deque(maxlen=ACTIVITY_PER_PERSONA))
            log.appendleft(
                {"time": time.time(), "tool": tool, "detail": detail[:300], "resultIds": result_ids[:20], "ok": ok}
            )

    def activity(self, persona_id: str) -> list[dict]:
        with self._lock:
            return list(self._activity.get(persona_id, []))

    # -- ask conversations --------------------------------------------------

    def conversation(self, persona_id: str, conv_id: str) -> list[dict]:
        with self._lock:
            return list(self._conversations.get((persona_id, conv_id), []))

    def append_turn(self, persona_id: str, conv_id: str, question: str, answer: str) -> None:
        key = (persona_id, conv_id)
        with self._lock:
            turns = self._conversations.pop(key, [])
            turns.append({"question": question[:4000], "answer": answer[:8000]})
            self._conversations[key] = turns[-MAX_TURNS:]
            while len(self._conversations) > MAX_CONVERSATIONS:
                self._conversations.popitem(last=False)
