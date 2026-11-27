# Strandvik scenario facts (coach reference, v2)

This file is the single source of truth for every dataset, document, Work IQ seed, agent and evaluation answer. If anything contradicts it, this file wins.

The storyline comes from Johan Wallquist's keynote *Enter the Agentic Enterprise Era* (Microsoft, November 2026), used with permission. Strandvik Drives, Kolvo, Poliden and all the people are fictional.

## The world

**Strandvik Drives AB** is part of a large Swedish engineering group. It builds and services **drive units**: the big motor and gearbox that make a heavy machine move, such as a press at a truck plant or a crusher in a mine.
- Factory in **Pune, India**. Spare-parts warehouse in **Rotterdam, Netherlands**. Field technicians all over Europe.
- Customers pay for **uptime**. When a drive unit fails, Strandvik must get them running again, fast.

| Company | Role | Site |
|---|---|---|
| Strandvik Drives AB | Supplier of SD drive units | HQ Gothenburg, factory Pune, warehouse Rotterdam |
| Kolvo AB | Truck maker, customer | Cab plant, Hisingen, Gothenburg. **Press line 2** runs on an SD-900 |
| Poliden AB | Mining company, customer | Crusher line C3, Skelleftehamn. Planned maintenance stop swaps an SD-900 |
| Nordic Drive Parts | Rival supplier: parts distributor | Answers in 1 minute, from a stock list |
| Hallberg Repair Services | Rival supplier: repair shop | Answers in office hours (08:45) |

## People (first names are used, as in the keynote)

| Name | Company | Role | Owns |
|---|---|---|---|
| **Alex** | Strandvik | Key account manager for Kolvo | Any delivery date or price promised to Kolvo |
| **Sam** | Strandvik | Key account manager for Poliden, at a trade fair in **Singapore** this week (UTC+8) | The **reservation** of the Rotterdam SD-900 for Poliden |
| **Maria** | Kolvo | Production manager, press shop | Her agent's standing instruction |
| Poliden maintenance planner | Poliden | Plans the stop | Confirms the new stop date **in writing** |
| Field technician (role) | Strandvik | Installs SD units | Wednesday night slot at Kolvo |

## Agents

| Agent | Works for | Works in | May do | May not do |
|---|---|---|---|---|
| **Maria's agent** | Kolvo, acting for Maria | Kolvo | Ask approved suppliers for price and delivery | Place an order without Maria |
| **Customer Service agent** | Strandvik | Customer service | Verify who is asking, open a case, hand over to the account owner's agent | Quote, order, or commit |
| **Alex's agent** | Alex | Strandvik, one thread | Orchestrate the specialists, ask colleagues, send a **proposal** | **Commit** a date or price (only Alex can) |
| **Parts agent** | Strandvik | ERP data (Fabric IQ) | Check stock, units, reservations | Sell or move a reserved unit |
| **Logistics agent** | Strandvik | Transport booking and the web (Web IQ) | Find routes and times, hold a flight | Book without approval |
| **Service agent** | Strandvik | Field service and contracts (Foundry IQ) | Check contracts and technician slots | Change a contract |

## The night: Tuesday 15 December 2026 (all times CET)

| Time | Event |
|---|---|
| 02:10 | Kolvo, press line 2: the SD-900 (serial **SD9-K-0412**) starts shaking. Vibration sensors go red. The night shift cuts the press to half speed, which buys time until **Thursday 17 December 06:00**. |
| 02:13 | Maria's agent follows her standing instruction ("when a critical part fails and there is no spare, ask our approved suppliers for price and delivery; never order without me") and sends a request to **three suppliers**: Strandvik, Nordic Drive Parts and Hallberg Repair Services. |
| 02:13 | Strandvik's **Customer Service agent** checks who is asking: Kolvo's agent, acting for Maria, allowed **price and delivery only**. It opens case **CS-88412**, links it to Kolvo and unit SD9-K-0412 on press line 2, and hands it to **Alex's agent**. |
| 02:14 | Nordic Drive Parts answers: "in stock, ships today". It read a stock list and cannot hold the unit. Later that morning the unit turns out to be sold already. |
| 03:10 | Alex's agent brings in the **Parts**, **Logistics** and **Service** agents in one thread. |
| 03:41 | Two candidate units: a **new SD-900 at the Pune factory** (serial **SD9-P-0981**, tested) and an **SD-900 on the shelf in Rotterdam** (serial **SD9-R-0733**), **reserved for Poliden** (reservation **RSV-2291**, owner **Sam**) for Poliden's maintenance stop on **Monday 21 December 2026**. There is a **note from Sam, last Friday 11 December**: "Poliden's stop will probably move two weeks." Not confirmed. **A note is a reason to ask.** |
| 03:52 | Alex's agent asks Sam in the thread. In Singapore it is 10:52. Sam replies: "Yes, it is moving two weeks. Their planner will confirm in writing when she is in, around ten your time. Fine by me, as long as Poliden gets the new unit in time." |
| 04:10 | Alex's agent sends a **proposal** to Maria's agent: SD-900 at Kolvo **Wednesday 16 December 09:00**, Strandvik technician **Wednesday night**. Unit, transport and booking attached. "**Final confirmation from Alex by 07:30.**" |
| 06:30 | Alex wakes up to **one thread**: Kolvo, the two units, Sam's answer, the proposal and a recommendation. |
| 07:30 | **Alex makes the call** (see the decision below). Alex approves. |
| 07:40 | Maria approves, from her kitchen. |
| 08:00 | Poliden's unit leaves Rotterdam by truck. |
| 08:45 | Hallberg Repair Services answers. Too late. |
| 10:05 | Poliden's planner confirms in writing: the stop moves to **Monday 4 January 2027**. The backup flight is cancelled. |
| Thu 06:00 | Press line 2 runs at full speed. |

## The decision at 07:30

| Option | Unit | Arrives at Kolvo | Extra cost | Risk |
|---|---|---|---|---|
| 1. Fly in the new unit | SD9-P-0981 from Pune | **Wednesday 16 Dec 19:00** (Landvetter 17:30), install the same night | about **40,000 EUR** air freight | If the flight is late, the press stops on Thursday at 06:00 |
| 2. Take Poliden's unit | SD9-R-0733 from Rotterdam | **Wednesday 16 Dec 09:00** by truck and ferry, a full day of margin | about **2,800 EUR** road freight | It is Poliden's unit. Only Poliden can confirm in writing that their stop moved (around 10:00, after Maria needs an answer at 08:00) |

**What Alex does: both.**
- Poliden's Rotterdam unit goes to Kolvo, leaving at 08:00.
- Reservation RSV-2291 moves to the new Pune unit SD9-P-0981.
- The flight stays booked until **11:00** as a backup.
- If Poliden confirms, the new unit goes by regular freight in time for 4 January, and the flight is cancelled. Both customers get a unit, and Alex takes the cost risk.

**The principle:** the agents did the groundwork, Sam knew the customer, and Alex made the call. An agent can do the work; only a person can answer for it. Every agent needs an owner.

## Rules (documents for Foundry IQ)

1. **External agent access policy (EAP-01):** an external agent must be identified (company and the person it acts for). Approved customers' agents may request **price and delivery** (a quote). **They may not place orders.** Every external request opens a case and goes to the account owner. Quotes are valid for 24 hours. **Only the key account manager can commit** a delivery date or a price.
2. **Reservation policy (RES-02):** a reserved unit belongs to its reservation until the **owner** releases it. A note, an email or a forecast is **not** a release: **a note is a reason to ask**. Reallocation needs the owner's approval in writing (a chat message counts). The reserved customer must still get an equal unit in time. The KAM who reallocates is accountable for the cost risk.
3. **Kolvo service contract (SC-KOL-2024):** critical drive units (press lines 1 to 3) have a **replacement target of 48 hours** from the request. Strandvik installs. Uptime credit of 0.5% of the annual contract value per day of downtime beyond the target. Kolvo's agent may request quotes on Maria's behalf; orders need Maria's approval.
4. **Poliden service contract (SC-POL-2025):** planned swaps are reserved at least 5 working days ahead. Poliden must confirm date changes in writing from its maintenance planner.
5. **Logistics rules (LOG-03):** Rotterdam to Gothenburg by truck and ferry (Kiel to Gothenburg) takes about 25 hours. Air freight from Pune to Gothenburg Landvetter takes 30 to 36 hours door to door. A flight hold can be kept for 6 hours without cost. Bookings above 10,000 EUR need KAM approval.
6. **SD-900 product sheet:** the SD-900 drive unit replaces SD-900s only (not SD-700). Installation takes 6 to 8 hours and needs a certified technician.
7. **Technician scheduling (FS-04):** a Strandvik technician is available at Kolvo on **Wednesday night (22:00 to 06:00)**. A night install needs 24 hours' notice.

## Microsoft 365 content (Work IQ seed)

| id | Type | When | Who (visible to) | Content |
|---|---|---|---|---|
| W1 | Teams note / chat | Fri 11 Dec 16:20 | Sam, posted in the "Poliden account" channel (Sam, Alex, sales leadership) | "Poliden's stop will probably move two weeks. Waiting for their planner." |
| W2 | Email | Wed 2 Dec | Poliden planner to Sam (Sam) | "The maintenance stop on 21 December is planned. We will confirm any change in writing." |
| W3 | Teams thread | Tue 15 Dec 03:52 to 03:53 | Alex's agent, Sam (Alex, Sam) | **Live in the hack**: the agent asks, Sam (a person or auto-Sam) replies |
| W4 | Calendar | Tue 15 Dec | Alex | "Kolvo weekly 09:30". Alex's alarm is at 06:30 |
| W5 | Email | Mon 14 Dec | Maria to Alex (Alex) | "Press line 2 has shown some vibration, we will keep an eye on it." |
| W6 | File | Nov | "Kolvo account plan FY27.docx" (Alex) | Kolvo is a strategic account; uptime matters more than price |
| W7 | Email (distractor) | | Facilities newsletter (everyone) | Contains one injected line for the untrusted-content discussion |

## The right answer at 04:10 (the proposal)
- Unit: an SD-900 at Kolvo **Wednesday 16 December 09:00**, from the Rotterdam warehouse (SD9-R-0733), released by its owner Sam, pending Poliden's written confirmation.
- Installation: Strandvik technician on **Wednesday night**.
- Backup: the new Pune unit SD9-P-0981 by air, with the flight held until 11:00.
- **Final confirmation from Alex by 07:30.** No order is placed, and no date is committed, by an agent.
