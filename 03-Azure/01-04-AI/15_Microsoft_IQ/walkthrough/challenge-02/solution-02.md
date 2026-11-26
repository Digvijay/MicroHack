# Walkthrough Challenge 2: Look outside with Web IQ

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-01/solution-01.md) - [Next Solution](../challenge-03/solution-03.md)

**[Back to Challenge 2](../../challenges/challenge-02.md)**

Duration: 40 minutes

## Expected end state

- The agent has the **web search** tool (`WebSearchTool` in code, **Web search** in the portal). No extra Azure resource: when web search is added directly to a prompt agent or a Responses request, Web IQ powers it.
- Answers to q03 to q05 carry at least one URL or a named, dated source.
- The team discussed the story clock versus the live web.
- A run `challenge 2: + Web IQ` on the leaderboard.

## Command sequence (developer path)

```bash
caldova ask "What is the current weather at the port of Esbjerg in Denmark, and are there any storm warnings for the area? Cite your sources." --iqs web
caldova ask "What is the current EUR to SEK exchange rate? Give the date of the rate and cite your source." --iqs web
caldova ask "Which public holidays fall in Germany and in Sweden between 7 December and 28 December 2026? Cite your sources." --iqs web
caldova eval --iqs web --label "challenge 2: + Web IQ"
caldova leaderboard
```

The code path: `agent.tools()` adds `WebSearchTool(user_location=WebSearchApproximateLocation(country="SE", city="Boras"))`, and `instructions()` adds `TOOL_GUIDANCE["web"]` under "Your tools". `ask()` collects `annotations[].url` from the output items and prints them as citations. In the eval, those URLs are appended to the text before the deterministic checks, so the web citation point counts them.

## Expected outputs

| Question | Good answer | Stable check |
|---|---|---|
| q03 Esbjerg weather | Current conditions and wind at Esbjerg, whether a DMI (or similar) warning is active, with a dated source | Contains "Esbjerg", has a URL |
| q04 EUR/SEK | SEK per 1 EUR with the date or time of the quote, from ECB, Riksbanken or a financial site | Contains "SEK", has a URL |
| q05 Holidays 7 to 28 December 2026 | No national holidays 7 to 23 December. Germany: 25 and 26 December. Sweden: 25 and 26 December, and 24 December treated as a holiday by most employers | Mentions 25 December or Christmas, has a URL |

The values change daily, so the judge scores recency and citation, not numbers. q06 onward still fail: the web knows nothing about Caldova.

## Teaching points

- **Grounding versus the story clock.** The instructions say "Today is Monday 7 December 2026". The web returns today's reality. Today there may be no storm at Esbjerg at all. This is not a bug: it shows that an answer is only as current as its source. Ask teams how the agent should handle a conflict between the story (instructions), the web and an internal email. They meet this again in q16 (Challenge 5), where the newer email must win over the older lakehouse ETA.
- **Citations are a review tool**, not decoration. Ask teams to open each link and check publisher and date.
- **Instructions decide tool use.** If `Tools used: none` appears, the model chose not to search. Make the question explicit or strengthen `TOOL_GUIDANCE["web"]`.
- **Compliance.** With Web IQ, query data may leave the Azure compliance boundary under the Web IQ terms. Have teams look at what the agent actually sent (portal run details). Should an order number ever go into a web query?

## Stretch notes (Web IQ APIs)

- A **Web IQ resource** in the subscription meters usage, priced per 1,000 calls. Calls go to `api.microsoft.ai`; the resource is not in the request path.
- **Scopes** are named site inclusion and exclusion rules shared by the AppIDs of a billing account. Example for Caldova: trust `dmi.dk`, `ecb.europa.eu`, `riksbank.se`.
- Endpoints to explore: **Auto**, **Weather**, **Places**. REST, MCP (JSON-RPC 2.0) or SDK.
- Web IQ needs a paid Azure subscription; Azure credits do not work. The lab does not provision it: treat this as a demo or discussion.
- Note for Challenge 6: web search added through a **toolbox** uses Grounding with Bing Search, not Web IQ.

## Common issues

| Symptom | Cause and fix |
|---|---|
| No URL in the answer, web point lost | Ask for citations explicitly. Check the instruction line asks for sources. |
| Answer says the weather is calm | Correct, the web is live. Use it for the discussion. |
| Web search tool missing in the portal | Web search can be disabled by an Azure admin for the subscription. Check with the lab owner. |
| Scores for q03 to q05 vary between runs | Live content and judge variance. Compare two runs. |

## Discussion prompts

- Which of your business questions depend on live outside facts?
- Which sources would you allow with a scope, and which would you block?
- When should an internal source beat the web, and when the other way round?

---

**[Home](../../README.md)** - [Coach guide](../README.md) - [Previous Solution](../challenge-01/solution-01.md) - [Next Solution](../challenge-03/solution-03.md)
