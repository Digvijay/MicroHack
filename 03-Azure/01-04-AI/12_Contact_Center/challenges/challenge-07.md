# Challenge 7: Measure quality

**[← Previous](challenge-06.md)** - [Home](../README.md) - [Next Challenge →](challenge-08.md)

## 🎯 Objective

Stop judging your agent by one good conversation. **Evaluate** it on your company's test questions with Foundry's built-in evaluators, change one setting, evaluate again and decide with evidence which version should go live.

## 🧭 Context

A language model gives slightly different answers each time. An agent that was perfect in your demo may still invent a fee, skip the identity check or answer an off-topic question on the tenth call. Before customers use it, a contact center needs to know **how often** it is right, not **whether** it can be right.

Each industry pack includes ten test questions with the expected answer (`evaluation.jsonl`). They cover facts from the articles, identity checks, things the agent must refuse and an off-topic question. Foundry runs your agent on every question and scores the answers.

## ✅ Tasks

### Part A: Get your test set (5 min)

1. In the Azure portal, open your storage account, then **Storage browser**, then the `evaluation` container, and download `evaluation.jsonl`.
2. Open it in a text editor. Each line has a `query` (what the customer says) and a `ground_truth` (what a good answer contains, with the article). Pick two lines and predict how your agent will do.

### Part B: Run the first evaluation (15 min)

1. In the Foundry portal, open `contact-chat-agent`, then its **Evaluation** tab, and select **Create** (or **New evaluation**).
2. Choose the agent as the target, and upload `evaluation.jsonl` as the dataset. Map `query` to the query and `ground_truth` to the ground truth if asked.
3. Select these evaluators:

   | Evaluator | What it checks |
   |---|---|
   | **Task adherence** | Did the agent follow its instructions? |
   | **Intent resolution** | Did it understand and address what the customer wanted? |
   | **Relevance** | Is the answer on topic? |
   | **Similarity** (or another ground-truth evaluator) | How close is the answer to the expected answer? |
   | **Tool call accuracy** | Did it call the right tools with the right inputs? |

4. Use your `ModelDeploymentName` as the judge model. Name the run `baseline` and start it. It takes a few minutes.

> 📸 **Screenshot to add:** `images/challenge-07-evaluation-setup.png`: the evaluation wizard with contact-chat-agent as target, evaluation.jsonl as dataset and the selected evaluators.

### Part C: Read the results (10 min)

1. Open the `baseline` run. Look at the average score per evaluator, then at the **rows**: which questions scored lowest?
2. Open the lowest-scoring row. Read the agent's answer and the evaluator's reasoning. Is the evaluator right? Evaluators are models too.
3. Look at the identity-check row (the wrong postcode). If the agent shared anything about the account, that is a serious failure whatever the average score says.

> 📸 **Screenshot to add:** `images/challenge-07-evaluation-results.png`: baseline results with average scores per evaluator and the per-question rows.

### Part D: Change one thing and compare (10 min)

1. Change **one** setting on `contact-chat-agent`, save it as a new version, and run the evaluation again with the same dataset and evaluators. Choose one:
   - set **Reasoning Effort** to **medium** (parameters icon next to **Model**), or
   - remove the line *ALWAYS search the knowledge base…* from the instructions.
2. Name the run after the change and **compare** the two runs. Which evaluators moved? Did any single question change from pass to fail?
3. With your team, decide which version you would put live, and what you would need to see before trusting a change on the **voice** agent too.

## ✔️ Success criteria

- [ ] You ran a `baseline` evaluation of `contact-chat-agent` on your company's ten test questions.
- [ ] You can name the lowest-scoring question and explain why it scored low.
- [ ] You changed one setting, re-ran the evaluation and compared the runs.
- [ ] You can explain why one good demo is not evidence, and what you would measure before going live.

## 📚 Learning resources

- [Evaluate agents in Foundry](https://learn.microsoft.com/azure/foundry/observability/quickstarts/quickstart-evaluate-hosted-agent)
- [Agent evaluators](https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/agent-evaluators)

[Coach solution and expected answers](../walkthrough/challenge-07/solution-07.md)
