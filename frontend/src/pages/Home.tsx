import { useState } from "react";
import { Send, ScanSearch, MapPin, Loader2, ArrowLeft, Star } from "lucide-react";
import type { BusinessInput, PlaceCandidate } from "../types";
import { exampleBusinesses, emptyBusinessInput } from "../data/exampleBusinesses";
import { AgentProgress } from "../components/ui";
import * as api from "../api";

interface HomeProps {
  loading: boolean;
  error: string | null;
  onSubmit: (business: BusinessInput) => void;
}

type Mode = "search" | "form";

export function Home({ loading, error, onSubmit }: HomeProps) {
  const [mode, setMode] = useState<Mode>("search");
  const [form, setForm] = useState<BusinessInput>(emptyBusinessInput);

  // General-search mode state
  const [query, setQuery] = useState("");
  const [searchBudget, setSearchBudget] = useState(300);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<PlaceCandidate[] | null>(null);
  const [extracted, setExtracted] = useState<{ goal: string; target_audience: string; business_name: string } | null>(null);

  function update<K extends keyof BusinessInput>(key: K, value: BusinessInput[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function submitForm(e: React.FormEvent) {
    e.preventDefault();
    if (!form.business_name.trim() || !form.location.trim() || loading) return;
    onSubmit(form);
  }

  function submitFromCandidate(candidate: PlaceCandidate) {
    onSubmit({
      business_name: candidate.name,
      business_type: extracted?.business_name || "",
      location: candidate.formatted_address,
      description: extracted?.goal || "",
      target_audience: extracted?.target_audience || "",
      goal: extracted?.goal || "",
      budget: searchBudget,
      place_id: candidate.place_id,
    });
  }

  async function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || searching || loading) return;
    setSearching(true);
    setSearchError(null);
    setCandidates(null);
    try {
      const result = await api.discoverBusiness(query);
      setExtracted(result.extracted);

      if (result.status === "found_one" && result.candidates[0]) {
        submitFromCandidate(result.candidates[0]);
        return;
      }
      if (result.status === "found_multiple") {
        setCandidates(result.candidates);
        return;
      }
      // not_found or not_configured -- fall back to the manual form,
      // pre-filled with whatever we could extract from the free text.
      setForm((f) => ({
        ...f,
        business_name: result.extracted.business_name,
        location: result.extracted.location_hint,
        goal: result.extracted.goal,
        target_audience: result.extracted.target_audience,
        budget: searchBudget,
      }));
      setMode("form");
      setSearchError(
        result.status === "not_configured"
          ? "Real business search isn't configured on this server -- continue with the details below."
          : `Couldn't find a real business matching "${result.extracted.business_name}" -- fill in the rest below to continue anyway.`,
      );
    } catch (err) {
      setSearchError((err as Error).message || "Search failed.");
    } finally {
      setSearching(false);
    }
  }

  const busy = loading || searching;

  return (
    <div className="agent-workbench">
      <section className="agent-desk" aria-labelledby="agent-title">
        <h1 id="agent-title">
          Small businesses don't need the biggest influencer.
          <br />
          <em>They need the right creator.</em>
        </h1>
        <p className="agent-introduction">
          Tell OUTTHERE about your business, and an AI agent will find, score, and rank real local
          creators by <strong>fit</strong> -- not follower count -- then build you a ready-to-run
          campaign.
        </p>

        <div className="tabs mb-5" role="tablist" aria-label="How to start">
          <button role="tab" aria-selected={mode === "search"} className={mode === "search" ? "active" : ""} onClick={() => setMode("search")} disabled={busy}>
            Describe your business
          </button>
          <button role="tab" aria-selected={mode === "form"} className={mode === "form" ? "active" : ""} onClick={() => setMode("form")} disabled={busy}>
            Fill out a form
          </button>
        </div>

        {mode === "search" && !candidates && (
          <form className="business-form" onSubmit={submitSearch} aria-busy={searching}>
            <label className="field-full">
              What's your business, and what do you need?
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="I am Ace Karaoke, and I'm looking to target a younger audience. What should I do?"
                disabled={busy}
                rows={3}
              />
            </label>
            <label>
              Monthly marketing budget ($)
              <input type="number" min={0} value={searchBudget} onChange={(e) => setSearchBudget(Number(e.target.value))} disabled={busy} />
            </label>
            <div className="form-actions">
              {searchError ? (
                <small style={{ color: "#a65e51" }}>{searchError}</small>
              ) : (
                <small className="muted">We'll search Google to find and confirm your real business.</small>
              )}
              <button className="btn primary" type="submit" disabled={!query.trim() || busy}>
                {searching ? <Loader2 size={15} className="working-icon" /> : <ScanSearch size={15} />}
                {searching ? "Searching..." : "Find My Business"}
              </button>
            </div>
          </form>
        )}

        {mode === "search" && candidates && (
          <div className="business-form" style={{ display: "block" }}>
            <button type="button" className="text-button mb-3" onClick={() => setCandidates(null)}>
              <ArrowLeft size={14} />
              Try a different search
            </button>
            <p className="mb-3">
              Found {candidates.length} real businesses matching <strong>{extracted?.business_name}</strong> -- which one is yours?
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {candidates.map((c) => (
                <button
                  key={c.place_id}
                  type="button"
                  className="panel"
                  style={{ textAlign: "left", cursor: "pointer", border: "1px solid var(--border)" }}
                  onClick={() => submitFromCandidate(c)}
                  disabled={loading}
                >
                  <strong>{c.name}</strong>
                  <div className="muted" style={{ fontSize: 13, marginTop: 4 }}>
                    <MapPin size={12} style={{ verticalAlign: -1, marginRight: 4 }} />
                    {c.formatted_address}
                  </div>
                  {c.rating != null && (
                    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                      <Star size={12} style={{ verticalAlign: -1, marginRight: 4 }} />
                      {c.rating}★ ({c.user_ratings_total} reviews)
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {mode === "form" && (
          <>
            <div className="example-chips" role="group" aria-label="Quick-fill an example business">
              {exampleBusinesses.map((b) => (
                <button key={b.business_name} type="button" onClick={() => setForm(b)} disabled={loading}>
                  <ScanSearch size={12} style={{ marginRight: 5, verticalAlign: -2 }} />
                  Try {b.business_name}
                </button>
              ))}
            </div>

            <form className="business-form" onSubmit={submitForm} aria-busy={loading}>
              <label>
                Business Name
                <input value={form.business_name} onChange={(e) => update("business_name", e.target.value)} placeholder="Sakura Bakery" disabled={loading} required />
              </label>
              <label>
                What do you sell?
                <input value={form.business_type} onChange={(e) => update("business_type", e.target.value)} placeholder="Korean bakery" disabled={loading} required />
              </label>
              <label>
                Where are you located?
                <input value={form.location} onChange={(e) => update("location", e.target.value)} placeholder="Arcadia, CA" disabled={loading} required />
              </label>
              <label>
                Monthly marketing budget ($)
                <input type="number" min={0} value={form.budget} onChange={(e) => update("budget", Number(e.target.value))} disabled={loading} />
              </label>
              <label>
                Who do you want to reach?
                <input value={form.target_audience} onChange={(e) => update("target_audience", e.target.value)} placeholder="Ages 18-30, local food lovers" disabled={loading} />
              </label>
              <label>
                What's your goal?
                <input value={form.goal} onChange={(e) => update("goal", e.target.value)} placeholder="More local customers" disabled={loading} />
              </label>
              <label className="field-full">
                Description
                <textarea value={form.description} onChange={(e) => update("description", e.target.value)} placeholder="Korean bakery selling pastries, coffee, and fresh bread." disabled={loading} />
              </label>
              <div className="form-actions">
                {error ? (
                  <small style={{ color: "#a65e51" }}>{error}</small>
                ) : (
                  <small className="muted">Real Google Places + AI agent, not a mock demo.</small>
                )}
                <button className="btn primary" type="submit" disabled={loading}>
                  {loading ? "Working..." : "Find My Creators"}
                  <Send size={15} />
                </button>
              </div>
            </form>
          </>
        )}

        {loading && <AgentProgress done={false} />}
      </section>

      {!busy && (
        <div className="footer-note">
          OUTTHERE
          <span>Get your business noticed.</span>
        </div>
      )}
    </div>
  );
}
