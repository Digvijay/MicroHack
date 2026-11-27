# Challenge 3: Know the business

[Previous Challenge](challenge-02.md) - **[Home](../README.md)** - [Next Challenge](challenge-04.md)

**Clock: 03:10** · **Time:** 75 minutes · **Products:** Fabric IQ (lakehouse, ontology, data agent), Foundry Agent Service

## The story

03:10. The case is with Alex's agent now. When it needs to check something in another part of the business, it brings in the agent that knows that part. First up: the parts agent. Where is there an SD-900 that could replace Kolvo's?

The ERP knows the stock. But the ERP is a pile of tables, and a pile of tables doesn't know that a unit on a shelf can still belong to somebody else. Strandvik has described how its business fits together: which unit is on which machine, at which customer, and **who owns the reservation** when a unit is promised to someone.

That's the ontology. A map of the business that agents can read. You drew it on paper in challenge 1. Now make it real.

## Goal

A **Parts agent** in the strandvik project answers stock questions from Strandvik's business data through **Fabric IQ**, and it knows that a reserved unit has an owner.

## Business task

1. Turn your paper map into an **ontology design**: entity types (for example Drive unit, Machine, Site, Customer, Reservation, Person), their key properties, and the **relationships** between them. Mark which relationship tells an agent "ask this person first".
2. Write three to five **example questions** with the answer you expect, for the data agent. One must be: *Which SD-900 units could replace SD9-K-0412 on Kolvo press line 2?*
3. Write the Parts agent's **may / may not**: check stock, units and reservations; never sell, release or move a reserved unit.

## Builder task

1. From `strandvik_lakehouse`, create a **Fabric data agent** named `strandvik_parts_data` over the lakehouse tables. Put the business role's ontology design into its instructions as an "ontology on paper", and load the example questions. Test it in Fabric, then **publish** it.
2. In the strandvik project, create the prompt agent **`strandvik-parts`** with the **Fabric IQ** tool pointing at your data agent, and the business role's instructions.

## Constraints

- The Parts agent answers from data, not from memory. Every serial it names must come from a tool call.
- It may report a reservation and its owner. It may never say a reserved unit is "available" without the reservation.
- The main path is the **ontology on paper**: the data agent reads the lakehouse tables, and the business design lives in its instructions. **If your tenant shows an Ontology item** (Fabric IQ, preview), you may build the design as a real ontology and put the data agent over it. Tell the coach which path you used.

## Success criteria

- [ ] The data agent in Fabric answers the replacement question with **SD9-P-0981** (new, tested, Pune) and **SD9-R-0733** (Rotterdam, **reserved** for Poliden, **RSV-2291**, owner **Sam**).
- [ ] It does **not** offer SD9-R-0750 (sold), SD9-P-0902 (in repair) or SD7-R-0388 (an SD-700, which does not fit).
- [ ] `strandvik-parts` gives the same answer in the Foundry playground, with a Fabric tool call visible in the response.
- [ ] The business role can show the ontology on paper (or the ontology item) and point at the relationship that leads to Sam.

## Hints

<details>
<summary>Hint 1: Where do I create the data agent?</summary>

Start from the lakehouse, not from the workspace **New item** list. The lakehouse ribbon has **Add to data agent**. The ontology on paper goes into the data agent's instructions, so the agent speaks in business terms (a Reservation is *owned by* a Person) and not only in joins. If the Fabric capacity is paused, ask the coach to resume it.

</details>

<details>
<summary>Hint 2: The data agent gives wrong or vague answers</summary>

Add instructions that explain the business meaning of columns (`status = in_stock` is not the same as free; a reservation with `status = active` blocks the unit). Example queries with their exact answers help more than long prose. The repo has ready ones in `data/fabric/data-agent-example-queries.json`: the data agent can import that file. If the agent cannot see a table you just loaded, refresh the SQL analytics endpoint metadata.

</details>

<details>
<summary>Hint 3: Connecting Fabric to Foundry</summary>

In the agent: **Add > Add tools > Configured**. Look for **Fabric IQ (OneLake Catalog)** (preview). The data agent must be **published** first. The catalog picker opens filtered to semantic models: change the type filter to **Data agent**. The first call can take a minute or more. The tool runs with the signed-in user's permissions, so your lab user needs access to the workspace.

</details>

<details>
<summary>Hint 4: Fit, not just stock</summary>

`machines.csv` says which model each machine requires. A unit in stock is only a candidate if its model matches the `required_model` of press line 2.

</details>

## Learning resources

- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)
- [What is ontology (preview)?](https://learn.microsoft.com/fabric/iq/ontology/overview) and the [ontology tutorial](https://learn.microsoft.com/fabric/iq/ontology/tutorial-0-introduction)
- [Fabric data agent concepts](https://learn.microsoft.com/fabric/data-science/concept-data-agent) and [create a Fabric data agent](https://learn.microsoft.com/fabric/data-science/how-to-create-data-agent)
- [Data agent example queries](https://learn.microsoft.com/fabric/data-science/data-agent-example-queries)
- [Use the Microsoft Fabric data agent with Foundry agents](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/fabric)

[Previous Challenge](challenge-02.md) - **[Home](../README.md)** - [Next Challenge](challenge-04.md)
