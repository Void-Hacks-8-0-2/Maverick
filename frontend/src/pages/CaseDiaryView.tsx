import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  BookOpen,
  Search,
  ShieldAlert,
  Activity,
  Clock,
  GitBranch,
  AlertCircle,
  RefreshCw,
  Loader2,
  Lock,
  Sparkles,
  Info,
  Edit3,
  ShieldCheck,
  FileCheck,
  Users
} from 'lucide-react';
import {
  createCaseDiary,
  getCaseDiary,
  generateDiaryNarrative
} from '../api/accounts';
import type {
  CaseDiary,
  CaseDiaryResponse
} from '../types';

const PRESET_ACCOUNTS = ['KKBK10000402', 'AIRP10000595', 'PYTM10001005', 'PUNB10000806'];

export const CaseDiaryView: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryAccount = searchParams.get('account') || searchParams.get('q') || 'KKBK10000402';
  const queryDiaryId = searchParams.get('diary_id');

  const [inputAccount, setInputAccount] = useState(queryAccount);
  const [activeAccount, setActiveAccount] = useState<string>(queryAccount);
  const [diary, setDiary] = useState<CaseDiary | null>(null);
  const [generationTimeMs, setGenerationTimeMs] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [narrativeLoading, setNarrativeLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'chronology' | 'facts' | 'findings' | 'provenance'>('chronology');

  // Options
  const [maxHops, setMaxHops] = useState<number>(4);
  const [withNarrative, setWithNarrative] = useState<boolean>(true);
  const [forceDeterministic, setForceDeterministic] = useState<boolean>(false);
  const [investigatorNotes, setInvestigatorNotes] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [eventFilter, setEventFilter] = useState<string>('ALL');

  useEffect(() => {
    if (queryDiaryId) {
      loadDiaryById(queryDiaryId);
    } else if (activeAccount) {
      loadOrCreateDiary(activeAccount);
    }
  }, [activeAccount, queryDiaryId]);

  const loadDiaryById = async (diaryId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res: CaseDiaryResponse = await getCaseDiary(diaryId);
      setDiary(res.case_diary);
      setGenerationTimeMs(res.generation_time_ms);
      setInvestigatorNotes(res.case_diary.investigator_notes || '');
      setInputAccount(res.case_diary.subject_account);
    } catch (err: any) {
      setError(err?.message || 'Failed to load case diary');
    } finally {
      setLoading(false);
    }
  };

  const loadOrCreateDiary = async (acc: string) => {
    setLoading(true);
    setError(null);
    try {
      const res: CaseDiaryResponse = await createCaseDiary({
        account_number: acc,
        max_hops: maxHops,
        generate_narrative: withNarrative,
        investigator_notes: investigatorNotes
      });
      setDiary(res.case_diary);
      setGenerationTimeMs(res.generation_time_ms);
      setInvestigatorNotes(res.case_diary.investigator_notes || '');
      setSearchParams({ account: acc, diary_id: res.case_diary.case_diary_id });
    } catch (err: any) {
      setError(err?.message || 'Failed to generate case diary');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputAccount.trim()) return;
    const clean = inputAccount.trim().toUpperCase();
    setActiveAccount(clean);
  };

  const handleRegenerateNarrative = async () => {
    if (!diary) return;
    setNarrativeLoading(true);
    try {
      const res: CaseDiaryResponse = await generateDiaryNarrative(diary.case_diary_id, {
        force_deterministic: forceDeterministic,
        investigator_notes: investigatorNotes
      });
      setDiary(res.case_diary);
      setGenerationTimeMs(res.generation_time_ms);
    } catch (err: any) {
      setError(err?.message || 'Failed to regenerate AI narrative');
    } finally {
      setNarrativeLoading(false);
    }
  };

  // Filtered facts
  const filteredFacts = (diary?.verified_facts || []).filter(f => {
    if (categoryFilter === 'ALL') return true;
    return f.category === categoryFilter;
  });

  // Filtered chronology
  const filteredChronology = (diary?.chronology || []).filter(ev => {
    if (eventFilter === 'ALL') return true;
    return ev.event_type === eventFilter;
  });

  const getEventBadgeColor = (type: string) => {
    switch (type) {
      case 'CASE_OPENED':
        return 'bg-blue-900/40 text-blue-300 border-blue-700/60';
      case 'ROOT_TRANSACTION':
        return 'bg-amber-900/40 text-amber-300 border-amber-700/60';
      case 'ATTRIBUTION_HOP':
        return 'bg-purple-900/40 text-purple-300 border-purple-700/60';
      case 'VELOCITY_EVENT':
        return 'bg-rose-900/40 text-rose-300 border-rose-700/60';
      case 'RISK_FINDING':
        return 'bg-orange-900/40 text-orange-300 border-orange-700/60';
      case 'ROLE_FINDING':
        return 'bg-emerald-900/40 text-emerald-300 border-emerald-700/60';
      case 'TERMINAL_ACCOUNT':
        return 'bg-red-900/40 text-red-300 border-red-700/60';
      default:
        return 'bg-gray-800 text-gray-300 border-gray-700';
    }
  };

  const getCategoryBadgeColor = (cat: string) => {
    switch (cat) {
      case 'SUBJECT':
        return 'bg-blue-900/50 text-blue-300 border-blue-700';
      case 'TRANSACTION':
        return 'bg-amber-900/50 text-amber-300 border-amber-700';
      case 'RISK':
        return 'bg-orange-900/50 text-orange-300 border-orange-700';
      case 'ROLE':
        return 'bg-emerald-900/50 text-emerald-300 border-emerald-700';
      case 'VELOCITY':
        return 'bg-rose-900/50 text-rose-300 border-rose-700';
      case 'ATTRIBUTION':
        return 'bg-purple-900/50 text-purple-300 border-purple-700';
      case 'PROVENANCE':
        return 'bg-cyan-900/50 text-cyan-300 border-cyan-700';
      default:
        return 'bg-gray-800 text-gray-300 border-gray-700';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-gray-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-7 h-7 text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
              Case Diary & Narrative
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-700/60">
                STEP 8
              </span>
            </h1>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Forensic Case Diary with Atomic Verified Facts, Chronology, and AI-Assisted Narrative Layer
          </p>
        </div>

        {/* Quick Links */}
        <div className="flex items-center gap-3">
          {diary && (
            <Link
              to={`/investigate?account=${diary.subject_account}`}
              className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded border border-gray-700 transition"
            >
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Blind Victim Workspace
            </Link>
          )}
          {diary?.case_file_id && (
            <span className="text-xs px-2.5 py-1 bg-emerald-950/80 text-emerald-300 rounded border border-emerald-700/60 font-mono">
              Linked File: {diary.case_file_id}
            </span>
          )}
        </div>
      </div>

      {/* Persistence Disclaimer Banner */}
      <div className="p-3 bg-amber-950/20 border border-amber-800/40 rounded-lg flex items-center justify-between text-xs text-amber-300/90">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            <strong>Process-Local Storage Notice:</strong> Case-diary metadata, verified facts, and AI narratives are maintained in backend process-local memory and are reset upon backend restart.
          </span>
        </div>
        <span className="font-mono text-gray-400 text-[11px] hidden sm:inline">
          SHA: 2c9f81fd... (2,000,000 rows locked)
        </span>
      </div>

      {/* Search & Configuration Bar */}
      <div className="bg-gray-900/70 border border-gray-800 p-4 rounded-xl shadow-lg space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-gray-400" />
            <input
              type="text"
              value={inputAccount}
              onChange={(e) => setInputAccount(e.target.value)}
              placeholder="Enter subject account number (e.g. KKBK10000402)"
              className="w-full pl-10 pr-4 py-2 bg-gray-950 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={maxHops}
              onChange={(e) => setMaxHops(Number(e.target.value))}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
              <option value={4}>4 Hops (Default)</option>
            </select>

            <label className="flex items-center gap-1.5 px-3 py-2 bg-gray-950 border border-gray-700 rounded-lg text-xs text-gray-300 cursor-pointer">
              <input
                type="checkbox"
                checked={withNarrative}
                onChange={(e) => setWithNarrative(e.target.checked)}
                className="rounded border-gray-700 text-indigo-600 focus:ring-indigo-500"
              />
              Generate AI Narrative
            </label>

            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-800 text-white rounded-lg text-sm font-medium transition flex items-center gap-2 shadow-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
              {loading ? 'Building Diary...' : 'Build Case Diary'}
            </button>
          </div>
        </form>

        {/* Quick Presets */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400">
          <span className="font-semibold text-gray-500">Benchmark Accounts:</span>
          {PRESET_ACCOUNTS.map((acc) => (
            <button
              key={acc}
              type="button"
              onClick={() => {
                setInputAccount(acc);
                setActiveAccount(acc);
              }}
              className={`px-2.5 py-1 rounded font-mono transition border ${
                activeAccount === acc
                  ? 'bg-indigo-900/60 text-indigo-300 border-indigo-700'
                  : 'bg-gray-950 text-gray-400 border-gray-800 hover:border-gray-700 hover:text-gray-300'
              }`}
            >
              {acc}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-950/40 border border-red-800/80 rounded-xl text-red-200 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Case Diary Generation Failed</p>
            <p className="text-xs text-red-300/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && !diary && (
        <div className="p-12 text-center bg-gray-900/40 border border-gray-800 rounded-xl space-y-4">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto" />
          <p className="text-gray-300 font-medium">Extracting Atomic Verified Facts & Multi-Hop Chronology...</p>
          <p className="text-xs text-gray-500">Running deterministic FIFO attribution and risk profile analysis</p>
        </div>
      )}

      {/* Case Diary Display */}
      {diary && (
        <div className="space-y-6">
          {/* Identity & Status Card */}
          <div className="bg-gray-900/80 border border-gray-800 p-5 rounded-xl shadow-lg space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-gray-800/80 pb-4">
              <div>
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-bold text-white font-mono">{diary.case_diary_id}</h2>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                    diary.status === 'COMPLETED'
                      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60'
                      : 'bg-amber-950/80 text-amber-300 border-amber-700/60'
                  }`}>
                    {diary.status}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1 font-mono">
                  Subject: <span className="text-indigo-300 font-semibold">{diary.subject_account}</span> |
                  Investigation ID: <span className="text-gray-300">{diary.investigation_id}</span>
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                {generationTimeMs !== null && (
                  <div className="bg-gray-950 px-3 py-1.5 rounded border border-gray-800">
                    <span className="text-gray-500">Latency:</span>{' '}
                    <span className="text-emerald-400 font-semibold">{generationTimeMs} ms</span>
                  </div>
                )}
                <div className="bg-gray-950 px-3 py-1.5 rounded border border-gray-800">
                  <span className="text-gray-500">Evidence SHA:</span>{' '}
                  <span className="text-cyan-400 font-semibold" title={diary.evidence_snapshot_sha256}>
                    {diary.evidence_snapshot_sha256.substring(0, 16)}...
                  </span>
                </div>
                <div className="bg-gray-950 px-3 py-1.5 rounded border border-gray-800">
                  <span className="text-gray-500">Facts:</span>{' '}
                  <span className="text-indigo-400 font-semibold">{diary.verified_facts.length}</span>
                </div>
                <div className="bg-gray-950 px-3 py-1.5 rounded border border-gray-800">
                  <span className="text-gray-500">Events:</span>{' '}
                  <span className="text-purple-400 font-semibold">{diary.chronology.length}</span>
                </div>
              </div>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
              <div className="p-3 bg-gray-950/60 border border-gray-800/80 rounded-lg">
                <span className="text-[11px] text-gray-400 block">Step 5B Mule Risk Index</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className="text-xl font-bold font-mono text-white">
                    {diary.findings.risk.risk_index.toFixed(1)}
                  </span>
                  <span className="text-xs px-1.5 py-0.5 rounded font-mono bg-orange-950 text-orange-300 border border-orange-800">
                    {diary.findings.risk.risk_band}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-gray-950/60 border border-gray-800/80 rounded-lg">
                <span className="text-[11px] text-gray-400 block">Primary Mule Role</span>
                <span className="text-sm font-semibold text-emerald-400 block mt-1">
                  {diary.findings.role.primary_role_label}
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  Fan-in: {diary.findings.role.fan_in} | Fan-out: {diary.findings.role.fan_out}
                </span>
              </div>

              <div className="p-3 bg-gray-950/60 border border-gray-800/80 rounded-lg">
                <span className="text-[11px] text-gray-400 block">Pass-Through Velocity</span>
                <span className={`text-sm font-semibold block mt-1 ${
                  diary.findings.velocity.pass_through_candidate ? 'text-rose-400' : 'text-gray-400'
                }`}>
                  {diary.findings.velocity.pass_through_candidate ? 'Rapid 3-15m Candidate' : 'Standard Velocity'}
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  Attributed: INR {diary.findings.velocity.attributed_volume.toLocaleString()}
                </span>
              </div>

              <div className="p-3 bg-gray-950/60 border border-gray-800/80 rounded-lg">
                <span className="text-[11px] text-gray-400 block">FIFO Root Seed Outflow</span>
                <span className="text-sm font-bold font-mono text-purple-300 block mt-1">
                  INR {diary.findings.attribution.root_seed_outflow.toLocaleString()}
                </span>
                <span className="text-[11px] text-gray-500 font-mono">
                  Max Hops: {diary.findings.attribution.max_hops_traversed} | Terminals: {diary.findings.attribution.terminal_account_count}
                </span>
              </div>
            </div>
          </div>

          {/* AI-Assisted Officer Narrative Section */}
          <div className="bg-gray-900/80 border border-gray-800 p-5 rounded-xl shadow-lg space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-800/80 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-white">AI-Assisted Officer Narrative</h3>
                {diary.narrative_metadata && (
                  <span className="text-xs px-2 py-0.5 rounded font-mono bg-gray-800 text-gray-300 border border-gray-700">
                    Source: {diary.narrative_metadata.narrative_source}
                  </span>
                )}
                {diary.narrative_metadata?.validation && (
                  <span className={`text-xs px-2 py-0.5 rounded font-mono border ${
                    diary.narrative_metadata.validation.validation_status === 'PASSED'
                      ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700'
                      : 'bg-rose-950/80 text-rose-300 border-rose-700'
                  }`}>
                    Validation: {diary.narrative_metadata.validation.validation_status}
                  </span>
                )}
              </div>

              {/* Controls */}
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={forceDeterministic}
                    onChange={(e) => setForceDeterministic(e.target.checked)}
                    className="rounded border-gray-700 text-indigo-600 focus:ring-indigo-500"
                  />
                  Force Deterministic Fallback
                </label>

                <button
                  type="button"
                  onClick={handleRegenerateNarrative}
                  disabled={narrativeLoading}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 text-gray-200 rounded text-xs font-medium border border-gray-700 transition flex items-center gap-1.5"
                >
                  {narrativeLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                  Regenerate Narrative
                </button>
              </div>
            </div>

            {/* Mandatory Forensic Disclaimer Box */}
            <div className="p-3 bg-indigo-950/20 border border-indigo-800/40 rounded-lg text-xs text-indigo-200/90 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
              <div>
                <strong>FORENSIC SEPARATION OF EVIDENCE:</strong> AI narrative is generated exclusively from the supplied verified facts and chronology events. It serves as an investigative aid and does not constitute judicial evidence, legal proof, or final beneficial ownership determination.
              </div>
            </div>

            {/* Narrative Content */}
            {diary.ai_narrative ? (
              <div className="prose prose-invert max-w-none text-xs text-gray-300 font-sans leading-relaxed bg-gray-950/60 p-5 rounded-lg border border-gray-800/80 space-y-4">
                {diary.ai_narrative.split('### ').filter(Boolean).map((section, idx) => {
                  const lines = section.split('\n');
                  const title = lines[0];
                  const body = lines.slice(1).join('\n');
                  return (
                    <div key={idx} className="space-y-1.5">
                      <h4 className="text-sm font-bold text-indigo-300 font-mono tracking-wide border-b border-gray-800 pb-1">
                        ### {title}
                      </h4>
                      <p className="whitespace-pre-line text-gray-300 leading-normal pl-1">
                        {body.trim()}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-500 bg-gray-950 rounded-lg border border-gray-800">
                <p>No narrative generated for this case diary.</p>
                <button
                  type="button"
                  onClick={handleRegenerateNarrative}
                  className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline"
                >
                  Generate Narrative Now
                </button>
              </div>
            )}
          </div>

          {/* Investigator Notes */}
          <div className="bg-gray-900/80 border border-gray-800 p-4 rounded-xl shadow-lg space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-gray-300">
              <Edit3 className="w-4 h-4 text-gray-400" />
              <span>Officer Case Notes</span>
            </div>
            <textarea
              value={investigatorNotes}
              onChange={(e) => setInvestigatorNotes(e.target.value)}
              placeholder="Record operational observations, court reference numbers, or officer instructions here..."
              rows={2}
              className="w-full p-2.5 bg-gray-950 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => setActiveTab('chronology')}
              className={`px-4 py-2.5 text-xs font-medium border-b-2 transition flex items-center gap-2 ${
                activeTab === 'chronology'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Chronology Timeline ({diary.chronology.length})
            </button>

            <button
              onClick={() => setActiveTab('facts')}
              className={`px-4 py-2.5 text-xs font-medium border-b-2 transition flex items-center gap-2 ${
                activeTab === 'facts'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              <FileCheck className="w-3.5 h-3.5" />
              Verified Atomic Facts ({diary.verified_facts.length})
            </button>

            <button
              onClick={() => setActiveTab('findings')}
              className={`px-4 py-2.5 text-xs font-medium border-b-2 transition flex items-center gap-2 ${
                activeTab === 'findings'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Forensic Findings Summary
            </button>

            <button
              onClick={() => setActiveTab('provenance')}
              className={`px-4 py-2.5 text-xs font-medium border-b-2 transition flex items-center gap-2 ${
                activeTab === 'provenance'
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-950/20'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              <Lock className="w-3.5 h-3.5" />
              Provenance & Seals
            </button>
          </div>

          {/* TAB 1: Chronology Timeline */}
          {activeTab === 'chronology' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400 font-mono">
                  Timestamp-sorted verified case events (deterministic sort key ordering)
                </span>
                <select
                  value={eventFilter}
                  onChange={(e) => setEventFilter(e.target.value)}
                  className="bg-gray-950 border border-gray-700 rounded px-2.5 py-1 text-xs text-gray-300 font-mono"
                >
                  <option value="ALL">All Event Types</option>
                  <option value="CASE_OPENED">Case Opened</option>
                  <option value="ROOT_TRANSACTION">Root Transactions</option>
                  <option value="ATTRIBUTION_HOP">Attribution Hops</option>
                  <option value="VELOCITY_EVENT">Velocity Events</option>
                  <option value="RISK_FINDING">Risk Findings</option>
                  <option value="ROLE_FINDING">Role Findings</option>
                  <option value="TERMINAL_ACCOUNT">Terminal Accounts</option>
                </select>
              </div>

              <div className="space-y-2">
                {filteredChronology.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="p-3 bg-gray-900/60 border border-gray-800 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-2 hover:border-gray-700 transition"
                  >
                    <div className="flex items-start gap-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-semibold border ${getEventBadgeColor(ev.event_type)}`}>
                        {ev.event_type}
                      </span>
                      <div>
                        <p className="text-xs text-gray-200">{ev.description}</p>
                        <p className="text-[11px] text-gray-500 font-mono mt-0.5">
                          Source: {ev.source_reference} | Sort Key: {ev.sort_key}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-xs font-mono self-end md:self-auto">
                      {ev.amount !== null && ev.amount !== undefined && (
                        <span className="text-purple-300 font-semibold">
                          INR {ev.amount.toLocaleString()}
                        </span>
                      )}
                      <span className="text-gray-400 text-[11px]">
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'Undated Finding'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: Verified Facts */}
          {activeTab === 'facts' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400 font-mono">
                  Atomic forensic facts derived strictly from verified data sources
                </span>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="bg-gray-950 border border-gray-700 rounded px-2.5 py-1 text-xs text-gray-300 font-mono"
                >
                  <option value="ALL">All Categories</option>
                  <option value="SUBJECT">Subject</option>
                  <option value="TRANSACTION">Transaction</option>
                  <option value="RISK">Risk</option>
                  <option value="ROLE">Role</option>
                  <option value="VELOCITY">Velocity</option>
                  <option value="ATTRIBUTION">Attribution</option>
                  <option value="PROVENANCE">Provenance</option>
                </select>
              </div>

              <div className="overflow-x-auto bg-gray-950 border border-gray-800 rounded-lg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-gray-900/90 text-gray-400 border-b border-gray-800">
                    <tr>
                      <th className="py-2.5 px-3">Fact ID</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Code</th>
                      <th className="py-2.5 px-3 font-sans">Statement</th>
                      <th className="py-2.5 px-3">Source Ref</th>
                      <th className="py-2.5 px-3">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60 text-gray-300">
                    {filteredFacts.map((fact) => (
                      <tr key={fact.fact_id} className="hover:bg-gray-900/40">
                        <td className="py-2 px-3 text-indigo-400 font-semibold">{fact.fact_id}</td>
                        <td className="py-2 px-3">
                          <span className={`text-[10px] px-2 py-0.5 rounded border ${getCategoryBadgeColor(fact.category)}`}>
                            {fact.category}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-gray-400">{fact.code}</td>
                        <td className="py-2 px-3 font-sans text-gray-200 max-w-md">{fact.statement}</td>
                        <td className="py-2 px-3 text-gray-500 truncate max-w-xs" title={fact.source_reference}>
                          {fact.source_reference}
                        </td>
                        <td className="py-2 px-3 text-gray-400">{fact.source_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: Forensic Findings Summary */}
          {activeTab === 'findings' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Risk Finding */}
              <div className="bg-gray-900/60 border border-gray-800 p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-orange-400" />
                    Step 5B Mule Risk Index
                  </h4>
                  <span className="text-xs font-mono text-gray-400">{diary.findings.risk.scoring_version}</span>
                </div>
                <div className="flex items-baseline gap-3">
                  <span className="text-3xl font-bold font-mono text-white">
                    {diary.findings.risk.risk_index.toFixed(1)}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded font-mono bg-orange-950 text-orange-300 border border-orange-800">
                    {diary.findings.risk.risk_band}
                  </span>
                </div>
                <div className="space-y-1.5 pt-2">
                  <span className="text-xs text-gray-400 block font-semibold">Family Breakdown:</span>
                  {Object.entries(diary.findings.risk.family_contributions).map(([fam, pts]) => (
                    <div key={fam} className="flex justify-between text-xs font-mono text-gray-300">
                      <span className="text-gray-400">{fam}:</span>
                      <span>{pts.toFixed(1)} pts</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Role Finding */}
              <div className="bg-gray-900/60 border border-gray-800 p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <Users className="w-4 h-4 text-emerald-400" />
                    Step 4 Mule Role Classification
                  </h4>
                  <span className="text-xs font-mono text-gray-400">BEHAVIORAL</span>
                </div>
                <span className="text-lg font-bold text-emerald-400 block">
                  {diary.findings.role.primary_role_label}
                </span>
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono">
                  <div className={`p-2 rounded border ${diary.findings.role.l1_collector_candidate ? 'bg-indigo-950/60 border-indigo-700 text-indigo-300' : 'bg-gray-950 border-gray-800 text-gray-600'}`}>
                    L1 Collector: {diary.findings.role.l1_collector_candidate ? 'YES' : 'NO'}
                  </div>
                  <div className={`p-2 rounded border ${diary.findings.role.l2_distributor_candidate ? 'bg-indigo-950/60 border-indigo-700 text-indigo-300' : 'bg-gray-950 border-gray-800 text-gray-600'}`}>
                    L2 Distributor: {diary.findings.role.l2_distributor_candidate ? 'YES' : 'NO'}
                  </div>
                  <div className={`p-2 rounded border ${diary.findings.role.l3_terminal_candidate ? 'bg-indigo-950/60 border-indigo-700 text-indigo-300' : 'bg-gray-950 border-gray-800 text-gray-600'}`}>
                    L3 Terminal: {diary.findings.role.l3_terminal_candidate ? 'YES' : 'NO'}
                  </div>
                </div>
                {diary.findings.role.classification_reasons.length > 0 && (
                  <div className="text-xs text-gray-400 pt-1">
                    Triggers: {diary.findings.role.classification_reasons.join(', ')}
                  </div>
                )}
              </div>

              {/* Velocity Finding */}
              <div className="bg-gray-900/60 border border-gray-800 p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <Clock className="w-4 h-4 text-rose-400" />
                    Step 5A Velocity (3-15 Min Window)
                  </h4>
                  <span className="text-xs font-mono text-gray-400">{diary.findings.velocity.classification_version}</span>
                </div>
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-gray-400">Pass-Through Candidate:</span>
                  <span className={diary.findings.velocity.pass_through_candidate ? 'text-rose-400 font-bold' : 'text-gray-400'}>
                    {diary.findings.velocity.pass_through_candidate ? 'TRUE' : 'FALSE'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-gray-400">Qualifying Event Count:</span>
                  <span className="text-gray-200">{diary.findings.velocity.qualifying_event_count}</span>
                </div>
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-gray-400">Attributed Rapid Volume:</span>
                  <span className="text-purple-300 font-bold">
                    INR {diary.findings.velocity.attributed_volume.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Attribution Finding */}
              <div className="bg-gray-900/60 border border-gray-800 p-4 rounded-xl space-y-3">
                <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                  <h4 className="font-semibold text-white flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-purple-400" />
                    Step 5C Temporal FIFO Attribution
                  </h4>
                  <span className="text-xs font-mono text-gray-400">{diary.findings.attribution.attribution_policy}</span>
                </div>
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-gray-400">Root Seed Outflow:</span>
                  <span className="text-purple-300 font-bold">
                    INR {diary.findings.attribution.root_seed_outflow.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-gray-400">Downstream Cumulative:</span>
                  <span className="text-cyan-300 font-bold">
                    INR {diary.findings.attribution.downstream_cumulative_attribution.toLocaleString()}
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 italic">
                  Note: Downstream cumulative volume represents hop-to-hop propagation and is not unique new money.
                </p>
              </div>
            </div>
          )}

          {/* TAB 4: Provenance & Seals */}
          {activeTab === 'provenance' && (
            <div className="bg-gray-900/60 border border-gray-800 p-5 rounded-xl space-y-4 text-xs font-mono">
              <h4 className="font-semibold text-white font-sans text-sm flex items-center gap-2">
                <Lock className="w-4 h-4 text-cyan-400" />
                Data Provenance & Cryptographic Seals
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-3 bg-gray-950 rounded border border-gray-800 space-y-2">
                  <span className="text-gray-400 font-semibold block">Dataset Provenance</span>
                  <div>Name: <span className="text-gray-200">{diary.data_provenance.dataset_name}</span></div>
                  <div>Rows: <span className="text-gray-200">{diary.data_provenance.dataset_rows?.toLocaleString()}</span></div>
                  <div>Dataset SHA-256: <span className="text-emerald-400 break-all">{diary.data_provenance.dataset_sha256}</span></div>
                </div>

                <div className="p-3 bg-gray-950 rounded border border-gray-800 space-y-2">
                  <span className="text-gray-400 font-semibold block">Case Diary Evidence Hash</span>
                  <div>Evidence Snapshot SHA-256:</div>
                  <div className="text-cyan-400 break-all font-bold">{diary.evidence_snapshot_sha256}</div>
                  <p className="text-[11px] text-gray-500 font-sans mt-1">
                    Calculated deterministically over canonical JSON VerifiedFacts.
                  </p>
                </div>
              </div>

              <div className="p-3 bg-gray-950 rounded border border-gray-800 space-y-1">
                <span className="text-gray-400 font-semibold block">Analytical Limitations</span>
                {Object.entries(diary.limitations).map(([k, v]) => (
                  <div key={k} className="text-gray-300">
                    <span className="text-gray-500">{k}:</span> {String(v)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
