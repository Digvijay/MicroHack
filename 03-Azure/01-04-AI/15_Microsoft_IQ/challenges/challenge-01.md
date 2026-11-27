# Challenge 1: Lights on

**[Home](../README.md)** - [Next Challenge](challenge-02.md)

**Clock: 02:10** · **Time:** 45 minutes · **Products:** your lab, Azure portal, Foundry portal, Fabric portal

## The story

It's ten past two. At Kolvo's cab plant on Hisingen, the drive unit on press line 2 starts shaking, and the vibration sensors go red. The night shift cuts the press to half speed. That buys time until Thursday morning at 06:00. Then the press stops, and the cab line with it.

Alex is asleep. Alex works at Strandvik Drives, which builds and services the drive units that keep heavy machines running. Customers pay Strandvik for uptime.

In three minutes, Maria's agent will knock on Strandvik's door. Before anyone can answer it, someone has to switch the lights on: know what Strandvik owns, where it is, and **who owns what**. That someone is your team.

## Goal

Your lab is open, your team knows the Strandvik world, and the world's data is where the agents will need it: the documents in Blob Storage and the business tables in a Fabric lakehouse.

## Business task

Map the Strandvik world **on paper** (a whiteboard, a sheet, a Loop page, anything). Use [`data/README.md`](../data/README.md), the CSV files in [`data/lakehouse/`](../data/lakehouse/) and the documents in [`data/documents/`](../data/documents/).

Your map shows at least:

- The **units** that matter tonight (by serial), and where each one is.
- The **machines** they run on, and at which **customer** and **site**.
- The **reservations**, and the **person who owns** each one.
- Who owns the **Kolvo** account and who owns the **Poliden** account.
- One line per agent you expect to build: what it **may** do and what it **may not** do.

Keep the map. You will turn it into an ontology in challenge 3 and into instructions in every challenge after that.

## Builder task

1. Fill `.env` for your lab with `create-env.sh` (or `create-env.ps1` on Windows). Share the three portal links it prints with your team.
2. Open the three portals with your lab user: the **strandvik** and **kolvo** projects in the Foundry portal, your resource group in the Azure portal, and your Fabric workspace.
3. Put the **seven Strandvik documents** into the `documents` container of your lab's storage account.
4. Put the **fourteen CSV files** into a Fabric lakehouse named `strandvik_lakehouse`, each as a table.

You may do steps 3 and 4 by hand in the portals, or with the helper notebook [`notebooks/00-load-the-world.ipynb`](../notebooks/00-load-the-world.ipynb). Both end in the same place.

## Constraints

- Use your **lab user** everywhere. Your own corporate account will not see the lab.
- Build in the **strandvik** project only. The **kolvo** project belongs to Kolvo: look, don't touch.
- Do not rename the documents or the tables. Later challenges (and the evaluation set) expect these names.
- Never commit `.env`. It holds your Work IQ keys.

## Success criteria

- [ ] `.env` exists and `PROJECT_ENDPOINT_STRANDVIK`, `STORAGE_ACCOUNT`, `WORKIQ_VIEWER_URL` and `WORKIQ_KEY` have values.
- [ ] The coach sees 7 `.md` files in the `documents` container (Azure portal > storage account > Storage browser).
- [ ] The coach sees 14 tables in `strandvik_lakehouse` in Fabric, and a preview of `reservations` shows `RSV-2291`.
- [ ] Your paper map answers, without a laptop: *Which unit runs press line 2? Which two SD-900s could replace it? Who owns the Rotterdam one?*
- [ ] Every team member can open the Kolvo project and see `maria-procurement`.

## Hints

<details>
<summary>Hint 1: Where do I start?</summary>

In a Codespace (dev container **Azure / AI / Microsoft IQ**), open a terminal in the hack folder and run `bash create-env.sh`. It signs you in once with a device code and only reads from Azure. At the end it prints the links you need.

</details>

<details>
<summary>Hint 2: No Fabric workspace?</summary>

The lab tries to create a workspace named `strandvik-...` for you. If `create-env.sh` says there is none, create a workspace in the Fabric portal, assign it to your lab's Fabric capacity (`iqcap...`), then run `create-env.sh` again so `FABRIC_WORKSPACE_ID` is filled.

</details>

<details>
<summary>Hint 3: Loading tables in the Fabric portal</summary>

Create the lakehouse, upload the CSV files to **Files**, then use **Load to Tables** on each file. On a small F2 capacity a load can be refused with HTTP 430 when another load is still running: wait a few seconds and try again. If a new table is missing in the SQL analytics endpoint, refresh its metadata.

</details>

<details>
<summary>Hint 4: Reading the map</summary>

Start from `machines.csv` (press line 2 is `KOL-PL2`), follow `drive_unit_serial` into `drive_units.csv`, then look for SD-900s with status `in_stock`. For each one, check `reservations.csv` and follow `owner_person_id` into `people.csv`. Watch out: not every SD-900 on a shelf is free, and not every drive unit fits a press.

</details>

## Learning resources

- [What is Microsoft Foundry Agent Service?](https://learn.microsoft.com/azure/ai-foundry/agents/overview)
- [Upload, download and list blobs in the Azure portal](https://learn.microsoft.com/azure/storage/blobs/storage-quickstart-blobs-portal)
- [Lakehouse: Load to Delta Lake tables](https://learn.microsoft.com/fabric/data-engineering/load-to-tables)
- [What is Fabric IQ?](https://learn.microsoft.com/fabric/iq/overview)

**[Home](../README.md)** - [Next Challenge](challenge-02.md)
