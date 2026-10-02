import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  ShieldAlert,
  AlertCircle,
  Loader2,
  Lock,
  Download,
  Building,
  Clock,
  ShieldCheck,
  Scale,
  FileText,
  FileSpreadsheet,
  Send
} from 'lucide-react';
import { createLegalDraft, getLegalDraft } from '../api/accounts';
import type {
  LegalDocumentType,
  LegalDraftPackage,
  LegalDraftResponse
} from '../types';

const PRESET_ACCOUNTS = ['KKBK10000402', 'AIRP10000595', 'PYTM10001005', 'PUNB10000806'];

const DOC_TYPES: { id: LegalDocumentType; title: string; subtitle: string; icon: any; color: string }[] = [
  {
    id: 'ACCOUNT_FREEZE_REQUEST',
    title: 'Account Freeze / Hold Request',
    subtitle: 'Formal notice requesting temporary debit hold / lien pending forensic investigation',
    icon: ShieldAlert,
    color: 'border-rose-500/30 bg-rose-500/5 text-rose-300'
  },
  {
    id: 'RECORD_PRESERVATION_REQUEST',
    title: 'Record Preservation Request',
    subtitle: 'Notice requesting retention of digital logs, IP audit trails, and transactional records',
    icon: Clock,
    color: 'border-amber-500/30 bg-amber-500/5 text-amber-300'
  },
  {
    id: 'BANK_INFORMATION_REQUISITION',
    title: 'Bank Information Requisition',
    subtitle: 'Statutory questionnaire requesting certified KYC, account master, and device logs',
    icon: Building,
    color: 'border-cyan-500/30 bg-cyan-500/5 text-cyan-300'
  },
  {
    id: 'EVIDENCE_ANNEXURE',
    title: 'Supporting Evidence Annexure',
    subtitle: 'Comprehensive multi-page annexure containing exact mathematical metrics and trace graph',
    icon: FileSpreadsheet,
    color: 'border-purple-500/30 bg-purple-500/5 text-purple-300'
  }
];

export const LegalFreezeView: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryAccount = searchParams.get('account') || searchParams.get('q') || 'KKBK10000402';
  const queryDraftId = searchParams.get('draft_id');

  const [subjectAccount, setSubjectAccount] = useState<string>(queryAccount);
  const [selectedDocType, setSelectedDocType] = useState<LegalDocumentType>('ACCOUNT_FREEZE_REQUEST');
  const [caseFileId, setCaseFileId] = useState<string>('');
  const [caseDiaryId, setCaseDiaryId] = useState<string>('');
  const [maxHops, setMaxHops] = useState<number>(4);

  // Officer Details Inputs
  const [officerName, setOfficerName] = useState<string>('');
  const [officerDesignation, setOfficerDesignation] = useState<string>('Inspector / Investigating Officer');
  const [policeStation, setPoliceStation] = useState<string>('Cyber Crime Police Station');
  const [requestingAuthority, setRequestingAuthority] = useState<string>('State Cyber Crime Investigation Bureau');
  const [caseReference, setCaseReference] = useState<string>('');
  const [incidentReference, setIncidentReference] = useState<string>('');
  const [recipientBank, setRecipientBank] = useState<string>('');
  const [recipientBranch, setRecipientBranch] = useState<string>('Nodal Officer / Law Enforcement Liaison');
  const [preservationPeriod, setPreservationPeriod] = useState<string>('90 Days');
  const [customAction, setCustomAction] = useState<string>('');
  const [investigatorNotes, setInvestigatorNotes] = useState<string>('');

  // Execution state
  const [draftPackage, setDraftPackage] = useState<LegalDraftPackage | null>(null);
  const [generationTimeMs, setGenerationTimeMs] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'document' | 'evidence' | 'seals'>('document');

  useEffect(() => {
    if (queryDraftId) {
      loadDraftById(queryDraftId);
    }
  }, [queryDraftId]);

  const loadDraftById = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res: LegalDraftResponse = await getLegalDraft(id);
      setDraftPackage(res.draft);
      setGenerationTimeMs(res.generation_time_ms);
      setSubjectAccount(res.draft.subject_account);
      setSelectedDocType(res.draft.document_type);
    } catch (err: any) {
      setError(err?.message || 'Failed to load legal draft');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!subjectAccount.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res: LegalDraftResponse = await createLegalDraft({
        subject_account: subjectAccount.trim().toUpperCase(),
        document_type: selectedDocType,
        case_file_id: caseFileId.trim() || undefined,
        case_diary_id: caseDiaryId.trim() || undefined,
        max_hops: maxHops,
        officer_name: officerName.trim() || undefined,
        officer_designation: officerDesignation.trim() || undefined,
        police_station: policeStation.trim() || undefined,
        requesting_authority: requestingAuthority.trim() || undefined,
        case_reference: caseReference.trim() || undefined,
        incident_reference: incidentReference.trim() || undefined,
        recipient_bank: recipientBank.trim() || undefined,
        recipient_branch: recipientBranch.trim() || undefined,
        preservation_period: preservationPeriod.trim() || undefined,
        requested_action: customAction.trim() || undefined,
        investigator_notes: investigatorNotes.trim() || undefined,
      });

      setDraftPackage(res.draft);
      setGenerationTimeMs(res.generation_time_ms);
      setSearchParams({
        account: res.draft.subject_account,
        draft_id: res.draft.package_id
      });
    } catch (err: any) {
      setError(err?.message || 'Failed to generate legal draft');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6 font-sans">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-white/[0.06] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
              <Scale className="w-4 h-4 text-amber-400" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-3">
              Legal Freeze & Bank Requisitions
              <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-white/[0.04] text-slate-400 border border-white/[0.06]">
                STEP 9
              </span>
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic Draft Legal Order & Requisition Workflows Grounded in Verified Evidence
          </p>
        </div>

        {/* Action badges */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] px-2.5 py-1 bg-amber-500/10 text-amber-300 border border-amber-500/20 rounded font-mono font-semibold">
            STATUS: DRAFT ONLY
          </span>
          <span className="text-[10px] px-2.5 py-1 bg-white/[0.04] text-slate-300 border border-white/[0.06] rounded font-mono">
            REVIEW REQUIRED
          </span>
        </div>
      </div>

      {/* Critical Non-Judicial Warning Banner - Restrained Amber/Neutral */}
      <div className="p-3.5 surface-l2 border-hairline rounded-xl text-xs text-amber-300/80 flex items-start gap-3">
        <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-amber-300 font-mono tracking-wider text-xs uppercase">
            DRAFT DOCUMENT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW
          </div>
          <div className="text-slate-400 leading-relaxed text-[11px]">
            Generated documents are structured drafts compiled exclusively from verified cyber-forensic accounting and graph evidence. They do NOT constitute an issued legal order, debit freeze instruction, or judicial declaration of criminal liability. Formal execution requires manual review, endorsement, and issuance by an authorized law-enforcement officer under applicable statutory powers.
          </div>
        </div>
      </div>

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Form Setup */}
        <div className="lg:col-span-1 space-y-5">
          {/* Step 1: Target Account */}
          <div className="surface-l2 border-hairline p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                1. Target Subject Account
              </span>
              <span className="text-[10px] font-mono text-slate-500">2M Rows Locked</span>
            </div>

            <div className="space-y-2">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  value={subjectAccount}
                  onChange={(e) => setSubjectAccount(e.target.value.toUpperCase())}
                  placeholder="e.g. KKBK10000402"
                  className="w-full pl-9 pr-3 py-2 bg-[#06080d] border border-white/[0.08] rounded-lg text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Benchmark Presets */}
              <div className="flex flex-wrap items-center gap-1.5 pt-1">
                <span className="text-[10px] text-slate-500 uppercase font-semibold font-mono">Presets:</span>
                {PRESET_ACCOUNTS.map((acc) => (
                  <button
                    key={acc}
                    type="button"
                    onClick={() => setSubjectAccount(acc)}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition border ${
                      subjectAccount === acc
                        ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                        : 'bg-white/[0.02] text-slate-400 border-white/[0.06] hover:border-white/[0.12] hover:text-slate-200'
                    }`}
                  >
                    {acc}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2">
              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">Hop Depth</label>
                <select
                  value={maxHops}
                  onChange={(e) => setMaxHops(Number(e.target.value))}
                  className="w-full bg-[#06080d] border border-white/[0.08] rounded p-1.5 text-xs font-mono text-slate-200"
                >
                  <option value={1}>1 Hop</option>
                  <option value={2}>2 Hops</option>
                  <option value={3}>3 Hops</option>
                  <option value={4}>4 Hops (Default)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 font-mono block mb-1">Preservation Period</label>
                <input
                  type="text"
                  value={preservationPeriod}
                  onChange={(e) => setPreservationPeriod(e.target.value)}
                  placeholder="90 Days"
                  className="w-full bg-[#06080d] border border-white/[0.08] rounded p-1.5 text-xs text-slate-200 placeholder-slate-500 font-mono"
                />
              </div>
            </div>
          </div>

          {/* Step 2: Document Type Selection */}
          <div className="surface-l2 border-hairline p-4 rounded-xl space-y-3">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block border-b border-white/[0.06] pb-2 font-mono">
              2. Select Document Type
            </span>

            <div className="space-y-2">
              {DOC_TYPES.map((dt) => {
                const Icon = dt.icon;
                const isSelected = selectedDocType === dt.id;
                return (
                  <button
                    key={dt.id}
                    type="button"
                    onClick={() => setSelectedDocType(dt.id)}
                    className={`w-full p-2.5 rounded-lg border text-left transition flex items-start gap-2.5 ${
                      isSelected
                        ? `${dt.color} ring-1 ring-cyan-500/30`
                        : 'bg-[#06080d]/50 border-white/[0.04] hover:border-white/[0.08] text-slate-400'
                    }`}
                  >
                    <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className={`text-xs font-bold ${isSelected ? 'text-slate-100' : 'text-slate-300'}`}>
                        {dt.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5 leading-tight">{dt.subtitle}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step 3: Officer Details */}
          <div className="surface-l2 border-hairline p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between border-b border-white/[0.06] pb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                3. Officer & Authority Details
              </span>
              <span className="text-[10px] text-slate-500 italic">Optional (Auto-Placeholders)</span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Investigating Officer</label>
                  <input
                    type="text"
                    value={officerName}
                    onChange={(e) => setOfficerName(e.target.value)}
                    placeholder="[TO BE COMPLETED]"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Officer Designation</label>
                  <input
                    type="text"
                    value={officerDesignation}
                    onChange={(e) => setOfficerDesignation(e.target.value)}
                    placeholder="Inspector / Investigating Officer"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Police Station</label>
                  <input
                    type="text"
                    value={policeStation}
                    onChange={(e) => setPoliceStation(e.target.value)}
                    placeholder="Cyber Police Station"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Requesting Authority</label>
                  <input
                    type="text"
                    value={requestingAuthority}
                    onChange={(e) => setRequestingAuthority(e.target.value)}
                    placeholder="State Cyber Crime Bureau"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Case Reference / FIR</label>
                  <input
                    type="text"
                    value={caseReference}
                    onChange={(e) => setCaseReference(e.target.value)}
                    placeholder="FIR-2025-..."
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-[11px]"
                  />
                </div>

                <div>
                  <label className="text-slate-400 block mb-1">Cyber Incident Ack No.</label>
                  <input
                    type="text"
                    value={incidentReference}
                    onChange={(e) => setIncidentReference(e.target.value)}
                    placeholder="ACK-2025-..."
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Recipient Bank</label>
                  <input
                    type="text"
                    value={recipientBank}
                    onChange={(e) => setRecipientBank(e.target.value)}
                    placeholder="[RECIPIENT BANK]"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Recipient Branch / Dept</label>
                  <input
                    type="text"
                    value={recipientBranch}
                    onChange={(e) => setRecipientBranch(e.target.value)}
                    placeholder="Nodal Officer / LEA Liaison"
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Linked Case File ID (Opt)</label>
                  <input
                    type="text"
                    value={caseFileId}
                    onChange={(e) => setCaseFileId(e.target.value)}
                    placeholder="CASE-..."
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-[11px]"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Linked Case Diary ID (Opt)</label>
                  <input
                    type="text"
                    value={caseDiaryId}
                    onChange={(e) => setCaseDiaryId(e.target.value)}
                    placeholder="DIARY-..."
                    className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono text-[11px]"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Specific Requested Action (Optional)</label>
                <input
                  type="text"
                  value={customAction}
                  onChange={(e) => setCustomAction(e.target.value)}
                  placeholder="e.g. Immediate lien placement on outward clearing balance"
                  className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Operational Notes / Remarks</label>
                <textarea
                  value={investigatorNotes}
                  onChange={(e) => setInvestigatorNotes(e.target.value)}
                  placeholder="Enter operational officer observations or dispatch instructions..."
                  rows={2}
                  className="w-full p-1.5 bg-[#06080d] border border-white/[0.08] rounded text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => handleGenerate()}
              disabled={loading || !subjectAccount.trim()}
              className="w-full py-2.5 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-bold rounded-lg text-xs transition flex items-center justify-center gap-2 uppercase tracking-wider mt-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {loading ? 'Compiling Legal Draft...' : 'Generate Legal Draft Package'}
            </button>
          </div>
        </div>

        {/* Right Column: Generated Draft & Previews */}
        <div className="lg:col-span-2 space-y-4">
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-200 text-xs flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-sm">Legal Draft Generation Failed</p>
                <p className="text-slate-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {loading && !draftPackage && (
            <div className="p-16 text-center surface-l2 border-hairline rounded-xl space-y-4">
              <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mx-auto" />
              <p className="text-slate-200 font-semibold text-sm">Compiling Verified Legal Document Draft...</p>
              <p className="text-xs text-slate-500">
                Extracting atomic evidence, formatting statutory notices, and calculating cryptographic SHA-256 seals.
              </p>
            </div>
          )}

          {draftPackage && (
            <div className="space-y-4">
              {/* Package Header Card */}
              <div className="surface-l2 border-hairline p-4 rounded-xl space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-sm font-bold text-slate-100 font-mono">{draftPackage.package_id}</h2>
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        {draftPackage.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Type: <span className="text-amber-300 font-semibold">{draftPackage.document_type}</span> |
                      Subject: <span className="text-white font-mono">{draftPackage.subject_account}</span>
                    </p>
                  </div>

                  {/* Download Actions */}
                  <div className="flex items-center gap-2">
                    <a
                      href={draftPackage.download_urls.pdf}
                      download={`${draftPackage.package_id}.pdf`}
                      className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download PDF
                    </a>
                    <a
                      href={draftPackage.download_urls.json}
                      download={`${draftPackage.package_id}.json`}
                      className="px-3 py-1.5 bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/[0.08] rounded text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download JSON
                    </a>
                  </div>
                </div>

                {/* Integrity Metrics Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                  <div className="bg-[#06080d] p-2.5 rounded border border-white/[0.06]">
                    <span className="text-slate-500 block text-[10px]">Evidence Snapshot SHA:</span>
                    <span className="text-cyan-400 font-semibold truncate block" title={draftPackage.evidence_snapshot_sha256}>
                      {draftPackage.evidence_snapshot_sha256.substring(0, 14)}...
                    </span>
                  </div>

                  <div className="bg-[#06080d] p-2.5 rounded border border-white/[0.06]">
                    <span className="text-slate-500 block text-[10px]">PDF Document SHA:</span>
                    <span className="text-emerald-400 font-semibold truncate block" title={draftPackage.pdf_sha256 || 'N/A'}>
                      {draftPackage.pdf_sha256 ? `${draftPackage.pdf_sha256.substring(0, 14)}...` : 'N/A'}
                    </span>
                  </div>

                  <div className="bg-[#06080d] p-2.5 rounded border border-white/[0.06]">
                    <span className="text-slate-500 block text-[10px]">Mule Risk Index:</span>
                    <span className="text-orange-400 font-semibold block">
                      {draftPackage.evidence.risk.risk_index.toFixed(1)}/100 ({draftPackage.evidence.risk.risk_band})
                    </span>
                  </div>

                  <div className="bg-[#06080d] p-2.5 rounded border border-white/[0.06]">
                    <span className="text-slate-500 block text-[10px]">Latency:</span>
                    <span className="text-purple-400 font-semibold block">
                      {generationTimeMs !== null ? `${generationTimeMs} ms` : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Tab Navigation */}
              <div className="flex border-b border-white/[0.06]">
                <button
                  onClick={() => setActiveTab('document')}
                  className={`px-4 py-2 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
                    activeTab === 'document'
                      ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  Compiled Legal Draft ({draftPackage.document.sections.length} Sections)
                </button>

                <button
                  onClick={() => setActiveTab('evidence')}
                  className={`px-4 py-2 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
                    activeTab === 'evidence'
                      ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Verified Evidence Summary
                </button>

                <button
                  onClick={() => setActiveTab('seals')}
                  className={`px-4 py-2 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
                    activeTab === 'seals'
                      ? 'border-cyan-500 text-cyan-400 bg-cyan-500/5'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Lock className="w-3.5 h-3.5" />
                  Integrity & Provenance Seals
                </button>
              </div>

              {/* TAB 1: Compiled Document Preview */}
              {activeTab === 'document' && (
                <div className="surface-l2 border-hairline rounded-xl p-6 space-y-5 text-slate-300 font-sans">
                  {/* Document Header */}
                  <div className="text-center border-b border-white/[0.06] pb-4 space-y-1">
                    <p className="text-[10px] font-mono tracking-widest text-slate-400 uppercase font-semibold">
                      {draftPackage.document.header_notice}
                    </p>
                    <h3 className="text-sm font-bold text-slate-100 tracking-wide font-mono mt-1">
                      {draftPackage.document.title}
                    </h3>
                    <div className="inline-block mt-2 px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded text-[11px] font-mono text-amber-300 font-semibold">
                      {draftPackage.document.draft_notice}
                    </div>
                  </div>

                  {/* Document Sections */}
                  <div className="space-y-4 text-xs leading-relaxed">
                    {draftPackage.document.sections.map((sec) => (
                      <div key={sec.id} className="space-y-1.5 bg-[#06080d]/60 p-3.5 rounded-lg border border-white/[0.04]">
                        <h4 className="text-xs font-bold text-slate-200 font-mono border-b border-white/[0.06] pb-1 uppercase tracking-wide">
                          {sec.heading}
                        </h4>
                        <div className="whitespace-pre-line text-slate-300 font-mono text-[11px] pt-1">
                          {sec.content}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Signature Footer */}
                  <div className="pt-4 border-t border-white/[0.06] grid grid-cols-2 gap-4 text-xs font-mono text-slate-400">
                    <div>
                      <p>Investigating Officer Signature: __________________</p>
                      <p className="mt-1">Date: __________________</p>
                    </div>
                    <div className="text-right">
                      <p>Authorizing Supervisory Seal: __________________</p>
                      <p className="mt-1">Agency: {draftPackage.officer_details.police_station}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Verified Evidence */}
              {activeTab === 'evidence' && (
                <div className="space-y-4 text-xs font-mono">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="surface-l2 border-hairline p-3.5 rounded-lg space-y-1.5">
                      <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Subject Flow Metrics</span>
                      <div>Observed Inflow: ₹{draftPackage.evidence.subject_account.observed_inflow.toLocaleString()}</div>
                      <div>Observed Outflow: ₹{draftPackage.evidence.subject_account.observed_outflow.toLocaleString()}</div>
                      <div>Net Flow Delta: ₹{draftPackage.evidence.subject_account.observed_net_flow_delta.toLocaleString()}</div>
                      <div>Unique Counterparties: {draftPackage.evidence.subject_account.unique_counterparties}</div>
                      <div>Transactions: {draftPackage.evidence.subject_account.incoming_transaction_count + draftPackage.evidence.subject_account.outgoing_transaction_count}</div>
                    </div>

                    <div className="surface-l2 border-hairline p-3.5 rounded-lg space-y-1.5">
                      <span className="text-slate-400 font-bold block text-[11px] uppercase tracking-wider">Analytical Risk & Roles</span>
                      <div>Risk Index: {draftPackage.evidence.risk.risk_index.toFixed(1)} ({draftPackage.evidence.risk.risk_band})</div>
                      <div>Primary Role: {draftPackage.evidence.roles.primary_role_label}</div>
                      <div>Pass-Through Candidate: {String(draftPackage.evidence.velocity.pass_through_candidate)}</div>
                      <div>Root Seed Outflow: ₹{draftPackage.evidence.attribution.root_seed_outflow.toLocaleString()}</div>
                      <div>Downstream Cumulative: ₹{draftPackage.evidence.attribution.downstream_cumulative_attribution.toLocaleString()}</div>
                    </div>
                  </div>

                  {/* Transaction Schedule */}
                  <div className="surface-l2 border-hairline rounded-lg p-3 overflow-x-auto">
                    <span className="text-slate-400 font-bold block mb-2 font-mono text-[11px] uppercase tracking-wider">
                      Verified Transactions Sample ({draftPackage.evidence.transactions_sample.length} Records)
                    </span>
                    <table className="w-full text-left text-[11px]">
                      <thead className="bg-[#06080d]/80 text-slate-400 border-b border-white/[0.06]">
                        <tr>
                          <th className="py-1.5 px-2">TX ID</th>
                          <th className="py-1.5 px-2">Timestamp</th>
                          <th className="py-1.5 px-2">Sender</th>
                          <th className="py-1.5 px-2">Receiver</th>
                          <th className="py-1.5 px-2 text-right">Amount (INR)</th>
                          <th className="py-1.5 px-2">Mode</th>
                          <th className="py-1.5 px-2">Direction</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {draftPackage.evidence.transactions_sample.map((tx) => (
                          <tr key={tx.transaction_id} className="hover:bg-white/[0.02]">
                            <td className="py-1.5 px-2 text-cyan-400">{tx.transaction_id}</td>
                            <td className="py-1.5 px-2 text-slate-500">{tx.timestamp}</td>
                            <td className="py-1.5 px-2 text-slate-300">{tx.sender_account}</td>
                            <td className="py-1.5 px-2 text-slate-300">{tx.receiver_account}</td>
                            <td className="py-1.5 px-2 text-right font-bold text-slate-100">
                              ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td className="py-1.5 px-2 text-slate-400">{tx.payment_mode}</td>
                            <td className="py-1.5 px-2 text-purple-400">{tx.direction}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: Seals & Provenance */}
              {activeTab === 'seals' && (
                <div className="surface-l2 border-hairline p-5 rounded-xl space-y-4 text-xs font-mono">
                  <h4 className="text-xs font-bold text-slate-100 font-sans flex items-center gap-2">
                    <Lock className="w-4 h-4 text-cyan-400" />
                    Cryptographic Integrity Verification
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3 bg-[#06080d] rounded border border-white/[0.06] space-y-1">
                      <span className="text-slate-400 font-semibold block">Evidence Snapshot SHA-256</span>
                      <div className="text-cyan-400 break-all font-bold">{draftPackage.evidence_snapshot_sha256}</div>
                      <p className="text-[10px] text-slate-500 font-sans mt-1">
                        Computed deterministically over canonical JSON verified facts.
                      </p>
                    </div>

                    <div className="p-3 bg-[#06080d] rounded border border-white/[0.06] space-y-1">
                      <span className="text-slate-400 font-semibold block">Compiled PDF Binary SHA-256</span>
                      <div className="text-emerald-400 break-all font-bold">{draftPackage.pdf_sha256 || 'N/A'}</div>
                      <p className="text-[10px] text-slate-500 font-sans mt-1">
                        Calculated over the final binary bytes of the compiled PDF.
                      </p>
                    </div>

                    <div className="p-3 bg-[#06080d] rounded border border-white/[0.06] space-y-1">
                      <span className="text-slate-400 font-semibold block">Canonical JSON Package SHA-256</span>
                      <div className="text-purple-400 break-all font-bold">{draftPackage.json_sha256}</div>
                    </div>

                    <div className="p-3 bg-[#06080d] rounded border border-white/[0.06] space-y-1">
                      <span className="text-slate-400 font-semibold block">Production Dataset SHA-256</span>
                      <div className="text-emerald-400 break-all font-bold">{draftPackage.evidence.dataset_sha256}</div>
                      <div className="text-[11px] text-slate-400">Rows: {draftPackage.evidence.dataset_rows.toLocaleString()}</div>
                    </div>
                  </div>

                  <div className="p-3 bg-[#06080d] rounded border border-white/[0.06] text-slate-400 text-[11px]">
                    <span className="text-amber-300 font-semibold block mb-1">Process-Local Storage Note:</span>
                    {draftPackage.persistence_note}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
