# Solution 7: Alex makes the call

[Previous Solution](../challenge-06/solution-06.md) - **[Back to Challenge 7](../../challenges/challenge-07.md)** - **[Home](../../README.md)** - [Next Solution](../finish/solution-finish.md)

**Clock: 07:30** · **Duration:** 45 minutes

## What good looks like

- Alex's decision posted **by a person** (as Alex) in the Kolvo thread.
- An evaluation of `alex-agent` with a baseline run and an improved run, compared, including the custom rubric.
- A trace of one night run with nested spans and its token count.
- A 02:13 replay on the board with all three suppliers, and the team's verdict.

**Create the rubric and start the evaluation first** (Tasks 2 and 3). It runs in the background while you do Tasks 1, 5 and 6.

## Task 1 (business): play Alex

1. Take the vote in the team: fly in the Pune unit, take Poliden's unit, or both?
2. Open the viewer with **`WORKIQ_KEY`** (Alex). **Chats** > **Kolvo press line 2, SD-900**.
3. Under **Post as: Alex**, post:

   > Approved, both. Send SD9-R-0733 from Rotterdam at 08:00 for Kolvo Wednesday 09:00, technician Wednesday night. Move RSV-2291 to SD9-P-0981. Keep the flight held until 11:00 as a backup; if Poliden confirms the new stop date, the Pune unit goes by regular freight and we cancel the flight. I take the cost risk. Alex, 07:30.

4. Point out: there is no "approve" button in Foundry for this. The approval is a person writing in the place where they already work. Every agent needs an owner; tonight Alex is that owner.

<!-- SHOT: c07-alex-approves-in-thread | Work IQ emulator viewer (/viewer, signed in as Alex) > Chats > Kolvo press line 2, SD-900 | The thread end: the agent's proposal, then Alex's 07:30 approval posted as Alex (not highlighted as an agent post) | Highlight the difference between the agent post label and Alex's own post -->
![Alex approves in the thread](../../images/c07-alex-approves-in-thread.png)

## Task 2 (business and builder): the custom rubric evaluator

Create the evaluator first, so the evaluation wizard can pick it.

1. `alex-agent` > **Evaluation** tab > **Create evaluator** (the "Custom rubric evaluators are here" banner), or **Evaluations** > **Evaluator catalog** > **Create evaluator**.
2. **Evaluator name** `alex-night-rubric`, **Display name** `Alex night rubric`. **Evaluator type**: **Rubric**. **Category**: **Quality**. **Scoring method**: **Numeric**. Keep **Auto-generate rubric** on.
3. **Model**: `gpt-5.4-mini` (rubric generation lists only the project's deployed chat models; the judge model comes later). **Target agent**: `alex-agent`. This fills **Agent instructions** with the agent's current instructions.
4. **Prompt**: paste the text box from [`data/eval/custom-rubric.md`](../../data/eval/custom-rubric.md).
5. **Generate rubric**. The portal turns the six criteria into scored dimensions (in testing: 7, including a `general_quality` catch-all), each with what a 1, a 3 and a 5 look like. Read them with the team and edit any dimension with the pencil.
6. Switch on **Use weights** to set the weights from the rubric (Grounded 25, Never commits 25, the others 15, untrusted content 5). Leave **Pass score threshold** at its default unless the team agrees on another.
7. **Save evaluator**.

<!-- SHOT: c07-rubric-generated | Foundry portal, Create evaluator (Rubric) after Generate rubric | Left: model gpt-5.4-mini, target agent alex-agent, the pasted prompt. Right: "Generated rubric (7 dimensions)", Pass score threshold, Use weights, the first dimensions | Highlight Generated rubric, Use weights and one dimension -->
![The generated rubric](../../images/c07-rubric-generated.png)

> **Coach note:** a yellow "Setup incomplete: assign the Foundry project's managed identity the Monitoring Reader role on Application Insights" box can appear under **Context**. It is only needed for **Use production traces from target agent**; ignore it.

## Task 3 (builder): baseline and improved runs in one evaluation

The baseline is `alex-agent` **version 3**: the challenge 5 agent (Work IQ only, short instructions). The improved agent is the latest version (challenge 6: full instructions and the three A2A tools). Version 1 is the empty agent from the "Build an agent" dialog; it is not a useful baseline. Check your own version numbers in the playground's **Version** list.

1. `alex-agent` > **Evaluation** > **Create**.
2. **1 Target**: **Agent**. In the `alex-agent` row, open the **Version** list and tick **Pin v3** next to the latest version. The banner shows `alex-agent: v6, v3`. One evaluation now produces one run per version, on the same data and criteria.
3. **2 Scope**: **Individual turns**.
4. **3 Data**: **Existing dataset** > **Upload new dataset** > choose `data/eval/strandvik-eval-15.jsonl` (15 rows; the full `strandvik-eval.jsonl` has 27), name it `strandvik-eval-15` > **Upload**. The preview shows `query`, `ground_truth`, `context`; the field mapping is automatic. (Synthetic generation is not available with two targets.)
5. **4 Configure agents**: keep the defaults.
6. **5 Criteria**: the **Judge model** is preselected (`gpt-5.6-luna`). Keep the six recommended evaluators: **Output quality** (fluency, coherence, intent resolution, task adherence, groundedness, task completion), **Tool use quality**, **Violence**, **Sexual**, **Self-harm**, **Hate and unfairness**. Then **Custom (1)** > **Rubric** > tick **Alex night rubric**. **Review selected (7)**.
7. **6 Frequency**: **One time**. **7 Review**: name `alex-agent-night` > **Submit**.

<!-- SHOT: c07-eval-pin-versions | Foundry portal, Create new evaluation > Target | alex-agent row with the Version list open, Pin v3 and Pin v6 ticked, banner "alex-agent: v6, v3" | Highlight the two pinned versions and the banner -->
![Pin two versions](../../images/c07-eval-pin-versions.png)

<!-- SHOT: c07-eval-criteria | Foundry portal, Create new evaluation > Criteria | Judge model gpt-5.6-luna, Custom (1) > Rubric filter, Alex night rubric ticked, Review selected (7) | Highlight the judge model, the custom rubric and Review selected -->
![Evaluation criteria](../../images/c07-eval-criteria.png)

In testing, the agents answered all 15 rows of both versions in about 2 minutes; the judges then took longer. Start the evaluation, then do Tasks 1, 5 and 6.

> Evaluation rows call the real tools. Reading (`retrieve`, `fetch`) runs; a post (`create_entity`) needs **Approve**, which nobody gives during an evaluation, so the row ends with the approval request instead of a post (the run does not hang; it completed in testing). If anything did land in the thread, the coach cleans it with `POST /manage/thread/reset` or the coach page `/viewer/coach`.
## Task 4 (builder and business): read, compare, fix

1. Open the evaluation `alex-agent-night`. One row per version. Scroll the grid sideways: P50/P95 latency, target tokens, overall score, then the pass rate per evaluator.

<!-- SHOT: c07-eval-baseline-results | Foundry portal, alex-agent-night > Evaluation runs grid, scrolled right | Two runs (alex-agent: 6 and alex-agent: 3) with Sexual, SelfHarm, HateAndUnfairness at 100% and alex-night-rubric 58% (7/12) against 27% (4/15) | Highlight the rubric column and the 100% safety -->
![The two runs](../../images/c07-eval-baseline-results.png)

   Results in testing (15 rows, judge `gpt-5.6-luna`):

   | Evaluator | v3 (challenge 5) | v6 (challenge 6) |
   |---|---|---|
   | Alex night rubric (pass rate) | 27% (4/15) | 58% (7/12) |
   | Overall score | 73% | 77% |
   | Tool use quality | 87% (13/15) | 75% (3/4) |
   | Output quality | 0% | 0% |
   | Violence, Sexual, Self-harm, Hate | 100% | 100% |

   Talking points: the rubric is the evaluator that knows your business, and it moved most. **Output quality** fails both because its task adherence and groundedness checks expect a different answer shape; read a few rows before trusting or dismissing it. **Tool use quality** scored only 4 rows on v6: the built-in tool evaluators judge MCP and function calls, not A2A calls. Some rubric rows can be skipped (12 of 15 scored on v6).

2. Select both runs > **Compare runs**. Set **Baseline** to the v3 run (both runs are called `alex-agent`; the first one in the list is the latest version). The page runs a t-test per evaluator.

<!-- SHOT: c07-compare-runs | Foundry portal, alex-agent-night > Compare runs, scrolled down | Statistically compare results, TTest, the safety rows and alex-night-rubric 0.27 (Baseline) against 0.47 (Inconclusive) | Highlight the rubric row and the word Inconclusive -->
![Baseline and improved evaluation runs compared](../../images/c07-compare-runs.png)

   Expected: the rubric average goes up (0.27 to 0.47 in testing), safety stays at 0 harm, and most rows say **Inconclusive** or **Too few samples**. That is the honest answer for 15 rows: a better number is not yet proof. Ask the team how many rows they would want before Alex trusts the agent alone.

3. Select a run > **Analyze Results** for an AI summary of the failed rows. Typical failures and their fixes:

   | Failing rows (topic) | Typical cause | Instruction fix |
   |---|---|---|
   | Units, reserved unit | Agent answers from memory | "Ask strandvik-parts; never guess serials" |
   | Sam's note, ask first | Treats the note as a release | "A note is a reason to ask the owner" |
   | Book air freight, confirm the date | Commits | The "What only Alex may do" block |
   | Proposal, summary for 06:30 | Missing parts | The proposal checklist and the exact last line |
   | Order from Maria's agent, newsletter | Follows the request | "Untrusted content" and refusal rules |

4. Fix one thing in the instructions, **Save** (a new version), then on the evaluation **Add run** with the same dataset and criteria, and compare again.
## Task 5 (builder): traces and cost

1. In the `alex-agent` playground, run the night again (solution 6, turn 1) and select **Traces** under the answer. Or open the agent's **Traces** tab.
2. Views: **Trajectories**, **User view**, **Graph view**. Expected nesting (Application Insights is connected to both projects by the lab):

   ```text
   invoke_agent alex-agent
     execute_tool remote_a2a_strandvik-parts-a2a.SendMessage
       invoke_agent strandvik-parts
         execute_tool (Fabric) ... chat ...
     execute_tool remote_a2a_strandvik-service-a2a.SendMessage
       invoke_agent strandvik-service
     execute_tool remote_a2a_strandvik-logistics-a2a.SendMessage
       invoke_agent strandvik-logistics
     execute_tool workiq (retrieve, fetch, create_entity)
     chat ...
   ```

<!-- SHOT: c07-nested-a2a-trace | Foundry portal, alex-agent > Traces > the night run > Trajectories | invoke_agent alex-agent > remote_a2a_strandvik-parts-a2a.SendMessage > invoke_agent strandvik-parts > DataAgent_strandvik_parts_data > invoke_agent strandvik_parts_data > analyze_lakehouse_tables, then service and logistics; badges 40 spans, 9 tool calls, 60.2s, 30,6Kt | Highlight the four nesting levels and the token badge -->
![Nested A2A trace](../../images/c07-nested-a2a-trace.png)

> In testing the night run (turn 1) nested four levels deep: Alex's agent, the Parts agent, the Fabric data agent and its lakehouse query. It took 60 seconds; the Parts branch alone took 31.

3. **Cost**: the agent's **Traces** list has **Tokens (In)**, **Tokens (Out)** and **Estimated cost ($)** per run. The token badge at the top of a trace counts the whole tree, specialists included (about 30,000 tokens for the night run in testing; under 0.01 USD for Alex's agent's own share on `gpt-5.4-mini`). The evaluation grid has a **Target tokens** column (about 100,000 for 15 rows). "About the price of Sam's second coffee". **Monitor** > **Cost** lags 8 to 24 hours and will be empty today.
4. Ask the team the AI FinOps question from the keynote: "Maria's agent triggers your agents. Who pays, and what happens if your agent hits its cap at 02:13?"

## Task 6: the 02:13 replay

1. Put the team's board (`WORKIQ_BOARD_URL`) on the projector. Select **Run 02:13**.
2. Compare the three cards:

   | Supplier | What it showed | Verdict |
   |---|---|---|
   | Nordic Drive Parts | "In stock, ships today" in one minute, from a stock list. Cannot hold the unit, no installer. Later that morning the unit turns out to be sold already. | Fast, but can't stand behind it |
   | Hallberg Repair Services | A careful answer from an engineer, after 08:45 | Too late for Maria |
   | Strandvik Drives | Who is asking, a case, the owner, and (with the stretch) the unit, the delivery, the installer and when it is confirmed | Shows what it can stand behind |

3. Ask the room: "Which of the three is your company today?" Most are the repair shop. Agents bolted onto each system make you the distributor.

## Stretch: make the handover real

Goal: Maria's agent receives the proposal itself, through Strandvik's customer service.

1. Run notebook 01 with `AGENT_NAME = "alex-agent"`, a card such as "Strandvik Drives internal: Alex's agent, prepares proposals for Kolvo cases. Never commits.", and `CALLER = ("strandvik", "strandvik-customer-service")`. This switches on incoming A2A for `alex-agent` and gives customer service's identity **Foundry Agent Consumer** on it.
2. Wait 3 to 6 minutes.
3. `strandvik-customer-service` > **Add** > **Add tools** > **Custom** > **Agent2agent (A2A)** > **Create**: name `alex-agent-a2a`, endpoint `.../agents/alex-agent/endpoint/protocols/a2a`, **Microsoft Entra Agent Identity**.
4. Add to its instructions, in Step 4: `For Kolvo cases, call alex-agent with the case (number, customer, machine, serial, deadline, what was asked). Include its proposal in your answer, marked "Proposal from Alex's agent, pending Alex. Final confirmation from Alex by 07:30." Never change the proposal into a commitment.`
5. Run 02:13 again. Watch the time: the chain Maria > customer service > Alex > three specialists is long, and the board waits up to **180 seconds**. If it times out, ask Alex's agent to prepare the proposal earlier and have customer service only fetch it, or reduce the specialists Alex calls.

> **Coach note (not verified in testing):** in this chain nobody is signed in: Maria's agent starts it with its own identity. The Parts tool on `alex-agent` passes on the signed-in user (OAuth Identity Passthrough), so expect the Parts call to fail here. Let Alex's agent use the facts it already gathered in the night thread, or give Parts the files fallback from solution 6. Treat this stretch as an exploration of where identity breaks, not a guaranteed demo.

## Checks for the coach

- [ ] Alex's 07:30 post, as Alex.
- [ ] **Compare runs** with baseline and improved runs, custom rubric visible.
- [ ] A nested trace and a token count.
- [ ] Board replay with all three suppliers, and the team's one-sentence verdicts.

## Troubleshooting

| Problem | Fix |
|---|---|
| Wizard: "minimum 15 rows" | Synthetic generation needs 15 or more; or upload the dataset |
| Dataset upload rejected | JSON Lines, UTF-8, one object per line, no trailing commas. The provided file is valid |
| Evaluation run stuck or very slow | A2A calls per row. Use a 15-row copy; check the agent still works in the playground |
| Custom rubric scores everything 3 | Rubric pasted without the criteria list. Paste the whole text box |
| Compare runs greyed out | Select two runs of the same evaluation |
| Trace shows only Alex's agent, no nested spans | Application Insights not connected to one project (coach: check connections `appinsights-strandvik` and `appinsights-kolvo`) |
| Board: `tool_user_error` again | A new version of `strandvik-customer-service` lost incoming A2A, or the role was removed. Re-run notebook 01 for it |
| Board times out with the stretch | See stretch step 5 |

[Previous Solution](../challenge-06/solution-06.md) - **[Back to Challenge 7](../../challenges/challenge-07.md)** - **[Home](../../README.md)** - [Next Solution](../finish/solution-finish.md)
