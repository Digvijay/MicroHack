# Coach guide: Microsoft IQ, one agent, four IQs

**[Home](../README.md)**

This folder is for coaches. Participants do not see it in the Codespace explorer (the dev container hides `walkthrough`), but it is on disk.

| File | Purpose |
|---|---|
| [scenario-facts.md](scenario-facts.md) | Single source of truth for every number, date, persona and the right answer. Read it first. |
| [Solution 1](challenge-01/solution-01.md) | Setup, the blind agent, how the evaluation works |
| [Solution 2](challenge-02/solution-02.md) | Web IQ, citations, the story clock |
| [Solution 3](challenge-03/solution-03.md) | Fabric lakehouse, data agent, Fabric IQ tool, ontology |
| [Solution 4](challenge-04/solution-04.md) | Foundry IQ knowledge base and knowledge graph, with the reference [ontology v2](challenge-04/caldova-supply-v2.jsonld) |
| [Solution 5](challenge-05/solution-05.md) | Work IQ, persona trimming, untrusted content, planting an email |
| [Solution 6](challenge-06/solution-06.md) | The capstone, the reference [playbook](challenge-06/playbook.md), evaluation and Agent Optimizer |
| [Evaluation rubric](../data/eval/rubric.md) | How the 19 questions are scored |

## Timing plan

The challenges add up to 5 hours 10 minutes. With a short welcome, two short breaks, lunch and the finish, the day runs from 09:00 to 15:25:

| Time | Block | Length | Coach focus |
|---|---|---|---|
| 09:00 | Welcome, scenario, form teams (mix business and developer profiles) | 10 min | The four sources of the right answer |
| 09:10 | [Challenge 1](../challenges/challenge-01.md): the blind agent | 30 min | Everyone has a working Codespace and `caldova check` |
| 09:40 | [Challenge 2](../challenges/challenge-02.md): Web IQ | 40 min | Story clock versus live web |
| 10:20 | Break | 10 min | Check Fabric capacities are running |
| 10:30 | [Challenge 3](../challenges/challenge-03.md): Fabric IQ | 60 min | Example queries demo, on-behalf-of |
| 11:30 | Lunch | 30 min | Stagger graph builds after lunch |
| 12:00 | [Challenge 4](../challenges/challenge-04.md): Foundry IQ | 60 min | Teglbruk yes/no demo, ontology v2 |
| 13:00 | Break | 10 min | |
| 13:10 | [Challenge 5](../challenges/challenge-05.md): Work IQ | 60 min | Sales Lead versus Supply Planner, plant an email |
| 14:10 | [Challenge 6](../challenges/challenge-06.md): four IQs | 60 min | Failures first, then the playbook |
| 15:10 | [Finish](../challenges/finish.md): recap, leaderboards, feedback | 15 min | Compare team leaderboards |

That is about 6 hours 25 minutes in total, including 50 minutes of breaks and lunch. The stretch goals in Challenges 3, 4 and 6 are for fast teams; skip them to finish earlier.

## Before the day

### Tenant (once, Fabric administrator)

In the **Fabric admin portal** > **Tenant settings**, enable for the lab users (or the whole tenant):

- [ ] **Users can create Fabric items**
- [ ] **Users can create ontology (preview) items** (Fabric IQ ontology)
- [ ] **Users can create and share Data agent item types (preview)** (Fabric data agent)
- [ ] **Users can use Copilot and other features powered by Azure OpenAI**, and, if the capacity region differs from the Azure OpenAI region, **Data sent to Azure OpenAI can be processed outside your capacity's geographic region**

Lab users must be in the group **M365-E5-Users** (Microsoft 365 E5 includes the Power BI Pro license that Fabric needs) and **GHCPUsers** (GitHub Copilot and Codespaces). Both are set in [`lab-defaults.json`](../labautomation/lab-defaults.json). See [labautomation/README.md](../labautomation/README.md#platform-admin-prerequisites-once-per-tenant).

### Each lab (the day before and the morning of)

- [ ] **Resume the F2 capacity** if it was paused: Azure portal > lab resource group > Fabric capacity > **Resume**, or

  ```bash
  az rest --method post --url "https://management.azure.com/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Fabric/capacities/<name>/resume?api-version=2023-11-01"
  ```

- [ ] The dashboard shows `FabricCapacityName`. If it is missing, the lab could not create a capacity: re-run the lab deployment or plan a shared capacity for that team.
- [ ] **Work IQ emulator seed check:** open `https://<function app host>/healthz`. Expect `{"status":"ok","items":N}` with N > 0 (the bundled pack has 25 items). Then open `WorkIQViewerUrl`, sign in with the Plant Manager key and check the Inbox shows "FW: SO-9001 PV-400 delivery confirmation" and Chats show the quality hold chat.
- [ ] **Admin key** for planting emails: Azure portal > lab resource group > the `iq-wiq-...` Function App > **Settings** > **Environment variables** > `WORKIQ_ADMIN_KEY`, or

  ```bash
  az functionapp config appsettings list -g <rg> -n <function app> --query "[?name=='WORKIQ_ADMIN_KEY'].value" -o tsv
  ```

  It is not on the participant dashboard on purpose, and it only controls that one lab's emulator.
- [ ] Run the whole hack once in a coach lab and record your scores in the table below.

### After the day

- Pause the Fabric capacities if the labs stay up (the largest cost item, about 8.6 USD per lab per day while running).

## Expected scores

These numbers come from the reference runs (same 19 questions, `gpt-5.4-mini`, one run each unless noted). Your teams will vary by about 5 to 10 points from run to run.

| Run | IQs | Score (of 190) | What the jump shows |
|---|---|---|---|
| Challenge 1: no IQ | none | 63 | General knowledge only. Honest refusals score low; the web questions get partial credit for naming Esbjerg. |
| Challenge 2: + Web IQ | web | 69 | Only 3 questions need the web, so the jump is small but the answers become cited and current. |
| Challenge 3: + Fabric IQ | web, fabric | 109 | The biggest single jump: stock, orders and money (q06 to q09) go from 1 to about 10 each. |
| Challenge 4: + Foundry IQ | web, fabric, foundry | 143 | Contracts and policies (q10 to q13) pass; Teglbruk is correctly refused. |
| Challenge 5: + Work IQ | all four | 123 | **The score drops.** More tools without guidance: the agent picks one tool, trusts stale data, and offers the customer's number instead of ours. |
| Challenge 6: + playbook | all four + playbook | 148 to 154 (two runs) | The playbook tells the agent which IQ to use for what and how to combine them. |

Use the Challenge 5 dip as a live discussion point: context is necessary, orchestration is what makes it useful.

## How to read the leaderboard

```bash
caldova leaderboard
```

| Column | Meaning |
|---|---|
| Run | The `--label` of the run |
| IQs | The IQs the agent had |
| Score / Max | Sum over the questions run. A full run is out of 190. Runs with `--only` or `--upto` have a smaller max: do not compare them with full runs. |
| % and bar | Score as a percentage, one block per 5% |
| When (UTC) | Run time |

The per-question table printed by `caldova eval` has `Q`, `Ch` (challenge), `Persona`, `Needs` (IQs the question needs), `Score` (0 to 10, green from 8, yellow from 5), `Judge` (0 to 5), `Tools` and `Why` (the judge's reason). Full answers are in `src/.caldova/leaderboard.json`.

What to look for:

- A question needs an IQ the run did not have: expected low score, not a bug.
- Big jumps between two identical runs: variance. Compare two runs before concluding.
- `Judge` capped at 1 with a high answer quality: a `must_not_include` gate phrase fired. Read the answer.
- q17 low after Challenge 5: the Sales Lead agent leaked or guessed a date.

## Live demo moments

These were all observed in testing. Each makes a good 3 to 5 minute demo on the projector.

| Challenge | Moment | How to show it |
|---|---|---|
| 1 | The honest blind agent | Ask the capstone with `--iqs none`. Praise "I can't know". |
| 2 | Grounding versus the story clock | Ask the Esbjerg weather question. Today's web disagrees with the story. |
| 3 | Data agents need examples | `caldova fabric-iq agent --no-examples`, ask q06 and q09 ("HX-220 housing", "Brennmark" exact match fail), then `caldova fabric-iq agent` and ask again. |
| 3 | On behalf of the user | Show the `UserEntraToken` connection and the Power BI audience. |
| 4 | Entity resolution | Explain "PV-400" versus "PV-400 pump valve" as two nodes, and the `rdfs:comment` naming rules in v1. |
| 4 | You only get what your ontology asks for | "Can we buy HX-220 from Teglbruk Metall AS?" with `--kb graph` (yes) and `--kb documents` (no). Then build v2 and ask the graph again (on quality hold). |
| 4 | Phrasing | "Which supplier cannot ship?" read as "no `shipsFrom` port". Show the printed GQL. |
| 5 | Permissions change what an agent knows | Same question as Sales Lead (stale "lands Tuesday 8 December") and Supply Planner (14 and 16 December). |
| 5 | Untrusted content | The injection line in the IT news email, in the viewer, and the untrusted-content notice in the `retrieve` payload. |
| 5 | Plant an email live | `POST /admin/items` with the admin key, then teams ask their agent. See [Solution 5](challenge-05/solution-05.md#live-demo-plant-a-new-email). |
| 6 | Four IQs are not enough | Without a playbook: one tool only, lakehouse ETA over the email, offering 2,000 instead of 1,800, and the cold draft that copied "4,000 by Friday" (judge 0). |
| 6 | The playbook | Add [playbook.md](challenge-06/playbook.md) and rerun `--only q16,q18,q19`. |

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `No active Fabric F-SKU capacity found` | Capacity paused or wrong `FABRIC_CAPACITY_NAME` | Resume the capacity, check the name |
| Cannot create a Fabric workspace or data agent | Tenant settings or no Fabric license | See [Before the day](#before-the-day) |
| `FeatureNotAvailable` on `caldova fabric-iq ontology` | Ontology tenant setting off | Enable "Users can create ontology (preview) items", or continue without the ontology |
| Data agent "no rows" | No example queries | `caldova fabric-iq agent` (with examples) |
| Graph source "ontology locked" or ignores changes | The ontology is fixed per knowledge source | Create a new version file and run `caldova foundry-iq graph --ontology <new name>` |
| Graph build slow or failing for many teams | Shared `gpt-5.6-luna` quota | Stagger graph builds, demo from the coach lab |
| HTTP 401 from Work IQ | Wrong key, or a key copied with spaces or a line break | Copy the key again; the header is `Bearer <key>` |
| Viewer or `/mcp` returns 503 | No persona keys on the Function App | Check the Function App settings |
| Strange characters on Windows | Console encoding | `$env:PYTHONIOENCODING='utf-8'` (the dev container sets `PYTHONIOENCODING=utf-8`) |
| `caldova: command not found` | New `PATH` not loaded | New terminal, or `cd src && uv run caldova ...` |
| Storage upload denied in the portal | Shared key access is disabled | **Switch to Microsoft Entra user account** |
| Scores jump between runs | Model and judge variance | Run twice, compare |

## Business and developer participants

- Mix profiles in each team. Business participants build in the portals; developers run the `caldova` commands. Both share one Codespace terminal for the evaluation.
- The evaluation always scores the **code-built** agent (`caldova-<persona>`), from the state in `src/.caldova/state.json`. A business-only team must run the setup commands once (`caldova fabric-iq load`, `caldova fabric-iq agent`, `caldova foundry-iq documents`) before the evaluations of Challenges 3 and 4. The challenge pages say so.
- Recommend the same names in the portal as in the code (`caldova-iq`, `caldova_lakehouse`, `CaldovaOperations`, `caldova-docs-kb`), so both paths share resources.

---

**[Home](../README.md)**
