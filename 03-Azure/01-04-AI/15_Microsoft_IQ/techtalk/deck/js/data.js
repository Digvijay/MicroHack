/* Every number and quote shown in the talk, with its source. Paths are relative to the hack folder.

   facts      walkthrough/scenario-facts.md, the single source of truth for every Strandvik name, time and number:
              the night (02:10, 02:13, 03:10, 03:41, 04:10, 06:30, 07:30, 08:45, 10:05), serials, RSV-2291, Sam's note,
              Sam's reply, the rules (EAP-01, RES-02, SC-KOL-2024 48 hours, LOG-03, FS-04) and the decision at 07:30.
   times      03:45 (the agent's question to Sam) and 03:52 (Sam's reply): images/readme-scenario.png and the thread in
              images/c06-proposal-in-thread.png. scenario-facts.md puts the question at 03:52; the emulator's story clock
              starts at 03:45 with the first live post (walkthrough/challenge-05/solution-05.md).
   units      data/lakehouse/drive_units.csv and reservations.csv; the expected answer in walkthrough/challenge-03/solution-03.md.
   board      images/c02-board-strandvik-answered.png and walkthrough/challenge-02/solution-02.md, task 6 (the scorecard
              after Run 02:13). Hallberg's and Nordic's answers are quoted from the same board.
   routes     walkthrough/challenge-06/solution-06.md: transport snapshot TR-01 and TR-02, "about 21 hours of margin".
              The 11 hours for the Pune route are counted from Wednesday 19:00 to Thursday 06:00 (derived).
              The talk names story days by weekday (Tuesday night to Thursday 06:00, next Monday), never by calendar date.
   slot       walkthrough/challenge-04/solution-04.md: FS-5101, Jonas, Wednesday 22:00 to Thursday 06:00.
   evaluation walkthrough/challenge-07/solution-07.md, results in testing (15 rows, judge gpt-5.6-luna):
              custom rubric pass rate 27% (4/15) for v3 and 58% (7/12) for v6; Compare runs 0.27 to 0.47 "Inconclusive";
              safety evaluators 100% in both runs.
   trace      walkthrough/challenge-07/solution-07.md, task 5, and images/c07-nested-a2a-trace.png: 60.2 s, 40 spans,
              9 tool calls, 30.6K tokens, four nesting levels, branches: Parts 31.29 s, Service 11.12 s, Logistics 9.89 s
              (shown rounded to 31.3, 11.1 and 9.9 s), under 0.01 USD for Alex's agent's share.
   status     README.md, "What is GA and what is preview".
   challenges README.md, "The clock and the challenges". */
window.TALK = {
  units: [
    { serial: 'SD9-P-0981', model: 'SD-900', site: 'Pune', status: 'In stock, tested', tag: 'free', kind: 'free' },
    { serial: 'SD9-R-0733', model: 'SD-900', site: 'Rotterdam', status: 'In stock', tag: 'reserved', kind: 'res' },
    { serial: 'SD9-R-0750', model: 'SD-900', site: 'Rotterdam', status: 'Sold', tag: 'sold to Delfzijl', kind: 'why' },
    { serial: 'SD9-P-0902', model: 'SD-900', site: 'Pune', status: 'In repair', tag: 'back next month', kind: 'why' },
    { serial: 'SD7-R-0388', model: 'SD-700', site: 'Rotterdam', status: 'In stock', tag: 'SD-700: no fit', kind: 'why' },
  ],

  // Axis of the routes slide: Tuesday 08:00 (0 h) to Thursday 06:00 (46 h).
  axis: { hours: 46, x0: 300, x1: 1180 },
  routes: [
    { unit: 'SD9-R-0733', from: 'Rotterdam', how: 'Truck to Kiel, ferry to Gothenburg', arrives: 'Wed 09:00', at: 25,
      cost: '2,800 EUR', note: 'about 25 hours, no approval needed', margin: 'about 21 h of margin' },
    { unit: 'SD9-P-0981', from: 'Pune', how: 'Air to Landvetter (17:30), then truck', arrives: 'Wed 19:00', at: 35,
      cost: '40,000 EUR', note: 'above 10,000 EUR: Alex approves. Flight hold free for 6 hours', margin: '11 h' },
  ],
  slot: { id: 'FS-5101', from: 38, to: 46, label: 'Wed 22:00 to Thu 06:00' },

  // The 04:10 proposal in the Kolvo thread (solution 6, shortened), with the agent and IQ behind each line.
  proposal: [
    { tx: 'Unit: SD9-R-0733, Rotterdam, reserved RSV-2291', src: 'Parts · Fabric IQ', c: 'fabric' },
    { tx: 'Sam releases it, pending Poliden in writing', src: 'Sam · Work IQ', c: 'work' },
    { tx: 'At Kolvo Wed 09:00 by truck and ferry, 2,800 EUR', src: 'Logistics · LOG-03', c: 'web' },
    { tx: 'Technician Wed 22:00 to Thu 06:00, slot FS-5101', src: 'Service · FS-04', c: 'foundry' },
    { tx: 'Backup: SD9-P-0981 by air, flight held until 11:00', src: 'Logistics · LOG-03', c: 'web' },
    { tx: 'Poliden: RSV-2291 moves to SD9-P-0981, in time', src: 'Service · RES-02', c: 'foundry' },
  ],

  board: {
    cols: ['Answered', 'Answered in time', 'Grounded, holds the unit', 'Respects quote only', 'Final confirmation by a person'],
    rows: [
      { name: 'Strandvik Drives', kind: 'your team', cells: [1, 1, 1, 1, 1], verdict: 'Shows what it can stand behind' },
      { name: 'Nordic Drive Parts', kind: 'parts distributor', cells: [1, 1, 0, 1, 0], verdict: 'Fast, but can\u2019t stand behind it' },
      { name: 'Hallberg Repair Services', kind: 'repair shop', cells: [1, 0, 0, 1, 1], verdict: 'Too late for Maria' },
    ],
  },

  evaluation: {
    rows: 15,
    rubric: [
      { version: 'v3', what: 'challenge 5', pct: 27, n: '4 of 15' },
      { version: 'v6', what: 'challenge 6', pct: 58, n: '7 of 12' },
    ],
    compare: { baseline: 0.27, improved: 0.47, verdict: 'Inconclusive' },
    safety: 100,
  },
  trace: { seconds: 60, tokens: 'about 30,000', levels: 4, partsSeconds: 31 },

  challenges: [
    { clock: '02:10', title: 'Lights on', product: 'Setup, the Strandvik world', status: '', min: 45 },
    { clock: '02:13', title: 'Who\u2019s asking?', product: 'Agent Service, A2A, agent identity, guardrails', status: 'A2A: GA', min: 45 },
    { clock: '03:10', title: 'Know the business', product: 'Fabric IQ: lakehouse, ontology, data agent', status: 'Ontology: Preview', min: 75 },
    { clock: '03:41', title: 'Why didn\u2019t it take the unit?', product: 'Foundry IQ: knowledge base', status: 'Knowledge bases: GA', min: 60 },
    { clock: '03:52', title: 'Sam in Singapore', product: 'Work IQ (emulator, same MCP contract)', status: 'Work IQ MCP: Preview', min: 60 },
    { clock: '04:10', title: 'The night shift', product: 'Web IQ, A2A orchestration', status: 'Web search: GA', min: 75 },
    { clock: '07:30', title: 'Alex makes the call', product: 'Evaluations, tracing, cost, the 02:13 replay', status: 'Evaluations: GA', min: 45 },
    { clock: 'Thu 06:00', title: 'The John Blund test', product: 'All five layers', status: '', min: 15 },
  ],
};
