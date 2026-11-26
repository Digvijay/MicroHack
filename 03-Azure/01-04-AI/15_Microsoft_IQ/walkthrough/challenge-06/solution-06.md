# Walkthrough Challenge 6: One agent, four IQs

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-05/solution-05.md)

**[Back to Challenge 6](../../challenges/challenge-06.md)**

Duration: 60 minutes

## Expected end state

- `src/playbook.md` (developer path) or the same text at the end of the portal agent's instructions (business path).
- Two leaderboard runs with all four IQs: one without and one with the playbook, ideally each run twice.
- Business path: a portal evaluation with a multi-turn q18 and q19 conversation, and one Agent Optimizer run.

## Command sequence (developer path)

```bash
caldova ask "Can we ship Brennmark's order by Friday, and what should we tell them?" --iqs web,fabric,foundry,work --persona plant-manager
caldova eval --iqs web,fabric,foundry,work --label "challenge 6: four IQs, no playbook"
# team writes src/playbook.md
caldova eval --iqs web,fabric,foundry,work --only q16,q18,q19 --label "retest"
caldova eval --iqs web,fabric,foundry,work --label "challenge 6: with playbook"
caldova eval --iqs web,fabric,foundry,work --label "challenge 6: with playbook, run 2"
caldova leaderboard
```

The reference playbook is [playbook.md](playbook.md). To give a stuck team the reference: `cp walkthrough/challenge-06/playbook.md src/playbook.md`. Do not hand it out before teams have seen their own failures: the learning is in mapping each rule to a failure.

## The right answer (q18, Plant Manager)

1. **Not the full order.** 600 finished + 1,200 built from HX-220 stock = **1,800 PV-400** by Friday 11 December. Capacity (400 a day, 600 with overtime) is not the limit; HX-220 is.
2. **No backup supplier.** Teglbruk Metall AS is on quality hold (QR-2026-118); SQP-04 allows no deviation for pressure-bearing parts; HX-220 is pressure-bearing.
3. **Allocation.** Brennmark is strategic, so the 1,200 HX-220 go to PV-400 for Brennmark (AP-02, and the Plant Manager's decision in M6). Solvik's CV-90 order (800, due 18 December, no partials) then depends on PO-7781 arriving about 16 December: at risk, still feasible.
4. **Tell Brennmark:** force majeure notice **within 48 hours**, so by **Wednesday 9 December 08:00**; offer **1,800 by Friday 11 December** and the remaining **2,200 by 18 December** (close to the 2,000 they said they could accept); get **written agreement** to the partial delivery (FA-2024-007); correct the promise of a full shipment made on 3 December.
5. **Money:** orders depending on Nordhavn's HX-220 are worth **1,975,000 EUR**; delayed value on Brennmark **2,200 x 410 = 902,000 EUR**; without force majeure the penalty would be 2% per week of 902,000 = **18,040 EUR per week** (capped at 10%).

**q19** (same conversation): a short customer message with the same offer, force majeure notice, request for written confirmation, and **no** mention of Teglbruk, the quality hold or lot L-7731 (any of those fails the gate).

## Why each playbook rule exists

Observed with all four IQs and no playbook: about **125 of 190** (lower than the 143 with three IQs). With the reference playbook: about **150 of 190** (148 and 154 in two runs). Each rule answers one observed failure:

| Playbook rule | Observed failure it fixes | Questions |
|---|---|---|
| Pick the right IQ: quantities in Fabric IQ, rules in Foundry IQ, people and partner news in Work IQ, public facts in Web IQ | The agent picked one tool, usually the first that seemed relevant, and stopped | q18 |
| "Emails and chats are newer than the lakehouse. For any status, delay or arrival date, ALWAYS call workiq.retrieve as well as Fabric IQ, and prefer the newest dated source" | It trusted the lakehouse ETA (8 December) over the partner email (14 and 16 December) | q16, q18 |
| "For a delivery decision, always do all four steps" (Work IQ, Fabric IQ, Foundry IQ, Web IQ) | Answers missed the contract (no force majeure, no written agreement) or the quality hold | q18 |
| "Offer only what Fabric IQ shows we can actually deliver. A customer's 'we could accept' is a ceiling, not our offer" | It offered Brennmark's 2,000 instead of the 1,800 Caldova can deliver | q18, q19 |
| "If the delay comes from an event outside our control, check the force majeure clause and its notice deadline, and say when the notice must be sent" | The 48-hour notice and its deadline were missing | q18, q19 |
| "Before you draft any message to a customer, first run the four delivery-decision steps. Never copy an earlier promise without checking it still holds" | Asked cold to draft the message, it copied M1: 4,000 by Friday. Judge score 0 | q19 |
| "Do not share internal details such as supplier names, quality holds or lot numbers with customers" | Drafts mentioned Teglbruk or the hold, which fails the q19 gate | q19 |
| "If an earlier promise cannot be kept, say so clearly", "Ask for written agreement when the contract requires it" | Drafts were vague about the change and forgot the written confirmation | q19 |
| "If a source is missing, say which source you could not see. Never fill the gap with a guess" | Protects q17 (Sales Lead) from a playbook that pushes for dates | q17 |

Note the playbook is appended for **every** persona, so rules must not break q17. A rule like "always give an arrival date" makes the Sales Lead agent guess.

## Multi-turn evaluation

q19 has `"follows": "q18"`. `evals.run()` asks q18 first, takes its `response_id`, and asks q19 with `previous_response_id`, so the draft is written after the decision, in the same conversation. In the portal, the Evaluate tab supports multi-turn conversations (GA): add q18 and q19 as one conversation.

## Variance

The agent, the Fabric data agent and the judge are all language models. In testing, multi-turn retests of q18 and q19 ranged from about 10 to 15 of 20 on identical configurations, and q09 can swing between 3 and 10. Ask teams to run twice and compare averages. Use `--only` to retest the hard questions cheaply.

## Business path notes

- Agent Optimizer: start from the agent's **Optimize** tab. Prompt agents can have instructions, function-tool descriptions and model choice optimized. Review the cost estimate before submitting.
- Optimizer and evaluation runs **execute tools**. All four IQ tools here are read only, and Work IQ write tools are blocked by policy, so it is safe. Make the point that this is not true for every agent.
- Compare the optimizer's proposal with the team's playbook. Discuss which rules the optimizer found from the scores, and which needed business knowledge (for example "a customer's offer is a ceiling").

## Stretch notes

- **Toolbox.** A Foundry toolbox publishes tools behind one managed MCP endpoint that other agents and GitHub Copilot can reuse, with central credentials, versioning and policy. Business plugins from Ignite 2026 package this idea for business users. Caveat: web search added to a toolbox uses Grounding with Bing Search, not Web IQ.
- **Real Work IQ swap.** Set `WORKIQ_ENDPOINT=https://workiq.svc.cloud.microsoft/mcp` and replace the `CustomKeys` connection with a Microsoft Entra user connection (delegated, needs Microsoft 365 Copilot and admin consent). `agent.py` does not change. That is the point of the emulator having the same contract.

## Common issues

| Symptom | Cause and fix |
|---|---|
| Playbook has no effect | File not at `src/playbook.md`, empty, or the agent was not rebuilt. `ask --iqs ...` and `eval` rebuild it. |
| Score drops after the playbook | Often q17 (rule forces a date) or q19 (rule too long, model loses the customer message focus). Shorten, test with `--only`. |
| q19 scores 0 | Gate phrase present: "4,000 by Friday", "Teglbruk", "quality hold" or "L-7731". Read the answer in `src/.caldova/leaderboard.json`. |
| Capstone takes long | Several tools in sequence, plus the data agent's own SQL step. Expected. |
| Optimizer run fails | Dataset rows need a query and a ground truth; the agent version must be saved. |

## Discussion prompts

- Which rules in your playbook are about **tools**, and which are about **business judgement**?
- Who in your company would own the playbook and the evaluation set?
- What would you add to the evaluation before letting this agent draft real customer messages?

---

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-05/solution-05.md)
