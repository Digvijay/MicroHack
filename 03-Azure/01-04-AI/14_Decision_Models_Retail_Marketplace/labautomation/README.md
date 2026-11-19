# labautomation — Decision Models for a Retail Marketplace

[`deploy-lab.ps1`](deploy-lab.ps1) gives each attendee one Foundry resource with three model
deployments. There is no facilitator pre-setup and no database: the listings, photos and
recorded reference runs ship in `src/data/`.

## What gets provisioned per attendee

| Resource | Purpose |
|----------|---------|
| Foundry resource (`AIServices`, S0, `dm-<hash>`) | Hosts the deployments. **Keyless**: `disableLocalAuth = true`, attendees sign in with Entra ID |
| Deployment `decision`: **Microsoft-Decision-1.1**, DataZoneStandard x500 | The gate's decision model (`/providers/microsoft/v1/systemone`) |
| Deployment `gpt-6-luna`: **gpt-6-luna**, DataZoneStandard x40 | Azure OpenAI **Decisions API** (`/openai/v1/decisions`) and the generative baseline (Responses API) |
| Deployment `decision-judge`: **Microsoft-Decision-1**, DataZoneStandard x50 | Challenge 6: judge for Foundry evaluators. [Decision-1.1 isn't supported as a judge yet](https://learn.microsoft.com/azure/foundry/observability/how-to/decision-model-judge) |
| Foundry project `marketplace-gate` | Lets attendees open the deployments in the Foundry portal; optional evaluation logging |
| RBAC per attendee: **Cognitive Services User** + **Foundry User** (formerly Azure AI User) | Call the models; run evaluations with a decision-model judge |

## What the attendee receives on their dashboard

| Credential | Goes into `src/.env` |
|------------|----------------------|
| `DecisionEndpoint` | `DECISION_ENDPOINT` |
| `OpenAIEndpoint` | `OPENAI_ENDPOINT` |
| `DecisionDeployment`, `LunaDeployment`, `JudgeDeployment` | `DECISION_DEPLOYMENT`, `LUNA_DEPLOYMENT`, `JUDGE_DEPLOYMENT` |
| `DecisionCapacity`, `LunaCapacity` | `DECISION_CAPACITY`, `LUNA_CAPACITY` (the client paces itself to these) |
| `FoundryProjectEndpoint` | Optional `PROJECT_ENDPOINT` |
| `ResourceGroupName` | — (find the resource in the portal) |

## Sizing and quota

One capacity unit is **1 request/min + 1,000 tokens/min** for all three models (verified from
the deployments' `rateLimits`). Data Zone quota is shared by every lab in the subscription:

| Model | DataZoneStandard quota (default) | Per lab | 8 labs |
|-------|-------------------|---------|--------|
| gpt-6-luna | 333 | 40 | 320 |
| Microsoft-Decision-1.1 | 4,500 | 500 | 4,000 |
| Microsoft-Decision-1 | 4,500 | 50 | 400 |

`gpt-6-luna` is the binding constraint, which is why `labsPerSubscription` is 8 and the
challenges run live on a 24-listing starter set and use **recorded runs** for the full
603-listing statistics.

> [!IMPORTANT]
> Azure's rate limiter counts the **size of the request**, not the tokens you are billed for.
> A photo sent as base64 counts in full: the gate's 384 px JPEGs cost about 3,500 tokens of
> rate limit each, although usage reports a few hundred. Measured: a text request drew ~830
> tokens from the limit, the same request with a 48 KB image ~15,000.

`estimatedDailyCostsUsd` is low because everything is pay-per-token: a full live run of the
starter set on all three models costs well under one US cent.

## Deployment robustness

| Concern | How the script handles it |
|---------|---------------------------|
| A region without one of the models, or without quota left | Before creating anything, the script checks each preferred region's model catalog (`DataZoneStandard`, exact version) **and** remaining quota, and picks the first that fits. It fails with the reason for every region if none fits. |
| A control-plane call fails | Every ARM call goes through `Invoke-MhhArm`, which throws on any non-2xx. |
| Two deployments on one account at once | Deployments are created one at a time; a 409 ("another operation in progress") is retried. Each must reach `Succeeded`, or the script fails. |
| "Provisioned" isn't "working" | Step 6 calls every API the challenges use — Decision-1.1 with text **and an image**, the Decisions API, the Responses API and the judge — and checks for a typed answer. Credentials are emitted **only after all probes pass**. The probes retry for up to 12 minutes while role assignments propagate. |
| MCAPS policies disabling public network access | The resource group is tagged `SecurityControl = Ignore` (the standard MCAPS exemption) and the script verifies `publicNetworkAccess = Enabled` after creation. Local auth stays disabled, so the endpoint still needs an Entra token with a data role. |
| Re-runs after a partial failure | Every step is idempotent: existing resources are checked, and a failed or wrongly sized deployment is re-created. |

The deployer identity is granted **Cognitive Services User** on the resource only so the
readiness probes can call the models.

## Local dry run

The platform injects `Get-MhhStableHash` and pre-creates the resource group, so
`deploy-lab.ps1` can't run directly outside the platform. Use
[`walkthrough/run-local.ps1`](../walkthrough/run-local.ps1), which supplies the helper,
creates the resource group and passes your own object ID:

```powershell
# Requires: Connect-AzAccount to the test subscription, Az.Accounts and Az.Resources.
../walkthrough/run-local.ps1 -ResourceGroupName rg-decision-hack-test -Location swedencentral
```

## References

- [Deploy and use Microsoft-Decision-1.1](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [Azure OpenAI Decisions API](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
- [Use a decision model as an evaluation judge](https://learn.microsoft.com/azure/foundry/observability/how-to/decision-model-judge)
- [Azure OpenAI starter (Bicep for gpt-6-luna Decisions)](https://github.com/Azure-Samples/azure-openai-starter)
