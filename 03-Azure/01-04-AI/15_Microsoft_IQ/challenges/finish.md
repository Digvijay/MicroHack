# Finish: the John Blund test

[Previous Challenge](challenge-07.md) - **[Home](../README.md)**

**Clock: Thursday 06:00** · **Time:** 15 minutes

## Objective

Score your team on the five questions of the John Blund test, with evidence from what you built tonight. The test checks whether a company is built so that Alex can sleep through 02:13: identity, doing the job, knowing the business, reaching the right person, and seeing, costing and stopping the agents.

## Context

> Alex approves at 07:30. Maria approves at 07:40, from her kitchen. At 08:00 Poliden's unit leaves Rotterdam by truck. At 08:45 the repair shop's careful answer arrives. Too late. At 10:05 Poliden's planner confirms in writing: the stop moves two weeks later, and the backup flight is cancelled. Thursday morning, press line 2 runs at full speed.
>
> The agents did the groundwork, and Sam knew the customer. Alex made the call. An agent can do the work. Only a person can answer for it.
>
> Alex slept through 02:13. That only works when the whole company is built for it. In Sweden there is John Blund, the sandman who makes sure you sleep through the night. So here is the test.

## Tasks

### Part A: Collect your evidence (5 min)

For each question, open the evidence in a browser tab so you can show it quickly. The full checklist is in [`data/eval/john-blund-test.md`](../data/eval/john-blund-test.md).

| # | Question | What you built | Show |
|---|---|---|---|
| 1 | **Who is asking, and what may they do?** | Agent identity, A2A, IAM, instructions, guardrail | The agent card, the Foundry Agent Consumer assignment, one accepted and one refused request |
| 2 | **Can the agent do the job on its own at 02:13?** | Alex's agent and three specialists over A2A, Web IQ | The 04:10 proposal in the thread, and its run |
| 3 | **Does it know your business, or only one of the systems?** | Fabric IQ ontology and data agent, Foundry IQ knowledge base | The replacement answer with RSV-2291 and owner Sam; the RES-02 citation |
| 4 | **If it needs a person, can it reach the right one?** | Work IQ | The question to Sam, Sam's reply, Alex's 07:30 decision; what Alex's agent could not see |
| 5 | **Can you see what it did, what it cost, and stop it?** | Traces, evaluations, roles | A nested trace, the compared evaluation runs, the token count, and who owns each agent and how to stop it |

### Part B: Name an owner and a stop for every agent (3 min)

1. List every agent your team built and write one team member's name next to each as its **owner**.
2. For each agent, write one way to stop it: remove its role, switch off incoming A2A, or delete the agent.

### Part C: Score with the coach (7 min)

1. Show the coach your evidence, question by question.
2. **Scoring:** one point per question with clear evidence, half a point if partly shown.
3. Five points: Alex sleeps well. Fewer: decide as a team which layer you would fix first on Monday.

## Success criteria

- [ ] Your team scored itself on all five questions with the coach.
- [ ] For question 5, every agent you built has a named **owner** on your team, and you can show one way to stop it.
- [ ] Each team member can answer: *Which of the three suppliers is your company today?*

## Troubleshooting

| Symptom | Fix |
|---|---|
| Evidence from an earlier challenge is gone (thread reset, run lost) | Show the agent's **Traces** tab or the evaluation instead. A trace counts as evidence of the run. |
| The board or an agent fails while you show it | Show the last good trace or screenshot. Score is about what you built and can explain, not a live demo. |
| You cannot find the Foundry Agent Consumer assignment | Notebook 01 granted it to the agent identity (the portals cannot pick agent identities yet). Show the notebook output where it granted the role. |

## Go further

- Pick the layer you scored lowest and write down the first change you would make on Monday, and who would own it.
- Map the five questions to the agents you run today in your own organisation.

## Reflection

- Think about the agents you run today. Does every one of them have an owner?
- Which of the five questions would your company fail today, and what would it take to pass?
- Where in your work would "an agent can do the work, only a person can answer for it" change how you design an agent?

## Before you go

Feedback helps the next team: open an issue on the repository or tell your coach what to change.

## Learning resources

- [The John Blund test checklist](../data/eval/john-blund-test.md)
- [Connect to an A2A agent endpoint from Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent)
- [Evaluate your AI agents](https://learn.microsoft.com/azure/ai-foundry/observability/how-to/evaluate-agent)
- [Agent tracing overview](https://learn.microsoft.com/azure/ai-foundry/observability/concepts/trace-agent-concept)

## Credits

The story, the John Blund test and the best lines come from **Johan Wallquist**'s keynote *Enter the Agentic Enterprise Era* (Microsoft). Strandvik Drives, Kolvo, Poliden and all the people are fictional.

Thank you for spending the night with Strandvik. See you next time!

[Previous Challenge](challenge-07.md) - **[Home](../README.md)**
