# Solution 1 — Set Up and Ask Your First Questions

**[← Back to Challenge 1](../../challenges/challenge-01.md)** · [Home](../../README.md)

## Setup checklist

| Step | Done when |
|------|-----------|
| Azure portal | Your resource group contains one Foundry resource `dm-…` with the deployments `decision`, `gpt-6-luna` and `decision-judge`. |
| GitHub | Your fork has a unique name and your Codespace was created with **New with options…** and the **Azure / AI / Decision Models Retail Marketplace** dev container. |
| `src/.env` | `DECISION_ENDPOINT`, `OPENAI_ENDPOINT` and the capacities are filled in from your Hackbox. |
| `gate check` | Prints three `ok` lines and **All good - you're ready.** |

A successful check looks like this (latencies vary; the first call includes signing in):

```
Checking your configuration and sign-in...

  DECISION_ENDPOINT  https://dm-xxxxxxxxxxxx.services.ai.azure.com
  OPENAI_ENDPOINT    https://dm-xxxxxxxxxxxx.openai.azure.com
  Entra sign-in      ok
  Microsoft-Decision-1.1     ok      P(yes)=1.00  (1863 ms)
  gpt-6-luna Decisions API   ok      P(yes)=1.00  (1689 ms)
  gpt-6-luna Responses API   ok      answer=True  (1252 ms)

All good - you're ready.
```

## Part E — What to notice in the console

Click **Ask the three models** on **ZM-0088**, a skillet listing that ends with *"Customers love
it - a great choice for any home."* The answer key says **publish**: that sentence is marketing
talk, not a product claim (policy section 3).

| | Microsoft-Decision-1.1 | gpt-6-luna Decisions | gpt-6-luna Responses (LLM) |
|---|---|---|---|
| `unsupported_claim` | P(yes) = **0.21** | P(yes) = **0.77** | `false` (no probability) |
| Outcome with default thresholds | **review** (0.21 is just above the `no` threshold of 0.20) | **review** | **publish** |
| Tokens in / out | ~1,080 / 9 | ~2,000 / 0 | ~1,100 / ~190 |

Things to point out:

- The two decision models **disagree in strength**. Microsoft-Decision-1.1 is fairly sure there is
  no unsupported claim; gpt-6-luna leans the other way. With the default thresholds both end up in
  review — the gate is cautious when it isn't sure.
- The generative model got this one right, but you can't tell **how sure** it was. You can't set a
  threshold on `false`.
- The decision models write almost **no output tokens** — the answer is the probabilities.

## Part F — Example custom questions

With Microsoft-Decision-1.1:

| Listing | Type | Question | Options / levels | Result |
|---------|------|----------|------------------|--------|
| ZM-0003 (garden hose) | Yes/no | *Is this product meant to be used outdoors?* | | P(yes) = **0.998** |
| ZM-0098 (desk lamp) | Yes/no | same | | P(yes) = **0.007** — a confident *no* |
| ZM-0053 (5 L tin of wall paint) | Choice | *Which material is the product mainly made of?* | `metal, plastic, wood, fabric, cannot tell` | `metal` 0.76, `cannot tell` 0.21, the rest ≤ 0.03 |

How to read the choice result: the model picked `metal` (the tin), but gave one chance in five to
`cannot tell`. Paint isn't really "made of" any of those materials. The `cannot tell` option gave
the model a **way out** — without it, that probability would have been forced onto a wrong
option. Challenge 2 comes back to this rule.

## Go further — the two request formats

`systemone_question` and `decisions_question` in [`clients.py`](../../src/gate/clients.py) turn one
question into each API's format. Three differences:

1. **Yes/no type name:** `noul` (Microsoft-Decision-1.1) vs `predicate` (Decisions API).
2. **Container:** Microsoft-Decision-1.1 takes `questions` as an **object keyed by name**; the
   Decisions API takes an **array** of questions, each with a `name`.
3. **Options:** Microsoft-Decision-1.1 uses `criteria` (an object for choice, a list for score); the
   Decisions API uses `choices` and `levels`.

Photos differ too: Microsoft-Decision-1.1 receives the photo as a base64 **asset** that the evidence
refers to (`"photo": "image:photo.jpg"`), while the Decisions API receives it as an `input_image`
part of the input message.

## Learn more

- [Deploy and use Microsoft-Decision-1.1](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [Use the Azure OpenAI Decisions API](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
