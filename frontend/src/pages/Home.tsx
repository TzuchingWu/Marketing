import { useState } from "react";
import { Send, ScanSearch } from "lucide-react";
import type { BusinessInput } from "../types";
import { exampleBusinesses, emptyBusinessInput } from "../data/exampleBusinesses";
import { AgentProgress } from "../components/ui";

interface HomeProps {
  loading: boolean;
  error: string | null;
  onSubmit: (business: BusinessInput) => void;
}

export function Home({ loading, error, onSubmit }: HomeProps) {
  const [form, setForm] = useState<BusinessInput>(emptyBusinessInput);

  function update<K extends keyof BusinessInput>(key: K, value: BusinessInput[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.business_name.trim() || !form.location.trim() || loading) return;
    onSubmit(form);
  }

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

        <div className="example-chips" role="group" aria-label="Quick-fill an example business">
          {exampleBusinesses.map((b) => (
            <button key={b.business_name} type="button" onClick={() => setForm(b)} disabled={loading}>
              <ScanSearch size={12} style={{ marginRight: 5, verticalAlign: -2 }} />
              Try {b.business_name}
            </button>
          ))}
        </div>

        <form className="business-form" onSubmit={submit} aria-busy={loading}>
          <label>
            Business Name
            <input
              value={form.business_name}
              onChange={(e) => update("business_name", e.target.value)}
              placeholder="Sakura Bakery"
              disabled={loading}
              required
            />
          </label>
          <label>
            What do you sell?
            <input
              value={form.business_type}
              onChange={(e) => update("business_type", e.target.value)}
              placeholder="Korean bakery"
              disabled={loading}
              required
            />
          </label>
          <label>
            Where are you located?
            <input
              value={form.location}
              onChange={(e) => update("location", e.target.value)}
              placeholder="Arcadia, CA"
              disabled={loading}
              required
            />
          </label>
          <label>
            Monthly marketing budget ($)
            <input
              type="number"
              min={0}
              value={form.budget}
              onChange={(e) => update("budget", Number(e.target.value))}
              disabled={loading}
            />
          </label>
          <label>
            Who do you want to reach?
            <input
              value={form.target_audience}
              onChange={(e) => update("target_audience", e.target.value)}
              placeholder="Ages 18-30, local food lovers"
              disabled={loading}
            />
          </label>
          <label>
            What's your goal?
            <input
              value={form.goal}
              onChange={(e) => update("goal", e.target.value)}
              placeholder="More local customers"
              disabled={loading}
            />
          </label>
          <label className="field-full">
            Description
            <textarea
              value={form.description}
              onChange={(e) => update("description", e.target.value)}
              placeholder="Korean bakery selling pastries, coffee, and fresh bread."
              disabled={loading}
            />
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

        {loading && <AgentProgress done={false} />}
      </section>

      {!loading && (
        <div className="footer-note">
          OUTTHERE
          <span>Get your business noticed.</span>
        </div>
      )}
    </div>
  );
}
