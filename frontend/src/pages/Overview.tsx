import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, LoaderCircle, Send, ScanSearch, ChartNoAxesCombined, Clapperboard, Fingerprint } from 'lucide-react';
import type { AgentActivity, Integration, Opportunity } from '../types';
import { ActivityFeed, OpportunityCard, SectionTitle, TrendChart } from '../components/ui';
import { promptSuggestions } from '../data/mockData';

interface OverviewProps {
  opportunities: Opportunity[];
  activities: AgentActivity[];
  integrations: Integration[];
  messages: { role: 'user' | 'pulse'; text: string }[];
  onAsk: (text: string) => void;
  onView: (o: Opportunity) => void;
  onBuild: (o: Opportunity) => void;
  onNavigate: (page: 'Opportunities' | 'Agent Activity' | 'Trends' | 'Integrations') => void;
}

export function Overview({ opportunities, activities, integrations, messages, onAsk, onView, onBuild, onNavigate }: OverviewProps) {
  const [draft, setDraft] = useState('');
  const [running, setRunning] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const connected = integrations.filter(i => i.connected);
  const latest = [...messages].reverse().find(m => m.role === 'pulse');
  const latestRequest = [...messages].reverse().find(m => m.role === 'user');
  function submit() {
    if (!draft.trim() || running) return;
    const command = draft.trim();
    setRunning(true);
    timer.current = setTimeout(() => {
      onAsk(command);
      setDraft('');
      setRunning(false);
    }, 550);
  }
  return <>
    <div className="agent-workbench">
      <section className="agent-desk" aria-labelledby="agent-title">
        <h1 id="agent-title">What should <em>Pulse</em> work on?</h1>
        <form className={`command-composer ${running ? 'is-running' : ''}`} onSubmit={e => { e.preventDefault(); submit(); }} aria-busy={running}>
          <label className="sr-only" htmlFor="agent-command">Give Pulse a direction</label>
          <textarea ref={input} id="agent-command" value={draft} onChange={e => setDraft(e.target.value)} disabled={running} placeholder="Find a trend that fits Hydra and suggest a campaign for our college audience…" onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(); } }} />
          <div className="composer-controls"><button className="btn primary" disabled={!draft.trim() || running} type="submit">{running ? <LoaderCircle size={15} className="working-icon" /> : <Send size={15} />}{running ? 'Working…' : 'Ask Pulse'}</button></div>
        </form>
        <div className="task-widgets" role="group" aria-label="Start a marketing task">
          {promptSuggestions.map((p, i) => { const Icon = [ScanSearch, ChartNoAxesCombined, Clapperboard, Fingerprint][i]; return <button key={p} title={p} onClick={() => { setDraft(p); input.current?.focus(); }} disabled={running}><Icon size={34} strokeWidth={1.35}/><span>{['Find opportunities', 'Research trends', 'Create a campaign', 'Explain the fit'][i]}</span></button>; })}
        </div>
        <div className="agent-response" aria-live="polite" aria-atomic="true">
          {running ? <div className="response-status"><LoaderCircle size={14} className="working-icon"/>Preparing your recommendation…</div> : latest ? <><div className="response-status"><Check size={14}/>Pulse / response ready</div><p>{latest.text}</p><button className="text-button" onClick={() => onNavigate('Opportunities')}>Review opportunities<ArrowRight size={14}/></button></> : null}
        </div>
      </section>

    </div>
    <section className="agent-output" aria-label="Agent recommendations">
      <SectionTitle title="Campaign ideas for Hydra"><button className="text-button" onClick={() => onNavigate('Opportunities')}>All opportunities<ArrowRight size={14}/></button></SectionTitle>
      <div className="recommendation-list">{opportunities.map((o, index) => <div className="ranked-opportunity" key={o.id}><div className="recommendation-index">{String(index + 1).padStart(2, '0')}</div><OpportunityCard opportunity={o} onView={() => onView(o)} compact/></div>)}</div>
      {!opportunities.length && <div className="empty-state"><h3>All recommendations reviewed</h3><p>Your dismissed opportunities are still available to restore.</p><button className="text-button" onClick={() => onNavigate('Opportunities')}>Open opportunities<ArrowRight size={14}/></button></div>}
    </section>
    <details className="research-details"><summary>Research summary</summary><section className="agent-results" aria-label="Agent results">
      <div><h2>Research, accumulated.</h2><dl className="results-summary"><div><dt>Active opportunities</dt><dd>{7 - (3 - opportunities.length)}</dd></div><div><dt>Trends monitored</dt><dd>126</dd></div><div><dt>Campaigns generated</dt><dd>14</dd></div><div><dt>Avg. audience match</dt><dd>84%</dd></div></dl></div>
      <div className="results-chart"><div className="chart-subtitle">Sunday Reset <span>30-day relative interest · +218%</span></div><TrendChart compact/><button className="text-button" onClick={() => onNavigate('Trends')}>Inspect trend evidence<ArrowRight size={14}/></button></div>
    </section>
    </details>
    <div className="footer-note">Pulse Marketing<span>Hydra · Demo data</span></div>
  </>;
}
