# Challenge 2: Look outside with Web IQ

**[Home](../README.md)** - [Previous Challenge](challenge-01.md) - [Next Challenge](challenge-03.md)

**Time:** 40 minutes. **IQ:** Web IQ.

## Story beat

08:20. A truck driver calls the Supply Planner: "They say Esbjerg is closed." Is that true? Is the storm getting worse? Which holidays fall before Brennmark's deadline? None of this is in Caldova's systems. It is on the public web, and it changes every hour. Your agent needs eyes on the outside world.

## What you learn

- How the **web search tool** grounds an agent in live web results, powered by **Web IQ**.
- Why citations and recency matter, and how to check them.
- The difference between **grounding** (what is true today) and the **story clock** (Monday 7 December 2026).
- Where the full Web IQ APIs go further: scopes, and the Auto, Weather and Places endpoints.

## Feature status

| Feature | Status |
|---|---|
| Web search tool (Web IQ) in Foundry agents | GA |
| Web IQ resource and APIs: scopes, Auto, Weather, Places (stretch only) | GA |

## Business path (portal, no code)

1. In the Foundry portal, open your agent `caldova-portal`.
2. Under **Tools**, select **Add** > **Web search**. There is no extra resource to create. When you add web search directly to a prompt agent, Web IQ powers it.
3. Add this line to the instructions:

   ```text
   - Web search: current public information, such as weather, storms, port closures, public holidays and exchange rates. Cite the web sources.
   ```

4. Save, then ask in the playground:

   ```text
   What is the current weather at the port of Esbjerg in Denmark, and are there any storm warnings for the area? Cite your sources.
   ```

5. Open the citations. For each one, check: Who published it? When? Is it an authority (for example the Danish Meteorological Institute) or a blog?
6. Ask two more questions and compare the sources:

   ```text
   What is the current EUR to SEK exchange rate? Give the date of the rate and cite your source.
   Which public holidays fall in Germany and in Sweden between 7 December and 28 December 2026? Cite your sources.
   ```

## Developer path (Codespace)

1. Ask the Supply Planner's question with Web IQ:

   ```bash
   caldova ask "What is the current weather at the port of Esbjerg in Denmark, and are there any storm warnings for the area? Cite your sources." --iqs web
   ```

   The output shows `Tools used: web_search` (the exact label can vary) and the cited URLs below the answer.

2. Open [`src/caldova/agent.py`](../src/caldova/agent.py) and find the web tool in `tools()`:

   ```python
   if "web" in iqs:
       out.append(WebSearchTool(user_location=WebSearchApproximateLocation(country="SE", city="Boras")))
   ```

   That one line is all it takes. `user_location` tells the search where the user is, so "local news" and "weather" mean Borås by default. Try changing `city` and ask about "local weather" again.

3. Find `TOOL_GUIDANCE["web"]`. The agent only uses a tool well when the instructions say **when** to use it. Read the text, and notice it asks for citations.
4. Look at how citations come back: in `ask()`, the code reads `annotations` with a `url` from each output item. Those are the links printed under the answer.

## Discuss: the web is live, the story is not

The hack is set on **Monday 7 December 2026**. The web search returns what is true **today**, the day you run it. So:

- The real weather at Esbjerg today may be calm. There may be no storm at all.
- The exchange rate is today's rate, not the rate on 7 December 2026.
- The holiday question works either way, because holidays are fixed dates.

Talk with your team:

1. Your agent's instructions say "Today is Monday 7 December 2026". The web says something else. Which one should win, and when?
2. If the web says the port is open but a partner email says it is closed, what should the agent do? (You meet this conflict again in Challenge 5.)
3. Which of your own business questions depend on live outside facts?

This is the key lesson of grounding: an answer is only as current as its source. A good agent says **where** and **when** a fact comes from.

## Evaluate (both paths)

Run this in the Codespace terminal (or ask your developer teammate or coach):

```bash
caldova eval --iqs web --label "challenge 2: + Web IQ"
caldova leaderboard
```

Look at q03, q04 and q05. Each needs a cited, current source. The web is live, so the judge checks recency and citation, not a fixed value. The questions about Caldova's own data (q06 onward) still fail: the web does not know Caldova's stock.

## Success criteria

- [ ] Your agent answers the Esbjerg weather question with at least one cited, dated web source.
- [ ] You checked who published each citation and when.
- [ ] Your team discussed the difference between the story date and today's web.
- [ ] The leaderboard shows `challenge 2: + Web IQ`, and q03 to q05 score higher than in the baseline.

## Stretch: the Web IQ APIs

The web search tool is the easy way in. The full **Web IQ** service gives you more control:

- A **Web IQ resource** in your Azure subscription for metering and billing. Calls go to `api.microsoft.ai`. Usage is priced per 1,000 calls.
- **Scopes**: named site inclusion and exclusion rules. For example, only trust `dmi.dk`, `ecb.europa.eu` and official holiday pages.
- Specialised endpoints: **Auto** (fresh, ranked answers for agents), **Weather** and **Places**.
- REST, MCP (JSON-RPC 2.0) or an SDK, with titles, URLs, snippets and timestamps ready for the model's context window.

Discuss: which Caldova questions would you limit to official sources with a scope?

> [!WARNING]
> When you connect to Web IQ, data you send in queries may leave the Azure compliance boundary, under the Web IQ terms. Do not put customer names or order numbers in a web query unless your policy allows it. Look at your agent's tool calls: what did it actually send to the web?

## Value card

| What this IQ is | What it fixed today | Where customers use it |
|---|---|---|
| **Web IQ**: fresh, ranked, citation-ready context from the public web, built for agents. | The agent can now check the weather, the exchange rate and the holidays, with sources. | Supply chain risk (weather, ports, strikes), market and competitor news, travel and field service, any answer that must be current and cited. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| No citations in the answer | Ask for them ("Cite your sources"). Check the instructions mention citations. |
| The answer talks about weather "today" with no storm | That is correct. The web is live. See [the discussion above](#discuss-the-web-is-live-the-story-is-not). |
| `Tools used: none` with `--iqs web` | The model decided not to search. Make the question explicit ("current", "cite"), or strengthen `TOOL_GUIDANCE["web"]`. |
| Web search not offered in the portal | An admin can block web search for the subscription. Ask your coach. |

## Learning resources

- [Use the web search tool in Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/web-search)
- [Microsoft Web IQ overview](https://learn.microsoft.com/en-us/web-iq/overview)
- [Microsoft IQ documentation](https://learn.microsoft.com/en-us/microsoft-iq/)

---

**[Home](../README.md)** - [Previous Challenge](challenge-01.md) - [Next Challenge](challenge-03.md)
