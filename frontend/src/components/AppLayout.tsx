import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  Activity,
  Search,
  Database,
  Network,
  ListFilter,
  BookOpen,
  Scale,
  Clock,
  Users,
  FileCheck2,
  Lock,
  ArrowRight,
  Menu,
  X
} from 'lucide-react';
import { getHealth } from '../api/dataset';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [quickAccount, setQuickAccount] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    getHealth()
      .then(() => setApiConnected(true))
      .catch(() => setApiConnected(false));
  }, []);

  const handleQuickJump = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = quickAccount.trim().toUpperCase();
    if (!cleaned) return;
    navigate(`/victim/${cleaned}`);
    setQuickAccount('');
  };

  interface NavItem {
    path: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    exact?: boolean;
  }

  interface NavGroup {
    group: string;
    items: NavItem[];
  }

  const navGroups: NavGroup[] = [
    {
      group: 'COMMAND',
      items: [
        { path: '/dashboard', label: 'Command Center', icon: Activity, exact: true }
      ]
    },
    {
      group: 'INVESTIGATE',
      items: [
        { path: '/victim', label: 'Victim Investigation', icon: ShieldAlert },
        { path: '/graph', label: 'Network Intelligence', icon: Network },
        { path: '/timeline', label: 'Forensic Timeline', icon: Clock },
        { path: '/transactions', label: 'Transaction Explorer', icon: ListFilter },
        { path: '/mules', label: 'Mule Intelligence', icon: Users },
      ]
    },
    {
      group: 'EVIDENCE',
      items: [
        { path: '/case-file', label: 'Forensic Case File', icon: FileCheck2 },
        { path: '/diary', label: 'Case Diary & AI', icon: BookOpen },
        { path: '/legal-freeze', label: 'Legal Freeze Drafts', icon: Scale },
      ]
    }
  ];

  // Helper to determine active module title for top bar
  const getActiveModuleTitle = () => {
    const p = location.pathname;
    if (p === '/dashboard' || p === '/command') return 'Command Center';
    if (p.startsWith('/victim')) return 'Victim Investigation';
    if (p.startsWith('/graph') || p.startsWith('/investigate')) return 'Network Intelligence';
    if (p.startsWith('/timeline')) return 'Forensic Timeline';
    if (p.startsWith('/transactions')) return 'Transaction Explorer';
    if (p.startsWith('/mules')) return 'Mule Intelligence';
    if (p.startsWith('/suspect') || p.startsWith('/account')) return 'Suspect Account Profile';
    if (p.startsWith('/case-file')) return 'Forensic Case File';
    if (p.startsWith('/diary') || p.startsWith('/case-diary')) return 'Case Diary & AI Narrative';
    if (p.startsWith('/legal-freeze')) return 'Legal Freeze & Bank Requisitions';
    return 'Forensic Workspace';
  };

  return (
    <div className="min-h-screen atmospheric-bg text-slate-100 flex flex-col font-sans selection:bg-cyan-500/20 selection:text-cyan-200">
      {/* Top Command Bar (Operational Horizon) */}
      <header className="bg-[#0b0f19]/95 backdrop-blur-md border-b border-white/[0.06] text-slate-200 sticky top-0 z-50 h-14 flex items-center px-4 sm:px-6 justify-between shrink-0">
        {/* Left: Brand Identity & Active Breadcrumb */}
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>

          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="p-1.5 bg-slate-900 border border-cyan-500/30 rounded text-cyan-400 group-hover:border-cyan-400/60 transition">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold tracking-wider text-slate-100 text-xs sm:text-sm font-mono">
                  ABHEDYA-CHAKRA
                </span>
                <span className="bg-cyan-950/40 text-cyan-400 border border-cyan-500/30 text-[9px] font-mono px-1 py-0.2 rounded font-medium">
                  v0.1
                </span>
              </div>
              <div className="text-[9px] text-slate-400 font-mono tracking-tight hidden sm:block">
                FINANCIAL CYBER-FORENSICS PLATFORM
              </div>
            </div>
          </Link>

          <div className="hidden lg:flex items-center gap-2 pl-4 border-l border-white/[0.06]">
            <span className="text-[10px] font-mono text-slate-400 tracking-wider">MODULE:</span>
            <span className="text-xs font-mono font-medium text-cyan-300">
              {getActiveModuleTitle()}
            </span>
          </div>
        </div>

        {/* Center: Global Quick Account Jump */}
        <form onSubmit={handleQuickJump} className="hidden md:flex items-center max-w-sm w-full mx-4">
          <div className="relative w-full">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              value={quickAccount}
              onChange={(e) => setQuickAccount(e.target.value)}
              placeholder="Jump to Account ID (e.g. KKBK10000402)..."
              className="w-full bg-[#06080d]/80 border border-white/[0.08] focus:border-cyan-500/50 rounded pl-8 pr-7 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-400 focus:outline-none transition"
            />
            {quickAccount && (
              <button
                type="submit"
                className="absolute right-2 top-2 text-cyan-400 hover:text-cyan-300"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </form>

        {/* Right: Forensic Engine Status & Database Indicator */}
        <div className="flex items-center gap-2 sm:gap-2.5 text-xs">
          <div className="hidden xl:flex items-center gap-1.5 bg-[#06080d]/60 border border-white/[0.06] px-2 py-1 rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] text-slate-300 font-mono">FORENSIC ENGINE</span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#06080d]/60 border border-white/[0.06] px-2 py-1 rounded">
            <Database className="w-3 h-3 text-cyan-400" />
            <span className="text-[10px] text-slate-300 font-mono hidden sm:inline">DATASET VERIFIED</span>
            <span className="text-[10px] text-slate-400 font-mono">(2M)</span>
          </div>

          <div className="flex items-center gap-1.5 bg-[#06080d]/60 border border-white/[0.06] px-2 py-1 rounded">
            <span className={`w-1.5 h-1.5 rounded-full ${apiConnected === true ? 'bg-emerald-400' : apiConnected === false ? 'bg-rose-500' : 'bg-amber-400'}`} />
            <span className="text-[10px] text-slate-300 font-mono hidden sm:inline">
              {apiConnected === true ? 'ONLINE' : apiConnected === false ? 'OFFLINE' : 'CONNECTING'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Body: Sidebar + Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar (260px desktop width) */}
        <aside
          className={`fixed md:sticky top-14 z-40 h-[calc(100vh-3.5rem)] w-[260px] bg-[#0b0f19] border-r border-white/[0.06] flex flex-col justify-between shrink-0 transition-transform duration-200 ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
        >
          {/* Navigation Links Grouped */}
          <div className="p-3 space-y-5 overflow-y-auto">
            {navGroups.map((group) => (
              <div key={group.group} className="space-y-1">
                <div className="px-2.5 pb-1 text-[10px] font-mono font-medium tracking-wider text-slate-400 uppercase">
                  {group.group}
                </div>
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const isActive = item.exact
                      ? location.pathname === item.path
                      : location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));

                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setMobileMenuOpen(false)}
                        className={`flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-mono transition-all relative ${
                          isActive
                            ? 'bg-slate-800/60 text-slate-100 font-medium border border-white/[0.08]'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 border border-transparent'
                        }`}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-cyan-400 rounded-r" />
                        )}
                        <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Sidebar Bottom: Provenance Stamp */}
          <div className="p-3 border-t border-white/[0.06] bg-[#070a12]/60 text-[10px] font-mono text-slate-400 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-300 font-medium">DATASET SHA-256</span>
              <Lock className="w-3 h-3 text-emerald-400" />
            </div>
            <div className="text-cyan-300 font-mono text-[9px] truncate bg-[#06080d] px-2 py-1 rounded border border-white/[0.06]">
              2c9f81fd34f728c0b7c1...
            </div>
            <div className="text-[9px] text-slate-400 flex justify-between pt-0.5">
              <span>Window: 15 Days</span>
              <span className="text-emerald-400 font-medium">2,000,000 Tx</span>
            </div>
          </div>
        </aside>

        {/* Backdrop for mobile sidebar */}
        {mobileMenuOpen && (
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-black/60 z-30 md:hidden backdrop-blur-sm"
          />
        )}

        {/* Central Fluid Workspace */}
        <main className="flex-1 overflow-y-auto min-w-0">
          <div className="p-4 sm:p-6 lg:p-7 max-w-[1600px] mx-auto min-h-full flex flex-col justify-between">
            <div>{children}</div>

            {/* Global Forensic Footer */}
            <footer className="mt-12 pt-4 border-t border-white/[0.06] text-[11px] font-mono text-slate-400 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                Operation &quot;ABHEDYA-CHAKRA&quot; &bull; Financial Cyber-Forensics Workstation
              </div>
              <div className="text-slate-400 text-[10px]">
                Deterministic DuckDB Vectorized Core &bull; Void Hacks() 8.0
              </div>
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
};
