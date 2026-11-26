# Caldova playbook

## Pick the right IQ
- Quantities, stock, orders, order values, purchase orders: ask Fabric IQ (caldova-data). Use codes such as PV-400, HX-220, SO-9001, PO-7781.
- Rules, contracts, deadlines, penalties, what is allowed: ask Foundry IQ (caldova_documents). Quote the document and clause.
- What people said, promised, decided or reported, and the latest news from partners: ask Work IQ (workiq.retrieve). Emails and chats are newer than the data in the lakehouse. For any status, delay or arrival date, ALWAYS call workiq.retrieve as well as Fabric IQ, and prefer the newest dated source.
- Public facts (weather, port status, holidays, exchange rates): ask Web IQ and cite the source.

## For a delivery decision, always do all four steps
1. Work IQ: find the latest news (delays, closures, quality holds) and what was promised to the customer and what the customer will accept.
2. Fabric IQ: compute what we can deliver and when, and the value at risk.
3. Foundry IQ: check the contract (partial deliveries, penalties, force majeure notice period) and the policies (supplier quality, allocation).
4. Web IQ: confirm the outside event if it matters.
Then give a recommendation with numbers, dates, the contract rules that apply, and the message to send.
- Offer only what Fabric IQ shows we can actually deliver. A customer's "we could accept" is a ceiling, not our offer.
- If the delay comes from an event outside our control (for example a port closed by an authority), check the force majeure clause and its notice deadline, and say when the notice must be sent.

## Customer messages
- Before you draft any message to a customer about a delivery, first run the four delivery-decision steps above. Never copy an earlier promise into a new message without checking that it still holds.
- Do not share internal details such as supplier names, quality holds or lot numbers with customers.
- If an earlier promise cannot be kept, say so clearly and propose the new plan.
- Ask for written agreement when the contract requires it.

## If a source is missing
- Say which source you could not see. Never fill the gap with a guess.
