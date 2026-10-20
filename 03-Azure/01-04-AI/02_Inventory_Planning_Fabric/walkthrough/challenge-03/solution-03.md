# Challenge 3 — Solution: Inventory Optimisation Agent

**[← Previous](../challenge-02/solution-02.md)** - [Home](../../README.md) - [Next Solution →](../challenge-04/solution-04.md)

**Duration:** 60 minutes

## Goal

Build the Inventory Optimisation Agent and use agent tracing to inspect its reasoning.

## Solution walkthrough

### Agent — key configuration point

Select dashboard **ModelDeploymentName** (default `gpt-5.4-mini`), including when
the facilitator has configured a fallback.

This agent should have **only Fabric IQ**, connected to the published `inventory-hack-agent` — no Web Search. Remove any default Web Search tool. Select the Data Agent through the OneLake Catalog as in Challenge 2, complete OAuth consent, and save the specialist version for Challenge 5. Do not use the retiring Fabric Data Agent connector. Optimisation decisions should be traceable to authoritative internal data, not unverified web content.

### Reading the trace — what to look for

In the agent's **Traces → Response view**, each run shows a tree of spans:

```
run
├── model_call (instructions + user message sent to gpt-5.4-mini)
├── tool_call: Fabric Data Agent
│   ├── input: { query: "current stock and reorder point for Leaf Blower X2 (P004) across all locations" }
│   └── output: { ... table of rows ... }
├── tool_call: Fabric Data Agent   ← agent may call multiple times
│   ├── input: { query: "average weekly sales for outdoor power tools over the last 8 weeks" }
│   └── output: { ... }
└── model_call (final synthesis → recommendation table)
```

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Agent returns "I don't have enough information" or an empty table | Product/category words don't match Fabric values | Ask by **SKU/productId** (e.g. `P004`) or the exact snake_case category value (`outdoor_power_tools`), not a friendly label like "Outdoor Power Tools" |
| Reorder quantity seems wrong | Agent used a different formula | Remind the agent of the formula in a follow-up: "Use the rule: reorder_qty = max(0, 30-day demand - current stock)" |
| Trace not appearing | Tracing may take 30–60 seconds to update | Refresh the agent's **Traces → Response view** |

### Sample recommendation table

> Illustrative — exact quantities depend on the agent's rounding. `DemandHistory` is **weekly per retail store**, so `average_daily_sales = average weekly units / 7` (~0.8/day for P004). 30-day demand is then ~24, so a store with 6–8 on hand yields a small positive reorder and a **CRITICAL** flag (on hand below safety stock 30).

```
| SKU  | Product        | Location | Current Stock | Suggested Reorder Qty | Priority |
|------|----------------|----------|---------------|-----------------------|----------|
| P004 | Leaf Blower X2 | Seattle  | 6             | 18                    | CRITICAL |
| P004 | Leaf Blower X2 | Portland | 8             | 16                    | CRITICAL |
| P006 | Hedge Trimmer  | Portland | 12            | 8                     | CRITICAL |
```
