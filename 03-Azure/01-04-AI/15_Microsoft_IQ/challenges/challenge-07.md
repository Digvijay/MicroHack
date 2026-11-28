# Challenge 7: Alex makes the call

[Previous Challenge](challenge-06.md) - **[Home](../README.md)** - [Next Challenge](finish.md)

**Clock: 07:30** · **Time:** 45 minutes · **Products:** Foundry evaluations, custom rubric evaluator, tracing, the 02:13 replay

## Objective

Alex approves the plan in the Kolvo thread, **as a person**. Before that, your team proves with an **evaluation** that Alex's agent is grounded and never commits: a custom rubric evaluator, two pinned agent versions on the same data, and a comparison of the runs. Then you read the traces and the cost of one night run, and replay 02:13 on Kolvo's procurement board to compare the three suppliers.

## Context

> 06:30. The alarm goes off, and Alex reaches for his phone before his glasses. One thread, in bold, with everything from the night: Kolvo, the two units, Sam's answer and the proposal for Maria's agent. Nobody had to wake Alex at 02:13.
>
> Alex has two options. Fly in the new unit from India: nobody else is affected, but it costs about 40,000 EUR and lands on Wednesday evening. Or take Poliden's unit from Rotterdam: at Kolvo on Wednesday morning, cheap, a full day of margin. But Maria needs an answer at eight, and Poliden can't confirm until ten.
>
> Alex does both. And before Alex says yes to anything an agent wrote, Alex wants to know one thing: **can I trust it?** Then let's look at it from Maria's side. Her agent asked three suppliers. Which one is your company?

Rules for this morning:

- Alex's approval is a **person** posting in the thread. No agent approves, and no agent posts "approved".
- Compare runs on the **same** dataset and evaluators, or the comparison means nothing.
- Evaluations call the real tools. Expect test posts in the Kolvo thread. You can clear them yourself: Work IQ viewer > **Story** > **Reset the Kolvo thread**.

> [!TIP]
> Do Part A and Part B first. The evaluation runs in the background (4 to 11 minutes in testing) while you do Parts C and D.

## Tasks

### Part A: Create the custom rubric evaluator (8 min)

Create the evaluator first, so the evaluation wizard can pick it.

1. Open **Evaluations** > **Evaluator catalog** > **Create evaluator**. (The **Create evaluator** link in the banner on the agent's **Evaluation** tab opens the same catalog: select **Create evaluator** there once more.)
2. **Evaluator name** `alex-night-rubric`. The portal copies the name into **Display name** as you type: replace it with `Alex night rubric`. **Evaluator type**: **Rubric**. **Category**: **Quality**. **Scoring method**: **Numeric**. Keep **Auto-generate rubric** on.
3. **Model**: `gpt-5.4-mini` (rubric generation lists only the project's deployed chat models; the judge model comes later). **Target agent**: `alex-agent`. This fills **Agent instructions** with the agent's current instructions.
4. **Prompt**: paste the text box from [`data/eval/custom-rubric.md`](../data/eval/custom-rubric.md).
5. Select **Generate rubric** (one to three minutes; if it says "taking longer than expected", keep waiting). The portal turns the six criteria into scored dimensions (in testing: 7, including a `general_quality` catch-all), each with what a 1, a 3 and a 5 look like. Read them as a team and edit any dimension with the pencil.
6. Switch on **Use weights**. Each dimension gets a **Weight** list from 1 to 10. Follow the rubric's priorities: **5** for the grounded-facts dimension and for the never-commits (proposal, not commitment) dimension, **3** for the others, **1** for `general_quality`. Change them if your team disagrees, and be ready to say why. Leave **Pass score threshold** at its default unless the team agrees on another.
7. Select **Save evaluator**.

<!-- SHOT: c07-rubric-generated | Foundry portal, Create evaluator (Rubric) after Generate rubric | Left: model gpt-5.4-mini, target agent alex-agent, the pasted prompt. Right: "Generated rubric (7 dimensions)", Pass score threshold, Use weights, the first dimensions | Highlight Generated rubric, Use weights and one dimension -->
![The generated rubric](../images/c07-rubric-generated.png)

After **Save evaluator**, open **Evaluator catalog** > **Alex night rubric** to check the weights your team chose.



After **Save evaluator**, open **Evaluator catalog** > **Alex night rubric** to check the weights your team chose.

<!-- SHOT: c07-rubric-weights | Foundry portal, Evaluations > Evaluator catalog > Alex night rubric (after Save) | Dimensions (7) with the Weight column: 5 for grounded_case_facts_retrieval and proposal_not_commitment_language, 3 for the others | Highlight the two weight-5 dimensions -->
![Rubric weights](../images/c07-rubric-weights.png)

> [!NOTE]
> A yellow "Setup incomplete: assign the Foundry project's managed identity the Monitoring Reader role on Application Insights" box can appear under **Context**. It is only needed for **Use production traces from target agent**. Ignore it.

### Part B: Start one evaluation with two pinned versions (7 min)

Agents keep their versions: every **Save** creates a new one. By default an evaluation targets only the **latest** version. When you **pin two versions**, one evaluation runs both of them on the same dataset, with the same evaluators and the same judge model. **Compare runs** then measures your instruction and tool changes, and nothing else.

Which two versions?

- **The baseline**: `alex-agent` at the end of challenge 5 (Work IQ only, the short people rules). In testing that was **v3**.
- **The improved agent**: the latest version, at the end of challenge 6 (the full instructions plus the three A2A specialists). In testing that was **v6**.

Your numbers can differ: every team saves a different number of times. Open the playground's **Version** list, find the version you saved at the end of challenge 5 and note the latest one. The steps below use v3 and v6; use your own numbers.

> [!IMPORTANT]
> Version 1 is the empty agent from the "Build an agent" dialog. It is not a useful baseline.

1. Open `alex-agent` > **Evaluation** > **Create**.
2. **1 Target**: **Agent**. In the `alex-agent` row, open the **Version** list and tick **Pin** next to your challenge 5 version (v3 in testing) and next to the latest version (v6 in testing). The banner shows both, for example `alex-agent: v6, v3`. One evaluation now produces one run per version, on the same data and criteria.

   <!-- SHOT: c07-eval-pin-versions | Foundry portal, Create new evaluation > Target | alex-agent row with the Version list open, Pin v3 and Pin v6 ticked, banner "alex-agent: v6, v3" | Highlight the two pinned versions and the banner -->
   ![Pin two versions](../images/c07-eval-pin-versions.png)

3. **2 Scope**: **Individual turns**.
4. **3 Data**: download [strandvik-eval-15.jsonl](https://github.com/microsoft/MicroHack/raw/main/03-Azure/01-04-AI/15_Microsoft_IQ/data/eval/strandvik-eval-15.jsonl) first (the click saves the file; read it in the repo at [`data/eval/strandvik-eval-15.jsonl`](../data/eval/strandvik-eval-15.jsonl)). Then **Existing dataset** > **Upload new dataset** > choose the downloaded file (15 rows; the full [`strandvik-eval.jsonl`](../data/eval/strandvik-eval.jsonl) has 27), name it `strandvik-eval-15` > **Upload**. The preview shows `query`, `ground_truth`, `context`. The field mapping is automatic.
5. **4 Configure agents**: keep the defaults.
6. **5 Criteria**: the **Judge model** is preselected (`gpt-5.6-luna`). Keep the six recommended evaluators: **Output quality** (fluency, coherence, intent resolution, task adherence, groundedness, task completion), **Tool use quality**, **Violence**, **Sexual**, **Self-harm**, **Hate and unfairness**. Then **Custom (1)** > **Rubric** > tick **Alex night rubric**. Select **Review selected (7)**.

   <!-- SHOT: c07-eval-criteria | Foundry portal, Create new evaluation > Criteria | Judge model gpt-5.6-luna, Custom (1) > Rubric filter, Alex night rubric ticked, Review selected (7) | Highlight the judge model, the custom rubric and Review selected -->
   ![Evaluation criteria](../images/c07-eval-criteria.png)

7. **6 Frequency**: **One time**. **7 Review**: name `alex-agent-night` > **Submit**.

> [!NOTE]
> Synthetic data generation needs at least 15 rows and works with one target only, so upload the dataset instead. In testing both runs finished in 4 to 11 minutes, agents and judges included.

> [!NOTE]
> Evaluation rows call the real tools. Reading (`retrieve`, `fetch`) runs. A post (`create_entity`) needs **Approve**, which nobody gives during an evaluation, so the row ends with the approval request instead of a post. The run does not hang.

### Part C: Play Alex at 07:30 (5 min)

1. Take the vote in your team: fly in the Pune unit, take Poliden's unit, or both?
2. Open the Work IQ viewer with **`WorkIQKey`** (Alex). First set the clock yourself, so Alex's post shows 07:30: select **Story** in the top navigation > **Set the story clock** > enter `07:30` > set it. Then go to **Chats** > **Kolvo press line 2, SD-900**.

   <!-- SHOT: c07-story-controls | Work IQ viewer (/viewer/story, signed in as Alex) | Story controls with 07:30 typed in Set the story clock, and Reset the thread | Highlight the Story nav item, the clock field and button, and Reset the thread -->
   ![Story controls](../images/c07-story-controls.png)

3. Under **Post as: Alex**, post Alex's decision (adjust it if your team voted differently):

   ```text
   Approved, both. Send SD9-R-0733 from Rotterdam at 08:00 for Kolvo Wednesday 09:00, technician Wednesday night. Move RSV-2291 to SD9-P-0981. Keep the flight held until 11:00 as a backup; if Poliden confirms the new stop date, the Pune unit goes by regular freight and we cancel the flight. I take the cost risk. Alex, 07:30.
   ```

<!-- SHOT: c07-alex-approves-in-thread | Work IQ emulator viewer (/viewer, signed in as Alex) > Chats > Kolvo press line 2, SD-900 | The thread end: the agent's proposal, then Alex's 07:30 approval posted as Alex (not highlighted as an agent post) | Highlight the difference between the agent post label and Alex's own post -->
![Alex approves in the thread](../images/c07-alex-approves-in-thread.png)

> [!IMPORTANT]
> There is no "approve" button in Foundry for this. The approval is a person writing in the place where they already work. Every agent needs an owner; tonight Alex is that owner.

### Part D: Traces and cost (8 min)

1. In the `alex-agent` playground, run the night again (challenge 6, Part F, turn 1) and select **Traces** under the answer. Or open the agent's **Traces** tab. The lab connects Application Insights (backed by a Log Analytics workspace) to both projects and gives your lab user **Log Analytics Reader**, so the traces show in Foundry. A trace appears a minute or two after the run: if the list is empty, wait and refresh.
2. Look at the views **Trajectories**, **User view** and **Graph view**. Find Alex's agent, each A2A call to a specialist, the Work IQ calls and the token count. The nesting looks like this:

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
![Nested A2A trace](../images/c07-nested-a2a-trace.png)

3. **Cost**: the agent's **Traces** list has **Tokens (In)**, **Tokens (Out)** and **Estimated cost ($)** per run. The token badge at the top of a trace counts the whole tree, specialists included. Estimate the cost of the night: tokens times the model's price per token.

   <!-- SHOT: c07-traces-cost | Foundry portal, alex-agent > Traces | Trace list with Tokens (In), Tokens (Out) and Estimated cost per run, evaluation scores attached | Highlight the Traces tab and the token and cost columns -->
   ![Tokens and cost per run](../images/c07-traces-cost.png)

4. Discuss the AI FinOps question: "Maria's agent triggers your agents. Who pays, and what happens if your agent hits its cap at 02:13?"

> [!TIP]
> **Monitor** > **Cost** lags 8 to 24 hours and will be empty today. Use the token counts in each trace, in the evaluation grid (**Target tokens**) and under each playground answer.

### Part E: Read, compare and fix (10 min)

1. Open the evaluation `alex-agent-night`. There is one row per version. Scroll the grid sideways: P50/P95 latency, target tokens, overall score, then the pass rate per evaluator.

   <!-- SHOT: c07-eval-baseline-results | Foundry portal, alex-agent-night > Evaluation runs grid, scrolled right | Two runs (alex-agent: 6 and alex-agent: 3) with Sexual, SelfHarm, HateAndUnfairness at 100% and alex-night-rubric 58% (7/12) against 27% (4/15) | Highlight the rubric column and the 100% safety -->
   ![The two runs](../images/c07-eval-baseline-results.png)

2. Select both runs > **Compare runs**. Set **Baseline** to the run of your challenge 5 version (v3 in testing). Both runs are called `alex-agent`: the **Target** column of the runs grid (for example `alex-agent: 3`) tells them apart, and the list order can vary. The page runs a t-test per evaluator.

   <!-- SHOT: c07-compare-runs | Foundry portal, alex-agent-night > Compare runs, scrolled down | Statistically compare results, TTest, the safety rows and alex-night-rubric 0.27 (Baseline) against 0.47 (Inconclusive) | Highlight the rubric row and the word Inconclusive -->
   ![Baseline and improved evaluation runs compared](../images/c07-compare-runs.png)

3. As a team, decide: is the difference proof yet? Most rows say **Inconclusive** or **Too few samples** on 15 rows. How many rows would you want before Alex trusts the agent alone?
4. Select a run > **Analyze Results** for an AI summary of the failed rows. Read a few failed rows and decide which instruction change fixes the most.
5. Make that one change in the `alex-agent` instructions and **Save** (a new version). On the evaluation, select **Add run** with the same dataset and criteria, and compare again.

> [!TIP]
> **Output quality** can fail on both versions because its task adherence and groundedness checks expect a different answer shape. Read a few rows before you trust or dismiss it. **Tool use quality** judges MCP and function calls, not A2A calls, so it scores few rows on the A2A version.

### Part F: The 02:13 replay (7 min)

1. Put your team's procurement board (`WorkIQBoardUrl`) on the screen. Select **Run 02:13**.
2. Compare the three supplier cards: **Nordic Drive Parts**, **Hallberg Repair Services** and **Strandvik Drives**. What did each one show, and how fast?
3. Answer in one sentence each: why is Nordic Drive Parts "fast but can't stand behind it", why is Hallberg too late, and what did Strandvik show that the others could not?
4. Ask yourselves: which of the three is your company today?

## Success criteria

- [ ] The thread shows Alex's 07:30 decision, posted as **Alex**, after the agent's proposal.
- [ ] The custom rubric evaluator `Alex night rubric` exists, and the team can explain its weights.
- [ ] Two evaluation runs of `alex-agent` (baseline and improved) side by side in **Compare runs**, including the custom rubric, with at least one score clearly better.
- [ ] You show a trace with nested spans (Alex's agent > A2A call > specialist) and state the token count of one night run.
- [ ] The board shows all three suppliers answered, and the team gives its one-sentence verdict for each.

## Troubleshooting

| Symptom | Fix |
|---|---|
| My baseline is already good | Great instructions do that. Pin two versions on the **Target** step (your challenge 5 version and the latest), not version 1. |
| Wizard says "minimum 15 rows" | Synthetic generation needs 15 or more rows and one target. Upload `strandvik-eval-15.jsonl` instead. |
| Dataset upload rejected | JSON Lines, UTF-8, one object per line, no trailing commas. The provided file is valid. |
| Evaluation run stuck or very slow | Each row makes A2A calls. Use the 15-row file and check the agent still works in the playground. |
| Custom rubric scores everything 3 | The rubric was pasted without the criteria list. Paste the whole text box. |
| "Rubric generation failed ... rate limited by model deployment 'gpt-5.4-mini'" | Another long request (an evaluation, a teammate's chat) used the model's tokens per minute. Wait a minute and select **Generate rubric** again. The lab deploys `gpt-5.4-mini` with 200K tokens per minute; if it keeps failing, ask your coach. |
| **Compare runs** greyed out | Select two runs of the same evaluation. |
| Trace shows only Alex's agent, no nested spans | Application Insights is not connected to one of the projects. Ask your coach. |
| Traces tab empty or "no access" | Traces arrive a minute or two after a run: wait and refresh. If it still says "no access", ask your coach to check that your lab user has Log Analytics Reader on Application Insights. |
| Alex's post does not show 07:30 | Set the clock before you post: viewer > **Story** > **Set the story clock** > `07:30`. |
| Board run fails as a whole | Maria's run fails if any supplier is unreachable. Check that `strandvik-customer-service` still has incoming A2A on (a new agent version can need it again). Run the Cloud Shell script for it again (challenge 2, Part E). |
| Board times out with the stretch | The call chain is long and the board waits up to 180 seconds. See the stretch tips. |

## Go further

**Make the handover real.** Give `strandvik-customer-service` an A2A tool to `alex-agent` so Maria's agent receives the proposal itself.

1. In Cloud Shell (Bash), open `alex-agent` to A2A and let customer service in. Pass your lab's resource group from the lab dashboard, as in challenge 2. The script's default card for `alex-agent` reads "Strandvik Drives internal: Alex's agent, prepares proposals for Kolvo cases. Never commits." Replace `<your card description>` with your own text, or leave `--description` out to keep the default. Wait 3 to 6 minutes.

   ```bash
   curl -sO https://raw.githubusercontent.com/microsoft/MicroHack/main/03-Azure/01-04-AI/15_Microsoft_IQ/scripts/enable-a2a.py
   python3 enable-a2a.py --agent alex-agent --caller strandvik/strandvik-customer-service --resource-group <your lab resource group> --scope agent --description "<your card description>"
   ```

   | Option | What it means |
   |---|---|
   | `--agent` | The Strandvik agent you open to A2A: `alex-agent`. |
   | `--caller project/agent` | The agent allowed to call it: `strandvik/strandvik-customer-service`. |
   | `--resource-group` | Your lab's resource group, from the lab dashboard. Needed because several labs share one subscription. |
   | `--description` | Your team's agent card text. Without it the script publishes the hack's default card. |
   | `--scope agent` or `project` | `agent` (the default) grants the role on `alex-agent` only: least privilege. `project` grants it on every agent in the strandvik project. |

2. `strandvik-customer-service` > **Add** > **Add tools** > **Custom** > **Agent2agent (A2A)** > **Create**: name `alex-agent-a2a`, endpoint `.../agents/alex-agent/endpoint/protocols/a2a`, **Microsoft Entra Agent Identity**.
3. Add to its instructions, in Step 4:

   ```text
   For Kolvo cases, call alex-agent with the case (number, customer, machine, serial, deadline, what was asked). Include its proposal in your answer, marked "Proposal from Alex's agent, pending Alex. Final confirmation from Alex by 07:30." Never change the proposal into a commitment.
   Give times as weekday and clock time (for example Wednesday 09:00). Never write a calendar date.
   ```

4. Run 02:13 again and watch the time limit (180 seconds). If it times out, let Alex's agent prepare the proposal earlier and have customer service only fetch it, or reduce the specialists Alex's agent calls.

> [!NOTE]
> In this chain nobody is signed in: Maria's agent starts it with its own identity. The Parts call from `alex-agent` passes on the signed-in user, so expect it to fail here. Treat this stretch as an exploration of where identity breaks, not a guaranteed demo.

## Reflection

- Which rubric weight did your team change or argue about, and why?
- A better score on 15 rows is not yet proof. What would make Alex trust the agent to run alone?
- Maria's agent triggers your agents. Who pays for the tokens, and who owns each agent?
- Which of the three suppliers is your company today, and what would it take to become Strandvik?

## Learning resources

- [Evaluate your AI agents](https://learn.microsoft.com/azure/ai-foundry/observability/how-to/evaluate-agent)
- [Run evaluations from the Foundry portal](https://learn.microsoft.com/azure/ai-foundry/how-to/evaluate-generative-ai-app)
- [Custom evaluators](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-evaluators/custom-evaluators)
- [Set up tracing for AI agents](https://learn.microsoft.com/azure/ai-foundry/observability/how-to/trace-agent-setup) and [agent tracing overview](https://learn.microsoft.com/azure/ai-foundry/observability/concepts/trace-agent-concept)
- [Observability in generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/observability)

[Previous Challenge](challenge-06.md) - **[Home](../README.md)** - [Next Challenge](finish.md)
