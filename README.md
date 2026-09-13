# OUTTHERE

**Get your business noticed.**

An AI-powered marketing agent for small businesses. Instead of chasing the
biggest influencer, OUTTHERE finds the *right* local content creator for
your business — ranked by fit, not follower count — and turns that into a
ready-to-run campaign.

> This README covers the **backend** in depth. A React/Vite frontend in
> `frontend/` is wired up to it end-to-end (real API calls, not mock
> data) — see the Frontend section under "Running it".

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
                FRONTEND (frontend/)
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
| `discover_business_from_text` *(optional/bonus)* | "General search" entry point: extracts a business name + goal/audience from free text (e.g. "I am Ace Karaoke, target a younger audience") and searches Google Places for real matches in one call. See below. |
| `find_real_business` *(optional/bonus)* | Search Google Places for businesses matching a name, for disambiguation when a name isn't unique (a chain with multiple real locations). |
| `analyze_business` | Turn raw business input into structured category/audience/goal data. Deterministic (keyword-rule based), not LLM-based, so it never breaks or drifts. Optionally validates the business on Google Places, either by fuzzy name match or an exact `place_id` from `find_real_business`. |
| `search_creators` | Find candidate creators by category/location from the demo dataset. Auto-widens the search if too few match, so it never dead-ends. |
| `analyze_creator` | Deterministic 0–100 Creator Fit Score for one creator vs. one business, with a 5-part breakdown, strengths/weaknesses, and an LLM (or template) explanation. |
| `rank_creators` | Score + sort a list of candidate creators, best fit first. |
| `search_real_creators` *(optional/bonus)* | Search the live web (OpenAI web search) for REAL, currently-active creators instead of the demo dataset, then score and rank them the same way. See below. |
| `generate_outreach` | Personalized outreach DM draft for a business to send to a creator. Never sends anything automatically. |
| `generate_campaign` | Full campaign plan (name, strategy, content ideas, offer, budget allocation, expected reach) from a ranked creator shortlist. |
| `generate_video_script` *(optional/bonus)* | Turns one campaign content idea into a shot-by-shot short-form video script (scenes, timing, on-screen text, caption, hashtags, CTA) — free, instant, no video file produced. |
| `generate_video_ad` *(optional/bonus)* | Builds a marketing angle + video prompt grounded in real Places signals, then generates an actual short AI video clip via Google Veo. Slow async job, real cost — explicitly opt-in, never called automatically. See below. |
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

`backend/data/creators.json` — 29 fictional creator profiles across food,
coffee, fashion, beauty, fitness, gaming, tech, travel, and nightlife,
spread across Arcadia, Monrovia, Pasadena, San Gabriel, Alhambra, Temple
City, Rosemead, El Monte, Glendale, City of Industry, and Los Angeles.
**Clearly labeled as demo/simulated data** (see the `_note` field) —
these are not real people or accounts. For real creators instead of this
dataset, see `search_real_creators` below.

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

## Video script generation (free/instant) + real video ads (Veo, opt-in)

`generate_video_script` turns one of `generate_campaign`'s `content_ideas`
into an actual shot-by-shot script: timed scenes, what to film, on-screen
text, a caption, hashtags, and a CTA — something a business owner could
film on a phone, or hand to a creator as a brief. It's LLM-assisted with
a deterministic per-category template fallback (`_fallback_video_script`
in `marketing_service.py`), so it always returns a complete, usable
script even with no API key configured. No new env var needed — reuses
`ANTHROPIC_API_KEY`. No video file is produced by this tool.

`generate_video_ad` goes further: it builds a specific marketing angle
and a single dense text-to-video prompt (grounded in real Places signals
like rating/review count when available, via `generate_ad_concept` in
`marketing_service.py`), then sends that prompt to **Google Veo**
(`backend/services/veo_service.py`) to actually generate a short vertical
video clip. This is a genuinely different reliability profile than every
other tool here: it's an async job (submit → poll → done, 30s–a few
minutes) with real per-clip cost and no free tier, so it's kept
explicitly opt-in — the agent is instructed to never call it
automatically as part of the normal recommend flow. Without
`GOOGLE_VEO_API_KEY` (or if generation fails/times out), the concept and
prompt are still returned — only `video.status` reflects whether an
actual clip was produced (`"ready"`, `"not_configured"`, `"failed"`, or
`"timed_out"`), so the concept alone is still useful.

Uses the Gemini API's `web_search`-style long-running-operation endpoint
with simple API-key auth (not Vertex AI's OAuth/service-account path).
Run `GET https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY`
to see which Veo models your key actually has access to.

## General search: real business discovery (optional, Google Places)

Instead of filling out a structured form, a user can type free text like
*"I am Ace Karaoke, I want to target a younger audience"*. `discover_business_from_text`
handles this in one call:

1. `extract_business_intent` (in `marketing_service.py`) pulls a business
   name, location hint, goal, and target audience out of the free text —
   LLM-assisted with a regex fallback (`_fallback_extract_intent`) so it
   always returns something searchable even offline.
2. `places_service.search_businesses` runs a Google Places Text Search
   for that name, returning **multiple** real candidates rather than
   silently picking one — e.g. searching "Ace Karaoke" genuinely returns
   two different real locations (San Gabriel and City of Industry, CA).
3. The response's `status` tells the caller what to do next:
   `"found_one"` → proceed directly; `"found_multiple"` → show the
   candidates and ask the user which real business they meant;
   `"not_found"` / `"not_configured"` → fall back to the manual form.
4. Once a specific business is confirmed, `analyze_business` accepts that
   exact `place_id` and fetches its details directly (`get_place_details`)
   — skipping fuzzy name matching entirely, so the analysis can't drift
   to a different, similarly-named business than the one actually picked.
   Its real address is parsed down to a clean `"City, ST"` string (not
   the raw street address) so locality scoring works correctly.

This is the same Google Places integration described above — no new key
needed, just a different (multi-result, disambiguating) way of using it.

## Real creator discovery via web search (optional, OpenAI)

`search_real_creators` searches the live web (via OpenAI's Responses API
`web_search` tool, in `backend/services/web_search_service.py`) for
real, currently-active creators instead of the demo dataset, then scores
and ranks them with the same deterministic Creator Fit Score.

**Important honesty constraint:** web search can reliably verify a
creator's platform, handle, name, bio, and (sometimes) an approximate
follower count. It **cannot** reliably verify engagement rate, audience
demographics, or collaboration cost — those aren't public web data,
they're exactly what the demo dataset fabricates for realism. This tool
never asks the model to guess those; they come back `null`, and
`scoring_service.py` treats unknown fields as a *neutral* assumption
(e.g. ~5% engagement) rather than *confirmed zero*, so a real creator
isn't unfairly crushed in scoring just for having unverifiable data.
Every result is tagged `"source": "web_search"` and `"verified"`
(whether a source URL was actually found).

Requires `OPEN_AI_WEBSEARCH_API_KEY` — note this needs **billing enabled**
on the OpenAI platform account (`platform.openai.com/settings/organization/billing`);
like Veo, there's no free tier and `insufficient_quota` errors happen on
the very first call otherwise. Without the key, or if search finds
nothing, this returns `[]` and callers should fall back to
`search_creators`.

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
GET  /api/integrations/status    real configured/not-configured status per integration
POST /api/agent/recommend        full workflow, real MCP round trip, returns activity_log
POST /api/business/discover      general search: free text -> extracted intent + real Places candidates
POST /api/business/find-real     search Google Places by name for disambiguation
POST /api/business/analyze
POST /api/creators/search
POST /api/creators/search-real   real creators via OpenAI web search, scored and ranked
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

Points at `http://127.0.0.1:8000` by default (`VITE_API_BASE_URL` to
override) and drives the real backend end-to-end: business input (a
structured form, or free-text "general search" with real-business
disambiguation) → ranked creator cards with score breakdowns → outreach
generation/CRM logging → video script/ad generation. The Agent Activity
and Integrations pages show real backend state, not demo toggles.

## Tests

```bash
pytest tests/ -v
```

72 tests covering: score bounds (0–100), determinism, locality/audience/
budget scoring direction (including neutral-not-zero handling for
unknown fields, e.g. web-search-discovered creators), zero-overlap
content relevance, empty search results (auto-widening), ranking
determinism and ordering, unknown business/creator lookups, outreach
personalization (and no duplicate fallback text), business-input edge
cases, campaign budget compliance, video script generation (fallback
shape/timing, category-specific templates, LLM parsing, graceful
handling of malformed LLM output), Places integration (real-data merge,
multi-result search disambiguation, address-to-city parsing, graceful
fallback with no key or on lookup failure, real vs. simulated presence
scoring), general-search intent extraction (LLM + regex fallback),
HubSpot integration (contact find-or-create, note attachment, graceful
degradation on missing token/API/unexpected failure), Veo video
generation (submit/poll/ready/timeout/error paths), and web-search
creator discovery (JSON/markdown-fence parsing, missing-handle
filtering, max-results, never-raises) — all of these monkeypatch their
respective service modules directly, so no real network calls or API
keys are needed to run the suite.

## Demo reliability

- No external API is required. With no `ANTHROPIC_API_KEY`, every tool
  still works via deterministic scoring + templated text.
- `search_creators` never returns empty — it widens the search instead.
- Unknown business/creator ids raise a clear MCP tool error (surfaced as
  HTTP 404), not a crash.
- The MCP server is spawned once per app lifetime and reused across
  requests (see `client_manager.py`), so in-memory business state stays
  consistent without needing a database.

## Not built yet (P2 / nice-to-have)

- Creator comparison, budget optimization UI, campaign regeneration
  prompts, export-to-file.
- Wiring `search_real_creators`'s web-search results into the default
  `CreatorProvider` path (currently a separate opt-in tool/endpoint,
  rather than swapped in as the default data source).
- Frontend automated tests (the old Hydra-flow test file was removed
  when the frontend was rebuilt for OUTTHERE's actual domain; backend
  coverage is thorough, frontend coverage currently relies on manual
  and live-browser verification).
