# Challenge 1: Meet Caldova, the blind agent

**[Home](../README.md)** - [Next Challenge](challenge-02.md)

**Time:** 30 minutes. **IQ:** none.

## Story beat

It is Monday 7 December 2026, 08:00, in Borås. The Plant Manager walks in with a coffee and one question: "Can we ship Brennmark's order by Friday, and what should we tell them?" You open a brand new AI agent and type the question. The agent has a frontier model, but nothing else. It does not know about the storm, the stock, the contract or the promise Sales made last Thursday. Today you find out what an agent without context can do, and what it cannot.

## What you learn

- How to set up your workspace: the Codespace, the sign-in and the lab values.
- What a Foundry prompt agent is: a model, instructions and (soon) tools.
- Why a good model without context gives an honest "I can't know", and why that is the right behaviour.
- How the 19 evaluation questions and the leaderboard measure your progress all day.

## Feature status

| Feature | Status |
|---|---|
| Foundry prompt agents (Foundry Agent Service) | GA |
| Agent playground in the Foundry portal | GA |

See [What is GA and what is preview](../README.md#what-is-ga-and-what-is-preview) for the full table.

## Set up your workspace (everyone, 15 min)

Both paths use the Codespace terminal for the scoring step, so everyone sets it up once. Business participants can use it only as a terminal.

### 1. Start the Codespace

1. Sign in to GitHub with your lab account and open the hack repository your coach shares.
2. Select **Code** > **Codespaces** > **...** > **New with options...**.
3. Under **Dev container configuration**, choose **Azure / AI / Microsoft IQ**. Select **Create codespace**.
4. Wait until the terminal prints `Ready. Next steps`. The setup installs Python 3.12, `uv`, the `caldova` command line, and creates `src/.env`.

> [!TIP]
> If `caldova` is not found, open a new terminal (the setup adds it to your `PATH`), or run `cd src && uv run caldova --help`.

### 2. Sign in to Azure

```bash
az login --use-device-code
```

Open the link, enter the code and sign in with your **lab account** (not your personal or work account). If you are asked for a subscription, pick the one on your lab dashboard.

### 3. Paste your lab values into `src/.env`

Open `src/.env` in the editor. Copy each value from your lab dashboard:

| Dashboard credential | `src/.env` variable |
|---|---|
| Subscription ID | `AZURE_SUBSCRIPTION_ID` |
| Resource Group Name | `AZURE_RESOURCE_GROUP` |
| FoundryProjectEndpoint | `PROJECT_ENDPOINT` |
| ModelDeploymentName | `MODEL_DEPLOYMENT_NAME` |
| GraphModelDeploymentName | `GRAPH_MODEL_DEPLOYMENT_NAME` |
| EmbeddingDeploymentName | `EMBEDDING_DEPLOYMENT_NAME` |
| SearchEndpoint | `SEARCH_ENDPOINT` |
| StorageAccountName | `STORAGE_ACCOUNT_NAME` |
| StorageContainer | `STORAGE_CONTAINER` |
| FabricCapacityName | `FABRIC_CAPACITY_NAME` |
| WorkIQEmulatorEndpoint | `WORKIQ_ENDPOINT` |
| WorkIQKeySalesLead | `WORKIQ_KEY_SALES_LEAD` |
| WorkIQKeySupplyPlanner | `WORKIQ_KEY_SUPPLY_PLANNER` |
| WorkIQKeyQualityHead | `WORKIQ_KEY_QUALITY_HEAD` |
| WorkIQKeyPlantManager | `WORKIQ_KEY_PLANT_MANAGER` |

Keep `FABRIC_WORKSPACE_NAME=caldova-iq`. You use `FoundryProjectUrl`, `FabricPortalUrl` and `WorkIQViewerUrl` in the browser, not in the file.

> [!IMPORTANT]
> `src/.env` holds your Work IQ keys. Never commit it. It is already in `.gitignore`.

### 4. Check the setup

```bash
caldova check
```

You see a table of your settings (none should say `missing`) and the line `Signed in. Foundry project reachable`.

## Business path (portal, no code)

1. Open `FoundryProjectUrl` from your dashboard, or go to [ai.azure.com](https://ai.azure.com) and open the `caldova-iq` project. Sign in with your lab account.
2. Select **Agents** > **Create agent**. Name it `caldova-portal`. Choose the model `gpt-5.4-mini`.
3. Paste these instructions:

   ```text
   You are the operations assistant of Caldova Components AB, a Swedish maker of industrial
   valves (plant in Boras). Today is Monday 7 December 2026, 08:00 CET. "Friday" means 11 December 2026.
   Answer in short, plain business English. Show the numbers you used.
   Never invent facts, names, quantities or dates. If you do not have a source for something, say what you
   could not find and which system would know it.
   ```

4. Look at **Tools** and **Knowledge**. If the new agent already has a **Web search** tool, remove it for now. You add it back in Challenge 2.
5. Save, open the **playground** and ask the Plant Manager's question:

   ```text
   Can we ship Brennmark's order by Friday, and what should we tell them?
   ```

6. Read the answer. A good blind agent says it does not have the stock, the order, the contract or the latest news, and tells you which system would know. It does not invent a number.

## Developer path (Codespace)

1. Ask the agent the Plant Manager's question with no IQ:

   ```bash
   caldova ask "Can we ship Brennmark's order by Friday, and what should we tell them?" --iqs none --persona plant-manager
   ```

   `--iqs none` creates a new version of the prompt agent `caldova-plant-manager` with no tools, then asks it through the Responses API. The last line, `Tools used: none`, proves it.

2. Open [`src/caldova/agent.py`](../src/caldova/agent.py) and find:
   - `BASE_INSTRUCTIONS`: the same text as the business path. Note the last rule: never invent, say what you could not find.
   - `instructions(iqs)`: with no IQ, the agent is told "You have no tools. Answer only from general knowledge."
   - `build()`: `PromptAgentDefinition(model, instructions, tools)` and `create_version`. Every `--iqs` change makes a new agent version, so you can compare versions in the portal.
3. Ask a general knowledge question. It should do fine:

   ```bash
   caldova ask "In two sentences, what is a force majeure clause in a commercial supply contract?"
   ```

## Evaluate (both paths)

The evaluation asks the agent **19 questions** ([`data/eval/questions.json`](../data/eval/questions.json)) and scores each from 0 to 10, so the maximum is 190.

| Questions | Challenge | What they need |
|---|---|---|
| q01, q02 | 1 | General knowledge only |
| q03 to q05 | 2 | Live web (weather, exchange rate, holidays), with citations |
| q06 to q09 | 3 | Business data: stock, orders, money |
| q10 to q13 | 4 | Contracts and policies |
| q14 to q17 | 5 | Emails, chats, meetings, and who may see them |
| q18, q19 | 6 | All four IQs. q19 continues the q18 conversation. |

Each answer gets up to 4 points for required facts, up to 5 from an AI judge that compares it with the reference answer, and 1 grounding point when the agent actually used the IQ the question needs (with a cited URL for web questions). Dangerous answers, such as "4,000 by Friday", lose the fact points and are capped by the judge.

Run the baseline in the Codespace terminal (business participants: run it yourself, or ask your developer teammate or coach):

```bash
caldova eval --iqs none --label "challenge 1: no IQ"
```

Then show the leaderboard:

```bash
caldova leaderboard
```

Expect a **low** score. Only q01 and q02 pass fully. Honest "I cannot know" answers earn a few judge points, so the total is not zero. You run the same command after every challenge, with one more IQ each time, and watch the bar grow.

## Success criteria

- [ ] `caldova check` shows no `missing` value and reaches your Foundry project.
- [ ] Your agent (portal or code) answers the Plant Manager's question without inventing numbers.
- [ ] You can explain why it cannot answer: it has no source for stock, contracts, news or promises.
- [ ] The leaderboard shows a run called `challenge 1: no IQ`.

## Value card

| What this IQ is | What it fixed today | Where customers use it |
|---|---|---|
| No IQ yet: a frontier model with instructions only. | Nothing, on purpose. It set the baseline and showed that honesty ("I can't know") beats a confident guess. | Every agent project starts here. Measure the model alone first, so you can prove what each source of context adds. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `caldova: command not found` | Open a new terminal, or run `cd src && uv run caldova check`. Check that you created the Codespace with **New with options...** and the **Azure / AI / Microsoft IQ** configuration. |
| `Missing settings in src/.env: ...` | Paste the named values from the dashboard. Save the file. |
| `AzureCliCredential` or `Please run 'az login'` | Run `az login --use-device-code` again with the lab account. |
| HTTP 401 or 403 from the Foundry project | You signed in with the wrong account, or the role assignment is still new. Wait 5 minutes and retry. |
| Strange characters in the output on Windows | Set `PYTHONIOENCODING=utf-8`. The Codespace already sets it. |

## Learning resources

- [Microsoft IQ documentation](https://learn.microsoft.com/en-us/microsoft-iq/)
- [Agent optimizer in Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-optimizer-overview) (you use it in Challenge 6)

---

**[Home](../README.md)** - [Next Challenge](challenge-02.md)
