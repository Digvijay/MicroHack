# Caldova scenario facts (coach reference)

This is the single source of truth for every dataset, document, emulator seed and evaluation answer in this hack. If something contradicts this file, this file wins.

## The company

**Caldova Components AB** is a fictional mid-size Swedish B2B manufacturer of industrial flow-control components (valves). Its head office and plant are in **Borås, Sweden**, and it has about 600 employees. Its customers are equipment makers in Northern Europe.

People are named only by **role**, never by name:

| Persona id | Role | Owns |
|---|---|---|
| `sales-lead` | Sales Lead, Key Accounts | Customer relationships, promises to customers |
| `supply-planner` | Supply Planner | Purchase orders, suppliers, inbound logistics |
| `quality-head` | Quality Head | Supplier quality, quality holds, deviations |
| `plant-manager` | Plant Manager | Production plan, overtime, allocation decisions |

Customer and supplier contacts are also roles, for example "Brennmark Purchasing Manager".

## Time

The hack takes place on **Monday 7 December 2026 at 08:00 CET**. "Friday" means **Friday 11 December 2026**.

## Master data (Fabric lakehouse)

### Suppliers
| supplier_id | name | country | port | status |
|---|---|---|---|---|
| SUP-01 | Nordhavn Castings A/S | Denmark | Esbjerg | active |
| SUP-02 | Teglbruk Metall AS | Norway | Bergen | quality_hold |
| SUP-03 | Kvarnby Polymers AB | Sweden | Malmö | active |
| SUP-04 | Rhein Präzision GmbH | Germany | Duisburg | active |
| SUP-05 | Baltic Fasteners UAB | Lithuania | Klaipėda | active |

### Components
| component_id | name | primary_supplier_id | backup_supplier_id | on_hand_boras | unit_cost_eur |
|---|---|---|---|---|---|
| HX-220 | Aluminium valve housing | SUP-01 | SUP-02 | 1200 | 38 |
| SL-12 | Seal kit | SUP-03 | | 9000 | 4 |
| ST-50 | Valve stem | SUP-04 | | 7000 | 11 |
| FX-8 | Fastener kit | SUP-05 | | 20000 | 1.5 |
| AC-3 | Electric actuator | SUP-04 | | 2500 | 95 |

### Products and bill of materials (qty 1 each)
| product_id | name | unit_price_eur | components | finished_goods_on_hand |
|---|---|---|---|---|
| PV-400 | Pump valve | 410 | HX-220, SL-12, ST-50, FX-8 | 600 |
| CV-90 | Control valve | 265 | HX-220, AC-3, FX-8 | 0 |
| BV-200 | Ball valve | 120 | ST-50, SL-12, FX-8 | 2500 |

Plant capacity is 400 PV-400 per day, or 600 per day with the approved weekend overtime. Parts, not capacity, are the bottleneck this week.

### Customers
| customer_id | name | country | tier |
|---|---|---|---|
| CUS-01 | Brennmark Industries GmbH | Germany | strategic |
| CUS-02 | Solvik Marine AS | Norway | key |
| CUS-03 | Østerdal Pumps AS | Norway | standard |
| CUS-04 | Ferrovia Systems S.p.A. | Italy | key |

### Open sales orders
| order_id | customer_id | product_id | quantity | due_date | order_value_eur |
|---|---|---|---|---|---|
| SO-9001 | CUS-01 | PV-400 | 4000 | 2026-12-11 | 1640000 |
| SO-9002 | CUS-02 | CV-90 | 800 | 2026-12-18 | 212000 |
| SO-9003 | CUS-03 | PV-400 | 300 | 2027-01-08 | 123000 |
| SO-9004 | CUS-04 | BV-200 | 1500 | 2026-12-15 | 180000 |

### Open purchase orders and shipments
| po_id | supplier_id | component_id | quantity | port | original_eta | status |
|---|---|---|---|---|---|---|
| PO-7781 | SUP-01 | HX-220 | 3500 | Esbjerg | 2026-12-08 | held_at_port |
| PO-7790 | SUP-04 | ST-50 | 4000 | Duisburg | 2026-12-10 | in_transit |
| PO-7795 | SUP-03 | SL-12 | 5000 | Malmö | 2026-12-09 | in_transit |

## Documents (Foundry IQ knowledge base, Azure Blob)

1. `supplier-agreement-nordhavn.md`: SA-2025-014. Nordhavn supplies HX-220 and ships from Esbjerg, with a 21-day lead time. If Nordhavn cannot deliver, Caldova may buy HX-220 from the backup supplier Teglbruk Metall AS after notifying the Supply Planner, **subject to the Supplier Quality Policy**.
2. `supplier-agreement-teglbruk.md`: Teglbruk is the backup for HX-220 with a 10-day lead time. Every lot needs incoming inspection.
3. `customer-agreement-brennmark.md`: FA-2024-007. Brennmark buys **PV-400 pump valves** for its compressor line in Hamburg.
   - **Partial deliveries are allowed if Brennmark's Purchasing Manager agrees in writing.**
   - Late delivery costs **2% of the late value per week, capped at 10%**.
   - **Force majeure** includes port closures declared by a public authority. Caldova must notify Brennmark **within 48 hours** of becoming aware.
4. `customer-agreement-solvik.md`: FA-2025-002. Solvik buys **CV-90 control valves** for ship ballast systems built in Bergen. **No partial deliveries.** The penalty is 1% per week, capped at 10%. Force majeure applies with the same 48-hour notice.
5. `customer-agreement-osterdal.md`: standard terms. Østerdal buys **PV-400 pump valves** for municipal water systems in Oslo. Partial deliveries are allowed. No penalty.
6. `customer-agreement-ferrovia.md`: Ferrovia buys **BV-200 ball valves** for rail braking systems. This customer is not affected; the document is a distractor.
7. `supplier-quality-policy-sqp-04.md`: **No component from a supplier with status "quality hold" may be used without a written deviation approved by the Quality Head.** Deviations are not granted for pressure-bearing parts. **HX-220 is pressure-bearing.**
8. `allocation-policy-ap-02.md`: when supply is short, allocate in this order: strategic, then key, then standard customers, then by due date. The Plant Manager may override this in writing.
9. `quality-report-qr-2026-118.md`: lot **L-7731** of HX-220 from **Teglbruk Metall AS** failed the pressure test on 4 December 2026. Teglbruk is on **quality hold** until a corrective action is approved. The expected date is **16 December 2026**.
10. `product-catalogue.md`: PV-400 contains HX-220, SL-12, ST-50 and FX-8. CV-90 contains HX-220, AC-3 and FX-8. BV-200 contains ST-50, SL-12 and FX-8. Use **product and part codes consistently** (PV-400, HX-220).

## Microsoft 365 content (Work IQ emulator seed)

| id | type | date (CET) | from → to / members | visible to | content |
|---|---|---|---|---|---|
| M1 | email | 2026-12-03 16:40 | sales-lead → Brennmark Purchasing Manager (cc plant-manager) | sales-lead, plant-manager | "I confirm the **full 4,000 PV-400 will ship by Friday 11 December**." **This is the promise.** |
| M2 | meeting + transcript file | 2026-12-02 10:00 | Weekly S&OP. Attendees: plant-manager, supply-planner, sales-lead | the attendees | Plant Manager: "Brennmark is our priority this month." Weekend overtime is approved, raising capacity to 600 a day. Supply Planner: "PO-7781 lands Tuesday 8 December, so we are covered." |
| M3 | Teams chat | 2026-12-04 15:05 | quality-head ↔ supply-planner, plant-manager added | quality-head, supply-planner, plant-manager | Quality Head: "Teglbruk lot L-7731 failed the pressure test. They stay on hold, and the corrective action is expected 16 Dec. Do not plan on Teglbruk HX-220." |
| M4 | email | 2026-12-07 07:12 | Nordic Freight Partners (logistics) → supply-planner | supply-planner | "The Danish Maritime Authority has **closed the port of Esbjerg** because of storm conditions. Container for PO-7781 (3,500 HX-220) is held. **Earliest departure 14 December**, so arrival in Borås is about **16 December**." |
| M5 | email | 2026-12-07 08:30, forwarded 08:50 | Brennmark Purchasing Manager → sales-lead, forwarded by sales-lead to plant-manager | sales-lead, plant-manager | "Can you confirm Friday? Our line stops on 14 December without valves. **We could accept 2,000 by Friday if the rest arrives by 18 December.** Please confirm in writing." |
| M6 | Teams chat | 2026-12-07 08:45 | supply-planner ↔ plant-manager | supply-planner, plant-manager | Supply Planner: "Esbjerg closed, PO-7781 is stuck. Earliest departure 14 Dec, so it arrives in Borås around 16 Dec. We have 1,200 HX-220 in Borås plus 600 finished PV-400." Plant Manager: "Hold all HX-220 for Brennmark until we decide." |
| M7 | SharePoint file | 2026-11-20 | "Key account plan FY27, Brennmark.docx" | sales-lead, plant-manager | Brennmark is worth about 6.5 M EUR a year and the renewal is in March 2027. The relationship is sensitive to late deliveries. |
| M8 | calendar event | 2026-12-07 11:00 | "Brennmark escalation call". Attendees: sales-lead, plant-manager | attendees | Agenda: confirm Friday delivery. |

Persona trimming is the key lesson. The **Sales Lead cannot see M3** (the quality hold) or **M4** (the port closure). Asked as Sales Lead, the agent cannot know the backup supplier is blocked.

The **Plant Manager** is the decision-maker and the persona for the capstone questions. They can see M1 (copied), M2, M3, M5 (forwarded), M6, M7 and M8, which is everything the right answer needs.

## The right answer ("Can we ship by Friday, and what do we tell Brennmark?")

1. **Not the full order.** With PO-7781 held, the parts available by Friday allow **600 finished PV-400 + 1,200 built from HX-220 stock = 1,800 PV-400**. Capacity is not the limit.
2. **The backup supplier cannot be used.** Teglbruk is on quality hold (QR-2026-118). Policy SQP-04 forbids the HX-220 because it is pressure-bearing, so no deviation can be granted.
3. **Allocation.** Brennmark is strategic, so the 1,200 HX-220 go to PV-400 for Brennmark (AP-02, and the Plant Manager's decision in M6). As a result, **Solvik's CV-90 order (800, due 18 December, no partials) depends on PO-7781 arriving about 16 December**. It is at risk but still feasible.
4. **What to tell Brennmark:**
   - Send a **force majeure notice within 48 hours** (the port was closed by an authority), so by **Wednesday 9 December 08:00**.
   - Offer **1,800 by Friday 11 December** and the **remaining 2,200 by 18 December**. That is close to the 2,000 they would accept (M5).
   - Get their **written agreement for the partial delivery** (contract FA-2024-007).
   - Correct the promise of a full shipment made in M1.
5. **Money:**
   - Orders depending on Nordhavn's HX-220: SO-9001, SO-9002 and SO-9003, together **1,975,000 EUR**.
   - Value delayed on Brennmark: **2,200 × 410 = 902,000 EUR**.
   - Without force majeure, the penalty would be 2% per week of 902,000 = **18,040 EUR per week**.

## Web IQ (live web)

The web is live, so evaluations check for **cited, current external context**, not fixed values. Typical questions:
- The current weather and storm warnings for Esbjerg.
- Public holidays in Germany and Sweden in the next two weeks.
- The current EUR/SEK exchange rate.
- Recent news about North Sea port closures.

## Details added by the data set

These details are not part of the core story. The data set in `data/` invented them so the documents and tables feel real. They must stay consistent with the files below.

| Detail | Value | Where |
|---|---|---|
| Teglbruk supplier agreement id | SA-2025-019 | `supplier-agreement-teglbruk.md` |
| Teglbruk HX-220 price | 44 EUR per unit delivered to Borås (express surcharge 5 EUR per unit under 10 days) | `supplier-agreement-teglbruk.md` |
| Østerdal standard terms id | CA-2023-031 | `customer-agreement-osterdal.md` |
| Ferrovia frame agreement id | FA-2025-009 | `customer-agreement-ferrovia.md` |
| Ferrovia force majeure notice | within 72 hours | `customer-agreement-ferrovia.md` |
| Ferrovia late penalty | 0.5% of the late value per week after 5 working days, capped at 5% | `customer-agreement-ferrovia.md` |
| Product catalogue id | CAT-2026 | `product-catalogue.md` |
| Lot L-7731 | 500 units of HX-220, purchase order PO-7702, received in Borås on 4 December 2026 | `quality-report-qr-2026-118.md`, `supplier_deliveries_history.csv` |
| L-7731 pressure test | 3 of 13 samples leaked at 24 bar proof pressure, so the lot failed | `quality-report-qr-2026-118.md` |
| Earlier Teglbruk lots | L-7310 (March 2026) and L-7522 (July 2026), 300 units each, passed | `quality-report-qr-2026-118.md`, `supplier_deliveries_history.csv` |
