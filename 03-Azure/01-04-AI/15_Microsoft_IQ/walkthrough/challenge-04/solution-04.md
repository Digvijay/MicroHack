# Walkthrough Challenge 4: Know the rules with Foundry IQ

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-03/solution-03.md) - [Next Solution](../challenge-05/solution-05.md)

**[Back to Challenge 4](../../challenges/challenge-04.md)**

Duration: 70 minutes

## Expected end state

- Ten documents in the blob container `caldova-docs`.
- Knowledge source `caldova-docs` and knowledge base `caldova-docs-kb` (agentic retrieval), connected to the project as an MCP tool.
- Graph knowledge source `caldova-graph-caldova-supply-v1` and knowledge base `caldova-graph-caldova-supply-v1-kb`, then the same for `caldova-supply-v2`.
- A team-written `data/foundry-iq/caldova-supply-v2.jsonld`. Reference: [caldova-supply-v2.jsonld](caldova-supply-v2.jsonld) in this folder.
- A run `challenge 4: + Foundry IQ` on the leaderboard.

## Command sequence (developer path)

```bash
caldova foundry-iq documents
caldova foundry-iq retrieve "Nordhavn cannot deliver. Can we buy HX-220 from Teglbruk Metall AS to cover the shortfall?"
caldova ask "Under our agreement with Brennmark Industries GmbH, does a port closure count as force majeure, and how quickly must we notify them?" --iqs foundry
caldova foundry-iq graph
caldova foundry-iq retrieve "Which customers buy products that contain components supplied by Nordhavn Castings A/S?" --kb graph
caldova foundry-iq gql "MATCH (s:\`Supplier\`)-->(c:\`Component\`)-->(p:\`Product\`)<--(cu:\`Customer\`) WHERE s.name = 'Nordhavn Castings A/S' RETURN DISTINCT s.name AS supplier, c.name AS component, p.name AS product, cu.name AS customer"
caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb graph
caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb documents
# team writes data/foundry-iq/caldova-supply-v2.jsonld
caldova foundry-iq graph --ontology caldova-supply-v2
caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb graph
caldova eval --iqs web,fabric,foundry --label "challenge 4: + Foundry IQ"
```

If a team is short on time, copy the reference v2 for them: `cp walkthrough/challenge-04/caldova-supply-v2.jsonld data/foundry-iq/`. (The `walkthrough` folder is hidden in the Codespace explorer but exists on disk.)

## What the code does

All Search calls use REST `api-version=2026-11-01-preview` (`SEARCH_PREVIEW_API` in `config.py`) with an Entra token for `https://search.azure.com`. The preview version covers both the GA knowledge base and the preview graph, so one client serves both parts.

| Step | Call |
|---|---|
| Upload | Blob `PUT` per document with the user's token (the lab disables shared keys). |
| Knowledge source | `PUT knowledgesources('caldova-docs')`, kind `azureBlob`, `ResourceId=` connection string, `ingestionParameters` with the embedding model. Polls `knowledgesources('caldova-docs')/status` until the run ends. |
| Knowledge base | `PUT knowledgebases('caldova-docs-kb')`: chat model `gpt-5.6-luna` for query planning, `retrievalReasoningEffort: low`, `outputMode: answerSynthesis`, retrieval instructions "Quote clause numbers". |
| Connection | ARM `PUT .../connections/caldova-docs-kb`: `category: RemoteTool`, `authType: ProjectManagedIdentity`, `audience: https://search.azure.com/`, target `<search>/knowledgebases/caldova-docs-kb/mcp?api-version=...`, `metadata.type: knowledgeBase_MCP`. The project identity has Search Index Data Reader. |
| Agent tool | `MCPTool(server_label="caldova_documents", allowed_tools=["knowledge_base_retrieve"])`. If a graph KB exists, a second tool `caldova_graph`. |
| Graph source | Same source body plus `graphExtraction` with the inline JSON-LD ontology and `chatCompletionModel` for extraction; `resultsProcessing: none`. The KB uses `outputMode: extractiveData` and instructions to use `graph_search`. The graph index name comes from `createdResources.graphIndex`. |
| Retrieve | `POST knowledgebases('<kb>')/retrieve` with `includeActivity`, and for the graph `graphParameters.includeQuery`, so the CLI can print the GQL. |
| GQL | `POST indexes('<graph index>')/docs/search.graph` with `{"gql": ..., "includeStatistics": true}`. |

Graph extraction takes several minutes (the CLI waits up to 20 minutes, then 15 seconds more for graph writes).

## Expected outputs

| Question | Expected answer |
|---|---|
| q10 Force majeure, Brennmark | Yes. FA-2024-007 counts port closures declared by a public authority as force majeure. Notify Brennmark in writing **within 48 hours** of becoming aware. (Ferrovia is 72 hours: a wrong answer here trips the gate.) |
| q11 Partial deliveries | Brennmark: yes, if its Purchasing Manager agrees **in writing**. Solvik: **no partial deliveries** (FA-2025-002). |
| q12 Teglbruk | **No.** Teglbruk Metall AS is on **quality hold** after lot L-7731 failed the pressure test on 4 December 2026 (QR-2026-118). **SQP-04**: no deviation for **pressure-bearing** parts, and HX-220 is pressure-bearing. Hold until corrective action, expected 16 December 2026. |
| q13 Allocation | AP-02: strategic, then key, then standard, then by due date. The Plant Manager may override in writing. |
| Graph: customers of Nordhavn | Brennmark Industries GmbH, Solvik Marine AS, Østerdal Pumps AS. **Not** Ferrovia Systems S.p.A. |

The GQL the planner generates for the Nordhavn question looks like this:

```text
MATCH (s:`Supplier`)-->(c:`Component`)-->(p:`Product`)<--(cu:`Customer`)
WHERE s.name = 'Nordhavn Castings A/S'
RETURN DISTINCT s.name AS supplier, c.name AS component, p.name AS product, cu.name AS customer
```

Expected rows: Nordhavn Castings A/S, HX-220, PV-400, Brennmark Industries GmbH; HX-220, PV-400, Østerdal Pumps AS; HX-220, CV-90, Solvik Marine AS.

## Teaching moments (all observed)

1. **Entity resolution.** Without naming guidance in `rdfs:comment`, the extractor created "PV-400" and "PV-400 pump valve" as two nodes. Customers that buy "PV-400 pump valves" hung off the second node, and the traversal from HX-220 missed them. The v1 comments ("Name it by its product code only... never with a description") fixed it. The documents also use codes consistently on purpose (see `data/README.md`). Point: ontology comments are prompts for the extractor.
2. **You only get what your ontology asks for.** With only the v1 graph, the agent answered **yes** to "Can we buy HX-220 from Teglbruk?", because v1 has `backupFor` but no notion of quality reports or policies. The documents KB says **no** (quality hold, SQP-04, pressure-bearing). v2 adds `QualityReport`, `Policy`, `placesOnHold`, `restricts` and `failedLotOf`; after `caldova foundry-iq graph --ontology caldova-supply-v2` the graph returns Teglbruk "on quality hold". The ontology is fixed at creation, so each version is a new knowledge source and KB. That is also why the agent instructions say "A relationship in the graph does not mean an action is allowed".
3. **Phrasing.** "Which supplier cannot ship?" was over-read by the query planner as "has no `shipsFrom` port" and returned the wrong suppliers. Ask relationship questions plainly ("Which supplier is on quality hold?") and check the printed GQL.

## Contrast for the debrief

| | Plain retrieval | Knowledge graph | Fabric IQ |
|---|---|---|---|
| Source | Document passages | Entities and relationships extracted from documents | Governed tables, data agent, ontology bound to tables |
| "Which customers depend on Nordhavn?" | Partly | Yes, by traversal | Yes, by join |
| "Can we use Teglbruk?" | Yes (reads policy and report) | Only with v2 | No policy text |
| "How much money is at risk?" | No | No | Yes: 1,975,000 EUR dependent, 902,000 EUR delayed |

## Business path notes

- Uploading in the Azure portal needs **Switch to Microsoft Entra user account** (storage keys are disabled) and the Storage Blob Data Contributor role (the lab grants it).
- If the team names the KB `caldova-docs-kb`, the developer commands and the portal agent use the same knowledge base. For scoring, `caldova foundry-iq documents` must have run once (it writes the CLI state).
- Part B is API only. Demo it from your own lab, or pair a business participant with a developer. The Foundry IQ skills plugin for GitHub Copilot CLI (`/plugin marketplace add microsoft/azure-skills`, `/plugin install foundry-iq-skills@azure-skills`) has a Knowledge Graph Playground viewer that works well on a projector.

## Common issues

| Symptom | Cause and fix |
|---|---|
| Graph source "ontology locked" or changes ignored | The ontology is fixed per source. Create a new version file (v2, v3) and run `caldova foundry-iq graph --ontology <name>`. |
| `documents failed` during ingestion | Search identity lacks Storage Blob Data Reader, or soft delete / versioning settings were changed on the storage account. |
| Graph build times out | Model quota for `gpt-5.6-luna` exhausted by parallel teams. Retry later, stagger teams. |
| `No knowledge graph yet` on `gql` | Run `caldova foundry-iq graph` first. |
| Agent says yes to Teglbruk | Only the graph was consulted. Check both tools are present and the instructions say to check policies first. |
| q10 fails with 72 hours | The agent read the Ferrovia agreement. Ask it to quote the Brennmark clause (FA-2024-007). |

## Discussion prompts

- What would your ontology v1 miss? Which relationship would an auditor ask for first?
- When is a graph worth the extraction cost, and when is retrieval enough?
- Who owns the ontology in your company: data, legal or the business?

---

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-03/solution-03.md) - [Next Solution](../challenge-05/solution-05.md)
