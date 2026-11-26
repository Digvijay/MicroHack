# Walkthrough Challenge 1: Meet Caldova, the blind agent

**[Home](../../README.md)** - [Coach guide](../README.md) - [Next Solution](../challenge-02/solution-02.md)

**[Back to Challenge 1](../../challenges/challenge-01.md)**

Duration: 30 minutes

## Expected end state

- A Codespace built from the **Azure / AI / Microsoft IQ** dev container. `python --version` is 3.12, `uv --version` and `az --version` work, `src/.venv` exists and `src/.env` was created from `.env.example` by `.devcontainer/post-create.sh`.
- `az login --use-device-code` done with the lab account.
- `src/.env` filled from the dashboard (see the mapping table in the challenge). `FABRIC_WORKSPACE_NAME=caldova-iq` and `STORAGE_CONTAINER=caldova-docs` stay as they are.
- `caldova check` prints every setting (no red `missing`), `workiq key <persona>: set` for all four personas, and `Signed in. Foundry project reachable: N agents`.
- A run `challenge 1: no IQ` on the leaderboard.

## Command sequence (developer path)

```bash
az login --use-device-code
caldova check
caldova ask "Can we ship Brennmark's order by Friday, and what should we tell them?" --iqs none --persona plant-manager
caldova ask "In two sentences, what is a force majeure clause in a commercial supply contract?"
caldova eval --iqs none --label "challenge 1: no IQ"
caldova leaderboard
```

What happens under the hood:

| Command | What it really does |
|---|---|
| `check` | Reads `src/.env` through `config.Settings`, then opens an `AIProjectClient` with `AzureCliCredential` and lists the agents. Proves both the settings and the data-plane role (Azure AI User). |
| `ask --iqs none` | `agent.build()` calls `agents.create_version` for `caldova-plant-manager` with `PromptAgentDefinition(model, instructions, tools=[])`. Then `agent.ask()` gets an OpenAI client bound to that agent and calls `responses.create`. |
| `eval` | Builds one agent version per persona used by the questions (`caldova-sales-lead`, `caldova-supply-planner`, `caldova-plant-manager`), runs 19 questions with 4 workers, scores each, appends to `src/.caldova/leaderboard.json`. |

## Expected answer to the capstone with no IQ

A good blind answer says it cannot confirm Friday: it has no access to stock, the order, the contract, the latest logistics news or what Sales promised. It lists what it would need and which system would know (ERP or lakehouse, contract repository, email). It must **not** invent a quantity or a date. `Tools used: none`.

If the agent invents numbers, show `BASE_INSTRUCTIONS` and the "You have no tools. Answer only from general knowledge." line in `agent.py`, and discuss why that rule matters.

## Expected scores

Only q01 (force majeure in general) and q02 (bill of materials) are designed to pass. Several other questions earn partial judge points for honest "I cannot see that" answers, and q17 (`expect_no_access`) rewards exactly that honesty, so the baseline is not near zero. Use the measured table in the [coach guide](../README.md#expected-scores) rather than a guess.

## The evaluation, explained for coaches

- 19 questions, 10 points each, 190 in total. Scoring is in [`data/eval/rubric.md`](../../data/eval/rubric.md) and `src/caldova/evals.py`.
- 0 to 4 points: `must_include` groups (case-insensitive substring, any alternative passes the group).
- Gate: any `must_not_include` phrase sets the deterministic part to 0 and caps the judge at 1.
- 0 to 5 points: an LLM judge (the same `MODEL_DEPLOYMENT_NAME`) compares with `gold`.
- 1 point: a URL in the answer when `web_citation_required` is true, otherwise free.
- `--upto` limits to earlier challenges, `--only q16,q18` runs a subset. Use the full set for leaderboard comparisons, so every run is out of 190.

## Common issues

| Symptom | Cause and fix |
|---|---|
| `python` or `uv` missing, no `src/.venv` | Codespace created with the default configuration. Recreate with **New with options...** > **Azure / AI / Microsoft IQ**. |
| `caldova: command not found` | The `PATH` line is added to `.bashrc` by `post-create.sh`. Open a new terminal, or run `cd src && uv run caldova check`. |
| `Missing settings in src/.env: ...` | Values not pasted or file not saved. |
| HTTP 401 or 403 on `check` | Wrong account in `az login`, or new role assignments still propagating. Run `az account show`, wait 5 minutes. |
| Encoding errors or boxes instead of `ø`, `å` on Windows | Set `$env:PYTHONIOENCODING='utf-8'`. The dev container already sets `PYTHONIOENCODING=utf-8`. |
| `FabricCapacityName` missing from the dashboard | The lab could not create a Fabric capacity (quota or region). Challenge 3 needs one: see the [coach guide](../README.md#before-the-day). |

## Discussion prompts

- Was the blind answer useful? What makes "I can't know" better than a confident guess?
- Which four systems would a human open to answer the Plant Manager? Map them to the four IQs.
- Why measure the model alone first?

---

**[Home](../../README.md)** - [Coach guide](../README.md) - [Next Solution](../challenge-02/solution-02.md)
