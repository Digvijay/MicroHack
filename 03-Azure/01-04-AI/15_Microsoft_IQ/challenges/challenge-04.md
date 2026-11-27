# Challenge 4: Why didn't it take the unit?

[Previous Challenge](challenge-03.md) - **[Home](../README.md)** - [Next Challenge](challenge-05.md)

**Clock: 03:41** · **Time:** 60 minutes · **Products:** Foundry IQ (knowledge bases), Foundry Agent Service; stretch: knowledge graph

## The story

03:41. Let's stop the clock here. Alex's agent has found two units. One is brand-new, at Strandvik's factory in India. The other one is on the shelf in Rotterdam. So why doesn't it take that one? It's right there.

Because it's reserved for Poliden, a mining company and another Strandvik customer, for a maintenance stop next Monday. And the reservation has an owner: Sam. There is even a note from Sam, from last Friday: Poliden's stop will *probably* move two weeks.

Quick vote in your team: is that enough to take the unit? Hands up if yes. Then read the policy. **A note is a reason to ask.** It's not a decision.

## Goal

A **Service agent** in the strandvik project answers contract, policy and scheduling questions from Strandvik's documents through a **Foundry IQ knowledge base**, cites its sources, and treats a note as a reason to ask.

## Business task

1. Write the **reservation rule** into the Service agent's instructions, in your own words but true to [`RES-02`](../data/documents/reservation-policy-res-02.md): who may release a reservation, what counts as a release, what does not, and what the reserved customer is still owed.
2. Add the Service agent's **may / may not**: check contracts and technician slots; never change a contract or book a technician.
3. **Judge** the answers. Ask the agent at least these three questions and score each answer from 1 to 5: grounded, cites the right document, and does not decide anything it may not decide.
   - *Sam wrote on Friday that Poliden's stop will probably move two weeks. Can we take the Rotterdam unit for Kolvo?*
   - *What is the replacement target for Kolvo's press lines?*
   - *When can a Strandvik technician install at Kolvo this week?*

## Builder task

1. In the strandvik project, connect **Foundry IQ** to your lab's Azure AI Search service.
2. Create a **knowledge base** with one **Azure Blob Storage** knowledge source over the `documents` container, using the `text-embedding-3-large` deployment and content extraction mode **Minimal**. Wait until the source is **Active**.
3. Create the prompt agent **`strandvik-service`** with the business role's instructions, without web search, and attach the knowledge base to it.

**Stretch:** build a **knowledge graph** over the same documents with your own ontology, using [`notebooks/02-knowledge-graph-stretch.ipynb`](../notebooks/02-knowledge-graph-stretch.ipynb), and compare its answer to "who must approve moving SD9-R-0733, and in what form?" with the plain knowledge base.

## Constraints

- No keys pasted into forms when an identity works. The lab has already given the Search service and the projects the roles they need.
- Answers cite the document (for example RES-02, SC-KOL-2024, FS-04). An answer without a source does not count.
- The Service agent never says "yes, take it". At most: "ask the owner, and here is what you need from them".

## Success criteria

- [ ] The knowledge source shows **Active** and the knowledge base is attached to `strandvik-service`.
- [ ] Asked about Sam's note, the agent says the unit stays reserved until **Sam** releases it, that a note is **not** a release, that written approval (a chat message counts) is needed, and that Poliden must still get an equal unit in time, citing **RES-02**.
- [ ] It answers **48 hours** for Kolvo's replacement target (SC-KOL-2024) and **Wednesday 16 December 22:00 to Thursday 17 December 06:00** (slot FS-5101, Jonas), with 24 hours' notice, for the technician (FS-04), each with a citation.
- [ ] The business role shows the team's 1 to 5 scores for the three answers.

<!-- SHOT: c04-service-agent-cites-res02 | Foundry portal, strandvik project, Agents > strandvik-service > Playground | Answer to "Sam wrote on Friday that Poliden's stop will probably move two weeks. Can we take the Rotterdam unit for Kolvo?" with citation chips and the kb tool chip | Highlight "a note is a reason to ask", the RES-02 citation and the knowledge base tool call -->
![The Service agent cites RES-02](../images/c04-service-agent-cites-res02.png)

## Hints

<details>
<summary>Hint 1: The embedding model is not in the list</summary>

The knowledge source form only lists model deployments that existed when the page loaded. The lab deploys `text-embedding-3-large` up front, so just reload the page before you open the form.

</details>

<details>
<summary>Hint 2: Which authentication should I pick?</summary>

Identity-based: **Project Managed Identity** to connect the Search service, and **System assigned identity** on the Blob source. The lab gave the Search service Storage Blob Data Reader on the storage account and Cognitive Services OpenAI User on the Foundry resource.

</details>

<details>
<summary>Hint 3: Minimal or Standard extraction?</summary>

**Minimal**. The seven documents are plain text, so Standard is not needed. In this lab Standard fails with "Unable to connect to AI Services using managed identity" (Cognitive Services User), even when that role is granted, because the Foundry resource has key-based (local) authentication disabled.

</details>

<details>
<summary>Hint 4: The chat completions model dropdown is empty</summary>

That field is optional. It may only show "Browse more models": leave it empty. Retrieval still works.

</details>

<details>
<summary>Hint 5: The agent answers but does not use the knowledge base</summary>

Tell it to. Instructions such as "always search the knowledge base before you answer a question about a contract, a policy, a reservation or a technician, and cite the document id" make the tool call reliable. Check the tool call chip under the answer. Also remove the default **Web search** tool: the Service agent answers from the policies only.

</details>

## Learning resources

- [What is Foundry IQ?](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/what-is-foundry-iq)
- [Connect agents to Foundry IQ knowledge bases](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/knowledge-retrieval)
- [What is a knowledge source?](https://learn.microsoft.com/azure/search/agentic-knowledge-source-overview)
- [Agentic retrieval overview](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)

[Previous Challenge](challenge-03.md) - **[Home](../README.md)** - [Next Challenge](challenge-05.md)
