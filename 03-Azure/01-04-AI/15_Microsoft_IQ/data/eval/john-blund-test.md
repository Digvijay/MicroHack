# The John Blund test

John Blund is the Scandinavian sandman: he makes sure you sleep. Alex slept through 02:13 because the agents did the night shift and left the decision for the morning. Before you finish, show the coach that your Strandvik agents pass all five questions. Each question maps to one layer of what you built.

| # | Question | Layer | Evidence your team shows |
|---|---|---|---|
| 1 | **Who is asking?** | Identity and access (agent identity, A2A, guardrails) | The `strandvik-customer-service` agent card and instructions. The IAM role assignment (Foundry Agent Consumer) for Maria's agent identity on the strandvik project. One trace where Maria's agent gets a case and a handover, and one where an unknown agent, or Maria's agent trying to place an order, is refused. |
| 2 | **Can it do the job?** | Agents and orchestration (Foundry Agent Service, A2A, Web IQ) | Alex's agent calling the Parts, Logistics and Service agents. The 04:10 proposal in the Kolvo thread with the unit, Wednesday 09:00 delivery, Wednesday night technician, the Pune backup with the flight held until 11:00, and "final confirmation from Alex by 07:30". |
| 3 | **Does it know the business?** | Knowledge (Fabric IQ, Foundry IQ) | The ontology (or the "ontology on paper" fallback) and the Fabric data agent answering "which SD-900 units could replace SD9-K-0412?" with SD9-P-0981 and SD9-R-0733 (reserved, RSV-2291, owner Sam). The Service agent citing RES-02 ("a note is a reason to ask"), SC-KOL-2024 (48 hours) and FS-04 (Wednesday night slot). |
| 4 | **Can it reach a person?** | Work IQ and people | Alex's agent finding Sam's Friday note, asking Sam in the Kolvo thread at 03:52 and reading the reply. Alex approving at 07:30. A note on persona trimming: Alex's agent cannot read Sam's mail from Poliden's planner. |
| 5 | **Can you see it, cost it and stop it?** | Observability, evaluation and control | Traces with nested spans across projects. The evaluation run: baseline, fix, re-run, compare, with the custom rubric. Token counts for the night. How you would stop an agent: who owns each agent, how to disable it or remove its A2A access. |

## Scoring suggestion

One point per question with clear evidence, half a point if partly shown. Five points: Alex sleeps well. Fewer: decide as a team which layer you would fix first on Monday.
