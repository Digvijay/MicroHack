# Challenge 6 solution: Post-contact analytics and supervisor insights

**[← Previous Solution](../challenge-05/solution-05.md)** - [Home](../../README.md) - [Challenge](../../challenges/challenge-06.md) - [Next Solution →](../challenge-07/solution-07.md)

**Duration:** 50 minutes

## Part A and B: Content Understanding

`contactCallAnalyzer` is a custom analyzer for audio using the lab's `gpt-5.4-mini`. Our results on the telco calls:

| Call | sentiment | intent | identity_checked | resolved | escalated | vulnerability_signs | empathy_score |
|---|---|---|---|---|---|---|---|
| `KC-CALL-01` First bill higher | positive | bill query | true | true | false | none | 4 |
| `KC-CALL-02` Broadband down three days | negative | broadband outage | true | true *or* false | true | *works from home* | 4 |
| `KC-CALL-03` Telecare alarm | neutral | internet outage | true | true *or* false | true | alarm pendant relies on the internet; sounded worried | 4 |

The transcript separates the two voices as **Speaker 1** (adviser) and **Speaker 2** (customer), with timestamps. Calls are about 60 to 80 seconds and take under a minute to analyse.

Things to point out:

- **`resolved` changed between runs** for calls 02 and 03. Is a call *resolved* when the outage is still on but the customer got what they needed? The field description doesn't say, so the model guesses. Fix it by tightening the description, for example *True only if nothing is left for the company to do*.
- **`vulnerability_signs` over-flagged call 02:** working from home is an impact, not a vulnerability. Again the description is the fix: list the kinds of vulnerability from article 002.
- **`empathy_score` is the field to trust least.** It's a judgement, and the same score for every call is a sign the model isn't discriminating. Use it to pick calls for a person to review, not to rate advisers.

The same pattern works for every industry: CALL-01 is a routine request, CALL-02 a frustrated customer affected by the week's trend, CALL-03 a vulnerable customer.

## Part C and D: supervisor insights

| Industry | Trend the supervisor should find | Missed identity checks |
|---|---|---|
| telco | `outage_fault`: 12 contacts, all in **ZZ4**, 3 to 6 March | `KC-C1008`, `KC-C1023` |
| energy | `billing_query`: 11 contacts, all in **ZZ2**, 2 to 6 March | `LE-C1005`, `LE-C1020` |
| bank | `scam_report`: 12 contacts across all areas, 3 to 7 March (the parcel-fee text scam) | `HB-C1012`, `HB-C1027` |
| insurance | `storm_damage`: 10 contacts, all in **ZZ3**, 2 to 5 March | `NI-C1010`, `NI-C1025` |
| retail | `late_delivery`: 11 contacts, all in **ZZ5**, 3 to 7 March | `PP-C1007`, `PP-C1022` |

In our telco run `supervisor-insights` listed the reasons with counts (outage/fault 12, moving home 7, billing and payment 6, engineer appointments 3, complaints 2). It identified the ZZ4 spike from 3 to 6 March and named `KC-C1008` and `KC-C1023`. Its recommended actions were tied to that evidence: review the ZZ4 outage communications and coach verification.

Ask groups to connect the dots: the trend in the supervisor's week matches the service notice the voice agent found in Challenge 3, and the call they analysed in Part A.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Analysis fails with an internal error | The participant chose the ready-made **call center** analyzer. It needs `gpt-4.1-mini`, which this lab doesn't deploy. Build the custom analyzer as the challenge describes. |
| *The analyzerId cannot contain '-'* | Use `contactCallAnalyzer`, not `contact-call-analyzer`. |
| Content Understanding asks for default models every time | Set the defaults once: completion `gpt-5.4-mini`, embedding `text-embedding-3-large`. |
| The supervisor answers about knowledge articles | It was given `contact-knowledge-kb` instead of `contact-insights-kb`. |
| The supervisor finds only one missed check | Retrieval returned part of the digest. Ask the question on its own (*Which contacts scored 1 for verification?*); it usually finds both. |
