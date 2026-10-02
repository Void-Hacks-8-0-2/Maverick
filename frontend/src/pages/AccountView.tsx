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
  Info,
  GitFork,
  Layers,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { 
  getAccountDetail, 
  getAccountFeatures, 
  getAccountVelocity, 
  getAccountRisk,
  getAccountAttribution,
  getAccountAttributionTrace
} from '../api/accounts';
import { getAccountTransactions } from '../api/transactions';
import type { 
  AccountDetail, 
  PaginatedTransactions, 
  TransactionItem, 
  AccountFeatures, 
  VelocityResponse, 
  MuleRiskScore,
  AccountAttributionResponse,
  AttributionTraceResponse
} from '../types';

export const AccountView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<AccountDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Forensic Features, Velocity & Risk Score state (Step 4, Step 5A, Step 5B)
  const [features, setFeatures] = useState<AccountFeatures | null>(null);
  const [velocity, setVelocity] = useState<VelocityResponse | null>(null);
  const [risk, setRisk] = useState<MuleRiskScore | null>(null);

  // Step 5C: Temporal FIFO Attribution & 4-Hop Trace State
  const [attribution, setAttribution] = useState<AccountAttributionResponse | null>(null);
  const [attributionTrace, setAttributionTrace] = useState<AttributionTraceResponse | null>(null);
  const [loadingAttribution, setLoadingAttribution] = useState<boolean>(true);
  const [attributionTab, setAttributionTab] = useState<'matches' | 'trace' | 'unallocated'>('matches');
  const [horizonFilter, setHorizonFilter] = useState<number | null>(null);

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

    // Fetch forensic features, velocity, and mule risk score in parallel
    getAccountFeatures(id)
      .then((feat) => setFeatures(feat))
      .catch(() => setFeatures(null));

    getAccountVelocity(id)
      .then((vel) => setVelocity(vel))
      .catch(() => setVelocity(null));

    getAccountRisk(id)
      .then((r) => setRisk(r))
      .catch(() => setRisk(null));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    setLoadingAttribution(true);

    Promise.all([
      getAccountAttribution(id, horizonFilter ?? undefined),
      getAccountAttributionTrace(id, 4, horizonFilter ?? undefined)
    ])
      .then(([attrData, traceData]) => {
        setAttribution(attrData);
        setAttributionTrace(traceData);
        setLoadingAttribution(false);
      })
      .catch(() => {
        setAttribution(null);
        setAttributionTrace(null);
        setLoadingAttribution(false);
      });
  }, [id, horizonFilter]);

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

      {/* Step 5B Explainable 0-100 Mule Risk Index */}
      {risk && (
        <div className="bg-[#0b0f19] border border-slate-800 rounded-xl p-5 space-y-5 shadow-xl font-mono">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-800/80 pb-3">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
              <div className="flex items-center space-x-2.5">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                  Mule Risk Index
                </h2>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${
                  risk.risk_band === 'VERY_HIGH'
                    ? 'bg-rose-950/40 border-rose-600/60 text-rose-400'
                    : risk.risk_band === 'HIGH'
                    ? 'bg-amber-950/40 border-amber-600/60 text-amber-400'
                    : risk.risk_band === 'MODERATE'
                    ? 'bg-cyan-950/40 border-cyan-600/60 text-cyan-400'
                    : 'bg-emerald-950/40 border-emerald-600/60 text-emerald-400'
                }`}>
                  {risk.risk_band === 'VERY_HIGH' ? 'VERY HIGH RISK INDEX'
                    : risk.risk_band === 'HIGH' ? 'HIGH RISK INDEX'
                    : risk.risk_band === 'MODERATE' ? 'MODERATE RISK INDEX'
                    : 'LOW RISK INDEX'}
                </span>
              </div>
            </div>
            <span className="text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded">
              INVESTIGATIVE CANDIDATE INDICATORS ONLY &bull; NOT LEGAL DETERMINATION
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Score & Tier Box (4 cols) */}
            <div className="lg:col-span-4 bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between space-y-4">
              <div>
                <span className="text-xs text-slate-400 uppercase tracking-wider block">Bounded Investigative Index</span>
                <div className="mt-2 flex items-baseline space-x-2">
                  <span className={`text-4xl font-extrabold ${
                    risk.risk_band === 'VERY_HIGH' ? 'text-rose-400'
                    : risk.risk_band === 'HIGH' ? 'text-amber-400'
                    : risk.risk_band === 'MODERATE' ? 'text-cyan-400'
                    : 'text-emerald-400'
                  }`}>
                    {risk.risk_index}
                  </span>
                  <span className="text-lg text-slate-500 font-bold">/ 100</span>
                </div>

                {/* Meter bar */}
                <div className="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      risk.risk_band === 'VERY_HIGH' ? 'bg-rose-500'
                      : risk.risk_band === 'HIGH' ? 'bg-amber-500'
                      : risk.risk_band === 'MODERATE' ? 'bg-cyan-500'
                      : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(Math.max(risk.risk_index, 3), 100)}%` }}
                  />
                </div>
              </div>

              <div className="text-[11px] text-slate-400 space-y-1.5 pt-2 border-t border-slate-800/80">
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>Model: <strong className="text-slate-300">{risk.risk_model_version}</strong></span>
                  <span>Provenance: <strong className="text-slate-300">{risk.risk_provenance}</strong></span>
                </div>
                <p className="text-[10px] text-slate-500 leading-normal italic">
                  Deterministic bounded aggregation across 6 independent evidence families with strict non-duplicative ceilings.
                </p>
              </div>
            </div>

            {/* Family Contribution Breakdown (8 cols) */}
            <div className="lg:col-span-8 bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 space-y-3">
              <span className="text-xs text-slate-400 uppercase tracking-wider block">
                Family Contribution Breakdown
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {/* Velocity */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Velocity (3–15 min)</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['VELOCITY'] ?? 0} <span className="text-slate-500 font-normal">/ 25</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['VELOCITY'] ?? 0) / 25) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Automation */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Automation / Device / IP</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['AUTOMATION'] ?? 0} <span className="text-slate-500 font-normal">/ 20</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['AUTOMATION'] ?? 0) / 20) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Flow Structure */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Flow Structure & Scale</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['FLOW_STRUCTURE'] ?? 0} <span className="text-slate-500 font-normal">/ 20</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['FLOW_STRUCTURE'] ?? 0) / 20) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Network Structure */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Counterparty & Network</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['NETWORK_STRUCTURE'] ?? 0} <span className="text-slate-500 font-normal">/ 15</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['NETWORK_STRUCTURE'] ?? 0) / 15) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Transaction Behavior */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Transaction Behavior</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['TRANSACTION_BEHAVIOR'] ?? 0} <span className="text-slate-500 font-normal">/ 10</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['TRANSACTION_BEHAVIOR'] ?? 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Role Support */}
                <div className="bg-[#0b0f19] border border-slate-800 p-2.5 rounded-lg space-y-1">
                  <div className="flex justify-between items-center text-[11px]">
                    <span className="text-slate-300">Role Classification Support</span>
                    <span className="font-bold text-cyan-400">
                      {risk.risk_family_scores['ROLE_SUPPORT'] ?? 0} <span className="text-slate-500 font-normal">/ 10</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${((risk.risk_family_scores['ROLE_SUPPORT'] ?? 0) / 10) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Why this score? Evidence reasons section */}
          {risk.risk_reasons && risk.risk_reasons.length > 0 && (
            <div className="bg-slate-900/30 border border-slate-800/80 rounded-xl p-4 space-y-2.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300 font-bold uppercase tracking-wider flex items-center space-x-1.5">
                  <Info className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Why this score? (Factual Evidence Reasons)</span>
                </span>
                <span className="text-[10px] text-slate-500">
                  {risk.risk_reasons.length} active evidence items
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                {risk.risk_reasons.slice(0, 6).map((reason, idx) => (
                  <div
                    key={idx}
                    className="bg-[#0b0f19] border border-slate-800/90 rounded-lg p-2.5 space-y-1"
                  >
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-bold text-cyan-300 tracking-wide">{reason.code}</span>
                      <span className="text-amber-400 font-bold bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.5 rounded">
                        +{reason.points} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-snug">
                      {reason.description}
                    </p>
                    <div className="text-[9px] text-slate-500 flex justify-between pt-0.5">
                      <span>Family: {reason.family}</span>
                      <span>Observed: {reason.observed_value}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

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

        {/* Step 5C: Temporal FIFO Attribution & 4-Hop Provenance Traversal */}
        <div className="border border-slate-800/90 rounded-xl p-4 bg-slate-900/40 font-mono space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <GitFork className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold uppercase text-slate-200">
                Step 5C: Temporal FIFO Attribution & 4-Hop Provenance Trace
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-cyan-950/60 border border-cyan-800/50 text-cyan-300">
                POLICY: {attribution?.policy_name ?? 'TEMPORAL_FIFO'}_{attribution?.policy_version ?? 'v1'}
              </span>
            </div>

            {/* Horizon Filter Selection */}
            <div className="flex items-center space-x-1.5 text-[11px]">
              <span className="text-slate-400 text-[10px] flex items-center space-x-1">
                <Clock className="w-3 h-3 text-slate-500" />
                <span>Horizon:</span>
              </span>
              {[
                { label: 'All Time', val: null },
                { label: '1h', val: 3600 },
                { label: '6h', val: 21600 },
                { label: '24h', val: 86400 },
                { label: '7d', val: 604800 },
              ].map((opt) => (
                <button
                  key={opt.label}
                  onClick={() => setHorizonFilter(opt.val)}
                  className={`px-2 py-0.5 rounded text-[10px] transition ${
                    horizonFilter === opt.val
                      ? 'bg-cyan-500 text-slate-950 font-bold'
                      : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Total Attributed Volume</span>
              <span className="text-base font-bold text-emerald-400">
                ₹{(attribution?.total_attributed_volume ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">FIFO chronologically funded</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Unallocated Outflow</span>
              <span className={`text-base font-bold ${
                (attribution?.total_unallocated_outflow ?? 0) > 0 ? 'text-amber-400' : 'text-slate-400'
              }`}>
                ₹{(attribution?.total_unallocated_outflow ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Unfunded outbound remainder</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">Attribution Edges</span>
              <span className="text-base font-bold text-cyan-400">
                {attribution?.attribution_edge_count ?? 0}
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">Inflow → Outflow links</span>
            </div>

            <div className="bg-[#0b0f19] p-3 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block uppercase">4-Hop Trace Reach</span>
              <span className="text-base font-bold text-purple-400">
                {attributionTrace?.total_hops_found ?? 0} hops / {attributionTrace?.edges.length ?? 0} edges
              </span>
              <span className="text-[10px] text-slate-500 block mt-0.5">
                {attributionTrace?.truncated ? '⚠️ Branch Capped' : 'Complete Provenance'}
              </span>
            </div>
          </div>

          {/* Sub-tab Navigation */}
          <div className="flex border-b border-slate-800 text-xs">
            <button
              onClick={() => setAttributionTab('matches')}
              className={`py-2 px-3 border-b-2 font-semibold transition flex items-center space-x-1.5 ${
                attributionTab === 'matches'
                  ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitFork className="w-3.5 h-3.5" />
              <span>FIFO Attribution Links ({attribution?.attribution_records.length ?? 0})</span>
            </button>

            <button
              onClick={() => setAttributionTab('trace')}
              className={`py-2 px-3 border-b-2 font-semibold transition flex items-center space-x-1.5 ${
                attributionTab === 'trace'
                  ? 'border-purple-400 text-purple-400 bg-purple-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>4-Hop Temporal Trace ({attributionTrace?.edges.length ?? 0})</span>
            </button>

            <button
              onClick={() => setAttributionTab('unallocated')}
              className={`py-2 px-3 border-b-2 font-semibold transition flex items-center space-x-1.5 ${
                attributionTab === 'unallocated'
                  ? 'border-amber-400 text-amber-400 bg-amber-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Unallocated Outflows ({attribution?.unallocated_records.length ?? 0})</span>
            </button>
          </div>

          {/* Tab 1: FIFO Attribution Links */}
          {attributionTab === 'matches' && (
            <div>
              {loadingAttribution ? (
                <div className="py-8 text-center text-slate-500 flex items-center justify-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                  <span>Computing chronological FIFO fund attributions...</span>
                </div>
              ) : !attribution || attribution.attribution_records.length === 0 ? (
                <div className="py-6 text-center text-slate-500 text-xs">
                  No chronological attribution matches found under current horizon.
                </div>
              ) : (
                <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
                  <table className="w-full text-left text-[11px] font-mono">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2 px-3">Inbound Source</th>
                        <th className="py-2 px-3">Outbound Dest</th>
                        <th className="py-2 px-3">Inflow Time</th>
                        <th className="py-2 px-3">Outflow Time</th>
                        <th className="py-2 px-3">Delay Delta</th>
                        <th className="py-2 px-3">Attributed Flow</th>
                        <th className="py-2 px-3">Hop</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 bg-[#070b12] text-slate-300">
                      {attribution.attribution_records.map((r, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="py-2 px-3">
                            <span className="text-cyan-400 font-semibold block">{r.source_transaction_id}</span>
                            <span className="text-[10px] text-slate-500">From: {r.source_account}</span>
                          </td>
                          <td className="py-2 px-3">
                            <span className="text-purple-400 font-semibold block">{r.destination_transaction_id}</span>
                            <span className="text-[10px] text-slate-500">To: {r.destination_account}</span>
                          </td>
                          <td className="py-2 px-3 text-slate-400">{r.source_timestamp.replace('T', ' ')}</td>
                          <td className="py-2 px-3 text-slate-400">{r.destination_timestamp.replace('T', ' ')}</td>
                          <td className="py-2 px-3 text-amber-300 font-semibold">
                            {r.delay_seconds >= 60 ? `${Math.floor(r.delay_seconds / 60)}m ${Math.round(r.delay_seconds % 60)}s` : `${Math.round(r.delay_seconds)}s`}
                          </td>
                          <td className="py-2 px-3 text-emerald-400 font-semibold">
                            ₹{r.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3">
                            <span className="bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded text-[10px] text-slate-300">
                              H{r.hop_number}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Tab 2: 4-Hop Temporal Trace */}
          {attributionTab === 'trace' && (
            <div className="space-y-3">
              {loadingAttribution ? (
                <div className="py-8 text-center text-slate-500 flex items-center justify-center space-x-2">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  <span>Traversing 4-hop temporal money-flow graph...</span>
                </div>
              ) : !attributionTrace || attributionTrace.edges.length === 0 ? (
                <div className="py-6 text-center text-slate-500 text-xs">
                  No downstream temporal money flow observed from this account.
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Truncation and Cycle Warnings */}
                  {attributionTrace.truncated && (
                    <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-700/60 text-amber-300 text-xs flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                        <span><strong>Traversal Truncated:</strong> {attributionTrace.truncation_reason} (branch limits applied)</span>
                      </div>
                      <span className="text-[10px] text-amber-400 uppercase font-bold bg-amber-900/40 px-2 py-0.5 rounded">Capped</span>
                    </div>
                  )}

                  {attributionTrace.cycles_detected && attributionTrace.cycles_detected.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-700/60 text-indigo-300 text-xs space-y-1">
                      <div className="flex items-center space-x-2 font-bold text-indigo-200">
                        <span>🔄 Account Flow Cycles Detected ({attributionTrace.cycles_detected.length}):</span>
                      </div>
                      <div className="text-[10px] text-indigo-300/90 font-mono space-y-0.5">
                        {attributionTrace.cycles_detected.map((c, i) => (
                          <div key={i}>&bull; {c} (branch traversal stopped to prevent infinite circular re-attribution)</div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Hop Level Breakdown Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                    {[1, 2, 3, 4].map((hopNum) => {
                      const hopEdges = attributionTrace.edges.filter((e) => e.hop_number === hopNum);
                      const hopTotal = hopEdges.reduce((sum, e) => sum + e.attributed_amount, 0);
                      return (
                        <div
                          key={hopNum}
                          className={`p-2.5 rounded-lg border text-xs font-mono ${
                            hopEdges.length > 0
                              ? 'bg-[#0b0f19] border-purple-800/50 text-slate-300'
                              : 'bg-slate-950/50 border-slate-900 text-slate-600'
                          }`}
                        >
                          <div className="flex justify-between items-center text-[10px] font-bold">
                            <span className={hopEdges.length > 0 ? 'text-purple-400' : 'text-slate-600'}>
                              HOP {hopNum}
                            </span>
                            <span>{hopEdges.length} edges</span>
                          </div>
                          <div className="text-sm font-bold text-slate-100 mt-1">
                            ₹{hopTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Trace Edges List */}
                  <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left text-[11px] font-mono">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                        <tr>
                          <th className="py-2 px-3">Hop / Type</th>
                          <th className="py-2 px-3">Intermediary Sender</th>
                          <th className="py-2 px-3">Next Downstream Account</th>
                          <th className="py-2 px-3">Destination Tx</th>
                          <th className="py-2 px-3">Timestamp</th>
                          <th className="py-2 px-3">Attributed Flow</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50 bg-[#070b12] text-slate-300">
                        {attributionTrace.edges.map((e, idx) => (
                          <tr key={idx} className="hover:bg-slate-800/30">
                            <td className="py-2 px-3">
                              <div className="flex items-center space-x-1.5">
                                <span className="bg-purple-950/60 border border-purple-800/60 px-1.5 py-0.5 rounded text-[10px] text-purple-300 font-bold">
                                  H{e.hop_number}
                                </span>
                                <span className={`text-[9px] px-1 py-0.5 rounded font-bold uppercase ${
                                  e.edge_type === 'ROOT_SEED'
                                    ? 'bg-amber-950/60 text-amber-300 border border-amber-800/50'
                                    : 'bg-cyan-950/60 text-cyan-300 border border-cyan-800/50'
                                }`}>
                                  {e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO'}
                                </span>
                              </div>
                            </td>
                            <td className="py-2 px-3 text-cyan-400 font-semibold">{e.intermediary_account}</td>
                            <td className="py-2 px-3 text-purple-400 font-semibold">{e.destination_account}</td>
                            <td className="py-2 px-3 text-slate-400">{e.destination_transaction_id}</td>
                            <td className="py-2 px-3 text-slate-400">{e.destination_timestamp.replace('T', ' ')}</td>
                            <td className="py-2 px-3 text-emerald-400 font-semibold">
                              ₹{e.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Unallocated Outflows */}
          {attributionTab === 'unallocated' && (
            <div>
              {!attribution || attribution.unallocated_records.length === 0 ? (
                <div className="py-6 text-center text-emerald-400/80 text-xs flex items-center justify-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>All outgoing fund transfers were fully attributed to prior inflows. Zero unallocated outflow.</span>
                </div>
              ) : (
                <div className="max-h-60 overflow-y-auto border border-slate-800 rounded-lg">
                  <table className="w-full text-left text-[11px] font-mono">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800 sticky top-0">
                      <tr>
                        <th className="py-2 px-3">Outflow Tx ID</th>
                        <th className="py-2 px-3">Receiver Account</th>
                        <th className="py-2 px-3">Timestamp</th>
                        <th className="py-2 px-3">Outflow Amount</th>
                        <th className="py-2 px-3">Attributed</th>
                        <th className="py-2 px-3">Unallocated Remainder</th>
                        <th className="py-2 px-3">Reason Code</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 bg-[#070b12] text-slate-300">
                      {attribution.unallocated_records.map((u, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="py-2 px-3 text-purple-400 font-semibold">{u.destination_transaction_id}</td>
                          <td className="py-2 px-3 text-slate-300">{u.destination_account}</td>
                          <td className="py-2 px-3 text-slate-400">{u.destination_timestamp.replace('T', ' ')}</td>
                          <td className="py-2 px-3 text-slate-200">
                            ₹{u.destination_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-emerald-400">
                            ₹{u.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3 text-amber-400 font-semibold">
                            ₹{u.unallocated_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-2 px-3">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                              u.reason === 'NO_PRIOR_INFLOW'
                                ? 'bg-slate-800 text-slate-400 border border-slate-700'
                                : u.reason === 'HORIZON_EXCEEDED'
                                ? 'bg-amber-950/60 text-amber-300 border border-amber-800/60'
                                : 'bg-rose-950/60 text-rose-300 border border-rose-800/60'
                            }`}>
                              {u.reason}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Legal / Evidence Disclaimer */}
          <div className="text-[10px] text-slate-500 pt-2 border-t border-slate-800/70 leading-relaxed">
            * INVESTIGATIVE ATTRIBUTION ONLY -- Deterministic accounting model based on chronological FIFO rules.
            Does not constitute legal proof of beneficial ownership or judicial determination of criminality.
            Unallocated amounts explicitly indicate funding from outside the observed window or account opening balance.
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
