# Challenge 6: The night shift

[Previous Challenge](challenge-05.md) - **[Home](../README.md)** - [Next Challenge](challenge-07.md)

**Clock: 04:10** · **Time:** 75 minutes · **Products:** Web IQ (web search), A2A orchestration, Foundry Agent Service

## The story

Alex's agent is running the case now. When it needs to check something in another part of the business, it brings in the agent that knows that part. The parts agent checks the stock. The logistics agent works out how fast a unit could get there. The service agent checks Kolvo's contract and whether a technician can install on Wednesday night.

Each one works in its own system, within what it may do, and hands its answer back. All in one thread, where Alex will pick it up in the morning. That's the second circle: our agents working together across the company while most of the company sleeps.

At 04:10, Alex's agent has a real proposal for Maria's agent: the unit, the transport and the technician. And one honest line at the end: **final confirmation from Alex by 07:30.** The agent can propose a date. Only Alex can commit to it.

## Goal

**Alex's agent** orchestrates `strandvik-parts`, a new **Logistics agent** and `strandvik-service` over **A2A**, combines their answers with Sam's reply, and posts **one proposal** in the Kolvo thread that Alex can approve at 07:30.

## Business task

1. Decide what the **proposal must contain**. Write it as a checklist: unit, route and arrival, installation, backup, what happens to Poliden, sources, and the last line.
2. Decide what **only Alex** may commit, and write it into Alex's agent's instructions as hard "never" rules (dates, prices, bookings above 10,000 EUR, releasing reservations, orders).
3. Write the Logistics agent's **may / may not**, true to [`LOG-03`](../data/documents/logistics-rules-log-03.md): find routes and times, hold a flight; never book without approval.

## Builder task

1. Create the prompt agent **`strandvik-logistics`** with the **Web search** tool (Web IQ) and the challenge 4 knowledge base for LOG-03.
2. Make the three specialists callable over A2A: incoming A2A on `strandvik-parts`, `strandvik-logistics` and `strandvik-service`, and the right role for **Alex's agent's identity** on the strandvik project.
3. Give `alex-agent` three **A2A tools**, one per specialist, next to its Work IQ tool.
4. Run the night in the `alex-agent` playground: one request in, one proposal posted in the Kolvo thread.

## Constraints

- Orchestrate with **A2A**. Do not use Foundry portal Workflows (they retire on 1 December 2026).
- Each specialist keeps its own tools. Alex's agent does not get the Fabric tool, the knowledge base or web search: it asks the specialists.
- The story's dates and prices come from Strandvik's data and documents. The web is for the real world: the route exists, the weather, a public holiday. If the web disagrees with LOG-03, the agent says so and uses LOG-03.
- Nothing is booked, ordered, released or committed by an agent.

## Success criteria

- [ ] One `alex-agent` run shows A2A calls to all three specialists and a Work IQ call that posts in the thread (check the tool chips or the trace).
- [ ] The proposal in the Kolvo thread contains: SD-900 **SD9-R-0733** from Rotterdam at Kolvo **Wednesday 16 December 09:00** by truck and ferry; Strandvik technician **Wednesday night 22:00 to 06:00**; backup **SD9-P-0981** by air with the flight **held until 11:00**; reservation RSV-2291 moves to SD9-P-0981 so Poliden gets an equal unit in time; Sam's release pending Poliden's written confirmation; and **"Final confirmation from Alex by 07:30."**
- [ ] The proposal names its sources (ERP data, RES-02, LOG-03, FS-04, SC-KOL-2024, Sam's reply).
- [ ] Asked "It is 04:10. Can you confirm the delivery date to Kolvo now?", Alex's agent says no, only Alex can.

<!-- SHOT: c06-proposal-in-thread | Work IQ emulator viewer (/viewer, signed in as Alex) > Chats > Kolvo press line 2, SD-900 | The thread after the 04:10 proposal: the agent's question to Sam, Sam's reply, then the proposal post from "Alex's agent (on behalf of Alex)" | Highlight the unit and arrival time, the backup flight held until 11:00, and the line "Final confirmation from Alex by 07:30" -->
![The 04:10 proposal in the Kolvo thread](../images/c06-proposal-in-thread.png)

## Hints

<details>
<summary>Hint 1: Same lock, new door</summary>

Inside the strandvik project the rules are the same as for Maria in challenge 2. Each target agent needs incoming A2A (notebook 01 works for any agent: change `AGENT_NAME` and the card). The **calling** agent, now `alex-agent`, needs **Foundry Agent Consumer** on the project. Then wait 3 to 5 minutes.

</details>

<details>
<summary>Hint 2: One failing tool breaks the whole run</summary>

As on the board, one unreachable A2A target fails Alex's whole response with `tool_user_error`. Add the A2A tools one at a time and test each before you add the next.

</details>

<details>
<summary>Hint 3: Alex's agent asks the wrong agent, or nobody</summary>

Tell it who knows what, by name: stock and reservations to the parts agent, routes and flight holds to the logistics agent, contracts and technicians to the service agent, people to Work IQ. Give it the order of work: facts first, then ask Sam, then propose.

</details>

<details>
<summary>Hint 4: The Parts agent works alone, but not when Alex's agent calls it</summary>

The Fabric IQ tool runs with a **user's** permissions. Called over A2A, there is no signed-in user. Look at the trace, then ask your coach for the fallback the lab supports.

</details>

## Learning resources

- [Use web search tool in Foundry Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/web-search)
- [Connect to an A2A agent endpoint from Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/agent-to-agent)
- [Enable incoming A2A on a Foundry agent](https://learn.microsoft.com/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint)
- [Agent tracing overview](https://learn.microsoft.com/azure/ai-foundry/observability/concepts/trace-agent-concept)

[Previous Challenge](challenge-05.md) - **[Home](../README.md)** - [Next Challenge](challenge-07.md)
