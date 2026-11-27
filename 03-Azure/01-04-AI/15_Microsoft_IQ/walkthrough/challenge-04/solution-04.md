# Solution 4: Why didn't it take the unit?

[Previous Solution](../challenge-03/solution-03.md) - **[Back to Challenge 4](../../challenges/challenge-04.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-05/solution-05.md)

**Clock: 03:41** · **Duration:** 60 minutes

## Goal

Foundry IQ connected to the lab's Search service, a knowledge base `strandvik-policies` with one Azure Blob Storage source over `documents` (status **Active**), and `strandvik-service` answering with citations and treating Sam's note as a reason to ask.

## Solution notes

### Run the vote first (Part A)

Stop the story clock at 03:41. Read the beat. Ask: "Is Sam's note enough to take the unit? Hands up if yes." Let one "yes" explain. Then point at RES-02 section 4.2: **a note is a reason to ask.** Restart the clock.

### Identities, not keys

- Part B: **Project Managed Identity**. The lab gave the project identity Search Index Data Reader, Search Index Data Contributor and Search Service Contributor. **API Key** also works, but steer teams to the identity.
- Part C: **System assigned identity** on the Blob source. The lab gave the Search service Storage Blob Data Reader on the storage account and Cognitive Services OpenAI User on the Foundry resource.

### Why Minimal extraction

The seven documents are plain text, so Minimal is enough. **Standard** fails in this lab with "Unable to connect to AI Services using managed identity ... Cognitive Services User", even when that role is granted, because the Foundry resource has local (key) authentication disabled.

### Knowledge base as a tool

- The embedding model list is read when the page loads: reload if `text-embedding-3-large` is missing.
- The chat completions model is optional; in testing the dropdown only showed "Browse more models". Retrieval works without it.
- The agent calls the knowledge base as an MCP tool named `kb-strandvik-policies-...`. Remove the default **Web search** tool, or answers drift to the web.
- The "search the knowledge base before every answer" line makes the tool call reliable.

### Stretch: knowledge graph (notebook 02)

Only for developers with the optional Codespace (on their own fork) or a local clone. The notebook creates `strandvik-graph-v1` with `graphExtraction` (Search preview REST API, chat model `gpt-5.6-luna`, the ontology inline), waits a few minutes for ingestion, then creates `strandvik-graph-v1-kb`. The chat model is only allowed together with `graphExtraction`. The ontology is fixed at creation: a changed ontology needs `VERSION = "v2"`. Expected answer: Sam, the reservation owner, in writing (a chat message counts), plus Poliden's planner for the stop date. The activity list shows graph retrieval.

## Expected results

All three were verified in testing, each with citations.

| Question | Expected answer | Sources |
|---|---|---|
| Sam wrote on Friday that Poliden's stop will probably move two weeks. Can we take the Rotterdam unit for Kolvo? | Not yet. SD9-R-0733 is reserved (RSV-2291) until its owner Sam releases it. A note is not a release: a note is a reason to ask. Ask Sam; his written approval (a chat message counts) is needed; Poliden must still get an equal SD-900 before next Monday; the reallocating KAM carries the cost risk. Poliden's planner must confirm any stop change in writing. | RES-02 4.1 to 4.5, SC-POL-2025 |
| What is the replacement target for Kolvo's press lines? | 48 hours from the request for critical units on press lines 1 to 3; Strandvik installs; uptime credit 0.5% of the annual contract value per day beyond the target. | SC-KOL-2024 |
| When can a Strandvik technician install at Kolvo this week? | Wednesday 22:00 to Thursday 06:00 (slot FS-5101, Jonas, SD-900 certified). A night install needs 24 hours' notice; installation takes 6 to 8 hours. | FS-04, SD-900 product sheet |

Scoring guide (1 to 5 each): **grounded**, **cites**, **stays in its lane**.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Embedding model missing in the form | List read at page load | Reload the page |
| Source fails with "Unable to connect to AI Services using managed identity ... Cognitive Services User" | Standard extraction; Foundry resource has local auth disabled | Recreate the source with **Minimal** |
| Chat completions model dropdown only shows "Browse more models" | Optional field | Leave it empty |
| Source stuck in Creating, or Failed | Container empty, or Search identity lacks Storage Blob Data Reader / Cognitive Services OpenAI User | Upload the documents, or re-run the lab deployment |
| Agent answers without a citation | No "search before every answer" line | Add it and cite the document id |
| Agent answers from the web | Default **Web search** still attached | **Actions for Web search** > **Remove**, **Save** |
| Agent says "yes, take the Rotterdam unit" | Reservation rule missing or too soft | Paste the RES-02 block |
| Calendar dates in answers | Weekday line missing | Add the weekday line and save |
| Notebook 02: `chatCompletionModel` error | Chat model used without `graphExtraction` | Do not change that part of the notebook |
| Notebook 02: 403 | Azure CLI on the wrong account, or user lacks Search Service Contributor | Sign in with the lab user; check the role |

## Checks for the coach

- [ ] Knowledge source **Active**, attached to `strandvik-service`.
- [ ] Sam's note answer: "a note is a reason to ask", ask Sam, written approval, equal unit in time, with RES-02.
- [ ] 48 hours (SC-KOL-2024) and Wednesday night 22:00 to 06:00 (FS-04), cited.
- [ ] The team's 1 to 5 scores.

[Previous Solution](../challenge-03/solution-03.md) - **[Back to Challenge 4](../../challenges/challenge-04.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-05/solution-05.md)
