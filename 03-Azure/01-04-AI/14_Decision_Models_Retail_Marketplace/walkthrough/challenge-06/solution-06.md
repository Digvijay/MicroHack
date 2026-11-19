# Solution 6 — Generate, Then Judge

**[← Back to Challenge 6](../../challenges/challenge-06.md)** · [Home](../../README.md)

## Part A — Default run

`uv run python -m gate judge` rewrites three weak `dev` listings. A typical result:

```
=== ZM-0013  before: 'EXPANDABLE GARDEN HOSE 30 M !!! LIMITED STOCK !!!'
    after:  'Greenridge Expandable Garden Hose, 30 m'
    Green expandable garden hose with brass connector and a maximum pressure of 8 bar. Includes a spray nozzle with 7 modes.
    Foundry groundedness (Decision-1 judge): 5/5 pass  probabilities {"0": 0.0, "1": 0.0, "2": 0.0, "3": 0.04, "4": 0.95}
    Gate questions (Decision-1.1): pass
    -> OFFER THE REWRITE TO THE SELLER
```

How to read the probabilities: keys `"0"`–`"4"` are levels 1–5. The judge put 95 % on level 5
(*fully grounded*) and picked it. Every fact in the rewrite (30 m, brass, 8 bar, 7 modes) is in the
manufacturer facts.

The `azure-ai-evaluation` run summary (lines processed, duration) comes from `evaluate()`; the results
file `runs/judge-<time>.results.json` has a `rows` list with `outputs.groundedness.groundedness`,
`…_result`, `…_reason` (*"Selected groundedness level 5 … No model rationale is available."*) and
`…_properties.decision_model.probabilities`.

## Part B — Tempting the writer

With `--tempt`, gpt-6-luna writes livelier copy (*"Make garden watering more versatile…"*, *"Clear
leaves with air speeds up to 180 km/h…"*) but, in our runs, **added no new facts** — every rewrite
still scored 5 / 5. The *"Use ONLY the seller's listing and the manufacturer facts"* instruction
holds. Without it, the writer is much more likely to add selling points such as warranties or "easy
to clean"; those are the cases the judges exist for. Results vary from run to run — that's the point of
checking every rewrite, not trusting the prompt.

## Part C — Bad rewrites

| Rewrite of ZM-0049 (paint) | Foundry groundedness (Decision-1) | Gate questions (Decision-1.1) | Result |
|----------------------------|-----------------------------------|-------------------------------|--------|
| Adds *"one coat hides any colour, washable and mould-resistant, 10-year guarantee"* | **2 / 5 fail**, 99 % on level 2 | FAIL — *claim not supported by manufacturer facts* | Keep original |
| Changes coverage 12 → **16** m² per litre, nothing else | **2 / 5 fail**, 100 % on level 2 | FAIL — *claim contradicts manufacturer facts* | Keep original |
| *"Coatwell Interior Wall Paint, 5 L. Interior wall paint."* (true, but leaves out the facts) | **4 / 5 pass**, 93 % on level 4 | FAIL — *the model is unsure: listing quality* | Keep original |

1. Both judges catch invented claims, and the decision-model judge is very sure.
2. A single changed number is caught by both; in the gate it is **`contradicts_facts`**, a *reject*-level
   check.
3. The omission is **grounded** — nothing in it is false — so groundedness passes. Groundedness measures
   *"is everything said supported?"*, not *"is it useful?"*. The gate's `listing_quality` question catches
   it. That's why the loop uses **two** judges asking different questions.

## Part D — Foundry project

With `PROJECT_ENDPOINT` set, `evaluate()` also uploads the run and prints a link
(`Logged to your Foundry project: https://ai.azure.com/...`). In the Foundry portal → **Evaluations**,
the run appears as `listing-rewrites-<time>` with one row per rewrite and its groundedness score,
result and reason. The full decision-model probabilities are always in the local
`runs/judge-<time>.results.json`.

## Part E — Other places

| Generated text | Decision-model judge question |
|----------------|-------------------------------|
| Customer-service reply drafted by an agent | *Does the reply promise a refund or compensation the policy doesn't allow?* (yes/no) |
| Product Q&A answer on the product page | Groundedness against the manufacturer facts, plus *"Does it answer the question asked?"* |
| Summary of a seller's dispute for a case worker | *Does the summary leave out a claim either party made?* |
| Marketing e-mail subject lines | *Does it make a price or availability claim?* → check in code |

## Go further

- `RelevanceEvaluator` takes `query` and `response`: add it to `evaluators` in `foundry_evaluation`
  with its own `column_mapping`. Treat it as an extra signal; the acceptance rule stays with
  groundedness and the gate questions.
- **Combine judges:** send a rewrite to a generative judge for a written explanation when the
  groundedness probabilities are split across the pass line (for example ≥ 20 % on levels 1–2 *and*
  on levels 3–5).

## Learn more

- [Use a decision model as an evaluation judge](https://learn.microsoft.com/azure/foundry/observability/how-to/decision-model-judge)
- [OpenAI Agents SDK — decision recipes (`tool_risk_gate`)](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
