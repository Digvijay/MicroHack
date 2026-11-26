# Caldova data

This folder holds the data for the Caldova scenario: the Fabric IQ lakehouse tables, the Foundry IQ document corpus and the evaluation set. All companies, people, orders and documents are fictional. Every number, date, id and rule agrees with `../walkthrough/scenario-facts.md`, which is the single source of truth. Microsoft 365 content (emails, chats, meetings, files M1 to M8) is not here: it is seeded by the Work IQ emulator in `../labautomation/workiq-emulator`.

## Fabric IQ: `lakehouse/`

CSV files, UTF-8, comma-separated, header row, ISO dates, no thousands separators. Load them as lakehouse tables and build the Fabric IQ ontology on top.

| File | Rows | Maps to scenario-facts.md |
|---|---|---|
| `suppliers.csv` | 5 | Suppliers (SUP-01 to SUP-05). Teglbruk Metall AS has status `quality_hold`. |
| `components.csv` | 5 | Components, plus `pressure_bearing` (true only for HX-220). |
| `products.csv` | 3 | Products PV-400, CV-90, BV-200 with price and finished goods on hand. |
| `bill_of_materials.csv` | 10 | Bill of materials, quantity 1 per unit. |
| `customers.csv` | 4 | Customers CUS-01 to CUS-04 with tier. |
| `sales_orders.csv` | 4 | Open sales orders SO-9001 to SO-9004. |
| `purchase_orders.csv` | 3 | Open purchase orders PO-7781, PO-7790, PO-7795. |
| `sales_orders_history.csv` | 400 | Shipped orders for the 12 months before 7 December 2026 (SO-8001 onward). Brennmark Industries GmbH is the largest customer at 6,502,600 EUR, matching the key account plan (about 6.5 M EUR a year). |
| `supplier_deliveries_history.csv` | 147 | Inbound deliveries for the same 12 months with promised and actual dates. Nordhavn Castings A/S has 2 winter weather delays at Esbjerg. Teglbruk Metall AS includes lot L-7731 (PO-7702) received on 2026-12-04 with `quality_result` = failed. |

The two history files contain no open orders and no open POs. They are produced by `generate_history.py` with a fixed seed, so `python generate_history.py` reproduces them byte for byte.

Key answers the tables support: orders that depend on HX-220 are worth 1,975,000 EUR; 1,800 PV-400 can be ready by Friday 11 December (600 finished plus 1,200 HX-220); the Brennmark value delayed is 902,000 EUR.

## Foundry IQ: `documents/`

Ten Markdown business documents for the Foundry IQ knowledge base (upload to Azure Blob Storage). They always use product and part codes (PV-400, CV-90, BV-200, HX-220, SL-12, ST-50, FX-8, AC-3) and full company names, and state relationships in plain sentences, so knowledge-graph extraction does not create duplicate entities.

| File | Document id | Content |
|---|---|---|
| `supplier-agreement-nordhavn.md` | SA-2025-014 | Primary HX-220 supply from Esbjerg, 21-day lead time, backup subject to SQP-04 |
| `supplier-agreement-teglbruk.md` | SA-2025-019 | Backup HX-220 supply, 10-day lead time, incoming inspection on every lot |
| `customer-agreement-brennmark.md` | FA-2024-007 | PV-400, partials only with written agreement, 2% per week capped at 10%, force majeure notice within 48 hours |
| `customer-agreement-solvik.md` | FA-2025-002 | CV-90, no partial deliveries, 1% per week capped at 10%, 48-hour notice |
| `customer-agreement-osterdal.md` | CA-2023-031 | Standard terms, PV-400, partials allowed, no penalty |
| `customer-agreement-ferrovia.md` | FA-2025-009 | BV-200, not affected (distractor) |
| `supplier-quality-policy-sqp-04.md` | SQP-04 | Quality hold rule, no deviations for pressure-bearing parts, HX-220 is pressure-bearing |
| `allocation-policy-ap-02.md` | AP-02 | Strategic, key, standard, then due date; Plant Manager override in writing |
| `quality-report-qr-2026-118.md` | QR-2026-118 | Lot L-7731 failed the pressure test on 4 December 2026; hold until corrective action, expected 16 December 2026 |
| `product-catalogue.md` | CAT-2026 | Products, bill of materials, components and suppliers |

## Evaluation: `eval/`

| File | Used by | Content |
|---|---|---|
| `questions.json` | Leaderboard | 19 questions across challenges 1 to 6, with persona, required IQs, gold answer and deterministic checks |
| `rubric.md` | Coaches | Scoring method and per-question table |

## Scripts

| File | Purpose |
|---|---|
| `generate_history.py` | Regenerates the two history CSV files deterministically (stdlib only). |
| `validate_data.py` | Checks totals, ids, bill of materials, document coverage, question schema, reproducibility and the no-dash style rule. Run `python validate_data.py`; it exits non-zero on any failure. |
