# Challenge 1 — Meet the Models

**[Home](../README.md)** - [Next Challenge →](challenge-02.md)

## 🎯 Objective

Find out what a **decision model** is by asking one the same questions as a chat model, about
real marketplace listings — and seeing what comes back.

## 🧭 Context

Zava Marketplace opens to sellers tomorrow. Every listing goes through the **Listing Gate**,
which asks nine small questions about it — *Is this a prohibited item? Does the photo match the
title? Is there text aimed at the reviewer?* — and turns the answers into one outcome: **publish**,
**auto-fix** (correct the category), **review** (a person decides) or **reject**.

The answers come from **decision models**. A decision model doesn't write. It answers a closed
question with a **probability for every possible answer**, in a single pass:

| Question type | Example | What comes back |
|---------------|---------|-----------------|
| **Yes / no** | *Does the listing ask shoppers to pay outside the marketplace?* | P(yes) = 0.98 |
| **Choice** | *Which category does this product belong to?* | `garden_and_lawn` 97%, `lighting` 1%, … |
| **Score** | *How useful is this listing to a shopper?* Unusable → Excellent | Most likely *Good*, with a probability per level |

You'll compare three ways of asking the same nine questions:

| In the console | Model | API |
|----------------|-------|-----|
| Microsoft-Decision-1.1 | Microsoft's decision model (generally available) | `/providers/microsoft/v1/systemone` |
| gpt-6-luna · Decisions API | OpenAI's model, used as a decision model | `/openai/v1/decisions` |
| gpt-6-luna · chat | The **same** deployment, used as a normal chat model | Responses API, JSON output |

## ✅ Tasks

### 🧭 Explore

#### Part A — Open the console (5 min)

1. On your Hackbox, find **ConsoleUrl** and **AccessCode**. Open the URL in your browser and
   enter the code.
2. Check the three lights at the top: **Microsoft-Decision-1.1**, **gpt-6-luna Decisions API**
   and **gpt-6-luna Responses API (chat)** should all be green. Hover over a light to see how
   long the model took to answer.
3. Read the lesson banner at the top of tab **1 · Meet the models**.

#### Part B — Predict, then ask three models (20 min)

1. In **Seller listings**, click **ZM-0050** — a smart-plug listing. Read the description to the
   end and the **manufacturer facts** below it.
2. **Predict:** what should the gate do with this listing? Pick an outcome in the drop-down.
   Not sure? Open the **Listing Policy** link.
3. **Try:** click **Ask all three models**.
4. **See:** for each model, look at
   - the **outcome** the gate's rules chose, and the reason;
   - the **probability bars** — which questions is each model sure about?
   - **tokens in/out** — how many words did each model write?
   - the line above the cards: did your prediction match the answer key?
5. Open **Show me the code** on two of the cards. Compare the request sent to
   Microsoft-Decision-1.1 with the one sent to the Decisions API. How is the yes/no question
   named in each (`noul` or `predicate`)?
6. Repeat with **ZM-0072** (a weedkiller) and **ZM-0056**. Predict first each time.

#### Part C — Ask your own questions (15 min)

With a listing selected, use **Ask your own question**. Click the examples to fill the form, or
write your own:

1. **Yes/no** — *"Is this product meant to be used outdoors?"* Try it on the garden hose
   **ZM-0005** and on the desk lamp **ZM-0186**.
2. **Choice** — *"What is the product mainly made of?"* with `metal, plastic, wood, fabric,
   cannot tell`. Look at the probability of **every** option, not only the winner.
3. **Score** — *"How expensive does this product seem for its type?"* with `cheap, average,
   premium` (lowest first).
4. Ask the same question to both decision models. Do they agree? Are they equally sure?

> [!NOTE]
> A yes/no probability close to **0** is a confident **no**, not an unsure answer. "Unsure" is
> a probability near the middle.

#### Part D — Where would I use this? (5 min)

Scroll to the **Where would I use this?** card. Write down one decision in your own work that a
decision model could make — a yes/no, a choice or a score — and click **Save**.

### 🛠️ Build *(optional, for developers)*

Set up the code once; you'll use it in every challenge.

1. In the [Azure portal](https://portal.azure.com), signed in with your lab account, open
   **Cloud Shell** (the `>_` icon) and choose **Bash**. When asked about storage, **mount your
   lab's file share** so your work survives breaks:
   1. Choose **Mount storage account**, pick your lab subscription and select **Apply**.
   2. Choose **Select existing storage account** and select **Next**.
   3. Pick your **ResourceGroupName**, the storage account **CloudShellStorage** from your
      Hackbox, and the file share **`cloudshell`**. Select **Select**.

   > [!IMPORTANT]
   > Cloud Shell recycles its machine after **20 minutes without input** — a lunch break is
   > enough. With the file share mounted, everything in your home folder (the clone, `.venv` and
   > `.env`) is still there when you come back. Without it, you start from scratch.
   >
   > Used Cloud Shell before without storage? Open **Settings → Reset User Settings** first, and
   > you'll get the storage question again.
2. Get the hack and install it:
   ```bash
   cd ~
   git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/MicroHack.git
   cd MicroHack && git sparse-checkout set 03-Azure/01-04-AI/14_Decision_Models_Retail_Marketplace
   cd 03-Azure/01-04-AI/14_Decision_Models_Retail_Marketplace/src
   python3 -m venv .venv && source .venv/bin/activate
   pip install -q -r requirements.txt
   cp ../.env.example .env && code .env
   ```
3. In `.env`, paste `DecisionEndpoint` and `OpenAIEndpoint` from your Hackbox, save, and check:
   ```bash
   python -m gate check
   ```
   Cloud Shell is already signed in as your lab account, so there are no keys and no `az login`.

   > [!TIP]
   > **Back from a break?** A new Cloud Shell session starts in your home folder. Run
   > `cd ~/MicroHack/03-Azure/01-04-AI/14_Decision_Models_Retail_Marketplace/src && source .venv/bin/activate`
   > and carry on — your files are on the mounted share.
4. **Call the API yourself.** Save this as `first.py` and run `python first.py`:
   ```python
   import httpx, config
   from azure.identity import DefaultAzureCredential

   token = DefaultAzureCredential().get_token("https://cognitiveservices.azure.com/.default").token
   body = {
       "model": config.DECISION_DEPLOYMENT,
       "state": "Garden hose 30 m, brass connector. For a quick deal call me on 0612 345 678.",
       "questions": {
           "contact": {"type": "noul", "instructions": "Does the text ask the buyer to contact the seller outside the marketplace?"},
           "category": {"type": "choice", "instructions": "Which category fits the product?",
                        "criteria": {"garden": "Garden products", "kitchen": "Kitchen products", "other": "Anything else"}},
       },
   }
   r = httpx.post(f"{config.DECISION_ENDPOINT}/providers/microsoft/v1/systemone",
                  headers={"Authorization": f"Bearer {token}"}, json=body)
   print(r.json())
   ```
5. Run the same listing through the gate from the command line:
   `python -m gate ask ZM-0050 --model decision luna llm --show-answer`
6. Open [`gate/clients.py`](../src/gate/clients.py) and find `systemone_question` and
   `decisions_question`. List three differences between the two request formats.

## 🏁 Success criteria

- [ ] The console opens and all three lights are green.
- [ ] You predicted the outcome for at least three listings and compared with the answer key.
- [ ] You can explain the difference between what a decision model and a chat model return.
- [ ] You asked your own yes/no, choice and score question and can explain each probability.
- [ ] You saved a **Where would I use this?** card.
- [ ] *(Build)* `python -m gate check` prints **All good** and your own script returned typed answers.

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| The console asks for the code again and again | Use the **AccessCode** from your Hackbox exactly; it's case-sensitive. Allow cookies for the site. |
| A light is red | Hover over it to see the error. Shortly after the lab is created, permissions can take a few minutes to arrive — reload after a minute. |
| A card shows `HTTP 429` | Too many requests for your deployment's capacity. Wait a minute and try again. |
| *(Build)* `DECISION_ENDPOINT is not set` | Paste the values into `src/.env` (not `.env.example`). |
| *(Build)* `pip install` is slow or fails | Cloud Shell needs internet access to PyPI. Retry once; the packages take about a minute. |
| *(Build)* My files are gone after a break | Cloud Shell started without storage. Open **Settings → Reset User Settings**, mount **CloudShellStorage** as in step 1, and repeat step 2 — it takes two minutes. |
| *(Build)* The storage account isn't in the list | Choose your lab subscription and **ResourceGroupName** first. If there's no **CloudShellStorage** on your Hackbox, your tenant blocks mounting: use a session without storage and repeat step 2 after each break. |
| *(Build)* `401` or `403` from your script | Check `az account show` shows your lab account. |

## 🧠 Reflection

- The chat model also answered every question. What can't you do with its answers that you can
  do with a probability?
- The decision models wrote almost no output tokens. Why does that matter at thousands of
  listings a day?
- Microsoft uses Microsoft-Decision-1.1 to route Copilot requests. What small, high-volume
  decision in your organisation looks like that?

## 📚 Learning resources

- [Decision models — Microsoft Foundry primer](https://github.com/microsoft-foundry/model-releases/blob/main/3-primers/decision-models.md)
- [Deploy and use Microsoft-Decision-1.1 in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision)
- [Introducing Microsoft-Decision-1.1 — quickstarts](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/introducing-microsoft-decision-1-1-build-faster-more-efficient-ai-applications-w/4573877)
- [Use the Azure OpenAI Decisions API](https://learn.microsoft.com/azure/foundry/openai/how-to/decisions)
- [Persist files in Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/persisting-shell-storage)
