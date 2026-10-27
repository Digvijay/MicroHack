# Challenge 6 solution: Event-driven Regulatory Intelligence Assistant

**[← Previous Solution](../challenge-05/solution-05.md)** - [Home](../../README.md) - [Challenge](../../challenges/challenge-06.md)

**Duration:** 30 minutes (shortcut) or 50 minutes (write it)

## Which path to suggest

Suggest the **shortcut** to anyone who is short on time or does not write Python. They see exactly the same result and still read the code. Suggest **write it** to developers; the three TODOs take about ten lines and teach the Agent Framework building blocks: executors, a builder, edges and the output.

## Write it: the three TODOs

```python
# TODO 1
executors = {
    role: AgentExecutor(
        FoundryAgent(project_endpoint=config.endpoint, credential=credential,
                     agent_name=name, agent_version=versions[role]),
        context_mode="last_agent",
    )
    for role, name in config.names.items()
}
# TODO 2
builder = WorkflowBuilder(start_executor=executors["CITATION"], output_from=[executors["BRIEFING"]])
# TODO 3
builder.add_edge(executors["CITATION"], executors["IMPACT"])
builder.add_edge(executors["IMPACT"], executors["BRIEFING"])
```

A plain `for` loop instead of the dictionary comprehension is fine. The finished file is `orchestrator/workflow.py`.

### What `check_starter.py` says

| Situation | Output |
|---|---|
| Nothing done yet | `NOT YET … TODO 1: create one AgentExecutor per saved agent` |
| TODO 1 done | `NOT YET … TODO 2: create the WorkflowBuilder with a start and an output` |
| TODOs 1 and 2 done | `NOT YET … TODO 3: add the two edges` |
| An edge goes to the wrong agent | `Expected the edges [...]; found [...]` |
| `context_mode` left out (defaults to `full`) | `… should use context_mode='last_agent' so it receives only the previous answer.` |
| Correct | `PASS: orchestrator/starter/workflow.py chains citation -> impact -> briefing correctly.` |

Why `last_agent`? With `full`, every agent receives the whole conversation so far. The briefing agent would then re-read the citation card as well as the impact assessment, which costs more tokens and can lead it to repeat the citation agent instead of summarising the assessment.

## Shortcut: the code tour

Ask shortcut participants to explain stop 4 back to you in one sentence: "Each saved agent is wrapped in an executor; the builder starts at the citation agent, connects citation to impact to briefing, and returns the briefing agent's answer."

## Expected results (both paths)

- Codespace setup ends with all tests passing (for example `43 passed`). This proves the pinned SDK installs and both the finished chain and the checker work, without calling Azure.
- `--event EVT-US-EL-2027-007-v1` prints `Processing EVT-US-EL-2027-007-v1 ...` and `Briefing written: briefings/EVT-US-EL-2027-007-v1.md`, then uploads it.
- Ten events exist after Monday and Tuesday (nine new, one update). With `--limit 3`, run the processor until it prints `No change events are waiting for a briefing.`
- Each briefing starts with a table: **PENDING HUMAN SIGN-OFF**, the event, the region, the time and the agent versions (for example `citation-agent v1, impact-agent v2, briefing-agent v1`).
- In Traces, the `briefing-agent` run receives the impact assessment as its input.

## What our test run produced

The warning-letter event took about a minute and produced a briefing marked **PENDING HUMAN SIGN-OFF** with `citation-agent v3, impact-agent v6, briefing-agent v6`. The reasoning was right: it applies through CMO-17, with `DEV-2026-114`, no second site and the at-risk `TASK-2026-044`. Two things were wrong, and they make a good closing discussion:

- It did not retrieve `SOP-QA-010` this time, so every action fell back to today + 30 days (2027-02-11) instead of 2027-01-26. The same agent got it right when asked directly in Challenge 3: retrieval varies between runs.
- It proposed a *Supply Chain Lead*, a role that is not in `owners.md`. The sign-off tool would refuse that task, so the error cannot reach the task register.

This is why the assistant only ever proposes: a person reviews the briefing and the sign-off tool checks the record.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `starter/workflow.py is not finished yet` | Expected with `--starter` until `check_starter.py` prints PASS |
| `NameError` or `KeyError` in the checker | Usually a typo in a role key; the keys are `CITATION`, `IMPACT` and `BRIEFING` |
| `Agent 'impact-agent' was not found` | The agent name differs; create it with that exact name, or set `IMPACT_AGENT_NAME` in `orchestrator/.env` |
| `FOUNDRY_PROJECT_ENDPOINT must be …` | Copy the endpoint from the dashboard exactly |
| `DefaultAzureCredential failed` | Run `az login --use-device-code` in the Codespace terminal |
| Azure Storage permission error | Wrong subscription or account name; check `az account show` |
| `The workflow returned no briefing` | Open Traces for the three agents; usually one agent without `caldova-regulatory-kb` under Knowledge, or still with Web search |
| Codespace setup failed | Rebuild the container; if it fails again, use the local devcontainer and report the log to the facilitator |
