"""MCP tools for short-form video content (Reels/TikTok scripts, and
opt-in real AI-generated video ads)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.services import marketing_service, veo_service
from backend.services.business_store import get_business


class VideoScriptBusiness(BaseModel):
    business_name: str = Field(..., description="Business name")
    business_category: str = Field("", description="Business category, e.g. 'food'")
    location: str = Field("", description="Business location, e.g. 'Arcadia, CA'")


def register(mcp) -> None:
    @mcp.tool()
    def generate_video_script(
        business: VideoScriptBusiness,
        content_idea: str,
        platform: str = "TikTok / Instagram Reels",
        duration_seconds: int = 30,
    ) -> dict:
        """
        Turn one campaign content idea into a shot-by-shot short-form
        video script: scene-by-scene timing, what to film, on-screen
        text, a caption, hashtags, and a call to action -- something a
        business owner (or the creator they're working with) could
        actually film on a phone, not just a vague idea.

        Use this AFTER generate_campaign, once the owner picks one of
        its content_ideas to turn into an actual example Reel/TikTok.
        This is free and instant (LLM-assisted with a deterministic
        template fallback) -- it does not produce an actual video file.
        For a real generated video clip, a separate opt-in tool would be
        used once a video-generation provider is configured.

        Input: business (business_name, business_category, location),
        content_idea (the idea to script out), platform (default "TikTok
        / Instagram Reels"), duration_seconds (default 30).

        Returns: platform, duration_seconds, based_on_idea, scenes
        (list of {timing, shot, on_screen_text, audio_note}), caption,
        hashtags, cta.
        """
        return marketing_service.generate_video_script(
            business.model_dump(), content_idea, platform, duration_seconds
        )

    @mcp.tool()
    def generate_video_ad(
        business_id: str,
        offer: str,
        target_audience: str,
        style: str = "authentic, energetic, phone-shot",
        duration_seconds: int = 8,
    ) -> dict:
        """
        Generate a real short AI video advertisement for a business,
        using the full discovery pipeline: pulls in whatever real signals
        analyze_business already found on Google Places for this business
        (rating, review count, address, category) instead of starting
        from a blank business name, has the LLM turn that into a specific
        marketing angle and a short scene concept, synthesizes those
        scenes into one text-to-video prompt, then sends that prompt to
        Google Veo to actually generate an 8-second vertical video clip.

        Use this only when the business owner explicitly wants an actual
        AI-generated video ad (not just a script) -- unlike every other
        tool in this server, video generation is a slow async job (can
        take 30 seconds to a few minutes) with a real per-clip cost, so
        this should be a deliberate, opt-in action, not something called
        automatically as part of the normal recommend/campaign flow.

        Requires GOOGLE_VEO_API_KEY to be configured. If it isn't set, or
        generation fails/times out, the ad CONCEPT (angle, scenes, video
        prompt) is still returned -- only `video.status` reflects whether
        an actual clip was produced ("ready", "not_configured", "failed",
        or "timed_out"), so the concept alone is still useful even
        without a working video provider.

        Input: business_id (from analyze_business), offer (e.g. "20% off
        lunch this week"), target_audience, style (default "authentic,
        energetic, phone-shot"), duration_seconds (default 8).

        Returns: campaign_angle, scenes, video_prompt, and video
        ({"status", "video_url", "reason"}).
        """
        business = get_business(business_id)
        if business is None:
            raise ValueError(f"Could not find business '{business_id}'. Call analyze_business first.")

        concept = marketing_service.generate_ad_concept(business, offer, target_audience, style, duration_seconds)
        video = veo_service.generate_video(concept["video_prompt"], aspect_ratio="9:16", duration_seconds=duration_seconds)

        return {**concept, "video": video}
