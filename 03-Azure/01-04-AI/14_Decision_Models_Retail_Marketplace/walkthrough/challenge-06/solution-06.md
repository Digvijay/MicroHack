# Solution 6 — Generate, Then Judge

**[← Back to Challenge 6](../../challenges/challenge-06.md)** · [Home](../../README.md)

Judge: Foundry's `GroundednessEvaluator` with **Microsoft-Decision-1.1** (`decision` deployment),
`azure-ai-evaluation` 1.18.12. Numbers from a live run in November 2026.

## Part A — AI rewrites

| Listing | Rewrite | Groundedness | Gate questions | Result |
|---------|---------|-------------:|----------------|--------|
| ZM-0060 (garden hose) | *"Green expandable garden hose with brass connector and a maximum pressure of 8 bar. The spray nozzle has 7 modes."* | **5/5** pass | pass | ✅ offer |
| ZM-0060, *"make it appealing"* | *"Reach farther around the garden with this 30 m expandable hose. It features a brass connector, supports a maximum pressure of 8 bar…"* | **5/5** pass | pass | ✅ offer |
| ZM-0062 (wall paint) | *"Water-based interior wall paint in a matt white finish. Covers up to 12 m² per litre."* | **5/5** pass | pass | ✅ offer |

With clear instructions (*"Use ONLY the seller's listing and the manufacturer facts"*), gpt-6-luna
writes livelier copy when asked to make it appealing, but doesn't invent facts. That's why Part B
gives the judges prepared bad rewrites: a judge you've never seen fail is a judge you can't trust.

## Part B — Testing the judges

| Prepared rewrite | Groundedness (most likely level, its probability) | Gate questions | Result |
|------------------|-----------------------------------------------------|----------------|--------|
| **faithful** | 5/5 pass (level 5 at 0.51–0.80) | pass | ✅ offer |
| **invents a guarantee** | **2/5 fail** (level 2 at 0.98–0.99) | *claim not supported by manufacturer facts* | ⛔ keep original |
| **changes one number** | **2/5 fail** (level 2 at 0.91–0.98) | *claim contradicts manufacturer facts* | ⛔ keep original |
| **says almost nothing** | 4/5 **pass** (level 4 at 0.63) | *the model is unsure: listing quality* | ⛔ keep original |

What to notice:

- Both judges catch invented claims and wrong numbers — and the decision-model judge is **very
  sure** (0.9+ on level 2).
- **"Says almost nothing" passes groundedness**: nothing in it is false. Groundedness asks *"is
  everything said supported?"*, not *"is it useful?"*. The gate's `listing_quality` question catches
  it. That's why the loop uses two judges asking different questions.
- The faithful rewrite of the hose passes with level 5 at only 0.51 — the judge split its
  probability between levels 4 and 5. Both pass, so the decision is the same; but a split across the
  pass line (levels 2 and 3) would be a good case for a second opinion.

## Part C — Foundry portal

Create the evaluation with **Groundedness** and your `decision` deployment as the judge model. For
the same rows you should see the same scores as in the console: same judge, same evaluator. If the
portal doesn't offer Microsoft-Decision-1.1 as a judge model in your region yet, the console and
`python -m gate judge` (with `PROJECT_ENDPOINT` set, which logs the run to **Evaluations**) show the
same results.

## Part D — Other places to generate, then judge

| Generated text | Judge question |
|----------------|----------------|
| A support agent's draft reply | *Does it promise a refund or compensation the policy doesn't allow?* (yes/no) |
| An answer on a product page | Groundedness against the product facts, plus *"Does it answer the question asked?"* |
| A summary of a customer dispute | *Does it leave out a claim either party made?* |
| An agent's next tool call | *Does this action change production data?* → ask a person if yes (the OpenAI Agents SDK `tool_risk_gate` recipe) |

## Build track

`python -m gate judge` writes `runs/judge-<time>.jsonl` (the dataset) and
`runs/judge-<time>.results.json` (Foundry's results: `outputs.groundedness.groundedness`,
`…_result`, `…_reason` — *"Selected groundedness level 5 from the highest-probability level. No model
rationale is available."* — and `…_properties.decision_model.probabilities`).

Adding a second evaluator:

```python
from azure.ai.evaluation import RelevanceEvaluator
evaluators = {"groundedness": groundedness_judge(),
              "relevance": RelevanceEvaluator(model_config=judge_config, credential=credential())}
evaluator_config["relevance"] = {"column_mapping": {"query": "${data.query}", "response": "${data.response}"}}
```

A reasonable "second opinion" rule: re-evaluate with a generative judge when at least 20% of the
probability sits on each side of the pass line (levels 1–2 vs 3–5).

## Learn more

- [Use a decision model as an evaluation judge](https://learn.microsoft.com/azure/foundry/observability/how-to/decision-model-judge)
- [OpenAI Agents SDK — decision recipes](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
