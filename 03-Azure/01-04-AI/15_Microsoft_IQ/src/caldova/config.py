"""Settings for the Caldova agent. Values come from src/.env (copied from .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent.parent
HACK_DIR = SRC_DIR.parent
DATA_DIR = HACK_DIR / "data"
STATE_DIR = SRC_DIR / ".caldova"

load_dotenv(SRC_DIR / ".env")

PERSONAS = ("sales-lead", "supply-planner", "quality-head", "plant-manager")
IQS = ("web", "fabric", "foundry", "work")

SEARCH_PREVIEW_API = "2026-11-01-preview"
SEARCH_GA_API = "2026-10-01"
CONNECTIONS_API = "2025-10-01-preview"


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    project_endpoint: str = _env("PROJECT_ENDPOINT")
    subscription_id: str = _env("AZURE_SUBSCRIPTION_ID")
    resource_group: str = _env("AZURE_RESOURCE_GROUP")
    model: str = _env("MODEL_DEPLOYMENT_NAME", "gpt-5.4-mini")
    graph_model: str = _env("GRAPH_MODEL_DEPLOYMENT_NAME", "gpt-5.6-luna")
    embedding_model: str = _env("EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")
    search_endpoint: str = _env("SEARCH_ENDPOINT").rstrip("/")
    storage_account: str = _env("STORAGE_ACCOUNT_NAME")
    storage_container: str = _env("STORAGE_CONTAINER", "caldova-docs")
    fabric_workspace: str = _env("FABRIC_WORKSPACE_NAME", "caldova-iq")
    fabric_capacity: str = _env("FABRIC_CAPACITY_NAME")
    workiq_endpoint: str = _env("WORKIQ_ENDPOINT")
    agent_name: str = _env("AGENT_NAME", "caldova")

    @property
    def account_name(self) -> str:
        # https://<account>.services.ai.azure.com/api/projects/<project>
        return self.project_endpoint.split("//", 1)[-1].split(".", 1)[0]

    @property
    def project_name(self) -> str:
        return self.project_endpoint.rstrip("/").rsplit("/", 1)[-1]

    @property
    def openai_endpoint(self) -> str:
        return f"https://{self.account_name}.openai.azure.com"

    @property
    def project_arm_id(self) -> str:
        return (f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
                f"/providers/Microsoft.CognitiveServices/accounts/{self.account_name}/projects/{self.project_name}")

    @property
    def storage_arm_id(self) -> str:
        return (f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
                f"/providers/Microsoft.Storage/storageAccounts/{self.storage_account}")

    def workiq_key(self, persona: str) -> str:
        return _env("WORKIQ_KEY_" + persona.upper().replace("-", "_"))

    def require(self, *names: str) -> None:
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            env = {"project_endpoint": "PROJECT_ENDPOINT", "subscription_id": "AZURE_SUBSCRIPTION_ID",
                   "resource_group": "AZURE_RESOURCE_GROUP", "search_endpoint": "SEARCH_ENDPOINT",
                   "storage_account": "STORAGE_ACCOUNT_NAME", "workiq_endpoint": "WORKIQ_ENDPOINT"}
            raise SystemExit("Missing settings in src/.env: " + ", ".join(env.get(m, m.upper()) for m in missing)
                             + ". Copy the values from your lab dashboard (Challenge 1).")


settings = Settings()
