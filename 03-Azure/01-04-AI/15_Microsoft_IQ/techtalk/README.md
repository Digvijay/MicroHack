# Tech talk: 02:13

Every company has the same models; this 24-minute talk follows one night at Strandvik Drives, from Maria's
request at 02:13 to Alex's decision at 07:30, and shows what makes the difference: what your agents know (the
IQs), whom they may talk to (A2A and identity) and who decides (people).
By **Digvijay Chauhan**, Solution Engineer, Microsoft.

| | |
|---|---|
| [`deck/index.html`](deck/index.html) | The talk: 15 animated slides (Reveal.js), with a timed, first-person script in the speaker notes |
| [`02-13.pdf`](02-13.pdf) | Every slide in its final state, one page per slide |

## Present the talk

1. Get the talk, then open `deck/index.html` in Edge or Chrome. Everything is in the folder:
   no server, no install and no internet needed. To download only this hack:
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/MicroHack.git
   cd MicroHack && git sparse-checkout set 03-Azure/01-04-AI/15_Microsoft_IQ
   ```
   Or use **Code > Download ZIP** on GitHub and unzip it.
2. Press **S** for the speaker view (notes and timer), **F** for full screen, **Esc** for the overview.
3. Each slide builds by itself when you arrive. When a slide has more to show, it stops and a small amber
   **Click to continue** cue appears at the top right: press the right arrow, the space bar or click when you
   are ready. The notes mark every click with **[click]**. The left arrow steps back and shows the previous
   state without replaying it.
4. The controls at the top right of every built slide: **Pause** (and Resume), **Replay** (from the start of the
   slide) and **Show all** (the final state at once).
5. Slide 11, **One thread, one decision**, is the moment of the talk. Let the 04:10 proposal build line by line in
   the Kolvo thread, each line stamped with the agent and the IQ it came from. Click: the clock flips to 06:30 and
   dawn comes up over Alex's two options. Ask the room what they would do. Click: 07:30, "Both." and Alex's own
   post close the thread.
6. Three room moments are planned: the hands-up vote on Sam's note (slide 8), "what would you do?" at 06:30
   (slide 11) and "which of the three suppliers is your company today?" (slide 13).

With reduced motion turned on in the operating system, every step appears at once.

The deck uses Bahnschrift (the story clock), Segoe UI Variable, Sitka and Cascadia Mono, which come with
Windows 11. On other systems it falls back to Segoe UI, Georgia and the system monospace font.

## Timing

| # | Slide | Starts | Length | Clicks |
|---|---|---|---|---|
| 1 | 02:13 (cover) | 0:00 | 1:00 | 0 |
| 2 | The press starts shaking | 1:00 | 1:30 | 1 |
| 3 | One request, three suppliers | 2:30 | 2:00 | 1 |
| 4 | Every company has the same models | 4:30 | 1:30 | 1 |
| 5 | Who's asking? | 6:00 | 1:45 | 1 |
| 6 | Alex's agent brings in the specialists | 7:45 | 1:15 | 1 |
| 7 | Which SD-900 could replace it? | 9:00 | 2:00 | 1 |
| 8 | Why didn't it take the unit? | 11:00 | 1:45 | 1 |
| 9 | Sam in Singapore | 12:45 | 2:00 | 2 |
| 10 | Two ways to the press | 14:45 | 1:30 | 1 |
| 11 | One thread, one decision | 16:15 | 2:30 | 2 |
| 12 | Can Alex trust it? | 18:45 | 2:00 | 2 |
| 13 | Run 02:13 again | 20:45 | 1:30 | 1 |
| 14 | Your night: seven challenges | 22:15 | 1:00 | 0 |
| 15 | Thank you | 23:15 | 0:30 | 0 |

## PDF

[`02-13.pdf`](02-13.pdf) has every slide in its final state. To make it again, open
`deck/index.html?print-pdf` in Edge or Chrome and print to PDF (landscape, no margins, background graphics on).

## Where the numbers come from

Every name, time and number of the story comes from [`walkthrough/scenario-facts.md`](../walkthrough/scenario-facts.md).
[`deck/js/data.js`](deck/js/data.js) lists every number shown with its source.

- Slides 2, 3 and 8: the night, the rules (EAP-01, RES-02, SC-KOL-2024, FS-04) and Sam's Friday note in the scenario
  facts. The supplier answers on slide 3 are shortened from Kolvo's procurement board after Run 02:13 (solution 2).
- Slide 5: the three locks and the two refused requests are the success criteria of challenge 2; "4 to 6 minutes"
  for a new role is from solution 2.
- Slide 7: `data/lakehouse/drive_units.csv` and `reservations.csv`, and the expected answer in solution 3.
- Slide 9: the agent's question at 03:45 and Sam's reply at 03:52, as in the README timeline
  (`images/readme-scenario.png`) and the thread in solution 6. The scenario facts put the question at 03:52; the
  emulator's story clock starts at 03:45 with the first live post (solution 5). Singapore is seven hours ahead.
- Slide 10: the transport snapshot TR-01 and TR-02 and "about 21 hours of margin" in solution 6. The 11 hours of the
  Pune route are counted from Wednesday 19:00 to Thursday 06:00. The talk names story days by weekday (Tuesday night
  to Thursday 06:00, next Monday), never by calendar date, month or year.
- Slide 11: the proposal (solution 6) and Alex's 07:30 post (solution 7), shortened. The dawn is decoration.
- Slide 12: results in testing in solution 7 (15 rows, judge `gpt-5.6-luna`): the custom rubric pass rate 27% (4 of
  15) for v3 and 58% (7 of 12) for v6, Compare runs 0.27 to 0.47 "Inconclusive", safety 100%; the trace of one night
  run: 60 seconds, about 30,000 tokens, four nesting levels (`images/c07-nested-a2a-trace.png`). If you rerun the
  evaluation, update the numbers in `data.js` and on the slide.
- Slide 13: the scorecard on the board after Run 02:13 (`images/c02-board-strandvik-answered.png`).
- Slide 14: "The clock and the challenges" and "What is GA and what is preview" in the [hack README](../README.md).

## Credits

Talk, script and design: Digvijay Chauhan, Solution Engineer, Microsoft. The story comes from **Johan Wallquist**'s
keynote *Enter the Agentic Enterprise Era* used with permission; "a note is a reason to
ask" and "an agent can do the work, only a person can answer for it" are his. Strandvik Drives, Kolvo, Poliden,
Nordic Drive Parts, Hallberg Repair Services and every person in the story are fictional.

The slides use [Reveal.js](https://revealjs.com) 6.0.2 by Hakim El Hattab, MIT licence, in
`deck/vendor/reveal.js-6.0.2/` with its `LICENSE`. One label in the speaker view (`plugin/notes.js`) was
reworded to avoid a dash. The beat engine and motion styles (`deck/js/beat-engine.js`, `deck/css/motion.css`)
come from the wow-reveal-presentations skill by the same author.
