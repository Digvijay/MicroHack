# Challenge 1: Monitor the portals and build the regulatory lake

**[Home](../README.md)** - [Next Challenge →](challenge-02.md)

## 🎯 Objective

Run Caldova's **Regulatory Web & Change Monitor**, load what it finds into the **regulatory lake** in Azure Blob Storage, and index the lake with **Foundry IQ** so your agents can search it from Challenge 2 onwards.

## 🧭 Context

It is Monday 11 January 2027. Five websites matter to Caldova: the UK, EU and US medicines regulators, a large US health plan and the UK pricing scheme. Nobody has time to read them every day, and when someone does, the same notice often turns up twice.

The monitor does the boring, must-be-exact part **in code**:

1. **Crawls** each allowlisted portal from its home page, follows links inside that portal only and ignores links that leave it.
2. **Normalises** each page: keeps the main text, drops menus and footers, and tidies whitespace.
3. **De-duplicates** by document ID and a fingerprint (hash) of the text. A copy at another address is not a new document.
4. **Versions**: changed text under the same document ID becomes version 2, and version 1 is marked superseded.
5. **Enriches metadata**: region, publisher, document type, dates, impacted domains and any Caldova products named.
6. **Anchors citations**: every paragraph gets a stable label such as `EU-SA-2027-004 v1 p3`.
7. **Raises a change event** for every new or updated document and loads everything into the lake.

Foundry IQ then turns the lake into a **knowledge base**: a search index that returns the best passages, with their source, to any agent that asks.

> [!NOTE]
> The portals are fictional training websites stored in this repository, so everyone gets the same results. Pointing the monitor at real regulator sites is a discussion point in the [finish](finish.md).

## ✅ Tasks

### Part A: Check your Foundry project (5 min)

1. Open [ai.azure.com](https://ai.azure.com) and select **your** project. Match the **Parent resource** to the `FoundryProjectEndpoint` on your lab dashboard.
2. Open **Models → Deployments**. Confirm that the chat model (`ModelDeploymentName`, default `gpt-5.4-mini`) and the embedding model (`EmbeddingDeploymentName`, default `text-embedding-3-small`) both show **Succeeded**.

> 📸 **Screenshot to add:** `images/challenge-01-model-deployments.png`: Models → Deployments with both deployments Succeeded.

### Part B: Run the monitor in Cloud Shell (15 min)

1. In a private browser window, sign in to the [Azure portal](https://portal.azure.com) with your lab account. Open **Cloud Shell** (`>_`) and choose **Bash**. If you are asked about storage, choose the option without storage.
2. Copy only this lab from GitHub and move into it:

   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/MicroHack regintel-microhack
   cd regintel-microhack
   git sparse-checkout set 03-Azure/01-04-AI/11_Healthcare_Regulatory_Intelligence
   cd 03-Azure/01-04-AI/11_Healthcare_Regulatory_Intelligence
   ```

   If your facilitator gives you a branch or tag, add `--branch <name>` after `--sparse`.

3. Check that Cloud Shell uses your lab subscription: `az account show --query name -o tsv`. If not, run `az account set --subscription "<lab subscription>"`.
4. Run Monday's crawl. Replace `<StorageAccountName>` with the value from your dashboard:

   ```bash
   python3 -m regintel --account <StorageAccountName> monitor --day monday
   ```

5. Read the summary. Answer for your team:
   - How many pages were crawled, and how many of them were just index pages?
   - Which document was found twice, and why is it **not** counted as new?
   - Which links were not followed, and why is that a good thing?

> 📸 **Screenshot to add:** `images/challenge-01-monitor-monday.png`: Cloud Shell showing the Monday monitor summary.

### Part C: Look inside the lake (10 min)

1. In the Azure portal, open your storage account → **Storage browser** → **Blob containers**.
2. Open `regulatory-knowledge/change-log.md` (select it, then **Edit** or **Download**). This is the list of everything the monitor found.
3. Open `regulatory-knowledge/documents/EU-SA-2027-004-v1.md`. Find:
   - the metadata the monitor added (region, document type, effective date, impacted domains, products named),
   - the second address under **Also published at**,
   - the paragraph labels `[EU-SA-2027-004 v1 p1]` … `p5`.
4. Browse `regulatory-knowledge/internal/`. These are Caldova's records: products, labels, studies, submissions, SOPs, quality records, market access, owners and history. `tracking/task-register.md` lists the tasks already in progress.
5. Open `lake-raw/events/`. There is one **change event** per new document. In Challenge 6 these events trigger your agents automatically.

> 📸 **Screenshot to add:** `images/challenge-01-storage-browser.png`: Storage browser showing the two containers and the documents folder.

### Part D: Build the Foundry IQ knowledge base (25 min)

1. In the Foundry portal (with the **New Foundry** toggle on), select **Build** in the top menu, then the **Knowledge** tab.
2. When asked, **connect your existing Azure AI Search service** (`SearchServiceName` from the dashboard). Do not create a new one.
3. **Create a knowledge base** named `caldova-regulatory-kb`, adding one knowledge source as follows.
4. **Knowledge source** of type **Azure Blob Storage**:
   - Storage account: `StorageAccountName`; container: **`regulatory-knowledge`** (not `lake-raw`).
   - Authentication: **managed identity** (the system identity of your search service). It already has read access.
   - Embedding model: `EmbeddingDeploymentName`.
   - Name it `caldova-lake`.
5. Knowledge base settings: **retrieval reasoning effort: Minimal** and **output: extractive data** (the raw passages). Your agents do the reasoning. If a chat model is requested, choose `ModelDeploymentName`.
6. **Save** and wait until the knowledge source shows that indexing has **succeeded** (a few minutes). The portal labels can differ slightly; the settings above are what matter.

> 📸 **Screenshot to add:** `images/challenge-01-knowledge-source.png`: creating the Azure Blob Storage knowledge source on the `regulatory-knowledge` container.

> 📸 **Screenshot to add:** `images/challenge-01-knowledge-base-ready.png`: the `caldova-regulatory-kb` knowledge base with indexing succeeded.

### Part E: Discuss (5 min)

Which steps of the monitor would you **never** hand to a language model, and why?

## ✔️ Success criteria

- [ ] The Monday monitor run reports **9 new documents** and **1 duplicate**.
- [ ] You can show the change log, one normalised document with its paragraph labels, and a change event in the lake.
- [ ] `caldova-regulatory-kb` exists, uses the `regulatory-knowledge` container and has finished indexing.
- [ ] You can explain why crawling, de-duplication and versioning are done in code.

## 📚 Learning resources

- [What is Foundry IQ?](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Agentic retrieval in Azure AI Search](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview)

[Coach solution and troubleshooting](../walkthrough/challenge-01/solution-01.md)
