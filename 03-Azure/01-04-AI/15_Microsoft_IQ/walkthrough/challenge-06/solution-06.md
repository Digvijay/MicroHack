# Solution 6: The night shift

[Previous Solution](../challenge-05/solution-05.md) - **[Back to Challenge 6](../../challenges/challenge-06.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-07/solution-07.md)

**Clock: 04:10** · **Duration:** 75 minutes

## Goal

One `alex-agent` run calls `strandvik-parts`, `strandvik-logistics` and `strandvik-service` over A2A, asks Sam through Work IQ, and posts the 04:10 proposal in the Kolvo thread, ending with "Final confirmation from Alex by 07:30."

## Solution notes

### Why A2A and not Workflows

Foundry portal Workflows are being retired and classic connected agents are gone. A2A keeps each specialist as its own agent with its own tools and owner; Alex's agent only asks. Check that teams create no Workflow items.

### Why the Cloud Shell script grants the role (Part C)

Same as challenge 2: each target needs incoming A2A, and the caller's **agent identity** needs **Foundry Agent Consumer**. Neither the Foundry **Assign Azure roles** dialog nor the Azure IAM member picker can find an agent identity yet. Teams run `enable-a2a.py` three times, `--agent strandvik-parts`, `strandvik-logistics` and `strandvik-service`, each with `--caller strandvik/alex-agent`. The script looks up `alex-agent`'s identity and grants the role on that one specialist (least privilege, `--scope agent`). Look for `granted` (or `already granted, nothing to do`) under `Foundry Agent Consumer for alex-agent on agent ...`. Each specialist gets its default card unless the team passes `--description`. An ephemeral Cloud Shell session loses the file, so teams download it again. The role needs 3 to 6 minutes before it works.

### Why Parts uses OAuth Identity Passthrough (Part E)

The Fabric IQ tool runs with a **signed-in user's** identity. With **Microsoft Entra Agent Identity**, the call arrives as an agent and the Fabric tool fails with `tool_server_error` (the trace shows the error on the Fabric tool span inside `strandvik-parts`). **OAuth Identity Passthrough** passes on the user; lab users have Foundry Agent Consumer on the project. Logistics and Service use only Foundry tools, so agent identity plus the script's role is enough. The role on Parts does no harm and keeps the door ready for a later Fabric that accepts agent identities. Same agent, two trust models: a good talking point.

### If the Parts agent fails over A2A

First fix: recreate `strandvik-parts-a2a` with **OAuth Identity Passthrough** (verified in testing). If Fabric is still not reachable (for example the capacity is paused and cannot be resumed), use this fallback. It keeps the architecture and swaps the data path:

1. Create a new version of `strandvik-parts` (or a second agent `strandvik-parts-files`).
2. **Add** > **Add tools** > **Configured** > **Code interpreter**, and **Upload files**: `drive_units.csv`, `machines.csv`, `reservations.csv`, `people.csv`, `account_owners.csv`, `customers.csv`, `sites.csv` from `data/lakehouse/`.
3. Add one line to the instructions: `If the Fabric data tool is not available, read the uploaded ERP extract files with the code interpreter, using the same rules.`
4. Keep the Fabric version for direct playground demos (challenge 3 success criteria still hold).

Test the Parts path before the day and tell teams which one to use.

### Flight hold end time

The hold is free for 6 hours (LOG-03 3.1). In the story it runs until 11:00. An agent that counts from its own clock may write 09:10. Both are right if it says "hold" (not "booking") and gives an end time.

## Expected results

**Logistics test (Part B):** TR-01 (Wednesday 09:00, 2,800 EUR, about 21 hours of margin) and TR-02 (Wednesday 19:00, 40,000 EUR, needs KAM approval, flight hold for 6 hours), citing LOG-03.

**Turn 1:** A2A calls to parts, service and logistics; a Work IQ search that finds Sam's note; a post asking Sam (after **Approve**); "waiting for Sam". About 60 seconds, half of it in the Parts branch.

**Turn 2:** the proposal in the thread. Wording varies; content must match:

```text
Proposal for Kolvo, case CS-88412 (pending Alex)
1. Unit: SD-900 SD9-R-0733, Rotterdam warehouse, reserved for Poliden (RSV-2291). Sam, the owner, released it at 03:53 in this thread, pending Poliden's written confirmation of the new stop date.
2. Delivery: truck and ferry (Kiel to Gothenburg), leaves Rotterdam Tuesday 08:00, at Kolvo Wednesday 09:00. About 2,800 EUR.
3. Installation: Strandvik technician Jonas, Wednesday 22:00 to Thursday 06:00 (slot FS-5101). Inside Kolvo's 48-hour target.
4. Backup: new SD9-P-0981 from Pune by air, Landvetter Wednesday 17:30, Kolvo 19:00, about 40,000 EUR. Flight held until 11:00 (a hold, not a booking; booking needs Alex's approval).
5. Poliden: RSV-2291 moves to SD9-P-0981. If Poliden confirms its stop next Monday moves two weeks, the unit goes by regular freight in time; if not, the held flight covers it.
6. Risks: Poliden's planner confirms in writing around 10:00; Maria needs an answer at 08:00.
7. Recommendation: send the Rotterdam unit at 08:00, move RSV-2291 to the Pune unit, keep the flight held until 11:00.
8. Sources: Strandvik ERP (parts agent), RES-02, SC-KOL-2024, LOG-03, FS-04, Sam's reply in this thread.
Final confirmation from Alex by 07:30.
```

**Turn 3:** no; it can propose, only Alex can commit; final confirmation from Alex by 07:30.

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `tool_user_error` on every `alex-agent` run | One specialist unreachable, `alex-agent` lacks the role, or the role is younger than 4 minutes | Remove A2A tools until it works, add back one at a time; check the script output (`granted` for each specialist); wait |
| A2A tool works for one specialist, not another | That specialist has no incoming A2A | Run `enable-a2a.py --agent <specialist> --caller strandvik/alex-agent` for it; check the card prints |
| `tool_server_error` from the Parts agent | The Parts A2A tool uses agent identity; Fabric needs a person | Recreate `strandvik-parts-a2a` with **OAuth Identity Passthrough** |
| Parts answers "no data found for SD9-K-0412" | The question named only the serial | Ask with customer and machine; the full turn 1 prompt works |
| Alex's agent answers from memory | Weak routing in instructions | Keep "Who knows what" and "Order of work"; name the tools exactly |
| Proposal says "confirmed" | Commit language | The "What only Alex may do" block; re-test with turn 3 |
| Proposal posted before Sam answered | Step 5 missing | Keep "ask the owner, then wait" in the order of work |
| Logistics agent quotes web ferry times that differ | Web is not the story | LOG-03 and the snapshot win; the web is for real-world checks |
| Turn 1 seems to hang after the post to Sam | The playground waits for **Approve** on `create_entity` | Approve the post; reading is auto-approved since challenge 5 |
| Thread times look off (proposal at 03:54, not 04:10) | The story clock starts at 03:45 with the first live post and runs in real time | Fine. Set it with `/viewer/coach` or `POST /manage/clock` with `{"time": "04:10"}` |

## Checks for the coach

- [ ] Trace or chips: three A2A calls plus Work IQ in one `alex-agent` run.
- [ ] The proposal in the thread matches the checklist and ends with "Final confirmation from Alex by 07:30."
- [ ] Times in the proposal are weekday and clock time, no calendar dates.
- [ ] Turn 3: refuses to commit.
- [ ] No Workflow items in the project.

[Previous Solution](../challenge-05/solution-05.md) - **[Back to Challenge 6](../../challenges/challenge-06.md)** - **[Home](../../README.md)** - [Next Solution](../challenge-07/solution-07.md)
