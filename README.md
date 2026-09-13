# OUTTHERE

**Get your business noticed.**

An AI-powered marketing agent for small businesses. Instead of chasing the
biggest influencer, OUTTHERE finds the *right* local content creator for
your business — ranked by fit, not follower count — and turns that into a
ready-to-run campaign.

> This README covers the **backend** in depth. A React/Vite frontend
> exists in `frontend/` but is not yet wired up to this backend (still
> using mock data) — that connection is the next piece of work.

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
           FRONTEND (frontend/, not yet wired up)
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
| `analyze_business` | Turn raw business input into structured category/audience/goal data. Deterministic (keyword-rule based), not LLM-based, so it never breaks or drifts. Optionally validates the business on Google Places (see below). |
| `search_creators` | Find candidate creators by category/location. Auto-widens the search if too few match, so it never dead-ends. |
| `analyze_creator` | Deterministic 0–100 Creator Fit Score for one creator vs. one business, with a 5-part breakdown, strengths/weaknesses, and an LLM (or template) explanation. |
| `rank_creators` | Score + sort a list of candidate creators, best fit first. |
| `generate_outreach` | Personalized outreach DM draft for a business to send to a creator. Never sends anything automatically. |
| `generate_campaign` | Full campaign plan (name, strategy, content ideas, offer, budget allocation, expected reach) from a ranked creator shortlist. |
| `generate_video_script` *(optional/bonus)* | Turns one campaign content idea into a shot-by-shot short-form video script (scenes, timing, on-screen text, caption, hashtags, CTA) — free, instant, no video file produced. See below. |
| `analyze_online_presence` *(optional/bonus)* | Google/social/consistency visibility scoring, real when the business was Places-verified, simulated otherwise (`data_source` says which) — plus real nearby competitors when coordinates are available. |
| `log_creator_outreach` *(optional/bonus)* | Logs an outreach attempt as a HubSpot CRM contact + note, once the owner has actually decided to send it. Never sends anything itself — see below. |

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

## Google Places integration (optional, real-data enrichment)

If `GOOGLE_MAPS_API_KEY` is set, `backend/services/places_service.py`
validates the business against real Google Places data:

- **`analyze_business`** looks the business up (Find Place + Details) and,
  if found, merges in `google_verified`, `formatted_address`,
  `latitude`/`longitude`, `google_rating`, `google_review_count`, and
  `has_website`. Geocoding is a side effect of this lookup, not its
  purpose — the resolved coordinates/address are just retained on the
  business record for future local-creator and competitor discovery; they
  do **not** change the deterministic city-based locality scoring in
  `scoring_service.py`.
- **`analyze_online_presence`** uses the real rating/review count/website
  presence to compute `google_presence` when the business was verified,
  and runs a real Nearby Search around its coordinates to list actual
  `nearby_competitors`. The response always includes `data_source`
  (`"real"` or `"simulated"`) so the UI/demo never misrepresents simulated
  numbers as real — see the spec's "don't falsely represent" requirement.

Without the key (or if the business can't be found on Places, or the API
call fails for any reason), everything falls back to exactly the
simulated/deterministic behavior this app had before Places existed —
see `tests/test_places_integration.py`. Requires the legacy **Places
API** to be enabled for your key in Google Cloud Console (Find Place,
Details, and Nearby Search endpoints) — not just "Places API (New)".

**Keeping the key safe:** put it only in `.env` (already `.gitignore`d,
never `.env.example`), restrict it in Google Cloud Console to the Places
API + your server's IP, and never let it reach frontend/browser code —
a key embedded in client-side JS is visible to anyone via view-source.

## HubSpot integration (optional, outreach tracking)

If `HUBSPOT_ACCESS_TOKEN` is set, `backend/services/hubspot_service.py`
logs outreach as CRM activity: `log_creator_outreach` finds-or-creates a
HubSpot contact for the creator (keyed on their handle, since creators
have no email address) and attaches a note with the offer + message that
was sent. This is a **logging** step, not a sending step — it runs only
after generate_outreach has already produced a message and the business
owner has decided to actually use it, so many creators' outreach status
can be tracked in one place (HubSpot) instead of disappearing once this
session ends.

Uses a HubSpot **Service Key / Private App access token** (a static
Bearer token scoped to one account) — not OAuth, since this is a
single-account integration rather than a multi-tenant app. Required
scopes: `crm.objects.contacts.read`, `crm.objects.contacts.write`.

Without the token (or if the HubSpot API call fails for any reason),
`log_creator_outreach` returns `{"logged": false, "reason": "..."}`
rather than raising or crashing anything — see
`tests/test_hubspot_integration.py`.

## Video script generation (free/instant) + real video (planned, opt-in)

`generate_video_script` turns one of `generate_campaign`'s `content_ideas`
into an actual shot-by-shot script: timed scenes, what to film, on-screen
text, a caption, hashtags, and a CTA — something a business owner could
film on a phone, or hand to a creator as a brief. It's LLM-assisted with
a deterministic per-category template fallback (`_fallback_video_script`
in `marketing_service.py`), so it always returns a complete, usable
script even with no API key configured. No new env var needed — reuses
`ANTHROPIC_API_KEY`. No video file is produced by this tool.

A separate, explicitly opt-in tool to generate an actual video clip via
a real video-generation provider (e.g. Runway, Luma, Veo) is planned but
not yet built — video generation is an async job (30s–minutes, real
per-clip cost, no free tier), a fundamentally different reliability
profile than every synchronous tool above, so it's being kept as a
clearly separate, user-triggered feature rather than baked into the core
campaign flow.

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
POST /api/business/{business_id}/presence
POST /api/outreach/log
POST /api/video/script
POST /api/video/ad
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Currently reads from `frontend/src/data/mockData.ts` rather than this
backend -- wiring it up to the REST endpoints above is the next piece
of work.

## Tests

```bash
pytest tests/ -v
```

39 tests covering: score bounds (0–100), determinism, locality/audience/
budget scoring direction, zero-overlap content relevance, empty search
results (auto-widening), ranking determinism and ordering, unknown
business/creator lookups, outreach personalization (and no duplicate
fallback text), business-input edge cases, campaign budget compliance,
video script generation (fallback shape/timing, category-specific
templates, LLM parsing, graceful handling of malformed LLM output),
Places integration (real-data merge, graceful fallback with no key
or on lookup failure, real vs. simulated presence scoring), and HubSpot
integration (contact find-or-create, note attachment, graceful
degradation on missing token/API/unexpected failure) — the Places and
HubSpot tests monkeypatch their respective service modules directly, so
no real network calls or API keys are needed to run the suite.

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
