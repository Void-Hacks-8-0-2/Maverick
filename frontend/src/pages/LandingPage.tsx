import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ShieldAlert,
  GitBranch,
  Network,
  Scale,
  Activity,
  CheckCircle2,
  Lock,
  Search,
} from 'lucide-react';
import { getDatasetSummary } from '../api/dataset';
import type { DatasetSummary } from '../types';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [stats, setStats] = useState<DatasetSummary | null>(null);
  const [searchAccount, setSearchAccount] = useState('');

  useEffect(() => {
    getDatasetSummary()
      .then((data) => setStats(data))
      .catch((err) => console.warn('Dataset summary fetch deferred:', err));
  }, []);

  // Abstract Network Visualization Canvas (GPU-Friendly, Pure Geometry, Strictly Decorative)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || window.innerWidth);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 650);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = canvas.parentElement?.clientWidth || window.innerWidth;
      height = canvas.height = canvas.parentElement?.clientHeight || 650;
    };
    window.addEventListener('resize', handleResize);

    // Generate abstract geometric flow nodes
    interface FlowNode {
      x: number;
      y: number;
      vx: number;
      vy: number;
      baseX: number;
      layer: number;
      radius: number;
      alpha: number;
    }

    const nodeCount = 42;
    const nodes: FlowNode[] = [];

    for (let i = 0; i < nodeCount; i++) {
      // 4 propagation depth layers: 0: Subject, 1: Hop 1, 2: Hop 2, 3: Terminals
      const layer = i === 0 ? 0 : i < 8 ? 1 : i < 22 ? 2 : 3;
      const targetXRatio = layer === 0 ? 0.12 : layer === 1 ? 0.35 : layer === 2 ? 0.62 : 0.88;
      const x = width * targetXRatio + (Math.random() - 0.5) * (width * 0.12);
      const y = height * 0.18 + Math.random() * (height * 0.65);

      nodes.push({
        x,
        y,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.35,
        baseX: x,
        layer,
        radius: layer === 0 ? 6.5 : layer === 3 ? 4.5 : 3.5,
        alpha: layer === 0 ? 0.9 : 0.45 + Math.random() * 0.35,
      });
    }

    let t = 0;
    const render = () => {
      t += 0.015;
      ctx.clearRect(0, 0, width, height);

      // Draw subtle propagation flow connection lines between adjacent layers
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          if (Math.abs(a.layer - b.layer) === 1) {
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < width * 0.32) {
              const edgeAlpha = (1 - dist / (width * 0.32)) * 0.14;
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.strokeStyle =
                a.layer === 0
                  ? `rgba(0, 217, 255, ${edgeAlpha * 1.5})`
                  : b.layer === 3
                  ? `rgba(244, 63, 94, ${edgeAlpha * 1.2})`
                  : `rgba(139, 92, 246, ${edgeAlpha})`;
              ctx.lineWidth = 1;
              ctx.stroke();
            }
          }
        }
      }

      // Draw nodes and subtle halos
      nodes.forEach((n) => {
        n.x += n.vx;
        n.y += n.vy;

        // Bounded floating
        if (Math.abs(n.x - n.baseX) > 25) n.vx *= -1;
        if (n.y < height * 0.15 || n.y > height * 0.85) n.vy *= -1;

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        if (n.layer === 0) {
          // Subject Root Node (Cyan double halo)
          ctx.fillStyle = '#00d9ff';
          ctx.fill();

          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + 6 + Math.sin(t) * 2, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(0, 217, 255, 0.35)';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (n.layer === 3) {
          // Terminal Nodes (Rose)
          ctx.fillStyle = 'rgba(244, 63, 94, 0.85)';
          ctx.fill();
        } else if (n.layer === 2) {
          // Distributor / L2
          ctx.fillStyle = 'rgba(139, 92, 246, 0.75)';
          ctx.fill();
        } else {
          // Intermediary
          ctx.fillStyle = 'rgba(100, 116, 139, 0.8)';
          ctx.fill();
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const acc = searchAccount.trim().toUpperCase() || 'KKBK10000402';
    navigate(`/victim/${acc}`);
  };

  return (
    <div className="min-h-screen bg-[#05070a] text-slate-100 atmospheric-canvas technical-vignette selection:bg-cyan-500/20 selection:text-cyan-300">
      {/* Top Editorial Navigation */}
      <header className="fixed top-0 inset-x-0 z-50 bg-[#05070a]/80 backdrop-blur-md border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-mono font-bold text-sm shadow-[0_0_15px_rgba(0,217,255,0.2)]">
              AC
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-slate-100 tracking-tight text-sm uppercase">
                  Abhedya Chakra
                </span>
                <span className="text-[10px] font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.2 rounded font-medium">
                  FORENSICS
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 block -mt-0.5">
                Financial Cyber-Forensics Workstation
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-6 text-xs font-mono">
            <button
              onClick={() => navigate('/victim/KKBK10000402')}
              className="text-slate-400 hover:text-slate-200 transition hidden sm:inline-block"
            >
              Victim Case
            </button>
            <button
              onClick={() => navigate('/graph')}
              className="text-slate-400 hover:text-slate-200 transition hidden sm:inline-block"
            >
              Network Graph
            </button>
            <button
              onClick={() => navigate('/transactions')}
              className="text-slate-400 hover:text-slate-200 transition hidden md:inline-block"
            >
              Audit Ledger
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-4 py-1.5 rounded-lg font-semibold flex items-center space-x-1.5 transition shadow-[0_0_20px_rgba(0,217,255,0.25)]"
            >
              <span>Console</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden">
        {/* Abstract Background Network Canvas */}
        <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
          <canvas ref={canvasRef} className="w-full h-full" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6">
          <div className="max-w-3xl space-y-6">
            {/* Small Eyebrow */}
            <div className="inline-flex items-center space-x-2 bg-slate-900/80 border border-white/[0.08] px-3 py-1 rounded-full text-xs font-mono backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-cyan-300 font-medium tracking-wider uppercase text-[11px]">
                FINANCIAL CYBER-FORENSICS PLATFORM
              </span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-slate-100 font-sans leading-[1.08]">
              FOLLOW THE MONEY.{' '}
              <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
                REVEAL THE NETWORK.
              </span>
            </h1>

            {/* Supporting Copy */}
            <p className="text-base sm:text-lg text-slate-300 font-sans leading-relaxed max-w-2xl font-normal">
              Investigate financial transaction networks, trace fund movement across multiple hops,
              identify explainable mule-network indicators, and generate evidence-grounded investigative packages.
            </p>

            {/* Primary Action Suite */}
            <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-6 py-3.5 rounded-xl flex items-center justify-center space-x-2 transition shadow-[0_0_30px_rgba(0,217,255,0.3)] text-sm font-sans"
              >
                <span>ENTER INVESTIGATION CONSOLE</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => navigate('/victim/KKBK10000402')}
                className="bg-[#0b0f19]/90 hover:bg-slate-800 text-slate-200 border border-white/[0.1] px-5 py-3.5 rounded-xl text-sm font-mono transition flex items-center justify-center space-x-2 backdrop-blur-md"
              >
                <ShieldAlert className="w-4 h-4 text-cyan-400" />
                <span>DEMO CASE: KKBK10000402</span>
              </button>
            </div>

            {/* Fast Subject Intake Search Bar */}
            <form onSubmit={handleSearchSubmit} className="pt-4 max-w-xl">
              <div className="relative flex items-center">
                <Search className="absolute left-3.5 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={searchAccount}
                  onChange={(e) => setSearchAccount(e.target.value)}
                  placeholder="Enter victim or suspect account ID (e.g. KKBK10000402)..."
                  className="w-full bg-[#0a0e14]/90 border border-white/[0.1] rounded-xl pl-10 pr-28 py-3 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition shadow-xl"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition"
                >
                  Direct Trace
                </button>
              </div>
            </form>
          </div>

          {/* Lower Hero Verified System Facts Strip */}
          <div className="mt-16 pt-8 border-t border-white/[0.08] grid grid-cols-2 md:grid-cols-4 gap-6 font-mono">
            <div className="space-y-1">
              <div className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight tabular-nums">
                {stats?.row_count ? `${(stats.row_count / 1000000).toFixed(1)}M+` : '2.0M+'}
              </div>
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                TRANSACTIONS INDEXED
              </div>
            </div>

            <div className="space-y-1">
              <div className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight tabular-nums">
                {stats?.unique_accounts?.toLocaleString() || '24,873'}
              </div>
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                UNIQUE ACCOUNTS
              </div>
            </div>

            <div className="space-y-1">
              <div className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight tabular-nums">
                15 DAYS
              </div>
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                FORENSIC WINDOW
              </div>
            </div>

            <div className="space-y-1">
              <div className="text-2xl sm:text-3xl font-bold text-cyan-400 tracking-tight tabular-nums">
                4 HOPS
              </div>
              <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                MAX ATTRIBUTION DEPTH
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Editorial Capabilities Section */}
      <section className="py-20 border-t border-white/[0.06] bg-[#070b10]">
        <div className="max-w-7xl mx-auto px-6 space-y-12">
          <div className="space-y-2">
            <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-widest font-semibold">
              CORE CAPABILITIES
            </span>
            <h2 className="text-2xl sm:text-3xl font-semibold text-slate-100 font-sans tracking-tight">
              Forensic Intelligence Methodology
            </h2>
            <p className="text-sm text-slate-400 font-sans max-w-xl">
              Engineered for financial cyber-investigators, compliance analysts, and enforcement task forces.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Capability 1: TRACE */}
            <div className="bg-[#0a0e14] border border-white/[0.07] p-6 rounded-2xl space-y-4 hover:border-cyan-500/30 transition group">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/40 border border-cyan-500/30 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition">
                <GitBranch className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">
                  01 / ATTRIBUTION
                </span>
                <h3 className="text-base font-semibold text-slate-100 font-sans">
                  Temporal FIFO Trace
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Follow stolen victim funds through multi-hop accounts with strict causal timestamps,
                conserving value and eliminating false attribution.
              </p>
            </div>

            {/* Capability 2: DETECT */}
            <div className="bg-[#0a0e14] border border-white/[0.07] p-6 rounded-2xl space-y-4 hover:border-purple-500/30 transition group">
              <div className="w-10 h-10 rounded-xl bg-purple-950/40 border border-purple-500/30 flex items-center justify-center text-purple-400 group-hover:scale-105 transition">
                <Activity className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-purple-400 uppercase tracking-wider">
                  02 / DETECTION
                </span>
                <h3 className="text-base font-semibold text-slate-100 font-sans">
                  6-Family Mule Scoring
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Identify structural layering, 3-15 minute pass-through velocity events, dormant reactivations,
                and high-fanout distributor nodes.
              </p>
            </div>

            {/* Capability 3: VISUALIZE */}
            <div className="bg-[#0a0e14] border border-white/[0.07] p-6 rounded-2xl space-y-4 hover:border-sky-500/30 transition group">
              <div className="w-10 h-10 rounded-xl bg-sky-950/40 border border-sky-500/30 flex items-center justify-center text-sky-400 group-hover:scale-105 transition">
                <Network className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-sky-400 uppercase tracking-wider">
                  03 / VISUALIZATION
                </span>
                <h3 className="text-base font-semibold text-slate-100 font-sans">
                  Semantic Network Graph
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Deterministic flow positioning with progressive cluster disclosure, parent locality,
                and WebGL acceleration for large 400+ node networks.
              </p>
            </div>

            {/* Capability 4: PRESERVE */}
            <div className="bg-[#0a0e14] border border-white/[0.07] p-6 rounded-2xl space-y-4 hover:border-rose-500/30 transition group">
              <div className="w-10 h-10 rounded-xl bg-rose-950/40 border border-rose-500/30 flex items-center justify-center text-rose-400 group-hover:scale-105 transition">
                <Scale className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <span className="text-[10px] font-mono text-rose-400 uppercase tracking-wider">
                  04 / EVIDENCE
                </span>
                <h3 className="text-base font-semibold text-slate-100 font-sans">
                  Court-Ready Case File
                </h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed font-sans">
                Compile cryptographically sealed case dossiers (SHA-256 integrity hash), verifiable
                case diaries, and Section 91/102 legal freeze drafts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Forensic Standards & Integrity Banner */}
      <section className="py-16 border-t border-white/[0.06] bg-[#05070a]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="bg-[#0b0f17] border border-white/[0.08] rounded-2xl p-8 sm:p-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
            <div className="space-y-3 max-w-2xl">
              <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400">
                <Lock className="w-3.5 h-3.5" />
                <span className="tracking-wider uppercase">ZERO HALLUCINATION PRINCIPLE</span>
              </div>
              <h3 className="text-xl sm:text-2xl font-semibold text-slate-100 font-sans tracking-tight">
                Deterministic Financial Causality
              </h3>
              <p className="text-xs sm:text-sm text-slate-400 font-sans leading-relaxed">
                Abhedya-Chakra enforces strict temporal attribution. No synthetic nodes or speculative connections
                are ever fabricated. Every link in the graph maps directly to an immutable transaction row in the production dataset.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-6 py-3 rounded-xl flex items-center justify-center space-x-2 transition text-xs font-mono"
              >
                <span>LAUNCH CONSOLE</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Institutional Footer */}
      <footer className="py-8 border-t border-white/[0.06] bg-[#040608] text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400 font-semibold">ABHEDYA CHAKRA</span>
            <span>&bull;</span>
            <span>Financial Cyber-Forensics Workstation</span>
          </div>

          <div className="flex items-center space-x-4 text-[11px] text-slate-400">
            <span>SHA-256: 2c9f81fd...</span>
            <span>&bull;</span>
            <span>2,000,000 Records Locked</span>
            <span>&bull;</span>
            <span className="text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> Engine Online
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};
