# Challenge 4 — From Probabilities to a Gate

**[← Previous](challenge-03.md)** - [Home](../README.md) - [Next Challenge →](challenge-05.md)

## 🎯 Objective

Turn probabilities into actions you can defend. You will check whether the probabilities can
be trusted, choose **thresholds** from the **cost of each kind of mistake** on held-out data,
measure the finished gate **once** on the test split, say honestly how safe it is, and work the
**reviewer queue** like a member of Zava's marketplace team.

## 🧭 Context

A probability is not a decision. The gate's rules ([`rules.py`](../src/gate/rules.py)) compare
every probability with two thresholds:

```
P(yes) >= yes threshold   ->  "yes"     (the gate acts on its own)
P(yes) <= no threshold    ->  "no"      (the gate acts on its own)
anything in between       ->  "unsure"  (a person decides: review)
```

The defaults are `yes = 0.80`, `no = 0.20` and `choice = 0.70` for every question. They are
guesses. Microsoft's [decision models primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
says to **set thresholds from real costs**, on labelled data, *"not left at 0.5 by default"*.
The OpenAI Agents SDK's
[decision recipes](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
do the same: thresholds come from a labelled set, and a refusal or an unsure answer goes to a
person.

**Not every mistake costs the same.** [`tune.py`](../src/gate/tune.py) gives every question three
costs, in reviewer-minutes (one manual review = 1):

| Question | Miss (problem let through) | False alarm (clean listing acted on) | Review |
|----------|---------------------------:|-------------------------------------:|-------:|
| `prohibited_item` | 100 | 20 (wrongful reject) | 1 |
| `off_platform_contact` | 50 | 20 | 1 |
| `contradicts_facts` | 20 | 20 | 1 |
| `addressed_to_gate` | 20 | 1 | 1 |
| `photo_matches_title` | 10 | 1 | 1 |
| `unsupported_claim`, `photo_shows_product` | 5 | 1 | 1 |
| `listing_quality` | 2 | 1 | 1 |
| `category` (choice) | 5 for a wrong automatic fix | — | 1 |

The tuner tries every pair of thresholds on the **threshold** split and keeps the cheapest.

**Three splits, three jobs.** You design on `dev`, choose thresholds on `threshold`, and measure on
`test` — **once**. A product never appears in two splits, so a threshold can't be tuned to one
product's photos and then "tested" on the same product. If you look at the test results and go
back to change a threshold, the test split has become a second threshold split and its numbers
no longer tell you how the gate will do on new listings.

**How safe is "3 unsafe out of 76"?** A small sample can't prove a low error rate. `metrics.py`
reports a 95% **upper bound** for the unsafe rate (Clopper-Pearson). A rough rule: with **zero**
failures in *n* listings, the true rate could still be about **3 / n**.

## ✅ Tasks

### Part A — The gate with default thresholds (10 min)

Use the recorded Microsoft-Decision-1.1 run, so everyone works with the same numbers:

```bash
uv run python -m gate report decision-all.jsonl --split test
```

Write down: outcome accuracy, review rate, how many listings were auto-published, how many of
those were **unsafe**, and the upper bound. Which kinds of listing slipped through?

### Part B — Can you trust the probabilities? (10 min)

Thresholds only make sense if a probability of 0.9 means "right about 9 times in 10". Look at
the reliability tables on the **threshold** split:

```bash
uv run python -m gate report decision-all.jsonl --split threshold --calibration
```

Each row is a bin of answers: how many (`n`), their mean probability, and how often the answer
was actually *yes*.

1. Which questions are **well calibrated** (mean P close to "actually true" in every bin with a
   real `n`)?
2. Look at `unsupported_claim`. About 120 answers sit between 0.1 and 0.5 and **none** of them is
   true. What does a `no` threshold of 0.20 do to all of those listings?
3. Look at `addressed_to_gate`. Every answer between 0.2 and 0.7 is **true**. Is a mid-range
   probability here "unsure", or a quiet "yes"?
4. Run the same command with `--split test` and look at `category`. On the threshold split
   almost every category answer is above 0.9; on the test split 16 answers fall between 0.6 and
   0.8, and none of them is right. What does that tell you about thresholds chosen on one set
   of products and used on another?

### Part C — Choose thresholds from costs (20 min)

1. Run the tuner on the recorded run. It chooses thresholds on the **threshold** split, saves
   them, and then shows the **test** split with the default and the tuned thresholds:
   ```bash
   uv run python -m gate tune decision-all.jsonl --save state/thresholds.json
   ```
2. Read the table at the top. For each question: where did the thresholds land, and how many
   misses, false alarms and reviews do they cause on the threshold split?
3. Compare the two test summaries at the bottom. What changed: accuracy, review rate,
   auto-published listings, unsafe publications, upper bound?
4. Do the same for gpt-6-luna and compare:
   ```bash
   uv run python -m gate tune luna-all.jsonl --save state/thresholds-luna.json
   ```
5. **Change the costs.** Zava's reviewers are fully booked next quarter. In
   [`tune.py`](../src/gate/tune.py), set every `review` cost to `3` and run both tuners again
   (without `--save`). Which model's gate changes, and how? Put the costs back afterwards.

> [!IMPORTANT]
> The tuner picks the cheapest thresholds **for the costs you give it**. The costs are a
> business decision, not a technical one. Write down who at Zava would have to agree to them.

### Part D — How sure can you be? (5 min)

1. With tuned thresholds, Microsoft-Decision-1.1 auto-publishes 76 test listings and 3 of them are
   unsafe. What is the upper bound? Would you tell Zava "the gate publishes about 4% unsafe
   listings"?
2. gpt-6-luna auto-publishes about 70 test listings and **none** is unsafe. Is the unsafe rate
   zero? What is the upper bound?
3. Roughly how many auto-published listings, with zero unsafe ones, would you need before you
   could say "under 1%"? Where would you get them?

### Part E — Work the reviewer queue (10 min)

1. Restart the console (it reads `state/thresholds.json` when it starts):
   ```bash
   uv run uvicorn ui.app:app --reload --port 8000
   ```
   The header now says **tuned thresholds**.
2. Open **Reviewer queue**, choose **Microsoft-Decision-1.1**, split `dev`, **starter set only**,
   and click **Run gate**.
3. Work through at least five listings. Click the listing ID to open it, read the reasons, and
   choose **Publish** or **Reject**. The queue then shows the answer key.
4. Which reasons were easy to decide? Which needed information the gate didn't show you? What
   would you add to the queue to make reviewers faster?

### Part F — Ship or don't ship (5 min)

Write a short recommendation for Zava's marketplace lead, with numbers from the **test** split:

- Which model and which thresholds you would start with.
- What share of listings a person still has to see, and why that is acceptable (or not).
- The unsafe rate **and** its upper bound, and the one kind of listing that worries you most.
- What you would monitor in the first month, and what would make you roll back.

## 🏁 Success criteria

- [ ] You read the reliability tables and can explain where the probabilities are and aren't trustworthy.
- [ ] You tuned thresholds on the **threshold** split and compared default and tuned thresholds on the **test** split.
- [ ] You changed the costs and can explain how the thresholds and the gate responded.
- [ ] You can explain why the test split may be used only once.
- [ ] You can state the gate's unsafe rate with its upper bound.
- [ ] You worked at least five listings in the reviewer queue.
- [ ] You wrote a ship / no-ship recommendation with numbers.

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| `This run has no listings from the threshold split` | You passed your own starter run. Tune on a recorded run (`decision-all.jsonl`) or an `evaluate --split threshold` run of your own. |
| The console still says **default thresholds** | Save to `src/state/thresholds.json` exactly, then restart `uvicorn`. |
| Tuned thresholds look extreme (for example `no <= 0.01`) | That's what the costs asked for. Look at how many misses and false alarms the question has, then decide if you agree with the costs. |
| Your tuned numbers differ from your neighbour's | Check you both tuned on the same recorded run with the same costs in `tune.py`. |

## 🚀 Go further

- **Tune on your own data.** Run Microsoft-Decision-1.1 on 40 threshold listings with your
  improved wording from Challenge 2
  (`uv run python -m gate evaluate --split threshold --limit 40`) and tune on that run. With so
  few listings, how stable are the thresholds?
- **One model per question.** The questions are independent. Using the two recorded runs, which
  model would you choose for each question? Sketch how `evaluate.run` would ask each question
  with a different model.
- Read how Microsoft's alert-routing sample turns a decision into an action and fails safe when
  it can't decide:
  [`alert-investigation-eventhub`](https://github.com/Azure-Samples/azure-functions-hosted-skills-samples/tree/main/alert-investigation-eventhub).

## 📚 Learning resources

- [Decision models — Microsoft Foundry primer: "How do we make the answers trustworthy?"](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Microsoft Decision-Benchmarks — calibration (ECE, Brier)](https://github.com/microsoftconnect/Decision-Benchmarks#how-answers-are-scored)
- [OpenAI Agents SDK — decision recipes (thresholds from labelled data, refusals go to review)](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
- [Deploy and use Microsoft-Decision-1.1 — limitations](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
