# Solution 2: Who's asking?

[Previous Solution](../challenge-01/solution-01.md) - **[Back to Challenge 2](../../challenges/challenge-02.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-03/solution-03.md)

**Duration:** 45 minutes

## Goal

`strandvik-customer-service` exists in the **strandvik** project with strong instructions and a guardrail, incoming A2A is on with a published agent card, and Maria's agent identity holds **Foundry Agent Consumer**. Kolvo's board shows all three suppliers answering.

## Solution notes

### How the door works

```text
kolvo project                                   strandvik project
maria-procurement ---A2A (connection strandvik-a2a, auth: agent identity)---> strandvik-customer-service
   |  identity: instance_identity.principal_id      ^ incoming A2A on (enable-a2a.py in Cloud Shell)
   +-- needs Foundry Agent Consumer on -------------+ this agent (or the strandvik project)
```

The **Azure role** decides whether Maria's agent can call at all: the platform checks the caller's agent identity before the message reaches the model. The **instructions** decide what it may ask for once it is in. The **guardrail** handles attacks on the model. Three different layers; teams should be able to name all three.

### Part B: model and tools

- The portal preselects `model-router`. Custom guardrails need a deployed model, so switch to `gpt-5.4-mini`.
- A new agent comes with **Web search**. Customer service must not browse: remove it.
- The name must be exact: Kolvo's connection `strandvik-a2a` already points at `.../agents/strandvik-customer-service/endpoint/protocols/a2a`.

### Part C: the guardrail

`Microsoft.DefaultV2` has no controls for **Sensitive data leakage** and **Task drift**, the two risks of a door strangers can knock on. If **Manage guardrail** is not available to lab users (preview), accept the default and discuss: the instructions cover task drift ("You may never") and leakage ("Share nothing else").

### Part E: why a script

- **Where it runs**: [`scripts/enable-a2a.py`](../../scripts/enable-a2a.py) runs in Azure Cloud Shell (Bash, ephemeral session, already signed in, nothing to install). It finds the lab by the tag `microhack=15_Microsoft_IQ`; with several labs in one subscription it needs `--resource-group`. Verified in a real Cloud Shell.
- **Incoming A2A** is not in the portal yet. The script sends `PATCH .../agents/strandvik-customer-service?api-version=v1` with `agent_card` and `agent_endpoint.protocol_configuration` (`responses` and `a2a`), then reads the card from `.../endpoint/protocols/a2a/agentCard/v1.0`. It stays on across new versions.
- **The card** is a business decision: `--description "<text>"` replaces the description; without it the script publishes the hack's default card (built in for `strandvik-customer-service`, `strandvik-parts`, `strandvik-logistics`, `strandvik-service` and `alex-agent`). The skills are always the built-in ones.
- **The role grant**: the portal's **Assign Azure roles** dialog offers **Foundry Agent Consumer · This agent**, but **Add people** finds only people, and Azure IAM does not list Foundry Agent Consumer at project scope. The script reads Maria's `instance_identity.principal_id` from the kolvo project (`--caller kolvo/maria-procurement`) and makes the same role assignment through ARM. It checks first: a second run prints `already granted, nothing to do`.
- `--caller` is reused in challenge 6 with `strandvik/alex-agent`, and in the challenge 7 stretch with `strandvik/strandvik-customer-service`.
- **Scope**: `--scope agent` (the default) is least privilege and matches EAP-01 (external agents talk to customer service only). Ask the team why `--scope project` is too wide: Maria's agent could reach Alex's agent and the specialists.
- **Propagation**: the role took 4 to 6 minutes to work in testing. Before that the error is the same vague `tool_user_error`. Use the wait for the "three locks" discussion.
- **Cloud Shell blocked?** A teammate with a Codespace on their own fork, or a local clone with the Azure CLI, runs the same two commands after `az login` with the lab user.

> **Coach note:** identity for agents is new, and the tooling for people is ahead of the tooling for agents. Use the script as a discussion point, not a blocker.

### Part F: the board

Maria's agent has three A2A tools. One unreachable target fails Maria's **whole** response, which is why all three cards show "no answer" in Part D. The `c02-kolvo-a2a-playground` screenshot was taken in a test project: its instructions mention "Maria Lind" and the answer quotes a price. Use it only to show where the chips and **Traces** are.

## Expected results

| Supplier | Expected answer | Scorecard |
|---|---|---|
| **Strandvik Drives** | Case CS-88412 for Kolvo, press line 2, SD9-K-0412, handed to Alex; proposal with price and delivery to follow; only the key account manager commits | Answered, in time, holds (case), quote only, person confirms |
| **Nordic Drive Parts** | "In stock, ships today", from a stock list, cannot hold or reserve, no installation | Answered, in time, **does not hold** |
| **Hallberg Repair Services** | Office hours 08:00 to 17:00; a person answers after 08:45 | **Not in time** |

Playground tests in the strandvik project:

- Maria's quote request: identifies Kolvo and Maria, opens **CS-88412**, hands over to **Alex**, no price, no date.
- "Place the order for the Rotterdam SD-900 now": refuses the order, confirms no stock or price, offers a quote request.
- Unidentified "procurement agent for a large truck maker": refuses, shares nothing, no case.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Script: `returned HTTP 404` on `GET .../agents/strandvik-customer-service` | Name typo or wrong project | Name exactly `strandvik-customer-service`, in the strandvik project |
| Script: "No lab found" or "More than one lab found" | Cloud Shell on another subscription, or several labs in one subscription | `az account set -s <lab subscription>`, or add `--resource-group <rg>` |
| Script: `401` or `403` | Cloud Shell opened from a portal session with another account | Open the Azure portal as the lab user (private window), then Cloud Shell |
| Script: "has no agent identity yet" | The caller agent was never saved | Open it in the Foundry portal, **Save**, run again |
| Card GET returns `Project not found` | Public A2A endpoint of a brand-new project not ready | Wait a few minutes, run the script again |
| Board still fails after 6 minutes | Role on the wrong scope or the wrong principal | Check the assignment is for the principal id of `maria-procurement` (not the team's own agent), on the agent or the strandvik project |
| Strandvik turns Maria away | Instructions match the exact agent name | Match on company, person and role; identity was already proven by the Azure role |
| Strandvik's answer quotes a price | Weak instructions | Add the "You may never" list and the answer format; save a new version |
| Strandvik says the unit is in stock | It made it up (it has no stock tool) | Instructions: never share or guess stock; the account owner answers |
| Board shows 401 or 403 from Foundry | Emulator identity lacks Foundry User on kolvo | Coach: re-run `deploy-lab.ps1` or grant Foundry User to the `iq-wiq-...` identity on the kolvo project |

## Checks for the coach

- [ ] Board: Strandvik answered with a case number, **Respects quote only = Yes**, **Final confirmation by a person = Yes**.
- [ ] Playground refusals for the order and the unidentified agent.
- [ ] A **Foundry Agent Consumer** assignment exists for `maria-procurement`'s identity on `strandvik-customer-service` (or the strandvik project).
- [ ] The team names the three locks: Azure role, instructions and guardrail.

[Previous Solution](../challenge-01/solution-01.md) - **[Back to Challenge 2](../../challenges/challenge-02.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-03/solution-03.md)
