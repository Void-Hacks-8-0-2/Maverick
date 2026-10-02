import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Lock,
  Download,
  ShieldCheck,
  Search,
  BookOpen,
  Scale
} from 'lucide-react';
import { createCaseFile } from '../api/accounts';
import type { CaseFileResponse } from '../types';
import { PageHeader } from '../components/PageHeader';
import { MetricCard } from '../components/MetricCard';
import { RiskBadge } from '../components/RiskBadge';
import { RoleBadge } from '../components/RoleBadge';
import { HashDisplay } from '../components/HashDisplay';
import { LoadingState } from '../components/LoadingState';
import { EmptyState } from '../components/EmptyState';
import { ErrorState } from '../components/ErrorState';
import { ProvenanceFooter } from '../components/ProvenanceFooter';

export const CaseFileView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const accountParam = searchParams.get('account') || '';
  const [accountInput, setAccountInput] = useState(accountParam || id || 'KKBK10000402');
  const [caseFile, setCaseFile] = useState<CaseFileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOrCreateCaseFile = (acc: string) => {
    if (!acc.trim()) return;
    setLoading(true);
    setError(null);

    createCaseFile({
      account_number: acc.trim().toUpperCase(),
      max_hops: 4,
      include_pdf: true,
      include_json: true
    })
      .then((res) => {
        setCaseFile(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to generate forensic case file');
        setLoading(false);
      });
  };

  useEffect(() => {
    if (accountParam) {
      setAccountInput(accountParam);
      fetchOrCreateCaseFile(accountParam);
    } else if (id) {
      setAccountInput(id);
      fetchOrCreateCaseFile(id);
    } else {
      fetchOrCreateCaseFile('KKBK10000402');
    }
  }, [id, accountParam]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (accountInput.trim()) {
      fetchOrCreateCaseFile(accountInput);
    }
  };

  const meta = caseFile?.metadata;
  const snapshot = caseFile?.evidence_snapshot;
  const risk = snapshot?.official_risk;
  const roles = snapshot?.mule_roles;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        category="EVIDENCE WORKSPACE"
        title="Forensic Case File & Evidence Dossier"
        description="Generates immutable, cryptographically sealed case packages containing subject account facts, behavioral indicators, multi-hop FIFO attribution, and official evidence snapshots."
        badge={
          meta ? (
            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded font-medium flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>SEALED EVIDENCE DOSSIER</span>
            </span>
          ) : undefined
        }
        actions={
          meta && (
            <div className="flex items-center gap-2">
              <a
                href={meta.pdf_download_url || `/api/case-files/${meta.case_file_id}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="bg-violet-700 hover:bg-violet-600 text-white px-3.5 py-1.5 rounded text-xs font-mono font-semibold flex items-center gap-1.5 transition shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF Report</span>
              </a>
              <a
                href={meta.json_download_url || `/api/case-files/${meta.case_file_id}/json`}
                target="_blank"
                rel="noreferrer"
                className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 px-3.5 py-1.5 rounded text-xs font-mono font-medium flex items-center gap-1.5 transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Evidence JSON</span>
              </a>
            </div>
          )
        }
      />

      {/* Account Query Bar */}
      <div className="bg-white border border-slate-200 p-3.5 rounded-xl shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={accountInput}
              onChange={(e) => setAccountInput(e.target.value)}
              placeholder="Enter subject account ID (e.g. KKBK10000402, AIRP10000595)..."
              className="w-full bg-white border border-slate-300 rounded pl-9 pr-4 py-2 text-xs sm:text-sm font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-violet-600 transition"
            />
          </div>
        </form>

        {/* Benchmark Account Quick Selectors */}
        <div className="flex flex-wrap items-center gap-2 mt-2.5 pt-2 border-t border-slate-100 text-[11px] font-mono text-slate-600">
          <span className="text-slate-500 text-[10px]">Benchmark Accounts:</span>
          {['KKBK10000402', 'AIRP10000595', 'PYTM10001005', 'PUNB10000806'].map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => {
                setAccountInput(acc);
                fetchOrCreateCaseFile(acc);
              }}
              className="bg-slate-50 hover:bg-violet-50 hover:text-violet-700 border border-slate-200 px-2 py-0.5 rounded text-slate-700 transition text-[11px]"
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <LoadingState
          message="Compiling Forensic Evidence Snapshot..."
          submessage="Aggregating 4-hop FIFO attribution, behavioral features, risk index, and computing cryptographic SHA-256 seals"
          heightClass="h-64"
        />
      ) : error ? (
        <ErrorState error={error} onRetry={() => fetchOrCreateCaseFile(accountInput)} />
      ) : caseFile && meta && snapshot ? (
        <div className="space-y-6">
          {/* Cryptographic Seals Strip */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 space-y-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-violet-700" />
                <span className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                  CRYPTOGRAPHIC INTEGRITY SEALS
                </span>
              </div>
              <div className="text-[11px] font-mono text-slate-600">
                CASE FILE ID: <span className="text-violet-700 font-semibold">{meta.case_file_id}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
                <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">Dataset SHA-256</div>
                <HashDisplay hash={meta.dataset_sha256} truncateLength={16} />
              </div>
              <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
                <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">Evidence Snapshot SHA</div>
                <HashDisplay hash={meta.evidence_snapshot_sha256} truncateLength={16} />
              </div>
              <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
                <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">Package JSON SHA</div>
                <HashDisplay hash={meta.json_sha256 || 'PENDING'} truncateLength={16} />
              </div>
              <div className="bg-slate-50 p-3 rounded border border-slate-200 space-y-1">
                <div className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">Report PDF SHA</div>
                <HashDisplay hash={meta.pdf_sha256 || 'PENDING'} truncateLength={16} />
              </div>
            </div>
            <div className="text-[10px] font-mono text-slate-500 pt-2 border-t border-slate-100 flex items-center justify-between">
              <span>Cryptographic hash verification ensures dataset and snapshot payload immutability.</span>
              <span className="text-amber-700 font-medium">SHA-256 is an integrity seal, not a complete legal chain of custody.</span>
            </div>
          </div>

          {/* Core Findings KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricCard
              label="Subject Account"
              value={meta.subject_account}
              subtitle="Investigation root entity"
              badge={<RoleBadge role={roles?.primary_role_label || 'NONE'} size="sm" />}
            />
            <MetricCard
              label="Mule Risk Index"
              value={risk?.risk_index !== undefined ? risk.risk_index.toFixed(1) : '...'}
              subtitle={risk?.risk_band ? `${risk.risk_band} RISK BAND` : 'Step 5B Engine'}
              badge={<RiskBadge score={risk?.risk_index} band={risk?.risk_band} size="sm" showLabel={false} />}
              variant="rose"
            />
            <MetricCard
              label="Observed Net Delta"
              value={`₹${snapshot.observed_facts.observed_net_flow_delta.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
              subtitle={`In: ₹${snapshot.observed_facts.total_observed_incoming_volume.toLocaleString(undefined, { maximumFractionDigits: 0 })} · Out: ₹${snapshot.observed_facts.total_observed_outgoing_volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              variant="default"
            />
            <MetricCard
              label="Downstream Cumulative Attribution"
              value={`₹${snapshot.attribution.downstream_cumulative_attribution.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
              subtitle={`Root Seed Outflow: ₹${snapshot.attribution.root_seed_outflow.toLocaleString(undefined, { maximumFractionDigits: 0 })} · ${snapshot.attribution.max_hops_traversed} Hops`}
              variant="emerald"
            />
          </div>

          {/* Investigation Scope & Pipeline Navigation Strip */}
          <div className="bg-white border border-slate-200 p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-700">
              <span className="text-slate-500">Forensic Pipeline:</span>
              <span className="bg-slate-50 px-2 py-0.5 rounded border border-slate-200 text-slate-700 font-medium">
                Created: {new Date(meta.created_at).toLocaleString()}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => navigate(`/victim/${meta.subject_account}`)}
                className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 px-2.5 py-1 rounded text-xs font-mono transition"
              >
                Victim Trace
              </button>
              <button
                type="button"
                onClick={() => navigate(`/graph?account=${meta.subject_account}`)}
                className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 px-2.5 py-1 rounded text-xs font-mono transition"
              >
                Graph
              </button>
              <button
                type="button"
                onClick={() => navigate(`/timeline?account_id=${meta.subject_account}`)}
                className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 px-2.5 py-1 rounded text-xs font-mono transition"
              >
                Timeline
              </button>
              <button
                type="button"
                onClick={() => navigate(`/diary?account=${meta.subject_account}&case_file_id=${meta.case_file_id}`)}
                className="bg-violet-50 hover:bg-violet-100 border border-violet-200 text-violet-800 px-2.5 py-1 rounded text-xs font-mono font-medium flex items-center gap-1 transition"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Open Case Diary</span>
              </button>
              <button
                type="button"
                onClick={() => navigate(`/legal-freeze?account=${meta.subject_account}&case_file_id=${meta.case_file_id}`)}
                className="bg-violet-50 hover:bg-violet-100 border border-violet-200 text-violet-800 px-2.5 py-1 rounded text-xs font-mono font-medium flex items-center gap-1 transition"
              >
                <Scale className="w-3.5 h-3.5" />
                <span>Draft Legal Freeze</span>
              </button>
            </div>
          </div>

          {/* Observed Facts and Risk Family Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Left: Deterministic Facts */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                <h3 className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                  Observed Subject Facts
                </h3>
                <span className="text-[9px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded font-medium">
                  VERIFIED ATOMIC EVIDENCE
                </span>
              </div>

              <div className="space-y-2 text-xs font-mono">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Total Inflow Transactions:</span>
                  <span className="text-slate-900 font-medium tabular-nums">{snapshot.observed_facts.incoming_transaction_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Total Outflow Transactions:</span>
                  <span className="text-slate-900 font-medium tabular-nums">{snapshot.observed_facts.outgoing_transaction_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Unique Counterparties:</span>
                  <span className="text-slate-900 font-medium tabular-nums">{snapshot.observed_facts.unique_counterparties}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">First Observed Timestamp:</span>
                  <span className="text-slate-800 tabular-nums">{snapshot.observed_facts.first_observed_timestamp ? new Date(snapshot.observed_facts.first_observed_timestamp).toLocaleString() : 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Last Observed Timestamp:</span>
                  <span className="text-slate-800 tabular-nums">{snapshot.observed_facts.last_observed_timestamp ? new Date(snapshot.observed_facts.last_observed_timestamp).toLocaleString() : 'N/A'}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">3–15 min Pass-Through:</span>
                  <span className="text-amber-700 font-medium">
                    {snapshot.velocity_profile.pass_through_candidate ? `Active (${(snapshot.velocity_profile.pass_through_ratio * 100).toFixed(0)}% attributed)` : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>

            {/* Right: Step 5B Risk Breakdown */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                <h3 className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                  Official Risk Family Contribution
                </h3>
                <RiskBadge score={risk?.risk_index} band={risk?.risk_band} size="sm" />
              </div>

              <div className="space-y-2.5">
                {risk?.family_points && Object.entries(risk.family_points).map(([family, points]) => (
                  <div key={family} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-600">{family}</span>
                      <span className="text-violet-700 font-semibold tabular-nums">+{Number(points)} pts</span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-violet-600 h-full rounded-full transition-all"
                        style={{ width: `${Math.min(100, (Number(points) / 25) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Terminal Accounts Summary */}
          {snapshot.terminal_accounts && snapshot.terminal_accounts.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                <h3 className="text-xs font-mono font-semibold text-slate-900 uppercase tracking-wider">
                  Identified Downstream Terminal Recipient Nodes
                </h3>
                <span className="text-xs font-mono text-rose-700 font-semibold">
                  {snapshot.terminal_accounts.length} Terminal Accounts Identified
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-50 text-slate-600 border-b border-slate-200 text-[10px] uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Terminal Account</th>
                      <th className="py-2.5 px-3">Hop Level</th>
                      <th className="py-2.5 px-3 text-right">Attributed Flow</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {snapshot.terminal_accounts.slice(0, 10).map((term) => (
                      <tr key={term.account_number} className="hover:bg-slate-50 transition-colors">
                        <td className="py-2 px-3 font-medium text-slate-900">{term.account_number}</td>
                        <td className="py-2 px-3 text-violet-700 font-medium">Hop {term.hop}</td>
                        <td className="py-2 px-3 text-right text-emerald-700 font-semibold tabular-nums">
                          ₹{term.attributed_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 px-3 text-right">
                          <button
                            type="button"
                            onClick={() => navigate(`/victim/${term.account_number}`)}
                            className="text-violet-700 hover:text-violet-900 hover:underline text-[11px] font-medium"
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Standardized Provenance Footer */}
          <ProvenanceFooter
            datasetSha256={meta.dataset_sha256}
            evidenceSnapshotSha256={meta.evidence_snapshot_sha256}
            provenanceChain="ANALYTICAL TIER -> STEP 6 INVESTIGATION -> STEP 7 CASE FILE PACKAGER"
          />
        </div>
      ) : (
        <EmptyState
          title="No Case File Generated"
          description="Enter a valid account ID above to generate and cryptographically seal an evidence case package."
        />
      )}
    </div>
  );
};
