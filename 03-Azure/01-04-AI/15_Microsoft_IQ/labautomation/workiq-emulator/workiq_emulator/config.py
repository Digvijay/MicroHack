"""Runtime settings read from environment variables (Azure Functions app settings)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

MIN_KEY_LENGTH = 16


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def persona_key_env_name(persona_id: str) -> str:
    return "WORKIQ_KEY_" + persona_id.upper().replace("-", "_")


def _seconds(value: str | None, default: float) -> float:
    try:
        return min(max(float((value or "").strip()), 0.0), 600.0)
    except ValueError:
        return default


@dataclass
class Settings:
    persona_keys: dict[str, str] = field(default_factory=dict)  # persona id -> key
    admin_key: str = ""
    session_secret: str = ""
    dev_mode: bool = False
    allow_mutations: bool = False
    seed_path: str | None = None
    seed: str = "strandvik"
    default_persona: str = "alex"
    allow_chat_write: bool = True
    auto_sam: bool = False
    auto_sam_delay: float = 30.0
    kolvo_thread: str = "W3"
    kolvo_project_endpoint: str = ""
    maria_agent_name: str = "maria-procurement"
    maria_request: str = ""
    public_base_url: str = ""
    foundry_endpoint: str = ""
    foundry_deployment: str = ""
    ignored_keys: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, persona_ids: list[str], env: dict[str, str] | None = None) -> "Settings":
        env = dict(os.environ if env is None else env)
        keys: dict[str, str] = {}
        ignored: list[str] = []
        for pid in persona_ids:
            name = persona_key_env_name(pid)
            value = (env.get(name) or "").strip()
            if not value:
                continue
            if len(value) < MIN_KEY_LENGTH:
                ignored.append(name)
                continue
            keys[pid] = value
        admin = (env.get("WORKIQ_ADMIN_KEY") or "").strip()
        if admin and len(admin) < MIN_KEY_LENGTH:
            ignored.append("WORKIQ_ADMIN_KEY")
            admin = ""
        return cls(
            persona_keys=keys,
            admin_key=admin,
            session_secret=(env.get("WORKIQ_SESSION_SECRET") or "").strip(),
            dev_mode=_truthy(env.get("WORKIQ_DEV_MODE")),
            allow_mutations=_truthy(env.get("WORKIQ_ALLOW_MUTATIONS")),
            seed_path=(env.get("WORKIQ_SEED_PATH") or "").strip() or None,
            seed=(env.get("WORKIQ_SEED") or "").strip().lower() or "strandvik",
            default_persona=(env.get("WORKIQ_DEFAULT_PERSONA") or "").strip() or "alex",
            allow_chat_write=_truthy(env.get("WORKIQ_ALLOW_CHAT_WRITE", "true")),
            auto_sam=_truthy(env.get("WORKIQ_AUTO_SAM")),
            auto_sam_delay=_seconds(env.get("WORKIQ_AUTO_SAM_DELAY_SECONDS"), 30.0),
            kolvo_thread=(env.get("WORKIQ_KOLVO_THREAD") or "").strip() or "W3",
            kolvo_project_endpoint=(env.get("KOLVO_PROJECT_ENDPOINT") or "").strip().rstrip("/"),
            maria_agent_name=(env.get("MARIA_AGENT_NAME") or "").strip() or "maria-procurement",
            maria_request=(env.get("MARIA_REQUEST") or "").strip(),
            public_base_url=(env.get("WORKIQ_PUBLIC_BASE_URL") or "").strip().rstrip("/"),
            foundry_endpoint=(env.get("FOUNDRY_OPENAI_ENDPOINT") or "").strip().rstrip("/"),
            foundry_deployment=(env.get("FOUNDRY_CHAT_DEPLOYMENT") or "").strip(),
            ignored_keys=ignored,
        )

    @property
    def auth_mode(self) -> str:
        """'keys' when persona keys exist, 'dev' for header-based local use, 'misconfigured' otherwise."""
        if self.persona_keys:
            return "keys"
        if self.dev_mode:
            return "dev"
        return "misconfigured"
