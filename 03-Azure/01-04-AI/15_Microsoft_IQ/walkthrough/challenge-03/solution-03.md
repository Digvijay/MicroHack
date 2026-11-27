# Solution 3: Know the business

[Previous Solution](../challenge-02/solution-02.md) - **[Back to Challenge 3](../../challenges/challenge-03.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-04/solution-04.md)

**Clock: 03:10** · **Duration:** 75 minutes

## Goal

A published Fabric data agent `strandvik_parts_data` over `strandvik_lakehouse`, with the team's ontology on paper in its instructions, and a Foundry prompt agent `strandvik-parts` that reaches it through Fabric IQ and knows that a reserved unit has an owner.

## Solution notes

### Check Fabric in the first 10 minutes

- **Capacity running.** If Fabric items do not open or the data agent does not answer, resume the capacity: Azure portal > the Fabric capacity > **Resume**.
- **Ontology on paper is the main path.** In the test tenant there was no **Ontology** item and no **Data agent** in the workspace **+ New item** list, and the Ontology API returned `FeatureNotAvailable`. The data agent is created from the lakehouse ribbon instead (Part B). Do not let teams wait for an admin. If the ribbon entry is missing too, the tenant setting **Users can create and share Data agent item types (preview)** is off.
- **Ontology item (Go further).** Only when the tenant setting **Users can create ontology (preview) items** is on. The editor is preview and changes often; the flow in Go further is the shape and could not be verified in the test tenant.

### Why the ontology goes into the instructions

A data agent over raw tables writes joins; it does not know that `in_stock` with an active reservation is not free. The ontology on paper gives it business words (a Reservation is *owned by* a Person) and the rules make the reservation visible. The two relationships that make an agent say "ask Sam first" are **Reservation owned by Person** (`reservations.owner_person_id = people.person_id`) and **Customer account owner Person** (`account_owners`). Ask every team to point at them.

Full expected design (teams may name things differently): the six core entity types in Part A, plus ServiceContract (`service_contracts`, `contract_id`), Technician (`technicians`), TechnicianSlot (`technician_schedule`, `slot_id`) and ExternalAgent (`approved_external_agents`, `agent_id`), with `covered by`, `scheduled at` and `acts for` relationships.

### Example queries do most of the work

The import file `data/fabric/data-agent-example-queries.json` holds 5 pairs in the format `{"question": "sql"}`. The replacement query joins `machines.required_model` (fit), `reservations` with `status = 'active'` (blocked) and `people` (owner). The "Preview runtime" banner is expected.

### Fabric IQ in Foundry

- The data agent must be **published**; Foundry uses the published stage.
- The **OneLake Catalog** picker opens filtered to **Semantic model**. Teams must switch the **Type** filter to **Data agent**.
- The tool runs with the **signed-in user's** permissions (identity passthrough). Same lab user in Foundry and Fabric, and a member of the workspace.
- The first call is slow: about 96 seconds in testing.
- The weekday line in both instruction blocks turns `needed_by_date` into "next Monday". The story never uses calendar dates.

## Expected results

Replacement question, data agent and `strandvik-parts` alike (about 30 seconds in Fabric):

| Serial | Site | Condition | Reservation | Owner |
|---|---|---|---|---|
| SD9-P-0981 | Strandvik Drives factory Pune | new, tested | none | |
| SD9-R-0733 | Strandvik Drives spare-parts warehouse Rotterdam | new | RSV-2291, Poliden AB, crusher line C3, needed next Monday | Sam |

Not offered: SD9-R-0750 (sold to Delfzijl Port Cranes), SD9-P-0902 (in repair), SD7-R-0388 (an SD-700). The point is the second row: SD9-R-0733 is reserved, so the answer is "ask Sam". In Foundry a tool call chip `strandvikpartsdata` shows under the answer.

Other example questions:

| Question | Expected answer |
|---|---|
| Who owns reservation RSV-2291? | Sam, key account manager for Poliden (currently in Singapore) |
| Is SD9-R-0733 free to use? | No. Reserved under RSV-2291 for Poliden until its owner Sam releases it |
| What drive unit does Kolvo press line 2 run on, and what is its status? | SD9-K-0412, vibration alarm, press at half speed |
| Who is the account owner for Kolvo AB? | Alex |

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Fabric items do not open, or the data agent never answers | Fabric capacity paused | Azure portal > the Fabric capacity > **Resume** |
| No **Data agent** or **Ontology** in **+ New item** | Expected in the test tenant | Use the lakehouse ribbon: **Add to data agent** > **New data agent**. If missing, the admin must enable **Users can create and share Data agent item types (preview)** |
| Data agent "cannot find table" | SQL analytics endpoint not synced | Open it and **Refresh**, or run the last cell of notebook 00 |
| SD9-R-0733 listed as "available" | Reservation rule or example query missing | Add the reservation rule and import the example queries |
| SD7-R-0388 listed | No fit rule | Add the `required_model` rule |
| Fabric IQ not in **Configured**, or no data agent in the picker | Not published, or picker filtered to **Semantic model** | Publish, refresh Foundry, set **Type** to **Data agent** |
| Tool call fails with an auth error | Identity passthrough: different users in Foundry and Fabric, or user not in the workspace | Sign in with the same lab user; add the user to the workspace |
| Playground seems stuck | First Fabric call is slow | Wait about 96 seconds before retrying |
| Answer shows `needed_by_date` as a calendar date | Weekday line missing | Add the weekday line to the instructions and save |

## Checks for the coach

- [ ] Data agent answer: SD9-P-0981 and SD9-R-0733 (RSV-2291, Sam), none of the three distractors.
- [ ] `strandvik-parts`: same answer, with a `strandvikpartsdata` tool call chip.
- [ ] Ontology on paper (or ontology item) with the "owned by" relationship from Reservation to Person.
- [ ] The team told you which path they used (paper or ontology item).

[Previous Solution](../challenge-02/solution-02.md) - **[Back to Challenge 3](../../challenges/challenge-03.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-04/solution-04.md)
