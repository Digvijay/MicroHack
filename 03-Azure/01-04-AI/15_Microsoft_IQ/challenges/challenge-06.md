# Challenge 6: One agent, four IQs

**[Home](../README.md)** - [Previous Challenge](challenge-05.md) - [Next Challenge](finish.md)

**Time:** 60 minutes. **IQ:** Microsoft IQ (all four).

## Story beat

10:55. Five minutes before the escalation call. The Plant Manager asks the question from this morning again: "Can we ship Brennmark's order by Friday, and what should we tell them?" This time your agent has the web, the business data, the rulebook and the people. Having all the context is not the same as using it well. Your last job is to make the agent decide like a good planner, and to prove it with an evaluation.

## What you learn

- How one agent combines four IQs in one answer, and where it still goes wrong.
- Why a short **playbook** (which IQ for what, in which order) beats more tools.
- How to evaluate multi-turn conversations, and why you run an evaluation twice.
- How the **Agent Optimizer** proposes better instructions from your evaluation.

## Feature status

| Feature | Status |
|---|---|
| Foundry prompt agents | GA |
| Multi-turn evaluation | GA |
| Agent Optimizer (Optimize tab) | GA |
| Insights | GA |
| Web search, Fabric IQ tool, Foundry IQ, Work IQ | As in Challenges 2 to 5 |
| Foundry toolbox (stretch) | GA |

## What goes wrong with four IQs (read first, 5 min)

Having all four IQs is not the same as using them well.

> [!IMPORTANT]
> **Teaching moment: four IQs are not enough.** In testing, the agent with all four IQs but no playbook scored about **125 of 190**, lower than with three IQs. It failed in ways that look a lot like a rushed human:
>
> - It **picked one tool** and stopped, instead of checking data, documents, people and the web.
> - It **trusted the lakehouse ETA** (8 December) over the newer partner email (q16).
> - It **offered the customer's 2,000** instead of the **1,800** Caldova can actually deliver.
> - Asked cold to draft the customer message, it **copied last week's broken promise** of 4,000 by Friday. The judge scored it 0.

A decision-grade answer contains:

- What we can deliver by Friday 11 December, and the numbers behind it.
- When the rest can follow, and why.
- Whether the backup supplier is an option, and why not.
- What the contract requires: notice, deadline, written agreement.
- The message to the customer, which corrects the earlier promise and keeps internal details internal.

The fix is a **playbook**. Instructions say **what** the agent is. A playbook says **how** it works: which IQ to use for what, and in which order. Write it yourself from the failures you see, with this structure:

```markdown
# Caldova playbook

## Pick the right IQ
- Quantities and money: ...
- Rules and contracts: ...
- What people said, promised, decided, and partner news: ...
- Public facts: ...

## For a delivery decision, always do all four steps
1. ...
2. ...
3. ...
4. ...

## Customer messages
- ...

## If a source is missing
- ...
```

Hints:

- Which source is **newest** when the lakehouse and an email disagree? Tell the agent to check both for any status, delay or arrival date.
- Is "we could accept 2,000" an offer to accept, or a ceiling?
- What must happen **before** the agent drafts any customer message?
- What must never appear in a message to a customer?
- What does the contract say about notice when an authority closes a port?

## Business path (portal, no code)

1. In the Foundry portal, open `caldova-portal` and change the key of the Work IQ tool to **WorkIQKeyPlantManager**. The Plant Manager is the decision maker and can see everything the right answer needs.
2. Ask in the playground:

   ```text
   Can we ship Brennmark's order by Friday, and what should we tell them?
   ```

   Then, in the **same conversation**: `Now draft the message to Brennmark's Purchasing Manager.`
3. Open the run details and check which tools the agent called. Did it use all four IQs?
4. Write your playbook at the end of the agent's instructions. Save. This creates a new agent version.
5. Open **Evaluate** and create an evaluation with a few questions from [`data/eval/questions.json`](../data/eval/questions.json): use `question` as the query and `gold` as the ground truth. Include q16, q17 and q18, and add q18 and q19 as one **multi-turn** conversation. Compare the version before and after the playbook.
6. Open the **Optimize** tab and start the **Agent Optimizer** with the same dataset. It runs your agent, scores it and proposes better instructions. Compare its proposal with your playbook and keep what is better.

> [!WARNING]
> Optimizer and evaluation runs **execute the agent's tools**. Use only read-only tools. All four IQ tools in this hack are read only (Work IQ write tools are blocked by policy).

## Developer path (Codespace)

1. Ask the capstone as the Plant Manager:

   ```bash
   caldova ask "Can we ship Brennmark's order by Friday, and what should we tell them?" --iqs web,fabric,foundry,work --persona plant-manager
   ```

   Look at `Tools used`. Did it use all four IQs?

2. Run the evaluation without a playbook and read the failures:

   ```bash
   caldova eval --iqs web,fabric,foundry,work --label "challenge 6: four IQs, no playbook"
   ```

   Look at q16, q18 and q19. Open `src/.caldova/leaderboard.json` to read the full answers.

3. Create `src/playbook.md` with your rules. Find `PLAYBOOK` in [`src/caldova/agent.py`](../src/caldova/agent.py): when the file exists and is not empty, `instructions()` appends it under "Team playbook (follow it)". The file is read when the agent is built, so every `caldova ask --iqs ...` and `caldova eval` picks up your latest version.
4. Retest only the hard questions while you iterate:

   ```bash
   caldova eval --iqs web,fabric,foundry,work --only q16,q18,q19 --label "retest"
   ```

> [!NOTE]
> **Multi-turn.** q19 ("Now draft the message...") follows q18 in the **same conversation**, because in real life you draft the message after you decide. The evaluation runs q18 first and passes its response id as `previous_response_id`. Read `run()` in [`src/caldova/evals.py`](../src/caldova/evals.py).

## Evaluate (both paths)

```bash
caldova eval --iqs web,fabric,foundry,work --label "challenge 6: with playbook"
caldova leaderboard
```

With a good playbook, the reference solution reached about **150 of 190** (148 and 154 in two runs).

> [!TIP]
> **Variance.** The agent, the data agent and the judge are all language models. The same question can score 3 on one run and 10 on the next. Run the evaluation **twice** before you decide a change helped.

## Success criteria

- [ ] Your agent answered the capstone as the Plant Manager and used several IQs.
- [ ] You found at least two failures in the evaluation and explained their cause.
- [ ] You wrote a playbook, and the score went up across two runs.
- [ ] Your draft message offers what Caldova can deliver, gives force majeure notice in time, asks for written agreement, and says nothing about suppliers or quality.
- [ ] (Business path) You ran a portal evaluation and an Agent Optimizer run.

## Stretch

- **Toolbox.** Publish the IQ tools as a Foundry **toolbox**: one managed MCP endpoint you can reuse in GitHub Copilot or other agents. This is the "business plugins" idea from Ignite 2026: package context once, use it everywhere. Note: web search added through a toolbox uses Grounding with Bing Search, not Web IQ.
- **Real Work IQ.** In a tenant with Microsoft 365 Copilot, set `WORKIQ_ENDPOINT=https://workiq.svc.cloud.microsoft/mcp` and replace the key connection with a Microsoft Entra user connection. Nothing else in your agent changes.
- **Insights.** Open your agent's traces in the Foundry portal and find a run where the agent skipped a tool.

## Value card

| What this IQ is | What it fixed today | Where customers use it |
|---|---|---|
| **Microsoft IQ**: Web IQ, Fabric IQ, Foundry IQ and Work IQ together, with the permissions of the person asking. | A grounded decision: 1,800 by Friday, the rest later, the right notice on time, no false promise, and a customer message ready to send. | Any decision that needs numbers, rules, people and the outside world at once: supply disruptions, deal desks, incident response, customer escalations. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| The playbook seems ignored | Check the file is `src/playbook.md` (not empty). It is read when the agent is built: run `caldova ask ... --iqs ...` or `caldova eval`, which rebuild the agent. |
| The agent uses only one tool | Make the playbook say "always do all four steps" for delivery decisions, and name the tools. |
| q17 fails after the playbook | q17 runs as the Sales Lead. A rule like "always give a date" makes it leak or guess. Keep "if a source is missing, say so". |
| Scores jump between runs | Expected. Compare two runs, use `--only` for the hard questions. |
| The optimizer run fails | Check the dataset has a query and a ground truth for each row, and the agent version is saved. |

## Learning resources

- [Agent optimizer in Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-optimizer-overview)
- [Create and manage a toolbox in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/toolbox)
- [Work IQ overview](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/)
- [Microsoft IQ documentation](https://learn.microsoft.com/en-us/microsoft-iq/)

---

**[Home](../README.md)** - [Previous Challenge](challenge-05.md) - [Next Challenge](finish.md)
