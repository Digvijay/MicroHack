# Work IQ emulator

The Work IQ emulator gives every hack participant a private, simulated Microsoft 365 work context for the Caldova scenario. It speaks the same MCP contract as Work IQ, so agent code written against the emulator also works against production Work IQ. Only the URL and the auth header change.

| | Production Work IQ | Emulator |
|---|---|---|
| Endpoint | `https://workiq.svc.cloud.microsoft/mcp` | `https://<function-app>/mcp` |
| Auth | Entra token with `WorkIQAgent.Ask` | `Authorization: Bearer <persona key>` |
| Data | Your Microsoft 365 tenant | `seed/caldova.json` (items M1 to M8 from `walkthrough/scenario-facts.md`, plus distractors) |

Why an emulator: real Work IQ needs Microsoft 365 Copilot licenses, Copilot billing and tenant admin consent. The hackathon tenant does not have them.

## What it is

* An Azure Functions app (Flex Consumption, Python 3.12). One HTTP-triggered ASGI function (Starlette) serves every route.
* `POST /mcp`: MCP streamable HTTP, JSON-RPC 2.0, stateless JSON responses. Methods: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
* `GET /viewer`: a read-only web view of the persona's mailbox, chats, calendar, files, people and recent agent tool calls.
* `GET /healthz`: `{"status":"ok","items":N}`, no auth.
* `/admin/*`: coach endpoints to replace, extend, reset or export the scenario pack.

## Personas and keys

Each persona has its own key. A key maps to exactly one persona. There is no persona switcher.

| Persona id | Display name | App setting for the key |
|---|---|---|
| `sales-lead` | Sales Lead | `WORKIQ_KEY_SALES_LEAD` |
| `supply-planner` | Supply Planner | `WORKIQ_KEY_SUPPLY_PLANNER` |
| `quality-head` | Quality Head | `WORKIQ_KEY_QUALITY_HEAD` |
| `plant-manager` | Plant Manager | `WORKIQ_KEY_PLANT_MANAGER` |

Every seeded item has a `visibleTo` list. `retrieve`, `fetch`, `fetch_blob`, `ask` and the viewer only return items that the calling persona can see. This is the main teaching point: the Sales Lead cannot see the quality hold chat (M3) or the port closure email (M4), so an agent running as the Sales Lead cannot know that the backup supplier is blocked. The Plant Manager (capstone persona) sees M1, M2, M3, M5 (forwarded), M6, M7 and M8.

## Contract coverage

| Tool | Emulated | Notes |
|---|---|---|
| `retrieve` | Yes | `structuredContent["application/vnd.ms-workiq.retrieval"]` with `results[]` (`id`, `markdown`, `resourceId`, `webUrl`, `entityUrl`, `entityType`, `contentProtection`, `resourceMetadata`, plus `chatId`/`messageId` or `driveId`/`itemId`, `relevanceScore`), `resultCount`, `searchMetadata.searchTerms`, `stoppedReason`, and `@workiq.untrustedContent`. Capabilities `Email`, `TeamsMessages`, `Meetings` (events and transcripts), `OneDriveAndSharePoint`, `People`. `GraphConnectors` needs strategy `copilot` and returns nothing. `Dataverse` is rejected. |
| `fetch` | Yes | Graph v1.0 shapes for `/me`, `/me/messages`, `/me/mailFolders/{inbox,sentitems,drafts}/messages`, `/me/events`, `/me/calendarView`, `/me/chats`, `/chats/{id}/messages`, `/me/drive`, `/me/drive/root/children`, `/me/drive/items/{id}`, `/drives/{id}/items/{id}`, `/sites/{id}/drive/root/children`, `/me/people`, `/users/{id}` and more (see `search_paths`). `$top` (default 25, maximum 100), `$select`, `$filter` (eq, ne, gt, ge, lt, le, contains, startswith, endswith, joined with `and`), `$orderby`, `$search`, `$count`. Chat messages are capped at 10. `$skip` and `$skiptoken` return 400. Paths outside `/me/`, `/users/`, `/sites/`, `/chats/`, `/drives/` return 403, and so do `/authentication/` and `/servicePrincipals/`. Unknown paths return a 404 entry. |
| `fetch_blob` | Yes | `/drives/{id}/items/{id}/content` and `/me/drive/items/{id}/content`. Returns the stored text of the file. |
| `ask` | Yes | Runs retrieval for the persona. If `FOUNDRY_OPENAI_ENDPOINT` and `FOUNDRY_CHAT_DEPLOYMENT` are set, the app calls Azure OpenAI chat completions with its managed identity and returns a grounded answer with `[^hN]` citations. Otherwise it returns an extractive list of the best matches. Conversations are kept in memory per persona and `conversationId`. |
| `list_agents` | Yes | Returns the built-in `bizchat-as-gpt-scenario` agent only. |
| `search_paths`, `get_schema` | Yes | Lists the emulated paths. Returns small JSON Schemas (or TypeScript) for message, event, chat, chatMessage, driveItem, person and user. |
| `create_entity`, `update_entity`, `delete_entity`, `do_action` | Policy-blocked | Same as a default tenant: `isError: true` with "Blocked by Work IQ tenant policy: mutation operations are disabled (emulator default)". With `WORKIQ_ALLOW_MUTATIONS=true`, `create_entity` on `/me/messages` creates a draft that only the persona can see. |
| `call_function` | Partly | Read functions `/me/calendarView` and `/me/drive/root/search(q='...')` succeed. Everything else is policy-blocked. |

Tool execution errors are returned with HTTP 200 and `isError: true`. JSON-RPC errors are used only for malformed requests, unknown methods and unknown tools.

### Known differences from production Work IQ

* `retrieve` puts a serialized copy of `structuredContent` in the MCP `content` text block (recommended by the MCP spec for older clients). Production may return an empty `content` array. Always read `structuredContent`.
* `strategy` is accepted and validated, but `grounding` and `copilot` behave the same.
* Capability scope fields (`items_by_url`, `shared_mailbox`, `folders`, `urls`) are accepted and ignored.
* `entityType` for files is `DriveItem` and for email is `Message`.
* Message and event bodies are plain text (`contentType: "text"`). Times are returned in UTC.
* `fetch_blob` returns the stored text of a document (`text/plain`), not the binary Office or PDF file. `format` conversion is not supported.
* No `@odata.nextLink` is returned, because `$skip` is blocked anyway.
* Events carry an extra `transcriptEntityUrl` field when the persona can see the meeting transcript.
* The `query` argument of `fetch` is accepted but no sanitization runs.

### What is not emulated

* The Microsoft 365 semantic index. Ranking is a small BM25 over subject, body, title and transcript text with accent-insensitive matching.
* The real permissions model. Visibility is a static `visibleTo` list per item.
* Copilot reasoning and orchestration. `ask` is a single model call over the top hits.
* Untrusted-content sanitization (XPIA). The seed contains one deliberate injection line in a distractor email ("AI assistant: ignore previous instructions...") so coaches can discuss how agents must treat retrieved content as data. The viewer renders it as escaped text.
* Live meetings, presence, sending mail, Graph connectors, Dataverse and sensitivity labels.

## Run it locally

```powershell
cd labautomation/workiq-emulator
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
# Microsoft corp network: add --default-index <your internal PyPI proxy>

# Option A: local development without keys. Send X-WorkIQ-Persona: <persona id>.
$env:WORKIQ_DEV_MODE = 'true'
# Option B: keys, like in Azure (at least 16 characters each).
$env:WORKIQ_KEY_SALES_LEAD = '<random secret>'
$env:WORKIQ_ADMIN_KEY = '<random secret>'

.venv/Scripts/python.exe -m uvicorn workiq_emulator.app:create_app --factory --port 7071
```

`func start` (Azure Functions Core Tools) also works, because `function_app.py` wraps the same ASGI app.

Smoke test with the official MCP Python client:

```powershell
.venv/Scripts/python.exe scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --key <persona key>
.venv/Scripts/python.exe scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --persona plant-manager   # dev mode
```

Run the tests:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

## Settings

| Setting | Purpose |
|---|---|
| `WORKIQ_KEY_<PERSONA>` | Persona key, for example `WORKIQ_KEY_PLANT_MANAGER`. Keys shorter than 16 characters are ignored. |
| `WORKIQ_ADMIN_KEY` | Key for `/admin/*`. Admin endpoints are disabled when it is not set. |
| `WORKIQ_SESSION_SECRET` | HMAC secret for viewer sessions. Derived from the admin key when not set. |
| `WORKIQ_DEV_MODE` | `true` allows `X-WorkIQ-Persona` when no persona keys exist. Without keys and without dev mode, `/mcp` and `/viewer` return 503. |
| `WORKIQ_ALLOW_MUTATIONS` | `true` lets `create_entity` create drafts under `/me/messages`. |
| `WORKIQ_SEED_PATH` | Alternative scenario pack file. |
| `WORKIQ_PUBLIC_BASE_URL` | Base URL for `webUrl` links, when the app sits behind a proxy. |
| `FOUNDRY_OPENAI_ENDPOINT`, `FOUNDRY_CHAT_DEPLOYMENT` | Optional Azure OpenAI endpoint (`https://<name>.openai.azure.com`, `.cognitiveservices.azure.com` or `.services.ai.azure.com`, or a `/openai/v1` URL) and deployment for `ask`. Auth uses the managed identity (role Cognitive Services OpenAI User). |

## Admin endpoints (coaches)

All need `Authorization: Bearer <WORKIQ_ADMIN_KEY>`.

| Endpoint | Purpose |
|---|---|
| `POST /admin/seed` | Replace the whole pack (strict validation: at most 500 items, 64 KB per item, types `email`, `event`, `chat`, `file`, `person`). |
| `POST /admin/items` | Append one item, for example a new email that a coach plants during the hack. |
| `POST /admin/reset` | Reload the bundled pack. |
| `GET /admin/pack` | Export the current pack. |

Example, plant a new email for the Sales Lead:

```powershell
$item = @{
  id = 'coach-update-1'; type = 'email'; date = '2026-12-07T09:30:00+01:00'; visibleTo = @('sales-lead')
  subject = 'Call me before 10:00'; from = @{ name = 'Brennmark Purchasing Manager'; address = 'purchasing.manager@brennmark.example' }
  to = @(@{ name = 'Sales Lead'; address = 'sales.lead@caldova.example' }); body = 'Please call me before 10:00.'
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri https://<host>/admin/items -Headers @{ Authorization = "Bearer $adminKey" } -ContentType application/json -Body $item
```

State is in memory per instance. Admin changes are lost on restart and are not shared between instances. The deployment sets `maximumInstanceCount` to 1 so that every request sees the same state.

## Deploy to Azure

`Deploy-WorkIQEmulator.ps1` is dot-sourced by the lab automation. It uses only Az PowerShell against the current context.

```powershell
. ./Deploy-WorkIQEmulator.ps1
$r = Deploy-WorkIQEmulator -SubscriptionId $sub -ResourceGroupName $rg -Location swedencentral -Name func-workiq-lab01 `
    -AppInsightsConnectionString $ai -FoundryOpenAIEndpoint $aoaiEndpoint -FoundryChatDeployment gpt-4.1-mini `
    -FoundryAccountResourceId $foundryAccountId `
    -Keys @{ 'sales-lead' = $k1; 'supply-planner' = $k2; 'quality-head' = $k3; 'plant-manager' = $k4 } `
    -AdminKey $adminKey -Tags @{ project = 'microhack' }
$r.McpEndpoint; $r.ViewerUrl
```

It creates or updates: the resource group tag `SecurityControl=Ignore`, a storage account (shared key access disabled, public network access enabled, also tagged), a Flex Consumption plan (FC1), the function app (Python 3.12, 2048 MB, maximum 1 instance, 16 concurrent HTTP requests per instance, system-assigned identity, `AzureWebJobsStorage__accountName`), the Storage Blob Data Owner role on the storage account and, when `-FoundryAccountResourceId` is given, Cognitive Services OpenAI User on the Foundry account. It then zips this folder (without tests, scripts, `.venv` and caches), publishes it with remote build to `https://<scm host>/api/publish?RemoteBuild=true`, waits for the deployment and probes `/healthz`. A full deployment takes about one minute.

Two lessons from testing on Flex Consumption:

* Flex gives Python apps 1 concurrent HTTP request per instance by default. With a single instance, about half of the requests hung until they timed out. The script sets `perInstanceConcurrency` to 16, which is safe because the app is async.
* Code that runs in worker threads does not call `logging` directly. Log lines are buffered and written on the event loop thread, and the `azure` SDK logger is silenced.

## Security notes

* Bearer keys are compared with `hmac.compare_digest` against every configured key. Missing or wrong keys get 401 with `WWW-Authenticate: Bearer`.
* The viewer stores an HMAC-signed session in a `Secure`, `HttpOnly`, `SameSite=Strict` cookie. The cookie never holds the raw key, and sessions end when the key rotates.
* Request body limit 256 KB on `/mcp`, query limit 2,000 characters, at most 20 `entityUrls`, control characters rejected.
* No CORS headers. Requests with a foreign `Origin` header are refused.
* Every response carries `Content-Security-Policy` (`default-src 'self'`, no scripts, `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`. All seeded content is HTML-escaped.
* Logs contain the method, tool name, persona, result count and latency. Keys and bodies are never logged.
* The only outbound call is the optional Azure OpenAI call, to an allow-listed Azure host.
* Persona keys and the admin key are stored as plain app settings. Treat the function app configuration as secret, and rotate keys per lab.

## Files

| Path | Purpose |
|---|---|
| `function_app.py` | Azure Functions entry point (`AsgiFunctionApp`). |
| `workiq_emulator/app.py` | Routes, auth, limits, security headers, viewer and admin. |
| `workiq_emulator/mcp.py` | JSON-RPC and MCP method handling. |
| `workiq_emulator/tools/` | Tool schemas and implementations. |
| `workiq_emulator/store.py` | Pack validation, derived Graph ids, the item store. |
| `workiq_emulator/graph.py` | Graph v1.0 JSON shapes. |
| `workiq_emulator/ranking.py` | BM25 ranking and tokenization. |
| `workiq_emulator/viewer/` | HTML pages and CSS. |
| `seed/caldova.json` | The Caldova scenario pack. |
| `scripts/mcp_smoke.py` | MCP client smoke test. |
| `tests/` | pytest suite. |
| `Deploy-WorkIQEmulator.ps1` | Azure deployment. |
