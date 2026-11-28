# Work IQ emulator

The Work IQ emulator gives every hack participant a private, simulated Microsoft 365 work context for the Strandvik scenario ("Alex sleeps through 02:13"). It speaks the same MCP contract as Work IQ, so agent code written against the emulator also works against production Work IQ. Only the URL and the auth header change.

| | Production Work IQ | Emulator |
|---|---|---|
| Endpoint | `https://workiq.svc.cloud.microsoft/mcp` | `https://<function-app>/mcp` |
| Auth | Entra token with `WorkIQAgent.Ask` | `Authorization: Bearer <persona key>` |
| Data | Your Microsoft 365 tenant | `seed/strandvik.json` (items W1 to W7 from `walkthrough/scenario-facts.md`, plus distractors) |

Why an emulator: real Work IQ needs Microsoft 365 Copilot licenses, Copilot billing and tenant admin consent. The hackathon tenant does not have them.

## What it is

* An Azure Functions app (Flex Consumption, Python 3.12). One HTTP-triggered ASGI function (Starlette) serves every route.
* `POST /mcp`: MCP streamable HTTP, JSON-RPC 2.0, stateless JSON responses. Methods: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
* `GET /viewer`: a web view of the persona's mailbox, chats, calendar, files, people and recent agent tool calls. Chat threads refresh every 4 seconds and have a reply box, so a person can play Sam or Alex live.
* `GET /board` (redirects to `/viewer/board`): Kolvo's procurement board with the **Run 02:13** button.
* `GET /healthz`: `{"status":"ok","items":N}`, no auth.
* `/manage/*`: coach endpoints to replace, extend, reset or export the scenario pack. Azure Functions reserves `/admin/*` for its own host API, so use `/manage/*` on a deployed lab; `/admin/*` still works as an alias when you run the app locally.

## Personas and keys

Each persona has its own key. A key maps to exactly one persona. The lab hands out two keys:

| Persona id | Display name | App setting for the key | Used by |
|---|---|---|---|
| `alex` | Alex, key account manager for Kolvo | `WORKIQ_KEY_ALEX` | The participant. Alex's agent calls `/mcp` with this key (it is `WORKIQ_KEY` in `.env`), and Alex signs in to the viewer with it. |
| `sam` | Sam, key account manager for Poliden | `WORKIQ_KEY_SAM` | The coach or teammate who plays Sam in the viewer. Optional: anyone signed in can also post as Sam (see below). |

Any other persona in the seed (`sales-leadership`, `service-coordinator`, `maria`, `poliden-planner`) gets a key only if you set `WORKIQ_KEY_<ID>` (upper case, `-` becomes `_`).

Every seeded item has a `visibleTo` list. `retrieve`, `fetch`, `fetch_blob`, `ask` and the viewer only return items that the calling persona can see. This is the teaching point of challenge 5: Alex sees Sam's note in the "Poliden account" channel (W1, "Poliden's stop will probably move two weeks"), but not the Poliden planner's email to Sam (W2). So Alex's agent knows there is a reason to ask, but not the answer. It has to ask Sam in the thread.

## Contract coverage

| Tool | Emulated | Notes |
|---|---|---|
| `retrieve` | Yes | `structuredContent["application/vnd.ms-workiq.retrieval"]` with `results[]` (`id`, `markdown`, `resourceId`, `webUrl`, `entityUrl`, `entityType`, `contentProtection`, `resourceMetadata`, plus `chatId`/`messageId` or `driveId`/`itemId`, `relevanceScore`), `resultCount`, `searchMetadata.searchTerms`, `stoppedReason`, and `@workiq.untrustedContent`. Capabilities `Email`, `TeamsMessages`, `Meetings` (events and transcripts), `OneDriveAndSharePoint`, `People`. `GraphConnectors` needs strategy `copilot` and returns nothing. `Dataverse` is rejected. |
| `fetch` | Yes | Graph v1.0 shapes for `/me`, `/me/messages`, `/me/mailFolders/{inbox,sentitems,drafts}/messages`, `/me/events`, `/me/calendarView`, `/me/chats`, `/chats/{id}/messages`, `/me/drive`, `/me/drive/root/children`, `/me/drive/items/{id}`, `/drives/{id}/items/{id}`, `/sites/{id}/drive/root/children`, `/me/people`, `/users/{id}` and more (see `search_paths`). `$top` (default 25, maximum 100), `$select`, `$filter` (eq, ne, gt, ge, lt, le, contains, startswith, endswith, joined with `and`), `$orderby`, `$search`, `$count`. Chat messages are capped at 10 (newest first). `$skip` and `$skiptoken` return 400. Paths outside `/me/`, `/users/`, `/sites/`, `/chats/`, `/drives/` return 403, and so do `/authentication/` and `/servicePrincipals/`. Unknown paths return a 404 entry. |
| `fetch_blob` | Yes | `/drives/{id}/items/{id}/content` and `/me/drive/items/{id}/content`. Returns the stored text of the file. |
| `ask` | Yes | Runs retrieval for the persona. If `FOUNDRY_OPENAI_ENDPOINT` and `FOUNDRY_CHAT_DEPLOYMENT` are set, the app calls Azure OpenAI chat completions with its managed identity and returns a grounded answer with `[^hN]` citations. Otherwise it returns an extractive list of the best matches. Conversations are kept in memory per persona and `conversationId`. |
| `list_agents` | Yes | Returns the built-in `bizchat-as-gpt-scenario` agent only. |
| `search_paths`, `get_schema` | Yes | Lists the emulated paths. Returns small JSON Schemas (or TypeScript) for message, event, chat, chatMessage, driveItem, person and user. |
| `create_entity` on `/chats/{chat-id}/messages` | Yes (lab policy) | The one write this lab allows. jsonBody `{"body": {"contentType": "text", "content": "..."}}` (`html` is reduced to text). The caller must be a member of the chat, otherwise 404. Returns 201 with a Graph `chatMessage`. The message is attributed to **"Alex's agent (on behalf of Alex)"**: `from.user` is the persona with that display name, `from.application` is `{displayName: "Alex's agent", applicationIdentityType: "bot"}`. Switch off with `WORKIQ_ALLOW_CHAT_WRITE=false`. |
| other `create_entity`, `update_entity`, `delete_entity`, `do_action` | Policy-blocked | Same as a default tenant: `isError: true` with "Blocked by Work IQ tenant policy: mutation operations are disabled (emulator default)". With `WORKIQ_ALLOW_MUTATIONS=true`, `create_entity` on `/me/messages` creates a draft that only the persona can see. |
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
* Live meetings, presence, sending mail, Graph connectors, Dataverse and sensitivity labels. Chat replies, mentions and reactions (posts are plain messages).

## Play Sam (challenge 5) and Alex (challenge 7)

The Kolvo thread (seed item `W3`, topic "Kolvo press line 2, SD-900", members Alex and Sam) is where Alex's agent asks Sam at 03:52 and where Alex makes the call at 07:30.

1. Open `https://<host>/viewer`, sign in with the Alex or Sam key, open **Chats** and the Kolvo thread.
2. The thread refreshes every 4 seconds. Posts from agents are highlighted and say "Alex's agent (on behalf of Alex)".
3. Under the thread, pick **Post as** (only the thread members are listed) and write the message. Sam's scripted answer from the scenario facts is: "Yes, it is moving two weeks. Their planner will confirm in writing when she is in, around ten your time. Fine by me, as long as Poliden gets the new unit in time."
4. At 07:30, post as Alex to approve (or not). That is a person making the call, not an agent.

Posting needs a viewer session, that is a valid lab persona key. Random visitors cannot post. Cross-origin form posts are refused, and the session cookie is `SameSite=Strict`.

### Story clock and story controls

Live posts in the Kolvo thread are stamped with a **story clock**, not the real time of day. Until the first live write in the Kolvo thread (an agent post or a viewer post) the story time is the seed's "now", Tuesday 03:45. The first live write starts the clock, and from then on real time runs (a lab day is about 7 hours, so 03:52, 04:10 and so on come out roughly right). Labs deployed well ahead of the hack are not affected, because the clock does not start with the app.

Participants control the story themselves. In the viewer, signed in with a lab persona key (Alex's `WorkIQKey` or Sam's `WorkIQKeySam`), select **Story** in the top navigation (`https://<host>/viewer/story`; the old `/viewer/coach` URL still works). No admin key is needed when you are signed in. Each lab has its own emulator, so the controls only affect that team's story. The page has two controls:

* **Set the story clock**: enter `HH:MM` (on the night of the story, Tuesday) or a full ISO 8601 time. For example, set **07:30 before "Alex makes the call"** (challenge 7), so Alex's approval posted from the viewer shows 07:30.
* **Reset the Kolvo thread**: removes every live post in the Kolvo thread (agents and people), cancels a pending auto-Sam reply and stops the story clock. Use it to start the night again.

The thread view shows the current story time under the auto-Sam switch.

Coaches can use the same page without signing in: every action then asks for the lab admin key `WORKIQ_ADMIN_KEY`. A coach script can do the same over HTTP with the admin key (see Admin endpoints).

### Auto-Sam (solo hackers)

Turn it on with the button above the Kolvo thread, or start with `WORKIQ_AUTO_SAM=true`. When anyone other than Sam posts in the Kolvo thread a message that mentions Sam (`Sam` or `@Sam`), Sam answers after `WORKIQ_AUTO_SAM_DELAY_SECONDS` (default 30):

* the message is about the Poliden unit, reservation, stop, Rotterdam or RSV-2291: the scripted "Yes, it is moving two weeks..." answer;
* anything else: "I am at a trade fair in Singapore this week. Please keep it short: what do you need from me?"

It is deterministic and uses no model. There are no timers: a due reply is posted lazily by the next request (any MCP call, viewer page or the thread's 4 second refresh), which is reliable on Flex Consumption. One reply is pending per thread at a time. Tell participants that the agent may need to read the thread again after about 30 seconds.

## Kolvo procurement board (challenges 2 and 7)

`https://<host>/board` shows Maria's 02:13 request, one card per supplier (Strandvik Drives, Nordic Drive Parts, Hallberg Repair Services) with status, answer and time to answer, a scorecard and Maria's agent's final message. It needs a viewer sign-in (any lab key) and is sized for a projector.

**Run 02:13** calls the Foundry Responses API on the Kolvo project with the function app's system-assigned managed identity (`DefaultAzureCredential`, token audience `https://ai.azure.com`):

```
POST {KOLVO_PROJECT_ENDPOINT}/openai/v1/responses
{"input": "<Maria's request>", "agent_reference": {"name": "maria-procurement", "type": "agent_reference"}}
```

The board reads the output items of type `a2a_preview_call` and `a2a_preview_call_output` (and `a2a_call` / `a2a_call_output`), matches each to a supplier by the tool or connection name (contains `strandvik`, `nordic` or `hallberg`), links outputs to calls by `call_id`, and takes Maria's final text from the `message` items. The last run is kept in memory and shown after a refresh.

* Before challenge 2 is done, the run fails. Foundry fails Maria's **whole** response with `tool_user_error` (in about 4 seconds) when any A2A target is unreachable, so all three suppliers show "no answer" and the board explains why (Strandvik agent missing, incoming A2A off, or the Foundry Agent Consumer role missing). That is the expected state. After the team creates `strandvik-customer-service`, enables incoming A2A and grants Maria's agent identity Foundry Agent Consumer on the strandvik project, wait 3 to 5 minutes and run again.
* The scorecard (Answered, Answered in time, Grounded and holds the unit, Respects quote only, Final confirmation by a person) is a set of simple keyword checks. It is a conversation starter, not a judge.
* Errors (missing setting, HTTP 401/403 from Foundry, timeouts) are shown in red on the board.

Why a synchronous call: the run takes 30 to 90 seconds. The button keeps one HTTP request open for up to 180 seconds (below the 230 second front-end limit) while the call runs in a worker thread, and the page polls `/viewer/api/board` every 4 seconds so other screens show "Running". On Flex Consumption an open request keeps the instance alive, while a background thread after the response could be frozen or recycled when the instance scales in. Only one run at a time; a run older than 240 seconds counts as failed.

## Run it locally

```powershell
cd labautomation/workiq-emulator
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
# Microsoft corp network: add --default-index <your internal PyPI proxy>

# Option A: local development without keys. Send X-WorkIQ-Persona: <persona id> (default alex).
$env:WORKIQ_DEV_MODE = 'true'
# Option B: keys, like in Azure (at least 16 characters each).
$env:WORKIQ_KEY_ALEX = '<random secret>'
$env:WORKIQ_KEY_SAM = '<random secret>'
$env:WORKIQ_ADMIN_KEY = '<random secret>'

.venv/Scripts/python.exe -m uvicorn workiq_emulator.app:create_app --factory --port 7071
```

`func start` (Azure Functions Core Tools) also works, because `function_app.py` wraps the same ASGI app.

Smoke test with the official MCP Python client:

```powershell
.venv/Scripts/python.exe scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --key <persona key>
.venv/Scripts/python.exe scripts/mcp_smoke.py --url http://127.0.0.1:7071/mcp --persona alex   # dev mode
```

Run the tests:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

## Settings

| Setting | Purpose |
|---|---|
| `WORKIQ_KEY_<PERSONA>` | Persona key, for example `WORKIQ_KEY_ALEX`. Keys shorter than 16 characters are ignored. |
| `WORKIQ_ADMIN_KEY` | Key for `/manage/*`. Admin endpoints are disabled when it is not set. |
| `WORKIQ_SESSION_SECRET` | HMAC secret for viewer sessions. The deploy script derives it from the admin key, so a redeploy keeps viewers signed in. Derived from the admin key when not set. |
| `WORKIQ_DEV_MODE` | `true` allows `X-WorkIQ-Persona` when no persona keys exist (without the header the caller is `WORKIQ_DEFAULT_PERSONA`, default `alex`). Without keys and without dev mode, `/mcp` and `/viewer` return 503. |
| `WORKIQ_ALLOW_MUTATIONS` | `true` lets `create_entity` create drafts under `/me/messages`. |
| `WORKIQ_SEED` | Bundled scenario pack under `seed/`, default `strandvik`. |
| `WORKIQ_SEED_PATH` | Alternative scenario pack file (wins over `WORKIQ_SEED`). |
| `WORKIQ_ALLOW_CHAT_WRITE` | Default `true`: agents may post into chats they are a member of. |
| `WORKIQ_AUTO_SAM` | Default `false`. Start with auto-Sam on. The viewer button changes it at run time. |
| `WORKIQ_AUTO_SAM_DELAY_SECONDS` | Default `30` (0 to 600). |
| `WORKIQ_KOLVO_THREAD` | Seed item id of the Kolvo thread, default `W3`. Fallback: the first chat with "Kolvo" in the topic that Sam is in. |
| `KOLVO_PROJECT_ENDPOINT` | Kolvo project endpoint for the board, `https://<account>.services.ai.azure.com/api/projects/kolvo`. Without it the Run button is disabled. |
| `MARIA_AGENT_NAME` | Agent the board invokes, default `maria-procurement`. |
| `MARIA_REQUEST` | Optional override of Maria's 02:13 request text. |
| `WORKIQ_PUBLIC_BASE_URL` | Base URL for `webUrl` links, when the app sits behind a proxy. |
| `FOUNDRY_OPENAI_ENDPOINT`, `FOUNDRY_CHAT_DEPLOYMENT` | Optional Azure OpenAI endpoint (`https://<name>.openai.azure.com`, `.cognitiveservices.azure.com` or `.services.ai.azure.com`, or a `/openai/v1` URL) and deployment for `ask`. Auth uses the managed identity (role Cognitive Services OpenAI User). |

## Roles for the function app's managed identity

| Role | Role id | Scope | Needed for |
|---|---|---|---|
| Storage Blob Data Owner | `b7e6dc6d-f1e8-4753-8033-0f276bb0955b` | The emulator's storage account | Deployment and `AzureWebJobsStorage` (the script assigns it). |
| Foundry User | `53ca6127-db72-4b80-b1b0-d745d6d5456d` | The kolvo project (or the Foundry account) | **Run 02:13** on the board (Responses API, audience `https://ai.azure.com`). The script assigns it when `-KolvoProjectResourceId` is given. |
| Cognitive Services OpenAI User | `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` | The Foundry account | Optional, model answers for `ask`. The script assigns it when `-FoundryAccountResourceId` is given. |

New role assignments can take a few minutes to apply.

## Endpoints

| Method and path | Auth | Purpose |
|---|---|---|
| `POST /mcp` | Persona key | MCP (JSON-RPC). |
| `GET /healthz` | None | `{"status":"ok","scenario":"strandvik","items":N}`. |
| `GET /viewer/...` | Viewer session | Mail, chats (thread view with reply box), calendar, files, people, agent activity, board. |
| `POST /viewer/login`, `POST /viewer/logout` | Persona key in the form | Viewer session. |
| `POST /viewer/reply` | Viewer session | Form fields `chat` (Graph chat id), `as` (a member persona id), `text`. |
| `GET /viewer/api/chat?id=<chat id>` | Viewer session | Thread as JSON, used by the 4 second refresh. |
| `POST /viewer/auto-sam` | Viewer session | Form field `on` (`true` or `false`). |
| `GET /board` | None | Redirects to `/viewer/board`. |
| `GET /viewer/board` | Viewer session | The procurement board. |
| `POST /viewer/board/run` | Viewer session | Runs Maria's request, blocks up to 180 seconds. Send `Accept: application/json` for a JSON result. 409 when a run is in progress. |
| `GET /viewer/api/board` | Viewer session | Last run as JSON. |
| `GET /viewer/story` (alias `GET /viewer/coach`) | None | Story controls page (story clock, reset the Kolvo thread). The **Story** item in the viewer navigation opens it. |
| `POST /viewer/coach/clock`, `POST /viewer/coach/reset-thread` | Viewer session, or the admin key in the form | Story controls. |
| `/manage/*` | Admin key | See below. |

## Admin endpoints (coaches)

All need `Authorization: Bearer <WORKIQ_ADMIN_KEY>`.

| Endpoint | Purpose |
|---|---|
| `POST /manage/seed` | Replace the whole pack (strict validation: at most 500 items, 64 KB per item, types `email`, `event`, `chat`, `file`, `person`). |
| `POST /manage/items` | Append one item, for example a new email that a coach plants during the hack. |
| `POST /manage/reset` | Reload the bundled pack. |
| `GET /manage/pack` | Export the current pack. |
| `GET /manage/clock` | Story clock: `{"storyTime": "<ISO 8601 story time, Tuesday 03:45>", "running": false}`. |
| `POST /manage/clock` | Set the story clock, body `{"time": "07:30"}` or a full ISO 8601 time. Returns the clock. |
| `POST /manage/thread/reset` | Remove live posts from the Kolvo thread, cancel auto-Sam, stop the clock. Returns `{"status": "ok", "removed": N, ...}`. |

Example, plant a new email for Alex:

```powershell
$item = @{
  id = 'coach-update-1'; type = 'email'; date = (Invoke-RestMethod "https://<host>/manage/clock" -Headers @{ Authorization = "Bearer $adminKey" }).storyTime; visibleTo = @('alex')
  subject = 'Call me before 08:00'; from = @{ name = 'Maria (Kolvo)'; address = 'maria@kolvo.example' }
  to = @(@{ name = 'Alex'; address = 'alex@strandvik.example' }); body = 'Please call me before 08:00.'
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri https://<host>/manage/items -Headers @{ Authorization = "Bearer $adminKey" } -ContentType application/json -Body $item
```

State is in memory per instance: admin changes, chat posts, the auto-Sam switch and the last board run are lost on restart and are not shared between instances. `POST /manage/reset` also removes all chat posts and stops the story clock. The deployment sets `maximumInstanceCount` to 1 so that every request sees the same state, and keeps one always-ready instance so the app does not scale to zero (and lose the story) while a team is idle. A redeploy restarts the app, and for a few minutes the old and the new instance both serve requests. Wait about five minutes after a redeploy, then reset the thread and start the night again.

## Deploy to Azure

`Deploy-WorkIQEmulator.ps1` is dot-sourced by the lab automation. It uses only Az PowerShell against the current context.

```powershell
. ./Deploy-WorkIQEmulator.ps1
$r = Deploy-WorkIQEmulator -SubscriptionId $sub -ResourceGroupName $rg -Location swedencentral -Name func-workiq-lab01 `
    -AppInsightsConnectionString $ai -FoundryOpenAIEndpoint $aoaiEndpoint -FoundryChatDeployment gpt-4.1-mini `
    -FoundryAccountResourceId $foundryAccountId `
    -Keys @{ alex = $alexKey; sam = $samKey } -AdminKey $adminKey `
    -KolvoProjectEndpoint "https://$account.services.ai.azure.com/api/projects/kolvo" -KolvoProjectResourceId $kolvoProjectId `
    -Tags @{ project = 'microhack' }
$r.McpEndpoint; $r.ViewerUrl; $r.BoardUrl
```

It creates or updates: the resource group tag `SecurityControl=Ignore`, a storage account (shared key access disabled, public network access enabled, also tagged), a Flex Consumption plan (FC1), the function app (Python 3.12, 2048 MB, maximum 1 instance, 16 concurrent HTTP requests per instance, system-assigned identity, `AzureWebJobsStorage__accountName`), the Storage Blob Data Owner role on the storage account and, when `-FoundryAccountResourceId` is given, Cognitive Services OpenAI User on the Foundry account, and when `-KolvoProjectResourceId` is given, Foundry User on that scope. It then zips this folder (without tests, scripts, `.venv` and caches), publishes it with remote build to `https://<scm host>/api/publish?RemoteBuild=true`, waits for the deployment and probes `/healthz`. A full deployment takes about one minute.

Optional v2 parameters (all backward compatible): `-Seed` (default `strandvik`, sets `WORKIQ_SEED`), `-AutoSam` (bool, default `$false`, sets `WORKIQ_AUTO_SAM`), `-KolvoProjectEndpoint` (sets `KOLVO_PROJECT_ENDPOINT`), `-MariaAgentName` (default `maria-procurement`), `-KolvoProjectResourceId` (Foundry User grant) and `-ExtraAppSettings` (hashtable merged last). The script writes the complete app settings on every run, so pass settings as parameters rather than adding them afterwards. The result object has `McpEndpoint`, `ViewerUrl`, `BoardUrl`, `FunctionAppName` and `PrincipalId`.

Two lessons from testing on Flex Consumption:

* Flex gives Python apps 1 concurrent HTTP request per instance by default. With a single instance, about half of the requests hung until they timed out. The script sets `perInstanceConcurrency` to 16, which is safe because the app is async.
* Code that runs in worker threads does not call `logging` directly. Log lines are buffered and written on the event loop thread, and the `azure` SDK logger is silenced.

## Security notes

* Bearer keys are compared with `hmac.compare_digest` against every configured key. Missing or wrong keys get 401 with `WWW-Authenticate: Bearer`.
* The viewer stores an HMAC-signed session in a `Secure`, `HttpOnly`, `SameSite=Strict` cookie. On Azure Functions the cookie carries `Domain=<app host>`, because the Python worker turns a missing Domain into an empty `domain=` attribute that strict clients (.NET, PowerShell web sessions) drop. The cookie never holds the raw key, and sessions end when the key rotates.
* Request body limit 256 KB on `/mcp`, query limit 2,000 characters, at most 20 `entityUrls`, control characters rejected.
* No CORS headers. Requests with a foreign `Origin` header are refused.
* Every response carries `Content-Security-Policy` (`default-src 'self'`, scripts only from the app itself (`/viewer/static/viewer.js`, no inline script), `frame-ancestors 'none'`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: same-origin` (not `no-referrer`, which makes browsers send `Origin: null` on form posts). All seeded content is HTML-escaped.
* Logs contain the method, tool name, persona, result count and latency. Keys and bodies are never logged.
* Outbound calls: the optional Azure OpenAI call for `ask`, and the board's Responses API call. Both go only to allow-listed Azure hosts (`*.services.ai.azure.com`, `*.cognitiveservices.azure.com`, `*.openai.azure.com`) with the managed identity.
* Anyone with a lab persona key can post in a thread as any member of that thread. This is on purpose (a coach plays Sam), and it is why keys are per lab.
* Persona keys and the admin key are stored as plain app settings. Treat the function app configuration as secret, and rotate keys per lab.

## Files

| Path | Purpose |
|---|---|
| `function_app.py` | Azure Functions entry point (`AsgiFunctionApp`). |
| `workiq_emulator/app.py` | Routes, auth, limits, security headers, viewer, board and admin. |
| `workiq_emulator/mcp.py` | JSON-RPC and MCP method handling. |
| `workiq_emulator/tools/` | Tool schemas and implementations. |
| `workiq_emulator/store.py` | Pack validation, derived Graph ids, the item store. |
| `workiq_emulator/graph.py` | Graph v1.0 JSON shapes. |
| `workiq_emulator/ranking.py` | BM25 ranking and tokenization. |
| `workiq_emulator/chat.py` | Kolvo thread lookup, auto-Sam rules, posted text cleanup. |
| `workiq_emulator/board.py` | Procurement board: Responses API call, output parsing, scorecard. |
| `workiq_emulator/viewer/` | HTML pages, CSS and `viewer.js` (thread refresh, board polling). |
| `seed/strandvik.json` | The Strandvik scenario pack (owned by the data workstream, copy of `data/workiq/strandvik-seed.json`). |
| `scripts/mcp_smoke.py` | MCP client smoke test. |
| `tests/` | pytest suite. `tests/fixtures/` holds a small Strandvik pack and a recorded Responses payload. |
| `Deploy-WorkIQEmulator.ps1` | Azure deployment. |
