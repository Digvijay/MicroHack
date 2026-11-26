# Tech talk: Into focus

Every company has the same models; this 23-minute talk shows, with Caldova's Monday morning, how the four Microsoft IQs bring an agent's answer into focus.
By **Digvijay Chauhan**, Solution Engineer, Microsoft.

| | |
|---|---|
| [`deck/index.html`](deck/index.html) | The talk: 15 animated slides (Reveal.js), with a timed, first-person script in the speaker notes |
| [`into-focus.pdf`](into-focus.pdf) | Every slide in its final state, one page per slide |

## Present the talk

1. Get the talk, then open `deck/index.html` in Edge or Chrome. Everything is in the folder:
   no server, no install and no internet needed. To download only this hack:
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/MicroHack.git
   cd MicroHack && git sparse-checkout set 03-Azure/01-04-AI/15_Microsoft_IQ
   ```
   Or use **Code > Download ZIP** on GitHub and unzip it.
2. Press **S** for the speaker view (notes and timer), **F** for full screen, **Esc** for the overview.
3. Each slide builds by itself when you arrive. When a slide has more to show, it stops and a small
   **Click to continue** cue appears at the top right: press the right arrow, the space bar or click when you
   are ready. The notes mark every click with **[click]**. The left arrow steps back and shows the previous
   state without replaying it.
4. The controls at the top right of every built slide: **Pause** (and Resume), **Replay** (from the start of the
   slide) and **Show all** (the final state at once).
5. Slide 10, **Bring the answer into focus**, is the moment of the talk. Read the question, then click: the four
   lenses arrive one by one and each sharpens its line of the answer. Click again and they converge.

With reduced motion turned on in the operating system, every step appears at once.

The deck uses Segoe UI Variable, Sitka and Cascadia Mono, which come with Windows 11. On other systems it falls
back to Segoe UI, Georgia and the system monospace font.

## Timing

| # | Slide | Starts | Length | Clicks |
|---|---|---|---|---|
| 1 | Into focus (cover) | 0:00 | 1:00 | 0 |
| 2 | Monday, 08:00 | 1:00 | 2:00 | 1 |
| 3 | Every company has the same models | 3:00 | 2:00 | 1 |
| 4 | Web IQ: look outside | 5:00 | 1:30 | 1 |
| 5 | Fabric IQ: know the business | 6:30 | 2:00 | 1 |
| 6 | Foundry IQ: know the rules | 8:30 | 1:30 | 1 |
| 7 | Two graphs, one question | 10:00 | 2:30 | 2 |
| 8 | Work IQ: know the people | 12:30 | 1:30 | 1 |
| 9 | Same question, two truths | 14:00 | 1:30 | 2 |
| 10 | Bring the answer into focus | 15:30 | 2:30 | 2 |
| 11 | The learning curve, one IQ at a time | 18:00 | 1:30 | 2 |
| 12 | Four IQs are not enough | 19:30 | 1:30 | 1 |
| 13 | What you can use today | 21:00 | 1:00 | 1 |
| 14 | One agent, four IQs, six challenges | 22:00 | 1:00 | 0 |
| 15 | Thank you | 23:00 | 0:20 | 0 |

## PDF

[`into-focus.pdf`](into-focus.pdf) has every slide in its final state. To make it again, open
`deck/index.html?print-pdf` in Edge or Chrome and print to PDF (landscape, no margins, background graphics on).

## Where the numbers come from

Every Caldova number comes from [`walkthrough/scenario-facts.md`](../walkthrough/scenario-facts.md).
[`deck/js/data.js`](deck/js/data.js) lists every measured value with its source.

- Slide 2: the blind agent's answer is the first sentence of a recorded run of challenge 1 (no IQ).
- Slide 4: q03 to q05 in `src/.caldova/leaderboard.json`, runs "challenge 1: no IQ" and "challenge 2: + Web IQ".
- Slide 5: the failing SQL is described in solution 3; the four 10 of 10 scores are from an earlier reference run
  (`src/.caldova/leaderboard-dev1.json`, "challenge 3: + Fabric IQ"). Single answers swing between runs.
- Slides 6 and 7: the documents in `data/documents` and the teaching moments in solution 4 (the split "PV-400" node,
  "Yes, buy from Teglbruk" with ontology v1, the fix in v2), all observed while building the hack.
- Slides 8 and 9: the Work IQ emulator seed (M1 to M8) and solution 5. The Work IQ part of the hack runs on an
  emulator with the exact Work IQ MCP contract, because a lab tenant has no Microsoft 365 Copilot licences.
- Slide 10: the reference answer to q18, coloured by the IQ each fact comes from. The composition is illustrative.
- Slide 11: the newest complete set of the six runs "challenge 1: no IQ" to "challenge 6: + playbook" in
  `src/.caldova/leaderboard.json` (26 November 2026): 63, 69, 109, 143, 123 and 154 out of 190, rounded. A second
  playbook run scored 148. If you rerun the evaluation, update the scores in `data.js`.
- Slide 12: "Why each playbook rule exists" in solution 6, including the cold draft that copied "4,000 by Friday"
  and scored 0 with the judge.
- Slide 13: "What is GA and what is preview" in the [hack README](../README.md#what-is-ga-and-what-is-preview).

## Credits

Talk, script and design: Digvijay Chauhan, Solution Engineer, Microsoft. Caldova and every person, company and
number in its story are fictional.

The slides use [Reveal.js](https://revealjs.com) 6.0.2 by Hakim El Hattab, MIT licence, in
`deck/vendor/reveal.js-6.0.2/` with its `LICENSE`. One label in the speaker view (`plugin/notes.js`) was
reworded to avoid a dash. The beat engine and motion styles (`deck/js/beat-engine.js`, `deck/css/motion.css`)
come from the wow-reveal-presentations skill by the same author.
