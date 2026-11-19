# Solution 3 — Same Questions, Three Ways

**[← Back to Challenge 3](../../challenges/challenge-03.md)** · [Home](../../README.md)

## Part A — The three clients

| Client | URL | Photo | Probabilities |
|--------|-----|-------|---------------|
| `ask_decision` | `{DECISION_ENDPOINT}/providers/microsoft/v1/systemone` | base64 **asset** (`assets: {"photo.jpg": ...}`), referenced as `"image:photo.jpg"` in `state` | In the response: P(yes) for `noul`, a distribution for `choice` / `score` |
| `ask_luna` | `{OPENAI_ENDPOINT}/openai/v1/decisions` (`client.decisions.create`) | `input_image` part with a `data:` URL | In the response, per question, for every choice / level |
| `ask_llm` | `{OPENAI_ENDPOINT}/openai/v1/responses` (`client.responses.create`, JSON schema output) | `input_image` part | **None.** The model writes JSON values; there is nothing to threshold |

## Part B — All 603 listings, test split

```bash
uv run python -m gate compare decision-all.jsonl luna-all.jsonl llm-all.jsonl --split test
```

| | Microsoft-Decision-1.1 | gpt-6-luna Decisions | gpt-6-luna Responses (LLM) |
|---|---:|---:|---:|
| `category` | 0.921 | 0.952 | 1.000 |
| `unsupported_claim` | 0.959 | **0.896** | 0.995 |
| `addressed_to_gate` | **0.958** | 1.000 | 0.983 |
| Other six questions | ≥ 0.991 | ≥ 0.987 | 1.000 |
| Gate outcome accuracy (default thresholds) | 0.845 | 0.903 | 0.979 |
| Review rate | 0.571 | 0.576 | 0.466 |
| **Unsafe publications** | **6** | **0** | **4** |
| Latency p50 / p95 | 264 / 368 ms | 591 / 1,857 ms | 2,735 / 4,351 ms |
| Tokens in / out | 1,039 / 8.8 | 1,955 / 0 | 1,078 / 200 |
| Est. cost per 10,000 listings* | $0.52 | $1.96 | $2.08 |

\* With the example prices in `.env.example`. Check real prices before you quote them.

Answers:

1. All three are near-perfect on prohibited items, off-platform contact, contradictions and photos.
   The questions that separate them are **`addressed_to_gate`** (Microsoft-Decision-1.1 misses the
   quiet *"verified by Zava staff"* notes), **`unsupported_claim`** (gpt-6-luna Decisions reads
   marketing talk as claims) and **`category`**.
2. Microsoft-Decision-1.1 publishes 6 and the generative model 4 unsafe listings — almost all
   `hard:subtle_aimed_at_gate` (one Microsoft-Decision-1.1 case, ZM-0537, is a contradicted piece
   count). gpt-6-luna Decisions publishes none.
3. The generative model has the **best accuracy** with default thresholds. What it doesn't give you
   is a **probability**: you can't tune it (Challenge 4), you can't tell a sure answer from a guess,
   and you can't send only the uncertain ones to a person. It is also ~10× slower and the most
   expensive. Its accuracy is a fair result — a decision model has to earn its place, as the primer
   says.
4. `unsupported_claim` is the worst calibrated for both decision models (ECE ≈ 0.16 for
   Microsoft-Decision-1.1, ≈ 0.11 for gpt-6-luna on the test split): many answers between 0.1 and 0.5
   that are never true.

## Part C — Latency, rate limits and cost

1. A decision model's answer **is** the probabilities; it doesn't write text. The generative model's
   ~200 output tokens are the JSON it writes (plus any reasoning) — you pay for them and wait for them.
2. Ranking: Microsoft-Decision-1.1 is the cheapest at any realistic price, because it uses about half
   the input tokens of gpt-6-luna and no output tokens. gpt-6-luna Decisions and Responses are close
   on input; Responses adds output tokens.
3. The `Pacer` estimates **characters of the request body ÷ 4** — a 384 px JPEG in base64 is most
   of it. A typical gpt-6-luna request counts as **~4,100 tokens** against the limit while being
   billed ~1,950.
4. Rough throughput (pacing on whichever limit is hit first):

   | Deployment | Capacity | Limit | Listings per minute |
   |------------|---------:|-------|--------------------:|
   | `decision` | 500 | 500 requests, 500,000 tokens / min | **~120** (token limit) |
   | `gpt-6-luna` | 40 | 40 requests, 40,000 tokens / min | **~10** — the bottleneck, shared by `luna` and `llm` |

## Part D — A sample recommendation

> **Use Microsoft-Decision-1.1 as the main gate**, with thresholds tuned in Challenge 4 and an
> improved `addressed_to_gate` question (Challenge 2), because it is the fastest (~0.3 s), the
> cheapest, and gives calibrated probabilities on every question except `unsupported_claim`.
> **Ask `addressed_to_gate` with gpt-6-luna Decisions** as a second opinion until the improved
> wording is proven on more data: it caught every quiet note. Keep the **generative model out of
> the gate**: no probabilities, 10× the latency. Use it where text must be written — rewriting
> listings for sellers (Challenge 6) — and let a decision model check what it writes.

## Learn more

- [Decision models — Microsoft Foundry primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Microsoft Decision-Benchmarks — how answers are scored](https://github.com/microsoftconnect/Decision-Benchmarks#how-answers-are-scored)
- [AI Gateway: decision and SystemOne models](https://github.com/Azure-Samples/ai-hub-gateway-solution-accelerator/blob/main/guides/decision-models-guide.md)
