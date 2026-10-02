import React, { useEffect, useState, useMemo } from 'react';
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
import { getVictimInvestigation, createCaseFile, getCachedVictimInvestigation } from '../api/accounts';
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

  const initialAccount = (routeParams.id || searchParams.get('account') || searchParams.get('q') || 'KKBK10000402').trim().toUpperCase();

  const [inputAccount, setInputAccount] = useState(initialAccount);
  const [activeAccount, setActiveAccount] = useState<string>(initialAccount);
  const [maxHops, setMaxHops] = useState<number>(4);
  const [horizonFilter, setHorizonFilter] = useState<number | undefined>(undefined);

  const initialCached = getCachedVictimInvestigation(initialAccount, 4, undefined);
  const [data, setData] = useState<VictimInvestigationResponse | null>(() => initialCached || null);
  const [loading, setLoading] = useState<boolean>(() => !initialCached);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'graph' | 'edges' | 'terminals' | 'transactions' | 'risk'>('graph');
  const [caseFileLoading, setCaseFileLoading] = useState<boolean>(false);
  const [caseFileError, setCaseFileError] = useState<string | null>(null);
  const [caseFileData, setCaseFileData] = useState<CaseFileResponse | null>(null);

  // Sync route param or search param changes
  useEffect(() => {
    const target = (routeParams.id || searchParams.get('account') || searchParams.get('q') || '').trim().toUpperCase();
    if (target && target !== activeAccount) {
      setInputAccount(target);
      setActiveAccount(target);
    }
  }, [routeParams.id, searchParams]);

  useEffect(() => {
    if (!activeAccount) return;
    // BUG 1 FIX: If the user switches account (or changes hops/horizon) before the
    // investigation promise resolves, cancelled=true prevents the stale response
    // from overwriting the state for the account the user most recently selected.
    let cancelled = false;

    // Check client cache first for instant synchronous render
    const cached = getCachedVictimInvestigation(activeAccount, maxHops, horizonFilter);
    if (cached) {
      setData(cached);
      setLoading(false);
      setError(null);
      setCaseFileData(null);
      setCaseFileError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setCaseFileData(null);
    setCaseFileError(null);
    setData(null);

    getVictimInvestigation(activeAccount, maxHops, horizonFilter)
      .then((res) => {
        if (cancelled) return;
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || `Failed to execute investigation for account ${activeAccount}`);
        setLoading(false);
      });

    return () => { cancelled = true; };
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

  // Convert trace nodes and edges for NetworkGraphViewer with stable referential memoization
  const graphNodes: GraphNode[] = useMemo(() => {
    if (!data?.trace?.nodes) return [];
    return data.trace.nodes.map((n) => {
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
        color: isRoot ? '#7c3aed' : isTerminal ? '#dc2626' : '#64748b',
      };
    });
  }, [data]);

  const graphEdges: GraphEdge[] = useMemo(() => {
    if (!data?.trace?.edges) return [];
    return data.trace.edges.map((e) => ({
      id: e.attribution_id,
      source: e.intermediary_account || e.source_account,
      target: e.destination_account,
      transaction_id: e.destination_transaction_id,
      amount: e.attributed_amount,
      attributed_amount: e.attributed_amount,
      delay_seconds: e.delay_seconds,
      payment_mode: e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO',
      color: e.edge_type === 'ROOT_SEED' ? '#7c3aed' : '#94a3b8',
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      {/* Top Search & Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
        <form onSubmit={handleSearch} className="flex-1 flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputAccount}
              onChange={(e) => setInputAccount(e.target.value)}
              placeholder="Enter subject account number (e.g., KKBK10000402)..."
              className="w-full bg-white border border-slate-300 focus:border-violet-600 rounded-lg pl-9 pr-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none transition"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={maxHops}
              onChange={(e) => setMaxHops(Number(e.target.value))}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-mono text-slate-800 focus:outline-none focus:border-violet-600"
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
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-2 text-xs font-mono text-slate-800 focus:outline-none focus:border-violet-600"
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
              className="bg-violet-700 hover:bg-violet-600 text-white font-semibold px-4 py-2 rounded-lg text-xs font-mono flex items-center gap-1.5 transition shrink-0 disabled:opacity-50 shadow-sm"
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
        <div className="flex items-center gap-1.5 border-t md:border-t-0 md:border-l border-slate-200 pt-2 md:pt-0 md:pl-3 text-xs font-mono shrink-0">
          <span className="text-[10px] text-slate-500">Presets:</span>
          {PRESET_ACCOUNTS.map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => handlePresetSelect(acc)}
              className={`text-[11px] font-mono px-2 py-0.5 rounded border transition ${
                activeAccount === acc
                  ? 'bg-violet-50 border-violet-300 text-violet-800 font-semibold'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {/* Error State */}
      {error && !data && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-800 space-y-2 shadow-sm">
          <div className="flex items-center space-x-2 text-rose-700 font-mono font-medium text-xs">
            <AlertCircle className="w-4 h-4" />
            <span>INVESTIGATION QUERY ERROR</span>
          </div>
          <p className="text-sm font-mono text-rose-900">{error}</p>
        </div>
      )}

      {/* Investigation Results / Progressive Layout */}
      {(!error || data) && (
        <div className="space-y-6">
          {/* UNIFIED SUBJECT DOSSIER HEADER */}
          <div className="bg-white rounded-xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-5">
            {/* Row 1: Subject Identity & Primary Status Badges & Quick Forensic Actions */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
              <div className="flex flex-wrap items-center gap-3">
                <div>
                  <span className="text-[10px] font-mono tracking-widest text-slate-500 uppercase block font-semibold">
                    INVESTIGATION SUBJECT
                  </span>
                  <div className="text-2xl sm:text-3xl font-semibold font-mono text-slate-900 tracking-tight">
                    {data?.account_number || activeAccount}
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1 lg:pt-3">
                  {data ? (
                    <>
                      <RiskBadge score={data.risk.risk_index} band={data.risk.risk_band} size="md" />
                      <RoleBadge role={data.roles.primary_role_label || 'L3 CANDIDATE'} size="md" />
                    </>
                  ) : (
                    <>
                      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-slate-100 text-slate-500 border border-slate-200 animate-pulse">
                        Evaluating Risk...
                      </span>
                      <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-mono font-medium bg-slate-100 text-slate-500 border border-slate-200 animate-pulse">
                        Classifying Role...
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleCreateCaseFile}
                  disabled={caseFileLoading || !data}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-violet-700 hover:bg-violet-600 disabled:opacity-50 text-white font-mono text-xs font-semibold shadow-sm transition"
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
                  disabled={!data}
                  onClick={() => data && navigate(`/timeline?account_id=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-mono text-xs transition disabled:opacity-50"
                >
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Timeline</span>
                </button>

                <button
                  type="button"
                  disabled={!data}
                  onClick={() => data && navigate(`/transactions?account=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-mono text-xs transition disabled:opacity-50"
                >
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  <span>Transactions</span>
                </button>

                <button
                  type="button"
                  disabled={!data}
                  onClick={() => data && navigate(`/legal-freeze?account=${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-mono text-xs transition disabled:opacity-50"
                >
                  <Scale className="w-3.5 h-3.5 text-slate-400" />
                  <span>Draft Order</span>
                </button>

                <button
                  type="button"
                  disabled={!data}
                  onClick={() => data && navigate(`/account/${data.account_number}`)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-mono text-xs transition disabled:opacity-50"
                >
                  <span>Profile</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Row 2: Financial Metrics & Forensic Telemetry Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 text-xs font-mono">
              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">ROOT INFLOW</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-emerald-700 tabular-nums">
                    ₹{data.account_summary.observed_incoming_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">Total observed credits</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">ROOT OUTFLOW</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-rose-700 tabular-nums">
                    ₹{data.account_summary.observed_outgoing_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">Root seed outflow</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">OBSERVED NET DELTA</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-slate-900 tabular-nums">
                    {data.account_summary.observed_net_flow_delta >= 0 ? '+' : ''}
                    ₹{data.account_summary.observed_net_flow_delta.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">Inflow minus outflow</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">DOWNSTREAM ATTRIBUTION</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-slate-900 tabular-nums">
                    ₹{data.trace.total_attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">Cumulative downstream</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">PASS-THROUGH VELOCITY</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-amber-700 tabular-nums">
                    {(data.velocity.pass_through_ratio * 100).toFixed(0)}%
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">{data ? `${data.velocity.qualifying_event_count} paired (3-15m)` : 'Calculating...'}</span>
              </div>

              <div className="space-y-0.5">
                <span className="text-[10px] text-slate-500 uppercase block tracking-wider">NETWORK DEPTH</span>
                {data ? (
                  <span className="text-base sm:text-lg font-semibold text-violet-700 tabular-nums">
                    {data.trace.total_hops_found} Hops &bull; {data.terminals.length} Terminal
                  </span>
                ) : (
                  <div className="h-6 w-24 bg-slate-100 rounded animate-pulse my-1" />
                )}
                <span className="text-[10px] text-slate-400 block">{data ? `${graphNodes.length} nodes • ${graphEdges.length} links` : 'Traversing graph...'}</span>
              </div>
            </div>

            {/* Row 3: Forensic Executive Synthesis Note */}
            {data ? (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs font-mono text-slate-700 flex items-start gap-2.5">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-600 shrink-0 mt-1.5" />
                <div className="leading-relaxed">
                  <span className="text-slate-600 font-semibold uppercase text-[10px] mr-1.5">FORENSIC SYNTHESIS:</span>
                  {data.evidence_summary.narrative}
                </div>
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs font-mono text-slate-500 flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-violet-600 shrink-0" />
                <span>Synthesizing multi-hop forensic narrative and cross-referencing counterparty flows...</span>
              </div>
            )}
          </div>

          {/* Case File Generation Error */}
          {caseFileError && (
            <div className="p-3.5 rounded-lg border border-rose-200 bg-rose-50 text-rose-800 text-xs font-mono flex items-center gap-2 shadow-sm">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span>{caseFileError}</span>
            </div>
          )}

          {/* Generated Case File Dossier (If Active) */}
          {caseFileData && (
            <div className="bg-white rounded-xl p-5 border border-violet-200 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-violet-50 border border-violet-200 rounded text-violet-700">
                    <FileCheck className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-slate-800">CASE FILE GENERATED:</span>
                      <span className="text-xs font-mono font-semibold text-violet-800 bg-violet-50 px-2 py-0.5 rounded border border-violet-200">
                        {caseFileData.metadata.case_file_id}
                      </span>
                    </div>
                    <div className="text-[10px] font-mono text-slate-500 mt-0.5">
                      Created: {new Date(caseFileData.metadata.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {caseFileData.metadata.pdf_download_url && (
                    <a
                      href={caseFileData.metadata.pdf_download_url}
                      download
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-violet-700 hover:bg-violet-600 text-white font-mono text-xs font-semibold shadow-sm transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </a>
                  )}
                  {caseFileData.metadata.json_download_url && (
                    <a
                      href={caseFileData.metadata.json_download_url}
                      download
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 font-mono text-xs transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Evidence JSON</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Hashes Strip */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono bg-slate-50 p-3 rounded border border-slate-200">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Snapshot SHA-256</span>
                  <span className="font-mono text-violet-700 break-all text-[11px] font-semibold">
                    {caseFileData.metadata.evidence_snapshot_sha256}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">PDF SHA-256</span>
                  <span className="font-mono text-emerald-700 break-all text-[11px] font-semibold">
                    {caseFileData.metadata.pdf_sha256 || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Dataset SHA-256</span>
                  <span className="font-mono text-slate-600 break-all text-[11px]">
                    {caseFileData.metadata.dataset_sha256}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Forensic Workspace Tabs & Dominant Graph Canvas */}
          <div className="bg-white rounded-xl overflow-hidden border border-slate-200 shadow-sm">
            {/* Tab Controls */}
            <div className="flex flex-wrap border-b border-slate-200 bg-slate-50 px-4 pt-2.5 gap-1 text-xs font-mono">
              <button
                type="button"
                onClick={() => setActiveTab('graph')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'graph'
                    ? 'border-violet-600 text-violet-700 font-semibold bg-white rounded-t'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
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
                    ? 'border-violet-600 text-violet-700 font-semibold bg-white rounded-t'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Attribution Links ({data ? data.trace.edges.length : '...'})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('terminals')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'terminals'
                    ? 'border-violet-600 text-violet-700 font-semibold bg-white rounded-t'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Terminal Destinations ({data ? data.terminals.length : '...'})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('transactions')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'transactions'
                    ? 'border-violet-600 text-violet-700 font-semibold bg-white rounded-t'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Subject Transactions ({data ? data.victim_transactions.length : '...'})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('risk')}
                className={`flex items-center gap-1.5 px-3 py-2 border-b-2 transition ${
                  activeTab === 'risk'
                    ? 'border-violet-600 text-violet-700 font-semibold bg-white rounded-t'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
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
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-violet-600 inline-block" />
                        <span>Root Subject</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
                        <span>Distributor Mule</span>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block" />
                        <span>Terminal Sink</span>
                      </span>
                    </div>
                    <span className="hidden sm:inline">Click any node to spotlight path &bull; Use HUD to filter</span>
                  </div>

                  <div className="rounded-lg overflow-hidden border border-slate-200">
                    {data ? (
                      graphNodes.length > 0 ? (
                        <NetworkGraphViewer
                          nodes={graphNodes}
                          edges={graphEdges}
                          rootAccountId={data.account_number}
                          truncated={data.trace.truncated}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-[500px] text-slate-500 font-mono text-xs">
                          No downstream money-flow attribution detected for this account.
                        </div>
                      )
                    ) : (
                      <div className="flex flex-col items-center justify-center h-[500px] bg-slate-50/50 space-y-4">
                        <div className="relative">
                          <div className="w-14 h-14 rounded-full border-2 border-violet-200 border-t-violet-600 animate-spin" />
                          <Network className="w-6 h-6 text-violet-600 absolute inset-0 m-auto" />
                        </div>
                        <div className="text-center space-y-1">
                          <p className="text-xs font-mono font-semibold text-slate-800">
                            Constructing Money-Flow Vector Graph...
                          </p>
                          <p className="text-[11px] font-mono text-slate-500 max-w-sm">
                            Traversing 4-hop FIFO paths, computing velocity deltas, and classifying terminal sinks.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: Attribution Edge Evidence */}
              {activeTab === 'edges' && (
                <div className="space-y-3">
                  <div className="text-[11px] font-mono text-slate-500 flex items-center justify-between">
                    <span>Deterministic FIFO attribution paths linking source funds to downstream outflows</span>
                    <span>Total Links: {data ? data.trace.edges.length : '...'}</span>
                  </div>

                  {data ? (
                    <div className="overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="w-full text-left text-xs font-mono text-slate-700">
                        <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase font-semibold">
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
                        <tbody className="divide-y divide-slate-100">
                          {data.trace.edges.map((e) => (
                            <tr key={e.attribution_id} className="hover:bg-slate-50 transition-colors">
                              <td className="py-2 px-3 text-violet-700 font-medium">Hop {e.hop_number}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                                    e.edge_type === 'ROOT_SEED'
                                      ? 'bg-violet-50 text-violet-700 border border-violet-200'
                                      : 'bg-slate-100 text-slate-700 border border-slate-200'
                                  }`}
                                >
                                  {e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO'}
                                </span>
                              </td>
                              <td className="py-2 px-3">
                                <Link
                                  to={`/account/${e.source_account}`}
                                  className="text-violet-700 hover:underline flex items-center gap-1 font-medium"
                                >
                                  <span>{e.source_account}</span>
                                </Link>
                              </td>
                              <td className="py-2 px-3">
                                <Link
                                  to={`/account/${e.destination_account}`}
                                  className="text-violet-700 hover:underline flex items-center gap-1 font-medium"
                                >
                                  <span>{e.destination_account}</span>
                                </Link>
                              </td>
                              <td className="py-2 px-3 text-right font-medium text-emerald-700 tabular-nums">
                                ₹{e.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </td>
                              <td className="py-2 px-3 text-right text-slate-500 tabular-nums">
                                {e.delay_seconds !== null ? `${e.delay_seconds}s` : '0s'}
                              </td>
                              <td className="py-2 px-3 text-slate-500">{e.source_transaction_id}</td>
                              <td className="py-2 px-3 text-slate-500">{e.destination_transaction_id}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-500 font-mono text-xs">
                      Traversing multi-hop attribution links...
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Terminal Accounts */}
              {activeTab === 'terminals' && (
                <div className="space-y-4">
                  <div className="text-[11px] font-mono text-slate-500">
                    Accounts that received attributed funds but had no forward attribution in this trace (potential cash-out sinks).
                  </div>

                  {data ? (
                    data.terminals.length === 0 ? (
                      <div className="text-center py-8 text-slate-500 font-mono text-xs">
                        No terminal recipient accounts detected.
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {data.terminals.map((t) => (
                          <div
                            key={t.account_number}
                            className="bg-white border border-slate-200 rounded-lg p-4 space-y-2 hover:border-slate-300 shadow-sm transition"
                          >
                            <div className="flex items-center justify-between">
                              <Link
                                to={`/account/${t.account_number}`}
                                className="text-xs font-mono font-semibold text-violet-700 hover:underline"
                              >
                                {t.account_number}
                              </Link>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 font-medium">
                                Hop {t.hop}
                              </span>
                            </div>

                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="text-slate-500 text-[11px]">Attributed Inflow:</span>
                              <span className="font-semibold text-emerald-700 tabular-nums">
                                ₹{t.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </span>
                            </div>

                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="text-slate-500 text-[11px]">Role:</span>
                              <span className="text-slate-800 font-medium">{t.primary_role}</span>
                            </div>

                            {t.risk_index !== null && (
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="text-slate-500 text-[11px]">Mule Risk:</span>
                                <span className="text-rose-700 font-semibold">
                                  {t.risk_index.toFixed(1)} / 100 ({t.risk_band})
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )
                  ) : (
                    <div className="p-8 text-center text-slate-500 font-mono text-xs">
                      Identifying terminal sink accounts...
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Subject Transactions */}
              {activeTab === 'transactions' && (
                <div className="space-y-3">
                  <div className="text-[11px] font-mono text-slate-500">
                    Chronological transactions involving subject {data ? data.account_number : '...'}.
                  </div>

                  {data ? (
                    <div className="overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="w-full text-left text-xs font-mono text-slate-700 whitespace-nowrap">
                        <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase font-semibold">
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
                        <tbody className="divide-y divide-slate-100">
                          {data.victim_transactions.map((tx) => (
                            <tr key={tx.row_id} className="hover:bg-slate-50 transition-colors">
                              <td className="py-2 px-3 font-medium text-slate-900">{tx.transaction_id}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${
                                    tx.direction === 'INCOMING'
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : 'bg-rose-50 text-rose-700 border border-rose-200'
                                  }`}
                                >
                                  {tx.direction}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-right font-medium text-slate-900 tabular-nums">
                                ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                              </td>
                              <td className="py-2 px-3 text-slate-500 tabular-nums">{tx.timestamp.replace('T', ' ')}</td>
                              <td className="py-2 px-3 text-slate-800">{tx.sender_account}</td>
                              <td className="py-2 px-3 text-slate-800">{tx.receiver_account}</td>
                              <td className="py-2 px-3 text-slate-600">{tx.payment_mode}</td>
                              <td className="py-2 px-3 text-slate-600">{tx.ip_address}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-8 text-center text-slate-500 font-mono text-xs">
                      Fetching subject transaction register...
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: Risk & Velocity Diagnostics */}
              {activeTab === 'risk' && (
                <div className="space-y-6">
                  {data ? (
                    <>
                      {/* Step 5B Risk Family Breakdown */}
                      <div className="space-y-3">
                        <h3 className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                          Step 5B Risk Family Contribution ({data.risk.risk_index.toFixed(1)} / 100)
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                          {Object.entries(data.risk.risk_family_scores || {}).map(([family, score]) => {
                            const numericScore = typeof score === 'number' ? score : Number(score) || 0;
                            return (
                              <div key={family} className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1.5">
                                <div className="flex items-center justify-between text-slate-800">
                                  <span className="capitalize">{family.toLowerCase().replace('_', ' ')}</span>
                                  <span className="font-semibold text-violet-700 tabular-nums">+{numericScore.toFixed(1)} pts</span>
                                </div>
                                <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className="bg-violet-600 h-1.5 rounded-full"
                                    style={{ width: `${Math.min(100, numericScore * 4)}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Step 5A Velocity Events */}
                      <div className="space-y-3 pt-4 border-t border-slate-200">
                        <h3 className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                          Step 5A Rapid Pass-Through Paired Events ({data.velocity.events.length} qualifying)
                        </h3>
                        {data.velocity.events.length === 0 ? (
                          <div className="text-xs font-mono text-slate-500 py-2">
                            No paired 3-15 minute pass-through events detected for this account.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {data.velocity.events.map((ev, i) => (
                              <div
                                key={i}
                                className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs font-mono flex items-center justify-between"
                              >
                                <div className="space-y-0.5">
                                  <span className="text-slate-900 font-medium">{ev.incoming_tx_id} &rarr; {ev.outgoing_tx_id}</span>
                                  <span className="text-[10px] text-slate-500 block">Transit Time: {ev.delay_str} ({ev.elapsed_seconds}s)</span>
                                </div>
                                <div className="text-right">
                                  <span className="font-semibold text-violet-700 tabular-nums">₹{ev.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                                  <span className="text-[9px] text-emerald-700 block font-semibold">QUALIFYING PASS-THROUGH</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="p-8 text-center text-slate-500 font-mono text-xs">
                      Computing risk families and velocity deltas...
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
