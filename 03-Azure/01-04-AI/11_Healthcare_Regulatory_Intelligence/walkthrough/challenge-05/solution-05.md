# Challenge 5 solution: Executive Briefing and human sign-off

**[← Previous Solution](../challenge-04/solution-04.md)** - [Home](../../README.md) - [Challenge](../../challenges/challenge-05.md) - [Next Solution →](../challenge-06/solution-06.md)

**Duration:** 60 minutes

## Expected portfolio briefing (shape)

**By region**

| Region | Changes | Biggest risk | Nearest internal due date |
|---|---|---|---|
| EU | EU-SA-2027-004, EU-GD-2027-011 | Liver warning on both products | RMP and PSUR update 11 Feb 2027 (DHPC 15 Feb) |
| UK | UK-SA-2027-002, UK-REG-2027-001, UK-PR-2027-001 | Label variation and PSUR procedure | UK forecast 2 Mar 2027 |
| US | US-EL-2027-007, US-REG-2027-003, US-CD-2027-015 v2 | Pen supply depends on CMO-17 | CMO-17 impact assessment 26 Jan 2027 |

**By portfolio**: CDX-TAB is affected by seven changes (both safety alerts, nitrosamines, payer, pricing, trial summary and PSUR). CDX-PEN is affected by the EU alert and the warning letter.

**Risks**: RED for pen supply (CMO-17 findings, open DEV-2026-114, no second site, re-audit TASK-2026-044 overdue); AMBER for the EU label timeline and the PSUR procedure; GREEN for pricing.

**Deadlines** (as in our test run): DHPC 1 Mar (internal 15 Feb), US payer evidence 1 Mar (15 Feb), EU variation 15 Mar (1 Mar), UK variation 29 Mar (15 Mar), US tier change 1 Apr (2 Mar). The CMO-17 assessment has no regulator deadline, so it appears under risks and decisions; later dates (PSUR rule 1 Jul, nitrosamines 1 Aug) may or may not be listed.

**Progress** (before any sign-off): TASK-2026-041 in progress; TASK-2026-044 **open and at risk**; TASK-2026-047 done.

EU-GD-2027-019 is omitted because it does not apply.

## Expected sign-off record for EU-SA-2027-004

```json
{
  "change": "EU-SA-2027-004 v1",
  "decision": "approved",
  "approver_role": "Regulatory Affairs Lead",
  "approved_by": "Alex Example",
  "note": "Approved with DHPC brought forward",
  "tasks": [
    {"title": "Update EU label text with the liver-injury warning (4.4, 4.8, leaflet)", "domain": "labelling", "region": "EU", "owner_role": "Labelling Lead", "due": "2027-03-01", "citation": "EU-SA-2027-004 v1 p2"},
    {"title": "Agree DHPC with the regulator and send to prescribers", "domain": "vigilance", "region": "EU", "owner_role": "Pharmacovigilance Lead", "due": "2027-02-15", "citation": "EU-SA-2027-004 v1 p4"},
    {"title": "Add liver injury to the RMP and next PSUR", "domain": "vigilance", "region": "EU", "owner_role": "Pharmacovigilance Lead", "due": "2027-02-11", "citation": "EU-SA-2027-004 v1 p5"}
  ]
}
```

Recording it prints `Tasks created: TASK-2027-001, TASK-2027-002, TASK-2027-003, TASK-2027-004`, and the decision is written to `lake-raw/tracking/audit-log.jsonl` with a SHA-256 of the exact JSON that was approved.

## Expected refusals (Part D)

| Attempt | Message contains |
|---|---|
| `US-CD-2027-015 v1` | `was superseded on 2027-01-12. Re-assess the current version` |
| Citation `p9` | `is not a paragraph in the lake` |
| `approved_by: briefing-agent` | `must be the person who made the decision, not an agent` |
| Same sign-off twice | `already has a recorded decision` |
| Warning-letter plan without `quality_approval_by` | `Manufacturing tasks also need 'quality_approval_by'` |

Discussion answer: instructions guide a model, but they can be ignored or misread. **Code enforces the rules every time**, and an auditor can read and test it (see `tests/test_signoff.py`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| The agent says "tasks created" | Point to the instruction "Never claim that tasks were created"; nothing exists until the command succeeds |
| JSON contains extra text or comments | Copy only the JSON block; the tool reports invalid JSON clearly |
| `owner_role must be one of …` | The agent used a role that is not in `owners.md`; MODIFY the task |
| Progress not visible to the agent | Re-run the indexer after `signoff` or `task`; start a new chat |
| Cloud Shell timed out between steps | Clone again; `--account` makes the tool download the state and the task register first |
