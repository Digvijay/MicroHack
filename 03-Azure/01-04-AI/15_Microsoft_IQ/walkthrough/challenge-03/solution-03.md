# Walkthrough Challenge 3: Know the business with Fabric IQ

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-02/solution-02.md) - [Next Solution](../challenge-04/solution-04.md)

**[Back to Challenge 3](../../challenges/challenge-03.md)**

Duration: 70 minutes

## Expected end state

- Fabric workspace `caldova-iq` on the lab F2 capacity, lakehouse `caldova_lakehouse` with nine tables.
- A published Fabric data agent `CaldovaOperations` over the lakehouse, with agent instructions, data source instructions and example queries.
- A Foundry project connection `caldova-fabric-iq` (developer path) or a Fabric IQ tool connection created in the portal (business path).
- Optional: ontology `CaldovaSupply` (preview).
- A run `challenge 3: + Fabric IQ` on the leaderboard.

## Command sequence (developer path)

```bash
caldova fabric-iq load
caldova fabric-iq agent --no-examples
caldova ask "How many HX-220 housings do we have on hand in Borås right now?" --iqs fabric
caldova ask "If we can ship only 1,800 PV-400 to Brennmark Industries GmbH by Friday, how many units of SO-9001 are delayed and what is their value?" --iqs fabric
caldova fabric-iq agent
caldova ask "How many HX-220 housings do we have on hand in Borås right now?" --iqs fabric
caldova ask "If we can ship only 1,800 PV-400 to Brennmark Industries GmbH by Friday, how many units of SO-9001 are delayed and what is their value?" --iqs fabric
caldova fabric-iq ontology
caldova eval --iqs web,fabric --label "challenge 3: + Fabric IQ"
```

What each command does (`src/caldova/fabric_iq.py`, REST on `https://api.fabric.microsoft.com/v1`):

| Command | Calls |
|---|---|
| `fabric-iq load` | `GET /capacities` (picks the Active F SKU named `FABRIC_CAPACITY_NAME`), `GET/POST /workspaces` (`caldova-iq`, assigned to the capacity), `POST /workspaces/{ws}/lakehouses`, OneLake DFS upload to `Files/caldova/<file>.csv`, `POST .../lakehouses/{id}/tables/{table}/load` (CSV, header, Overwrite) for each of the nine files. Saves ids and the SQL endpoint in `src/.caldova/state.json`. |
| `fabric-iq agent` | Builds the data agent definition: `data_agent.json`, `stage_config.json` (`aiInstructions`), `datasource.json` (lakehouse, `dbo` schema, nine tables, `dataSourceInstructions`) and, with examples, `fewshots.json`, for both `draft` and `published`. `POST /workspaces/{ws}/dataAgents` or `.../updateDefinition`. Saves the MCP URL and calls `connect_fabric_iq()`. |
| `fabric-iq ontology` | `ontology_definition()` generates TMDL parts (tables, six entities, five relationships), `POST /workspaces/{ws}/ontologies`. Maps `FeatureNotAvailable` to a clear message. |

The connection (ARM `PUT .../projects/<project>/connections/caldova-fabric-iq?api-version=2025-10-01-preview`):

```json
{
  "properties": {
    "category": "RemoteTool",
    "authType": "UserEntraToken",
    "target": "https://api.fabric.microsoft.com/v1/mcp/workspaces/<ws>/dataagents/<id>/agent",
    "audience": "https://analysis.windows.net/powerbi/api",
    "isSharedToAll": true
  }
}
```

`UserEntraToken` means the Fabric call runs on behalf of the user who asks. The agent sees only what that user may see in Fabric. The user also needs a Fabric license and read access to the data agent and the lakehouse.

## Expected outputs

| Question | Expected answer |
|---|---|
| q06 HX-220 in Borås | **1,200** HX-220 aluminium valve housings |
| q07 Orders depending on Nordhavn | Nordhavn supplies HX-220, used in PV-400 and CV-90. SO-9001 Brennmark Industries GmbH 1,640,000 EUR, SO-9002 Solvik Marine AS 212,000 EUR, SO-9003 Østerdal Pumps AS 123,000 EUR, total **1,975,000 EUR**. Ferrovia (BV-200) not affected. |
| q08 PV-400 ready by Friday | **1,800** = 600 finished + 1,200 built from HX-220 stock. Capacity (400 a day, 600 with overtime) is not the limit. |
| q09 Delayed on SO-9001 | **2,200** units, 2,200 x 410 = **902,000 EUR** |

A correct SQL for q07 looks like the Kvarnby few-shot with `s.name LIKE '%Nordhavn%'`:

```sql
SELECT DISTINCT so.order_id, c.name AS customer, so.product_id, so.quantity, so.order_value_eur
FROM dbo.sales_orders so
JOIN dbo.customers c ON c.customer_id = so.customer_id
JOIN dbo.bill_of_materials b ON b.product_id = so.product_id
JOIN dbo.components co ON co.component_id = b.component_id
JOIN dbo.suppliers s ON s.supplier_id = co.primary_supplier_id
WHERE s.name LIKE '%Nordhavn%'
```

## Teaching moment: example queries

Observed in testing with `--no-examples`: the data agent filtered on the `name` column (`WHERE name = 'HX-220 housing'`) or used an exact customer name (`name = 'Brennmark'`), returned no rows, and the Foundry agent then guessed or gave up. With the four `FEW_SHOTS` the generated SQL filters on `component_id = 'HX-220'` and matches companies with `LIKE '%Brennmark%'`, and the answers become stable. Message for the room: a data agent is only as good as its semantics. Instructions say what the tables mean; example queries show how to ask them.

For the business path, the two examples on the challenge page (HX-220 stock, Solvik orders) are enough to show the effect. The other two few-shots (Kvarnby dependency, BV-200 buildable) help q07 and q08.

## Ontology notes (preview)

- The generated ontology has entities Supplier, Component, Product, Customer, SalesOrder and PurchaseOrder, and relationships Component Supplied By, Order By Customer, Order For Product, PO For Component and PO To Supplier.
- It has **no bill of materials relationship** (Component used in Product), because `bill_of_materials` is a many-to-many link table and not an entity. That is a good stretch discussion: to answer "which customers depend on Nordhavn" by traversal, the ontology needs a Component to Product relationship. With `--source ontology`, q07 may be weaker than with the tables.
- If the tenant setting is off, the command prints "Ontology (preview) is turned off in this tenant..." and exits. Teams continue; the data agent is enough for the score.

## Common issues

| Symptom | Cause and fix |
|---|---|
| `No active Fabric F-SKU capacity found` | Capacity paused, or `FABRIC_CAPACITY_NAME` wrong. Resume it (Azure portal > Fabric capacity > Resume) and check the name. |
| Cannot create a workspace or a data agent in the portal | Tenant settings ("Users can create Fabric items", data agent, Copilot and Azure OpenAI) or no Fabric license. See the [coach guide](../README.md#before-the-day). |
| `FeatureNotAvailable` on `fabric-iq ontology` | Tenant setting "Users can create ontology (preview) items" is off. Continue without it. |
| Data agent answers "no rows" | Rerun `caldova fabric-iq agent` (with examples), check data source instructions, ask with codes. |
| First call after publishing fails or times out | Publishing takes a moment. Wait a minute, ask again. |
| HTTP 401 or 403 from the Fabric IQ tool | The user has no access to the workspace or no Fabric license, or the connection audience is wrong. |
| Load to Tables creates `components_1` or wrong types | Delete the table and load again with **New table** and the file name. |

## Discussion prompts

- Which tables in your company would become the first data agent? What example queries would it need?
- Why is an on-behalf-of connection safer than a service account?
- Where does a table end and an ontology begin?

---

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-02/solution-02.md) - [Next Solution](../challenge-04/solution-04.md)
