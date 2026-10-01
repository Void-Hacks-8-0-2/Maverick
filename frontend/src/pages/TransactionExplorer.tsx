import React, { useEffect, useState } from 'react';
import { Search, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { getAccountTransactions } from '../api/transactions';
import type { TransactionItem } from '../types';

export const TransactionExplorer: React.FC = () => {
  const [targetAccount, setTargetAccount] = useState('KKBK10000000');
  const [inputAccount, setInputAccount] = useState('KKBK10000000');
  const [direction, setDirection] = useState<'all' | 'in' | 'out'>('all');
  const [page, setPage] = useState(0);
  const pageSize = 25;

  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getAccountTransactions(targetAccount, direction, pageSize, page * pageSize)
      .then((res) => {
        setTransactions(res.items);
        setTotalCount(res.total_count);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to fetch transactions');
        setLoading(false);
      });
  }, [targetAccount, direction, page]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputAccount.trim()) return;
    setTargetAccount(inputAccount.trim());
    setPage(0);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Title & Filter Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-slate-100 tracking-wide">
            Transaction Ledger Explorer
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Displaying production transaction ledger from <span className="text-cyan-400">VoidHacks8_MuleAccount_2M_Transactions.csv</span>.
          </p>
        </div>

        {/* Account search input */}
        <form onSubmit={handleFilterSubmit} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={inputAccount}
              onChange={(e) => setInputAccount(e.target.value)}
              placeholder="Account ID (e.g. KKBK10000000)"
              className="bg-[#0b0f19] border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition w-60"
            />
          </div>
          <button
            type="submit"
            className="bg-cyan-600 hover:bg-cyan-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
          >
            Filter
          </button>
        </form>
      </div>

      {/* Main Ledger Table */}
      <div className="bg-[#0b0f19] border border-slate-800 rounded-xl overflow-hidden shadow-2xl space-y-0">
        <div className="p-4 bg-slate-900/60 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3 text-xs font-mono">
            <span className="text-slate-400">
              Filter Account: <span className="text-cyan-400 font-bold">{targetAccount}</span>
            </span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">
              Total Records: <span className="text-slate-200 font-semibold">{totalCount}</span>
            </span>
          </div>

          <div className="flex items-center space-x-3">
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
            <div className="flex items-center space-x-1.5 font-mono text-xs text-slate-400">
              <span>
                Page {page + 1} of {Math.max(1, Math.ceil(totalCount / pageSize))}
              </span>
              <button
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="p-1 bg-slate-950 border border-slate-800 rounded disabled:opacity-30 hover:bg-slate-800"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={(page + 1) * pageSize >= totalCount}
                onClick={() => setPage((p) => p + 1)}
                className="p-1 bg-slate-950 border border-slate-800 rounded disabled:opacity-30 hover:bg-slate-800"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/40 border-b border-rose-800 text-xs font-mono text-rose-300">
            {error}
          </div>
        )}

        {/* Ledger Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-900/40 text-slate-400 border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-2.5 px-4">Transaction ID</th>
                <th className="py-2.5 px-4">Sender Account</th>
                <th className="py-2.5 px-4">Receiver Account</th>
                <th className="py-2.5 px-4">Amount (INR)</th>
                <th className="py-2.5 px-4">Payment Mode</th>
                <th className="py-2.5 px-4">Narration</th>
                <th className="py-2.5 px-4">IP Address</th>
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-4">Device</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-1 text-cyan-400" />
                    <span>Loading ledger records...</span>
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500">
                    No transactions found matching this account filter.
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.Transaction_ID} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-semibold text-slate-200">
                      {tx.Transaction_ID}
                    </td>
                    <td className="py-3 px-4">
                      <span className={tx.Sender_Account === targetAccount ? 'text-cyan-400 font-bold' : 'text-slate-300'}>
                        {tx.Sender_Account}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={tx.Receiver_Account === targetAccount ? 'text-purple-400 font-bold' : 'text-slate-300'}>
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
                    <td className="py-3 px-4 text-slate-300 text-[11px] whitespace-nowrap">
                      {tx.Timestamp || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-300 text-[11px]">
                      {tx.Device_Type ? (
                        <span className="bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded text-[10px]">
                          {tx.Device_Type}
                        </span>
                      ) : (
                        '—'
                      )}
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
