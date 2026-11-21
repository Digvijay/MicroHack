# Challenge 3 — Can I Trust the Numbers?

**[← Previous](challenge-02.md)** - [Home](../README.md) - [Next Challenge →](challenge-04.md)

## 🎯 Objective

Judge three ways of answering the gate's questions — Microsoft-Decision-1.1, gpt-6-luna through the
Decisions API, and gpt-6-luna as a chat model — on **all 1,310 labelled listings**, the way
Microsoft judges its own decision models. Then decide which you would use, and for what.

## 🧭 Context

Microsoft's primer says a decision model *"earns its place on our workload, not on a benchmark"*:
collect labelled inputs, run the decision model **and a larger model**, and compare **accuracy,
latency and cost per decision** — and check **calibration** before you let it act on its own.
That's this challenge.

Running every listing through three models for every attendee would use the whole room's quota,
so the hack ships **recorded runs** of all three models on every listing, made with the same code.
Comparing them is instant and free.

What the numbers mean:

| In the console | Plain meaning |
|----------------|---------------|
| **Outcome accuracy** | How often the gate's final outcome (publish / fix / review / reject) matched the answer key |
| **Unsafe listings published** | Listings the gate published that should have gone to a person or been rejected. The number that hurts. |
| **Sent to a person** | The share of listings that end up in the reviewer queue — someone's workload |
| **Typical latency (p50)** | How long one listing takes, for half of the listings |
| **Per 10,000 listings** | Estimated cost from the tokens used (example prices — check current Azure prices) |
| **Calibration** | When the model says 70%, is it right about 70% of the time? |

## ✅ Tasks

### 🧭 Explore — in tab **3 · Compare**

#### Part A — Predict, then compare (15 min)

1. **Predict:** which of the three will be most accurate? Pick one.
2. Keep the split on **test** and the three recorded runs ticked. If you created a
   **decision-mine** run in Challenge 2, tick it too. Click **Compare**.
3. **See:** for each model, read the cards. Then answer:
   - Which is the most accurate? Were you right?
   - Which publishes the most **unsafe** listings? Click the IDs under *Which unsafe listings got
     through?* — what kind of listing are they?
   - What does the chat model **not** give you that the other two do?
   - How do latency and cost compare? How many output tokens does each write per listing?
4. Look at **Accuracy per question**. Which questions do all three get right? Which question
   separates them?
5. If you have a **decision-mine** run: did your improved question from Challenge 2 hold up on
   516 listings it had never seen?

#### Part B — Can you trust the probabilities? (15 min)

1. In **When the model says 70%, is it right 70% of the time?**, choose Microsoft-Decision-1.1 and
   the question `unsupported_claim`.
2. Light bars show what the model said; dark bars show how often the answer was actually *yes*.
   Where do they match? Where don't they?
3. Switch to `addressed_to_gate` and `category`, and to gpt-6-luna. Which questions have
   probabilities you'd trust enough to act on automatically?
4. Under each band is the number of answers in it. Why should you ignore a band with only 2
   answers?

> [!TIP]
> Look at `category` on the test split: almost every mistake is the **smart LED bulb** — is it
> `smart_home` or `lighting`? The model isn't sure either (66–83%). When the labels themselves
> overlap, fix the question or the policy, not the model. You'll set a threshold for it in
> Challenge 4.

#### Part C — Decide (10 min)

Write a short recommendation for Zava's marketplace team in your **Where would I use this?**
card, or in your own notes:

- Which model for the gate, and why — using accuracy, **unsafe**, calibration, latency **and** cost?
- One model for every question, or different models for different questions?
- Where, if anywhere, does the chat model belong?

### 🛠️ Build *(optional, for developers)*

```bash
python -m gate compare decision-all.jsonl luna-all.jsonl llm-all.jsonl --split test
python -m gate report decision-all.jsonl --split threshold --calibration
```

1. Read `question_metrics()` in [`gate/metrics.py`](../src/gate/metrics.py). It scores answers the
   same way as Microsoft's [Decision-Benchmarks](https://github.com/microsoftconnect/Decision-Benchmarks)
   runner: yes/no counts as *yes* at P ≥ 0.5, failed answers count against **coverage**, not
   accuracy, and calibration uses 10 bins (ECE) and the Brier score.
2. Run Microsoft's own benchmark runner against your `decision` deployment on a small sample
   (`--limit 20`), following the *Microsoft-Decision-1 in Microsoft Foundry* section of the
   Decision-Benchmarks README, and compare its numbers with the gate's.

## 🏁 Success criteria

- [ ] You compared the three models on the **test** split and can name the question that separates them.
- [ ] You can explain why the most accurate model isn't automatically the best choice.
- [ ] You read a calibration chart and can say where the probabilities are trustworthy.
- [ ] You wrote a recommendation that uses accuracy, unsafe publications, calibration, latency and cost.

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| No **decision-mine** run in the list | Run **Re-score with my questions** in the Question studio first, then reload this tab. |
| The calibration chart is empty | The chat model has no probabilities. Choose a decision model. |
| Numbers differ slightly from your neighbour's | Only runs you created yourself differ; the recorded runs are the same for everyone. |

## 🧠 Reflection

- If the chat model is more accurate, why would anyone use a decision model? When would you
  choose the chat model anyway?
- Accuracy on 516 listings — how many unsafe listings would that be at 10,000 listings a day?
- What labelled data do you already have in your organisation that you could test a decision
  model on next week?

## 📚 Learning resources

- [Decision models primer: "How do we test one on our own data?"](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Microsoft Decision-Benchmarks — how answers are scored](https://github.com/microsoftconnect/Decision-Benchmarks#how-answers-are-scored)
- [Microsoft-Decision-1.1 announcement (benchmarks, pricing)](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-microsoft-decision-1-1-build-faster-more-efficient-ai-applications-w/4573877)
- [Artificial Analysis Decision Index](https://artificialanalysis.ai/evaluations/artificial-analysis-decision-index)
