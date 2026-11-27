# Solution 1: Lights on

**[Back to Challenge 1](../../challenges/challenge-01.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-02/solution-02.md)

**Duration:** 45 minutes

## Goal

The team has its lab open, `.env` filled, 7 documents in the `documents` blob container, 14 tables in `strandvik_lakehouse`, and a paper map with units, machines, sites, customers, reservations and **owners**.

## Solution notes

### Part A: why `create-env.sh`

It only reads from Azure. It finds the lab by the resource group tag `microhack=15_Microsoft_IQ`, so the most common failure is signing in with a corporate account instead of the lab user. Only one person per team needs `.env`; the others can work from the portal links. On Windows without bash, `create-env.ps1` does the same.

### Part C: storage browser authentication

Shared key access is off on the storage account. The lab user has **Storage Blob Data Contributor**, so the Storage browser must use **Microsoft Entra user account**. The role can take a minute to apply on a fresh lab.

### Part D: lakehouse gotchas

- Keep **Lakehouse schemas** off. Later challenges expect the tables directly under **Tables**.
- On F2, parallel **Load to Tables** jobs are refused with HTTP 430. Load one file at a time and retry after 20 seconds.
- The Fabric data agent in challenge 3 reads the schema from the **SQL analytics endpoint**, not from the lakehouse view. Opening the endpoint once and selecting **Refresh** avoids "table not found" later.
- The notebook `00-load-the-world.ipynb` is an equal path: it uploads CSVs to `Files/strandvik/`, loads each table (waiting on HTTP 430), refreshes the SQL endpoint metadata and prints all tables and columns. If the Azure CLI session is gone, the participant runs `az login --use-device-code` in the terminal first.

### Part E: the map is the real deliverable

The map feeds the ontology (challenge 3) and every set of instructions after that. Insist on **owners**: the whole story turns on Sam owning the Rotterdam reservation and Alex owning the Kolvo account.

## Expected results

### `.env` (values differ per lab)

```text
PROJECT_ENDPOINT_STRANDVIK=https://iq-<hash>.services.ai.azure.com/api/projects/strandvik
PROJECT_ENDPOINT_KOLVO=https://iq-<hash>.services.ai.azure.com/api/projects/kolvo
MODEL_DEPLOYMENT_NAME=gpt-5.4-mini
STORAGE_ACCOUNT=iqst<hash>
DOCUMENTS_CONTAINER=documents
WORKIQ_MCP_URL=https://iq-wiq-<hash>....azurewebsites.net/mcp
WORKIQ_VIEWER_URL=https://.../viewer
WORKIQ_BOARD_URL=https://.../board
WORKIQ_KEY=<Alex's persona key>
WORKIQ_KEY_SAM=<Sam's persona key>
FABRIC_WORKSPACE_ID=<guid, or empty until the workspace exists>
```

### Tables and row counts

`sites` 9, `customers` 6, `people` 8, `account_owners` 6, `approved_external_agents` 2, `machines` 15, `drive_units` 22, `reservations` 5, `technicians` 4, `technician_schedule` 6, `transport_options` 6, `price_list` 8, `service_contracts` 6, `service_cases` 5.

### A good map

```text
Kolvo AB (customer, strategic)                 Poliden AB (customer, strategic)
  owner: Alex (KAM)                              owner: Sam (KAM, in Singapore)
  site: cab plant Hisingen, Gothenburg           site: Skelleftehamn
  service contract: 48 h replacement            service contract: changes confirmed in writing
  machine: press line 2 (KOL-PL2, critical)      machine: crusher line C3 (POL-C3)
    requires SD-900                                requires SD-900
    runs on SD9-K-0412 (vibration alarm,           planned stop next Monday: swap the worn unit
    half speed until Thursday 06:00)

Candidate SD-900 units
  SD9-P-0981  Pune factory, new, tested          not reserved
  SD9-R-0733  Rotterdam warehouse, new           RESERVED: RSV-2291 for Poliden C3, needed next Monday,
                                                 owner Sam. Sam's Friday note: "will probably move"
Not candidates
  SD9-R-0750  sold (Delfzijl Port Cranes)        SD9-P-0902  in repair
  SD7-R-0388  SD-700: does not fit an SD-900 press

People who decide
  Alex: any date or price to Kolvo     Sam: releases RSV-2291
  Maria: any Kolvo order               Poliden planner: confirms the stop date in writing
```

The map does not need to be this complete, but it must have the owners. One "may / may not" line per agent:

| Agent | May | May not |
|---|---|---|
| Maria's agent (Kolvo) | Ask approved suppliers for price and delivery | Order without Maria |
| Customer Service | Verify who is asking, open a case, hand over to the account owner | Quote, order or commit |
| Alex's agent | Orchestrate specialists, ask colleagues, send a proposal | Commit a date or price |
| Parts | Check stock, units, reservations | Sell or move a reserved unit |
| Logistics | Find routes and times, hold a flight | Book without approval |
| Service | Check contracts and technician slots | Change a contract |

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `create-env.sh`: "no Microsoft IQ lab found" | Signed in with the wrong account | `az logout`, run again with the lab user, or pass the resource group: `bash create-env.sh <rg>` |
| `FABRIC_WORKSPACE_ID` stays empty | The lab could not create the `strandvik-...` workspace | Create it (name starting with `strandvik`) on `iqcap<hash>`, run the script again |
| Storage browser: "This request is not authorized" | Authentication method is access key, or the role is not applied yet | Switch to **Microsoft Entra user account**; wait a minute on a fresh lab |
| **Load to Tables** greyed out | A folder or non-CSV file is selected | Select one CSV file |
| HTTP 430 in Fabric | F2 capacity busy with another load | Wait 20 seconds, retry |
| Fabric items fail or the workspace is read-only | Fabric capacity paused | Azure portal > `iqcap<hash>` > **Resume** |

## Checks for the coach

- [ ] `.env` has values (ask to see the variable names, not the keys).
- [ ] Storage browser: 7 files in `documents`.
- [ ] Fabric: 14 tables, `reservations` preview shows RSV-2291.
- [ ] Ask the team: "Which two SD-900s could replace SD9-K-0412, and who owns the Rotterdam one?" Answer: SD9-P-0981 and SD9-R-0733, owner Sam.

**[Back to Challenge 1](../../challenges/challenge-01.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-02/solution-02.md)
