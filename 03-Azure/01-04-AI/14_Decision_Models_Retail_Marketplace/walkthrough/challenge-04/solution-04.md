# Solution 4 — Where Do I Draw the Line?

**[← Back to Challenge 4](../../challenges/challenge-04.md)** · [Home](../../README.md)

All numbers come from the recorded runs, so yours match as long as you use the same run and
settings. "Threshold split" = 524 listings; "test split" = 516 listings of products never seen
while tuning.

## Part A — Moving the line by hand (Microsoft-Decision-1.1, threshold split)

Starting point, default 0.20 / 0.80 for every question: **88.9%** outcome accuracy, **20.4%** sent
to a person, **379** published automatically, **5** of them unsafe.

| Question | Your thresholds (no / yes) | Accuracy | Sent to a person | Published | Unsafe |
|----------|----------------------------|---------:|-----------------:|----------:|-------:|
| `addressed_to_gate` | 0.20 / 0.50 | 88.9% | 20.4% | 379 | 5 |
| `addressed_to_gate` | 0.05 / 0.10 | 89.3% | 20.8% | 377 | 3 |
| `addressed_to_gate` | **0.01 / 0.03** | 89.9% | 21.4% | 374 | **0** |
| `unsupported_claim` | **0.50 / 0.80** | **93.3%** | **16.0%** | 402 | 5 |
| `unsupported_claim` | 0.95 / 0.99 | 93.1% | 15.8% | 403 | **6** |

What you're trading:

- **`addressed_to_gate`:** on the threshold split, Microsoft-Decision-1.1 gives the twelve quiet
  *"verified by staff"* notes anything from 0.01 to 0.72 — five of them below 0.10. Treating even a
  small probability as *yes* catches them all, at the price of a few more reviews. A low threshold
  is right when a miss is expensive.
- **`unsupported_claim`:** the model is **under-confident about "no"** — many honest listings get
  0.2–0.5 (you saw this in the Challenge 3 calibration chart). Raising the *no* threshold sends
  ~4% fewer listings to a person without losing safety. Go too far and an invented claim slips
  through.

## Part B — Thresholds from costs

| Microsoft-Decision-1.1, threshold split | Accuracy | Sent to a person | Published | Unsafe | Upper bound |
|-------------------------------------------|---------:|-----------------:|----------:|-------:|------------:|
| Default 0.20 / 0.80 | 88.9% | 20.4% | 379 | 5 | 2.8% |
| Cheapest thresholds (default costs) | **100%** | **11.3%** | 427 | **0** | 0.7% |

The tuned thresholds per question:

| Question | Thresholds |
|----------|------------|
| `category` | choice ≥ **0.88** |
| `prohibited_item` | no ≤ 0.11 · yes ≥ 0.86 |
| `off_platform_contact` | no ≤ 0.02 · yes ≥ 0.97 |
| `contradicts_facts` | no ≤ 0.68 · yes ≥ 0.97 |
| `unsupported_claim` | no ≤ **0.84** · yes ≥ 0.94 |
| `addressed_to_gate` | no ≤ **0.01** · yes ≥ **0.02** |
| `photo_shows_product` | no ≤ 0.02 · yes ≥ 0.60 |
| `photo_matches_title` | no ≤ 0.25 · yes ≥ 0.61 |
| `listing_quality` (P poor) | no ≤ 0.27 · yes ≥ 0.73 |

- **`category` at 0.88** fixes the smart-bulb problem: the model is only 66–83% sure the bulb is
  *lighting*, so instead of a wrong automatic fix, the listing goes to a person.
- **Changing the costs** (reviews cost 3; a prohibited item costs 300) gives the **same gate** on this
  data. Microsoft-Decision-1.1 separates the threshold split so cleanly that there's a threshold pair
  with no mistakes for every question — whatever the costs. Costs matter when answers overlap: in a
  real marketplace, with messier listings, they will.
- gpt-6-luna Decisions: 88.0% → **98.9%** accuracy, 23.3% → 12.4% sent to a person, 0 unsafe either way.

## Part C — The final exam (test split)

| | Accuracy | Sent to a person | Published | Unsafe | Upper bound | Automatic fixes (correct) |
|---|---:|---:|---:|---:|---:|---:|
| Decision-1.1, default | 79.5% | 25.4% | 350 | 6 | 3.4% | 29 (6) |
| Decision-1.1, **tuned** | **92.6%** | 18.2% | 388 | **2** | 1.6% | 7 (7) |
| gpt-6-luna, default | 85.7% | 25.4% | 350 | 0 | 0.85% | 11 (8) |
| gpt-6-luna, **tuned** | **94.4%** | 16.5% | 396 | **0** | 0.75% | 12 (8) |

- **The threshold split said 100%; the test split says 92.6%.** Thresholds fitted to one set of
  products are a little too fitted. That's the whole reason the test split exists — and why opening
  it again and again would quietly turn it into a second threshold split.
- The two unsafe listings on test with tuned Decision-1.1: one quiet note to the reviewer and one
  invented claim. Fixing the `addressed_to_gate` *question* (Challenge 2) removes the first kind for
  good; thresholds alone can't.
- **0 unsafe out of 396 is not zero.** The upper bound is **0.75%**: "under 1%, probably" is the honest
  statement. With zero failures, the upper bound is roughly 3 ÷ *n*, so "under 1%" needs about 300
  clean auto-published listings — and "under 0.1%" about 3,000. In practice that means a **shadow
  run** on real traffic, with people still checking everything.
- **Automatic category fixes:** with default thresholds Decision-1.1 makes 29 fixes and only 6 are
  right (the smart bulb). Tuned, it makes 7 and all are right.

## Part D — Reviewer queue

With default thresholds, Microsoft-Decision-1.1 sends **10 of the 24** starter listings to the
queue (8 published, 5 rejected, 1 auto-fixed). Easy reasons: *implausible price (34% of the reference price)*, *no photo*, *GTIN not in
catalogue*, *poor listing quality*. Hard ones: *the model is unsure: unsupported claim* — a reviewer
needs the claim highlighted next to the facts. Good ideas from attendees: show the reference price,
highlight the sentence that triggered the reason, and show the model's probability.

## Part E — A sample recommendation

> Launch with **gpt-6-luna Decisions** and cost-tuned thresholds: 94.4% accuracy on 516 unseen
> listings, **0 unsafe of 396 published** (upper bound 0.75%), 16.5% to a person. Move to
> **Microsoft-Decision-1.1** — about 2× faster and 4× cheaper — once the improved `addressed_to_gate`
> question is in production: tuned, it's at 92.6% with 2 unsafe of 388 (upper bound 1.6%). Run a
> four-week **shadow** with people still reviewing everything; roll back if any prohibited item or
> off-platform contact is published automatically.

## Build track

`python -m gate tune decision-all.jsonl --save state/thresholds.json` prints the same table as the
console and the default-vs-tuned comparison on the test split. In `rules.py`, `yes_no()` returns
`"failed"` for any answer whose status isn't `ok`, and `decide()` turns that into a **review**
reason: a failed answer is never treated as *no*.

## Learn more

- [Decision models primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [OpenAI Agents SDK — decision recipes](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
