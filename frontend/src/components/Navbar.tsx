import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShieldAlert, Activity, Search, Database, Network, ListFilter, BookOpen, Scale, Clock } from 'lucide-react';
import { getHealth } from '../api/dataset';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    getHealth()
      .then(() => setApiConnected(true))
      .catch(() => setApiConnected(false));
  }, []);

  const navLinks = [
    { path: '/', label: 'Command Center', icon: Activity },
    { path: '/victim', label: 'Blind Victim Trace', icon: ShieldAlert },
    { path: '/diary', label: 'Case Diary & AI', icon: BookOpen },
    { path: '/legal-freeze', label: 'Legal Drafts', icon: Scale },
    { path: '/investigate', label: 'Network Workspace', icon: Search },
    { path: '/transactions', label: 'Transactions', icon: ListFilter },
    { path: '/timeline', label: 'Timeline', icon: Clock },
    { path: '/graph', label: 'Network Graph', icon: Network },
  ];

  return (
    <header className="bg-white border-b border-slate-200 text-slate-800 sticky top-0 z-50 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo & Platform Identity */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2.5">
              <img src="/abhedya-logo.png" alt="Abhedya-Chakra Emblem" className="w-8 h-8 object-contain shrink-0" />
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold tracking-wider text-slate-900 text-sm font-mono">ABHEDYA-CHAKRA</span>
                  <span className="bg-slate-100 text-slate-600 border border-slate-200 text-[10px] font-mono px-1.5 py-0.5 rounded">v0.1</span>
                </div>
                <div className="text-[9px] text-slate-500 font-mono tracking-wider uppercase">CYBER FORENSICS & MULE DETECT</div>
              </div>
            </Link>
          </div>

          {/* Nav Routes */}
          <nav className="flex space-x-1">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-medium transition ${
                    isActive
                      ? 'bg-violet-50 text-violet-700 border border-violet-200 font-semibold'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* System & Source Indicator */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded text-xs">
              <Database className="w-3.5 h-3.5 text-violet-700" />
              <span className="text-[10px] text-slate-700 font-mono">PROD DATASET (2M)</span>
            </div>

            <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded text-xs">
              <span className={`w-1.5 h-1.5 rounded-full ${apiConnected === true ? 'bg-emerald-500' : apiConnected === false ? 'bg-rose-500' : 'bg-amber-500'}`} />
              <span className="text-[10px] text-slate-600 font-mono">
                {apiConnected === true ? 'API ONLINE' : apiConnected === false ? 'API OFFLINE' : 'CHECKING...'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
