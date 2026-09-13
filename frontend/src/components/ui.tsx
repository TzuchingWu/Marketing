import {
  ArrowRight,
  Search,
  Activity,
  Leaf,
  Timer,
  Check,
  X,
  MapPin,
  Target,
  MessageCircle,
  DollarSign,
  Users,
  Loader2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { AgentActivityItem, CreatorMatch, ScoreBreakdown } from "../types";

export function Badge({ children, tone = "green" }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function SectionTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}

export function Metric({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
}) {
  return (
    <div className="metric">
      <div className="flex items-center justify-between">
        <span>{label}</span>
        {icon}
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

const SCORE_BREAKDOWN_LABELS: { key: keyof ScoreBreakdown; label: string; max: number }[] = [
  { key: "locality", label: "Locality", max: 30 },
  { key: "audience_match", label: "Audience Match", max: 25 },
  { key: "content_relevance", label: "Content Relevance", max: 20 },
  { key: "engagement", label: "Engagement", max: 15 },
  { key: "budget_fit", label: "Budget Fit", max: 10 },
];

export function ScoreBreakdownBars({ breakdown }: { breakdown: ScoreBreakdown }) {
  return (
    <div className="detail-metrics">
      {SCORE_BREAKDOWN_LABELS.map(({ key, label, max }) => (
        <div className="metric" key={key}>
          <span>{label}</span>
          <strong>
            {breakdown[key]}
            <small style={{ fontSize: 12, fontWeight: 400 }}> / {max}</small>
          </strong>
          <div className="fit-bar">
            <span style={{ width: `${Math.min(100, (breakdown[key] / max) * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function CreatorCard({
  creator: c,
  rank,
  onView,
  onOutreach,
}: {
  creator: CreatorMatch;
  rank?: number;
  onView: () => void;
  onOutreach: () => void;
}) {
  return (
    <article className="opportunity-card">
      <div className="opportunity-content" style={{ padding: rank ? "21px 21px 21px" : undefined }}>
        <div className="flex justify-between items-center">
          <Badge tone={c.fit_score >= 85 ? "green" : c.fit_score >= 70 ? "amber" : "neutral"}>
            <span className="dot" />
            {c.recommendation}
          </Badge>
          <span className="score">
            {c.fit_score}
            <small> / 100 fit score</small>
          </span>
        </div>
        <h3>
          {rank ? `#${rank} ` : ""}
          {c.handle}
        </h3>
        <div className="card-stats">
          <span>
            <Users size={13} />
            <b>{c.followers.toLocaleString()}</b> followers
          </span>
          <span>
            <b>{c.engagement_rate}%</b> engagement
          </span>
          <span>
            <DollarSign size={13} />
            <b>${c.estimated_collaboration_cost}</b> est.
          </span>
        </div>
        <p>{c.bio}</p>
        <div className="tags">
          <span>{c.platform}</span>
          <span>{c.location}</span>
          {c.categories.slice(0, 2).map((cat) => (
            <span key={cat}>{cat}</span>
          ))}
        </div>
        <button className="card-link" onClick={onView}>
          View Creator
          <ArrowRight size={16} />
        </button>
        <div className="flex gap-2 mt-3">
          <button className="btn primary compact" onClick={onOutreach}>
            <MessageCircle size={14} />
            Generate Outreach
          </button>
        </div>
      </div>
    </article>
  );
}

export function AgentProgress({ done }: { done: boolean }) {
  const steps = [
    "Understanding your business",
    "Finding relevant creators",
    "Scoring creator fit",
    "Building your campaign",
  ];
  const [activeStep, setActiveStep] = useState(0);
  useEffect(() => {
    if (done) {
      setActiveStep(steps.length);
      return;
    }
    const interval = setInterval(() => {
      setActiveStep((s) => Math.min(s + 1, steps.length - 1));
    }, 1400);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done]);
  return (
    <div className="agent-response" aria-live="polite" aria-atomic="true">
      {steps.map((label, i) => (
        <div className="response-status" key={label}>
          {i < activeStep ? (
            <Check size={14} />
          ) : i === activeStep ? (
            <Loader2 size={14} className="working-icon" />
          ) : (
            <span style={{ width: 14, display: "inline-block" }} />
          )}
          {label}
          {i < activeStep ? "..." : i === activeStep ? "..." : ""}
        </div>
      ))}
    </div>
  );
}

export function ActivityFeed({
  items,
  short = false,
  showDescriptions = false,
}: {
  items: AgentActivityItem[];
  short?: boolean;
  showDescriptions?: boolean;
}) {
  return (
    <div className="activity-feed">
      {items.slice(0, short ? 3 : undefined).map((a, i) => (
        <div className="activity-item" key={a.id}>
          <div className={`activity-symbol ${i === 0 ? "fresh" : ""}`}>
            {a.category === "Research" ? (
              <Search size={15} />
            ) : a.category === "Action" ? (
              <Check size={15} />
            ) : a.category === "Decision" ? (
              <Target size={15} />
            ) : (
              <Activity size={15} />
            )}
          </div>
          <div className="min-w-0">
            <div className="activity-meta">
              <span>{a.category}</span>
              <time>{a.time}</time>
            </div>
            <h4>{a.title}</h4>
            {(!short || showDescriptions) && <p>{a.description}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <Timer size={30} />
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}

export function LocationTag({ location }: { location: string }) {
  return (
    <span className="tags" style={{ display: "inline-flex" }}>
      <span>
        <MapPin size={11} style={{ marginRight: 4, verticalAlign: -1 }} />
        {location}
      </span>
    </span>
  );
}

export function Modal({
  title,
  onClose,
  children,
  drawer = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  drawer?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.focus();
    const handle = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const elements = ref.current?.querySelectorAll<HTMLElement>(
          'button,input,textarea,select,[tabindex="0"]',
        );
        if (!elements?.length) return;
        const first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", handle);
    return () => {
      document.body.style.overflow = oldOverflow;
      document.removeEventListener("keydown", handle);
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title} className={drawer ? "modal drawer" : "modal"}>
        <div className="modal-header">
          <h2>
            <Leaf size={20} />
            {title}
          </h2>
          <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
