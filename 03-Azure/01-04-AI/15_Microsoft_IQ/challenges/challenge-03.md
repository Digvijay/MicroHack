# Challenge 3: Know the business with Fabric IQ

**[Home](../README.md)** - [Previous Challenge](challenge-02.md) - [Next Challenge](challenge-04.md)

**Time:** 60 minutes. **IQ:** Fabric IQ.

## Story beat

09:00. The Supply Planner opens five spreadsheets to answer three questions: how many HX-220 housings are in Borås, which orders depend on Nordhavn Castings A/S, and how much money is at risk. The answers are in Caldova's tables, but nobody can join them fast enough. You give your agent the business data, through a governed **Fabric data agent** that sees only what the signed-in user may see.

## What you learn

- How to turn CSV files into lakehouse tables and a **Fabric data agent**.
- Why a data agent needs **example queries** and table semantics, not just tables.
- How the **Fabric IQ tool** connects a Foundry agent to Fabric **on behalf of the user**.
- What an **ontology** adds: business entities and relationships on top of tables.

## Feature status

| Feature | Status |
|---|---|
| Fabric lakehouse and Load to Tables | GA |
| Fabric data agent | GA |
| Fabric IQ MCP (data agent MCP endpoint) | GA |
| Fabric IQ tool in Foundry agents | Preview |
| Fabric IQ ontology | Preview |

> [!NOTE]
> The older **Fabric data agent** tool in Foundry was deprecated on 6 November 2026 in favour of the **Fabric IQ** tool. Use the Fabric IQ tool in this hack.

## The data

Nine CSV files in [`data/lakehouse`](../data/lakehouse) become nine tables: `suppliers`, `components`, `products`, `bill_of_materials`, `customers`, `sales_orders` (open orders), `purchase_orders` (open POs), `sales_orders_history` and `supplier_deliveries_history`. See [`data/README.md`](../data/README.md) for each file.

## Business path (portal, no code)

### A. Lakehouse (20 min)

1. Download the nine CSV files: in the Codespace explorer, select the files in `data/lakehouse`, right-click and choose **Download**. Or download them from the repository on GitHub.
2. Open `FabricPortalUrl` from your dashboard (or [app.fabric.microsoft.com](https://app.fabric.microsoft.com)) and sign in with your lab account.
3. Select **Workspaces** > **New workspace**. Name it `caldova-iq`. Under **Advanced**, choose **Fabric capacity** and your lab capacity (`FabricCapacityName`). Select **Apply**.
4. In the workspace, select **New item** > **Lakehouse**. Name it `caldova_lakehouse`.
5. Under **Files**, select **Upload** > **Upload files** and upload the nine CSV files.
6. For each file, select **...** > **Load to Tables** > **New table**. Keep the file name as the table name (for example `components`), header row on, separator comma.
7. Open the `components` table and check: HX-220 has `on_hand_boras` = 1200.

### B. Data agent (20 min)

1. In the workspace, select **New item** > **Data agent**. Name it `CaldovaOperations`.
2. **Add data** > choose `caldova_lakehouse` > select all nine tables.
3. In **Agent instructions**, paste the text of `AGENT_INSTRUCTIONS` from [`src/caldova/fabric_iq.py`](../src/caldova/fabric_iq.py).
4. In the lakehouse data source, open **Data source instructions** and paste `SOURCE_INSTRUCTIONS` from the same file. It explains which table holds what, and to filter on codes such as `PV-400`, not on names.
5. Test it first **without** example queries. Ask in the data agent chat:

   ```text
   How many HX-220 housings do we have on hand in Boras right now?
   If we can ship only 1,800 PV-400 to Brennmark Industries GmbH by Friday, how many units of SO-9001 are delayed and what is their value?
   ```

   Look at the SQL it generated. Does it filter on the `name` column with "HX-220 housing"? Does it look for the exact name "Brennmark"?

6. Open **Example queries** for the lakehouse and add these two (from `FEW_SHOTS` in `fabric_iq.py`):

   | Question | SQL query |
   |---|---|
   | How many HX-220 do we have on hand in Boras? | `SELECT component_id, name, on_hand_boras FROM dbo.components WHERE component_id = 'HX-220'` |
   | Show the open orders of Solvik. | `SELECT so.order_id, c.name AS customer, so.product_id, so.quantity, so.due_date, so.order_value_eur FROM dbo.sales_orders so JOIN dbo.customers c ON c.customer_id = so.customer_id WHERE c.name LIKE '%Solvik%'` |

7. Ask the two questions again. Expect **1,200** HX-220, and **2,200** units delayed worth **902,000 EUR**.
8. Select **Publish**.

### C. Connect it to your Foundry agent (10 min)

1. In the Foundry portal, open `caldova-portal` > **Tools** > **Add** > **Fabric IQ**.
2. Browse the **OneLake catalog** and select the `CaldovaOperations` data agent. Create the connection.
3. Add this line to the instructions:

   ```text
   - Fabric IQ (Caldova data agent): numbers from Caldova's business data: stock, orders, order values, suppliers, bill of materials, purchase orders. Use it for any quantity or money question.
   ```

4. Ask in the playground: `Which customers have open sales orders that depend on components from Nordhavn Castings A/S, and what is the total value of those orders?`

## Developer path (Codespace)

### A. Load the lakehouse

```bash
caldova fabric-iq load
```

This calls the Fabric REST API (`https://api.fabric.microsoft.com/v1`): it finds or creates the workspace `caldova-iq` on your capacity, creates the lakehouse `caldova_lakehouse`, uploads each CSV to OneLake (`Files/caldova/`) and calls the **Load Table** API for each one. It prints the workspace id, the lakehouse id and the nine tables.

### B. A data agent without examples

```bash
caldova fabric-iq agent --no-examples
caldova ask "How many HX-220 housings do we have on hand in Borås right now?" --iqs fabric
caldova ask "If we can ship only 1,800 PV-400 to Brennmark Industries GmbH by Friday, how many units of SO-9001 are delayed and what is their value?" --iqs fabric
```

`fabric-iq agent` writes the data agent definition (instructions, the lakehouse data source, its tables) as parts of a Fabric item definition, publishes it, and saves its MCP endpoint `https://api.fabric.microsoft.com/v1/mcp/workspaces/<workspace>/dataagents/<id>/agent`. Run each question twice. Watch for "no rows", a wrong number, or a filter like `name = 'HX-220 housing'` or `name = 'Brennmark'`.

### C. Teach it with examples

```bash
caldova fabric-iq agent
caldova ask "How many HX-220 housings do we have on hand in Borås right now?" --iqs fabric
caldova ask "If we can ship only 1,800 PV-400 to Brennmark Industries GmbH by Friday, how many units of SO-9001 are delayed and what is their value?" --iqs fabric
```

Now the definition also contains `fewshots.json` with the four `FEW_SHOTS` from [`src/caldova/fabric_iq.py`](../src/caldova/fabric_iq.py). Compare the answers.

> [!IMPORTANT]
> **Teaching moment.** A data agent turns a question into SQL. Without examples it guesses how people name things: "HX-220 housings" is not a value in any column, and "Brennmark" is not the full name "Brennmark Industries GmbH". Example queries and table semantics (filter on codes, match company names with `LIKE`) are what make it reliable. This is true for every natural language to SQL system.

### D. How the agent reaches Fabric

Read `connect_fabric_iq()`. It creates a Foundry project connection with:

| Property | Value | Why |
|---|---|---|
| `category` | `RemoteTool` | An MCP server the agent calls. |
| `authType` | `UserEntraToken` | The call runs **on behalf of the signed-in user**. |
| `audience` | `https://analysis.windows.net/powerbi/api` | The token is for Fabric (Power BI) APIs. |
| `target` | the data agent MCP URL | Where the tool lives. |

In `agent.py`, `FabricIQPreviewTool(project_connection_id=..., server_url=...)` adds the tool. Because the token is the user's, the agent sees only the data that user may see in Fabric. No service account with access to everything.

### E. The ontology (preview)

```bash
caldova fabric-iq ontology
```

This generates an ontology definition from the tables (`ontology_definition()`) and creates the item `CaldovaSupply`. It has six entities (Supplier, Component, Product, Customer, SalesOrder, PurchaseOrder) and five relationships. A generated entity looks like this:

```text
/// A company that supplies parts to Caldova.
entity Supplier
	lineageTag: <guid>
	backingTable: suppliers
	keyProperty: supplier_id

	property name
		dataType: string
		backingConfiguration
			valueColumn: suppliers.name
```

And a relationship, in `entityRelationships.tmdl`:

```text
entityRelationship 'Component Supplied By'
	fromEntity: Component
	toEntity: Supplier
	backingConfiguration
		relationship: rel_0
```

If the tenant setting for ontology is off, the command prints "Ontology (preview) is turned off in this tenant". Tell your coach and continue: the data agent is all you need for the score.

**Business path:** in the workspace, select **New item** > **Ontology (preview)**, and create entity types bound to the lakehouse tables (Supplier to `suppliers`, Component to `components`, and so on), then add relationships.

## Evaluate (both paths)

```bash
caldova eval --iqs web,fabric --label "challenge 3: + Fabric IQ"
caldova leaderboard
```

Look at q06 to q09: 1,200 HX-220; Brennmark, Solvik and Østerdal worth 1,975,000 EUR; 1,800 PV-400 by Friday; 2,200 units delayed worth 902,000 EUR. Language models vary, so run it twice before you draw conclusions.

> [!NOTE]
> **Business-only team?** The evaluation builds its own agent from the `caldova` state. Run `caldova fabric-iq load` and `caldova fabric-iq agent` once in the Codespace before the evaluation. If you used the names above, they reuse your workspace, lakehouse and data agent, and replace the data agent's definition with the reference one.

## Success criteria

- [ ] Nine tables are in `caldova_lakehouse`.
- [ ] The published data agent answers 1,200 HX-220 and 902,000 EUR delayed.
- [ ] You saw an answer fail without example queries, and get fixed with them.
- [ ] Your Foundry agent calls the Fabric IQ tool for quantity and money questions.
- [ ] You can explain why the connection uses the user's token.
- [ ] The leaderboard shows `challenge 3: + Fabric IQ`.

## Stretch

- Point the data agent at the ontology instead of the tables: `caldova fabric-iq agent --source ontology`. Ask q07 again. Look at the relationships in `RELATIONSHIPS`: which one is missing to go from a supplier to a customer? How would you model the bill of materials?
- Ask a history question: "Which supplier had the most late deliveries in the last 12 months?"

## Value card

| What this IQ is | What it fixed today | Where customers use it |
|---|---|---|
| **Fabric IQ**: governed business data in OneLake, a data agent that answers in business terms, and an ontology of entities and relationships. | Stock, buildable quantity, affected orders and money at risk, computed from the real tables. | Supply chain and inventory, finance (revenue at risk), sales operations, any "how many" or "how much" question over governed data. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No active Fabric F-SKU capacity found` | The capacity is paused or `FABRIC_CAPACITY_NAME` is wrong. Azure portal > resource group > Fabric capacity > **Resume**, or ask your coach. |
| You cannot create a workspace in the Fabric portal | Your user needs a Fabric license and the tenant setting "Users can create Fabric items". Ask your coach. |
| The data agent returns "no rows" or a wrong number | Rerun with examples (`caldova fabric-iq agent`), check the data source instructions, ask with codes (`HX-220`). |
| `Fabric IQ is not connected yet` | Run `caldova fabric-iq agent` first. |
| `Ontology (preview) is turned off in this tenant` | A Fabric admin must enable "Users can create ontology (preview) items". Continue without it. |
| The first answer after publishing is slow or fails | Wait one minute after publishing and ask again. |

## Learning resources

- [What is Fabric IQ?](https://learn.microsoft.com/en-us/fabric/iq/overview)
- [What is ontology (preview)?](https://learn.microsoft.com/en-us/fabric/iq/ontology/overview)
- [Fabric data agent](https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent)
- [Connect agents to Microsoft Fabric with Fabric IQ (preview)](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric-iq)

---

**[Home](../README.md)** - [Previous Challenge](challenge-02.md) - [Next Challenge](challenge-04.md)
