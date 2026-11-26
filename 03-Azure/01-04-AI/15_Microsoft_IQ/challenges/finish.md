# Finish: one agent, four IQs

**[Home](../README.md)** - [Previous Challenge](challenge-06.md)

## Story beat

11:00. The escalation call starts. The Plant Manager does not promise 4,000 by Friday. Caldova offers 1,800 PV-400 by Friday 11 December and the remaining 2,200 by 18 December, sends the force majeure notice well before Wednesday 9 December 08:00, and asks Brennmark to confirm the partial delivery in writing. Nobody suggests the backup supplier. The answer came from four places, and your agent found all of them.

## Recap

Fill in the last column from `caldova leaderboard`.

| IQ | What it added | Questions it unlocked | Your score after this challenge |
|---|---|---|---|
| None (Challenge 1) | A baseline, and an honest "I can't know" | q01, q02 | |
| **Web IQ** (Challenge 2) | Live, cited facts from outside: weather, rates, holidays | q03 to q05 | |
| **Fabric IQ** (Challenge 3) | Stock, buildable quantity, affected orders and money at risk | q06 to q09 | |
| **Foundry IQ** (Challenge 4) | Contracts, policies and a graph of who depends on whom | q10 to q13 | |
| **Work IQ** (Challenge 5) | Promises, decisions and partner news, trimmed per person | q14 to q17 | |
| **Microsoft IQ + playbook** (Challenge 6) | One decision from all four sources, and a message ready to send | q18, q19 | |

Three lessons to take home:

1. **Context beats model size.** The model did not change all day. The context did.
2. **Permissions are part of the answer.** Who asks changes what the agent can know, and that is a feature.
3. **Measure every change.** An evaluation set turns "it feels better" into a number, and catches regressions such as a broken promise copied into a customer email.

## Where would you use this?

Discuss in your team, by role:

| Role | Prompt |
|---|---|
| Business leader | Which weekly decision in your area needs numbers, rules, people and outside news at once? |
| Data owner | Which tables would become your first Fabric data agent? What example queries would it need? Which entities and relationships belong in an ontology? |
| Knowledge or legal owner | Which documents would go into a knowledge base first? Which relationships would you want in a graph? |
| IT and security | Which permissions must the agent respect? How do you treat retrieved content as untrusted? Which data may leave your compliance boundary through web search? |
| Developer | Which tools would you publish once, as a toolbox, and reuse in several agents? What goes into your evaluation set? |

## Take it home

- **Work IQ:** point `WORKIQ_ENDPOINT` at `https://workiq.svc.cloud.microsoft/mcp` and use a Microsoft Entra user connection in a tenant with Microsoft 365 Copilot. See the [Work IQ overview](https://learn.microsoft.com/en-us/microsoft-365/copilot/extensibility/work-iq/).
- **Fabric IQ:** start with one lakehouse and one data agent with good example queries, then add an ontology. See [What is Fabric IQ?](https://learn.microsoft.com/en-us/fabric/iq/overview) and [Connect agents to Fabric with Fabric IQ](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/fabric-iq).
- **Foundry IQ:** start with a knowledge base over a small, clean set of documents. See [What is Foundry IQ?](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq).
- **Web IQ:** start with the web search tool, then add scopes for trusted sources. See the [Web IQ overview](https://learn.microsoft.com/en-us/web-iq/overview).
- **All of it:** [Microsoft IQ documentation](https://learn.microsoft.com/en-us/microsoft-iq/).

The `caldova` code in [`src/caldova`](../src/caldova) is a small, readable reference for every call: copy the parts you need.

## Cleanup

- **Pause the Fabric capacity** if your lab stays up after today: Azure portal > your resource group > the Fabric capacity > **Pause**. It is the largest cost item and is billed only while running.
- Stop your Codespace (**Codespaces** > **...** > **Stop codespace**), and delete it when you no longer need it.
- Do not commit `src/.env`. It holds your Work IQ keys.
- The lab platform deletes your resource group when the event ends. All Caldova data is fictional.

## Feedback

Tell your coach one thing that worked and one thing to improve. Which IQ surprised you most, and which teaching moment will you reuse with your own team?

Thank you for taking part.

---

**[Home](../README.md)** - [Previous Challenge](challenge-06.md)
