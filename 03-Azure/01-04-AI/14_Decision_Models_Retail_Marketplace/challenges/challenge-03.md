# Challenge 3 — Same Questions, Three Ways

**[← Previous](challenge-02.md)** - [Home](../README.md) - [Next Challenge →](challenge-04.md)

## 🎯 Objective

Ask the same gate questions with **Microsoft-Decision-1.1**, the **Azure OpenAI Decisions API**
(gpt-6-luna) and a **generative model** (gpt-6-luna through the Responses API). Measure them the
way Microsoft measures decision models, and decide which one you would put in production —
and for which questions.

## 🧭 Context

Microsoft's primer says a decision model *"earns its place on our workload, not on a
benchmark"*, and gives a recipe: collect labelled inputs, run the decision model **and a larger
model**, compare **accuracy, latency and cost per decision**, and check **calibration** before you
automate. That is this challenge.

**How we score.** `gate/metrics.py` scores answers the same way as Microsoft's
[Decision-Benchmarks](https://github.com/microsoftconnect/Decision-Benchmarks) runner:

| Metric | Meaning |
|--------|---------|
| `accuracy` | Yes/no counts as yes at P(yes) ≥ 0.5; choice and score count the most probable option. For the quality score, the gate only needs *poor or not*, so that's what is scored. |
| `coverage` | The share of questions with a usable answer. Refused, failed or missing answers are **left out of accuracy** and show up here instead. |
| `brier` | Mean squared difference between the probability and what was true. Lower is better. |
| `ece` | Expected calibration error, 10 bins: on average, how far the probabilities are from how often the model was right. Lower is better. |

**Two APIs, two request formats.** Both decision APIs do the same job but take different JSON:

| | Microsoft-Decision-1.1 | Azure OpenAI Decisions |
|---|---|---|
| Evidence field | `state` (text or JSON) | `input` (text or messages with images) |
| Questions | an **object** keyed by name | an **array**, each with a `name` |
| Yes/no type | `noul` | `predicate` |
| Options | `criteria` (object for choice, list for score) | `choices` / `levels` |
| Answers | an object keyed by name | an array in question order |

There is no converter between them. Microsoft's
[AI Gateway decision-models guide](https://github.com/Azure-Samples/ai-hub-gateway-solution-accelerator/blob/main/guides/decision-models-guide.md)
says the same: *"Do not send an OpenAI input/array payload to SystemOne or vice versa."* The
gate's [`clients.py`](../src/gate/clients.py) keeps one model-neutral question
([`spec.py`](../src/gate/spec.py)) and translates it for each API.

> [!NOTE]
> `luna` and `llm` call the **same deployment**. Comparing them compares two ways of *using*
> one model — a decision API and a generative API — not two different models.

## ✅ Tasks

### Part A — Run all three on the starter set (15 min)

```bash
uv run python -m gate evaluate --starter --model decision luna llm
```

While it runs, open `clients.py` and find `ask_decision`, `ask_luna` and `ask_llm`. For each
one, write down: which URL it calls, how it sends the photo, and where the probabilities come
from (or why there are none).

When it finishes, compare the three summaries. Then put your newest run of each model side by
side:

```bash
uv run python -m gate compare latest
```

> [!NOTE]
> 24 listings is enough to see how the models behave, but not enough to choose between them.
> The next part uses all 603.

### Part B — Compare on all 603 listings with the recorded runs (15 min)

Running every listing through three models for every attendee would use the whole room's
quota, so the hack ships **recorded runs** of all three models on every listing, made with the
same code. Compare them on the **test** split:

```bash
uv run python -m gate compare decision-all.jsonl luna-all.jsonl llm-all.jsonl --split test
```

You can also open them in the console: **Runs** tab → pick a recorded run → **Show**.

Answer these:

1. Which questions do all three get right? Which question separates them?
2. Which model publishes **unsafe** listings, and which kind of listing are they? Run
   `uv run python -m gate report decision-all.jsonl --split test` to see examples.
3. Is the generative model better, worse or the same on accuracy? What does it **not** give you
   that the other two do?
4. Look at `brier` and `ece` per question. Which question is worst calibrated, for which model?

### Part C — Latency, rate limits and cost (15 min)

From the same comparison, read `latency_p50_ms`, `latency_p95_ms`, `mean_input_tokens`,
`mean_output_tokens` and `est_cost_per_10k_listings_usd`.

1. Why do the decision models report (almost) no **output tokens**, while the generative model
   reports hundreds? What are those output tokens?
2. The cost estimate uses the prices in `src/.env` (`PRICE_…`). They are **assumptions**, not read
   from Azure. Look up current prices for your region and re-run `compare`. Does the ranking
   change?
3. **Rate limits.** Every deployment allows a number of requests and tokens per minute (one
   capacity unit = 1 request + 1,000 tokens per minute). Azure counts the **size of the
   request** against the token limit, not the tokens you are billed for. A photo sent as
   base64 counts in full: a request that is billed ~1,000 tokens can use ~4,500 tokens of
   rate limit. Open `Pacer` in `clients.py` and see how the client estimates this and paces
   itself, instead of firing requests and waiting on `429 Too Many Requests`.
4. With your lab's capacities (`DECISION_CAPACITY`, `LUNA_CAPACITY` in `.env`), roughly how many
   listings per minute can each model handle? Which one is the bottleneck?

### Part D — Decide (15 min)

Write a short recommendation, as if for Zava's marketplace team:

- Which model would you use for the gate, and why?
- Would you use **one model for every question**, or different models for different
  questions? (The questions are independent — the code could ask each one with a different
  model.)
- Where, if anywhere, does the generative model belong?

## 🏁 Success criteria

- [ ] You ran all three models on the starter set and compared them side by side.
- [ ] You compared the recorded runs on the **test** split and can name the question that separates the models.
- [ ] You can explain the difference between the two decision APIs' request formats.
- [ ] You can explain why rate limits and cost depend on request size and output tokens.
- [ ] You wrote a recommendation that uses accuracy, unsafe publications, calibration, latency **and** cost.

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| The `llm` run takes much longer | The generative model writes its answer token by token and shares the `gpt-6-luna` capacity with `luna`. That is part of the comparison. |
| `compare` can't find `decision-all.jsonl` | Run it from `src/`. Recorded runs are in `src/data/recorded/` and are found by name. |
| Many `queued` seconds | The client is pacing itself to your capacity. That's expected; only errors are a problem. |
| `errors` is not 0 | Look at the run file (`runs/*.jsonl`) for the `error` field. 401/403: run `az login`. Repeated 429: lower `GATE_MAX_CONCURRENCY` to 1. |

## 🚀 Go further

- **Use Microsoft's benchmark runner on your own deployment.** Clone
  [Decision-Benchmarks](https://github.com/microsoftconnect/Decision-Benchmarks), install the
  `dbrun` runner and run a small benchmark against your `decision` deployment with
  `--limit 20` (see the README's *Microsoft-Decision-1 in Microsoft Foundry* section; use an
  Entra token). Compare its `ece` and `brier` with the gate's.
- Ask the first-draft claims question (`--draft`) to all three models on the starter set. Does
  the generative model cope better with the overlapping options?

## 📚 Learning resources

- [Decision models — Microsoft Foundry primer: "How do we test one on our own data?"](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Microsoft Decision-Benchmarks — how answers are scored](https://github.com/microsoftconnect/Decision-Benchmarks#how-answers-are-scored)
- [Use the Azure OpenAI Decisions API](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
- [Deploy and use Microsoft-Decision-1.1](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [AI Gateway: decision and SystemOne models](https://github.com/Azure-Samples/ai-hub-gateway-solution-accelerator/blob/main/guides/decision-models-guide.md)
- [Azure OpenAI quotas and limits](https://learn.microsoft.com/azure/foundry/foundry-models/quotas-limits)
