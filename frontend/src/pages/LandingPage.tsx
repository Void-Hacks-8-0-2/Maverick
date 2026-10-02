import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDatasetSummary } from '../api/dataset';
import type { DatasetSummary } from '../types';

/* ──────────────────────────────────────────────────────────────
   ABHEDYA-CHAKRA Landing Page
   Minimal, premium, institutional. Single LAUNCH CTA.
   ────────────────────────────────────────────────────────────── */


export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stats, setStats] = useState<DatasetSummary | null>(null);

  useEffect(() => {
    getDatasetSummary()
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  /* Subtle light-background network animation */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    const resize = () => {
      canvas.width  = canvas.parentElement?.clientWidth  || window.innerWidth;
      canvas.height = canvas.parentElement?.clientHeight || window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // 4-layer propagation geometry (ROOT → L1 → L2 → L3)
    interface Pt { x: number; y: number; vx: number; vy: number; layer: number; r: number }
    const pts: Pt[] = [];
    const N = 36;

    const init = () => {
      pts.length = 0;
      const W = canvas.width, H = canvas.height;
      for (let i = 0; i < N; i++) {
        const layer = i === 0 ? 0 : i < 6 ? 1 : i < 18 ? 2 : 3;
        const xRatio = [0.12, 0.35, 0.62, 0.88][layer];
        pts.push({
          x: W * xRatio + (Math.random() - 0.5) * W * 0.1,
          y: H * 0.15 + Math.random() * H * 0.7,
          vx: (Math.random() - 0.5) * 0.18,
          vy: (Math.random() - 0.5) * 0.22,
          layer,
          r: [7, 4, 3.5, 3][layer],
        });
      }
    };

    init();
    window.addEventListener('resize', init);

    const layerColor = [
      'rgba(109,40,217,',   // ROOT — violet
      'rgba(16,185,129,',   // L1 — emerald
      'rgba(245,158,11,',   // L2 — amber
      'rgba(220,38,38,',    // L3 — red
    ];

    const draw = () => {
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      // Draw connecting edges first
      for (let i = 0; i < pts.length; i++) {
        for (let j = i + 1; j < pts.length; j++) {
          const a = pts[i], b = pts[j];
          if (Math.abs(a.layer - b.layer) !== 1) continue;
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 220) continue;
          const alpha = (1 - dist / 220) * 0.07;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(109,40,217,${alpha})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Draw nodes
      pts.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        // gentle bounce within bounds
        if (p.x < 20 || p.x > W - 20) p.vx *= -1;
        if (p.y < 20 || p.y > H - 20) p.vy *= -1;

        const baseAlpha = p.layer === 0 ? 0.35 : 0.18;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `${layerColor[p.layer]}${baseAlpha})`;
        ctx.fill();
        // ring
        ctx.strokeStyle = `${layerColor[p.layer]}${baseAlpha + 0.12})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      animId = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
      window.removeEventListener('resize', init);
    };
  }, []);

  return (
    <div className="relative min-h-screen flex flex-col overflow-hidden" style={{ background: 'linear-gradient(160deg, #f8f9fa 0%, #ede9fe 80%, #f3f4f6 100%)' }}>
      {/* Decorative background canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none select-none"
        aria-hidden="true"
      />

      {/* Top bar — minimal branding */}
      <header className="relative z-10 flex items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
          <img src="/abhedya-logo.png" alt="Abhedya-Chakra Emblem" className="w-7 h-7 object-contain select-none shrink-0" />
          <span className="text-xs font-mono font-medium tracking-[0.2em] text-violet-900 uppercase select-none">
            Abhedya-Chakra
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          {stats && (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
              <span>Dataset active · {stats.row_count?.toLocaleString() ?? '2,000,000'} Tx</span>
            </>
          )}
        </div>
      </header>

      {/* Hero — centered, spacious, no marketing copy */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pb-24 text-center">
        {/* Logo mark */}
        <div className="mb-8 flex items-center justify-center">
          <img 
            src="/abhedya-logo.png" 
            alt="Abhedya-Chakra Emblem" 
            className="w-24 h-24 sm:w-28 sm:h-28 object-contain select-none drop-shadow-sm" 
          />
        </div>

        {/* Wordmark */}
        <h1
          className="font-semibold tracking-[-0.03em] text-slate-900 mb-3 select-none"
          style={{ fontSize: 'clamp(2.2rem, 6vw, 4rem)', lineHeight: 1.05, fontFamily: "'Inter', sans-serif" }}
        >
          ABHEDYA-CHAKRA
        </h1>

        {/* Descriptor — small, secondary, not a slogan */}
        <p className="text-sm font-mono text-violet-700 tracking-[0.15em] uppercase mb-4 select-none">
          Financial Cyber-Forensics
        </p>

        <p className="text-[13px] text-slate-500 max-w-sm leading-relaxed mb-12 select-none">
          Investigate transaction networks.
          Trace financial flows.
          Preserve evidence.
        </p>

        {/* SINGLE CTA */}
        <button
          type="button"
          id="launch-btn"
          onClick={() => navigate('/dashboard')}
          className="group relative inline-flex items-center gap-3 px-12 py-4 rounded-xl font-mono font-semibold text-sm tracking-[0.15em] uppercase text-white transition-all duration-200"
          style={{
            background: '#6d28d9',
            boxShadow: '0 4px 24px rgba(109,40,217,0.35)',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = '#7c3aed';
            (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 6px 32px rgba(109,40,217,0.45)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = '#6d28d9';
            (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 4px 24px rgba(109,40,217,0.35)';
          }}
        >
          LAUNCH
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="transition-transform duration-200 group-hover:translate-x-0.5">
            <path d="M3 8h10M9 4l4 4-4 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </main>

      {/* Bottom metadata strip & Educational Disclaimer */}
      <footer className="relative z-10 pb-6 flex flex-col items-center gap-2.5">
        <div className="flex items-center gap-6 text-[10px] font-mono text-slate-400 tracking-wider">
          <span>DuckDB Vectorized Core</span>
          <span className="w-px h-3 bg-slate-300" />
          <span>SHA-256 Integrity Verified</span>
          <span className="w-px h-3 bg-slate-300" />
          <span>4-Hop FIFO Attribution</span>
        </div>
        <div className="text-[11px] font-mono text-slate-400 tracking-wide text-center px-4 select-none">
          Educational project &bull; For demonstration and research purposes only &bull; Not for operational law-enforcement use
        </div>
      </footer>
    </div>
  );
};
