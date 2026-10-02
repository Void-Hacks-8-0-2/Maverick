import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Users,
  Search,
  Filter,
  Zap,
  ChevronLeft,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';
import { getMuleIntelligence } from '../api/accounts';
import type { MuleCandidateItem, MuleIntelligenceSummary } from '../types';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { RoleBadge } from '../components/RoleBadge';
import { LoadingState } from '../components/LoadingState';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';

export const MuleIntelligence: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Query state
  const roleFilter = searchParams.get('role') || '';
  const riskBandFilter = searchParams.get('risk_band') || '';
  const velocityOnly = searchParams.get('velocity') === 'true';
  const sortBy = searchParams.get('sort_by') || 'risk';
  const page = parseInt(searchParams.get('page') || '0', 10);
  const pageSize = 25;

  const [summary, setSummary] = useState<MuleIntelligenceSummary | null>(null);
  const [items, setItems] = useState<MuleCandidateItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search input within current view
  const [searchFilter, setSearchFilter] = useState('');

  const fetchCandidates = () => {
    setLoading(true);
    setError(null);

    getMuleIntelligence({
      role: roleFilter || undefined,
      risk_band: riskBandFilter || undefined,
      velocity_only: velocityOnly || undefined,
      sort_by: sortBy,
      order: 'desc',
      limit: pageSize,
      offset: page * pageSize
    })
      .then((res) => {
        setSummary(res.summary);
        setItems(res.items);
        setTotalCount(res.total_count);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to query mule intelligence store');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchCandidates();
  }, [roleFilter, riskBandFilter, velocityOnly, sortBy, page]);

  const updateParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value === null || value === '') {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    next.set('page', '0'); // Reset page on filter change
    setSearchParams(next);
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  const filteredItems = searchFilter
    ? items.filter((it) => it.account_number.toUpperCase().includes(searchFilter.trim().toUpperCase()))
    : items;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        category="INTELLIGENCE DISCOVERY"
        title="Mule Intelligence & Candidate Triage"
        description="Multi-signal candidate identification across 24,873 observed account entities. Analyzes topological fan-in/fan-out dispersion, 3–15 min pass-through velocity, and 0–100 Mule Risk Index scores."
        badge={
          <span className="text-[10px] font-mono text-violet-700 bg-violet-50 border border-violet-200 px-2 py-0.5 rounded font-semibold">
            DETERMINISTIC CLASSIFICATION
          </span>
        }
      />

      {/* Role Architecture Reference Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-xl p-4 flex flex-col justify-between border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-semibold text-slate-900">LAYER 1 — COLLECTOR</span>
            <RoleBadge role="L1" size="sm" />
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Inbound credit aggregation nodes with high fan-in from multiple sources. Siphon funds from victims or initial deposit conduits.
          </p>
          <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span>Candidates in Dataset:</span>
            <span className="text-emerald-700 font-semibold tabular-nums">{summary?.l1_count.toLocaleString() ?? '...'}</span>
          </div>
        </div>

        <div className="rounded-xl p-4 flex flex-col justify-between border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-semibold text-slate-900">LAYER 2 — DISTRIBUTOR</span>
            <RoleBadge role="L2" size="sm" />
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            High fan-out pass-through conduits that rapidly split and disperse bulk inflows into smaller outbound hops across the network.
          </p>
          <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span>Candidates in Dataset:</span>
            <span className="text-amber-700 font-semibold tabular-nums">{summary?.l2_count.toLocaleString() ?? '...'}</span>
          </div>
        </div>

        <div className="rounded-xl p-4 flex flex-col justify-between border border-slate-200 bg-white shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono font-semibold text-slate-900">LAYER 3 — TERMINAL</span>
            <RoleBadge role="L3" size="sm" />
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Sink nodes, cash-out points, or accounts absorbing funds without forward credit transfers. Primary targets for asset freeze recovery.
          </p>
          <div className="mt-3 pt-2 border-t border-slate-200 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span>Candidates in Dataset:</span>
            <span className="text-rose-700 font-semibold tabular-nums">{summary?.l3_count.toLocaleString() ?? '...'}</span>
          </div>
        </div>
      </div>

      {/* KPI Metrics Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard
          label="Total Analyzed Accounts"
          value={summary ? summary.total_accounts.toLocaleString() : '...'}
          subtitle="Observed entities in dataset"
          icon={Users}
        />
        <MetricCard
          label="High Risk (Index ≥ 70)"
          value={summary ? summary.high_risk_count.toLocaleString() : '...'}
          subtitle="Priority triage candidates"
          icon={ShieldAlert}
          iconColor="text-rose-600"
          variant="rose"
          onClick={() => updateParam('risk_band', riskBandFilter === 'HIGH' ? '' : 'HIGH')}
        />
        <MetricCard
          label="Rapid Pass-Through"
          value={summary ? summary.velocity_count.toLocaleString() : '...'}
          subtitle="3–15 min transit candidates"
          icon={Zap}
          iconColor="text-amber-600"
          variant="amber"
          onClick={() => updateParam('velocity', velocityOnly ? '' : 'true')}
        />
        <MetricCard
          label="Filter Matched"
          value={totalCount.toLocaleString()}
          subtitle={`Page ${page + 1} of ${Math.max(1, totalPages)}`}
          icon={Filter}
          variant="purple"
        />
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-white border border-slate-200 p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-xs">
        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-500 mr-1 font-semibold">
            <Filter className="w-3.5 h-3.5 text-violet-700" />
            <span>Filters:</span>
          </div>

          {/* Role Filter */}
          <select
            value={roleFilter}
            onChange={(e) => updateParam('role', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-xs font-mono text-slate-800 focus:outline-none focus:border-violet-600"
          >
            <option value="">All Roles</option>
            <option value="L1">L1 Collector</option>
            <option value="L2">L2 Distributor</option>
            <option value="L3">L3 Terminal</option>
            <option value="ANY">Any Candidate Role</option>
          </select>

          {/* Risk Band Filter */}
          <select
            value={riskBandFilter}
            onChange={(e) => updateParam('risk_band', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-xs font-mono text-slate-800 focus:outline-none focus:border-violet-600"
          >
            <option value="">All Risk Bands</option>
            <option value="VERY_HIGH">Very High Risk (≥ 85)</option>
            <option value="HIGH">High Risk (70–84)</option>
            <option value="MODERATE">Moderate Risk (40–69)</option>
            <option value="LOW">Low Risk (&lt; 40)</option>
          </select>

          {/* Velocity Toggle Button */}
          <button
            type="button"
            onClick={() => updateParam('velocity', velocityOnly ? '' : 'true')}
            className={`px-3 py-1.5 rounded text-xs font-mono flex items-center gap-1.5 border transition ${
              velocityOnly
                ? 'bg-amber-50 border-amber-300 text-amber-700 font-semibold'
                : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900'
            }`}
          >
            <Zap className="w-3 h-3 text-amber-600" />
            <span>3–15m Velocity Only</span>
          </button>

          {/* Sort Selector */}
          <div className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
            <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">SORT:</span>
            <select
              value={sortBy}
              onChange={(e) => updateParam('sort_by', e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 text-xs font-mono text-slate-800 focus:outline-none focus:border-violet-600"
            >
              <option value="risk">Mule Risk Index</option>
              <option value="volume">Observed Inflow</option>
              <option value="fan_in">Fan-In (Senders)</option>
              <option value="fan_out">Fan-Out (Receivers)</option>
              <option value="tx_count">Transaction Count</option>
            </select>
          </div>
        </div>

        {/* Quick Search on Results */}
        <div className="relative w-full sm:w-60">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            placeholder="Search account ID in page..."
            className="w-full bg-slate-50 border border-slate-200 rounded pl-8 pr-3 py-1.5 text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-violet-600"
          />
        </div>
      </div>

      {/* Main Results Table */}
      {loading ? (
        <LoadingState
          message="Querying Mule Candidate Repository..."
          submessage="Retrieving pre-materialized features from 24,873 accounts"
        />
      ) : error ? (
        <ErrorState error={error} onRetry={fetchCandidates} />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No Mule Candidates Matched Filter Criteria"
          description="Try relaxing the risk band or selecting 'All Roles' to widen the investigative scope."
          action={
            <button
              onClick={() => {
                setSearchParams(new URLSearchParams());
              }}
              className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded text-xs font-mono text-violet-700 font-semibold transition"
            >
              Reset Filters
            </button>
          }
        />
      ) : (
        <div className="border border-slate-200 bg-white rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase tracking-wider sticky top-0 font-semibold">
                <tr>
                  <th className="py-2.5 px-4 font-semibold">Account ID</th>
                  <th className="py-2.5 px-4 font-semibold">Risk Index</th>
                  <th className="py-2.5 px-4 font-semibold">Candidate Roles</th>
                  <th className="py-2.5 px-4 font-semibold">Velocity (3-15m)</th>
                  <th className="py-2.5 px-4 font-semibold">Observed Inflow</th>
                  <th className="py-2.5 px-4 font-semibold">Observed Outflow</th>
                  <th className="py-2.5 px-4 font-semibold">Net Flow Delta</th>
                  <th className="py-2.5 px-4 font-semibold">Fan In / Out</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-800">
                {filteredItems.map((item) => {
                  const hasRoles = item.layer1_candidate || item.layer2_candidate || item.layer3_candidate;
                  return (
                    <tr
                      key={item.account_number}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      <td className="py-2.5 px-4 font-semibold">
                        <button
                          type="button"
                          onClick={() => navigate(`/victim/${item.account_number}`)}
                          className="hover:text-violet-900 text-violet-700 font-mono font-semibold transition"
                        >
                          {item.account_number}
                        </button>
                      </td>
                      <td className="py-2.5 px-4">
                        <RiskBadge score={item.risk_index} band={item.risk_band} size="sm" />
                      </td>
                      <td className="py-2.5 px-4">
                        <div className="flex flex-wrap items-center gap-1">
                          {item.layer1_candidate && <RoleBadge role="L1" size="sm" />}
                          {item.layer2_candidate && <RoleBadge role="L2" size="sm" />}
                          {item.layer3_candidate && <RoleBadge role="L3" size="sm" />}
                          {!hasRoles && (
                            <span className="text-slate-400 text-[10px]">Baseline</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-4">
                        {item.pass_through_candidate ? (
                          <div className="flex items-center gap-1.5 text-amber-700 font-semibold">
                            <Zap className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                            <span className="tabular-nums">
                              {item.pass_through_ratio !== null ? `${(item.pass_through_ratio * 100).toFixed(0)}%` : 'Active'}
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px]">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-emerald-700 font-semibold tabular-nums">
                        ₹{item.incoming_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-4 text-rose-700 font-semibold tabular-nums">
                        ₹{item.outgoing_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className={`py-2.5 px-4 font-semibold tabular-nums ${item.net_flow_delta >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                        {item.net_flow_delta >= 0 ? '+' : ''}
                        ₹{item.net_flow_delta.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-4 text-slate-700 tabular-nums">
                        <span className="text-violet-700 font-semibold">{item.fan_in}</span>
                        <span className="text-slate-400 mx-1">/</span>
                        <span className="text-amber-700 font-semibold">{item.fan_out}</span>
                      </td>
                      <td className="py-2.5 px-4 text-right space-x-1 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => navigate(`/victim/${item.account_number}`)}
                          className="bg-violet-50 hover:bg-violet-100 border border-violet-200 text-violet-700 px-2 py-0.5 rounded text-[11px] font-semibold transition"
                        >
                          Investigate
                        </button>
                        <button
                          type="button"
                          onClick={() => navigate(`/graph?account=${item.account_number}`)}
                          className="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 px-2 py-0.5 rounded text-[11px] transition"
                        >
                          Graph
                        </button>
                        <button
                          type="button"
                          onClick={() => navigate(`/timeline?account_id=${item.account_number}`)}
                          className="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 px-2 py-0.5 rounded text-[11px] transition"
                        >
                          Timeline
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs font-mono text-slate-600">
            <div>
              Showing {page * pageSize + 1}–{Math.min(totalCount, (page + 1) * pageSize)} of {totalCount.toLocaleString()} candidates
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => updateParam('page', Math.max(0, page - 1).toString())}
                disabled={page === 0}
                className="p-1 rounded bg-white border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="tabular-nums font-semibold">
                Page {page + 1} of {Math.max(1, totalPages)}
              </span>
              <button
                type="button"
                onClick={() => updateParam('page', Math.min(totalPages - 1, page + 1).toString())}
                disabled={page >= totalPages - 1}
                className="p-1 rounded bg-white border border-slate-200 hover:bg-slate-100 disabled:opacity-40 text-slate-700 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Forensic Notice */}
      <div className="text-[10px] font-mono text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200">
        NOTICE: Candidate classifications are explainable mathematical indicators derived from observed dataset activity. They do not constitute formal legal proof or beneficial ownership determinations.
      </div>
    </div>
  );
};
