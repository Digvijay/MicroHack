/* Numbers and quotes shown in the talk, with their source. Paths are relative to the hack folder.

   story        walkthrough/scenario-facts.md (the single source of truth for every Caldova number)
   blind        src/.caldova/leaderboard-dev1.json, run "challenge 1: no IQ", answer to q18 (first sentence)
   web          src/.caldova/leaderboard.json (26 November 2026): q03 to q05 in "challenge 1: no IQ" and "challenge 2: + Web IQ"
   fabric       src/.caldova/leaderboard-dev1.json, the earlier reference run, "challenge 3: + Fabric IQ": q06 to q09 scored 10 of 10.
                The failing SQL without example queries is from walkthrough/challenge-03/solution-03.md
   graph        walkthrough/challenge-04/solution-04.md, teaching moments 1 and 2 (observed while building the hack)
   permissions  walkthrough/challenge-05/solution-05.md (Sales Lead repeated the stale S&OP line)
   playbook     walkthrough/challenge-06/solution-06.md, "Why each playbook rule exists"
   leaderboard  src/.caldova/leaderboard.json, the newest complete set of the six labels "challenge 1: no IQ" to
                "challenge 6: + playbook" (26 November 2026, 16:24 to 16:38): 62.8, 69.2, 108.7, 142.8, 123.0, 153.6,
                rounded. A second playbook run at 16:42 scored 147.7. If that file is missing or incomplete, use the
                earlier complete run in leaderboard-dev1.json (77, 79, 136, 151, 142, 153) and set illustrative: true.
   ga           README.md, "What is GA and what is preview" (Ignite 2026) */
window.TALK = {
  story: {
    housingsInBoras: 1200, finished: 600, byFriday: 1800, later: 2200, ordered: 4000,
    atRiskEur: 1975000, delayedEur: 902000, noticeHours: 48,
  },
  blind: 'I can\u2019t verify Brennmark\u2019s order status from here, so I can\u2019t say if we can ship it by Friday with confidence.',
  web: [
    { q: 'Weather and storm warnings for Esbjerg, cited', before: 5, after: 9 },
    { q: 'The EUR to SEK exchange rate today, cited', before: 5, after: 10 },
    { q: 'Public holidays in Germany and Sweden before the deadline', before: 7, after: 9 },
  ],
  fabric: [
    { id: 'q06', what: 'Stock in Bor\u00e5s', value: '1,200', unit: 'HX-220', detail: 'housings on hand', score: 10 },
    { id: 'q07', what: 'Orders on Nordhavn', value: '1,975,000', unit: 'EUR', detail: 'Brennmark, Solvik and \u00d8sterdal', score: 10 },
    { id: 'q08', what: 'Buildable by Friday', value: '1,800', unit: 'PV-400', detail: '600 finished + 1,200 built', score: 10 },
    { id: 'q09', what: 'Delayed on SO-9001', value: '902,000', unit: 'EUR', detail: '2,200 \u00d7 410 EUR', score: 10 },
  ],
  leaderboard: {
    max: 190,
    illustrative: false,
    source: 'leaderboard.json',
    second: 148,
    runs: [
      { label: 'challenge 1: no IQ', add: 'none', score: 63 },
      { label: 'challenge 2: + Web IQ', add: 'web', score: 69 },
      { label: 'challenge 3: + Fabric IQ', add: 'fabric', score: 109 },
      { label: 'challenge 4: + Foundry IQ', add: 'foundry', score: 143 },
      { label: 'challenge 5: + Work IQ', add: 'work', score: 123 },
      { label: 'challenge 6: + playbook', add: 'playbook', score: 154 },
    ],
  },
  ga: [
    { iq: 'agent', feature: 'Foundry prompt agents, multi-turn evaluation, Agent Optimizer, Insights', status: 'GA', ch: '1, 6' },
    { iq: 'web', feature: 'Web search tool (Web IQ) in Foundry agents', status: 'GA', ch: '2' },
    { iq: 'fabric', feature: 'Fabric data agent, Fabric IQ MCP', status: 'GA', ch: '3' },
    { iq: 'fabric', feature: 'Fabric IQ ontology, Fabric IQ tool in Foundry', status: 'Preview', ch: '3' },
    { iq: 'foundry', feature: 'Foundry IQ knowledge bases (agentic retrieval)', status: 'GA', ch: '4' },
    { iq: 'foundry', feature: 'Foundry IQ knowledge graph (entity graph)', status: 'Preview', ch: '4' },
    { iq: 'work', feature: 'Work IQ MCP server (retrieve)', status: 'GA', note: 'GA per the Ignite blog, preview per the MCP docs', ch: '5' },
  ],
};
