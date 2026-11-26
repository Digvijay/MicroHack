"""Process-wide mutable state: the current store, agent activity and ask conversations.

All state is in memory. Deploy with maximumInstanceCount 1 so every request sees the same state."""

from __future__ import annotations

import copy
import os
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

from .config import Settings
from .store import Persona, Store, load_pack_file, validate_item

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
    def __init__(self, settings: Settings | None = None, pack: dict | None = None):
        self._lock = threading.RLock()
        if pack is None:
            seed_path = settings.seed_path if settings else (os.environ.get("WORKIQ_SEED_PATH") or None)
            pack = load_pack_file(seed_path)
        self._bundled_pack = copy.deepcopy(pack)
        self.store = Store(copy.deepcopy(pack))
        self.settings = settings or Settings.from_env(list(self.store.personas))
        self._activity: dict[str, deque] = {}
        self._conversations: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()

    # -- store management ---------------------------------------------------

    def replace_pack(self, pack: dict) -> Store:
        new_store = Store(copy.deepcopy(pack))
        with self._lock:
            self.store = new_store
        return new_store

    def reset(self) -> Store:
        return self.replace_pack(self._bundled_pack)

    def append_item(self, item: dict) -> Store:
        with self._lock:
            pack = copy.deepcopy(self.store.pack)
            validate_item(item, set(self.store.personas), set(self.store.sites))
            pack["items"].append(item)
            return self.replace_pack(pack)

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
