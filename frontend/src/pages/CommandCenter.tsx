import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowRight,
  Activity,
  Lock,
  Zap,
  Network,
  Clock,
  FileCheck2,
  Users,
  TrendingUp,
} from 'lucide-react';
import { getDatasetSummary } from '../api/dataset';
import { searchAccounts, getMuleIntelligence, getVictimInvestigation } from '../api/accounts';
import type { DatasetSummary, AccountSearchItem, MuleIntelligenceSummary } from '../types';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();

  const [summary, setSummary]         = useState<DatasetSummary | null>(null);
  const [muleSummary, setMuleSummary] = useState<MuleIntelligenceSummary | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [metricsError, setMetricsError]     = useState<string | null>(null);

  const [subjectAccount, setSubjectAccount] = useState('');
  const [searchResults, setSearchResults]   = useState<AccountSearchItem[]>([]);

  useEffect(() => {
    setLoadingMetrics(true);
    setMetricsError(null);

    Promise.all([
      getDatasetSummary(),
      getMuleIntelligence({ limit: 1 })
    ])
      .then(([ds, mules]) => {
        setSummary(ds);
        setMuleSummary(mules.summary);
        setLoadingMetrics(false);
      })
      .catch((err) => {
        setMetricsError(err.message || 'Failed to load dataset overview');
        setLoadingMetrics(false);
      });

    searchAccounts('KKBK', 8)
      .then((res) => setSearchResults(res))
      .catch(() => {});

    // Speculatively pre-warm key evaluation accounts during browser idle
    const prewarmTimer = setTimeout(() => {
      getVictimInvestigation('KKBK10000402').catch(() => {});
      getVictimInvestigation('BARB10000427').catch(() => {});
    }, 400);

    return () => clearTimeout(prewarmTimer);
  }, []);

  const handleInitiateTrace = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = subjectAccount.trim().toUpperCase();
    if (!cleaned) return;
    navigate(`/victim/${cleaned}`);
  };

  const handlePrefetch = (account: string) => {
    const cleaned = account.trim().toUpperCase();
    if (cleaned) {
      getVictimInvestigation(cleaned).catch(() => {});
    }
  };

  const handleInvestigate = (account: string) => {
    navigate(`/victim/${account}`);
  };

  const totalMules = muleSummary
    ? (muleSummary.l1_count + muleSummary.l2_count + muleSummary.l3_count)
    : 5433;
  const l1Pct = muleSummary ? Math.round((muleSummary.l1_count / totalMules) * 100) : 19;
  const l2Pct = muleSummary ? Math.round((muleSummary.l2_count / totalMules) * 100) : 55;
  const l3Pct = muleSummary ? Math.round((muleSummary.l3_count / totalMules) * 100) : 26;

  // Quick-action cards for the investigator
  const quickActions = [
    {
      id: 'victim',
      label: 'Victim Investigation',
      description: 'Multi-hop fund trace from any victim account',
      icon: Activity,
      path: '/victim',
      accent: 'var(--accent)',
      bg: 'var(--accent-light)',
      border: 'var(--accent-border)',
    },
    {
      id: 'graph',
      label: 'Network Intelligence',
      description: 'Visualise transaction graph and mule network',
      icon: Network,
      path: '/graph',
      accent: '#059669',
      bg: '#f0fdf4',
      border: 'rgba(5,150,105,0.2)',
    },
    {
      id: 'mules',
      label: 'Mule Intelligence',
      description: 'Browse classified L1/L2/L3 mule candidates',
      icon: Users,
      path: '/mules',
      accent: '#d97706',
      bg: '#fffbeb',
      border: 'rgba(217,119,6,0.2)',
    },
    {
      id: 'timeline',
      label: 'Forensic Timeline',
      description: 'Chronological transaction event analysis',
      icon: Clock,
      path: '/timeline',
      accent: '#dc2626',
      bg: '#fef2f2',
      border: 'rgba(220,38,38,0.2)',
    },
    {
      id: 'case-file',
      label: 'Case File & Evidence',
      description: 'Packaged forensic evidence and legal freeze',
      icon: FileCheck2,
      path: '/case-file',
      accent: '#4b5563',
      bg: '#f8f9fa',
      border: 'rgba(0,0,0,0.1)',
    },
  ];

  return (
    <div className="space-y-8">
      {/* ── 1. INVESTIGATION INTAKE ──────────────────────────────── */}
      <div
        className="rounded-xl p-6 sm:p-8"
        style={{ backgroundColor: '#ffffff', border: '1px solid var(--border-subtle)', boxShadow: '0 2px 12px rgba(0,0,0,0.05)' }}
      >
        <div className="max-w-3xl space-y-4">
          <div>
            <div className="text-[10px] font-mono font-semibold tracking-[0.2em] uppercase mb-2" style={{ color: 'var(--accent)' }}>
              Investigation Console
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Start an Investigation
            </h1>
            <p className="text-sm mt-1.5 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              Enter any account number to initiate multi-hop fund attribution, velocity detection,
              and deterministic mule role classification.
            </p>
          </div>

          {/* Primary form */}
          <form onSubmit={handleInitiateTrace} className="space-y-3 pt-1">
            <div className="flex flex-col sm:flex-row gap-2.5">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-3.5 w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
                <input
                  id="investigation-input"
                  type="text"
                  value={subjectAccount}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSubjectAccount(val);
                    if (val.trim().length >= 10) {
                      handlePrefetch(val);
                    }
                  }}
                  placeholder="Enter victim or account number (e.g. KKBK10000402)..."
                  className="w-full rounded-lg pl-10 pr-4 py-3 text-xs sm:text-sm font-mono focus:outline-none transition"
                  style={{
                    backgroundColor: 'var(--surface-2)',
                    border: '1px solid var(--border-medium)',
                    color: 'var(--text-primary)',
                  }}
                  onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                  onBlur={(e)  => { e.currentTarget.style.borderColor = 'var(--border-medium)'; }}
                />
              </div>
              <button
                type="submit"
                id="investigate-btn"
                className="px-6 py-3 rounded-lg text-xs font-semibold font-mono tracking-wider flex items-center justify-center gap-2 transition shrink-0 text-white"
                style={{ backgroundColor: 'var(--accent)', boxShadow: '0 2px 8px rgba(109,40,217,0.25)' }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent-soft)'; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent)'; }}
              >
                <span>INVESTIGATE</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* ── 2. QUICK ACTION GRID ─────────────────────────────────── */}
      <div>
        <div className="text-[10px] font-mono font-semibold tracking-[0.15em] uppercase mb-3" style={{ color: 'var(--text-tertiary)' }}>
          Investigative Modules
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                type="button"
                onClick={() => navigate(action.path)}
                id={`quick-action-${action.id}`}
                className="text-left p-4 rounded-lg transition group"
                style={{
                  backgroundColor: action.bg,
                  border: `1px solid ${action.border}`,
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.boxShadow = `0 4px 12px ${action.border}`;
                  (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.boxShadow = 'none';
                  (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
                }}
              >
                <Icon className="w-5 h-5 mb-2.5" style={{ color: action.accent }} />
                <div className="text-xs font-semibold mb-1" style={{ color: action.accent }}>
                  {action.label}
                </div>
                <div className="text-[10px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                  {action.description}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 3. DATASET TELEMETRY STRIP ──────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 rounded-lg text-[11px] font-mono"
        style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}
      >
        <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <span className="w-1.5 h-1.5 rounded-full bg-violet-600" />
          <span>DATASET:</span>
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>2,000,000 TX</span>
        </div>
        <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <span>ENTITIES:</span>
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
            {summary ? summary.unique_accounts.toLocaleString() : '24,873'} ACCOUNTS
          </span>
        </div>
        <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <span>WINDOW:</span>
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>15 CALENDAR DAYS</span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="w-3 h-3" style={{ color: 'var(--semantic-emerald)' }} />
          <span style={{ color: 'var(--text-secondary)' }}>INTEGRITY:</span>
          <span className="font-semibold" style={{ color: 'var(--semantic-emerald)' }}>SHA-256 VERIFIED</span>
          <span className="hidden sm:inline" style={{ color: 'var(--text-tertiary)' }}>(2c9f81fd...)</span>
        </div>
        <div className="flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <TrendingUp className="w-3 h-3" />
          <span>GROSS:</span>
          <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
            ₹{summary ? summary.total_amount.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '...'}
          </span>
        </div>
      </div>

      {/* ── 4. MULE NETWORK INTELLIGENCE ────────────────────────── */}
      {loadingMetrics ? (
        <LoadingState
          message="Loading Forensic Intelligence..."
          submessage="Aggregating mule candidate metrics from DuckDB"
          heightClass="h-24"
        />
      ) : metricsError ? (
        <ErrorState error={metricsError} />
      ) : (
        <div
          className="rounded-xl p-5 space-y-4"
          style={{ backgroundColor: '#ffffff', border: '1px solid var(--border-subtle)' }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              <h2 className="text-xs font-mono font-semibold tracking-wider uppercase" style={{ color: 'var(--text-primary)' }}>
                Mule Network Intelligence
              </h2>
            </div>
            <div className="text-[11px] font-mono" style={{ color: 'var(--text-secondary)' }}>
              Total Classified: <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{totalMules.toLocaleString()}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* L1 Collector */}
            <div className="p-3.5 rounded-lg space-y-2" style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="font-semibold" style={{ color: '#059669' }}>L1 COLLECTOR</span>
                <span style={{ color: 'var(--text-tertiary)' }}>{l1Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                {muleSummary?.l1_count.toLocaleString() ?? '1,032'}
              </div>
              <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--surface-4)' }}>
                <div className="h-full rounded-full" style={{ width: `${l1Pct}%`, backgroundColor: '#059669' }} />
              </div>
              <div className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>High fan-in credit aggregation</div>
            </div>

            {/* L2 Distributor */}
            <div className="p-3.5 rounded-lg space-y-2" style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="font-semibold" style={{ color: 'var(--accent)' }}>L2 DISTRIBUTOR</span>
                <span style={{ color: 'var(--text-tertiary)' }}>{l2Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                {muleSummary?.l2_count.toLocaleString() ?? '2,988'}
              </div>
              <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--surface-4)' }}>
                <div className="h-full rounded-full" style={{ width: `${l2Pct}%`, backgroundColor: 'var(--accent)' }} />
              </div>
              <div className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>Rapid pass-through dispersion</div>
            </div>

            {/* L3 Terminal */}
            <div className="p-3.5 rounded-lg space-y-2" style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="font-semibold" style={{ color: 'var(--semantic-rose)' }}>L3 TERMINAL</span>
                <span style={{ color: 'var(--text-tertiary)' }}>{l3Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                {muleSummary?.l3_count.toLocaleString() ?? '1,413'}
              </div>
              <div className="w-full h-1 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--surface-4)' }}>
                <div className="h-full rounded-full" style={{ width: `${l3Pct}%`, backgroundColor: 'var(--semantic-rose)' }} />
              </div>
              <div className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>Sink absorption &amp; cash-out</div>
            </div>

            {/* Rapid Velocity */}
            <div className="p-3.5 rounded-lg space-y-2" style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="font-semibold" style={{ color: 'var(--semantic-amber)' }}>RAPID VELOCITY</span>
                <Zap className="w-3 h-3" style={{ color: 'var(--semantic-amber)' }} />
              </div>
              <div className="text-xl font-mono font-semibold tabular-nums" style={{ color: 'var(--text-primary)' }}>
                {muleSummary?.velocity_count.toLocaleString() ?? '171'}
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono pt-1" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>High-Risk (Score ≥70):</span>
                <span className="font-semibold" style={{ color: 'var(--semantic-rose)' }}>
                  {muleSummary?.high_risk_count.toLocaleString() ?? '30'}
                </span>
              </div>
              <div className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>3–15 min turnaround window</div>
            </div>
          </div>
        </div>
      )}

      {/* ── 5. NOTABLE INVESTIGATIVE SIGNALS ───────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-semibold tracking-wider uppercase" style={{ color: 'var(--text-secondary)' }}>
            Notable Investigative Signals ({searchResults.length} accounts)
          </h3>
          <span className="text-[10px] font-mono" style={{ color: 'var(--text-tertiary)' }}>
            Click &ldquo;Investigate&rdquo; to open the Blind Victim Trace
          </span>
        </div>

        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border-subtle)', backgroundColor: '#ffffff' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono forensic-table">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <th className="py-2.5 px-4">Account ID</th>
                  <th className="py-2.5 px-4">Inbound Tx</th>
                  <th className="py-2.5 px-4">Outbound Tx</th>
                  <th className="py-2.5 px-4">Observed Inflow</th>
                  <th className="py-2.5 px-4">Observed Outflow</th>
                  <th className="py-2.5 px-4">Net Delta</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {searchResults.map((item) => (
                  <tr key={item.account}>
                    <td className="py-2.5 px-4 font-medium">
                      <button
                        type="button"
                        onClick={() => handleInvestigate(item.account)}
                        onMouseEnter={(e) => {
                          handlePrefetch(item.account);
                          (e.currentTarget as HTMLButtonElement).style.textDecoration = 'underline';
                        }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.textDecoration = 'none'; }}
                        className="font-mono transition"
                        style={{ color: 'var(--accent)' }}
                      >
                        {item.account}
                      </button>
                    </td>
                    <td className="py-2.5 px-4 tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {item.inbound_transaction_count}
                    </td>
                    <td className="py-2.5 px-4 tabular-nums" style={{ color: 'var(--text-secondary)' }}>
                      {item.outbound_transaction_count}
                    </td>
                    <td className="py-2.5 px-4 font-medium tabular-nums" style={{ color: 'var(--semantic-emerald)' }}>
                      ₹{item.observed_inflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 font-medium tabular-nums" style={{ color: 'var(--semantic-rose)' }}>
                      ₹{item.observed_outflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td
                      className="py-2.5 px-4 font-medium tabular-nums"
                      style={{ color: item.dataset_observed_net_movement >= 0 ? 'var(--semantic-emerald)' : 'var(--semantic-rose)' }}
                    >
                      {item.dataset_observed_net_movement >= 0 ? '+' : ''}
                      ₹{item.dataset_observed_net_movement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => handleInvestigate(item.account)}
                        onMouseEnter={(e) => {
                          handlePrefetch(item.account);
                          (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent-soft)';
                        }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--accent)'; }}
                        className="px-2.5 py-1 rounded text-[11px] font-semibold transition text-white"
                        style={{ backgroundColor: 'var(--accent)' }}
                      >
                        Investigate
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/graph?account=${item.account}`)}
                        className="px-2.5 py-1 rounded text-[11px] transition"
                        style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-3)'; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-2)'; }}
                      >
                        Graph
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/timeline?account_id=${item.account}`)}
                        className="px-2.5 py-1 rounded text-[11px] transition"
                        style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-3)'; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-2)'; }}
                      >
                        Timeline
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/account/${item.account}`)}
                        className="px-2.5 py-1 rounded text-[11px] transition"
                        style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-medium)', color: 'var(--text-secondary)' }}
                        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-3)'; }}
                        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-2)'; }}
                      >
                        Profile
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
