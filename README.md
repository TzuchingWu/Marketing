# OUTTHERE

**Get your business noticed.**

An AI-powered marketing agent for small businesses. Instead of chasing the
biggest influencer, OUTTHERE finds the *right* local content creator for
your business — ranked by fit, not follower count — and turns that into a
ready-to-run campaign.

> This README covers the **backend**, which is the current focus. The
> frontend does not exist yet.

## Problem

Small businesses often don't have the budget or expertise to run
sophisticated marketing campaigns, and generic "top 100 influencers" lists
are useless to a bakery in Arcadia with a $300/month budget.

## Solution

OUTTHERE uses an AI agent + MCP tools to discover and rank creators based
on business-specific fit (locality, audience, content relevance,
engagement, budget) rather than follower count.

## Why MCP?

MCP gives the AI agent a standardized interface to business discovery,
creator search, creator analysis, ranking, outreach, and campaign
generation — as callable tools with typed schemas, rather than
hand-rolled function calls buried in application code. This is not a
web app with MCP mentioned in the README: **the MCP server is where the
business logic lives**, and the FastAPI layer is a thin client of it.

```text
                    USER
                     │
                     ▼
                FRONTEND (not built yet)
                     │
                     ▼
              FastAPI (backend/main.py)
                     │
         MCP ClientSession (stdio, shared,
          started once at app startup)
                     │
                     ▼
         OUTTHERE MCP SERVER (backend/mcp/server.py)
                     │
       ┌─────────────┼─────────────┬─────────────┐
       ▼             ▼             ▼             ▼
  Business        Creator       Campaign      Online
  Analysis      Search/Score    Generation   Presence
       │             │             │             │
       └─────────────┴──────┬──────┴─────────────┘
                            ▼
                     Creator Data
              (backend/data/creators.json,
               behind a swappable provider)
```

Every REST endpoint, and the main "Find My Creators" agent workflow, calls
into the MCP server through a real `ClientSession.call_tool()` — not a
direct Python function call. You can see this in `backend/mcp/client_manager.py`.

## MCP tools implemented

All in `backend/mcp/tools/`, registered by `backend/mcp/server.py`:

| Tool | Purpose |
|---|---|
| `analyze_business` | Turn raw business input into structured category/audience/goal data. Deterministic (keyword-rule based), not LLM-based, so it never breaks or drifts. |
| `search_creators` | Find candidate creators by category/location. Auto-widens the search if too few match, so it never dead-ends. |
| `analyze_creator` | Deterministic 0–100 Creator Fit Score for one creator vs. one business, with a 5-part breakdown, strengths/weaknesses, and an LLM (or template) explanation. |
| `rank_creators` | Score + sort a list of candidate creators, best fit first. |
| `generate_outreach` | Personalized outreach DM draft for a business to send to a creator. Never sends anything automatically. |
| `generate_campaign` | Full campaign plan (name, strategy, content ideas, offer, budget allocation, expected reach) from a ranked creator shortlist. |
| `analyze_online_presence` *(optional/bonus)* | Simulated visibility scoring (Google/social/consistency) to motivate why creator marketing helps. |

Every tool has a docstring written for the calling LLM: what it does, when
to use it, and what it returns (FastMCP turns these into the tool
descriptions an agent sees).

## The Creator Fit Score (fit over fame)

Deterministic, pure-Python, no LLM involved — `backend/services/scoring_service.py`.
The LLM's job is to *explain* the score, never to compute it.

```text
Locality / geographic relevance     30 pts
Audience demographic match          25 pts
Content / category relevance        20 pts
Engagement quality                  15 pts
Budget compatibility                10 pts
                                    -------
Total                              100 pts
```

Same business + creator input always produces the same score (see
`tests/test_scoring.py`).

## AI reasoning vs. deterministic code

- **Deterministic (no LLM):** business category/age/interest extraction,
  every scoring component, ranking order, budget allocation.
- **LLM-assisted (optional, falls back to templates if unavailable):**
  explaining *why* a creator is a good fit, writing outreach messages,
  suggesting campaign names/ideas, and — in agentic mode — deciding which
  MCP tools to call and in what order.

## Two ways the agent runs

`backend/mcp/agent_client.py` drives the workflow
(`analyze_business → search_creators → rank_creators → generate_campaign`)
through the MCP server:

- **Agentic** (`ANTHROPIC_API_KEY` set): Claude sees the live MCP tool
  list and decides which tools to call with what arguments. We just relay
  its tool_use requests to the real MCP server and feed results back.
- **Scripted fallback** (no key, or the LLM call errors): the exact same
  MCP tools are called in a fixed order by plain Python. This guarantees
  the demo works completely offline — a hackathon-reliability requirement.

Either way, every tool call is recorded to an `activity_log` for the "AI
Agent Activity" UI, e.g.:

```text
✓ analyze_business    Understood: bakery in Arcadia, CA
✓ search_creators     Found 10 candidate creator(s)
✓ rank_creators       Ranked 10 creator(s), top match @arcadiaeats (91/100)
✓ generate_campaign   Created $275 campaign reaching ~29,400
```

## Data

`backend/data/creators.json` — 27 fictional creator profiles across food,
coffee, fashion, beauty, fitness, gaming, tech, and travel, spread across
Arcadia, Monrovia, Pasadena, San Gabriel, Alhambra, Temple City, Rosemead,
El Monte, Glendale, and Los Angeles. **Clearly labeled as demo/simulated
data** (see the `_note` field) — these are not real people or accounts.

Access goes through `backend/data/creator_provider.py`, an abstract
`CreatorProvider` interface. Swapping in a real creator-discovery API
later means writing one new class with the same two methods — no other
code changes.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: add ANTHROPIC_API_KEY for agentic mode + richer text

uvicorn backend.main:app --reload --port 8000
```

Then either:

```bash
# Full workflow through the real MCP server
curl -X POST http://127.0.0.1:8000/api/agent/recommend \
  -H "Content-Type: application/json" \
  -d '{"business_name":"Sakura Bakery","business_type":"Korean bakery","location":"Arcadia, CA","description":"Small Korean bakery selling pastries, coffee, and fresh bread.","target_audience":"18-30 year olds","goal":"Get more local customers","budget":300}'
```

or point an MCP-compatible client (e.g. Claude Desktop) directly at the
server:

```bash
python -m backend.mcp.server
```

### REST endpoints (thin wrappers over the MCP tools)

```text
GET  /api/health
POST /api/agent/recommend        full workflow, real MCP round trip, returns activity_log
POST /api/business/analyze
POST /api/creators/search
POST /api/creators/rank
POST /api/outreach/generate
POST /api/campaign/generate
```

## Tests

```bash
pytest tests/ -v
```

21 tests covering: score bounds (0–100), determinism, locality/audience/
budget scoring direction, zero-overlap content relevance, empty search
results (auto-widening), ranking determinism and ordering, unknown
business/creator lookups, outreach personalization (and no duplicate
fallback text), business-input edge cases, and campaign budget
compliance.

## Demo reliability

- No external API is required. With no `ANTHROPIC_API_KEY`, every tool
  still works via deterministic scoring + templated text.
- `search_creators` never returns empty — it widens the search instead.
- Unknown business/creator ids raise a clear MCP tool error (surfaced as
  HTTP 404), not a crash.
- The MCP server is spawned once per app lifetime and reused across
  requests (see `client_manager.py`), so in-memory business state stays
  consistent without needing a database.

## Not built yet (frontend, P1/P2)

- Frontend UI (landing form, agent activity panel, creator cards,
  outreach/campaign views).
- Creator comparison, budget optimization UI, campaign regeneration
  prompts, export-to-file.
- A real creator-discovery API behind `CreatorProvider` (currently mock
  data only, by design for the hackathon demo).
