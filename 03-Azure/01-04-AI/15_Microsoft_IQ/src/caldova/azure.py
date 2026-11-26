"""Small REST helpers for Azure Resource Manager, Foundry IQ (Azure AI Search), Fabric and OneLake."""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

import httpx
from azure.identity import AzureCliCredential, ChainedTokenCredential, DefaultAzureCredential

from .config import STATE_DIR

ARM = "https://management.azure.com"
FABRIC = "https://api.fabric.microsoft.com/v1"


@lru_cache(maxsize=1)
def credential():
    # Prefer the az login session in the Codespace; fall back to the full default chain.
    return ChainedTokenCredential(AzureCliCredential(process_timeout=30),
                                  DefaultAzureCredential(exclude_cli_credential=True))


def token(scope: str) -> str:
    return credential().get_token(scope).token


class AzureError(RuntimeError):
    pass


def request(method: str, url: str, scope: str, body: Any = None, ok: tuple[int, ...] = (200, 201, 202, 204),
            headers: dict[str, str] | None = None, timeout: float = 180) -> httpx.Response:
    hdrs = {"Authorization": "Bearer " + token(scope), "Content-Type": "application/json"}
    hdrs.update(headers or {})
    content = json.dumps(body) if body is not None and not isinstance(body, (bytes, str)) else body
    for attempt in range(5):
        r = httpx.request(method, url, headers=hdrs, content=content, timeout=timeout)
        if r.status_code in (429, 500, 502, 503) and attempt < 4:
            time.sleep(int(r.headers.get("Retry-After", 2 ** attempt * 3)))
            continue
        break
    if r.status_code not in ok:
        raise AzureError(f"{method} {url.split('?')[0]} failed with HTTP {r.status_code}: {r.text[:1500]}")
    return r


def arm(method: str, path: str, body: Any = None, ok=(200, 201, 202, 204)) -> dict:
    r = request(method, ARM + path, "https://management.azure.com/.default", body, ok)
    return r.json() if r.content else {}


def search(method: str, endpoint: str, path: str, api: str, body: Any = None, ok=(200, 201, 204)) -> dict:
    sep = "&" if "?" in path else "?"
    r = request(method, f"{endpoint}/{path}{sep}api-version={api}", "https://search.azure.com/.default", body, ok)
    return r.json() if r.content else {}


def fabric(method: str, path: str, body: Any = None, ok=(200, 201, 202)) -> dict:
    """Fabric REST call. Long-running operations (202 + Location) are awaited."""
    r = request(method, path if path.startswith("http") else FABRIC + path,
                "https://api.fabric.microsoft.com/.default", body, ok)
    if r.status_code == 202 and r.headers.get("Location"):
        loc = r.headers["Location"]
        deadline = time.time() + 900
        while time.time() < deadline:
            time.sleep(int(r.headers.get("Retry-After", 5)))
            s = request("GET", loc, "https://api.fabric.microsoft.com/.default", ok=(200, 202))
            st = s.json() if s.content else {}
            status = st.get("status")
            if status in ("Succeeded", "Completed") or (s.status_code == 200 and status is None):
                res = httpx.get(loc + "/result", headers={"Authorization": "Bearer " + token(
                    "https://api.fabric.microsoft.com/.default")}, timeout=60)
                return res.json() if res.status_code == 200 and res.content else st
            if status in ("Failed", "Cancelled"):
                raise AzureError("Fabric operation failed: " + json.dumps(st.get("error", st))[:1500])
        raise AzureError("Fabric operation timed out after 15 minutes.")
    return r.json() if r.content else {}


def onelake_upload(workspace_id: str, item_id: str, path: str, data: bytes) -> None:
    base = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{item_id}/{path}"
    scope = "https://storage.azure.com/.default"
    request("PUT", base + "?resource=file&overwrite=true", scope, ok=(200, 201))
    request("PATCH", base + "?action=append&position=0", scope, data, ok=(200, 202),
            headers={"Content-Type": "application/octet-stream"})
    request("PATCH", f"{base}?action=flush&position={len(data)}", scope, ok=(200,))


def blob_upload(account: str, container: str, name: str, data: bytes, content_type: str) -> None:
    url = f"https://{account}.blob.core.windows.net/{container}/{name}"
    request("PUT", url, "https://storage.azure.com/.default", data, ok=(201,),
            headers={"x-ms-blob-type": "BlockBlob", "x-ms-version": "2025-01-05", "Content-Type": content_type})


def blob_container(account: str, container: str) -> None:
    url = f"https://{account}.blob.core.windows.net/{container}?restype=container"
    request("PUT", url, "https://storage.azure.com/.default", ok=(201, 409), headers={"x-ms-version": "2025-01-05"})


# ---- tiny state file so later challenges find what earlier ones created ----------

def load_state() -> dict:
    f = STATE_DIR / "state.json"
    return json.loads(f.read_text()) if f.exists() else {}


def save_state(**values: Any) -> dict:
    STATE_DIR.mkdir(exist_ok=True)
    state = load_state() | values
    (STATE_DIR / "state.json").write_text(json.dumps(state, indent=2))
    return state
