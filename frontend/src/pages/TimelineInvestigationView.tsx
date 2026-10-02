import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Search,
  Clock,
  Zap,
  GitBranch,
  ShieldAlert,
  AlertOctagon,
  ArrowDown,
  ArrowUp,
  SlidersHorizontal,
} from 'lucide-react';
import {
  getTimeline,
} from '../api/explorer';
import type { TimelineEvent, TimelineEventType, TimelineSummary } from '../api/explorer';

// ─── Config ───────────────────────────────────────────────────────────────────
const EVENT_TYPES: { value: string; label: string }[] = [
  { value: 'all', label: 'All Events' },
  { value: 'TRANSACTION', label: 'Transactions' },
  { value: 'VELOCITY', label: 'Velocity Alerts' },
  { value: 'ATTRIBUTION', label: 'FIFO Attribution' },
  { value: 'RISK_ROLE', label: 'Risk / Role' },
  { value: 'TERMINAL', label: 'Terminal Sink' },
];

const EVENT_ICON: Record<TimelineEventType, React.FC<{ className?: string }>> = {
  TRANSACTION: Activity,
  VELOCITY: Zap,
  ATTRIBUTION: GitBranch,
  RISK_ROLE: ShieldAlert,
  TERMINAL: AlertOctagon,
};

const EVENT_ICON_COLOR: Record<TimelineEventType, string> = {
  TRANSACTION: 'text-slate-400',
  VELOCITY: 'text-amber-400',
  ATTRIBUTION: 'text-purple-400',
  RISK_ROLE: 'text-cyan-400',
  TERMINAL: 'text-rose-400',
};

const DOT_COLOR: Record<TimelineEventType, string> = {
  TRANSACTION: 'bg-slate-400',
  VELOCITY: 'bg-amber-400',
  ATTRIBUTION: 'bg-purple-400',
  RISK_ROLE: 'bg-cyan-400',
  TERMINAL: 'bg-rose-400',
};

function fmt(n: number) {
  return '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── Summary Bar ─────────────────────────────────────────────────────────────
const SummaryBar: React.FC<{ summary: TimelineSummary }> = ({ summary }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-3.5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono shadow-xs">
    {[
      { label: 'EVENTS', value: summary.total_events.toLocaleString(), color: 'text-slate-900' },
      { label: 'TRANSACTIONS', value: summary.transaction_count.toLocaleString(), color: 'text-slate-900' },
      { label: 'INFLOW', value: fmt(summary.incoming_volume), color: 'text-emerald-700 font-semibold' },
      { label: 'OUTFLOW', value: fmt(summary.outgoing_volume), color: 'text-rose-700 font-semibold' },
      { label: 'VELOCITY ALERTS', value: summary.velocity_event_count.toLocaleString(), color: 'text-amber-700 font-semibold' },
      { label: 'FIFO EDGES', value: summary.attribution_event_count.toLocaleString(), color: 'text-violet-700 font-semibold' },
    ].map(({ label, value, color }) => (
      <div key={label} className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
        <div className="text-slate-500 uppercase text-[9px] tracking-wider mb-0.5 font-semibold">{label}</div>
        <div className={`font-semibold text-xs sm:text-sm tabular-nums ${color}`}>{value}</div>
      </div>
    ))}
  </div>
);

// ─── Event Card (Light surface with semantic pip) ─────────────────────
const EventCard: React.FC<{ event: TimelineEvent; highlight?: string }> = ({ event, highlight }) => {
  const [open, setOpen] = useState(false);
  const Icon = EVENT_ICON[event.event_type] ?? Activity;

  return (
    <div
      className="relative flex gap-3 rounded-lg border border-slate-200 bg-white p-3.5 cursor-pointer transition-all hover:border-violet-300 hover:shadow-xs shadow-xs"
      onClick={() => setOpen((v) => !v)}
    >
      <div className={`shrink-0 mt-0.5 ${EVENT_ICON_COLOR[event.event_type]}`}>
        <Icon className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-slate-900 font-semibold text-xs font-mono leading-tight">{event.title}</span>
          <span className="text-slate-500 text-[10px] font-mono whitespace-nowrap shrink-0 tabular-nums">
            {event.timestamp.replace('T', ' ').slice(0, 19)}
          </span>
        </div>
        <p className="text-slate-600 text-xs font-mono leading-snug truncate">{event.description}</p>

        {event.amount !== undefined && event.amount > 0 && (
          <div className="flex items-center gap-1.5 pt-0.5 font-mono">
            {event.direction === 'INCOMING' ? (
              <ArrowDown className="w-3.5 h-3.5 text-emerald-600" />
            ) : event.direction === 'OUTGOING' ? (
              <ArrowUp className="w-3.5 h-3.5 text-rose-600" />
            ) : null}
            <span className={`text-xs font-semibold tabular-nums ${event.direction === 'INCOMING' ? 'text-emerald-700' : event.direction === 'OUTGOING' ? 'text-rose-700' : 'text-slate-700'}`}>
              {fmt(event.amount)}
            </span>
          </div>
        )}

        {event.source_account && highlight && event.source_account !== highlight && (
          <div className="text-[10px] text-slate-500 font-mono">
            {event.source_account}
            {event.destination_account ? ` → ${event.destination_account}` : ''}
          </div>
        )}

        {open && Object.keys(event.details).length > 0 && (
          <div className="mt-2.5 pt-2 border-t border-slate-200 space-y-1">
            {Object.entries(event.details).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2 text-[10px] font-mono">
                <span className="text-slate-500 uppercase shrink-0 font-medium">{k}:</span>
                <span className="text-slate-800 text-right break-all">
                  {Array.isArray(v) ? v.join(', ') : typeof v === 'object' ? JSON.stringify(v) : String(v)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Main Page ────────────────────────────────────────────────────────────────
export const TimelineInvestigationView: React.FC = () => {
  const [accountInput, setAccountInput] = useState('');
  const [accountId, setAccountId] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [direction, setDirection] = useState('all');
  const [paymentMode, setPaymentMode] = useState('');
  const [eventType, setEventType] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [summary, setSummary] = useState<TimelineSummary | null>(null);
  const [totalEvents, setTotalEvents] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rangeInfo, setRangeInfo] = useState<{ start: string; end: string } | null>(null);

  const fetchRef = useRef(0);

  const doFetch = useCallback(() => {
    const seq = ++fetchRef.current;
    setLoading(true);
    setError(null);

    const params = {
      ...(accountId && { account_id: accountId }),
      ...(startTime && { start_time: startTime }),
      ...(endTime && { end_time: endTime }),
      ...(direction && direction !== 'all' && { direction: direction as 'all' | 'in' | 'out' }),
      ...(paymentMode && { payment_mode: paymentMode }),
      ...(eventType && eventType !== 'all' && { event_type: eventType }),
      page,
      page_size: pageSize,
    };

    getTimeline(params)
      .then((res) => {
        if (seq !== fetchRef.current) return;
        setEvents(res.events);
        setSummary(res.summary);
        setTotalEvents(res.total_events);
        setHasMore(res.has_more);
        setRangeInfo({ start: res.range.start_time, end: res.range.end_time });
      })
      .catch((err) => {
        if (seq !== fetchRef.current) return;
        setError(err.message || 'Failed to fetch timeline');
      })
      .finally(() => {
        if (seq === fetchRef.current) setLoading(false);
      });
  }, [accountId, startTime, endTime, direction, paymentMode, eventType, page]);

  useEffect(() => { doFetch(); }, [doFetch]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAccountId(accountInput.trim().toUpperCase());
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 pb-4" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <div>
          <div className="text-[10px] font-mono tracking-widest font-semibold uppercase mb-1" style={{ color: 'var(--accent)' }}>
            FORENSIC CHRONOLOGY
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight font-sans flex items-center gap-2">
            <Clock className="w-5 h-5 text-violet-700" />
            <span>Timeline Investigation</span>
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Chronological forensic event stream across 2M transactions
            {rangeInfo && (
              <span className="ml-2 text-slate-500">
                [{rangeInfo.start.slice(0, 10)} → {rangeInfo.end.slice(0, 10)}]
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => setShowFilters((v) => !v)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-xs font-mono transition ${
            showFilters
              ? 'bg-violet-50 border-violet-300 text-violet-700 font-semibold'
              : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Filters</span>
        </button>
      </div>

      {/* ── Search & Filter Controls ────────────────────────────── */}
      <div className="bg-white rounded-xl p-4 border border-slate-200 space-y-3 shadow-xs">
        <form onSubmit={handleSearch} className="flex flex-wrap gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={accountInput}
              onChange={(e) => setAccountInput(e.target.value)}
              placeholder="Account ID (leave blank for global)..."
              className="w-full bg-slate-50 border border-slate-200 focus:border-violet-600 rounded pl-8 pr-3 py-1.5 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none transition"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-1.5 bg-violet-700 hover:bg-violet-600 text-white text-xs font-mono font-semibold rounded transition"
          >
            Investigate
          </button>
          {accountId && (
            <button
              type="button"
              onClick={() => { setAccountInput(''); setAccountId(''); setPage(1); }}
              className="px-3 py-1.5 border border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-mono rounded transition"
            >
              Global View
            </button>
          )}
        </form>

        {/* Filter Drawer */}
        {showFilters && (
          <div className="pt-3 border-t border-slate-200 grid grid-cols-2 md:grid-cols-5 gap-3 text-xs font-mono">
            <div className="space-y-1">
              <label className="text-slate-500 uppercase text-[9px] tracking-wider block font-semibold">Start Time</label>
              <input
                value={startTime}
                onChange={(e) => { setStartTime(e.target.value); setPage(1); }}
                placeholder="2026-09-15 00:00:00"
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-slate-800 text-xs focus:outline-none focus:border-violet-600 transition"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 uppercase text-[9px] tracking-wider block font-semibold">End Time</label>
              <input
                value={endTime}
                onChange={(e) => { setEndTime(e.target.value); setPage(1); }}
                placeholder="2026-09-29 23:59:58"
                className="w-full bg-slate-50 border border-slate-200 rounded px-2.5 py-1 text-slate-800 text-xs focus:outline-none focus:border-violet-600 transition"
              />
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 uppercase text-[9px] tracking-wider block font-semibold">Direction</label>
              <select
                value={direction}
                onChange={(e) => { setDirection(e.target.value); setPage(1); }}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs focus:outline-none focus:border-violet-600 transition"
              >
                <option value="all">All</option>
                <option value="in">Incoming</option>
                <option value="out">Outgoing</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 uppercase text-[9px] tracking-wider block font-semibold">Payment Mode</label>
              <select
                value={paymentMode}
                onChange={(e) => { setPaymentMode(e.target.value); setPage(1); }}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs focus:outline-none focus:border-violet-600 transition"
              >
                <option value="">All</option>
                {['UPI', 'IMPS', 'NEFT', 'RTGS'].map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-slate-500 uppercase text-[9px] tracking-wider block font-semibold">Event Type</label>
              <select
                value={eventType}
                onChange={(e) => { setEventType(e.target.value); setPage(1); }}
                className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 text-xs focus:outline-none focus:border-violet-600 transition"
              >
                {EVENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* Event Type Filter Pills */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {EVENT_TYPES.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => { setEventType(value); setPage(1); }}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition border ${
                eventType === value
                  ? 'bg-violet-50 border-violet-300 text-violet-700 font-semibold'
                  : 'border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Summary Bar ─────────────────────────────────────────── */}
      {summary && <SummaryBar summary={summary} />}

      {/* ── Context Banner ──────────────────────────────────────── */}
      {accountId && (
        <div className="flex items-center gap-2 bg-violet-50 border border-violet-200 rounded-lg px-4 py-2 text-xs font-mono text-violet-900">
          <ShieldAlert className="w-4 h-4 text-violet-700" />
          <span>Investigating subject:</span>
          <span className="font-semibold text-slate-900">{accountId}</span>
          {summary?.risk_role_findings && (
            <span className="ml-3 text-slate-600">
              Risk: <span className="text-rose-700 font-semibold">{String(summary.risk_role_findings.mule_risk_score ?? '—')}/100</span>
              {' &bull; '}
              Role: <span className="text-violet-700 font-semibold">{String(summary.risk_role_findings.role ?? '—')}</span>
            </span>
          )}
        </div>
      )}

      {/* ── Event Stream with Single Subtle Spine ───────────────── */}
      <div className="space-y-3">
        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs font-mono text-rose-700">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-14 text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin mr-2 text-violet-600" />
            <span className="text-xs font-mono">Building chronological timeline…</span>
          </div>
        )}

        {!loading && events.length === 0 && !error && (
          <div className="py-14 text-center text-slate-500 text-xs font-mono">
            No events found for selected timeline criteria.
          </div>
        )}

        {!loading && events.length > 0 && (
          <div className="relative space-y-2.5 pl-6">
            {/* Single subtle vertical spine */}
            <div className="absolute left-2.5 top-2 bottom-2 w-px bg-slate-200" />

            {events.map((event) => (
              <div key={event.event_id} className="relative">
                {/* Discrete dot along the vertical spine */}
                <div className={`absolute -left-6 top-4 w-2 h-2 rounded-full ring-2 ring-white ${DOT_COLOR[event.event_type]}`} />
                <EventCard event={event} highlight={accountId} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Pagination ───────────────────────────────────────────── */}
      {!loading && totalEvents > pageSize && (
        <div className="flex items-center justify-between text-xs font-mono text-slate-600 border-t border-slate-200 pt-4">
          <span className="tabular-nums">{totalEvents.toLocaleString()} total events &bull; Page {page}</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 bg-white rounded disabled:opacity-40 hover:bg-slate-50 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Prev
            </button>
            <button
              disabled={!hasMore}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 px-3 py-1.5 border border-slate-200 bg-white rounded disabled:opacity-40 hover:bg-slate-50 transition"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
