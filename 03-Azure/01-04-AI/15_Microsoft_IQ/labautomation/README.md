# labautomation: Microsoft IQ hack v2 (Strandvik Drives)

[`deploy-lab.ps1`](deploy-lab.ps1) gives every lab (one team, or one solo hacker) a complete,
isolated environment for "Alex sleeps through 02:13": one Foundry resource with two projects
(`strandvik`, empty, and `kolvo`, pre-built), Foundry IQ (Azure AI Search) with an empty
`documents` container, Application Insights on both projects, a Fabric capacity and workspace,
and the Work IQ emulator with Kolvo's procurement board. There is no shared backend and no
coach step per lab. One-time tenant settings are listed under
[Platform admin prerequisites](#platform-admin-prerequisites-once-per-tenant).

Participants build everything else themselves in the browser: the portals, plus one script in
Azure Cloud Shell ([`scripts/enable-a2a.py`](../scripts/enable-a2a.py)). They need no Codespace and
no local install, and they never run these scripts. Several labs share one subscription
(`labsPerSubscription`), so every `enable-a2a.py` command in the challenges passes
`--resource-group <your lab resource group>` with the name from the lab dashboard.

| File | Purpose |
|------|---------|
| [`deploy-lab.ps1`](deploy-lab.ps1) | Run by the MicroHack platform once per lab, unattended |
| [`setup-kolvo.ps1`](setup-kolvo.ps1) | Kolvo pre-build (agents, A2A, role). Called by `deploy-lab.ps1`; safe to run again on its own |
| [`workiq-emulator/`](workiq-emulator/) | Work IQ emulator (MCP server, viewer, procurement board), deployed by `Deploy-WorkIQEmulator.ps1` |
| [`run-local.ps1`](run-local.ps1) | Local test wrapper (platform helper stand-ins). Never run by the platform |
| [`lab-defaults.json`](lab-defaults.json) | Platform settings (groups, region list, cost, labs per subscription) |

## Platform contract

- Parameters: `DeploymentType`, `SubscriptionId`, `ResourceGroupName`, `PreferredLocation`,
  `AllowedEntraUserIds` (from the platform) plus `FabricSkuName` (default `F2`),
  `ChatModelCapacity` (200), `GraphModelCapacity` (100), `EmbeddingModelCapacity` (50).
- The platform pre-sets the Az context and pre-creates the resource group. The scripts never
  call `Connect-AzAccount`, `Set-AzContext`, `az login` or `az account set`.
- Helper files are found through `$PSScriptRoot`.
- Platform helpers used: `Get-MhhStableHash`, `New-MhhStablePassword`, `Get-MhhLabUser`,
  `Update-MhhToken`.
- Outputs are `@{ HackboxCredential = @{ name; value; note } }` objects (see
  [Outputs](#outputs)).

## What gets provisioned per lab

Everything except Fabric lives in one region (the "lab region", normally `swedencentral`).

| Resource | Name | Notes |
|----------|------|-------|
| Log Analytics workspace | `iq-log-<hash>` | PerGB2018, 30 days |
| Application Insights (workspace-based) | `iq-appi-<hash>` | Connected to both projects as `appinsights-strandvik` and `appinsights-kolvo` (category `AppInsights`, `ApiKey` = connection string). The names differ because a same-named connection in a second project collides. Also used by the Work IQ emulator. |
| Foundry account (`AIServices`, S0) | `iq-<account-hash>` | Own hash: user ids plus the resource group name and creation time, so a re-provisioned lab gets a fresh subdomain (a purged and re-created subdomain keeps answering A2A "Project not found" for a long time). A re-run in the same group finds and reuses its tagged account. Custom subdomain, system identity, `allowProjectManagement = true`, public network access on, local auth disabled (Entra only) |
| Foundry project | `strandvik` | System identity. **Empty**: participants build all Strandvik agents here |
| Foundry project | `kolvo` | System identity. **Pre-built** by `setup-kolvo.ps1`, see [Kolvo pre-build](#kolvo-pre-build) |
| Model `gpt-5.4-mini` | GlobalStandard, 200K TPM | Agents, rubric generation |
| Model `gpt-5.6-luna` | GlobalStandard, 100K TPM | Evaluation judge, knowledge graph extraction |
| Model `text-embedding-3-large` | GlobalStandard, 50K TPM | Foundry IQ knowledge sources |
| Azure AI Search (Foundry IQ) | `iq-srch-<hash>` | **Basic**, system identity, `aadOrApiKey` with `http401WithBearerChallenge`, semantic ranker `free`, public network access on |
| Storage account | `iqst<hash>` | StorageV2, Standard_LRS, TLS 1.2, no anonymous access, shared key off, blob soft delete on (7 days), versioning off (the knowledge graph stretch needs both) |
| Blob container | `documents` | **Empty**. Participants upload the Strandvik documents (portal or notebook 00) |
| Fabric capacity | `iqcap<hash>` | Default **F2**, lab user is **capacity admin**, left **Active** |
| Fabric workspace | `strandvik-<hash>` | On the lab capacity, lab user is **Admin**. Best effort: if the deployment identity cannot call the Fabric API, the lab user creates it in the Fabric portal |
| Work IQ emulator | `iq-wiq-<hash>` | Azure Functions Flex Consumption. MCP server (`/mcp`), viewer (`/viewer`), Kolvo procurement board (`/board`). Persona keys `alex` (participant) and `sam`; admin key stays in the app settings |

Model versions are resolved at deploy time (the default GlobalStandard version), so the script
does not break when a new version becomes the default.

## Kolvo pre-build

[`setup-kolvo.ps1`](setup-kolvo.ps1) builds Kolvo's side of the story through the Foundry
REST API (`https://<account>.services.ai.azure.com/api/projects/kolvo`, `api-version=v1`,
token audience `https://ai.azure.com`) and ARM:

| Item | Details |
|------|---------|
| `nordic-drive-parts` | Prompt agent (gpt-5.4-mini). Answers at once from its stock list: "In stock, ships today." Cannot hold or reserve a unit, no installation. **Incoming A2A on** |
| `hallberg-repair` | Prompt agent. Repair shop, office hours 08:00 to 17:00 CET; at night it replies that a person answers after 08:45. **Incoming A2A on** |
| A2A connections | `nordic-drive-parts-a2a`, `hallberg-repair-a2a`, `strandvik-a2a` in the kolvo project. Category `RemoteA2A`, auth `AgenticIdentityToken`, audience `https://ai.azure.com`. `strandvik-a2a` points at `.../api/projects/strandvik/agents/strandvik-customer-service/endpoint/protocols/a2a`, which participants create in challenge 2 |
| `maria-procurement` | Prompt agent with the three A2A tools (`a2a`, version 1.0). Maria's standing instruction: ask the approved suppliers for price, delivery time and whether they can hold the unit for SD9-K-0412 on press line 2, needed before Thursday 06:00; summarise per supplier; never order |
| Role | Maria's agent identity (`instance_identity.principal_id`) gets **Foundry Agent Consumer** on the **kolvo** project, so it can call the rivals. It deliberately does **not** get it on the strandvik project: granting that is the participants' task in challenge 2 |

Incoming A2A is enabled with `PATCH /agents/<name>` (`agent_card` plus
`agent_endpoint.protocol_configuration` `responses` and `a2a`). The script is idempotent: an
unchanged agent is left alone, a changed definition becomes a new version, connections and
role assignments use stable names.

## Outputs

| Credential | Value |
|------------|-------|
| `StrandvikProjectUrl` | Foundry portal deep link to the `strandvik` project |
| `KolvoProjectUrl` | Foundry portal deep link to the `kolvo` project |
| `StrandvikProjectEndpoint` | `https://iq-<hash>.services.ai.azure.com/api/projects/strandvik` |
| `KolvoProjectEndpoint` | `https://iq-<hash>.services.ai.azure.com/api/projects/kolvo` |
| `FoundryAccountName` | `iq-<hash>` |
| `ModelDeploymentName` | `gpt-5.4-mini` |
| `JudgeModelDeploymentName` | `gpt-5.6-luna` |
| `EmbeddingDeploymentName` | `text-embedding-3-large` |
| `SearchEndpoint` | `https://iq-srch-<hash>.search.windows.net` |
| `StorageAccountName` | `iqst<hash>` |
| `DocumentsContainer` | `documents` |
| `FabricCapacityName` | `iqcap<hash>` (only when the capacity is Active) |
| `FabricPortalUrl` | Fabric portal link (the workspace when it exists) |
| `FabricWorkspaceId` | Workspace id (only when the workspace was created) |
| `WorkIQEmulatorEndpoint` | `https://<emulator host>/mcp` |
| `WorkIQViewerUrl` | `https://<emulator host>/viewer` |
| `WorkIQBoardUrl` | `https://<emulator host>/board` |
| `WorkIQKey` | Alex's persona key (MCP tool header and viewer) |
| `WorkIQKeySam` | Sam's persona key, for whoever plays Sam |
| `ApplicationInsightsName` | `iq-appi-<hash>` |
| `LabRegion` | The lab region |

Participants read these on the lab dashboard. Developers who use the optional Codespace or a
local clone run [`create-env.sh`](../create-env.sh) (or `create-env.ps1`), which reads the same
values from Azure and writes `.env` for the notebooks.

The emulator **admin key** is not an output. Coaches read `WORKIQ_ADMIN_KEY` from the Function
App's environment variables (Azure portal > the lab resource group > `iq-wiq-...` > Settings >
Environment variables). The platform itself emits `Resource Group Name`, `Subscription ID`
and the lab user credentials.

## RBAC

The platform grants the lab user **Owner** on the resource group (control plane only). The
script adds:

| Principal | Scope | Roles (role id) |
|-----------|-------|-----------------|
| Lab user | Foundry account | Foundry Project Manager (`eadc314b-1a2d-4efa-be10-5d325db5065e`), Foundry User (`53ca6127-db72-4b80-b1b0-d745d6d5456d`), Cognitive Services User, Cognitive Services OpenAI User |
| Lab user | Search service | Search Service Contributor, Search Index Data Contributor |
| Lab user | Storage account | Storage Blob Data Contributor |
| Lab user | Application Insights and Log Analytics workspace | Log Analytics Reader (`73c42c96-874c-492b-b04d-ab87d138a893`), so traces show in Foundry (challenge 7) |
| Lab user | Fabric | Capacity admin (UPN via `Get-MhhLabUser`), workspace Admin |
| Search identity | Foundry account | Cognitive Services OpenAI User |
| Search identity | Storage account | Storage Blob Data Reader |
| Each project identity | Search service | Search Index Data Reader, Search Index Data Contributor, Search Service Contributor |
| Each project identity | Foundry account | Foundry User |
| `maria-procurement` agent identity | kolvo project | Foundry Agent Consumer (`eed3b665-ab3a-47b6-8f48-c9382fb1dad6`) |
| Work IQ emulator identity | kolvo project | Foundry User (the board's "Run 02:13" calls `maria-procurement`) |
| Work IQ emulator identity | Foundry account | Cognitive Services OpenAI User (granted by `Deploy-WorkIQEmulator`) |
| Deployment identity (if not the lab user) | Foundry account | Foundry User (to build the Kolvo agents through the data plane) |

**Why no RBAC administrator role for the lab user?** Challenge 2 asks the lab user to grant
Maria's agent identity **Foundry Agent Consumer** on the strandvik customer service agent (with
`enable-a2a.py` in Cloud Shell, because the portals cannot pick agent identities yet). The built-in **Foundry Project Manager** role already allows
`roleAssignments/write` with a condition that limits it to exactly two roles: Foundry Agent
Consumer and Foundry User. That is all the challenge needs, and the platform's Owner role on
the resource group covers it too.

Role assignments go through ARM REST with deterministic names, check for an existing
assignment first, treat `RoleAssignmentExists` as success and retry while a new managed
identity replicates (`PrincipalNotFound`).

## Known waits

| What | How long | Notes |
|------|----------|-------|
| First full run | about 25 to 35 minutes | Search and the emulator build dominate |
| Public A2A endpoint of a brand-new project | several minutes after the project exists | Agent cards answer `Project not found` until then. `deploy-lab.ps1` re-runs `setup-kolvo.ps1` at the end and waits up to 15 minutes for the rivals' cards |
| Foundry Agent Consumer grant to work | about 4 minutes | Until then Maria's call fails with a vague `tool_user_error`. Teach: wait 3 to 5 minutes |
| Foundry IQ blob knowledge source | about 1 minute | 10 small markdown files, Creating to Active |
| Knowledge graph source (notebook 02) | a few minutes | Graph extraction with gpt-5.6-luna |
| Fabric table loads on F2 | 20 to 60 seconds per table | HTTP 430 when busy: the notebook waits and retries |
| Monitor > Cost in Foundry | 8 to 24 hours | Use token counts in traces and the evaluation grid on the day |

## Region choice

`preferredLocation` is `swedencentral, francecentral, switzerlandnorth`. On a fresh run the
script picks the first region where Search offers new **Basic** services with the **semantic
ranker**, the Search Basic quota is not used up, and all three models have enough
GlobalStandard quota. If a create still fails with a quota or capacity error, it removes what
it created there (and purges the soft-deleted Foundry account) and tries the next region. A
re-run stays in the region where the lab already lives. Fabric tries the lab region first.

## Deployment robustness

| Concern | How the script handles it |
|---------|---------------------------|
| A control-plane call fails but the cmdlet does not throw | Every ARM call goes through `Invoke-MhhArm`, which throws on non-2xx and retries 429 and 5xx |
| A PUT returns 2xx or 202 and fails later | `Wait-ArmProvisioned` polls every resource (account, both projects, each model deployment, Search, storage, Log Analytics, Fabric) until `Succeeded`; connections, containers and agents are read back after creation |
| MCAPS policies force `publicNetworkAccess = Disabled` | The resource group gets `SecurityControl = Ignore` (merged, existing tags kept) before anything is created. Storage and Search public access are then re-read and repaired; the script fails rather than hand over a broken lab |
| Soft-deleted Foundry account holds the subdomain | `CustomDomainInUse` triggers a purge and one retry |
| A new data role is not active yet | Foundry data-plane calls in `setup-kolvo.ps1` retry 401/403 for up to 10 minutes |
| Fabric capacity or workspace cannot be created | Logged as `[WARN]`; the rest of the lab works and the Fabric outputs are omitted |
| Emulator settings | The Kolvo settings (`KOLVO_PROJECT_ENDPOINT`, `MARIA_AGENT_NAME=maria-procurement`, `WORKIQ_SEED=strandvik`, `WORKIQ_AUTO_SAM=false`) are passed as parameters and merged into the app settings again afterwards |
| Long runs outlive the platform credential | `Update-MhhToken` between phases and in poll loops |
| Re-runs | Every step is check-before-create; keys come from `New-MhhStablePassword`, so a re-run keeps them |

## How to re-run

- **Whole lab:** run `deploy-lab.ps1` again with the same parameters (platform re-deploy, or
  `run-local.ps1` locally). It converges and changes nothing that is already right.
- **Kolvo only** (for example after a coach changed an agent by mistake):

  ```powershell
  ./setup-kolvo.ps1 -SubscriptionId <sub> -ResourceGroupName <rg> -AccountName iq-<hash>
  ```

  It needs an Az PowerShell context with Owner (or User Access Administrator) on the resource
  group and Foundry User on the Foundry account.
- **Reset Strandvik's side:** delete the agents in the strandvik project in the Foundry portal.
  Nothing in the automation depends on them.

## Platform admin prerequisites (once per tenant)

Set once by the lab tenant's Fabric administrator, **Fabric admin portal, Tenant settings**:

- **Users can create Fabric items** (lab users or the whole tenant).
- **Users can create ontology (preview) items** (challenge 3 has a fallback if this is off).
- **Users can create and share Data agent item types (preview)**.
- **Users can use Copilot and other features powered by Azure OpenAI**, and, if the capacity
  region differs from the Azure OpenAI region, **Data sent to Azure OpenAI can be processed
  outside your capacity's geographic region**.
- Optional, for the automatic workspace: **Service principals can use Fabric APIs** for the
  platform's deployment identity. Without it the lab user creates the workspace by hand.

Lab users need a Fabric (Power BI) licence: `"groups": ["GHCPUsers", "M365-E5-Users"]` in
[`lab-defaults.json`](lab-defaults.json) assigns Microsoft 365 E5 (includes Power BI Pro) and a
GitHub Copilot seat. Participants do not need Codespaces: the hack is browser only. The hack does
not provide Codespaces billing. A participant who wants a Codespace creates it on their own fork,
using their own GitHub account's Codespaces allowance (personal GitHub accounts include free
Codespaces hours every month), or uses a local clone.

## Packing and quotas (`labsPerSubscription = 10`)

| Limit (per subscription and region, typical) | Per lab | Labs that fit |
|----------------------------------------------|---------|---------------|
| gpt-5.4-mini GlobalStandard, 2,000K TPM | 200K | 10 |
| gpt-5.6-luna GlobalStandard, 1,000K TPM | 100K | 10 |
| text-embedding-3-large GlobalStandard, 2,000K TPM | 50K | 40 |
| Fabric capacity quota, 64 to 512 CU | F2 = 2 CU | 32 to 256 |
| **Azure AI Search Basic services, 12 (some subscriptions 16)** | 1 | **12** |

Search Basic and the two chat models bind at 10 to 12 labs. The chat models were raised to 200K and 100K because 100K was rate limited during rubric generation and evaluations; if a region has less quota, the deploy moves on to the next preferred region.

## Cost estimate (per lab per day, pay as you go)

| Item | USD per day |
|------|-------------|
| Fabric F2, running 24 hours | about 8.6 |
| Azure AI Search Basic | about 2.5 |
| Model tokens (agents, A2A calls, evaluations with the judge model, graph extraction, embeddings) | about 3 to 6 |
| Application Insights and Log Analytics (traces) | about 0.5 |
| Storage | under 0.1 |
| Functions Flex Consumption (no always-ready instances) | about 0 |
| **Total** | **about 16** (`estimatedDailyCostsUsd`) |

Fabric is billed only while running. Coaches can **pause** it outside hack hours (Azure
portal > Fabric capacity > Pause, or `POST .../capacities/<name>/suspend?api-version=2023-11-01`).
Re-running the script resumes it.

## Local test run

```powershell
# Requires an Az PowerShell context (Connect-AzAccount) and az login to the test subscription.
./run-local.ps1 -SubscriptionId <sub> -ResourceGroupName rg-iq-v2-test -PreferredLocation swedencentral
```

`run-local.ps1` supplies stand-ins for the platform helpers, creates the resource group, uses
your own object id as the lab user, runs `deploy-lab.ps1` and prints the outputs (secrets
masked unless `-ShowSecrets`). Then run `bash ../create-env.sh rg-iq-v2-test` to check `.env`.

## Teardown

The platform deletes the lab resource group when the event ends. For a local test:

```powershell
az group delete -n rg-iq-v2-test --yes --no-wait
```

The Foundry account stays soft-deleted for 48 hours. A new resource group gets a new account
name, so it does not collide; if it ever does, the script purges the soft-deleted account when it
hits `CustomDomainInUse` and retries once. Agent identities are removed with their agents.
