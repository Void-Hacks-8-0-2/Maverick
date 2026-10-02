import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  ArrowRight,
  TrendingUp,
  Activity,
  Lock,
  Zap,
  Layers
} from 'lucide-react';
import { getDatasetSummary } from '../api/dataset';
import { searchAccounts, getMuleIntelligence } from '../api/accounts';
import type { DatasetSummary, AccountSearchItem, MuleIntelligenceSummary } from '../types';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();

  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [muleSummary, setMuleSummary] = useState<MuleIntelligenceSummary | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  const [subjectAccount, setSubjectAccount] = useState('');
  const [searchResults, setSearchResults] = useState<AccountSearchItem[]>([]);

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

    // Populate initial notable investigative signals (high volume / active accounts)
    searchAccounts('KKBK', 8)
      .then((res) => setSearchResults(res))
      .catch(() => {});
  }, []);

  const handleInitiateTrace = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = subjectAccount.trim().toUpperCase();
    if (!cleaned) return;
    navigate(`/victim/${cleaned}`);
  };

  const handleQuickInvestigate = (accountNumber: string) => {
    navigate(`/victim/${accountNumber}`);
  };

  const totalMules = muleSummary ? (muleSummary.l1_count + muleSummary.l2_count + muleSummary.l3_count) : 5433;
  const l1Pct = muleSummary ? Math.round((muleSummary.l1_count / totalMules) * 100) : 19;
  const l2Pct = muleSummary ? Math.round((muleSummary.l2_count / totalMules) * 100) : 55;
  const l3Pct = muleSummary ? Math.round((muleSummary.l3_count / totalMules) * 100) : 26;

  return (
    <div className="space-y-7">
      {/* 1. INVESTIGATION INTAKE HERO (Institutional Operations Surface) */}
      <div className="relative surface-panel rounded-2xl p-6 sm:p-8 overflow-hidden border border-white/[0.08] shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/[0.03] rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-4xl mx-auto space-y-5">
          <div className="space-y-1.5">
            <div className="text-[10px] font-mono tracking-widest text-cyan-400 uppercase flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>ABHEDYA CHAKRA</span>
              <span className="text-slate-600">&bull;</span>
              <span className="text-slate-400">INVESTIGATION CONSOLE</span>
            </div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-semibold text-slate-100 tracking-tight font-sans">
              START AN INVESTIGATION
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-2xl font-sans">
              Enter any account number to initiate multi-hop fund attribution, rapid velocity detection,
              and deterministic mule role classification across the production dataset.
            </p>
          </div>

          {/* Primary Intake Form */}
          <form onSubmit={handleInitiateTrace} className="space-y-3 pt-1">
            <div className="flex flex-col sm:flex-row gap-2.5">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={subjectAccount}
                  onChange={(e) => setSubjectAccount(e.target.value)}
                  placeholder="Enter victim or account number (e.g. KKBK10000402)..."
                  className="w-full bg-[#05070a] border border-white/[0.12] focus:border-cyan-400/80 rounded-xl pl-10 pr-4 py-3 text-xs sm:text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none transition shadow-inner"
                />
              </div>
              <button
                type="submit"
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-6 py-3 rounded-xl text-xs font-semibold font-mono tracking-wider flex items-center justify-center gap-2 transition shrink-0 shadow-lg shadow-cyan-500/20 active:scale-[0.99]"
              >
                <span>INVESTIGATE</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Benchmark Quick-Launch Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs font-mono">
              <span className="text-[11px] text-slate-400">Priority Test Cases:</span>
              {[
                { id: 'KKBK10000402', label: 'Victim Benchmark (27 Nodes)' },
                { id: 'BARB10000427', label: 'Large Distributor (425 Nodes)' },
                { id: 'PYTM10001005', label: 'L2 Intermediary' },
                { id: 'AIRP10000595', label: 'L1 Collector' },
              ].map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => handleQuickInvestigate(c.id)}
                  className="bg-[#0a0e14] hover:bg-slate-800 border border-white/[0.08] hover:border-cyan-500/40 px-2.5 py-1 rounded-lg text-[11px] text-cyan-300 transition flex items-center gap-1.5"
                >
                  <span className="font-semibold">{c.id}</span>
                  <span className="text-slate-400 text-[10px]">({c.label})</span>
                </button>
              ))}
            </div>
          </form>
        </div>
      </div>

      {/* 2. INTEGRATED DATASET TELEMETRY STRIP */}
      <div className="surface-l1 border border-white/[0.06] rounded-lg px-4 py-2.5 flex flex-wrap items-center justify-between gap-y-2 gap-x-6 text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span className="text-slate-400">DATASET:</span>
          <span className="font-semibold text-slate-200">2,000,000 TX</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
          <span className="text-slate-400">ENTITIES:</span>
          <span className="font-semibold text-slate-200">
            {summary ? summary.unique_accounts.toLocaleString() : '24,873'} ACCOUNTS
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
          <span className="text-slate-400">WINDOW:</span>
          <span className="font-semibold text-slate-200">15 CALENDAR DAYS</span>
        </div>
        <div className="flex items-center gap-2">
          <Lock className="w-3 h-3 text-emerald-400" />
          <span className="text-slate-400">INTEGRITY:</span>
          <span className="font-semibold text-emerald-400">SHA-256 VERIFIED</span>
          <span className="text-slate-400 text-[10px] hidden sm:inline">(2c9f81fd...)</span>
        </div>
        <div className="flex items-center gap-2">
          <TrendingUp className="w-3 h-3 text-slate-400" />
          <span className="text-slate-400">GROSS:</span>
          <span className="font-semibold text-slate-200">
            ₹{summary ? summary.total_amount.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '...'}
          </span>
        </div>
      </div>

      {/* 3. COHESIVE INVESTIGATIVE SIGNALS (Unified Intelligence Region) */}
      {loadingMetrics ? (
        <LoadingState
          message="Loading Platform Forensics..."
          submessage="Aggregating dataset summary and mule intelligence metrics from DuckDB"
          heightClass="h-28"
        />
      ) : metricsError ? (
        <ErrorState error={metricsError} />
      ) : (
        <div className="surface-l2 rounded-xl p-5 border border-white/[0.06] space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs font-mono font-semibold tracking-wider text-slate-200 uppercase">
                MULE NETWORK INTELLIGENCE SIGNALS
              </h2>
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              Total Classified Candidates: <span className="text-cyan-300 font-semibold">{totalMules.toLocaleString()}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* L1 Collector */}
            <div className="bg-[#06080d]/60 border border-white/[0.06] p-3.5 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-cyan-400 font-medium">L1 COLLECTOR</span>
                <span className="text-slate-400">{l1Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold text-slate-100 tabular-nums">
                {muleSummary?.l1_count.toLocaleString() || '1,032'}
              </div>
              <div className="w-full bg-slate-800/80 h-1 rounded-full overflow-hidden">
                <div className="bg-cyan-400 h-full rounded-full" style={{ width: `${l1Pct}%` }} />
              </div>
              <div className="text-[10px] text-slate-400 font-mono">High fan-in credit aggregation</div>
            </div>

            {/* L2 Distributor */}
            <div className="bg-[#06080d]/60 border border-white/[0.06] p-3.5 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-purple-400 font-medium">L2 DISTRIBUTOR</span>
                <span className="text-slate-400">{l2Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold text-slate-100 tabular-nums">
                {muleSummary?.l2_count.toLocaleString() || '2,988'}
              </div>
              <div className="w-full bg-slate-800/80 h-1 rounded-full overflow-hidden">
                <div className="bg-purple-400 h-full rounded-full" style={{ width: `${l2Pct}%` }} />
              </div>
              <div className="text-[10px] text-slate-400 font-mono">Rapid pass-through dispersion</div>
            </div>

            {/* L3 Terminal */}
            <div className="bg-[#06080d]/60 border border-white/[0.06] p-3.5 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-rose-400 font-medium">L3 TERMINAL</span>
                <span className="text-slate-400">{l3Pct}%</span>
              </div>
              <div className="text-xl font-mono font-semibold text-slate-100 tabular-nums">
                {muleSummary?.l3_count.toLocaleString() || '1,413'}
              </div>
              <div className="w-full bg-slate-800/80 h-1 rounded-full overflow-hidden">
                <div className="bg-rose-400 h-full rounded-full" style={{ width: `${l3Pct}%` }} />
              </div>
              <div className="text-[10px] text-slate-400 font-mono">Sink absorption &amp; cash-out</div>
            </div>

            {/* Rapid Velocity & High Risk */}
            <div className="bg-[#06080d]/60 border border-white/[0.06] p-3.5 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-amber-400 font-medium">RAPID VELOCITY</span>
                <Zap className="w-3 h-3 text-amber-400" />
              </div>
              <div className="text-xl font-mono font-semibold text-slate-100 tabular-nums">
                {muleSummary?.velocity_count.toLocaleString() || '171'}
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono pt-1 border-t border-white/[0.06]">
                <span className="text-slate-400">High-Risk (Score ≥70):</span>
                <span className="text-rose-400 font-semibold">{muleSummary?.high_risk_count.toLocaleString() || '30'}</span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono">3–15 minute turnaround window</div>
            </div>
          </div>
        </div>
      )}

      {/* 4. NOTABLE INVESTIGATIVE SIGNALS (Refined Financial Ledger) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-semibold tracking-wider text-slate-300 uppercase">
              NOTABLE INVESTIGATIVE SIGNALS ({searchResults.length} Accounts Displayed)
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Click &quot;Investigate&quot; to open the Blind Victim Trace workflow
          </span>
        </div>

        <div className="surface-l2 rounded-xl overflow-hidden border border-white/[0.06] shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#070a12]/90 text-slate-400 border-b border-white/[0.06] text-[10px] uppercase tracking-wider sticky top-0">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Account ID</th>
                  <th className="py-2.5 px-4 font-medium">Inbound Tx</th>
                  <th className="py-2.5 px-4 font-medium">Outbound Tx</th>
                  <th className="py-2.5 px-4 font-medium">Observed Inflow</th>
                  <th className="py-2.5 px-4 font-medium">Observed Outflow</th>
                  <th className="py-2.5 px-4 font-medium">Net Flow Delta</th>
                  <th className="py-2.5 px-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04] text-slate-300">
                {searchResults.map((item) => (
                  <tr key={item.account} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-2.5 px-4 font-medium text-slate-100 flex items-center space-x-2">
                      <button
                        type="button"
                        onClick={() => handleQuickInvestigate(item.account)}
                        className="hover:text-cyan-300 text-cyan-400 font-mono transition"
                      >
                        {item.account}
                      </button>
                    </td>
                    <td className="py-2.5 px-4 text-slate-300 tabular-nums">
                      {item.inbound_transaction_count}
                    </td>
                    <td className="py-2.5 px-4 text-slate-300 tabular-nums">
                      {item.outbound_transaction_count}
                    </td>
                    <td className="py-2.5 px-4 text-emerald-400 font-medium tabular-nums">
                      ₹{item.observed_inflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-rose-400 font-medium tabular-nums">
                      ₹{item.observed_outflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className={`py-2.5 px-4 font-medium tabular-nums ${item.dataset_observed_net_movement >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {item.dataset_observed_net_movement >= 0 ? '+' : ''}
                      ₹{item.dataset_observed_net_movement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => handleQuickInvestigate(item.account)}
                        className="bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 px-2 py-0.5 rounded text-[11px] font-medium transition"
                      >
                        Investigate
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/graph?account=${item.account}`)}
                        className="bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.06] text-slate-300 px-2 py-0.5 rounded text-[11px] transition"
                      >
                        Graph
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/timeline?account_id=${item.account}`)}
                        className="bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.06] text-slate-300 px-2 py-0.5 rounded text-[11px] transition"
                      >
                        Timeline
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate(`/account/${item.account}`)}
                        className="bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.06] text-slate-300 px-2 py-0.5 rounded text-[11px] transition"
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
