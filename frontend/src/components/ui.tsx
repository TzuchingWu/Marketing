import {
  ArrowUpRight,
  ArrowRight,
  Search,
  Activity,
  Leaf,
  Timer,
  Users,
  Check,
  X,
} from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  CartesianGrid,
} from "recharts";
import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { Opportunity, AgentActivity } from "../types";
import { trendHistory } from "../data/mockData";
export function Badge({
  children,
  tone = "green",
}: {
  children: ReactNode;
  tone?: string;
}) {
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
export function OpportunityArt({ opportunity }: { opportunity: Opportunity }) {
  return (
    <div className={`opportunity-art ${opportunity.color}`}>
      <span className="art-kicker">HYDRA / EVERYDAY RITUALS</span>
      <div className="art-orbit orbit-one" />
      <div className="art-orbit orbit-two" />
      <span className="art-word">
        {opportunity.id === "sunday"
          ? "reset."
          : opportunity.id === "run"
            ? "together."
            : "begin."}
      </span>
      <div className="product-packet">
        <Leaf size={16} />
        <strong>hydra</strong>
        <span>
          ELECTROLYTE
          <br />
          DRINK MIX
        </span>
        <div className="packet-line" />
        <small>LIME + SEA SALT</small>
      </div>
      <span className="art-bottom">A little ritual. A better you.</span>
      <span className="art-icon">
        {opportunity.id === "run" ? <Users /> : <Leaf />}
      </span>
    </div>
  );
}
export function OpportunityCard({
  opportunity: o,
  onView,
  onBuild,
  onDismiss,
  compact = false,
}: {
  opportunity: Opportunity;
  onView: () => void;
  onBuild?: () => void;
  onDismiss?: () => void;
  compact?: boolean;
}) {
  return (
    <article className={`opportunity-card ${compact ? "compact-opportunity" : ""}`}>
      <OpportunityArt opportunity={o} />
      <div className="opportunity-content">
        <div className="flex justify-between items-center">
          <Badge>
            <span className="dot" />
            {o.stage}
          </Badge>
          <span className="score">
            {o.score}
            <small> / 100 opportunity score</small>
          </span>
        </div>
        <h3>{o.name}</h3>
        <div className="card-stats">
          <span>
            <ArrowUpRight size={15} />
            <b>+{o.growth}%</b> growth
          </span>
          <span>
            <b>{o.match}%</b> audience match
          </span>
        </div>
        <p>{o.id === 'sunday' ? 'Growing Sunday Reset routines give Hydra a natural place in its younger audience’s wellness content.' : o.id === 'run' ? 'Post-run hydration connects Hydra with active professionals through creator-led running communities.' : o.reasoning.split(/(?<=[.!?])\s+/)[0]}</p>
        {!compact && <div className="tags"><span>{o.platform}</span><span>{o.format}</span></div>}
        {onBuild && (
          <div className="card-extra">
            <span>{o.audience}</span>
            <span>
              {o.relevance}% brand relevance · {o.product}
            </span>
          </div>
        )}
        <button className="card-link" onClick={onView}>
          View Opportunity
          <ArrowRight size={16} />
        </button>
        {onBuild && (
          <div className="flex gap-2 mt-3">
            <button className="btn primary compact" onClick={onBuild}>
              Build Campaign
            </button>
            {onDismiss && <button className="btn compact" onClick={onDismiss}>Dismiss</button>}
          </div>
        )}
      </div>
    </article>
  );
}
export function TrendChart({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "chart compact-chart" : "chart"}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={trendHistory}
          margin={{ top: 10, right: 5, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#41866b" stopOpacity={0.24} />
              <stop offset="100%" stopColor="#41866b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="#ebeee9" />
          <XAxis
            dataKey="day"
            tickLine={false}
            axisLine={false}
            minTickGap={45}
            tick={{ fontSize: 11, fill: "#89928a" }}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e1e5de",
              fontSize: 12,
            }}
          />
          <Area
            name="Relative interest"
            type="monotone"
            dataKey="interest"
            stroke="#34785b"
            strokeWidth={2.5}
            fill="url(#trendFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
export function ActivityFeed({
  items,
  short = false,
  showDescriptions = false,
}: {
  items: AgentActivity[];
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
              <Leaf size={15} />
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
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === ref.current)
        ) {
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
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={drawer ? "modal drawer" : "modal"}
      >
        <div className="modal-header">
          <h2>
            <Search size={20} />
            {title}
          </h2>
          <button
            className="icon-button"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
