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

/* Shared logo mark */
const AppLogoMark: React.FC = () => (
  <img
    src="/abhedya-logo.png"
    alt="Abhedya-Chakra Emblem"
    className="w-7 h-7 object-contain select-none shrink-0"
  />
);

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
    icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>;
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
        { path: '/victim',       label: 'Victim Investigation',  icon: ShieldAlert },
        { path: '/graph',        label: 'Network Intelligence',  icon: Network },
        { path: '/timeline',     label: 'Forensic Timeline',     icon: Clock },
        { path: '/transactions', label: 'Transaction Explorer',  icon: ListFilter },
        { path: '/mules',        label: 'Mule Intelligence',     icon: Users },
      ]
    },
    {
      group: 'EVIDENCE',
      items: [
        { path: '/case-file',    label: 'Forensic Case File',   icon: FileCheck2 },
        { path: '/diary',        label: 'Case Diary & AI',      icon: BookOpen },
        { path: '/legal-freeze', label: 'Legal Freeze Drafts',  icon: Scale },
      ]
    }
  ];

  const getActiveModuleTitle = () => {
    const p = location.pathname;
    if (p === '/dashboard' || p === '/command') return 'Command Center';
    if (p.startsWith('/victim'))       return 'Victim Investigation';
    if (p.startsWith('/graph') || p.startsWith('/investigate')) return 'Network Intelligence';
    if (p.startsWith('/timeline'))     return 'Forensic Timeline';
    if (p.startsWith('/transactions')) return 'Transaction Explorer';
    if (p.startsWith('/mules'))        return 'Mule Intelligence';
    if (p.startsWith('/suspect') || p.startsWith('/account')) return 'Suspect Account Profile';
    if (p.startsWith('/case-file'))    return 'Forensic Case File';
    if (p.startsWith('/diary') || p.startsWith('/case-diary')) return 'Case Diary & AI Narrative';
    if (p.startsWith('/legal-freeze')) return 'Legal Freeze & Bank Requisitions';
    return 'Forensic Workspace';
  };

  return (
    <div
      className="min-h-screen flex flex-col font-sans"
      style={{ backgroundColor: 'var(--canvas)', color: 'var(--text-primary)' }}
    >
      {/* ── Top Application Bar ───────────────────────────────── */}
      <header
        className="sticky top-0 z-50 h-14 flex items-center px-4 sm:px-6 justify-between shrink-0"
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '1px solid var(--border-subtle)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}
      >
        {/* Left: Logo + Wordmark */}
        <div className="flex items-center gap-3.5">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>

          <Link to="/" className="flex items-center gap-2.5 group" id="app-logo-link">
            <AppLogoMark />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold tracking-wider text-slate-900 text-xs sm:text-sm font-mono">
                  ABHEDYA-CHAKRA
                </span>
              </div>
              <div className="text-[9px] font-mono tracking-tight hidden sm:block" style={{ color: 'var(--text-tertiary)' }}>
                FINANCIAL CYBER-FORENSICS
              </div>
            </div>
          </Link>

          <div className="hidden lg:flex items-center gap-2 pl-4" style={{ borderLeft: '1px solid var(--border-subtle)' }}>
            <span className="text-[10px] font-mono tracking-wider" style={{ color: 'var(--text-tertiary)' }}>MODULE</span>
            <span className="text-xs font-mono font-medium" style={{ color: 'var(--accent)' }}>
              {getActiveModuleTitle()}
            </span>
          </div>
        </div>

        {/* Center: Global quick-jump search */}
        <form onSubmit={handleQuickJump} className="hidden md:flex items-center max-w-sm w-full mx-4">
          <div className="relative w-full">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
            <input
              type="text"
              value={quickAccount}
              onChange={(e) => setQuickAccount(e.target.value)}
              placeholder="Jump to Account ID (e.g. KKBK10000402)..."
              id="global-quick-jump"
              className="w-full rounded pl-8 pr-7 py-1.5 text-xs font-mono focus:outline-none transition"
              style={{
                backgroundColor: 'var(--surface-2)',
                border: '1px solid var(--border-medium)',
                color: 'var(--text-primary)',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
              onBlur={(e)  => { e.currentTarget.style.borderColor = 'var(--border-medium)'; }}
            />
            {quickAccount && (
              <button type="submit" className="absolute right-2 top-2" style={{ color: 'var(--accent)' }}>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </form>

        {/* Right: Status indicators */}
        <div className="flex items-center gap-2 sm:gap-2.5 text-xs">
          <div
            className="hidden xl:flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono"
            style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-pulse" />
            <span>FORENSIC ENGINE</span>
          </div>

          <div
            className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono"
            style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)', color: 'var(--text-secondary)' }}
          >
            <Database className="w-3 h-3" style={{ color: 'var(--accent)' }} />
            <span className="hidden sm:inline">DATASET</span>
            <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>2M</span>
          </div>

          <div
            className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono"
            style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border-subtle)' }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: apiConnected === true ? '#059669' : apiConnected === false ? '#dc2626' : '#d97706' }}
            />
            <span className="hidden sm:inline" style={{ color: 'var(--text-secondary)' }}>
              {apiConnected === true ? 'ONLINE' : apiConnected === false ? 'OFFLINE' : 'CONNECTING'}
            </span>
          </div>
        </div>
      </header>

      {/* ── Main Body: Sidebar + Workspace ──────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left Sidebar */}
        <aside
          className={`fixed md:sticky top-14 z-40 h-[calc(100vh-3.5rem)] w-[240px] flex flex-col justify-between shrink-0 transition-transform duration-200 ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          }`}
          style={{
            backgroundColor: '#ffffff',
            borderRight: '1px solid var(--border-subtle)',
          }}
        >
          {/* Navigation */}
          <div className="p-3 space-y-5 overflow-y-auto">
            {navGroups.map((group) => (
              <div key={group.group} className="space-y-0.5">
                <div
                  className="px-2.5 pb-1 text-[9px] font-mono font-semibold tracking-[0.15em] uppercase"
                  style={{ color: 'var(--text-tertiary)' }}
                >
                  {group.group}
                </div>
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
                      className="flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-mono transition-all relative"
                      style={isActive
                        ? {
                            backgroundColor: 'var(--accent-light)',
                            color: 'var(--accent)',
                            border: '1px solid var(--accent-border)',
                            fontWeight: 600,
                          }
                        : {
                            color: 'var(--text-secondary)',
                            border: '1px solid transparent',
                          }}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLAnchorElement).style.backgroundColor = 'var(--surface-2)';
                          (e.currentTarget as HTMLAnchorElement).style.color = 'var(--text-primary)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          (e.currentTarget as HTMLAnchorElement).style.backgroundColor = 'transparent';
                          (e.currentTarget as HTMLAnchorElement).style.color = 'var(--text-secondary)';
                        }
                      }}
                    >
                      {isActive && (
                        <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r" style={{ backgroundColor: 'var(--accent)' }} />
                      )}
                      <Icon
                        className="w-3.5 h-3.5 shrink-0 nav-icon"
                        style={{ color: isActive ? 'var(--accent)' : 'var(--text-tertiary)' }}
                      />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Sidebar Bottom: Dataset provenance */}
          <div
            className="p-3 text-[10px] font-mono space-y-1.5"
            style={{
              borderTop: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--surface-2)',
              color: 'var(--text-tertiary)',
            }}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>DATASET SHA-256</span>
              <Lock className="w-3 h-3" style={{ color: 'var(--semantic-emerald)' }} />
            </div>
            <div
              className="font-mono text-[9px] truncate px-2 py-1 rounded"
              style={{
                backgroundColor: 'var(--surface-3)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--accent)',
              }}
            >
              2c9f81fd34f728c0b7c1...
            </div>
            <div className="flex justify-between pt-0.5">
              <span>Window: 15 Days</span>
              <span className="font-medium" style={{ color: 'var(--semantic-emerald)' }}>2,000,000 Tx</span>
            </div>
          </div>
        </aside>

        {/* Mobile backdrop */}
        {mobileMenuOpen && (
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-black/25 z-30 md:hidden backdrop-blur-sm"
          />
        )}

        {/* Central Workspace */}
        <main className="flex-1 overflow-y-auto min-w-0">
          <div className="p-4 sm:p-6 lg:p-7 max-w-[1600px] mx-auto min-h-full flex flex-col justify-between">
            <div>{children}</div>

            {/* Global Forensic Footer */}
            <footer
              className="mt-12 pt-4 text-[11px] font-mono flex flex-col md:flex-row md:items-center justify-between gap-2"
              style={{
                borderTop: '1px solid var(--border-subtle)',
                color: 'var(--text-tertiary)',
              }}
            >
              <div>
                Operation &ldquo;ABHEDYA-CHAKRA&rdquo; &bull; Financial Cyber-Forensics Workstation
              </div>
              <div className="text-[10px] text-slate-400 text-center">
                Educational project &bull; For demonstration and research purposes only &bull; Not for operational law-enforcement use
              </div>
              <div className="text-[10px]">
                Deterministic DuckDB Vectorized Core &bull; Void Hacks() 8.0
              </div>
            </footer>
          </div>
        </main>
      </div>
    </div>
  );
};
