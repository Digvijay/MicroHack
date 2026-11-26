# Evaluation rubric (coach guide)

This rubric explains how the leaderboard scores the Caldova agent with `questions.json`. The set has 19 questions. Each challenge adds one Microsoft IQ, so the score shows how the agent improves as it gets more context. All data is fictional. The single source of truth for every answer is `walkthrough/scenario-facts.md`.

## How a question is scored

Each question gets a score from 0 to 10. A run's score is the sum over all questions (maximum 190).

| Part | Points | How it works |
|---|---|---|
| Deterministic: must include | 0 to 4 | `must_include` is a list of groups. Each group is a list of alternatives. A group passes if the answer contains at least one alternative (case-insensitive substring). Points = 4 x (groups passed / total groups). |
| Deterministic: must not include | gate | If the answer contains any phrase in `must_not_include` (case-insensitive), the deterministic part scores 0 and the judge score is capped at 1. These phrases signal a dangerous or wrong answer, for example confirming 4,000 by Friday, or using Teglbruk Metall AS as a solution. |
| LLM judge | 0 to 5 | A judge model compares the answer with `gold` and scores 0 to 5 (see scale below). The judge sees the question, the persona and the gold answer. |
| Grounding | 0 or 1 | 1 point if the agent called at least one IQ the question needs (see `iqs`). For `web_citation_required` questions the answer must also contain a URL. Questions that need no IQ get this point automatically. |

### Judge scale

| Score | Meaning |
|---|---|
| 5 | Correct and complete. All key facts and numbers in the gold answer are present. No wrong claims. |
| 4 | Correct, with one minor fact missing. |
| 3 | Mostly correct, but a key fact or number is missing or vague. |
| 2 | Partly correct, with an important error or a missing reason. |
| 1 | Mostly wrong, or a confident answer with no grounding. |
| 0 | Wrong, harmful or no answer. |

The judge also follows two rules: an answer that only says it does not have the information scores at most 1, and for the persona trimming question (q17) "I don't know" without searching Work IQ scores at most 2. This keeps a blind agent from scoring well by refusing.

### Special cases

- **Web IQ questions (q03 to q05).** The web is live, so the gold text describes what a good answer contains, not a fixed value. The judge checks recency and citation. Deterministic checks only use stable words such as "Esbjerg" or "SEK".
- **Persona trimming (q17, `expect_no_access: true`).** The question is asked as `sales-lead`, who cannot see the port closure email (M4) or the quality hold chat (M3). The correct behaviour is to say it cannot find the information and to suggest asking the Supply Planner. Any mention of 16 December fails the gate, because that date is only visible to the Supply Planner. Score the honesty, not the date.
- **Capstone (q18, q19).** These need all four IQs and are asked as `plant-manager`, the decision-maker, who can see M1 (copied), M2, M3, M5 (forwarded), M6, M7 and M8. q19 is a **multi-turn** question: it follows q18 in the same conversation ("Now draft the message..."), because in real life you draft the message after you decide. Give full judge marks only if the answer: offers 1,800 by Friday 11 December and the remaining 2,200 by 18 December; sends force majeure notice within 48 hours (by Wednesday 9 December 08:00); asks for written agreement to the partial delivery; does not confirm 4,000 by Friday; and does not offer Teglbruk Metall AS as a fix. For q19 the message is customer-facing, so any mention of Teglbruk, the quality hold or lot L-7731 fails the gate.
- **Variance.** The agent, the Fabric data agent and the judge are all language models, so the same question can score differently on two runs (for example q09 can swing between 3 and 10). Compare runs, not single answers, and run the evaluation twice before drawing conclusions.

## Questions and required IQs

| id | Challenge | Persona | IQs required | Tests | Key answer |
|---|---|---|---|---|---|
| q01 | 1 Baseline | supply-planner | none | General knowledge | Force majeure excuses events beyond a party's control |
| q02 | 1 Baseline | supply-planner | none | General knowledge | BOM lists components and quantities |
| q03 | 2 Web IQ | supply-planner | Web | Live weather, cited | Esbjerg weather and warnings, with source |
| q04 | 2 Web IQ | supply-planner | Web | Live FX rate, cited | Current EUR/SEK with date and source |
| q05 | 2 Web IQ | supply-planner | Web | Holidays, cited | 25 and 26 December in both countries |
| q06 | 3 Fabric IQ | supply-planner | Fabric | Stock lookup | 1,200 HX-220 in Borås |
| q07 | 3 Fabric IQ | supply-planner | Fabric | Graph join: supplier to component to product to order | Brennmark, Solvik, Østerdal: 1,975,000 EUR |
| q08 | 3 Fabric IQ | supply-planner | Fabric | Buildable quantity | 600 + 1,200 = 1,800 PV-400 |
| q09 | 3 Fabric IQ | supply-planner | Fabric | Delayed value | 2,200 x 410 = 902,000 EUR |
| q10 | 4 Foundry IQ | supply-planner | Foundry | Contract clause | Port closure is force majeure, notice within 48 hours |
| q11 | 4 Foundry IQ | supply-planner | Foundry | Compare contracts | Brennmark partials in writing; Solvik no partials |
| q12 | 4 Foundry IQ | supply-planner | Foundry | Multi-document reasoning | No: quality hold, SQP-04, HX-220 pressure-bearing |
| q13 | 4 Foundry IQ | supply-planner | Foundry | Policy lookup | AP-02: strategic, key, standard, due date; Plant Manager override |
| q14 | 5 Work IQ | sales-lead | Work | Email (M1) | Promised the full 4,000 PV-400 by Friday 11 Dec |
| q15 | 5 Work IQ | plant-manager | Work | Forwarded email (M5) | Would accept 2,000 by Friday if the rest arrives by 18 Dec, in writing |
| q16 | 5 Work IQ | supply-planner | Work | Email (M4) beats stale meeting (M2) | Departs 14 Dec, arrives about 16 Dec |
| q17 | 5 Work IQ | sales-lead | Work | Persona trimming | Cannot find it; must not say 16 December |
| q18 | 6 All together | plant-manager | Web, Fabric, Foundry, Work | Full decision | 1,800 Friday, 2,200 by 18 Dec, force majeure in 48 h, written agreement |
| q19 | 6 All together | plant-manager | Web, Fabric, Foundry, Work | Customer message | Same offer, force majeure notice, no internal quality details |

## Expected progression

| Agent configuration | Questions it should pass |
|---|---|
| Model only | q01, q02 |
| + Web IQ | q03 to q05 |
| + Fabric IQ | q06 to q09 |
| + Foundry IQ | q10 to q13 |
| + Work IQ | q14 to q17 |
| All four | q18, q19 |

A good team reaches about 150 out of 190 by the end of challenge 6. The reference runs scored 63, 69, 109, 143, 123 and 148 to 154 for challenges 1 to 6 (see walkthrough/README.md). Note the drop at challenge 5: more tools without guidance make the agent worse, until the playbook in challenge 6. Low scores on q18 and q19 usually mean the agent did not combine the sources, or it used the wrong persona.
