# labautomation: Microsoft IQ hack (Caldova Components)

[`deploy-lab.ps1`](deploy-lab.ps1) gives every attendee a complete, isolated lab:
a Foundry project with three models, Foundry IQ (Azure AI Search) with a storage
container for the Caldova documents, a Fabric capacity for Fabric IQ, and a Work IQ
emulator that serves the Caldova Microsoft 365 content per persona. There is no
shared backend and no facilitator step per attendee. A few one-time tenant settings
are listed under [Platform admin prerequisites](#platform-admin-prerequisites-once-per-tenant).

## What gets provisioned per attendee

Everything except Fabric lives in one region (the "lab region").

| Resource | Name | Notes |
|----------|------|-------|
| Log Analytics workspace | `iq-log-<hash>` | PerGB2018, 30 days |
| Application Insights (workspace-based) | `iq-appi-<hash>` | Connected to the Foundry project (`appinsights` connection), so the Traces tab works. Also used by the Work IQ emulator. |
| Foundry account (`AIServices`, S0) | `iq-<hash>` | Custom subdomain, system identity, `allowProjectManagement = true`, public network access on, **local auth disabled** (Entra only) |
| Foundry project | `caldova-iq` | System identity |
| Model `gpt-5.4-mini` | GlobalStandard, 100K TPM | Agent chat model |
| Model `gpt-5.6-luna` | GlobalStandard, 50K TPM | Foundry IQ knowledge graph extraction and knowledge base query planning |
| Model `text-embedding-3-small` | GlobalStandard, 50K TPM | Embeddings for the knowledge source |
| Azure AI Search (Foundry IQ) | `iq-srch-<hash>` | **Basic**, system identity, `aadOrApiKey` with `http401WithBearerChallenge`, semantic ranker `free`, public network access on. The knowledge graph uses REST api-version `2026-11-01-preview` and was verified on Basic in swedencentral. |
| Storage account | `iqst<hash>` | StorageV2, Standard_LRS, TLS 1.2, no anonymous blob access, **shared key access disabled** (Entra only), **blob soft delete on (7 days), versioning off** (required by the Foundry IQ entity graph) |
| Blob container | `caldova-docs` | The attendee uploads the ten Caldova documents here |
| Fabric capacity | `iqcap<hash>` | Default **F2** (`-FabricSkuName`), attendee is **capacity admin**, left **Active** |
| Work IQ emulator | `iq-wiq-<hash>` | Azure Functions Flex Consumption MCP server, deployed by [`workiq-emulator/Deploy-WorkIQEmulator.ps1`](workiq-emulator/Deploy-WorkIQEmulator.ps1) with four persona keys and one admin key |

Model capacities are parameters (`-ChatModelCapacity`, `-GraphModelCapacity`,
`-EmbeddingModelCapacity`). Model versions are resolved at deploy time from the
account's model list (the default GlobalStandard version), so the script does not
break when a new version becomes the default.

## What the attendee receives on the dashboard

| Credential | Value |
|------------|-------|
| `FoundryProjectUrl` | Deep link to the project in the Foundry portal |
| `FoundryProjectEndpoint` | `https://iq-<hash>.services.ai.azure.com/api/projects/caldova-iq` |
| `ModelDeploymentName` | `gpt-5.4-mini` |
| `GraphModelDeploymentName` | `gpt-5.6-luna` |
| `EmbeddingDeploymentName` | `text-embedding-3-small` |
| `SearchEndpoint` | `https://iq-srch-<hash>.search.windows.net` |
| `StorageAccountName` | `iqst<hash>` |
| `StorageContainer` | `caldova-docs` |
| `FabricCapacityName` | `iqcap<hash>` (only emitted when the capacity is Active) |
| `FabricPortalUrl` | Fabric portal link for the lab tenant (only with the capacity) |
| `WorkIQEmulatorEndpoint` | The emulator's MCP endpoint (`.../mcp`) |
| `WorkIQViewerUrl` | Web viewer for the emulated Microsoft 365 content |
| `WorkIQKeySalesLead` | Persona key, Sales Lead |
| `WorkIQKeySupplyPlanner` | Persona key, Supply Planner |
| `WorkIQKeyQualityHead` | Persona key, Quality Head |
| `WorkIQKeyPlantManager` | Persona key, Plant Manager |
| `ApplicationInsightsConnectionString` | Optional, for the attendee's own telemetry |
| `LabRegion` | The region the lab landed in |

The emulator's **admin key** (for `/admin/seed`, `/admin/items` and `/admin/reset`) is deliberately **not** on the dashboard. Coaches read it from the Function App setting `WORKIQ_ADMIN_KEY`: Azure portal > the lab resource group > the `wiq-...` Function App > Settings > Environment variables. Or run `az functionapp config appsettings list -g <rg> -n <app> --query "[?name=='WORKIQ_ADMIN_KEY'].value" -o tsv`. It only controls that one lab's emulator.

The platform itself emits `Resource Group Name`, `Subscription ID` and the Entra
credentials (reserved names), so the script does not.

All keys come from `New-MhhStablePassword` (48 characters, `[A-Za-z0-9]` only, safe
in HTTP headers). They are stable per lab and purpose, so a re-run keeps the values
already shown on the dashboard.

## RBAC

The platform already grants the attendee **Owner** on the resource group (control
plane only). The script adds the data-plane roles:

| Principal | Scope | Roles |
|-----------|-------|-------|
| Attendee | Foundry account | Azure AI User, Cognitive Services User, Cognitive Services OpenAI User |
| Attendee | Search service | Search Service Contributor, Search Index Data Contributor |
| Attendee | Storage account | Storage Blob Data Contributor |
| Attendee | Fabric capacity | Capacity admin (UPN resolved with `Get-MhhLabUser`) |
| Search identity | Foundry account | Cognitive Services OpenAI User (embeddings, graph extraction, query planning) |
| Search identity | Storage account | Storage Blob Data Reader (knowledge source ingestion) |
| Foundry project identity | Search service | Search Index Data Reader (knowledge base MCP connection) |
| Foundry project identity | Foundry account | Azure AI User |
| Work IQ emulator identity | Foundry account | Granted by `Deploy-WorkIQEmulator` |

Role assignments go through ARM REST with a deterministic assignment name. The script
checks for an existing assignment first, treats `RoleAssignmentExists` as success and
retries while a new managed identity is still replicating (`PrincipalNotFound`). No
Microsoft Graph permission is needed.

## Region choice

`preferredLocation` is `swedencentral, francecentral, switzerlandnorth`. On a fresh
run the script picks the first region that passes all of these checks, and emits
`Write-Warning` for every region it skips:

- Search offers new **Basic** services there and has the **semantic ranker** (needed
  by agentic retrieval). Read live from `Microsoft.Search/fetchOfferings`. This rules
  out West Europe, North Europe and Germany West Central (no new dedicated services)
  and Norway East (no semantic ranker or agentic retrieval).
- The Search Basic service quota in that region is not used up.
- All three models are offered as GlobalStandard and have enough free quota.

If a model deployment or the Search create still fails with a quota or capacity error
(for example parallel labs racing for the last quota), the script deletes what it
created in that region (and purges the soft-deleted Foundry account) and moves on to
the next region. On a re-run the region is locked to where the lab already lives.
Fabric tries the lab region first, then the other preferred regions on its own.

## Deployment robustness

| Concern | How the script handles it |
|---------|---------------------------|
| A control-plane call fails but the cmdlet does not throw | Every ARM call goes through `Invoke-MhhArm`, which throws on any non-2xx (with `-AllowNotFound` for existence probes) and retries 429 and 5xx gateway errors. |
| Long-running creates return 2xx but fail later | `Wait-ArmProvisioned` polls every resource (account, project, each model deployment, Search, storage, Log Analytics, Fabric) until `provisioningState = Succeeded` and throws on `Failed`, `Canceled` or timeout. Search also waits for `status = running` and an identity. |
| MCAPS policies force `publicNetworkAccess = Disabled` | The script merges `SecurityControl = Ignore` onto the resource group (existing tags are kept) before creating anything, and tags each resource. It then re-reads the storage account and the Search service, and repairs the public endpoint if a policy flipped it. If it cannot, provisioning fails instead of publishing a broken lab. Security is unchanged: Foundry and storage are Entra only, Search accepts Entra tokens. |
| Foundry IQ entity graph needs blob soft delete on and versioning off | Set on the blob service and read back. Provisioning fails if they do not apply. |
| Soft-deleted Foundry account holds the subdomain | `CustomDomainInUse` triggers a purge of the deleted account and one retry. |
| Region has no quota or capacity | Pre-checks plus clean fallback to the next region, see [Region choice](#region-choice). |
| Fabric capacity cannot be created (quota, region) | Tries every preferred region, then logs `[WARN]` and continues. The rest of the lab still works and `FabricCapacityName` is not emitted. A paused capacity is resumed on a re-run. |
| Resource providers not registered | Registered and awaited at the start (Fabric only warns). |
| Long runs outlive the platform credential | `Update-MhhToken` is called between phases and inside every poll loop. |
| Re-runs | Every step is check-before-create, so a re-run converges to the same lab and keeps the same keys. |

## Platform admin prerequisites (once per tenant)

These cannot be set from `lab-defaults.json` or the script. The lab tenant's Fabric
administrator sets them once in the **Fabric admin portal, Tenant settings**:

- **Users can create Fabric items** (enabled for the lab users or the whole tenant).
- **Users can create ontology (preview) items** (Fabric IQ ontology).
- **Users can create and share Data agent item types (preview)**, the Fabric data agent.
- **Users can use Copilot and other features powered by Azure OpenAI**, and, if the
  capacity region differs from the Azure OpenAI region, **Data sent to Azure OpenAI
  can be processed outside your capacity's geographic region**.

Lab users also need a Fabric (Power BI) license to open the Fabric portal and create a
workspace. `"groups": ["GHCPUsers", "M365-E5-Users"]` in
[`lab-defaults.json`](lab-defaults.json) takes care of that: `M365-E5-Users` assigns a
Microsoft 365 E5 license (includes Power BI Pro), and `GHCPUsers` gives each lab user a
GitHub Copilot seat and Codespaces access for the hack repository.

## Packing and quotas (`labsPerSubscription = 10`)

| Limit (per subscription and region, typical values) | Per lab | Labs that fit |
|-----------------------------------------------------|---------|---------------|
| gpt-5.4-mini GlobalStandard, 2,000K TPM | 100K | 20 |
| gpt-5.6-luna GlobalStandard, 1,000K TPM | 50K | 20 |
| text-embedding-3-small GlobalStandard, 2,000K TPM | 50K | 40 |
| Fabric capacity quota, 64 to 512 CU | F2 = 2 CU | 32 to 256 |
| **Azure AI Search Basic services, 12 (some subscriptions 16)** | 1 | **12** |

Search Basic is the binding limit. 10 leaves headroom for a coach lab or a re-created
service. If your subscriptions have a higher Search quota you can raise it, but keep
`labsPerSubscription x capacity` below each model quota.

## Cost estimate (per attendee per day, pay as you go)

| Item | USD per day |
|------|-------------|
| Fabric F2, running 24 hours | about 8.6 |
| Azure AI Search Basic | about 2.5 |
| Model tokens (agent runs, graph extraction, embeddings) | about 3 to 6 |
| Storage, Log Analytics, Application Insights | about 0.5 |
| Functions Flex Consumption (no always-ready instances) | about 0 |
| **Total** | **about 16** (`estimatedDailyCostsUsd`) |

The Fabric capacity is the largest item and is billed only while running. Coaches can
**pause** it outside hack hours (Azure portal, Fabric capacity, Pause, or
`POST .../capacities/<name>/suspend?api-version=2023-11-01`). Re-running the script
resumes it.

## Local test run

The platform injects helpers (`Get-MhhStableHash`, `New-MhhStablePassword`,
`Get-MhhLabUser`, `Update-MhhToken`) and pre-creates the resource group, so
`deploy-lab.ps1` cannot run on its own. Use [`run-local.ps1`](run-local.ps1), which
supplies stand-ins, creates the resource group, resolves your object ID (falling back
to the `oid` claim of your access token when `Get-AzADUser` cannot reach Graph), runs
the script and prints the credentials (secrets masked unless `-ShowSecrets`).

```powershell
# Requires Connect-AzAccount and az login to the test subscription.
./run-local.ps1 -SubscriptionId <sub> -ResourceGroupName rg-iq-lab-test -Location swedencentral
```

A full first run takes about 15 to 25 minutes (Search and Fabric dominate). A re-run
takes a few minutes and changes nothing.

> `run-local.ps1` is a local helper only. The platform never runs it.

## Cleanup

The platform deletes the attendee's resource group when the event ends. For a local
test, pause the Fabric capacity if you keep the lab, otherwise delete the group:

```powershell
az group delete -n rg-iq-lab-test --yes --no-wait
```

The Foundry account goes to soft delete for 48 hours. A new run for the same user
purges it automatically when it hits `CustomDomainInUse`.
