# Strandvik data

This folder holds the data for the Strandvik scenario: the Fabric lakehouse tables, the Foundry IQ documents, the Work IQ seed, the evaluation set and the knowledge-graph ontology. All companies, people, units and documents are fictional. Every name, serial, time, price and rule agrees with `../walkthrough/scenario-facts.md`, the single source of truth.

## Fabric IQ: `lakehouse/` (challenges 1 and 3)

CSV files, UTF-8, comma-separated, header row, snake_case columns, ISO dates, timestamps with offset (CET). The ERP snapshot is taken on Tuesday at about 03:10. Load them as lakehouse tables, then build the ontology and the Fabric data agent (the Parts agent uses it).

| File | Rows | Content |
|---|---|---|
| `sites.csv` | 9 | Gothenburg HQ, Pune factory, Rotterdam warehouse, Kolvo cab plant Hisingen, Poliden Skelleftehamn and four other customer sites |
| `customers.csv` | 6 | Kolvo AB, Poliden AB and four other customers, with tier and service contract |
| `people.csv` | 8 | Alex, Sam (in Singapore), Lina, Erik, Jonna (sales leadership), Noor (field service), Maria (Kolvo), Poliden maintenance planner |
| `account_owners.csv` | 6 | Who owns each customer: Alex owns Kolvo, Sam owns Poliden |
| `approved_external_agents.csv` | 2 | Customer agents allowed to ask for price and delivery (Kolvo's `maria-procurement`, acting for Maria); none may order |
| `machines.csv` | 15 | Customer machines and the drive unit each runs on. Kolvo press line 2 runs on SD9-K-0412 (half speed) |
| `drive_units.csv` | 22 | SD-900 and SD-700 units. In stock SD-900s: SD9-P-0981 (new, tested, Pune) and SD9-R-0733 (Rotterdam). Distractors: SD9-R-0750 (sold), SD9-P-0902 (in repair), SD7-R-0388 (SD-700, does not fit) |
| `reservations.csv` | 5 | RSV-2291: SD9-R-0733 for Poliden crusher C3, needed for next Monday's stop, owner Sam |
| `technicians.csv` | 4 | Field technicians and their certified models |
| `technician_schedule.csv` | 6 | Slot FS-5101: Jonas at Kolvo, Wednesday 22:00 to Thursday 06:00, available |
| `transport_options.csv` | 6 | Rotterdam to Kolvo by truck and ferry (25 h, 2,800 EUR, arrives Wed 09:00); Pune to Kolvo by air (30 to 36 h, 40,000 EUR, Landvetter 17:30, Kolvo 19:00) |
| `price_list.csv` | 8 | List prices for units and installation |
| `service_contracts.csv` | 6 | SC-KOL-2024 (48 h target, 0.5% per day, 1,240,000 EUR), SC-POL-2025 and four others |
| `service_cases.csv` | 5 | Historical cases up to CS-88411. CS-88412 does not exist yet: it is opened live at 02:13 |

## Foundry IQ: `documents/` (challenges 1 and 4)

Upload to the `documents` blob container and build the knowledge base for the Service agent.

| File | Document id | Key rules |
|---|---|---|
| `external-agent-access-policy-eap-01.md` | EAP-01 | Identify company and person; price and delivery only; no orders; every request opens a case for the account owner; quotes valid 24 hours; only the KAM commits |
| `reservation-policy-res-02.md` | RES-02 | Reserved until the owner releases it; a note is a reason to ask; written approval (chat counts); equal unit in time; KAM carries the cost risk |
| `service-contract-kolvo-sc-kol-2024.md` | SC-KOL-2024 | 48-hour replacement target for press lines 1 to 3; Strandvik installs; 0.5% uptime credit per day; orders need Maria |
| `service-contract-poliden-sc-pol-2025.md` | SC-POL-2025 | Planned swaps reserved 5 working days ahead; date changes confirmed in writing by Poliden's planner |
| `logistics-rules-log-03.md` | LOG-03 | Truck and ferry about 25 h; air 30 to 36 h; flight hold 6 h free; bookings above 10,000 EUR need KAM approval |
| `sd-900-product-sheet.md` | PS-SD900 | SD-900 replaces SD-900s only; installation 6 to 8 hours by a certified technician |
| `technician-scheduling-fs-04.md` | FS-04 | Technician at Kolvo Wednesday night 22:00 to 06:00; night install needs 24 hours' notice |

## Work IQ: `workiq/` (challenge 5)

`strandvik-seed.json` is the Work IQ emulator seed (W1 to W7 plus background noise). An identical copy lives at `../labautomation/workiq-emulator/seed/strandvik.json`; keep both in sync. Personas: `alex`, `sam`, `sales-leadership`, `service-coordinator`, `maria`, `poliden-planner`. The Kolvo thread is chat item `W3`; the 03:52 exchange is produced live.

## Evaluation: `eval/` (challenge 7 and finish)

| File | Content |
|---|---|
| `strandvik-eval.jsonl` | 27 single-turn rows (`query`, `ground_truth`, `context`) for the Foundry portal Evaluation "Existing dataset" option, including adversarial rows |
| `strandvik-eval-15.jsonl` | 15 of those rows (6, 7, 8, 12, 13, 14, 16, 18 to 24, 26): the faster set used in challenge 7 |
| `custom-rubric.md` | Text to paste into a custom rubric evaluator for Alex's agent, with weights |
| `john-blund-test.md` | The five-question finish checklist and the evidence to show |

## Knowledge graph: `foundry-iq/` (challenge 4 stretch)

`strandvik-ontology.jsonld` is the ontology for Foundry IQ graph extraction. The `rdfs:comment` on every class tells the extractor how entities are named, which avoids duplicate entities.

## Script

`validate_data.py` checks referential integrity across the CSVs, the key facts (serials, reservation, owners, times, prices), the documents' rules, the seed (W1 to W7 and visibility), the eval files, the ontology and the no-dash style rule. Run `python validate_data.py`; it exits non-zero on any failure. Standard library only, Python 3.10+.
