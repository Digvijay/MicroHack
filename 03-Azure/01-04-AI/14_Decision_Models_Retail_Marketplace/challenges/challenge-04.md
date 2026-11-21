# Challenge 4 — Where Do I Draw the Line?

**[← Previous](challenge-03.md)** - [Home](../README.md) - [Next Challenge →](challenge-05.md)

## 🎯 Objective

Turn probabilities into decisions you can defend. Put a price on each kind of mistake, let the
console find the cheapest thresholds, open the test split **once**, say honestly how safe the gate
is — and then work the reviewer queue yourself.

## 🧭 Context

A probability is not a decision. The gate compares every probability with two **thresholds**:

```
P(yes) at or above the "yes" threshold  →  the gate acts on its own
P(yes) at or below the "no"  threshold  →  the gate acts on its own
anything in between                      →  unsure: a person decides (review)
```

The defaults are 80% and 20% for every question. They're guesses. The
[primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
and the [Microsoft-Decision-1.1 guidance](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
both say: set thresholds **from the cost of false positives and false negatives**, on labelled data.

Not every mistake costs the same. Publishing a prohibited item is far worse than asking a person to
look at a clean listing. The console prices mistakes in **reviewer-minutes** (one manual review =
1), tries every pair of thresholds, and keeps the cheapest.

**Three splits, three jobs.** You tune on the **threshold** split. The **test** split holds
products the gate never saw while you tuned; you open it once, at the end. If you peek and go back
to change things, the test split stops telling you how the gate will do on new listings.

## ✅ Tasks

### 🧭 Explore — in tab **4 · Thresholds**

#### Part A — Move the line by hand (15 min)

1. Choose **Microsoft-Decision-1.1** (`decision-all.jsonl`) — or your **decision-mine** run from
   Challenge 2.
2. Pick the question **addressed_to_gate**. **Predict:** if you *lower* the thresholds, what happens
   to unsafe listings, and to the share sent to a person?
3. Drag **yes** and **no** down step by step (try 0.10 / 0.05, then 0.03 / 0.01). Watch the four
   numbers and the change against the defaults.
4. Switch to **unsupported_claim**. This time drag **no** *up* (try 0.50). What happens to the
   reviewer workload? Keep going (0.95). When does it start to hurt safety?
5. In one sentence: what are you trading when you move a threshold?

#### Part B — Price the mistakes (15 min)

1. Look at the sliders: what a published prohibited item, contact detail, false spec, note to the
   gate and invented feature cost — and what one manual review costs. Do you agree? Who at Zava
   would have to agree?
2. Click **Find the cheapest thresholds**. Compare **Default thresholds** with **Your cheapest
   thresholds** on the threshold split.
3. Open **Thresholds per question**. Where did the thresholds land? Find `category`: what's the
   choice threshold now, and what does it do to the smart-bulb problem from Challenge 3?
4. Change the costs — make reviews expensive (3), or a published prohibited item cost 300 — and
   tune again. Does anything change? If not, look at the table: when the model's answers are
   cleanly separated, many cost settings lead to the same thresholds. Costs matter most where
   answers overlap.
5. Click **Use these thresholds**. The header now says *your thresholds*.

#### Part C — The final exam (10 min)

1. Click **Open the test split**. **Predict** first: the tuned gate looked very good on the
   threshold split. Will it look as good on products it has never seen?
2. Look at **unsafe rate could still be up to (95%)**. If the gate published 0 unsafe listings out
   of 300, is the unsafe rate zero? Roughly how many clean auto-published listings would you need
   to say "under 1%"?
3. The console counts how often you open the test split. Why does that matter?

#### Part D — Work the reviewer queue (15 min)

1. In **Work the reviewer queue**, choose a model and click **Fill the queue**. The gate runs the
   starter set with your thresholds; everything it isn't sure about lands here.
2. Click a listing ID to open it, read **why the gate wasn't sure**, and decide **Publish** or
   **Reject**. The answer key appears after each decision.
3. Work through at least five. Which reasons were easy? Which needed information the gate didn't
   show you? What would make reviewers faster?

#### Part E — Ship it or not? (5 min)

In your **Where would I use this?** card: which model and thresholds would you launch with, what
share of listings would a person still see, what's the unsafe rate **and its upper bound**, and what
would you monitor in the first month?

### 🛠️ Build *(optional, for developers)*

```bash
python -m gate tune decision-all.jsonl --save state/thresholds.json
python -m gate report decision-all.jsonl --split test --thresholds state/thresholds.json
```

1. Change the costs in `COSTS` in [`gate/tune.py`](../src/gate/tune.py) and tune again.
2. Read `yes_no()` and `decide()` in [`gate/rules.py`](../src/gate/rules.py): what happens to a
   refused, missing or failed answer? (It is never treated as *no*.)
3. Read `upper_bound()` in [`gate/metrics.py`](../src/gate/metrics.py) (one-sided Clopper-Pearson).

## 🏁 Success criteria

- [ ] You moved a threshold by hand and can say what you traded.
- [ ] You tuned thresholds from costs on the **threshold** split and compared them with the defaults.
- [ ] You opened the test split and can state the unsafe rate **with its upper bound**.
- [ ] You worked at least five listings in the reviewer queue.
- [ ] You wrote a ship / don't-ship recommendation with numbers.

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| *The chat model returns no probabilities* | Thresholds need probabilities. Choose a decision-model run. |
| The header still says *default thresholds* | Click **Use these thresholds** after tuning. |
| The queue is empty | Click **Fill the queue** and wait for it to finish (about a minute). |
| Thresholds look extreme (for example *no ≤ 0.01*) | That's what the costs asked for. Check the misses and false alarms in the table, then decide whether you agree with the costs. |

## 🧠 Reflection

- Who in your organisation would own the costs? Have they ever been written down?
- The upper bound often surprises people. How would you explain it to a manager in one sentence?
- What would a "shadow run" look like for your use case — the model deciding, people still checking
  everything, for a few weeks?

## 📚 Learning resources

- [Decision models primer: "Set thresholds from real costs"](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Microsoft-Decision-1.1 — best practices for thresholds and abstention](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [OpenAI Agents SDK — decision recipes (thresholds from labelled data, refusals go to review)](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
- [Decision actions in Azure Logic Apps — designed for human oversight](https://techcommunity.microsoft.com/blog/integrationsonazureblog/announcing-decision-apis-as-actions-in-azure-logic-apps/4573643)
