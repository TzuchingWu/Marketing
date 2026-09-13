"""
OUTTHERE FastAPI backend.

The MCP server (backend/mcp/server.py) is the primary AI-facing
interface and does all the real work: business analysis, creator
scoring, ranking, outreach, and campaign generation. This REST layer is
a thin wrapper around a single shared MCP ClientSession (see
backend/mcp/client_manager.py) started at app startup -- every endpoint
below calls an MCP tool rather than reimplementing logic, so FastAPI is
transport only, not a second copy of the business logic.

Run with: uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.mcp import client_manager
from backend.mcp.agent_client import run_agent_workflow
from backend.services import hubspot_service, llm_client, places_service, veo_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await client_manager.startup()
    try:
        yield
    finally:
        await client_manager.shutdown()


app = FastAPI(title="OUTTHERE API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BusinessInput(BaseModel):
    business_name: str
    business_type: str
    location: str
    description: str = ""
    target_audience: str = ""
    goal: str = ""
    budget: int = 0


class RankRequest(BaseModel):
    business_id: str
    creator_ids: list[str]


class SearchRequest(BaseModel):
    category: str
    location: str
    target_audience: str = ""
    max_results: int = 10


class OutreachRequest(BaseModel):
    business: dict
    creator: dict
    offer: str
    tone: str = "friendly"


class LogOutreachRequest(BaseModel):
    creator_handle: str
    creator_name: str = ""
    platform: str = ""
    business_name: str
    offer: str
    message: str


class VideoScriptRequest(BaseModel):
    business: dict
    content_idea: str
    platform: str = "TikTok / Instagram Reels"
    duration_seconds: int = 30


class VideoAdRequest(BaseModel):
    business_id: str
    offer: str
    target_audience: str
    style: str = "authentic, energetic, phone-shot"
    duration_seconds: int = 8


class CampaignRequest(BaseModel):
    business_id: str
    creator_ids: list[str]
    budget: int | None = None
    goal: str | None = None


async def _call(name: str, args: dict):
    parsed, is_error = await client_manager.call_tool(name, args)
    if is_error:
        detail = parsed if isinstance(parsed, str) else str(parsed)
        raise HTTPException(status_code=404, detail=detail)
    return parsed


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    tools = await client_manager.list_tools()
    return {"status": "ok", "mcp_tools": [t.name for t in tools]}


@app.get("/api/integrations/status")
async def integrations_status():
    """Real configured/not-configured status for each optional integration
    -- never exposes key values, just whether one is set. The core product
    (deterministic scoring, mock creator data) works with all of these off."""
    return {
        "anthropic": llm_client.is_available(),
        "google_maps": places_service.is_configured(),
        "hubspot": hubspot_service.is_configured(),
        "veo": veo_service.is_configured(),
    }


# ---------------------------------------------------------------------------
# Main agent workflow -- the primary "Find My Creators" action. Runs the
# full pipeline through the MCP server and returns an activity log of
# every tool call made along the way.
# ---------------------------------------------------------------------------

@app.post("/api/agent/recommend")
async def agent_recommend(business: BusinessInput):
    try:
        return await run_agent_workflow(business.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent workflow failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Direct MCP-tool-backed endpoints -- used for finer-grained frontend
# interactions (e.g. regenerating outreach for a single creator) without
# re-running the whole discovery workflow.
# ---------------------------------------------------------------------------

@app.post("/api/business/analyze")
async def analyze_business(business: BusinessInput):
    return await _call("analyze_business", {"business": business.model_dump()})


@app.post("/api/creators/search")
async def search_creators(req: SearchRequest):
    return await _call("search_creators", req.model_dump())


@app.post("/api/creators/rank")
async def rank_creators(req: RankRequest):
    return await _call("rank_creators", req.model_dump())


@app.post("/api/outreach/generate")
async def generate_outreach(req: OutreachRequest):
    return await _call("generate_outreach", req.model_dump())


@app.post("/api/campaign/generate")
async def generate_campaign(req: CampaignRequest):
    return await _call("generate_campaign", req.model_dump())


@app.post("/api/business/{business_id}/presence")
async def analyze_online_presence(business_id: str):
    return await _call("analyze_online_presence", {"business_id": business_id})


@app.post("/api/outreach/log")
async def log_creator_outreach(req: LogOutreachRequest):
    return await _call("log_creator_outreach", req.model_dump())


@app.post("/api/video/script")
async def generate_video_script(req: VideoScriptRequest):
    return await _call("generate_video_script", req.model_dump())


@app.post("/api/video/ad")
async def generate_video_ad(req: VideoAdRequest):
    # Video generation is a slow async job (can take minutes) -- this
    # request will hang open for the duration rather than returning
    # immediately like every other endpoint.
    return await _call("generate_video_ad", req.model_dump())
