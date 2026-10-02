import React from 'react';
import { ShieldCheck, Database, Lock } from 'lucide-react';
import { HashDisplay } from './HashDisplay';

interface ProvenanceFooterProps {
  datasetSha256?: string;
  evidenceSnapshotSha256?: string;
  provenanceChain?: string;
  disclaimer?: string;
}

export const ProvenanceFooter: React.FC<ProvenanceFooterProps> = ({
  datasetSha256 = '2c9f81fd34f728c0b7c1e803cb49e1e231c1d9204a77badfcb737f50adf73101',
  evidenceSnapshotSha256,
  provenanceChain = 'RAW DATASET -> ANALYTICAL TIER -> FEATURE STORE -> FORENSIC EVIDENCE',
  disclaimer = 'INVESTIGATIVE FORENSICS ONLY — Deterministic accounting and behavioral models. Does not constitute legal determination or judicial finding of guilt.'
}) => {
  return (
    <div className="surface-l2 border-hairline rounded-xl p-4 sm:p-5 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono font-semibold text-slate-200 uppercase tracking-wider">
            Evidence Provenance & Cryptographic Seals
          </span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>PRODUCTION STORE (2,000,000 ROWS)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div className="flex items-center justify-between bg-[#06080d]/60 p-2.5 rounded-lg border border-white/[0.04]">
          <span className="text-slate-400 font-mono text-[11px] flex items-center gap-1.5">
            <Lock className="w-3 h-3 text-slate-500" />
            Dataset SHA-256:
          </span>
          <HashDisplay hash={datasetSha256} />
        </div>

        {evidenceSnapshotSha256 && (
          <div className="flex items-center justify-between bg-[#06080d]/60 p-2.5 rounded-lg border border-white/[0.04]">
            <span className="text-slate-400 font-mono text-[11px] flex items-center gap-1.5">
              <ShieldCheck className="w-3 h-3 text-cyan-400" />
              Evidence Snapshot SHA-256:
            </span>
            <HashDisplay hash={evidenceSnapshotSha256} />
          </div>
        )}
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 text-[10px] font-mono text-slate-500">
        <div>PROVENANCE: {provenanceChain}</div>
        <div className="text-slate-500/80 italic">{disclaimer}</div>
      </div>
    </div>
  );
};
