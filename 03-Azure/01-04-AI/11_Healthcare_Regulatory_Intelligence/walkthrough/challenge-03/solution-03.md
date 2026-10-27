# Challenge 3 solution: Obligation & Impact Extractor

**[← Previous Solution](../challenge-02/solution-02.md)** - [Home](../../README.md) - [Challenge](../../challenges/challenge-03.md) - [Next Solution →](../challenge-04/solution-04.md)

**Duration:** 60 minutes

Caldova's due-date rules (`internal/owners.md`): **deadline − 14 days**; otherwise **effective date − 30 days**; otherwise **within 30 days of today** (11 January 2027 → 10 February 2027). A past due date means **at risk**.

## EU-SA-2027-004: applies to CDX-TAB and CDX-PEN (EU)

| # | Obligation | Deadline | Domain | Citation | Affected items | Owner | Internal due |
|---|---|---|---|---|---|---|---|
| 1 | Update SmPC 4.4 and 4.8 and the package leaflet | variation by 15 Mar 2027 | labelling | v1 p2, p3 | LBL-EU-TAB v7, LBL-EU-PEN v4, SOP-LAB-001 | Labelling Lead | **1 Mar 2027** |
| 2 | Agree a DHPC and send it to prescribers | 1 Mar 2027 | vigilance | v1 p4 | SOP-PV-005 | Pharmacovigilance Lead | **15 Feb 2027** |
| 3 | Add liver injury to the RMP and next PSUR | none stated | vigilance | v1 p5 | SUB-2027-003 (RMP, no date), CAL-401 | Pharmacovigilance Lead | **10 Feb 2027** (rule 3) |

Good answers also notice:

- A label variation normally takes **6 weeks** (`submissions.md`). Starting on 11 January finishes around 22 February, inside the 1 March internal date but with little slack.
- **History** (`history.md`): in 2026 Caldova updated EU, UK and US labels together. The US labels (`LBL-US-TAB`, `LBL-US-PEN`) are *not* required by this EU alert; aligning them is a question for experts.

## US-EL-2027-007: applies to CDX-PEN through CMO-17

- `quality-records.md`: CMO-17 fills **all** EU and US CDX-PEN supply, there is **no second site**, and deviation **DEV-2026-114** (particles in lot P-2611) is open. The letter's finding 1 is about particles [v1 p2].
- `SOP-QA-010`: assess a regulator finding within **10 working days**, so by **25 January 2027**. Owner: **Quality Head**.
- Existing task **TASK-2026-044** (CMO-17 re-audit, due 15 December 2026) is **at risk**. The agent should escalate it, not duplicate it.
- The 15-working-day response [v1 p4] is **CMO-17's** obligation, not Caldova's. Good answers keep the two apart.

## UK-REG-2027-001: applies (UK authorisation holder)

- No product is named, but Caldova holds `PL 54321/0001` in the UK.
- `SOP-PV-003` says 70 or 90 days and must be changed: effective **1 July 2027**, so the internal due date is **1 June 2027**. Owner: Pharmacovigilance Lead.
- `SUB-2027-002` (data lock 31 July 2027, planned 20 October = 81 days) breaks the new **60-day** rule. It must be submitted by **29 September 2027**.

## EU-GD-2027-019: does not apply

Veterinary medicines only [v1 p1, p3]. Caldova has no veterinary products. No actions should be proposed. The monitor tagged it `labelling` because of the word *carton*; tags help filtering but are not a decision.

## Other changes, for coaches

| Change | Expected result |
|---|---|
| UK-SA-2027-002 | CDX-TAB only (`LBL-UK-TAB`); variation by 29 Mar 2027, internal due 15 Mar 2027; serious cases reported within 15 days |
| EU-GD-2027-011 | CAL-301 ended 30 Jun 2026; plain-language summary **not started**; due 30 Jun 2027, internal due 16 Jun 2027; update SOP-CT-002; owner: Clinical Disclosure Lead |
| US-REG-2027-003 | CDX-TAB; confirm by 1 Aug 2027, internal due 18 Jul 2027; CAPA-2026-031 in progress; **existing TASK-2026-041**; owner: Quality Head |
| US-CD-2027-015 v2 | CDX-TAB; evidence by 1 Mar 2027, internal due 15 Feb 2027; update MA-US-DOSSIER v3; tier 3 from 1 Apr 2027; owner: Market Access Lead |
| UK-PR-2027-001 | CDX-TAB; MA-UK-FORECAST assumes 15.3%, now 18.5% from 1 Apr 2027; internal due 2 Mar 2027; owner: Market Access Lead |

## Troubleshooting

| Symptom | Fix |
|---|---|
| The agent says the warning letter does not apply | Ask: "Which products does CMO-17 make for Caldova?" If it can, it should find `quality-records.md`. Reinforce the instruction to search **internal records** too |
| Invented record IDs (for example `SOP-PV-009`) | Compare with `internal/sops.md`; check that the trace retrieved internal files |
| Dates without the rule | Ask for the "How the date was calculated" column; it must quote the owners.md rule |
| Proposes a new nitrosamine task | It missed `tracking/task-register.md`; ask it to check existing tasks |
