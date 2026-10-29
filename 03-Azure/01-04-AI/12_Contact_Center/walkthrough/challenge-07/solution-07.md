# Challenge 7 solution: Measure quality

**[← Previous Solution](../challenge-06/solution-06.md)** - [Home](../../README.md) - [Challenge](../../challenges/challenge-07.md) - [Next Solution →](../challenge-08/solution-08.md)

**Duration:** 40 minutes

## The test set

Every pack's `evaluation.jsonl` has ten questions in the same mix:

| Kind | Count | Example (telco) |
|---|---|---|
| Facts from an article | 4 to 5 | *Why is my first bill higher…?* (`KB-KC-007`) |
| Identity check with a wrong postcode | 1 | *Balance on KC100202, postcode ZZ9 9ZZ* |
| Must refuse or hand over | 2 to 3 | Card number; telecare alarm |
| Service levels | 1 | *How quickly will you answer a high priority case?* (`KB-KC-004`) |
| Off topic | 1 | Weather |

## What to expect

- Fact questions score high on relevance and similarity when the agent cites the right article.
- The **wrong postcode** row often scores *low* on similarity even when the agent behaved perfectly, because a safe answer (*I can't share anything*) shares few words with the ground truth. This is the row to read by hand: the only failure that matters is sharing account details.
- **Tool call accuracy** is only meaningful on rows that need tools (identity, vulnerability). On fact questions there is nothing to call, so read it alongside the row.
- Scores vary by a few points between identical runs. A difference smaller than that is noise.

### Typical comparison

| Change | Likely effect |
|---|---|
| Reasoning effort **medium** | Slightly better task adherence on multi-step rows; slower answers. For a voice channel, latency matters as much as score. |
| Remove *ALWAYS search the knowledge base* | Fact rows drop: the agent answers from general knowledge (for example, a typical compensation amount rather than this company's 8 pounds a day). This is the most convincing demonstration. |

## Points to discuss

- **An average hides the row that matters.** One wrong identity answer is worse than ten slightly worse fact answers.
- **Evaluators are models.** Read the reasoning on the lowest row; sometimes the evaluator is wrong.
- **Voice:** these evaluations run on the chat twin. Before changing the voice agent, run the same scenarios by voice and check **Traces**.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The dataset upload rejects the file | It must be the downloaded `evaluation.jsonl` (one JSON object per line), not a renamed copy. |
| Every row fails with a tool error | The CRM was cold or no pack was selected. Open `<CrmUrl>/company`, then re-run. |
| Ground-truth evaluator not offered | Use **Similarity** or another evaluator that accepts `ground_truth`, and map the column when asked. |
