# Solution 1: Lights on

**[Back to Challenge 1](../../challenges/challenge-01.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-02/solution-02.md)

**Duration:** 45 minutes

## Goal

The team works in the browser from its lab dashboard (three portals open, Cloud Shell opens) and has 7 documents in the `documents` blob container, 14 tables in `strandvik_lakehouse`, and a paper map with units, machines, sites, customers, reservations and **owners**.

## Solution notes

### Part A: browser only

Participants install nothing and need no Codespace. They work from the **lab dashboard** values (project links, `FabricPortalUrl`, `StorageAccountName`, `WorkIQBoardUrl`, `WorkIQViewerUrl`, `WorkIQEmulatorEndpoint`, `WorkIQKey`, `WorkIQKeySam`) and download the hack as a ZIP for the `data/documents` and `data/lakehouse` uploads. The most common failure is a corporate account signed in to the portal instead of the lab user: insist on a private window.

Part B ends with opening **Cloud Shell** (Bash, **No storage account required**). Challenges 2, 6 and 7 run `scripts/enable-a2a.py` there. If Cloud Shell is blocked in the tenant, find out now: a teammate with the optional Codespace (on their own fork, billed to their GitHub account) or a local clone with the Azure CLI runs the same script after `az login`.

The optional Codespace or local clone (end of the challenge) is for developers who want to run notebooks 00 and 02. There `create-env.sh` (or `create-env.ps1`) only reads from Azure, finds the lab by the tag `microhack=15_Microsoft_IQ` and writes `.env`.

### Part C: storage browser authentication

Shared key access is off on the storage account. The lab user has **Storage Blob Data Contributor**, so the Storage browser must use **Microsoft Entra user account**. The role can take a minute to apply on a fresh lab.

### Part D: lakehouse gotchas

- Keep **Lakehouse schemas** off. Later challenges expect the tables directly under **Tables**.
- On F2, parallel **Load to Tables** jobs are refused with HTTP 430. Load one file at a time and retry after 20 seconds.
- The Fabric data agent in challenge 3 reads the schema from the **SQL analytics endpoint**, not from the lakehouse view. Opening the endpoint once and selecting **Refresh** avoids "table not found" later.
- The optional notebook `00-load-the-world.ipynb` (Codespace or local clone only) is an equal path: it uploads CSVs to `Files/strandvik/`, loads each table (waiting on HTTP 430), refreshes the SQL endpoint metadata and prints all tables and columns. If the Azure CLI session is gone, the participant runs `az login --use-device-code` in the terminal first.

### Part E: the map is the real deliverable

The map feeds the ontology (challenge 3) and every set of instructions after that. Insist on **owners**: the whole story turns on Sam owning the Rotterdam reservation and Alex owning the Kolvo account.

## Expected results

### Lab dashboard values (differ per lab)

The same values that `create-env.sh` writes to `.env` in the optional Codespace (`.env` name in brackets):

```text
StrandvikProjectEndpoint  https://iq-<hash>.services.ai.azure.com/api/projects/strandvik   (PROJECT_ENDPOINT_STRANDVIK)
KolvoProjectEndpoint      https://iq-<hash>.services.ai.azure.com/api/projects/kolvo       (PROJECT_ENDPOINT_KOLVO)
ModelDeploymentName       gpt-5.4-mini                                                     (MODEL_DEPLOYMENT_NAME)
StorageAccountName        iqst<hash>                                                       (STORAGE_ACCOUNT)
DocumentsContainer        documents                                                        (DOCUMENTS_CONTAINER)
WorkIQEmulatorEndpoint    https://iq-wiq-<hash>....azurewebsites.net/mcp                   (WORKIQ_MCP_URL)
WorkIQViewerUrl           https://.../viewer                                               (WORKIQ_VIEWER_URL)
WorkIQBoardUrl            https://.../board                                                (WORKIQ_BOARD_URL)
WorkIQKey                 <Alex's persona key>                                             (WORKIQ_KEY)
WorkIQKeySam              <Sam's persona key>                                              (WORKIQ_KEY_SAM)
FabricWorkspaceId         <guid, or missing until the workspace exists>                    (FABRIC_WORKSPACE_ID)
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
| Portals show no lab resources | Signed in with the corporate account | Private browser window, sign in with the lab user from the lab dashboard |
| Cloud Shell does not open or is blocked by policy | Tenant policy on Cloud Shell | Plan B for challenges 2, 6 and 7: a teammate runs `enable-a2a.py` from a Codespace on their own fork or a local clone after `az login` |
| No `strandvik-...` workspace in Fabric | The lab could not create it | Create it (name starting with `strandvik`) on `iqcap<hash>` |
| Optional Codespace: `create-env.sh` says "no Microsoft IQ lab found" | Signed in with the wrong account | `az logout`, run again with the lab user, or pass the resource group: `bash create-env.sh <rg>` |
| Storage browser: "This request is not authorized" | Authentication method is access key, or the role is not applied yet | Switch to **Microsoft Entra user account**; wait a minute on a fresh lab |
| **Load to Tables** greyed out | A folder or non-CSV file is selected | Select one CSV file |
| HTTP 430 in Fabric | F2 capacity busy with another load | Wait 20 seconds, retry |
| Fabric items fail or the workspace is read-only | Fabric capacity paused | Azure portal > `iqcap<hash>` > **Resume** |

## Checks for the coach

- [ ] Every team member is in the three portals with the lab user, and Cloud Shell (Bash) opened once.
- [ ] Storage browser: 7 files in `documents`.
- [ ] Fabric: 14 tables, `reservations` preview shows RSV-2291.
- [ ] Ask the team: "Which two SD-900s could replace SD9-K-0412, and who owns the Rotterdam one?" Answer: SD9-P-0981 and SD9-R-0733, owner Sam.

**[Back to Challenge 1](../../challenges/challenge-01.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-02/solution-02.md)
