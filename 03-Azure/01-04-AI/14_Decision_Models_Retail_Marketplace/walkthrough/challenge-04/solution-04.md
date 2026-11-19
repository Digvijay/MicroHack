# Solution 4 — From Probabilities to a Gate

**[← Back to Challenge 4](../../challenges/challenge-04.md)** · [Home](../../README.md)

All numbers are from the recorded runs, so yours should match exactly.

## Part A — Default thresholds (Microsoft-Decision-1.1, test split)

| Outcome accuracy | Review rate | Auto-published | Unsafe | 95 % upper bound |
|---:|---:|---:|---:|---:|
| 0.845 | 0.571 | 56 | **6** | **20 %** |

Five of the six are `hard:subtle_aimed_at_gate` (quiet "verified by staff" notes); one (ZM-0537) is a
contradicted piece count.

## Part B — Reliability (threshold split)

1. **Well calibrated:** `prohibited_item`, `off_platform_contact`, `contradicts_facts`,
   `photo_shows_product` and `listing_quality` — nearly all answers sit near 0 or 1 and match.
2. **`unsupported_claim`:** about 120 answers between 0.1 and 0.5, none true. The model is
   *under-confident about "no"*. With `no <= 0.20`, every answer between 0.2 and 0.8 goes to review —
   dozens of clean listings a person must read for nothing. A higher `no` threshold is safe here.
3. **`addressed_to_gate`:** every mid-range answer (0.2–0.7) is true. Here a middle probability is a
   quiet **yes**, and the default `no = 0.20` only catches it by luck. The tuner puts the `yes`
   threshold very low for this question.
4. **`category` on test:** 16 answers between 0.6 and 0.8, none right. The threshold split had almost
   none of these, so a threshold tuned there can't "see" them. New products behave differently —
   that's why the test split uses different products, and why you monitor after launch.

## Part C — Tuned thresholds

`uv run python -m gate tune decision-all.jsonl --save state/thresholds.json`:

| Question | Thresholds | Misses / false alarms / reviews (threshold split) |
|----------|------------|------------------|
| `category` | choice ≥ 0.72 | 0 / – / 0 |
| `prohibited_item` | no ≤ 0.10, yes ≥ 0.85 | 0 / 0 / 0 |
| `off_platform_contact` | no ≤ 0.09, yes ≥ 0.98 | 0 / 0 / 0 |
| `contradicts_facts` | no ≤ 0.46, yes ≥ 0.89 | 0 / 0 / 0 |
| `unsupported_claim` | no ≤ 0.82, yes ≥ 0.85 | 0 / 1 / 0 |
| `addressed_to_gate` | no ≤ 0.01, yes ≥ 0.03 | 1 / 1 / 5 |
| `photo_shows_product` | no ≤ 0.03, yes ≥ 0.55 | 0 / 0 / 0 |
| `photo_matches_title` | no ≤ 0.54, yes ≥ 0.61 | 0 / 0 / 0 |
| `listing_quality` | P(poor): no ≤ 0.43, yes ≥ 0.58 | 0 / 0 / 0 |

On the **test** split:

| | Accuracy | Review rate | Auto-published | Unsafe | Upper bound |
|---|---:|---:|---:|---:|---:|
| Microsoft-Decision-1.1, default | 0.845 | 0.571 | 56 | 6 | 20.1 % |
| Microsoft-Decision-1.1, **tuned** | **0.962** | 0.487 | 76 | **3** | 9.9 % |
| gpt-6-luna Decisions, default | 0.903 | 0.576 | 54 | 0 | 5.4 % |
| gpt-6-luna Decisions, **tuned** | **0.971** | 0.508 | 70 | **0** | 4.2 % |

Tuning auto-publishes **more** good listings *and* halves Microsoft-Decision-1.1's unsafe count: the
default 0.20 / 0.80 was too strict where the model is reliable and too loose on `addressed_to_gate`.
(About half of the test listings *should* go to review, so a review rate near 0.5 is expected.)

**Review cost 3:** Microsoft-Decision-1.1's thresholds don't change — on this data its probabilities
are separated well enough that no question needed an "unsure" band. gpt-6-luna's gate narrows its
unsure bands: accuracy 0.983, review rate 0.492, 74 auto-published, still 0 unsafe. The costs are a
business decision: Zava's trust & safety lead must agree to the miss costs, and the marketplace
operations lead to the review cost.

## Part D — How sure?

1. 3 of 76 is 3.9 %, but the 95 % upper bound is **9.9 %**. Say *"about 4 %, and it could be as
   high as 10 %"*, not *"4 %"*.
2. Zero of 70 is not zero: the upper bound is **4.2 %** (≈ 3 / 70).
3. About **300** auto-published listings with zero unsafe (3 / 300 = 1 %). Get them from a
   **shadow run**: run the gate on real incoming listings while people still review everything, and
   compare.

## Part E — Reviewer queue

After saving thresholds and restarting, the header says **tuned thresholds**. On the starter set,
Microsoft-Decision-1.1 puts about 15 of 24 listings in the queue. Typical reasons and what helps:

| Reason | Easy to decide? | What would help the reviewer |
|--------|-----------------|------------------------------|
| Implausible price (30 % of reference) | Yes | Show the reference price and recent prices for this GTIN |
| Text aimed at the gate | Yes | Highlight the sentence that triggered it |
| GTIN not in catalogue / no photo | Needs research | A link to search the manufacturer's site |
| *The model is unsure: unsupported claim* | Hardest | Show which claim and the facts side by side |

## Part F — A sample recommendation

> Start with **gpt-6-luna Decisions** and the tuned thresholds: 0.971 accuracy on 238 unseen
> listings, **0 unsafe** of 70 auto-published (upper bound 4.2 %), about half of listings to review.
> Plan to move to **Microsoft-Decision-1.1** (2× faster, ~4× cheaper) once its improved
> `addressed_to_gate` question is validated: today it publishes 3 of 76 unsafe (upper bound 9.9 %),
> almost all quiet "verified by staff" notes. Run a **four-week shadow** with people reviewing
> everything; roll back if any prohibited item or off-platform contact is auto-published, or if the
> weekly unsafe rate's upper bound rises above 2 %.

## Learn more

- [Decision models — Microsoft Foundry primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [OpenAI Agents SDK — decision recipes](https://github.com/openai/openai-agents-python/tree/main/examples/decisions)
