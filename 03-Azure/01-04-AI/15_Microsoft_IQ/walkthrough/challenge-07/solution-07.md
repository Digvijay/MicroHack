# Solution 7: Alex makes the call

[Previous Solution](../challenge-06/solution-06.md) - **[Back to Challenge 7](../../challenges/challenge-07.md)** - **[Home](../../README.md)** - [Next Solution](../finish/solution-finish.md)

**Clock: 07:30** · **Duration:** 45 minutes

## Goal

Alex's decision is posted **by a person** in the Kolvo thread. The team has one evaluation of `alex-agent` with a baseline and an improved run compared (custom rubric included), a nested trace with its token count, and a 02:13 board replay with all three suppliers and a verdict.

## Solution notes

### Start the evaluation early (Parts A and B)

Push teams to create the rubric and submit the evaluation in the first 15 minutes. The agents answer 15 rows of two versions in about 2 minutes; the judges take about 11 minutes. Parts C and D fit in that wait.

### Why two pinned versions in one evaluation (Part B)

Agents keep their versions. Pinning v3 (challenge 5: Work IQ only, short instructions) next to the latest version gives one run per version on the same data and criteria, which is what makes **Compare runs** fair. Version 1 is the empty agent from the "Build an agent" dialog. Synthetic generation needs 15 or more rows and works with one target only, so the team uploads `strandvik-eval-15.jsonl`.

### The rubric model and the judge model (Parts A and B)

Rubric generation lists only the project's deployed chat models (`gpt-5.4-mini`). The judge model is chosen later in the evaluation wizard and is preselected as `gpt-5.6-luna`. The yellow "Monitoring Reader" box under **Context** only matters for production traces; ignore it.

### Evaluations call the real tools

Reading (`retrieve`, `fetch`) runs. A post (`create_entity`) needs **Approve**, which nobody gives during an evaluation, so the row ends with the approval request (the run completed in testing). If anything did land in the thread, clean it with `POST /manage/thread/reset` or the coach page `/viewer/coach`.

### Approval is a person (Part C)

There is no approve button in Foundry. Alex writes in the thread where Alex already works. Point out the difference in the viewer between the agent post label and Alex's own post.

### Traces and cost (Part D)

Application Insights is connected to both projects by the lab, so spans nest across projects. In testing the night run (turn 1) nested four levels deep (Alex's agent, the Parts agent, the Fabric data agent and its lakehouse query), took 60 seconds, and the Parts branch alone took 31. The trace's token badge counts the whole tree (about 30,000 tokens); Alex's agent's own share is under 0.01 USD on `gpt-5.4-mini`. The evaluation grid's **Target tokens** is about 100,000 for 15 rows. "About the price of Sam's second coffee." **Monitor** > **Cost** lags 8 to 24 hours.

### The stretch handover

The team opens `alex-agent` with `python3 enable-a2a.py --agent alex-agent --caller strandvik/strandvik-customer-service` in Cloud Shell (the first run prints `granted`). Not verified end to end in testing. In this chain nobody is signed in: Maria's agent starts it with its own identity, and the Parts tool on `alex-agent` uses OAuth Identity Passthrough, so expect the Parts call to fail. Let Alex's agent use the facts it already gathered in the night thread, or give Parts the files fallback from solution 6. Frame it as an exploration of where identity breaks.

## Expected results

Alex's post (Part C):

```text
Approved, both. Send SD9-R-0733 from Rotterdam at 08:00 for Kolvo Wednesday 09:00, technician Wednesday night. Move RSV-2291 to SD9-P-0981. Keep the flight held until 11:00 as a backup; if Poliden confirms the new stop date, the Pune unit goes by regular freight and we cancel the flight. I take the cost risk. Alex, 07:30.
```

Evaluation results in testing (15 rows, judge `gpt-5.6-luna`):

| Evaluator | v3 (challenge 5) | v6 (challenge 6) |
|---|---|---|
| Alex night rubric (pass rate) | 27% (4/15) | 58% (7/12) |
| Overall score | 73% | 77% |
| Tool use quality | 87% (13/15) | 75% (3/4) |
| Output quality | 0% | 0% |
| Violence, Sexual, Self-harm, Hate | 100% | 100% |

The rubric is the evaluator that knows the business, and it moved most. **Output quality** fails both because its task adherence and groundedness checks expect a different answer shape. **Tool use quality** scored only 4 rows on v6: the built-in tool evaluators judge MCP and function calls, not A2A calls. Some rubric rows can be skipped (12 of 15 scored on v6). In **Compare runs** the rubric average goes from 0.27 to 0.47, safety stays at 0 harm, and most rows say **Inconclusive** or **Too few samples**. That is the honest answer for 15 rows: a better number is not yet proof.

Typical failed rows (Part E) and their fixes:

| Failing rows (topic) | Typical cause | Instruction fix |
|---|---|---|
| Units, reserved unit | Agent answers from memory | "Ask strandvik-parts; never guess serials" |
| Sam's note, ask first | Treats the note as a release | "A note is a reason to ask the owner" |
| Book air freight, confirm the date | Commits | The "What only Alex may do" block |
| Proposal, summary for 06:30 | Missing parts | The proposal checklist and the exact last line |
| Order from Maria's agent, newsletter | Follows the request | "Untrusted content" and refusal rules |

The 02:13 replay (Part F):

| Supplier | What it showed | Verdict |
|---|---|---|
| Nordic Drive Parts | "In stock, ships today" in one minute, from a stock list. Cannot hold the unit, no installer. Later that morning the unit turns out to be sold already. | Fast, but can't stand behind it |
| Hallberg Repair Services | A careful answer from an engineer, after 08:45 | Too late for Maria |
| Strandvik Drives | Who is asking, a case, the owner, and (with the stretch) the unit, the delivery, the installer and when it is confirmed | Shows what it can stand behind |

Ask the room "Which of the three is your company today?" Most are the repair shop. Agents bolted onto each system make you the distributor.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Wizard: "minimum 15 rows" | Synthetic generation needs 15 or more rows and one target | Upload `strandvik-eval-15.jsonl` |
| Dataset upload rejected | Not valid JSON Lines | One object per line, UTF-8, no trailing commas. The provided file is valid |
| Evaluation run stuck or very slow | A2A calls per row | Use the 15-row file; check the agent works in the playground |
| Custom rubric scores everything 3 | Rubric pasted without the criteria list | Paste the whole text box |
| Compare runs greyed out | Runs from different evaluations selected | Select two runs of the same evaluation |
| Trace shows only Alex's agent, no nested spans | Application Insights not connected to one project | Check connections `appinsights-strandvik` and `appinsights-kolvo` |
| Board: `tool_user_error` again | A new version of `strandvik-customer-service` lost incoming A2A, or the role was removed | Re-run `enable-a2a.py --agent strandvik-customer-service --caller kolvo/maria-procurement` in Cloud Shell |
| Board times out with the stretch | Chain Maria > customer service > Alex > three specialists exceeds 180 seconds | Prepare the proposal earlier and only fetch it, or call fewer specialists |
| Test posts in the Kolvo thread | Evaluation rows called Work IQ | `POST /manage/thread/reset` or `/viewer/coach` |

## Checks for the coach

- [ ] Alex's 07:30 post, as Alex.
- [ ] **Compare runs** with baseline and improved runs, custom rubric visible.
- [ ] A nested trace and a token count.
- [ ] Board replay with all three suppliers, and the team's one-sentence verdicts.

[Previous Solution](../challenge-06/solution-06.md) - **[Back to Challenge 7](../../challenges/challenge-07.md)** - **[Home](../../README.md)** - [Next Solution](../finish/solution-finish.md)
