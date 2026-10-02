import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Search,
  ShieldAlert,
  Activity,
  Clock,
  AlertTriangle,
  Layers,
  Network,
  GitBranch,
  FileText,
  CheckCircle2,
  DollarSign,
  Users,
  ExternalLink,
  RefreshCw,
  AlertCircle,
  FileCheck,
  Download,
  Loader2
} from 'lucide-react';
import { getVictimInvestigation, createCaseFile } from '../api/accounts';
import type {
  VictimInvestigationResponse,
  CaseFileResponse,
  GraphNode,
  GraphEdge
} from '../types';
import { NetworkGraphViewer } from '../components/NetworkGraphViewer';

const PRESET_ACCOUNTS = ['KKBK10000402', 'PYTM10001005', 'AIRP10000595', 'PUNB10000806'];

export const VictimInvestigation: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialAccount = searchParams.get('account') || searchParams.get('q') || 'KKBK10000402';

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
  };

  const handlePresetSelect = (acc: string) => {
    setInputAccount(acc);
    setActiveAccount(acc);
    setSearchParams({ account: acc });
  };

  // Convert trace nodes and edges for NetworkGraphViewer
  const graphNodes: GraphNode[] = data?.trace?.nodes?.map((n) => {
    const isRoot = n.id === data.account_number || n.is_root;
    const isTerminal = data.terminals.some((t) => t.account_number === n.id);
    return {
      id: n.id,
      type: isRoot ? 'root' : isTerminal ? 'terminal' : 'intermediary',
      is_root: isRoot,
      hop: n.hop,
      label: n.id,
      size: isRoot ? 18 : isTerminal ? 14 : 10,
      color: isRoot ? '#10b981' : isTerminal ? '#f43f5e' : '#38bdf8',
    };
  }) || [];

  const graphEdges: GraphEdge[] = data?.trace?.edges?.map((e) => ({
    id: e.attribution_id,
    source: e.source_account,
    target: e.destination_account,
    transaction_id: e.destination_transaction_id,
    amount: e.attributed_amount,
    payment_mode: e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO',
    color: e.edge_type === 'ROOT_SEED' ? '#10b981' : '#38bdf8',
  })) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Title & Platform Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
              Operation Abhedya-Chakra &middot; Forensic Module
            </span>
            <span className="bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 text-[10px] font-mono px-2 py-0.5 rounded font-semibold">
              STEP 6: BLIND VICTIM TRACE
            </span>
          </div>
          <h1 className="text-2xl font-bold font-mono text-slate-100 tracking-wide mt-1">
            Blind Victim Investigation Workspace
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            Input an arbitrary victim account to trace multi-hop fund dissipation, correlate rapid pass-through velocity, and uncover downstream terminal mule entities.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-300 flex items-center space-x-2">
            <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
            <span>SHA-256 VERIFIED &middot; 2.0M TX</span>
          </div>
        </div>
      </div>

      {/* Prominent Search & Filter Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-lg">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-5 h-5 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputAccount}
              onChange={(e) => setInputAccount(e.target.value)}
              placeholder="Enter victim or subject account number (e.g., KKBK10000402)..."
              className="w-full bg-slate-950 border border-slate-700/80 rounded-lg pl-11 pr-4 py-2.5 text-sm font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={maxHops}
              onChange={(e) => setMaxHops(Number(e.target.value))}
              className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
              <option value={4}>4 Hops (Default)</option>
              <option value={5}>5 Hops</option>
              <option value={6}>6 Hops</option>
            </select>

            <select
              value={horizonFilter === undefined ? '' : horizonFilter}
              onChange={(e) => setHorizonFilter(e.target.value ? Number(e.target.value) : undefined)}
              className="bg-slate-950 border border-slate-700/80 rounded-lg px-3 py-2.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">Horizon: All Time</option>
              <option value={3600}>Horizon: 1 Hour</option>
              <option value={21600}>Horizon: 6 Hours</option>
              <option value={86400}>Horizon: 24 Hours</option>
              <option value={604800}>Horizon: 7 Days</option>
            </select>

            <button
              type="submit"
              disabled={loading}
              className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold px-5 py-2.5 rounded-lg text-xs font-mono flex items-center space-x-2 transition-colors disabled:opacity-50"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>ANALYZING...</span>
                </>
              ) : (
                <>
                  <Activity className="w-4 h-4" />
                  <span>INVESTIGATE</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Preset Sample Account Chips */}
        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-slate-800/80">
          <span className="text-[11px] font-mono text-slate-400">Sample Accounts:</span>
          {PRESET_ACCOUNTS.map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => handlePresetSelect(acc)}
              className={`text-[11px] font-mono px-2 py-0.5 rounded border transition-colors ${
                activeAccount === acc
                  ? 'bg-cyan-950/80 border-cyan-500/60 text-cyan-300'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-4 shadow-xl">
          <div className="inline-flex p-3 bg-cyan-950 border border-cyan-800/60 rounded-full text-cyan-400 animate-pulse">
            <Activity className="w-7 h-7" />
          </div>
          <h2 className="text-base font-bold font-mono text-slate-100">
            Running Blind Victim Investigation on {activeAccount}...
          </h2>
          <div className="max-w-md mx-auto space-y-2 text-left text-xs font-mono text-slate-400">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Validating account entity & analytical dimensions...</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Extracting raw subject transactions & counterparties...</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Evaluating L1/L2/L3 mule roles & 0-100 Mule Risk Index...</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Computing 3-15 minute pass-through velocity signals...</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Traversing 4-hop temporal FIFO fund attribution...</span>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-6 text-slate-200 space-y-3">
          <div className="flex items-center space-x-2.5 text-rose-400 font-mono font-bold">
            <AlertCircle className="w-5 h-5" />
            <span>Investigation Error</span>
          </div>
          <p className="text-sm font-mono text-slate-300">{error}</p>
          <p className="text-xs text-slate-400">
            Verify the account number exists in the 2,000,000-transaction dataset. Click on a sample account above or search from the Command Center.
          </p>
        </div>
      )}

      {/* Investigation Results */}
      {data && !loading && (
        <div className="space-y-6">
          {/* Warnings Banner if any */}
          {data.warnings && data.warnings.length > 0 && (
            <div className="space-y-2">
              {data.warnings.map((w, idx) => (
                <div
                  key={idx}
                  className="bg-amber-950/40 border border-amber-800/70 rounded-lg p-3 text-xs font-mono text-amber-300 flex items-start space-x-2.5"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}

          {/* Executive Evidence Summary Box */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-slate-950 border border-slate-800 rounded-xl p-5 shadow-md space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-slate-300">INVESTIGATION ID:</span>
                <span className="text-xs font-mono text-cyan-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800 font-bold">
                  {data.investigation_id}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 text-emerald-300 font-semibold">
                  STATUS: {data.status}
                </span>
              </div>
              <div className="flex items-center space-x-3">
                <div className="text-[11px] font-mono text-slate-400 hidden md:block">
                  Generated: {new Date(data.generated_at).toLocaleString()}
                </div>
                <button
                  type="button"
                  onClick={handleCreateCaseFile}
                  disabled={caseFileLoading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:opacity-50 text-white font-mono text-xs font-bold shadow-md transition-all cursor-pointer"
                >
                  {caseFileLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Generating Case File...</span>
                    </>
                  ) : (
                    <>
                      <FileCheck className="w-3.5 h-3.5" />
                      <span>Create Case File</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <p className="text-xs font-mono text-slate-200 leading-relaxed bg-slate-950/70 p-3 rounded-lg border border-slate-800/60">
              {data.evidence_summary.narrative}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] font-mono">
              <div className="bg-slate-950/50 p-2 rounded border border-slate-800/50">
                <span className="text-slate-400 block">Activity:</span>
                <span className="text-slate-100 font-bold">{data.evidence_summary.observed_activity}</span>
              </div>
              <div className="bg-slate-950/50 p-2 rounded border border-slate-800/50">
                <span className="text-slate-400 block">Attribution Links:</span>
                <span className="text-cyan-300 font-bold">{data.evidence_summary.temporal_attribution_summary}</span>
              </div>
              <div className="bg-slate-950/50 p-2 rounded border border-slate-800/50">
                <span className="text-slate-400 block">Risk Evaluation:</span>
                <span className="text-amber-300 font-bold">{data.evidence_summary.risk_summary}</span>
              </div>
              <div className="bg-slate-950/50 p-2 rounded border border-slate-800/50">
                <span className="text-slate-400 block">Classification:</span>
                <span className="text-purple-300 font-bold">{data.evidence_summary.role_summary}</span>
              </div>
            </div>
          </div>

          {/* Case File Error Alert */}
          {caseFileError && (
            <div className="bg-rose-950/40 border border-rose-800 rounded-lg p-3 text-xs font-mono text-rose-300 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>Failed to generate case file: {caseFileError}</span>
            </div>
          )}

          {/* Step 7: Forensic Case File Dossier Panel */}
          {caseFileData && (
            <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 border-2 border-cyan-500/60 rounded-xl p-5 shadow-2xl space-y-4 animate-in fade-in duration-300">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-cyan-950 border border-cyan-700/80 rounded-lg text-cyan-400">
                    <FileCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-bold text-slate-400">CASE FILE GENERATED:</span>
                      <span className="text-xs font-mono font-bold text-cyan-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        {caseFileData.metadata.case_file_id}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-700 text-emerald-300 font-bold">
                        SHA-256 VERIFIED
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                      Investigation Ref: {caseFileData.metadata.investigation_id} | Created: {new Date(caseFileData.metadata.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {caseFileData.metadata.pdf_download_url && (
                    <a
                      href={caseFileData.metadata.pdf_download_url}
                      download
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-bold shadow-lg transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF Case Report</span>
                    </a>
                  )}
                  {caseFileData.metadata.json_download_url && (
                    <a
                      href={caseFileData.metadata.json_download_url}
                      download
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-mono text-xs font-semibold transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Download Evidence JSON</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Hashes & Provenance Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono bg-slate-950/80 p-3.5 rounded-lg border border-slate-800/80">
                <div className="space-y-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Evidence Snapshot SHA-256</span>
                  <span className="font-mono text-emerald-400 break-all text-[11px] font-semibold">
                    {caseFileData.metadata.evidence_snapshot_sha256}
                  </span>
                </div>
                <div className="space-y-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Document (PDF) SHA-256</span>
                  <span className="font-mono text-cyan-400 break-all text-[11px] font-semibold">
                    {caseFileData.metadata.pdf_sha256 || 'N/A'}
                  </span>
                </div>
                <div className="space-y-1">
                  <span className="text-slate-400 block text-[10px] uppercase font-bold tracking-wider">Production Dataset SHA-256</span>
                  <span className="font-mono text-slate-300 break-all text-[11px]">
                    {caseFileData.metadata.dataset_sha256}
                  </span>
                </div>
              </div>

              {/* Money Conservation & Official Risk Contribution Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5">
                  <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Attribution Integrity</span>
                  <div className="flex justify-between text-slate-300">
                    <span>Root Outflow Under Investigation:</span>
                    <span className="font-bold text-rose-400">₹{caseFileData.evidence_snapshot.attribution.root_seed_outflow.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Downstream Cumulative Attribution:</span>
                    <span className="font-bold text-emerald-400">₹{caseFileData.evidence_snapshot.attribution.downstream_cumulative_attribution.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 italic pt-1 border-t border-slate-900">
                    {caseFileData.evidence_snapshot.attribution.note}
                  </div>
                </div>

                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5">
                  <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">
                    Step 5B Official Family Points ({caseFileData.evidence_snapshot.official_risk.risk_index.toFixed(1)} / 100)
                  </span>
                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    {Object.entries(caseFileData.evidence_snapshot.official_risk.family_points).map(([fam, pts]) => (
                      <div key={fam} className="flex justify-between px-2 py-0.5 bg-slate-900 rounded border border-slate-800/60">
                        <span className="text-slate-400 text-[10px] truncate">{fam}</span>
                        <span className="font-bold text-cyan-400">+{pts.toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Mandatory Disclaimer & Storage Note */}
              <div className="space-y-1.5 bg-slate-950/40 p-2.5 rounded border border-slate-900 text-[11px] font-mono text-slate-400">
                <div className="italic">{caseFileData.metadata.disclaimer}</div>
                <div className="text-slate-400 border-t border-slate-900/80 pt-1">
                  <span className="text-slate-300 font-bold">Storage Notice:</span> Case-file metadata and generated artifacts are maintained in process-local cache for the active session.
                </div>
              </div>
            </div>
          )}


          {/* Top 4 KPI Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* KPI 1: Inflow / Outflow */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                <span>Observed Inflow / Outflow</span>
                <DollarSign className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-lg font-bold font-mono text-slate-100">
                ₹{data.account_summary.observed_outgoing_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                <span>In: ₹{data.account_summary.observed_incoming_volume.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                <span className="text-cyan-400">Net Delta: ₹{data.account_summary.observed_net_flow_delta.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            {/* KPI 2: Attributed Amount & Hop Depth */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                <span>Attributed Flow / Hops</span>
                <Layers className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-lg font-bold font-mono text-emerald-400">
                ₹{data.trace.total_attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
              <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                <span>Depth: {data.trace.total_hops_found} Hops</span>
                <span>Edges: {data.trace.edges.length} Links</span>
              </div>
            </div>

            {/* KPI 3: Mule Risk Index */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                <span>Mule Risk Index</span>
                <ShieldAlert className="w-4 h-4 text-amber-400" />
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-lg font-bold font-mono text-slate-100">
                  {data.risk.risk_index.toFixed(1)} / 100
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    data.risk.risk_band === 'VERY_HIGH'
                      ? 'bg-rose-950 text-rose-300 border border-rose-700'
                      : data.risk.risk_band === 'HIGH'
                      ? 'bg-orange-950 text-orange-300 border border-orange-700'
                      : data.risk.risk_band === 'MODERATE'
                      ? 'bg-amber-950 text-amber-300 border border-amber-700'
                      : 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                  }`}
                >
                  {data.risk.risk_band}
                </span>
              </div>
              <div className="text-[11px] font-mono text-slate-400 truncate">
                Role: {data.roles.primary_role_label}
              </div>
            </div>

            {/* KPI 4: Velocity Profile */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-1">
              <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
                <span>Pass-Through Velocity</span>
                <Clock className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-lg font-bold font-mono text-purple-300">
                {(data.velocity.pass_through_ratio * 100).toFixed(1)}%
              </div>
              <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                <span>{data.velocity.qualifying_event_count} Events (3-15m)</span>
                <span>{data.terminals.length} Terminal(s)</span>
              </div>
            </div>
          </div>

          {/* Forensic Workspace Tabs */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            <div className="flex flex-wrap border-b border-slate-800 bg-slate-950/60 px-4 pt-3 gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('graph')}
                className={`flex items-center space-x-2 px-3 py-2 text-xs font-mono font-medium border-b-2 transition-colors ${
                  activeTab === 'graph'
                    ? 'border-cyan-400 text-cyan-400 bg-slate-900/80 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Network className="w-3.5 h-3.5" />
                <span>4-Hop Provenance Graph ({graphNodes.length} nodes)</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('edges')}
                className={`flex items-center space-x-2 px-3 py-2 text-xs font-mono font-medium border-b-2 transition-colors ${
                  activeTab === 'edges'
                    ? 'border-cyan-400 text-cyan-400 bg-slate-900/80 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitBranch className="w-3.5 h-3.5" />
                <span>Attribution Links ({data.trace.edges.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('terminals')}
                className={`flex items-center space-x-2 px-3 py-2 text-xs font-mono font-medium border-b-2 transition-colors ${
                  activeTab === 'terminals'
                    ? 'border-cyan-400 text-cyan-400 bg-slate-900/80 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Terminal Recipients ({data.terminals.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('transactions')}
                className={`flex items-center space-x-2 px-3 py-2 text-xs font-mono font-medium border-b-2 transition-colors ${
                  activeTab === 'transactions'
                    ? 'border-cyan-400 text-cyan-400 bg-slate-900/80 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Subject Transactions ({data.victim_transactions.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('risk')}
                className={`flex items-center space-x-2 px-3 py-2 text-xs font-mono font-medium border-b-2 transition-colors ${
                  activeTab === 'risk'
                    ? 'border-cyan-400 text-cyan-400 bg-slate-900/80 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Risk & Velocity Diagnostics</span>
              </button>
            </div>

            <div className="p-5">
              {/* TAB 1: 4-Hop Provenance Graph */}
              {activeTab === 'graph' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" />
                        <span>Victim / Root</span>
                      </span>
                      <span className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 rounded-full bg-cyan-400 inline-block" />
                        <span>Intermediary Hop</span>
                      </span>
                      <span className="flex items-center space-x-1.5">
                        <span className="w-3 h-3 rounded-full bg-rose-500 inline-block" />
                        <span>Terminal Mule Node</span>
                      </span>
                    </div>
                    <span>Click node to view full profile &middot; Scroll to zoom</span>
                  </div>

                  <div className="h-[480px] bg-slate-950 rounded-lg border border-slate-800 overflow-hidden relative">
                    {graphNodes.length > 0 ? (
                      <NetworkGraphViewer
                        nodes={graphNodes}
                        edges={graphEdges}
                        rootAccountId={data.account_number}
                        truncated={data.trace.truncated}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-slate-500 font-mono text-xs">
                        No downstream money-flow attribution detected for this account.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: Attribution Edge Evidence */}
              {activeTab === 'edges' && (
                <div className="space-y-3">
                  <div className="text-xs font-mono text-slate-400 flex items-center justify-between">
                    <span>Forensic attribution links linking source funds to downstream outflows</span>
                    <span>Total Links: {data.trace.edges.length}</span>
                  </div>

                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left text-xs font-mono text-slate-300">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="px-3 py-2">Hop</th>
                          <th className="px-3 py-2">Edge Type</th>
                          <th className="px-3 py-2">Source</th>
                          <th className="px-3 py-2">Destination</th>
                          <th className="px-3 py-2 text-right">Attributed (INR)</th>
                          <th className="px-3 py-2 text-right">Delay (s)</th>
                          <th className="px-3 py-2">Source Tx ID</th>
                          <th className="px-3 py-2">Destination Tx ID</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {data.trace.edges.map((e) => (
                          <tr key={e.attribution_id} className="hover:bg-slate-800/30">
                            <td className="px-3 py-2 font-bold text-cyan-400">Hop {e.hop_number}</td>
                            <td className="px-3 py-2">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  e.edge_type === 'ROOT_SEED'
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                                    : 'bg-cyan-950 text-cyan-300 border border-cyan-700'
                                }`}
                              >
                                {e.edge_type === 'ROOT_SEED' ? 'SEED' : 'FIFO'}
                              </span>
                            </td>
                            <td className="px-3 py-2">
                              <Link
                                to={`/account/${e.source_account}`}
                                className="text-cyan-400 hover:underline flex items-center space-x-1"
                              >
                                <span>{e.source_account}</span>
                                <ExternalLink className="w-3 h-3 opacity-60" />
                              </Link>
                            </td>
                            <td className="px-3 py-2">
                              <Link
                                to={`/account/${e.destination_account}`}
                                className="text-cyan-400 hover:underline flex items-center space-x-1"
                              >
                                <span>{e.destination_account}</span>
                                <ExternalLink className="w-3 h-3 opacity-60" />
                              </Link>
                            </td>
                            <td className="px-3 py-2 text-right font-bold text-emerald-400">
                              ₹{e.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="px-3 py-2 text-right text-slate-400">
                              {e.delay_seconds !== null ? `${e.delay_seconds}s` : '0s'}
                            </td>
                            <td className="px-3 py-2 text-slate-400">{e.source_transaction_id} (row {e.source_row_id})</td>
                            <td className="px-3 py-2 text-slate-400">{e.destination_transaction_id} (row {e.destination_row_id})</td>
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
                  <div className="text-xs font-mono text-slate-400">
                    Accounts that received attributed funds but had no further downstream attribution in this trace (potential cash-out or terminal mules).
                  </div>

                  {data.terminals.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 font-mono text-xs">
                      No terminal recipient accounts detected.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {data.terminals.map((t) => (
                        <div
                          key={t.account_number}
                          className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2.5 hover:border-slate-700 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <Link
                              to={`/account/${t.account_number}`}
                              className="text-sm font-mono font-bold text-cyan-400 hover:underline flex items-center space-x-1"
                            >
                              <span>{t.account_number}</span>
                              <ExternalLink className="w-3.5 h-3.5" />
                            </Link>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                              Hop {t.hop}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-400">Attributed Inflow:</span>
                            <span className="font-bold text-emerald-400">
                              ₹{t.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </span>
                          </div>

                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="text-slate-400">Primary Role:</span>
                            <span className="text-purple-300 font-semibold">{t.primary_role}</span>
                          </div>

                          {t.risk_index !== null && (
                            <div className="flex items-center justify-between text-xs font-mono">
                              <span className="text-slate-400">Mule Risk Index:</span>
                              <span className="text-amber-300 font-bold">
                                {t.risk_index.toFixed(1)} / 100 ({t.risk_band})
                              </span>
                            </div>
                          )}

                          {t.reason_codes && t.reason_codes.length > 0 && (
                            <div className="pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400 space-y-1">
                              <span className="block text-[10px] text-slate-500 uppercase">Triggers:</span>
                              {t.reason_codes.slice(0, 2).map((rc, i) => (
                                <div key={i} className="text-slate-300 truncate">&bull; {rc}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Subject Raw Transactions */}
              {activeTab === 'transactions' && (
                <div className="space-y-3">
                  <div className="text-xs font-mono text-slate-400">
                    Raw transactions involving {data.account_number} (most recent up to 100).
                  </div>

                  <div className="overflow-x-auto border border-slate-800 rounded-lg">
                    <table className="w-full text-left text-xs font-mono text-slate-300 whitespace-nowrap">
                      <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="px-3 py-2">Row ID</th>
                          <th className="px-3 py-2">Transaction ID</th>
                          <th className="px-3 py-2">Direction</th>
                          <th className="px-3 py-2 text-right">Amount (INR)</th>
                          <th className="px-3 py-2">Timestamp</th>
                          <th className="px-3 py-2">Sender</th>
                          <th className="px-3 py-2">Receiver</th>
                          <th className="px-3 py-2">Mode</th>
                          <th className="px-3 py-2">IP Address</th>
                          <th className="px-3 py-2">Device</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {data.victim_transactions.map((tx) => (
                          <tr key={tx.row_id} className="hover:bg-slate-800/30">
                            <td className="px-3 py-2 text-slate-500">{tx.row_id}</td>
                            <td className="px-3 py-2 font-semibold text-slate-200">{tx.transaction_id}</td>
                            <td className="px-3 py-2">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  tx.direction === 'INCOMING'
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                                    : 'bg-rose-950 text-rose-300 border border-rose-700'
                                }`}
                              >
                                {tx.direction}
                              </span>
                            </td>
                            <td className="px-3 py-2 text-right font-bold text-slate-100">
                              ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="px-3 py-2 text-slate-400">{tx.timestamp.replace('T', ' ')}</td>
                            <td className="px-3 py-2 text-slate-300">{tx.sender_account}</td>
                            <td className="px-3 py-2 text-slate-300">{tx.receiver_account}</td>
                            <td className="px-3 py-2 text-slate-400">{tx.payment_mode}</td>
                            <td className="px-3 py-2 text-slate-400">{tx.ip_address}</td>
                            <td className="px-3 py-2 text-slate-400">{tx.device_type || 'N/A'}</td>
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
                    <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                      Step 5B: 6-Family Mule Risk Breakdown ({data.risk.risk_index.toFixed(1)} / 100)
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                      {Object.entries(data.risk.risk_family_scores || {}).map(([family, score]) => {
                        const numericScore = typeof score === 'number' ? score : Number(score) || 0;
                        return (
                          <div key={family} className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5">
                            <div className="flex items-center justify-between text-slate-300">
                              <span className="capitalize">{family.toLowerCase().replace('_', ' ')}</span>
                              <span className="font-bold text-cyan-400">{numericScore.toFixed(1)} pts</span>
                            </div>
                            <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="bg-cyan-500 h-1.5 rounded-full"
                                style={{ width: `${Math.min(100, numericScore * 4)}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Step 5A Velocity Events */}
                  <div className="space-y-3 pt-4 border-t border-slate-800">
                    <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                      Step 5A: 3-15 Minute Pass-Through Paired Events ({data.velocity.events.length} listed)
                    </h3>
                    {data.velocity.events.length === 0 ? (
                      <div className="text-xs font-mono text-slate-500 py-3">
                        No paired 3-15 minute pass-through events detected for this account.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {data.velocity.events.map((ev, i) => (
                          <div
                            key={i}
                            className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono flex items-center justify-between"
                          >
                            <div className="space-y-0.5">
                              <span className="text-slate-200 font-semibold">{ev.incoming_tx_id} &rarr; {ev.outgoing_tx_id}</span>
                              <span className="text-[11px] text-slate-400 block">Delay: {ev.delay_str} ({ev.elapsed_seconds}s)</span>
                            </div>
                            <div className="text-right">
                              <span className="font-bold text-purple-300">₹{ev.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                              <span className="text-[10px] text-emerald-400 block font-semibold">QUALIFYING PASS-THROUGH</span>
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

          {/* Forensic Legal Disclaimer & Integrity Seal */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-[11px] font-mono text-slate-400 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2 text-[10px] text-slate-500">
              <span>DATASET: {data.data_provenance.dataset_name} ({data.data_provenance.dataset_rows.toLocaleString()} records)</span>
              <span>SHA-256: {data.data_provenance.dataset_sha256}</span>
              <span>POLICY: {data.data_provenance.attribution_policy} {data.data_provenance.attribution_policy_version}</span>
            </div>
            <p className="text-slate-400 leading-relaxed">
              <span className="font-bold text-slate-300">INVESTIGATIVE FORENSICS ONLY:</span> {data.disclaimer}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
