# Finish: the John Blund test (coach guide)

[Previous Solution](../challenge-07/solution-07.md) - **[Back to Finish](../../challenges/finish.md)** - **[Home](../../README.md)**

**Clock: Thursday 06:00** · **Duration:** 15 minutes

## Goal

Each team scores itself on the five John Blund questions with evidence, names an owner and a stop for every agent, and leaves with the keynote's closing lines.

## Solution notes

### How to run it

1. Set the story clock to **Thursday 06:00**. Read the beat from the finish page: 07:40 Maria approves, 08:00 the truck leaves, 08:45 Hallberg answers, 10:05 Poliden confirms the stop moves two weeks later, Thursday press line 2 at full speed.
2. Give teams Parts A and B (about 8 minutes) to open their evidence and name owners.
3. Go team by team for Part C (3 minutes each, or in parallel with several coaches). The team shows evidence; you score.
4. Close with the keynote's last lines (below).

### Scoring sheet

One point per question with clear evidence, half a point if partly shown.

| # | Question | Full point when the team shows | Half point |
|---|---|---|---|
| 1 | Who is asking, and what may they do? | The agent card of `strandvik-customer-service`; IAM on the strandvik project with `maria-procurement` as Foundry Agent Consumer; a trace or board answer where Maria gets a case and a handover; a refusal of an order or of an unknown agent; the guardrail and why | Only one of the two locks (IAM or instructions) |
| 2 | Can the agent do the job on its own at 02:13? | `alex-agent` calling parts, logistics and service over A2A; the 04:10 proposal in the thread with unit, Wednesday 09:00, Wednesday night technician, Pune backup held until 11:00, Poliden covered, "Final confirmation from Alex by 07:30" | Proposal with gaps, or only two specialists |
| 3 | Does it know the business, or only one system? | The ontology (or paper fallback) with Reservation owned by Person; the data agent's replacement answer with RSV-2291 and owner Sam; the Service agent citing RES-02, SC-KOL-2024 and FS-04 | Data or documents, not both |
| 4 | If it needs a person, can it reach the right one? | The agent's question to Sam, Sam's reply, the agent reading it; Alex's 07:30 decision posted as Alex; the team explains why Alex's agent could not see the planner's email | Asked Sam but never read the reply, or no human decision |
| 5 | Can you see what it did, what it cost, and stop it? | A nested trace across agents; two compared evaluation runs including the custom rubric; a token count for the night; a named owner per agent and one way to stop each | Traces or evaluation, not both; owners not named |

Five points: Alex sleeps well. Fewer: ask "Which layer would you fix first on Monday?" and let the team answer.

### Closing (read aloud)

From Johan Wallquist's keynote:

> Alex slept through 02:13. That only works when the whole company is built for it.
>
> The agents did the groundwork, and Sam knew the customer. Alex made the call. An agent can do the work. Only a person can answer for it.

Then map the five questions to what the teams built, and to the wider Microsoft platform the keynote names:

| Question | Built today | In the keynote's Microsoft terms |
|---|---|---|
| Who's asking | Agent identity, A2A, IAM, guardrails | Entra Agent ID, Agent 365, Purview |
| Doing the job | Foundry Agent Service, A2A, Web IQ | Foundry |
| Knowing the business | Fabric IQ ontology and data agent, Foundry IQ | Fabric IQ with the ontology, Foundry IQ for the documents |
| Reaching the right person | Work IQ (emulator), the thread | Work IQ, in Copilot and Teams |
| Seeing, costing, stopping | Traces, evaluations, token counts, roles | Agent 365, Purview Audit, Defender, Foundry governance |

Last question to the room, no hands needed: "Think about the agents you run today. Does every one of them have an owner?"

## Expected results

Expected answers to the "stop it" question (Part B):

| Way to stop | Effect |
|---|---|
| Remove `maria-procurement`'s **Foundry Agent Consumer** role on the strandvik project | Kolvo's agent can no longer call Strandvik (and Maria's whole run fails, as in challenge 2) |
| Switch off incoming A2A (PATCH the agent without `a2a` in `protocol_configuration`) | Nobody can call that agent over A2A |
| Remove an A2A tool from `alex-agent` | Alex's agent stops using that specialist |
| Delete the agent | Its agent identity is removed with it |
| Remove the Work IQ tool or rotate the emulator key | Alex's agent loses access to Alex's Microsoft 365 world |

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Team cannot show the 04:10 proposal | The thread was reset after challenge 6 or 7 | Accept the run's trace as evidence |
| Team shows the IAM role but not the refusal | Only one lock tested | Half point; ask them to send the order request on the board or in the playground |
| No owner per agent | The team never discussed ownership | Give them a minute in Part B; no full point on question 5 without names |
| Scoring takes too long | Too many teams for one coach | Score in parallel with several coaches, or let teams self-score with the sheet and spot-check one question |

## Checks for the coach

- [ ] Every team scored on all five questions.
- [ ] Every team named an owner and one stop per agent.
- [ ] Closing lines read and the "owner" question asked.
- [ ] Feedback collected (an issue on the repository, or a short form).
- [ ] Fabric capacities paused if labs stay up overnight (Azure portal > `iqcap<hash>` > **Pause**). The platform deletes the lab resource groups when the event ends.

[Previous Solution](../challenge-07/solution-07.md) - **[Back to Finish](../../challenges/finish.md)** - **[Home](../../README.md)**
