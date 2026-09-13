import { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Clapperboard,
  Copy,
  Film,
  Loader2,
  RotateCcw,
  Target,
  Users,
} from "lucide-react";
import type { CreatorMatch, PresenceResult, RecommendResult, VideoAdResult, VideoScript } from "../types";
import { Badge, Modal, ScoreBreakdownBars, SectionTitle, CreatorCard } from "../components/ui";
import * as api from "../api";

/** The agent's free-text summary sometimes comes back with markdown
 * emphasis (**bold**) from the LLM -- this is plain text, not rendered
 * markdown, so strip the literal asterisks rather than showing them. */
function stripMarkdown(text: string): string {
  return text.replace(/\*\*(.+?)\*\*/g, "$1").replace(/(?<!\*)\*(?!\*)([^*]+)\*(?!\*)/g, "$1");
}

interface ResultsProps {
  result: RecommendResult;
  onNewSearch: () => void;
  onToast: (msg: string) => void;
}

export function Results({ result, onNewSearch, onToast }: ResultsProps) {
  const { business, creators, campaign } = result;
  const [detailCreator, setDetailCreator] = useState<CreatorMatch | null>(null);
  const [outreachCreator, setOutreachCreator] = useState<CreatorMatch | null>(null);
  const [presence, setPresence] = useState<PresenceResult | null>(null);
  const [presenceLoading, setPresenceLoading] = useState(false);
  const [scriptResult, setScriptResult] = useState<{ idea: string; script: VideoScript } | null>(null);
  const [scriptLoading, setScriptLoading] = useState<string | null>(null);
  const [videoAd, setVideoAd] = useState<VideoAdResult | null>(null);
  const [videoAdLoading, setVideoAdLoading] = useState(false);

  const opportunityScore = creators.length
    ? Math.round(creators.reduce((sum, c) => sum + c.fit_score, 0) / creators.length)
    : 0;

  async function checkPresence() {
    if (!business.business_id) return;
    setPresenceLoading(true);
    try {
      setPresence(await api.analyzePresence(business.business_id));
    } catch (err) {
      onToast(`Couldn't check online presence: ${(err as Error).message}`);
    } finally {
      setPresenceLoading(false);
    }
  }

  async function generateScript(idea: string) {
    setScriptLoading(idea);
    try {
      const script = await api.generateVideoScript(
        { business_name: business.business_name, business_category: business.business_category, location: business.location },
        idea,
      );
      setScriptResult({ idea, script });
    } catch (err) {
      onToast(`Couldn't generate video script: ${(err as Error).message}`);
    } finally {
      setScriptLoading(null);
    }
  }

  async function generateAd() {
    if (!business.business_id) return;
    setVideoAdLoading(true);
    setVideoAd(null);
    try {
      const ad = await api.generateVideoAd({
        business_id: business.business_id,
        offer: campaign.offers[0] || "Special offer this week",
        target_audience: business.target_interests.join(", ") || "local customers",
      });
      setVideoAd(ad);
    } catch (err) {
      onToast(`Video ad generation failed: ${(err as Error).message}`);
    } finally {
      setVideoAdLoading(false);
    }
  }

  return (
    <>
      <button className="text-button mb-5" onClick={onNewSearch}>
        <ArrowLeft size={15} />
        New search
      </button>

      <div className="detail-heading">
        <div>
          <Badge tone={business.google_verified ? "green" : "neutral"}>
            {business.google_verified ? "Google Verified" : "Demo Data"}
          </Badge>
          <h1>{business.business_name}</h1>
          <p>
            {business.location} · {business.sub_category || business.business_category}
            {business.google_verified && business.google_rating ? (
              <> · {business.google_rating}★ ({business.google_review_count} reviews)</>
            ) : null}
          </p>
        </div>
        <button className="btn compact" onClick={checkPresence} disabled={presenceLoading}>
          {presenceLoading ? <Loader2 size={14} className="working-icon" /> : <Target size={14} />}
          Check Online Presence
        </button>
      </div>

      <div className="opportunity-score-banner">
        <div>
          <small>CREATOR MARKETING OPPORTUNITY</small>
          <strong>{opportunityScore} / 100</strong>
        </div>
        <p className="muted" style={{ maxWidth: 420 }}>{stripMarkdown(result.agent_summary)}</p>
      </div>

      {presence && (
        <section className="panel mb-5">
          <SectionTitle title="Online Presence">
            <Badge tone={presence.data_source === "real" ? "green" : "neutral"}>
              {presence.data_source === "real" ? "Real Google data" : "Simulated"}
            </Badge>
          </SectionTitle>
          <div className="detail-metrics" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
            <div className="metric"><span>Google Presence</span><strong>{presence.google_presence}</strong></div>
            <div className="metric"><span>Social Presence</span><strong>{presence.social_presence}</strong></div>
            <div className="metric"><span>Content Consistency</span><strong>{presence.content_consistency}</strong></div>
            <div className="metric"><span>Overall Visibility</span><strong>{presence.overall_visibility}</strong></div>
          </div>
          <ul className="mt-3" style={{ paddingLeft: 18, fontSize: 13, lineHeight: 1.7 }}>
            {presence.recommendations.map((r) => <li key={r}>{r}</li>)}
          </ul>
          {presence.nearby_competitors.length > 0 && (
            <div className="competitor-list">
              <span className="eyebrow">NEARBY COMPETITORS (REAL)</span>
              {presence.nearby_competitors.map((c) => (
                <div className="competitor-row" key={c.place_id}>
                  <span>{c.name} · {c.vicinity}</span>
                  <span>{c.rating ? `${c.rating}★ (${c.user_ratings_total})` : ""}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section aria-label="Top creator matches">
        <SectionTitle eyebrow="RANKED BY FIT, NOT FOLLOWER COUNT" title="Top Creator Matches" />
        <div className="recommendation-list">
          {creators.map((c, i) => (
            <div className="ranked-opportunity" key={c.creator_id}>
              <div className="recommendation-index">{String(i + 1).padStart(2, "0")}</div>
              <CreatorCard
                creator={c}
                onView={() => setDetailCreator(c)}
                onOutreach={() => setOutreachCreator(c)}
              />
            </div>
          ))}
        </div>
      </section>

      <section className="panel mt-5">
        <SectionTitle eyebrow={`$${campaign.budget} BUDGET`} title={campaign.campaign_name} />
        <p className="muted">{campaign.strategy}</p>
        <div className="detail-metrics" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          <div className="metric"><span>Estimated Spend</span><strong>${campaign.estimated_spend}</strong></div>
          <div className="metric"><span>Expected Reach</span><strong>{campaign.expected_reach.toLocaleString()}</strong></div>
          <div className="metric"><span>Creators</span><strong>{campaign.creators.length}</strong></div>
        </div>
        <div className="mt-5">
          <span className="eyebrow">CONTENT IDEAS</span>
          <ul style={{ paddingLeft: 18, fontSize: 14, lineHeight: 1.9 }}>
            {campaign.content_ideas.map((idea) => (
              <li key={idea} className="flex items-center justify-between gap-2">
                <span style={{ flex: 1, minWidth: 0 }}>{idea}</span>
                <button className="btn compact" style={{ flexShrink: 0 }} onClick={() => generateScript(idea)} disabled={scriptLoading === idea}>
                  {scriptLoading === idea ? <Loader2 size={13} className="working-icon" /> : <Clapperboard size={13} />}
                  Script
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className="insight mt-5">
          <Film size={20} />
          <div>
            <strong>Want a real AI-generated video ad?</strong>
            <p>Uses Google Veo -- an async job that can take 30s to a few minutes and has a real cost per clip.</p>
            <button className="btn primary mt-2" onClick={generateAd} disabled={videoAdLoading}>
              {videoAdLoading ? <Loader2 size={14} className="working-icon" /> : <Film size={14} />}
              {videoAdLoading ? "Generating (this can take a while)..." : "Generate AI Video Ad"}
            </button>
          </div>
        </div>
        {videoAd && <VideoAdPanel ad={videoAd} />}
      </section>

      {detailCreator && (
        <CreatorDetailModal
          creator={detailCreator}
          onClose={() => setDetailCreator(null)}
          onOutreach={() => {
            setOutreachCreator(detailCreator);
            setDetailCreator(null);
          }}
        />
      )}
      {outreachCreator && (
        <OutreachModal
          business={business}
          creator={outreachCreator}
          onClose={() => setOutreachCreator(null)}
          onToast={onToast}
        />
      )}
      {scriptResult && <VideoScriptModal idea={scriptResult.idea} script={scriptResult.script} onClose={() => setScriptResult(null)} />}
    </>
  );
}

function CreatorDetailModal({
  creator: c,
  onClose,
  onOutreach,
}: {
  creator: CreatorMatch;
  onClose: () => void;
  onOutreach: () => void;
}) {
  return (
    <Modal title={c.handle} onClose={onClose}>
      <div className="modal-body">
        <div className="flex justify-between items-center mb-3">
          <span className="score">{c.fit_score}<small> / 100 fit score</small></span>
          <Badge tone={c.fit_score >= 85 ? "green" : "amber"}>{c.recommendation}</Badge>
        </div>
        <p className="muted">{c.bio}</p>
        <div className="tags mt-3">
          <span>{c.platform}</span>
          <span>{c.location}</span>
          {c.categories.map((cat) => <span key={cat}>{cat}</span>)}
        </div>

        <div className="audience-icon mt-5"><Users size={24} /></div>
        <h3>{c.followers.toLocaleString()} followers</h3>
        <p className="muted">
          {c.audience_local_percentage}% local audience · {c.audience_age_range} primary age range ·{" "}
          {c.engagement_rate}% engagement
        </p>
        <p className="muted">Estimated collaboration: ${c.estimated_collaboration_cost}</p>

        <span className="eyebrow mt-5" style={{ display: "block" }}>SCORE BREAKDOWN</span>
        <ScoreBreakdownBars breakdown={c.score_breakdown} />

        <div className="insight mt-3">
          <Target size={18} />
          <div>
            <strong>Why OUTTHERE recommends them</strong>
            <p>{c.explanation}</p>
          </div>
        </div>
        {c.strengths.length > 0 && (
          <div className="tags mt-3">{c.strengths.map((s) => <span key={s}>{s}</span>)}</div>
        )}

        <button className="btn primary w-full mt-5" onClick={onOutreach}>
          Generate Outreach
          <ArrowRight size={16} />
        </button>
      </div>
    </Modal>
  );
}

function OutreachModal({
  business,
  creator,
  onClose,
  onToast,
}: {
  business: RecommendResult["business"];
  creator: CreatorMatch;
  onClose: () => void;
  onToast: (msg: string) => void;
}) {
  const [tone, setTone] = useState("friendly");
  const [offer, setOffer] = useState(`Free tasting + $${Math.min(150, creator.estimated_collaboration_cost)} sponsored post`);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [logging, setLogging] = useState(false);

  async function generate() {
    setLoading(true);
    try {
      const res = await api.generateOutreach(
        { name: business.business_name, description: business.description, goal: business.marketing_goal, location: business.location },
        { handle: creator.handle, name: creator.name, category: creator.categories, location: creator.location },
        offer,
        tone,
      );
      setMessage(res.message);
    } catch (err) {
      onToast(`Couldn't generate outreach: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  async function logToCrm() {
    setLogging(true);
    try {
      const res = await api.logOutreach({
        creator_handle: creator.handle,
        creator_name: creator.name,
        platform: creator.platform,
        business_name: business.business_name,
        offer,
        message,
      });
      onToast(res.logged ? "Logged to HubSpot CRM." : `Not logged: ${res.reason}`);
    } catch (err) {
      onToast(`Couldn't log outreach: ${(err as Error).message}`);
    } finally {
      setLogging(false);
    }
  }

  return (
    <Modal title={`Outreach to ${creator.handle}`} onClose={onClose}>
      <div className="modal-body">
        <label className="mb-3" style={{ display: "block" }}>
          <span className="eyebrow" style={{ display: "block", marginBottom: 6 }}>OFFER</span>
          <input
            className="w-full"
            style={{ padding: "8px 10px", border: "1px solid var(--border)", borderRadius: 6 }}
            value={offer}
            onChange={(e) => setOffer(e.target.value)}
          />
        </label>
        <div className="flex gap-2 mb-3">
          {["friendly", "professional", "playful"].map((t) => (
            <button key={t} className={`btn compact ${tone === t ? "primary" : ""}`} onClick={() => setTone(t)}>
              {t}
            </button>
          ))}
        </div>
        {message ? (
          <div className="hook-field">
            <p>{message}</p>
          </div>
        ) : (
          <p className="muted">Click generate to draft a personalized message.</p>
        )}
        <div className="flex gap-2 mt-5">
          <button className="btn primary" onClick={generate} disabled={loading}>
            {loading ? <Loader2 size={14} className="working-icon" /> : <RotateCcw size={14} />}
            {message ? "Regenerate" : "Generate"}
          </button>
          {message && (
            <>
              <button className="btn" onClick={() => { navigator.clipboard.writeText(message); onToast("Copied to clipboard."); }}>
                <Copy size={14} />
                Copy
              </button>
              <button className="btn" onClick={logToCrm} disabled={logging}>
                {logging ? <Loader2 size={14} className="working-icon" /> : <Check size={14} />}
                Log to CRM
              </button>
            </>
          )}
        </div>
        <small className="muted mt-3" style={{ display: "block" }}>
          Never sent automatically -- review and send it yourself.
        </small>
      </div>
    </Modal>
  );
}

function VideoScriptModal({ idea, script, onClose }: { idea: string; script: VideoScript; onClose: () => void }) {
  return (
    <Modal title={`Video Script: ${idea}`} onClose={onClose}>
      <div className="modal-body">
        <p className="muted">{script.platform} · {script.duration_seconds}s</p>
        <div className="scene-list">
          {script.scenes.map((s, i) => (
            <div className="scene-item" key={i}>
              <span className="scene-timing">{s.timing}</span>
              <div>
                <p>{s.shot}</p>
                {s.on_screen_text && <p className="scene-text">"{s.on_screen_text.replace(/^["']+|["']+$/g, "")}"</p>}
              </div>
            </div>
          ))}
        </div>
        <span className="eyebrow">CAPTION</span>
        <p>{script.caption}</p>
        <span className="eyebrow">HASHTAGS</span>
        <div className="tags mb-3">{script.hashtags.map((h) => <span key={h}>{h}</span>)}</div>
        <span className="eyebrow">CTA</span>
        <p>{script.cta}</p>
      </div>
    </Modal>
  );
}

function VideoAdPanel({ ad }: { ad: VideoAdResult }) {
  return (
    <div className="video-result">
      <span className="eyebrow">{ad.campaign_angle}</span>
      {ad.video.status === "ready" && ad.video.video_url ? (
        <video controls src={ad.video.video_url} />
      ) : (
        <p className="muted mt-2">
          {ad.video.status === "not_configured" && "Video generation isn't configured on the backend -- here's the concept and prompt that would have been used."}
          {ad.video.status === "failed" && `Video generation failed: ${ad.video.reason}`}
          {ad.video.status === "timed_out" && "Video generation is taking longer than expected -- try again shortly."}
        </p>
      )}
      <details className="mt-3">
        <summary className="text-button" style={{ display: "inline-flex" }}>View generated prompt</summary>
        <p className="muted mt-2">{ad.video_prompt}</p>
      </details>
    </div>
  );
}
