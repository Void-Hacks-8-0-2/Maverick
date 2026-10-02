import React, { useEffect, useState } from 'react';
import { useSearchParams, Link, useNavigate, useParams } from 'react-router-dom';
import {
  Search,
  ShieldAlert,
  Clock,
  Network,
  GitBranch,
  FileText,
  Users,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  FileCheck,
  Download,
  Loader2,
  Scale
} from 'lucide-react';
import { getVictimInvestigation, createCaseFile } from '../api/accounts';
import type {
  VictimInvestigationResponse,
  CaseFileResponse,
  GraphNode,
  GraphEdge
} from '../types';
import { NetworkGraphViewer } from '../components/NetworkGraphViewer';
import { RiskBadge } from '../components/RiskBadge';
import { RoleBadge } from '../components/RoleBadge';

const PRESET_ACCOUNTS = ['KKBK10000402', 'PYTM10001005', 'AIRP10000595', 'PUNB10000806'];

export const VictimInvestigation: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeParams = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const initialAccount = routeParams.id || searchParams.get('account') || searchParams.get('q') || 'KKBK10000402';

  const [inputAccount, setInputAccount] = useState(initialAccount);
  const [activeAccount, setActiveAccount] = useState<string | null>(initialAccount);
  const [data, setData] = useState<VictimInvestigationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'graph' | 'edges' | 'terminals' | 'transactions' | 'risk'>('graph');
  const [maxHops, setMaxHops] = useState<number>(4);
  const [horizonFilter, setHorizonFilter] = useState<number | undefined>(undefined);
  const [caseFileLoading, setCaseFileLoading] = useState<boolean>(false);
  const [caseFileError, setCaseFileError] = useState<string | null>(null);
  const [caseFileData, setCaseFileData] = useState<CaseFileResponse | null>(null);

  // Sync route param or search param changes
  useEffect(() => {
    const target = routeParams.id || searchParams.get('account') || searchParams.get('q');
    if (target && target !== activeAccount) {
      setInputAccount(target);
      setActiveAccount(target);
    }
  }, [routeParams.id, searchParams]);

  useEffect(() => {
    if (!activeAccount) return;

    setLoading(true);
    setError(null);
    setCaseFileData(null);
    setCaseFileError(null);

    getVictimInvestigation(activeAccount, maxHops, horizonFilter)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || `Failed to execute investigation for account ${activeAccount}`);
        setLoading(false);
      });
  }, [activeAccount, maxHops, horizonFilter]);

  const handleCreateCaseFile = async () => {
    if (!activeAccount || !data) return;
    setCaseFileLoading(true);
    setCaseFileError(null);
    try {
      const res = await createCaseFile({
        account_number: activeAccount,
        investigation_id: data.investigation_id,
        max_hops: maxHops,
        horizon_seconds: horizonFilter,
        include_pdf: true,
        include_json: true,
      });
      setCaseFileData(res);
    } catch (err: any) {
      setCaseFileError(err.message || 'Failed to generate forensic case file');
    } finally {
      setCaseFileLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = inputAccount.trim().toUpperCase();
    if (!cleaned) return;
    setActiveAccount(cleaned);
    setSearchParams({ account: cleaned });
    navigate(`/victim/${cleaned}`);
  };

  const handlePresetSelect = (acc: string) => {
    setInputAccount(acc);
    setActiveAccount(acc);
    setSearchParams({ account: acc });
    navigate(`/victim/${acc}`);
  };

  // Convert trace nodes and edges for NetworkGraphViewer
  const graphNodes: GraphNode[] = data?.trace?.nodes?.map((n) => {
    const isRoot = n.id === data.account_number || n.is_root;
    const isTerminal = data.terminals.some((t) => t.account_number === n.id);
    return {
      id: n.id,
      type: isRoot ? 'root' : isTerminal ? 'terminal' : 'intermediary',
      is_root: isRoot,
      is_terminal: isTerminal,
      role: isTerminal ? 'L3' : isRoot ? 'ROOT' : undefined,
      hop: n.hop,
      label: n.id,
      size: isRoot ? 22 : isTerminal ? 13 : 9,
      color: isRoot ? '#00d9ff' : isTerminal ? '#f43f5e' : '#475569',
    };
  }) || [];

  const graphEdges: GraphEdge[] = data?.trace?.edges?.map((e) => ({
    id: e.attribution_id,
    source: e.intermediary_account || e.source_account,
    target: e.destination_account,
    transaction_id: e.destination_transaction_id,
    amount: e.attributed_amount,
    attributed_amount: e.attributed_amount,
    delay_seconds: e.delay_seconds,
    payment_mode: e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO',
    color: e.edge_type === 'ROOT_SEED' ? '#00d9ff' : '#8b5cf6',
  })) || [];

  return (
    <div className="space-y-6">
      {/* Top Search & Filter Bar */}
      <div className="surface-l1 border border-white/[0.06] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-lg">
        <form onSubmit={handleSearch} className="flex-1 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputAccount}
              onChange={(e) => setInputAccount(e.target.value)}
              placeholder="Enter subject account number (e.g., KKBK10000402)..."
              className="w-full bg-[#06080d]/80 border border-white/[0.08] focus:border-cyan-500/60 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-100 placeholder-slate-400 focus:outline-none transition"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={maxHops}
              onChange={(e) => setMaxHops(Number(e.target.value))}
              className="bg-[#06080d]/80 border border-white/[0.08] rounded-lg px-2.5 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
              <option value={4}>4 Hops (Default)</option>
              <option value={5}>5 Hops</option>
            </select>

            <select
              value={horizonFilter === undefined ? '' : horizonFilter}
              onChange={(e) => setHorizonFilter(e.target.value ? Number(e.target.value) : undefined)}
              className="bg-[#06080d]/80 border border-white/[0.08] rounded-lg px-2.5 py-2 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Horizons</option>
              <option value={3600}>1 Hour</option>
              <option value={21600}>6 Hours</option>
              <option value={86400}>24 Hours</option>
              <option value={604800}>7 Days</option>
            </select>

            <button
              type="submit"
              disabled={loading}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-4 py-2 rounded-lg text-xs font-mono flex items-center gap-1.5 transition shrink-0 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>ANALYZING...</span>
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" />
                  <span>TRACE</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Preset Sample Account Chips */}
        <div className="flex items-center gap-1.5 border-t md:border-t-0 md:border-l border-white/[0.06] pt-2 md:pt-0 md:pl-3 text-xs font-mono shrink-0">
          <span className="text-[10px] text-slate-400">Presets:</span>
          {PRESET_ACCOUNTS.map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => handlePresetSelect(acc)}
              className={`text-[11px] font-mono px-2 py-0.5 rounded border transition ${
                activeAccount === acc
                  ? 'bg-slate-800 border-cyan-500/50 text-cyan-300 font-medium'
                  : 'bg-[#06080d]/60 border-white/[0.06] text-slate-400 hover:text-slate-200'
              }`}
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="surface-l2 rounded-xl p-8 text-center space-y-4 shadow-xl border border-white/[0.06]">
          <div className="inline-flex p-3 bg-cyan-950/40 border border-cyan-500/30 rounded-full text-cyan-400 animate-pulse">
            <RefreshCw className="w-6 h-6 animate-spin" />
          </div>
          <h2 className="text-base font-semibold font-mono text-slate-100">
            Running Forensic Multi-Hop Trace on {activeAccount}...
          </h2>
          <div className="max-w-md mx-auto space-y-1.5 text-left text-xs font-mono text-slate-400 pt-2">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Vectorized DuckDB extraction &amp; counterparties...</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Evaluating L1/L2/L3 mule roles &amp; 0-100 Mule Risk Index...</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
              <span>Traversing temporal FIFO fund attribution &amp; rapid velocity...</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-6 text-slate-200 space-y-2">
          <div className="flex items-center space-x-2 text-rose-400 font-mono font-medium text-xs">
            <AlertCircle className="w-4 h-4" />
            <span>INVESTIGATION QUERY ERROR</span>
          </div>
          <p className="text-sm font-mono text-slate-300">{error}</p>
        </div>
      )}

      {/* Investigation Results */}
      {data && !loading && (
        <div className="space-y-6">
          {/* UNIFIED SUBJECT DOSSIER HEADER (The Core Demo Surface) */}
          <div className="surface-l2 rounded-xl p-5 sm:p-6 border border-white/[0.08] shadow-2xl space-y-5">
            {/* Row 1: Subject Identity & Primary Status Badges & Quick Forensic Actions */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
              <div className="flex flex-wrap items-center gap-3">
                <div>
                  <span className="text-[10px] font-mono tracking-widest text-slate-400 uppercase block">
                    INVESTIGATION SUBJECT
                  </span>
                  <div className="text-2xl sm:text-3xl font-semibold font-mono text-slate-100 tracking-tight">
                    {data.account_number}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1 lg:pt-3">
                  <RiskBadge score={data.risk.risk_index} band={data.risk.risk_band} size="md" />
                  <RoleBadge role={data.roles.primary_role_label || 'L3 CANDIDATE'} size="md" />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleCreateCaseFile}
                  disabled={caseFileLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-mono text-xs font-semibold shadow-md transition"
                >
                  {caseFileLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Generating...</span>
                    </>
                  ) : (
                    <>
                      <FileCheck className="w-3.5 h-3.5" />
                      <span>Create Evidence Package</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => navigate(`/timeline?account_id=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.08] text-slate-200 font-mono text-xs transition"
                >
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Timeline</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate(`/transactions?account=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.08] text-slate-200 font-mono text-xs transition"
                >
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  <span>Transactions</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate(`/legal-freeze?account_id=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.08] text-slate-200 font-mono text-xs transition"
                >
                  <Scale className="w-3.5 h-3.5 text-slate-400" />
                  <span>Draft Order</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate(`/account/${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-[#06080d]/80 hover:bg-slate-800 border border-white/[0.08] text-slate-200 font-mono text-xs transition"
                >
                  <span>Profile</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Row 2: Financial Metrics & Forensic Telemetry Strip (No disconnected cards) */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">ROOT INFLOW</span>
                <span className="text-base sm:text-lg font-semibold text-emerald-400 tabular-nums">
                  ₹{data.account_summary.observed_incoming_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-400 block">Total observed credits</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">ROOT OUTFLOW</span>
                <span className="text-base sm:text-lg font-semibold text-rose-400 tabular-nums">
                  ₹{data.account_summary.observed_outgoing_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-400 block">Root seed outflow</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">OBSERVED NET DELTA</span>
                <span className="text-base sm:text-lg font-semibold text-cyan-300 tabular-nums">
                  {data.account_summary.observed_net_flow_delta >= 0 ? '+' : ''}
                  ₹{data.account_summary.observed_net_flow_delta.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-400 block">Inflow minus outflow</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">DOWNSTREAM ATTRIBUTION</span>
                <span className="text-base sm:text-lg font-semibold text-slate-100 tabular-nums">
                  ₹{data.trace.total_attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-slate-400 block">Cumulative downstream</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">PASS-THROUGH VELOCITY</span>
                <span className="text-base sm:text-lg font-semibold text-amber-300 tabular-nums">
                  {(data.velocity.pass_through_ratio * 100).toFixed(0)}%
                </span>
                <span className="text-[10px] text-slate-400 block">{data.velocity.qualifying_event_count} paired (3-15m)</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-400 uppercase block tracking-wider">NETWORK DEPTH</span>
                <span className="text-base sm:text-lg font-semibold text-purple-300 tabular-nums">
                  {data.trace.total_hops_found} Hops &bull; {data.terminals.length} Terminal
                </span>
                <span className="text-[10px] text-slate-400 block">{graphNodes.length} nodes &bull; {graphEdges.length} links</span>
              </div>
            </div>

            {/* Row 3: Forensic Executive Synthesis Note */}
            <div className="bg-[#06080d]/60 border border-white/[0.06] rounded-lg p-3 text-xs font-mono text-slate-300 flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
              <div className="leading-relaxed">
                <span className="text-slate-400 font-semibold uppercase text-[10px] mr-1.5">FORENSIC SYNTHESIS:</span>
                {data.evidence_summary.narrative}
              </div>
            </div>
          </div>

          {/* Case File Generation Error */}
          {caseFileError && (
            <div className="surface-l2 p-3.5 rounded-lg border border-rose-500/30 bg-rose-500/5 text-rose-300 text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{caseFileError}</span>
            </div>
          )}

          {/* Generated Case File Dossier (If Active) */}
          {caseFileData && (
            <div className="surface-l3 rounded-xl p-5 border border-cyan-500/40 shadow-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-900 border border-cyan-500/30 rounded text-cyan-400">
                    <FileCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-slate-200">CASE FILE GENERATED:</span>
                      <span className="text-xs font-mono font-semibold text-cyan-300 bg-[#06080d] px-2 py-0.5 rounded border border-white/[0.06]">
                        {caseFileData.metadata.case_file_id}
                      </span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                      Created: {new Date(caseFileData.metadata.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {caseFileData.metadata.pdf_download_url && (
                    <a
                      href={caseFileData.metadata.pdf_download_url}
                      download
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-mono text-xs font-semibold shadow transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </a>
                  )}
                  {caseFileData.metadata.json_download_url && (
                    <a
                      href={caseFileData.metadata.json_download_url}
                      download
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-white/[0.08] text-slate-200 font-mono text-xs transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Evidence JSON</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Hashes Strip */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono bg-[#06080d]/80 p-3 rounded border border-white/[0.06]">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase block">Snapshot SHA-256</span>
                  <span className="font-mono text-emerald-400 break-all text-[11px]">
                    {caseFileData.metadata.evidence_snapshot_sha256}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase block">PDF SHA-256</span>
                  <span className="font-mono text-cyan-300 break-all text-[11px]">
                    {caseFileData.metadata.pdf_sha256 || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase block">Dataset SHA-256</span>
                  <span className="font-mono text-slate-400 break-all text-[11px]">
                    {caseFileData.metadata.dataset_sha256}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Forensic Workspace Tabs & Dominant Graph Canvas */}
          <div className="surface-l2 rounded-xl overflow-hidden border border-white/[0.06] shadow-xl">
            {/* Tab Controls */}
            <div className="flex flex-wrap border-b border-white/[0.06] bg-[#070a12]/80 px-4 pt-2.5 gap-1 text-xs font-mono">
              <button
                type="button"
                onClick={() => setActiveTab('graph')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'graph'
                    ? 'border-cyan-400 text-cyan-300 font-medium bg-[#0b0f19]/60 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Network className="w-3.5 h-3.5" />
                <span>Money-Flow Vector Graph ({graphNodes.length} nodes)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('edges')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'edges'
                    ? 'border-cyan-400 text-cyan-300 font-medium bg-[#0b0f19]/60 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Attribution Links ({data.trace.edges.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('terminals')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'terminals'
                    ? 'border-cyan-400 text-cyan-300 font-medium bg-[#0b0f19]/60 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Terminal Destinations ({data.terminals.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('transactions')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'transactions'
                    ? 'border-cyan-400 text-cyan-300 font-medium bg-[#0b0f19]/60 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Subject Transactions ({data.victim_transactions.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('risk')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'risk'
                    ? 'border-cyan-400 text-cyan-300 font-medium bg-[#0b0f19]/60 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Risk Breakdown &amp; Velocity</span>
              </button>
            </div>

            <div className="p-4 sm:p-5">
              {/* TAB 1: Money-Flow Vector Graph (Dominant Visual Workspace) */}
              {activeTab === 'graph' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block" />
                        <span>Root Subject</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-purple-400 inline-block" />
                        <span>Distributor Mule</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
                        <span>Terminal Sink</span>
                      </span>
                    </div>
                    <span className="hidden sm:inline">Click any node to spotlight path &bull; Use HUD to filter</span>
                  </div>

                  <div className="rounded-lg overflow-hidden border border-white/[0.06]">
                    {graphNodes.length > 0 ? (
                      <NetworkGraphViewer
                        nodes={graphNodes}
                        edges={graphEdges}
                        rootAccountId={data.account_number}
                        truncated={data.trace.truncated}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-[500px] text-slate-400 font-mono text-xs">
                        No downstream money-flow attribution detected for this account.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: Attribution Edge Evidence */}
              {activeTab === 'edges' && (
                <div className="space-y-3">
                  <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                    <span>Deterministic FIFO attribution paths linking source funds to downstream outflows</span>
                    <span>Total Links: {data.trace.edges.length}</span>
                  </div>

                  <div className="overflow-x-auto border border-white/[0.06] rounded-lg">
                    <table className="w-full text-left text-xs font-mono text-slate-300">
                      <thead className="bg-[#070a12] text-slate-400 border-b border-white/[0.06] text-[10px] uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Hop</th>
                          <th className="py-2.5 px-3">Edge Type</th>
                          <th className="py-2.5 px-3">Source Account</th>
                          <th className="py-2.5 px-3">Destination Account</th>
                          <th className="py-2.5 px-3 text-right">Attributed (INR)</th>
                          <th className="py-2.5 px-3 text-right">Delay</th>
                          <th className="py-2.5 px-3">Source Tx ID</th>
                          <th className="py-2.5 px-3">Destination Tx ID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {data.trace.edges.map((e) => (
                          <tr key={e.attribution_id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="py-2 px-3 text-cyan-400 font-medium">Hop {e.hop_number}</td>
                            <td className="py-2 px-3">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                                  e.edge_type === 'ROOT_SEED'
                                    ? 'bg-cyan-950/40 text-cyan-300 border border-cyan-500/30'
                                    : 'bg-purple-950/40 text-purple-300 border border-purple-500/30'
                                }`}
                              >
                                {e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO'}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <Link
                                to={`/account/${e.source_account}`}
                                className="text-cyan-300 hover:underline flex items-center gap-1"
                              >
                                <span>{e.source_account}</span>
                              </Link>
                            </td>
                            <td className="py-2 px-3">
                              <Link
                                to={`/account/${e.destination_account}`}
                                className="text-cyan-300 hover:underline flex items-center gap-1"
                              >
                                <span>{e.destination_account}</span>
                              </Link>
                            </td>
                            <td className="py-2 px-3 text-right font-medium text-emerald-400 tabular-nums">
                              ₹{e.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-2 px-3 text-right text-slate-400 tabular-nums">
                              {e.delay_seconds !== null ? `${e.delay_seconds}s` : '0s'}
                            </td>
                            <td className="py-2 px-3 text-slate-400">{e.source_transaction_id}</td>
                            <td className="py-2 px-3 text-slate-400">{e.destination_transaction_id}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: Terminal Accounts */}
              {activeTab === 'terminals' && (
                <div className="space-y-4">
                  <div className="text-[11px] font-mono text-slate-400">
                    Accounts that received attributed funds but had no forward attribution in this trace (potential cash-out sinks).
                  </div>

                  {data.terminals.length === 0 ? (
                    <div className="text-center py-8 text-slate-400 font-mono text-xs">
                      No terminal recipient accounts detected.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {data.terminals.map((t) => (
                        <div
                          key={t.account_number}
                          className="bg-[#06080d]/60 border border-white/[0.06] rounded-lg p-4 space-y-2 hover:border-white/[0.12] transition"
                        >
                          <div className="flex items-center justify-between">
                            <Link
                              to={`/account/${t.account_number}`}
                              className="text-xs font-mono font-semibold text-cyan-300 hover:underline"
                            >
                              {t.account_number}
                            </Link>
                            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-white/[0.06] text-slate-400">
                              Hop {t.hop}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-400 text-[11px]">Attributed Inflow:</span>
                            <span className="font-semibold text-emerald-400 tabular-nums">
                              ₹{t.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-400 text-[11px]">Role:</span>
                            <span className="text-purple-300 font-medium">{t.primary_role}</span>
                          </div>

                          {t.risk_index !== null && (
                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="text-slate-400 text-[11px]">Mule Risk:</span>
                              <span className="text-rose-400 font-semibold">
                                {t.risk_index.toFixed(1)} / 100 ({t.risk_band})
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Subject Transactions */}
              {activeTab === 'transactions' && (
                <div className="space-y-3">
                  <div className="text-[11px] font-mono text-slate-400">
                    Chronological transactions involving subject {data.account_number}.
                  </div>

                  <div className="overflow-x-auto border border-white/[0.06] rounded-lg">
                    <table className="w-full text-left text-xs font-mono text-slate-300 whitespace-nowrap">
                      <thead className="bg-[#070a12] text-slate-400 border-b border-white/[0.06] text-[10px] uppercase">
                        <tr>
                          <th className="py-2.5 px-3">Transaction ID</th>
                          <th className="py-2.5 px-3">Direction</th>
                          <th className="py-2.5 px-3 text-right">Amount (INR)</th>
                          <th className="py-2.5 px-3">Timestamp</th>
                          <th className="py-2.5 px-3">Sender</th>
                          <th className="py-2.5 px-3">Receiver</th>
                          <th className="py-2.5 px-3">Mode</th>
                          <th className="py-2.5 px-3">IP Address</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {data.victim_transactions.map((tx) => (
                          <tr key={tx.row_id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="py-2 px-3 font-medium text-slate-200">{tx.transaction_id}</td>
                            <td className="py-2 px-3">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                                  tx.direction === 'INCOMING'
                                    ? 'bg-emerald-950/30 text-emerald-400 border border-emerald-500/30'
                                    : 'bg-rose-950/30 text-rose-400 border border-rose-500/30'
                                }`}
                              >
                                {tx.direction}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-right font-medium text-slate-100 tabular-nums">
                              ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-2 px-3 text-slate-400 tabular-nums">{tx.timestamp.replace('T', ' ')}</td>
                            <td className="py-2 px-3 text-slate-300">{tx.sender_account}</td>
                            <td className="py-2 px-3 text-slate-300">{tx.receiver_account}</td>
                            <td className="py-2 px-3 text-slate-400">{tx.payment_mode}</td>
                            <td className="py-2 px-3 text-slate-400">{tx.ip_address}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 5: Risk & Velocity Diagnostics */}
              {activeTab === 'risk' && (
                <div className="space-y-6">
                  {/* Step 5B Risk Family Breakdown */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
                      Step 5B Risk Family Contribution ({data.risk.risk_index.toFixed(1)} / 100)
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                      {Object.entries(data.risk.risk_family_scores || {}).map(([family, score]) => {
                        const numericScore = typeof score === 'number' ? score : Number(score) || 0;
                        return (
                          <div key={family} className="bg-[#06080d]/60 p-3 rounded-lg border border-white/[0.06] space-y-1.5">
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="capitalize">{family.toLowerCase().replace('_', ' ')}</span>
                              <span className="font-semibold text-cyan-300 tabular-nums">+{numericScore.toFixed(1)} pts</span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                              <div
                                className="bg-cyan-400 h-1 rounded-full"
                                style={{ width: `${Math.min(100, numericScore * 4)}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Step 5A Velocity Events */}
                  <div className="space-y-3 pt-4 border-t border-white/[0.06]">
                    <h3 className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
                      Step 5A Rapid Pass-Through Paired Events ({data.velocity.events.length} qualifying)
                    </h3>
                    {data.velocity.events.length === 0 ? (
                      <div className="text-xs font-mono text-slate-400 py-2">
                        No paired 3-15 minute pass-through events detected for this account.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {data.velocity.events.map((ev, i) => (
                          <div
                            key={i}
                            className="bg-[#06080d]/60 p-3 rounded-lg border border-white/[0.06] text-xs font-mono flex items-center justify-between"
                          >
                            <div className="space-y-0.5">
                              <span className="text-slate-200 font-medium">{ev.incoming_tx_id} &rarr; {ev.outgoing_tx_id}</span>
                              <span className="text-[10px] text-slate-400 block">Transit Time: {ev.delay_str} ({ev.elapsed_seconds}s)</span>
                            </div>
                            <div className="text-right">
                              <span className="font-semibold text-purple-300 tabular-nums">₹{ev.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                              <span className="text-[9px] text-emerald-400 block font-medium">QUALIFYING PASS-THROUGH</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
