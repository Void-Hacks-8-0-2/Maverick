import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  SlidersHorizontal,
  X,
  ExternalLink,
  AlertTriangle,
  ListFilter
} from 'lucide-react';
import {
  queryTransactionsExplorer,
  getTransactionDetail,
} from '../api/explorer';
import type { ForensicTransactionItem, TransactionDetailResponse } from '../api/explorer';

// ─── Helpers ──────────────────────────────────────────────────────────────────
const PAYMENT_MODES = ['UPI', 'IMPS', 'NEFT', 'RTGS'];
const DEVICE_TYPES = ['Android', 'iOS', 'Windows_Browser', 'Web_Emulator', 'Linux_Script'];
const SORT_FIELDS = [
  { value: 'timestamp', label: 'Timestamp' },
  { value: 'amount', label: 'Amount' },
  { value: 'transaction_id', label: 'Transaction ID' },
] as const;

function fmt(n: number) {
  return '₹' + n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ─── Detail Drawer (Level 3 Surface) ──────────────────────────────────────────
interface DetailDrawerProps {
  stableId: string | null;
  onClose: () => void;
}

const DetailDrawer: React.FC<DetailDrawerProps> = ({ stableId, onClose }) => {
  const [data, setData] = useState<TransactionDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!stableId) { setData(null); return; }
    setLoading(true);
    getTransactionDetail(stableId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [stableId]);

  if (!stableId) return null;

  const tx = data?.transaction;
  const links = data?.investigation_links as Record<string, unknown> | undefined;

  return (
    <div className="fixed inset-y-0 right-0 w-96 surface-l3 border-l border-white/[0.08] shadow-2xl z-50 flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <span className="text-xs font-mono font-semibold text-slate-100 uppercase tracking-wider">Transaction Ledger Inspector</span>
        <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded transition text-slate-400 hover:text-slate-200">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-mono">
        {loading && (
          <div className="flex items-center justify-center py-10 text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin mr-2 text-cyan-400" />
            Loading transaction details…
          </div>
        )}

        {!loading && tx && (
          <>
            {tx.is_duplicate_tx_id && (
              <div className="bg-amber-950/25 border border-amber-500/30 rounded p-2.5 text-amber-300 space-y-1">
                <div className="flex items-center gap-1.5 font-medium text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                  <span>DUPLICATE TRANSACTION ID</span>
                </div>
                <div className="text-[10px] text-slate-400 leading-normal">
                  2+ independent source records share this ID. Duplicate IDs do not necessarily indicate fraudulent activity.
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Row label="Stable ID" value={tx.stable_id} />
              <Row label="Transaction ID" value={tx.Transaction_ID} />
              <Row label="Timestamp" value={tx.Timestamp.replace('T', ' ')} />
              <Row label="Amount" value={fmt(tx.Amount)} highlight />
              <Row label="Payment Mode" value={tx.Payment_Mode} />
              <Row label="Device" value={tx.Device_Type} />
              <Row label="IP Address" value={tx.IP_Address} />
              <Row label="Narration" value={tx.Narration || '—'} />
            </div>

            <div className="border-t border-white/[0.06] pt-3 space-y-1.5">
              <div className="text-slate-400 uppercase text-[9px] tracking-wider mb-1 font-semibold">Counterparties</div>
              <Row label="Sender" value={tx.Sender_Account} />
              <Row label="Sender IFSC" value={tx.Sender_IFSC} />
              <Row label="Receiver" value={tx.Receiver_Account} />
              <Row label="Receiver IFSC" value={tx.Receiver_IFSC} />
            </div>

            {links && (
              <div className="border-t border-white/[0.06] pt-3 space-y-1.5">
                <div className="text-slate-400 uppercase text-[9px] tracking-wider mb-1 font-semibold">Forensic Classification</div>
                {links.sender_mule_risk ? (
                  <Row
                    label="Sender Risk"
                    value={`${String((links.sender_mule_risk as Record<string, unknown>).score)}/100 · ${String((links.sender_mule_risk as Record<string, unknown>).band)}`}
                    highlight
                  />
                ) : null}
                {links.sender_mule_role ? (
                  <Row label="Sender Role" value={String(links.sender_mule_role)} />
                ) : null}
                {links.receiver_mule_risk ? (
                  <Row
                    label="Receiver Risk"
                    value={`${String((links.receiver_mule_risk as Record<string, unknown>).score)}/100 · ${String((links.receiver_mule_risk as Record<string, unknown>).band)}`}
                    highlight
                  />
                ) : null}
                {links.receiver_mule_role ? (
                  <Row label="Receiver Role" value={String(links.receiver_mule_role)} />
                ) : null}
              </div>
            )}

            {links?.links && (
              <div className="border-t border-white/[0.06] pt-3 space-y-1">
                <div className="text-slate-400 uppercase text-[9px] tracking-wider mb-1 font-semibold">Investigation Shortcuts</div>
                {Object.entries(links.links as Record<string, string>).map(([k, v]) => (
                  <a
                    key={k}
                    href={v}
                    className="flex items-center gap-1.5 text-cyan-300 hover:underline transition py-0.5"
                  >
                    <ExternalLink className="w-3 h-3 text-cyan-400" />
                    <span>{k.replace(/_/g, ' ')}</span>
                  </a>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

const Row: React.FC<{ label: string; value: string; highlight?: boolean }> = ({ label, value, highlight }) => (
  <div className="flex justify-between gap-2">
    <span className="text-slate-400 uppercase text-[10px] shrink-0">{label}:</span>
    <span className={`text-right break-all font-mono tabular-nums ${highlight ? 'text-cyan-300 font-semibold' : 'text-slate-200'}`}>{value}</span>
  </div>
);

// ─── Main Page ────────────────────────────────────────────────────────────────
export const TransactionExplorer: React.FC = () => {
  // Filter state
  const [accountId, setAccountId] = useState('');
  const [txId, setTxId] = useState('');
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [paymentMode, setPaymentMode] = useState('');
  const [deviceType, setDeviceType] = useState('');
  const [narration, setNarration] = useState('');
  const [sortBy, setSortBy] = useState<'timestamp' | 'amount' | 'transaction_id'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showFilters, setShowFilters] = useState(false);

  // Applied (committed) filter state — triggers fetch
  const [applied, setApplied] = useState({
    accountId: '', txId: '', minAmount: '', maxAmount: '',
    startTime: '', endTime: '', paymentMode: '', deviceType: '', narration: '',
    sortBy: 'timestamp' as 'timestamp' | 'amount' | 'transaction_id', sortOrder: 'desc' as 'asc' | 'desc',
  });

  const [page, setPage] = useState(1);
  const pageSize = 50;

  const [items, setItems] = useState<ForensicTransactionItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const fetchRef = useRef(0);

  const doFetch = useCallback(() => {
    const seq = ++fetchRef.current;
    setLoading(true);
    setError(null);

    const params = {
      ...(applied.accountId && { account_id: applied.accountId }),
      ...(applied.txId && { transaction_id: applied.txId }),
      ...(applied.minAmount && { min_amount: Number(applied.minAmount) }),
      ...(applied.maxAmount && { max_amount: Number(applied.maxAmount) }),
      ...(applied.startTime && { start_time: applied.startTime }),
      ...(applied.endTime && { end_time: applied.endTime }),
      ...(applied.paymentMode && { payment_mode: applied.paymentMode }),
      ...(applied.deviceType && { device_type: applied.deviceType }),
      ...(applied.narration && { narration: applied.narration }),
      sort_by: applied.sortBy,
      sort_order: applied.sortOrder,
      page,
      page_size: pageSize,
    };

    queryTransactionsExplorer(params)
      .then((res) => {
        if (seq !== fetchRef.current) return;
        setItems(res.items);
        setTotalCount(res.total_count);
        setTotalPages(res.total_pages);
        setHasNext(res.has_next);
      })
      .catch((err) => {
        if (seq !== fetchRef.current) return;
        setError(err.message || 'Failed to fetch transactions');
      })
      .finally(() => {
        if (seq === fetchRef.current) setLoading(false);
      });
  }, [applied, page]);

  useEffect(() => { doFetch(); }, [doFetch]);

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setApplied({ accountId, txId, minAmount, maxAmount, startTime, endTime, paymentMode, deviceType, narration, sortBy, sortOrder });
  };

  const handleClearAll = () => {
    setAccountId(''); setTxId(''); setMinAmount(''); setMaxAmount('');
    setStartTime(''); setEndTime(''); setPaymentMode(''); setDeviceType(''); setNarration('');
    setSortBy('timestamp'); setSortOrder('desc');
    setPage(1);
    setApplied({ accountId: '', txId: '', minAmount: '', maxAmount: '', startTime: '', endTime: '', paymentMode: '', deviceType: '', narration: '', sortBy: 'timestamp', sortOrder: 'desc' });
  };

  const activeFilterCount = [applied.accountId, applied.txId, applied.minAmount, applied.maxAmount, applied.startTime, applied.endTime, applied.paymentMode, applied.deviceType, applied.narration].filter(Boolean).length;

  return (
    <div className="space-y-4">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 pb-4 border-b border-white/[0.06]">
        <div>
          <div className="text-[10px] font-mono tracking-widest text-cyan-400 uppercase mb-1">
            FORENSIC FINANCIAL LEDGER
          </div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-100 tracking-tight font-sans flex items-center gap-2">
            <ListFilter className="w-5 h-5 text-cyan-400" />
            <span>Transaction Explorer</span>
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Server-side DuckDB query over{' '}
            <span className="text-cyan-300 font-medium">2,000,000 production transactions</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded border text-xs font-mono transition ${
              showFilters || activeFilterCount > 0
                ? 'bg-slate-800 border-cyan-500/50 text-cyan-300 font-medium'
                : 'bg-[#06080d]/80 border-white/[0.08] text-slate-400 hover:text-slate-200'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="ml-0.5 bg-cyan-500 text-slate-950 font-bold rounded-full w-4 h-4 flex items-center justify-center text-[9px]">
                {activeFilterCount}
              </span>
            )}
          </button>
          {activeFilterCount > 0 && (
            <button
              onClick={handleClearAll}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded border border-white/[0.08] bg-[#06080d]/80 text-xs font-mono text-slate-400 hover:text-rose-400 transition"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Filter Panel ───────────────────────────────────────── */}
      {showFilters && (
        <form
          onSubmit={handleApply}
          className="surface-l1 border border-white/[0.06] rounded-xl p-4 space-y-3"
        >
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 text-xs font-mono">
            <FilterField label="Account ID" value={accountId} onChange={setAccountId} placeholder="e.g. KKBK10000402" />
            <FilterField label="Transaction ID" value={txId} onChange={setTxId} placeholder="TXN... or partial" />
            <FilterField label="Min Amount (₹)" value={minAmount} onChange={setMinAmount} placeholder="e.g. 10000" type="number" />
            <FilterField label="Max Amount (₹)" value={maxAmount} onChange={setMaxAmount} placeholder="e.g. 500000" type="number" />
            <FilterField label="Start Time" value={startTime} onChange={setStartTime} placeholder="2026-09-15 00:00:00" />
            <FilterField label="End Time" value={endTime} onChange={setEndTime} placeholder="2026-09-29 23:59:58" />
            <FilterField label="Narration (contains)" value={narration} onChange={setNarration} placeholder="keyword" />
            <FilterField label="IP Address" value={''} onChange={() => {}} placeholder="filter disabled" disabled />

            <div className="space-y-1">
              <label className="text-slate-400 uppercase text-[9px] tracking-wider block">Payment Mode</label>
              <select
                value={paymentMode}
                onChange={(e) => setPaymentMode(e.target.value)}
                className="w-full bg-[#06080d]/80 border border-white/[0.08] rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 transition"
              >
                <option value="">All</option>
                {PAYMENT_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-400 uppercase text-[9px] tracking-wider block">Device Type</label>
              <select
                value={deviceType}
                onChange={(e) => setDeviceType(e.target.value)}
                className="w-full bg-[#06080d]/80 border border-white/[0.08] rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 transition"
              >
                <option value="">All</option>
                {DEVICE_TYPES.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-400 uppercase text-[9px] tracking-wider block">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="w-full bg-[#06080d]/80 border border-white/[0.08] rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 transition"
              >
                {SORT_FIELDS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-slate-400 uppercase text-[9px] tracking-wider block">Order</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                className="w-full bg-[#06080d]/80 border border-white/[0.08] rounded px-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 transition"
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.06]">
            <button
              type="button"
              onClick={handleClearAll}
              className="px-3 py-1.5 text-xs font-mono rounded border border-white/[0.08] text-slate-400 hover:text-slate-200 transition"
            >
              Clear All
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold transition"
            >
              Apply Filters
            </button>
          </div>
        </form>
      )}

      {/* ── Stats Bar ──────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 surface-l1 border border-white/[0.06] rounded-lg px-4 py-2">
        <span>Records: <span className="text-slate-200 font-semibold tabular-nums">{totalCount.toLocaleString()}</span></span>
        <span className="text-slate-700">|</span>
        <span>Page <span className="text-slate-200 tabular-nums">{page}</span> of <span className="text-slate-200 tabular-nums">{totalPages}</span></span>
        <span className="text-slate-700">|</span>
        <span>Sort: <span className="text-cyan-300 font-medium">{sortBy} {sortOrder}</span></span>
        {applied.accountId && (
          <><span className="text-slate-700">|</span>
          <span>Account: <span className="text-cyan-300 font-medium">{applied.accountId}</span></span></>
        )}
      </div>

      {/* ── Table ──────────────────────────────────────────────── */}
      <div className="surface-l2 border border-white/[0.06] rounded-xl overflow-hidden shadow-2xl">
        {error && (
          <div className="p-3 bg-rose-950/20 border-b border-rose-500/30 text-xs font-mono text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#070a12] text-slate-400 border-b border-white/[0.06] text-[10px] uppercase tracking-wider sticky top-0">
              <tr>
                <th className="py-2.5 px-3">Tx ID</th>
                <th className="py-2.5 px-3">Sender</th>
                <th className="py-2.5 px-3">Receiver</th>
                <th className="py-2.5 px-3 text-right">Amount</th>
                <th className="py-2.5 px-3">Mode</th>
                <th className="py-2.5 px-3">Device</th>
                <th className="py-2.5 px-3">Narration</th>
                <th className="py-2.5 px-3">IP</th>
                <th className="py-2.5 px-3 whitespace-nowrap">Timestamp</th>
                <th className="py-2.5 px-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] text-slate-300">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-14 text-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto mb-1.5 text-cyan-400" />
                    Querying 2M transaction dataset…
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-14 text-center text-slate-400">
                    No transactions match your filter criteria.
                  </td>
                </tr>
              ) : (
                items.map((tx) => (
                  <tr
                    key={tx.stable_id}
                    className={`hover:bg-slate-800/30 transition cursor-pointer ${
                      selectedId === tx.stable_id ? 'bg-slate-800/40 border-l-2 border-cyan-400' : ''
                    }`}
                    onClick={() => setSelectedId(selectedId === tx.stable_id ? null : tx.stable_id)}
                  >
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-1">
                        <span className="text-slate-100 font-medium">{tx.Transaction_ID}</span>
                        {tx.is_duplicate_tx_id && (
                          <span title="Duplicate TX ID in dataset">
                            <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-3">
                      <span className={applied.accountId && tx.Sender_Account === applied.accountId ? 'text-cyan-300 font-semibold' : ''}>
                        {tx.Sender_Account}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className={applied.accountId && tx.Receiver_Account === applied.accountId ? 'text-purple-300 font-semibold' : ''}>
                        {tx.Receiver_Account}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-right text-emerald-400 font-medium tabular-nums whitespace-nowrap">
                      {fmt(tx.Amount)}
                    </td>
                    <td className="py-2 px-3">
                      <span className="text-[10px] bg-[#06080d]/80 border border-white/[0.06] text-slate-300 px-1.5 py-0.2 rounded font-mono">
                        {tx.Payment_Mode}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-400">{tx.Device_Type}</td>
                    <td className="py-2 px-3 text-slate-400 max-w-[160px] truncate" title={tx.Narration}>
                      {tx.Narration || '—'}
                    </td>
                    <td className="py-2 px-3 text-slate-400">{tx.IP_Address}</td>
                    <td className="py-2 px-3 text-slate-400 tabular-nums whitespace-nowrap">{tx.Timestamp.replace('T', ' ')}</td>
                    <td className="py-2 px-3">
                      <ExternalLink className="w-3.5 h-3.5 text-slate-500 hover:text-cyan-400 transition" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-white/[0.06] bg-[#070a12]/60 text-xs font-mono text-slate-400">
          <span className="tabular-nums">{totalCount.toLocaleString()} records total</span>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="p-1.5 bg-[#06080d] border border-white/[0.08] rounded disabled:opacity-30 hover:bg-slate-800 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="tabular-nums">
              {page} / {totalPages}
            </span>
            <button
              disabled={!hasNext}
              onClick={() => setPage((p) => p + 1)}
              className="p-1.5 bg-[#06080d] border border-white/[0.08] rounded disabled:opacity-30 hover:bg-slate-800 transition"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      <DetailDrawer stableId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  );
};

// ─── Filter Field Helper ──────────────────────────────────────────────────────
interface FilterFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}

const FilterField: React.FC<FilterFieldProps> = ({ label, value, onChange, placeholder, type = 'text', disabled }) => (
  <div className="space-y-1">
    <label className="text-slate-400 uppercase text-[9px] tracking-wider block">{label}</label>
    <div className="relative">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full bg-[#06080d]/80 border border-white/[0.08] rounded pl-7 pr-2 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 transition placeholder-slate-500 disabled:opacity-30"
      />
    </div>
  </div>
);
