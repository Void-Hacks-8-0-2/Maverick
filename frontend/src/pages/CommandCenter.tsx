import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Database,
  TrendingUp,
  Layers,
  Info,
  Loader2
} from 'lucide-react';
import { getDatasetSummary } from '../api/dataset';
import { searchAccounts } from '../api/accounts';
import type { DatasetSummary, AccountSearchItem } from '../types';
import { DatasetStatusCard } from '../components/DatasetStatusCard';

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();

  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<AccountSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    getDatasetSummary()
      .then((data) => {
        setSummary(data);
        setLoadingSummary(false);
      })
      .catch((err) => {
        setSummaryError(err.message || 'Failed to load dataset summary');
        setLoadingSummary(false);
      });

    // Initial search for prominent accounts
    searchAccounts('KKBK', 8)
      .then((res) => setSearchResults(res))
      .catch(() => {});
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    setSearchError(null);
    searchAccounts(searchQuery.trim(), 20)
      .then((res) => {
        setSearchResults(res);
        setSearching(false);
      })
      .catch((err) => {
        setSearchError(err.message || 'Search failed');
        setSearching(false);
      });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Active Development Dataset Status Component */}
      <DatasetStatusCard summary={summary} />

      {/* Dataset KPI Summary Cards */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-mono font-semibold tracking-wider text-slate-400 uppercase">
            Dataset Summary & Health Metrics
          </h2>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
            SOURCE: {summary?.source_type || 'PRODUCTION_DATASET'}
          </span>
        </div>

        {loadingSummary ? (
          <div className="h-28 flex items-center justify-center bg-slate-900/60 rounded-xl border border-slate-800">
            <Loader2 className="w-6 h-6 text-cyan-400 animate-spin" />
            <span className="ml-2 text-xs font-mono text-slate-400">Loading dataset metrics...</span>
          </div>
        ) : summaryError ? (
          <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-xs text-rose-300 font-mono">
            {summaryError}
          </div>
        ) : summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Row Count */}
            <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-mono">TOTAL TRANSACTIONS</span>
                <Database className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                {summary.row_count.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Unique Tx: {summary.unique_transactions.toLocaleString()}
              </div>
            </div>

            {/* Card 2: Unique Accounts */}
            <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-mono">UNIQUE ACCOUNTS</span>
                <Layers className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                {summary.unique_accounts.toLocaleString()}
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Senders & Receivers
              </div>
            </div>

            {/* Card 3: Total Flow */}
            <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-mono">OBSERVED VOLUME</span>
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100">
                ₹{summary.total_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
              <div className="text-[11px] text-emerald-400 font-mono">
                INR Total Value Transferred
              </div>
            </div>

            {/* Card 4: Source Attributes */}
            <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-mono">SOURCE ATTRIBUTES</span>
                <Info className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="space-y-1">
                <div className="text-xs font-mono text-slate-300 flex items-center justify-between">
                  <span>Timestamp:</span>
                  <span className="text-emerald-400 font-semibold">Available</span>
                </div>
                <div className="text-xs font-mono text-slate-300 flex items-center justify-between">
                  <span>Device_Type:</span>
                  <span className="text-emerald-400 font-semibold">Available</span>
                </div>
              </div>
              <div className="text-[10px] text-cyan-500/80 font-mono">
                All 11 forensic fields validated
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Payment Modes Distribution */}
      {summary && (
        <div className="bg-[#0b0f19] border border-slate-800 p-4 rounded-xl space-y-3">
          <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
            Payment Mode Distribution in Production Transactions
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(summary.payment_modes).map(([mode, count]) => {
              const pct = ((count / summary.row_count) * 100).toFixed(1);
              return (
                <div key={mode} className="bg-slate-900/80 border border-slate-800/80 p-3 rounded-lg">
                  <div className="text-xs font-mono text-cyan-400 font-bold">{mode}</div>
                  <div className="text-lg font-bold font-mono text-slate-200 mt-1">
                    {count.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono">{pct}% of dataset</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Account Search Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold font-mono text-slate-100">Account Investigation Search</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Query any account number to inspect transaction history, observed counterparty movements, and topological network graph.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search account ID (e.g. KKBK10000000, ICIC10000335)..."
              className="w-full bg-[#0b0f19] border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
            />
          </div>
          <button
            type="submit"
            disabled={searching}
            className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-xs font-semibold font-mono flex items-center space-x-1.5 transition"
          >
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Search</span>}
          </button>
        </form>

        {searchError && (
          <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-xs font-mono text-rose-300">
            {searchError}
          </div>
        )}

        {/* Results Table */}
        <div className="bg-[#0b0f19] border border-slate-800 rounded-xl overflow-hidden shadow-lg">
          <div className="p-3 bg-slate-900/60 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">
              {searching ? 'Querying dataset...' : `Matching Accounts (${searchResults.length})`}
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              Observed Net Movement = Inflow - Outflow
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/40 text-slate-400 border-b border-slate-800 text-[11px]">
                <tr>
                  <th className="py-2.5 px-4">Account ID</th>
                  <th className="py-2.5 px-4">Inbound Tx</th>
                  <th className="py-2.5 px-4">Outbound Tx</th>
                  <th className="py-2.5 px-4">Observed Inflow</th>
                  <th className="py-2.5 px-4">Observed Outflow</th>
                  <th className="py-2.5 px-4">Net Movement</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {searchResults.length === 0 && !searching ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No matching accounts found. Try searching for "KKBK", "ICIC", or "PYTM".
                    </td>
                  </tr>
                ) : (
                  searchResults.map((item) => (
                    <tr key={item.account} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-4 font-bold text-slate-100 flex items-center space-x-2">
                        <span>{item.account}</span>
                      </td>
                      <td className="py-3 px-4 text-emerald-400">
                        {item.inbound_transaction_count}
                      </td>
                      <td className="py-3 px-4 text-rose-400">
                        {item.outbound_transaction_count}
                      </td>
                      <td className="py-3 px-4 text-emerald-400 font-semibold">
                        ₹{item.observed_inflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-rose-400 font-semibold">
                        ₹{item.observed_outflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className={`py-3 px-4 font-bold ${item.dataset_observed_net_movement >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {item.dataset_observed_net_movement >= 0 ? '+' : ''}
                        ₹{item.dataset_observed_net_movement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-3 px-4 text-right space-x-1.5">
                        <button
                          onClick={() => navigate(`/account/${item.account}`)}
                          className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded text-[11px] transition"
                        >
                          Details
                        </button>
                        <button
                          onClick={() => navigate(`/graph?account=${item.account}`)}
                          className="bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-800/60 text-cyan-300 px-2.5 py-1 rounded text-[11px] transition"
                        >
                          Graph
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
