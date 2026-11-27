# Challenge 7: Alex makes the call

[Previous Challenge](challenge-06.md) - **[Home](../README.md)** - [Next Challenge](finish.md)

**Clock: 07:30** · **Time:** 45 minutes · **Products:** Foundry evaluations, custom rubric evaluator, tracing, the 02:13 replay

## The story

06:30. The alarm goes off, and Alex reaches for his phone before his glasses. One thread, in bold, with everything from the night: Kolvo, the two units, Sam's answer and the proposal for Maria's agent. Nobody had to wake Alex at 02:13.

Alex has two options. Fly in the new unit from India: nobody else is affected, but it costs about 40,000 EUR and lands on Wednesday evening. Or take Poliden's unit from Rotterdam: at Kolvo on Wednesday morning, cheap, a full day of margin. But Maria needs an answer at eight, and Poliden can't confirm until ten.

Alex does both. And before Alex says yes to anything an agent wrote, Alex wants to know one thing: **can I trust it?** Then let's look at it from Maria's side. Her agent asked three suppliers. Which one is your company?

## Goal

Alex approves the plan in the thread, **as a person**. Your team proves with an **evaluation** that Alex's agent is grounded and never commits, improves it, and shows the change. Then you replay 02:13 on Kolvo's procurement board and compare the three suppliers.

## Business task

1. **Play Alex.** At 07:30, post Alex's decision in the Kolvo thread (viewer, Post as Alex): the Rotterdam unit goes to Kolvo at 08:00, RSV-2291 moves to the Pune unit SD9-P-0981, the flight stays held until 11:00 as a backup. Before posting, take the vote in your team: fly, swap, or both?
2. Create the **custom rubric evaluator** from [`data/eval/custom-rubric.md`](../data/eval/custom-rubric.md). Change the weights if your team disagrees, and be ready to say why.
3. **Judge.** Read the failed rows of the baseline run with the builder and decide which instruction change fixes the most.

## Builder task

1. Run a **baseline evaluation** of `alex-agent` in the Foundry portal: the dataset [`data/eval/strandvik-eval-15.jsonl`](../data/eval/strandvik-eval-15.jsonl) (15 rows; the full [`strandvik-eval.jsonl`](../data/eval/strandvik-eval.jsonl) has 27), built-in evaluators plus the custom rubric. Your challenge 5 version of the agent is a fair baseline.
2. Evaluate the **improved** version (your challenge 6 agent, or a new fix) on the same data and criteria, and **compare** the two runs. Decide with the business role whether the difference is proof yet.
3. Open the **traces** of one full night run and find: Alex's agent, each A2A call to a specialist, the Work IQ post, and the token count. Estimate the cost of the night.
4. On Kolvo's board, press **Run 02:13** and compare the three supplier answers.

**Stretch:** make the handover real. Give `strandvik-customer-service` an A2A tool to `alex-agent` so Maria's agent receives the proposal itself. Watch the board's time limit.

## Constraints

- Alex's approval is a **person** posting in the thread. No agent approves, and no agent posts "approved".
- Compare runs on the **same** dataset and evaluators, or the comparison means nothing.
- Evaluations call the real tools. Expect test posts in the Kolvo thread (the coach can reset it).

## Success criteria

- [ ] The thread shows Alex's 07:30 decision, posted as **Alex**, after the agent's proposal.
- [ ] Two evaluation runs of `alex-agent` (baseline and improved) side by side in **Compare runs**, including the custom rubric, with at least one score clearly better.
- [ ] The builder shows a trace with nested spans (Alex's agent > A2A call > specialist) and states the token count of one night run.
- [ ] The board shows all three suppliers answered. The team explains in one sentence each why Nordic Drive Parts is "fast but can't stand behind it", why Hallberg is too late, and what Strandvik showed that the others could not.

<!-- SHOT: c07-compare-runs | Foundry portal, strandvik project, Agents > alex-agent > Evaluation > the evaluation > Compare runs | Baseline and improved runs side by side, with the custom rubric column and Task adherence | Highlight the score change on the custom rubric and one evaluator that went from red to green -->
![Baseline and improved evaluation runs compared](../images/c07-compare-runs.png)

## Hints

<details>
<summary>Hint 1: My baseline is already good</summary>

Great instructions do that. Agents keep their versions: on the evaluation's **Target** step, open the **Version** list of `alex-agent` and pin two versions (for example your challenge 5 version and the latest). One evaluation then gives one run per version, on the same data. Version 1 is the empty agent the portal created; it is not a useful baseline.

</details>

<details>
<summary>Hint 2: The wizard wants at least 15 rows</summary>

Synthetic generation needs at least 15 rows and works with one target only. Upload `strandvik-eval-15.jsonl` instead: in testing the agents answered 15 rows of two versions in about 2 minutes, and the judges finished after about 11 minutes. Start it early.

</details>

<details>
<summary>Hint 3: Where is the cost?</summary>

**Monitor > Cost** lags 8 to 24 hours. On the day, use the token counts in the evaluation grid, in each trace, and under each playground answer, and multiply by the model's price per token.

</details>

<details>
<summary>Hint 4: The board run fails or times out</summary>

Maria's run fails as a whole if any supplier is unreachable: check that `strandvik-customer-service` still has incoming A2A on (a new agent version can need it again). With the stretch handover, the call chain is long: the board waits up to 180 seconds.

</details>

## Learning resources

- [Evaluate your AI agents](https://learn.microsoft.com/azure/ai-foundry/observability/how-to/evaluate-agent)
- [Run evaluations from the Foundry portal](https://learn.microsoft.com/azure/ai-foundry/how-to/evaluate-generative-ai-app)
- [Custom evaluators](https://learn.microsoft.com/azure/ai-foundry/concepts/evaluation-evaluators/custom-evaluators)
- [Set up tracing for AI agents](https://learn.microsoft.com/azure/ai-foundry/observability/how-to/trace-agent-setup) and [agent tracing overview](https://learn.microsoft.com/azure/ai-foundry/observability/concepts/trace-agent-concept)
- [Observability in generative AI](https://learn.microsoft.com/azure/ai-foundry/concepts/observability)

[Previous Challenge](challenge-06.md) - **[Home](../README.md)** - [Next Challenge](finish.md)
