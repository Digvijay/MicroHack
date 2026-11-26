# Microsoft IQ: one agent, four IQs

Welcome to the **Microsoft IQ** MicroHack. You build one AI agent for **Caldova**, a valve manufacturer with a problem on Monday morning. In each challenge you give the agent one more part of **Microsoft IQ**: the outside world (**Web IQ**), the business data (**Fabric IQ**), the company's knowledge (**Foundry IQ**) and how its people work (**Work IQ**). After every challenge, a scoreboard shows how much smarter the agent got, and why.

> **Tech talk:** open the day with [Into focus](techtalk/README.md), a 23-minute animated talk for this hack.

The hack has two paths. You can take either one, and switch at any time:

- **Business path:** build in the portals (Foundry, Fabric, the Work IQ viewer). No code.
- **Developer path:** build in a Codespace with Python and REST, and see every API call.

Both paths build the same agent and are scored on the same questions.

- [**Why Microsoft IQ**](#why-microsoft-iq)
- [**Learning objectives**](#learning-objectives)
- [**Scenario**](#scenario)
- [**Architecture**](#architecture)
- [**What is GA and what is preview**](#what-is-ga-and-what-is-preview)
- [**Requirements**](#requirements)
- [**Challenges**](#challenges)
- [**Glossary**](#glossary)
- [**Repository layout**](#repository-layout)
- [**Contributors**](#contributors)

## Why Microsoft IQ

Every company can use the same frontier models. What makes an agent useful is **context**: what is happening outside, what the numbers say, what the rules are and what people already promised. Microsoft IQ is the layer that gives agents that context, with the permissions of the person asking:

| IQ | What it knows | The question it answers for Caldova |
|---|---|---|
| **Web IQ** | The live web: news, weather, places, public facts | Is the port of Esbjerg really closed? Which public holidays fall before the deadline? |
| **Fabric IQ** | The state of the business: governed data, entities, relationships, rules | How many valves can we build by Friday? How much revenue is at risk? |
| **Foundry IQ** | Curated institutional knowledge: contracts, policies, reports | Does a port closure count as force majeure? May we use the backup supplier? |
| **Work IQ** | How people work: emails, chats, meetings, files | What did Sales promise the customer? What did the customer say they would accept? |

None of them can answer Caldova's real question alone. Together they can.

## Learning objectives

By the end of this MicroHack you can:

- Explain what each of the four IQs adds, and when to use which one.
- Ground an agent in live web results, with citations (**Web IQ**).
- Turn business tables into a governed **Fabric data agent** and an **ontology**, and connect them to an agent (**Fabric IQ**).
- Build a **knowledge base** with agentic retrieval, extract a **knowledge graph** with your own ontology, and compare the two (**Foundry IQ**).
- Use the **Work IQ** MCP contract, and see how permission trimming changes what an agent can know.
- Combine all four in one agent, measure it with **evaluations**, and improve it with the **Agent Optimizer**.

## Scenario

> **Monday 7 December 2026, 08:00, Borås, Sweden.**
> A storm has closed the port of Esbjerg. A container with 3,500 valve housings for Caldova is stuck there. Caldova's biggest customer, Brennmark Industries, needs 4,000 PV-400 pump valves by **Friday**. Last Thursday, Sales promised the full order.
>
> The Plant Manager asks: **"Can we ship by Friday, and what do we tell Brennmark?"**

**Caldova Components AB** is a fictional, mid-size Swedish maker of industrial valves. Its people appear only by role: Sales Lead, Supply Planner, Quality Head and Plant Manager.

The answer is spread across four places:

- The **web** knows about the storm and the holidays.
- The **lakehouse** knows the stock, the orders and which products use which parts.
- The **contracts and policies** know the force majeure clause, the partial delivery rule and why the backup supplier cannot be used.
- The **emails and chats** know what Sales promised, what the customer will accept and what the Quality Head decided on Friday.

The scenario is a vehicle, not the goal. The goal is to see, step by step, what each IQ adds.

![Caldova scenario: one question, four sources](images/readme-scenario.png)

## Architecture

![Architecture: one Foundry agent with four IQ tools](images/readme-architecture.png)

| Component | Role in the hack |
|---|---|
| **Foundry Agent Service** | Hosts the Caldova agent (a prompt agent with `gpt-5.4-mini`), runs evaluations and the Agent Optimizer. |
| **Web IQ** (web search tool) | Live web grounding with citations. |
| **Fabric IQ**: lakehouse, data agent and ontology | Caldova's tables in OneLake. A **data agent** answers questions over them. The **ontology** names the business entities (Supplier, Component, Product, Customer, Order) and their relationships. The agent reaches them through the **Fabric IQ tool**, as the signed-in user. |
| **Foundry IQ** (Azure AI Search) | A **knowledge base** over Caldova's contracts and policies (agentic retrieval), and a **knowledge graph** extracted from the same documents with your ontology. The agent reaches both through MCP. |
| **Work IQ** (emulator) | The lab runs a Work IQ emulator with the **same MCP contract** as Microsoft 365 Work IQ: `retrieve`, `fetch`, `ask` and the schema tools, with emails, chats, meetings and files for four personas. A viewer lets you read the mailbox the agent searches. |
| **Codespace** | Python 3.12, `uv`, the `caldova` command line and the evaluation leaderboard. |

> **Why an emulator for Work IQ?** Real Work IQ needs Microsoft 365 Copilot licenses and tenant admin consent, which a lab tenant does not have. The emulator speaks the exact same protocol, so the agent and the code are the same. Only the URL and the sign-in change. See [the emulator's README](labautomation/workiq-emulator/README.md) for what it does and does not emulate.

## What is GA and what is preview

This hack showcases what Microsoft announced at Ignite 2026. Each challenge marks every feature as **GA** or **Preview**.

| Feature | Status | Challenge |
|---|---|---|
| Foundry prompt agents, multi-turn evaluation, Agent Optimizer, Insights | GA | 1, 6 |
| Web search tool (Web IQ) in Foundry agents | GA | 2 |
| Fabric data agent, Fabric IQ MCP | GA | 3 |
| Fabric IQ ontology, Fabric IQ tool in Foundry | Preview | 3 |
| Foundry IQ knowledge bases (agentic retrieval) | GA | 4 |
| Foundry IQ knowledge graph (entity graph) | Preview | 4 |
| Work IQ MCP server (retrieve) | GA per Ignite blog, preview per MCP docs | 5 |

## Requirements

- A lab from the MicroHack platform. It provides a resource group with Foundry, Azure AI Search, storage, a Fabric capacity and the Work IQ emulator. See [labautomation/README.md](labautomation/README.md).
- A GitHub account with Codespaces (developer path), or a browser (business path).
- Your lab sign-in has a Fabric license (the lab adds it).
- **Coaches:** read [walkthrough/scenario-facts.md](walkthrough/scenario-facts.md) before the day. It is the single source of truth for every number.

## Challenges

| # | Challenge | IQ | Time |
|---|---|---|---|
| 1 | [Meet Caldova: the blind agent](challenges/challenge-01.md) | none | 30 min |
| 2 | [Look outside: Web IQ](challenges/challenge-02.md) | Web IQ | 40 min |
| 3 | [Know the business: Fabric IQ](challenges/challenge-03.md) | Fabric IQ | 60 min |
| 4 | [Know the rules: Foundry IQ](challenges/challenge-04.md) | Foundry IQ | 60 min |
| 5 | [Know the people: Work IQ](challenges/challenge-05.md) | Work IQ | 60 min |
| 6 | [One agent, four IQs](challenges/challenge-06.md) | Microsoft IQ | 60 min |
| | [Finish](challenges/finish.md) | | |

Plan about **6 hours** with breaks (5 hours 10 minutes of challenges). Stretch goals are at the end of challenges 3, 4 and 6.

## Glossary

| Term | Meaning |
|---|---|
| **Agent** | An AI model with instructions and tools. It decides which tool to call to answer a question. |
| **MCP** | Model Context Protocol, the open standard agents use to call tools on a server. Work IQ, Foundry IQ and Fabric IQ all speak MCP. |
| **Ontology** | A model of your business: entity types (Supplier, Product), their properties and the relationships between them. Fabric IQ binds it to tables. Foundry IQ uses one to extract a graph from documents. |
| **Knowledge base** | A Foundry IQ object that plans a search across one or more knowledge sources and returns grounded content with citations. |
| **Knowledge graph** | Entities and relationships extracted from documents. You query it with natural language or GQL. |
| **Persona** | A role at Caldova (Sales Lead, Supply Planner, Quality Head, Plant Manager). Work IQ only returns what that person can see. |
| **Evaluation** | A fixed set of questions with reference answers, scored automatically after every challenge. |

## Repository layout

```text
15_Microsoft_IQ/
├── challenges/          Challenge pages (both paths)
├── walkthrough/         Coach solutions and the scenario facts
├── data/                Lakehouse tables, documents, ontologies, evaluation questions
├── src/                 The caldova command line and agent code (developer path)
├── labautomation/       Lab provisioning and the Work IQ emulator
└── images/              Diagrams
```

## Contributors

- Digvijay Chauhan, Solution Engineer, Microsoft
