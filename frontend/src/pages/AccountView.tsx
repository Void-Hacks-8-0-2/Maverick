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
  ChevronRight,
  ShieldAlert,
  Zap,
  Clock,
  Info
} from 'lucide-react';
import { getAccountDetail, getAccountFeatures, getAccountVelocity } from '../api/accounts';
import { getAccountTransactions } from '../api/transactions';
import type { AccountDetail, PaginatedTransactions, TransactionItem, AccountFeatures, VelocityResponse } from '../types';

export const AccountView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<AccountDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Forensic Features & Velocity state (Step 4 & Step 5A)
  const [features, setFeatures] = useState<AccountFeatures | null>(null);
  const [velocity, setVelocity] = useState<VelocityResponse | null>(null);

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

    // Fetch forensic features and velocity in parallel
    getAccountFeatures(id)
      .then((feat) => setFeatures(feat))
      .catch(() => setFeatures(null));

    getAccountVelocity(id)
      .then((vel) => setVelocity(vel))
      .catch(() => setVelocity(null));
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

      {/* Forensic Intelligence & Candidate Classification (Step 4 & Step 5A) */}
      <div className="bg-[#0b0f19] border border-slate-800 rounded-xl p-5 space-y-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-mono font-bold uppercase tracking-wider text-slate-200">
              Forensic Candidate Intelligence & Behavioral Metrics
            </h2>
          </div>
          <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded">
            INVESTIGATIVE CANDIDATE INDICATORS ONLY &bull; NOT LEGAL DETERMINATION
          </span>
        </div>

        {/* Step 4 Candidate Role Badges */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Layer 1 */}
          <div className={`p-4 rounded-xl border font-mono transition ${
            features?.layer1_candidate
              ? 'bg-amber-950/20 border-amber-600/60 text-amber-300'
              : 'bg-slate-900/30 border-slate-800/70 text-slate-400'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase">Layer 1: Collector Mule</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                features?.layer1_candidate
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300'
                  : 'bg-slate-800 text-slate-500'
              }`}>
                {features?.layer1_candidate ? 'CANDIDATE' : 'NOT QUALIFIED'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              High-volume fan-in collection node consolidating funds from victim accounts.
            </p>
            {features?.layer1_candidate && features.layer1_reasons.length > 0 && (
              <div className="mt-3 pt-2 border-t border-amber-900/40 space-y-1">
                {features.layer1_reasons.map((r, i) => (
                  <div key={i} className="text-[10px] text-amber-200/90 flex items-start space-x-1">
                    <span className="text-amber-400 font-bold">&bull;</span>
                    <span>{r.description}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Layer 2 */}
          <div className={`p-4 rounded-xl border font-mono transition ${
            features?.layer2_candidate
              ? 'bg-cyan-950/20 border-cyan-600/60 text-cyan-300'
              : 'bg-slate-900/30 border-slate-800/70 text-slate-400'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase">Layer 2: Distributor Mule</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                features?.layer2_candidate
                  ? 'bg-cyan-500/20 border border-cyan-500/40 text-cyan-300'
                  : 'bg-slate-800 text-slate-500'
              }`}>
                {features?.layer2_candidate ? 'CANDIDATE' : 'NOT QUALIFIED'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              Layering node splitting inbound amounts into multiple outward dispersals.
            </p>
            {features?.layer2_candidate && features.layer2_reasons.length > 0 && (
              <div className="mt-3 pt-2 border-t border-cyan-900/40 space-y-1">
                {features.layer2_reasons.map((r, i) => (
                  <div key={i} className="text-[10px] text-cyan-200/90 flex items-start space-x-1">
                    <span className="text-cyan-400 font-bold">&bull;</span>
                    <span>{r.description}</span>
                  </div>
                ))}
              </div>
            )}
            {!features?.layer2_candidate && (
              <div className="mt-3 pt-2 border-t border-slate-800/80 text-[10px] space-y-1 text-slate-500 font-mono">
                <div className="flex justify-between">
                  <span>Observed Fan-out (Receivers):</span>
                  <span className="text-slate-300 font-bold">{features?.fan_out ?? detail.unique_receivers} <span className="text-slate-500 font-normal">/ 95 min</span></span>
                </div>
                <div className="flex justify-between">
                  <span>Outbound Tx Count:</span>
                  <span className="text-slate-300 font-bold">{features?.outgoing_txn_count ?? detail.outbound_transaction_count} <span className="text-slate-500 font-normal">/ 95 min</span></span>
                </div>
                <p className="text-[10px] text-slate-400 mt-1 italic">
                  Does not qualify: below structural threshold of 95 receivers.
                </p>
              </div>
            )}
          </div>

          {/* Layer 3 */}
          <div className={`p-4 rounded-xl border font-mono transition ${
            features?.layer3_candidate
              ? 'bg-rose-950/20 border-rose-600/60 text-rose-300'
              : 'bg-slate-900/30 border-slate-800/70 text-slate-400'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase">Layer 3: Terminal Node</span>
              <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                features?.layer3_candidate
                  ? 'bg-rose-500/20 border border-rose-500/40 text-rose-300'
                  : 'bg-slate-800 text-slate-500'
              }`}>
                {features?.layer3_candidate ? 'CANDIDATE' : 'NOT QUALIFIED'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">
              Final cash-out or automation-controlled terminal disbursement node.
            </p>
            {features?.layer3_candidate && features.layer3_reasons.length > 0 && (
              <div className="mt-3 pt-2 border-t border-rose-900/40 space-y-1.5">
                <div className="text-[10px] text-rose-300/90 font-bold uppercase tracking-wider">
                  {features.layer3_reasons.some(r => r.code === 'AUTOMATION_DEVICE_ACTIVITY')
                    ? 'Triggered Mode B: Automated Outflow Drain'
                    : features.layer3_reasons.some(r => r.code === 'TERMINAL_FLOW_SINK')
                    ? 'Triggered Mode A: Terminal Accumulation Sink'
                    : 'Triggered Mode C: Concentrated IP Sink'}
                </div>
                {features.layer3_reasons.map((r, i) => (
                  <div key={i} className="text-[10px] text-rose-200/90 bg-rose-950/30 p-1.5 rounded border border-rose-900/30 space-y-0.5">
                    <div className="flex justify-between items-center text-[9px] font-bold text-rose-400">
                      <span>{r.code}</span>
                      <span>Obs: {r.observed_value} {r.threshold !== null && r.threshold !== undefined ? `| Thr: ${r.threshold}` : ''}</span>
                    </div>
                    <div className="text-slate-300 text-[10px] leading-tight">{r.description}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Investigative Forensic Distinction: Layer 3 vs. Layer 2 */}
        {features?.layer3_candidate && !features?.layer2_candidate && ((features?.outgoing_txn_count ?? 0) > 0 || (features?.fan_out ?? 0) > 0) && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-2.5 font-mono">
            <div className="flex items-center space-x-2 text-cyan-400">
              <Info className="w-4 h-4 shrink-0" />
              <span className="text-xs font-bold uppercase tracking-wide">
                Investigative Forensic Distinction: Layer 3 vs. Layer 2 Classification
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-[#0b0f19] border border-slate-800/80 p-3 rounded-lg space-y-1.5">
                <div className="text-[11px] font-bold text-slate-300 flex items-center justify-between">
                  <span>Why NOT Layer 2 (Distributor)?</span>
                  <span className="text-slate-500 font-normal">Structural Classifier</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  This account has <span className="text-cyan-300 font-semibold">{features?.fan_out ?? detail.unique_receivers} unique receivers</span> across <span className="text-cyan-300 font-semibold">{features?.outgoing_txn_count ?? detail.outbound_transaction_count} outbound transfers</span>.
                  The structural Layer 2 Distributor classifier strictly requires high fan-out of <span className="text-amber-300 font-semibold">≥ 95 unique receivers</span> and <span className="text-amber-300 font-semibold">≥ 95 outbound transactions</span>.
                  Therefore, this account does NOT qualify as a wide-scale structural distributor.
                </p>
              </div>

              <div className="bg-[#0b0f19] border border-slate-800/80 p-3 rounded-lg space-y-1.5">
                <div className="text-[11px] font-bold text-rose-300 flex items-center justify-between">
                  <span>Why Layer 3 (Terminal / Cash-Out)?</span>
                  <span className="text-rose-400 font-normal">Automated Outflow Drain</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  All <span className="text-rose-300 font-semibold">{features?.web_emulator_txn_count ?? 0} outgoing transactions</span> were executed via <span className="text-rose-300 font-semibold">Web_Emulator</span> (automated environment) discharging <span className="text-rose-300 font-semibold">₹{(features?.outgoing_volume ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> (exceeding the ₹100,000 threshold).
                  Coupled with a <span className="text-amber-300 font-semibold">{Math.round((features?.pass_through_ratio ?? 0) * 100)}% pass-through ratio</span> in the 3–15 min window, it exhibits automated terminal extraction rather than wide distribution.
                </p>
              </div>
            </div>
            <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
              *Investigative indicator derived deterministically from transaction headers and device fingerprints. Not a legal conclusion or declaration of criminality.
            </div>
          </div>
        )}

        {/* Step 5A 3-15 Minute Pass-Through Velocity Detection Panel */}
        <div className="border border-slate-800/90 rounded-xl p-4 bg-slate-900/40 font-mono space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold uppercase text-slate-200">
                Step 5A: 3–15 Minute Pass-Through Velocity Detection
              </span>
            </div>
            <span className={`text-[10px] px-2.5 py-0.5 rounded font-bold uppercase ${
              features?.pass_through_candidate
                ? 'bg-amber-500/20 border border-amber-500/40 text-amber-400 animate-pulse'
                : 'bg-slate-800 text-slate-500 border border-slate-700'
            }`}>
              {features?.pass_through_candidate ? '⚡ PASS-THROUGH VELOCITY CANDIDATE' : 'NOT VELOCITY CANDIDATE'}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Pass-Through Ratio</span>
              <span className="text-base font-bold text-cyan-400">
                {features?.pass_through_ratio !== null && features?.pass_through_ratio !== undefined
                  ? `${(features.pass_through_ratio * 100).toFixed(1)}%`
                  : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Threshold: ≥ 90.0%</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Qualifying Outbound Txs</span>
              <span className="text-base font-bold text-slate-100">
                {features?.pass_through_outgoing_transaction_count ?? 0}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Threshold: ≥ 2 txs</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Attributed Volume</span>
              <span className="text-base font-bold text-emerald-400">
                ₹{((features?.pass_through_attributed_volume ?? 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Within 3–15 min window</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Median Window Latency</span>
              <span className="text-base font-bold text-purple-400">
                {features?.median_incoming_to_outgoing_seconds
                  ? `${Math.floor(features.median_incoming_to_outgoing_seconds / 60)}m ${Math.round(features.median_incoming_to_outgoing_seconds % 60)}s`
                  : 'N/A'}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Window: [180s, 900s]</span>
            </div>
          </div>

          {/* Velocity Events Table if any */}
          {velocity && velocity.events.length > 0 && (
            <div className="pt-2">
              <div className="text-[11px] font-semibold text-slate-400 mb-2 flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Qualifying 3–15 Minute Pass-Through Events ({velocity.events.length})</span>
              </div>
              <div className="max-h-48 overflow-y-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-[11px] font-mono">
                  <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                    <tr>
                      <th className="py-2 px-3">Inbound Tx</th>
                      <th className="py-2 px-3">Outbound Tx</th>
                      <th className="py-2 px-3">Inbound Time</th>
                      <th className="py-2 px-3">Outbound Time</th>
                      <th className="py-2 px-3">Delay</th>
                      <th className="py-2 px-3">Attributed Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50 bg-[#070b12] text-slate-300">
                    {velocity.events.map((ev, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="py-2 px-3 text-cyan-400 font-semibold">{ev.incoming_transaction_id}</td>
                        <td className="py-2 px-3 text-purple-400 font-semibold">{ev.outgoing_transaction_id}</td>
                        <td className="py-2 px-3 text-slate-400">{ev.incoming_timestamp.replace('T', ' ')}</td>
                        <td className="py-2 px-3 text-slate-400">{ev.outgoing_timestamp.replace('T', ' ')}</td>
                        <td className="py-2 px-3 text-amber-300 font-semibold">
                          {Math.floor(ev.delay_seconds / 60)}m {ev.delay_seconds % 60}s ({ev.delay_seconds}s)
                        </td>
                        <td className="py-2 px-3 text-emerald-400 font-semibold">
                          ₹{ev.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
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
                txData.items.map((tx: TransactionItem, idx: number) => (
                  <tr key={`${tx.Transaction_ID}-${idx}`} className="hover:bg-slate-800/40 transition">
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
                    <td className="py-3 px-4 text-slate-300 text-[11px]">
                      {tx.Timestamp ? tx.Timestamp.replace('T', ' ') : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-300 text-[11px]">
                      {tx.Device_Type || '—'}
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
