import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Network,
  Share2,
  TrendingUp,
  TrendingDown,
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  Loader2,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { getAccountDetail } from '../api/accounts';
import { getAccountTransactions } from '../api/transactions';
import type { AccountDetail, PaginatedTransactions, TransactionItem } from '../types';

export const AccountView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<AccountDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Transactions pagination state
  const [direction, setDirection] = useState<'all' | 'in' | 'out'>('all');
  const [page, setPage] = useState(0);
  const pageSize = 20;
  const [txData, setTxData] = useState<PaginatedTransactions | null>(null);
  const [loadingTx, setLoadingTx] = useState(true);

  useEffect(() => {
    if (!id) return;

    setLoadingDetail(true);
    setDetailError(null);

    getAccountDetail(id)
      .then((data) => {
        setDetail(data);
        setLoadingDetail(false);
      })
      .catch((err) => {
        setDetailError(err.message || 'Failed to load account details');
        setLoadingDetail(false);
      });
  }, [id]);

  useEffect(() => {
    if (!id) return;

    setLoadingTx(true);
    getAccountTransactions(id, direction, pageSize, page * pageSize)
      .then((data) => {
        setTxData(data);
        setLoadingTx(false);
      })
      .catch(() => {
        setLoadingTx(false);
      });
  }, [id, direction, page]);

  if (loadingDetail) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <span className="ml-3 font-mono text-sm text-slate-400">Loading account dossier...</span>
      </div>
    );
  }

  if (detailError || !detail) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 space-y-4">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center space-x-1 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>
        <div className="bg-rose-950/40 border border-rose-800 p-6 rounded-xl font-mono text-xs text-rose-300">
          <p className="font-bold text-sm">Account Not Found</p>
          <p className="mt-1">{detailError || `Account ${id} was not observed in the production dataset.`}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Breadcrumb & Action Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-mono text-slate-500 uppercase">Target Account</span>
              <span className="bg-slate-800 border border-slate-700 text-slate-300 text-[10px] font-mono px-1.5 py-0.5 rounded">
                OBSERVED IN DATASET
              </span>
            </div>
            <h1 className="text-xl font-bold font-mono text-slate-100 tracking-wide mt-0.5">
              {detail.account_id}
            </h1>
          </div>
        </div>

        {/* Buttons calling real APIs */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => navigate(`/graph?account=${detail.account_id}&mode=ego`)}
            className="bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 px-3.5 py-2 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5 transition shadow"
          >
            <Network className="w-4 h-4" />
            <span>View Network</span>
          </button>

          <button
            onClick={() => navigate(`/graph?account=${detail.account_id}&mode=trace`)}
            className="bg-purple-950 hover:bg-purple-900 border border-purple-700 text-purple-300 px-3.5 py-2 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5 transition shadow"
          >
            <Share2 className="w-4 h-4" />
            <span>Trace 4 Hops</span>
          </button>

          <button
            onClick={() => {
              const el = document.getElementById('transaction-history');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-3.5 py-2 rounded-lg text-xs font-mono font-semibold flex items-center space-x-1.5 transition"
          >
            <Activity className="w-4 h-4" />
            <span>View Transactions</span>
          </button>
        </div>
      </div>

      {/* Financial Movement Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Inflow */}
        <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono">OBSERVED INFLOW</span>
            <ArrowDownLeft className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            ₹{detail.observed_inflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {detail.inbound_transaction_count} inbound transactions from {detail.unique_senders} unique senders
          </div>
        </div>

        {/* Outflow */}
        <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono">OBSERVED OUTFLOW</span>
            <ArrowUpRight className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">
            ₹{detail.observed_outflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[11px] text-slate-500 font-mono">
            {detail.outbound_transaction_count} outbound transactions to {detail.unique_receivers} unique receivers
          </div>
        </div>

        {/* Net Movement */}
        <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-mono">DATASET-OBSERVED NET MOVEMENT</span>
            {detail.dataset_observed_net_movement >= 0 ? (
              <TrendingUp className="w-4 h-4 text-emerald-400" />
            ) : (
              <TrendingDown className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className={`text-2xl font-bold font-mono ${detail.dataset_observed_net_movement >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {detail.dataset_observed_net_movement >= 0 ? '+' : ''}
            ₹{detail.dataset_observed_net_movement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            *Observed in sample (not full bank balance)
          </div>
        </div>
      </div>

      {/* Associated Metadata (IFSC, IP, Payment Modes) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Payment Modes */}
        <div className="bg-[#0b0f19] border border-slate-800 p-4 rounded-xl space-y-2">
          <span className="text-xs font-mono text-slate-400 uppercase">Payment Modes</span>
          <div className="flex flex-wrap gap-2 pt-1">
            {Object.entries(detail.payment_mode_distribution).map(([pm, cnt]) => (
              <span key={pm} className="bg-slate-900 border border-slate-700/80 px-2.5 py-1 rounded text-xs font-mono text-slate-200">
                <span className="text-cyan-400 font-bold">{pm}</span>: {cnt}
              </span>
            ))}
          </div>
        </div>

        {/* Observed IFSCs */}
        <div className="bg-[#0b0f19] border border-slate-800 p-4 rounded-xl space-y-2">
          <span className="text-xs font-mono text-slate-400 uppercase">Observed IFSC Codes</span>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {detail.associated_ifscs.map((ifsc) => (
              <span key={ifsc} className="bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[11px] px-2 py-0.5 rounded">
                {ifsc}
              </span>
            ))}
          </div>
        </div>

        {/* Observed IPs */}
        <div className="bg-[#0b0f19] border border-slate-800 p-4 rounded-xl space-y-2">
          <span className="text-xs font-mono text-slate-400 uppercase">Observed IP Endpoints</span>
          <div className="flex flex-wrap gap-1.5 pt-1 max-h-24 overflow-y-auto">
            {detail.associated_ips.map((ip) => (
              <span key={ip} className="bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[11px] px-2 py-0.5 rounded">
                {ip}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Transaction History Section */}
      <div id="transaction-history" className="bg-[#0b0f19] border border-slate-800 rounded-xl overflow-hidden shadow-xl space-y-0">
        {/* Table Header Filter Toolbar */}
        <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-semibold text-slate-300 uppercase">
              Observed Transactions ({txData?.total_count || 0})
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {/* Direction Filter */}
            <div className="flex bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs font-mono">
              {(['all', 'in', 'out'] as const).map((dir) => (
                <button
                  key={dir}
                  onClick={() => {
                    setDirection(dir);
                    setPage(0);
                  }}
                  className={`px-3 py-1 rounded text-xs capitalize transition ${
                    direction === dir
                      ? 'bg-slate-800 text-cyan-400 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {dir}
                </button>
              ))}
            </div>

            {/* Pagination Controls */}
            {txData && (
              <div className="flex items-center space-x-1.5 font-mono text-xs text-slate-400">
                <span>
                  Page {page + 1} of {Math.max(1, Math.ceil(txData.total_count / pageSize))}
                </span>
                <button
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  className="p-1 bg-slate-950 border border-slate-800 rounded disabled:opacity-30 hover:bg-slate-800"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={(page + 1) * pageSize >= txData.total_count}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-1 bg-slate-950 border border-slate-800 rounded disabled:opacity-30 hover:bg-slate-800"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/40 text-slate-400 border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Transaction ID</th>
                <th className="py-2.5 px-4">Sender</th>
                <th className="py-2.5 px-4">Receiver</th>
                <th className="py-2.5 px-4">Amount</th>
                <th className="py-2.5 px-4">Mode</th>
                <th className="py-2.5 px-4">Narration</th>
                <th className="py-2.5 px-4">IP</th>
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Device</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {loadingTx ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-1 text-cyan-400" />
                    <span>Loading transactions...</span>
                  </td>
                </tr>
              ) : !txData || txData.items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-500">
                    No transactions found for this account and direction filter.
                  </td>
                </tr>
              ) : (
                txData.items.map((tx: TransactionItem) => (
                  <tr key={tx.Transaction_ID} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-semibold text-slate-200">
                      {tx.Transaction_ID}
                    </td>
                    <td className="py-3 px-4">
                      <span className={tx.Sender_Account === detail.account_id ? 'text-cyan-400 font-bold' : 'text-slate-300'}>
                        {tx.Sender_Account}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={tx.Receiver_Account === detail.account_id ? 'text-purple-400 font-bold' : 'text-slate-300'}>
                        {tx.Receiver_Account}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-emerald-400">
                      ₹{tx.Amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-3 px-4">
                      <span className="bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-[10px]">
                        {tx.Payment_Mode}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 max-w-[200px] truncate" title={tx.Narration}>
                      {tx.Narration}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{tx.IP_Address}</td>
                    <td className="py-3 px-4 text-slate-500 italic text-[11px]">
                      Unavailable
                    </td>
                    <td className="py-3 px-4 text-slate-500 italic text-[11px]">
                      Unavailable
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
