# Coach guide: Alex sleeps through 02:13

**[Home](../README.md)**

This folder is for coaches. It has the full, click-by-click solutions, the exact instructions to paste into each agent and the troubleshooting notes. Participants should solve the [challenges](../challenges/) first; send them here only when they are stuck after the hints.

| File | Purpose |
|---|---|
| [scenario-facts.md](scenario-facts.md) | Single source of truth for every name, serial, time, price, rule and the right answer. Read it first. |
| [Solution 1](challenge-01/solution-01.md) | Lights on: `.env`, the portals, documents to Blob, lakehouse in Fabric, the paper map |
| [Solution 2](challenge-02/solution-02.md) | Who's asking: `strandvik-customer-service`, agent card, incoming A2A, the IAM role, the board |
| [Solution 3](challenge-03/solution-03.md) | Know the business: ontology (and the fallback), Fabric data agent, `strandvik-parts` |
| [Solution 4](challenge-04/solution-04.md) | Why didn't it take the unit: Foundry IQ knowledge base, `strandvik-service`, knowledge graph stretch |
| [Solution 5](challenge-05/solution-05.md) | Sam in Singapore: `alex-agent` with the Work IQ emulator, playing Sam, auto-Sam, trimming |
| [Solution 6](challenge-06/solution-06.md) | The night shift: `strandvik-logistics`, A2A orchestration, the 04:10 proposal |
| [Solution 7](challenge-07/solution-07.md) | Alex makes the call: approval, evaluations, traces, cost, the 02:13 replay |
| [Finish](finish/solution-finish.md) | The John Blund test: scoring and the closing talk |
| [Lab automation](../labautomation/README.md) | What the lab provisions, outputs, RBAC, known waits, re-runs |
| [Work IQ emulator](../labautomation/workiq-emulator/README.md) | Viewer, playing Sam, auto-Sam, the board, admin endpoints |

## The day in one paragraph

Teams are Strandvik's agent team. The lab pre-builds Kolvo's side (Maria's agent and two rival suppliers) in the **kolvo** project. Teams build five agents in the **strandvik** project: `strandvik-customer-service` (the door), `strandvik-parts` (Fabric IQ), `strandvik-service` (Foundry IQ), `strandvik-logistics` (Web IQ) and `alex-agent` (Work IQ plus A2A to the three specialists). A coach or teammate plays Sam in the Work IQ viewer. At the end, Kolvo's procurement board replays 02:13 against every team's agent and the teams take the John Blund test.

## Timing plan

About 7 hours of challenges. A full day with breaks:

| Time | Block | Length | Story clock | Coach focus |
|---|---|---|---|---|
| 09:00 | Welcome, the story so far (read the 02:10 and 02:13 beats from Johan Wallquist's keynote), form teams | 15 min | | Mix business and builder profiles in each team. Solo hackers are fine. |
| 09:15 | [Challenge 1](../challenges/challenge-01.md): Lights on | 45 min | 02:10 | Everyone has `.env` and all three portals. Fabric workspace exists. |
| 10:00 | [Challenge 2](../challenges/challenge-02.md): Who's asking? | 45 min | 02:13 | Make every team run the board **before** the fix. Watch the 3 to 5 minute role wait. |
| 10:45 | Break | 10 min | | Check every lab's board shows Strandvik answering. |
| 10:55 | [Challenge 3](../challenges/challenge-03.md): Know the business | 75 min | 03:10 | Ontology tenant setting: decide on the fallback in the first 10 minutes. |
| 12:10 | Lunch | 40 min | | Capacities stay on. |
| 12:50 | [Challenge 4](../challenges/challenge-04.md): Why didn't it take the unit? | 60 min | 03:41 | Run the vote on Sam's note. "A note is a reason to ask." |
| 13:50 | [Challenge 5](../challenges/challenge-05.md): Sam in Singapore | 60 min | 03:52 | Play Sam for teams without a spare person, or point them at auto-Sam. |
| 14:50 | Break | 10 min | | |
| 15:00 | [Challenge 6](../challenges/challenge-06.md): The night shift | 75 min | 04:10 | A2A one tool at a time. Fabric over A2A fallback if needed. |
| 16:15 | [Challenge 7](../challenges/challenge-07.md): Alex makes the call | 45 min | 07:30 | Start evaluations early. Then the 02:13 replay on the projector. |
| 17:00 | [Finish](../challenges/finish.md): the John Blund test | 15 min | Thu 06:00 | Score the five questions with each team. |

Short on time? Drop the stretch goals (knowledge graph in challenge 4, real handover in challenge 7), and in challenge 6 let teams orchestrate two specialists instead of three.

## Before the day

### Once per tenant (Fabric administrator)

In the **Fabric admin portal** > **Tenant settings**, for the lab users or the whole tenant:

- [ ] **Users can create Fabric items**
- [ ] **Users can create ontology (preview) items**. If this stays off, challenge 3 uses the documented fallback.
- [ ] **Users can create and share Data agent item types (preview)**
- [ ] **Users can use Copilot and other features powered by Azure OpenAI** (and, if the capacity region differs from the Azure OpenAI region, **Data sent to Azure OpenAI can be processed outside your capacity's geographic region**)

Lab users must be in the groups from [`lab-defaults.json`](../labautomation/lab-defaults.json) (Fabric licence through Microsoft 365 E5, Codespaces).

### Per lab (the evening before)

Sign in with one lab user and check:

- [ ] The **kolvo** project shows `maria-procurement`, `nordic-drive-parts` and `hallberg-repair`.
- [ ] The **strandvik** project is empty (no agents), and the three model deployments exist.
- [ ] The board (`/board` on the emulator host) loads after sign-in. **Run 02:13** fails with the red hint about Strandvik: that is the correct starting state.
- [ ] The Fabric capacity is **Active** (Azure portal > the `iqcap...` resource). Resume it if it was paused.
- [ ] The `documents` container is empty, and Storage browser opens it with your Entra account.

### In the room

- A big **story clock** on a second screen (any full-screen clock page, or a slide with the time). You move it forward at every challenge.
- Printed [scenario facts](scenario-facts.md), one per coach.
- One spare laptop or browser profile signed in to the Work IQ viewer as **Sam**, for playing Sam across teams.

## How to run the clock

The clock is the story's spine. At the start of every challenge:

1. Set the story clock to the challenge time (02:10, 02:13, 03:10, 03:41, 03:52, 04:10, 07:30).
2. Read the story beat from the challenge out loud, in 30 seconds. The lines are from Johan Wallquist's keynote; read them as they are.
3. Ask the one question of the moment:
   - 02:13: "Who's asking, and what are they allowed to do?"
   - 03:41: **the vote.** "Is Sam's note enough to take the unit? Hands up if yes." Then: "A note is a reason to ask. It's not a decision."
   - 07:30: **the vote.** "Who flies in the new unit? Who takes Poliden's unit?" Then reveal: Alex does both.
   - The replay: "Which supplier is your company today? The distributor, the repair shop or Strandvik?"
4. At the end of the challenge, ask one team to show their success criteria in two minutes.

## How to play Sam

Sam is Strandvik's key account manager for Poliden, at a trade fair in Singapore (UTC+8, 10:52 when the agent asks). Sam is friendly, busy and protective of Poliden.

1. Open the viewer (`WORKIQ_VIEWER_URL` from the team's `.env`, or the emulator host + `/viewer`) in a **private window**, and sign in with the team's **Sam key** (`WORKIQ_KEY_SAM`).
2. Open **Chats** > **Kolvo press line 2, SD-900**. The thread refreshes every 4 seconds; agent posts are highlighted and say "Alex's agent (on behalf of Alex)".
3. When the agent asks, reply under **Post as: Sam**. The scripted answer:

   > Yes, it is moving two weeks. Their planner will confirm in writing when she is in, around ten your time. Fine by me, as long as Poliden gets the new unit in time.

4. Improvise inside the facts only. Good improvisations: "Which unit would Poliden get instead?", "Who pays the extra freight?" (answer: the KAM who reallocates carries the cost risk, RES-02). Never change the facts (the stop moves two weeks, the planner confirms around 10:00).
5. If the agent's question is vague ("Hi Sam, any news?"), answer like a busy person: "I am at a trade fair in Singapore this week. Please keep it short: what do you need from me?" That teaches the business role to write a better question.

Teams can play Sam themselves: anyone signed in to the viewer with a lab key can post as any member of the thread.

## Auto-Sam (solo hackers)

- Turn it on with the **auto-Sam** button above the Kolvo thread in the viewer (or at deploy time with `WORKIQ_AUTO_SAM=true`).
- Auto-Sam replies about 30 seconds after any post by someone other than Sam that **mentions Sam** (`Sam` or `@Sam`). About the Poliden unit, reservation, stop, Rotterdam or RSV-2291, it gives the scripted answer; otherwise the "keep it short" answer.
- There are no timers: the reply is posted by the next request (any MCP call, viewer refresh). The agent's turn ends before Sam answers, so the participant asks the agent again ("Did Sam answer?").
- It is deterministic and uses no model.

## The board

Kolvo's procurement board is at the emulator host + `/board`. Sign in with any lab key. It shows Maria's 02:13 request, one card per supplier (Strandvik Drives, Nordic Drive Parts, Hallberg Repair Services) and a scorecard.

| State | What the board shows | Why |
|---|---|---|
| Before challenge 2 | All three suppliers "no answer", a red hint about Strandvik | Foundry fails Maria's **whole** response with `tool_user_error` when any A2A target is unreachable |
| After challenge 2 (and the 3 to 5 minute wait) | Strandvik: case number and handover. Nordic: "in stock, ships today" from a stock list, cannot hold. Hallberg: office hours, answers after 08:45 | All three A2A targets reachable |
| After the challenge 7 stretch | Strandvik's card carries the proposal and "final confirmation from Alex by 07:30" | Customer service hands over to `alex-agent` over A2A |

- **Run 02:13** calls `maria-procurement` through the Responses API with the emulator's managed identity. A run takes 30 to 90 seconds; the button waits up to 180 seconds. One run at a time per lab. The last run stays on screen until the emulator restarts.
- The scorecard (Answered, Answered in time, Grounded and holds the unit, Respects quote only, Final confirmation by a person) is keyword-based. It starts the conversation; it does not judge.
- For the replay, put each team's board on the projector in turn and ask the replay question.

## Reset tips

| To reset | Do this |
|---|---|
| Chat posts in the Kolvo thread (after evaluations or a messy rehearsal) | Coach page `/viewer/coach` > **Reset the thread** (admin key in the form), or `POST /manage/thread/reset`: removes the live posts, stops the story clock. `POST /manage/reset` also reloads the whole seed. To stamp a beat at its story time, set the clock first (coach page, or `POST /manage/clock` with `{"time": "07:30"}`). The admin key is `WORKIQ_ADMIN_KEY` in the Function App's **Environment variables** (Azure portal > lab resource group > `iq-wiq-...` > Settings). |
| A Strandvik agent | Delete it in the Foundry portal (strandvik project > Agents > the agent > Delete) and create it again. Re-run notebook 01 for it (it switches on incoming A2A and grants the caller's role for the new identity). |
| The whole Strandvik side | Delete all agents in the strandvik project, the knowledge base and its source. Nothing in the automation depends on them. |
| Kolvo's agents (someone edited them) | Run `labautomation/setup-kolvo.ps1` (needs an Az PowerShell context with Owner on the resource group). It is idempotent. |
| Fabric | Delete the lakehouse, ontology and data agent items, then load again (portal or notebook 00). |

```powershell
# Reset the Work IQ emulator (coach). $adminKey from the Function App's environment variables.
Invoke-RestMethod -Method Post -Uri "https://<emulator host>/manage/reset" -Headers @{ Authorization = "Bearer $adminKey" }
```

The emulator keeps its state in memory: a restart of the Function App also clears posts, the auto-Sam switch and the last board run.

## Common failures

| Symptom | Cause | Fix |
|---|---|---|
| Board or Maria's playground: `tool_user_error` ("A user error occurred while executing a tool call") | `strandvik-customer-service` missing, incoming A2A off, or Maria's identity has no **Foundry Agent Consumer** on the strandvik project | Fix the missing piece, then **wait 3 to 5 minutes** (about 4 in testing) |
| Agent card check returns `Project not found` | Brand-new project, public A2A endpoint not ready yet | Wait a few minutes |
| Role assigned on the wrong scope or to the wrong identity | Granted on the kolvo project, or to the target agent instead of the caller | The **caller** needs **Foundry Agent Consumer** on the **target** (agent or strandvik project). Re-run notebook 01 with the right `AGENT_NAME` (target) and `CALLER`; portals cannot pick agent identities yet |
| Parts agent fails only when called by another agent (`tool_server_error`) | Fabric IQ needs a person; the A2A tool used agent identity | Use **OAuth Identity Passthrough** on the `strandvik-parts-a2a` tool (solution 6) |
| Alex's whole run fails after adding A2A tools | One specialist unreachable (no incoming A2A, or `alex-agent` identity lacks the role) | Add and test one A2A tool at a time |
| Embedding model missing in the knowledge source form | The form only lists deployments that existed when the page loaded | Reload the page |
| Knowledge source fails or stays empty | Container empty, or Search identity roles missing | Upload the documents; check Storage Blob Data Reader for the Search identity |
| Chat completions model dropdown only shows "Browse more models" | gpt-5.x models not offered there | Leave it empty |
| Fabric: HTTP 430 on Load to Tables | F2 capacity busy | Wait 20 seconds and retry |
| Data agent cannot see a new table | SQL analytics endpoint metadata not synced | Refresh the SQL endpoint metadata |
| No **Ontology** item in Fabric, or `FeatureNotAvailable` | Tenant setting off | Fallback in [solution 3](challenge-03/solution-03.md#fallback-ontology-on-paper) |
| `strandvik-parts` works alone, fails when `alex-agent` calls it | Fabric IQ tool needs a signed-in user; over A2A there is none | Fallback in [solution 6](challenge-06/solution-06.md#if-the-parts-agent-fails-over-a2a) |
| MCP tool returns 401 | Header value missing `Bearer ` or wrong key | `Authorization: Bearer <WORKIQ_KEY>` (Alex's key) |
| Agent post never appears in the thread | Agent posted to the wrong chat id, or did not call `create_entity` | Check the tool call output; tell the agent the exact path in its instructions |
| Evaluation wizard rejects synthetic data | Minimum is 15 rows | Use 15 or more, or the provided dataset (27 rows) |
| Monitor > Cost is empty | Cost views lag 8 to 24 hours | Use token counts in traces and the evaluation grid |
| Somebody built a Workflow | Foundry portal Workflows are being retired | Orchestrate with A2A from `alex-agent` |

## Solutions

- [Solution 1: Lights on](challenge-01/solution-01.md)
- [Solution 2: Who's asking?](challenge-02/solution-02.md)
- [Solution 3: Know the business](challenge-03/solution-03.md)
- [Solution 4: Why didn't it take the unit?](challenge-04/solution-04.md)
- [Solution 5: Sam in Singapore](challenge-05/solution-05.md)
- [Solution 6: The night shift](challenge-06/solution-06.md)
- [Solution 7: Alex makes the call](challenge-07/solution-07.md)
- [Finish: the John Blund test](finish/solution-finish.md)

**[Home](../README.md)**
