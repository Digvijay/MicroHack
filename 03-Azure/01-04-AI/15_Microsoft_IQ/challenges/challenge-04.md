# Challenge 4: Know the rules with Foundry IQ

**[Home](../README.md)** - [Previous Challenge](challenge-03.md) - [Next Challenge](challenge-05.md)

**Time:** 60 minutes. **IQ:** Foundry IQ.

## Story beat

10:00. The Supply Planner has an idea: "Nordhavn is stuck. Let's buy the HX-220 from Teglbruk, our backup supplier." It sounds sensible. But the answer is hidden in three different documents: the supplier agreement, a quality report from last Friday and a policy about pressure-bearing parts. Your agent needs Caldova's rulebook, and it needs to read across documents.

## What you learn

- How a **knowledge base** with agentic retrieval answers questions across many documents, with citations.
- How a **knowledge graph** extracts entities and relationships from the same documents, guided by **your ontology**.
- Why "you only get what your ontology asks for", and how to version an ontology.
- When to use plain retrieval, a document graph or the Fabric ontology.

## Feature status

| Feature | Status |
|---|---|
| Foundry IQ knowledge bases (agentic retrieval) | GA |
| Knowledge base as an MCP tool in Foundry agents | GA |
| Foundry IQ knowledge graph (entity graph) | Preview, API only |

## The documents

Ten Markdown files in [`data/documents`](../data/documents): four customer agreements, two supplier agreements, the supplier quality policy SQP-04, the allocation policy AP-02, the quality report QR-2026-118 and the product catalogue. See [`data/README.md`](../data/README.md#foundry-iq-documents).

## Part A: a knowledge base (GA, 35 min)

### Business path (portal, no code)

1. Upload the documents. In the Azure portal, open your storage account (`StorageAccountName`) > **Containers** > `caldova-docs` > **Upload**. Select the ten files from `data/documents` (download them from the Codespace first). If the portal says you have no access, select **Switch to Microsoft Entra user account**: the lab disables storage keys.
2. In the Foundry portal, open **Knowledge** (Foundry IQ). If asked, connect the Azure AI Search service from your dashboard (`SearchEndpoint`).
3. Create a **knowledge base** named `caldova-docs-kb` with a knowledge source of type **Azure Blob Storage**: your storage account, container `caldova-docs`, embedding model `text-embedding-3-small`, chat model `gpt-5.6-luna`. Wait until ingestion finishes.
4. Open `caldova-portal` > **Knowledge** > **Add** and select `caldova-docs-kb`. Add this line to the instructions:

   ```text
   - Foundry IQ (caldova_documents): contracts, policies, quality reports and the catalogue. Use it for rules, obligations, penalties and deadlines, and quote the clause. Before you say an action is allowed, check the policies and quality holds.
   ```

5. Ask: `Nordhavn cannot deliver. Can we buy HX-220 from Teglbruk Metall AS to cover the shortfall?`

### Developer path (Codespace)

```bash
caldova foundry-iq documents
```

This takes a few minutes. Read [`src/caldova/foundry_iq.py`](../src/caldova/foundry_iq.py) while it runs. The command:

1. Uploads the ten documents to Blob Storage with your Entra token.
2. Creates a **knowledge source** `caldova-docs` (`PUT knowledgesources('caldova-docs')`, kind `azureBlob`, with the embedding model), and waits until ingestion ends.
3. Creates a **knowledge base** `caldova-docs-kb` (`PUT knowledgebases('caldova-docs-kb')`) with low retrieval reasoning effort and answer synthesis.
4. Registers the knowledge base MCP endpoint (`.../knowledgebases/caldova-docs-kb/mcp`) as a Foundry project connection: category `RemoteTool`, auth `ProjectManagedIdentity`. In `agent.py`, an `MCPTool` with `allowed_tools=["knowledge_base_retrieve"]` uses it.

Query the knowledge base directly, without the agent:

```bash
caldova foundry-iq retrieve "Nordhavn cannot deliver. Can we buy HX-220 from Teglbruk Metall AS to cover the shortfall?"
```

Then through the agent:

```bash
caldova ask "Under our agreement with Brennmark Industries GmbH, does a port closure count as force majeure, and how quickly must we notify them?" --iqs foundry
```

Expected: **No** to Teglbruk (quality hold after QR-2026-118, SQP-04 forbids deviations for pressure-bearing parts, and HX-220 is pressure-bearing). **Yes** to force majeure for Brennmark, with notice **within 48 hours**.

## Part B: a knowledge graph (Preview, 35 min)

Retrieval finds passages. A **graph** finds relationships: which supplier feeds which component, which product, which customer. Foundry IQ extracts the graph from the documents, using an **ontology** you write in JSON-LD.

### Build the graph from ontology v1

Open [`data/foundry-iq/caldova-supply-v1.jsonld`](../data/foundry-iq/caldova-supply-v1.jsonld). It defines five classes (Supplier, Component, Product, Customer, Port) and five relationships (`supplies`, `backupFor`, `usedIn`, `buys`, `shipsFrom`). Read the `rdfs:comment` texts: they tell the extraction model how to name things.

```bash
caldova foundry-iq graph
caldova foundry-iq retrieve "Which customers buy products that contain components supplied by Nordhavn Castings A/S?" --kb graph
```

Expected: exactly **Brennmark Industries GmbH, Solvik Marine AS and Østerdal Pumps AS**, and **not** Ferrovia Systems S.p.A. (it buys BV-200, which has no HX-220). The command also prints the **GQL** query the planner generated. Run your own:

```bash
caldova foundry-iq gql "MATCH (s:\`Supplier\`)-->(c:\`Component\`)-->(p:\`Product\`)<--(cu:\`Customer\`) WHERE s.name = 'Nordhavn Castings A/S' RETURN DISTINCT s.name AS supplier, c.name AS component, p.name AS product, cu.name AS customer"
```

> [!NOTE]
> **Teaching moment: entity resolution.** In an early test, the ontology had no naming guidance. The extractor created two nodes, "PV-400" and "PV-400 pump valve", and the traversal missed customers. The comments in v1 ("Name it by its product code only, for example PV-400, never with a description") fixed it. Ontology text is instructions for the extractor.

### You only get what your ontology asks for

Ask the same question to both knowledge bases:

```bash
caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb graph
caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb documents
```

The graph sees `Teglbruk Metall AS backupFor HX-220` and nothing else, so it suggests **yes**. The documents say **no**. Ontology v1 has no idea what a quality report or a policy is, so the extractor never captured the hold.

**Your task:** write ontology v2.

1. Copy `data/foundry-iq/caldova-supply-v1.jsonld` to `data/foundry-iq/caldova-supply-v2.jsonld`.
2. Add two classes: `cal:QualityReport` and `cal:Policy`. Give each a naming comment (by its id, for example QR-2026-118 or SQP-04).
3. Add three relationships: `cal:placesOnHold` (QualityReport to Supplier), `cal:restricts` (Policy to Component) and `cal:failedLotOf` (QualityReport to Component). Write a clear `rdfs:comment` for each.
4. Build a **new** graph and ask again:

   ```bash
   caldova foundry-iq graph --ontology caldova-supply-v2
   caldova foundry-iq retrieve "Can we buy HX-220 from Teglbruk Metall AS?" --kb graph
   ```

Now the graph returns Teglbruk as **on quality hold**. The ontology is fixed when a graph source is created, so each version becomes a new knowledge source and knowledge base (`caldova-graph-caldova-supply-v2`). After this command, `--kb graph`, `gql` and the agent use v2.

> [!TIP]
> **Phrasing matters.** Ask relationship questions plainly. In testing, "Which supplier cannot ship?" was read by the query planner as "has no `shipsFrom` port". "Which supplier is on quality hold?" works.

### Business path for Part B

The knowledge graph is API only in this preview. Run the two copy-paste commands above with a developer teammate, or watch your coach's demo. Optional: the Foundry IQ skills plugin for GitHub Copilot CLI has a **Knowledge Graph Playground** viewer:

```text
/plugin marketplace add microsoft/azure-skills
/plugin install foundry-iq-skills@azure-skills
```

## Which one answers what?

| Question | Plain retrieval (knowledge base) | Knowledge graph (Foundry IQ) | Fabric IQ (tables, data agent, ontology) |
|---|---|---|---|
| "Can we buy HX-220 from Teglbruk?" | Yes, reads the policy and the report | Only if the ontology models holds and policies | No, the tables have a status but no policy text |
| "Which customers depend on Nordhavn?" | Partly, from scattered passages | Yes, a traversal over the documents | Yes, a join over governed tables |
| "How much money is at risk?" | No | No | Yes, computed from the orders |

## Evaluate (both paths)

```bash
caldova eval --iqs web,fabric,foundry --label "challenge 4: + Foundry IQ"
caldova leaderboard
```

Look at q10 to q13: force majeure and 48 hours, partial deliveries (Brennmark in writing, Solvik none), Teglbruk blocked by SQP-04, and the AP-02 allocation order.

> [!NOTE]
> **Business-only team?** The evaluation builds its own agent from the `caldova` state. Run `caldova foundry-iq documents` once in the Codespace before the evaluation.

## Success criteria

- [ ] Your agent answers the Teglbruk question with **no**, and cites QR-2026-118 and SQP-04.
- [ ] The v1 graph returns three customers for Nordhavn, without Ferrovia.
- [ ] You wrote ontology v2 and the graph now knows about the quality hold.
- [ ] You can explain when to use retrieval, a document graph or the Fabric ontology.
- [ ] The leaderboard shows `challenge 4: + Foundry IQ`.

## Value card

| What this IQ is | What it fixed today | Where customers use it |
|---|---|---|
| **Foundry IQ**: knowledge bases with agentic retrieval over curated content, plus a knowledge graph extracted with your ontology. | Force majeure, partial delivery rules, the allocation policy and the blocked backup supplier, with clause citations. | Contracts and procurement, policies and compliance, quality and regulatory documents, product knowledge across many files. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Foundry IQ is not set up yet` | Run `caldova foundry-iq documents` first. |
| Upload fails in the Azure portal | Select **Switch to Microsoft Entra user account** in the container view. |
| `... documents failed` during ingestion | Check the search identity can read the storage account. Ask your coach. |
| The graph command reports the ontology is locked, or ignores your changes | The ontology is fixed per source. Use a new file name (v2, v3) and run `caldova foundry-iq graph --ontology <new name>`. |
| `Ontology file not found` | The file must be in `data/foundry-iq` and end in `.jsonld`. Pass the name without the extension. |
| The graph returns odd or empty results | Ask plainly, name entities as in the ontology comments, and check the printed GQL. |

## Learning resources

- [What is Foundry IQ?](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Create a knowledge base](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-how-to-create-knowledge-base)
- [Create and query an entity graph](https://learn.microsoft.com/en-us/azure/search/agentic-knowledge-source-how-to-entity-graph)

---

**[Home](../README.md)** - [Previous Challenge](challenge-03.md) - [Next Challenge](challenge-05.md)
