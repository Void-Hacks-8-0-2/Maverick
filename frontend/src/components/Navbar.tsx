import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ShieldAlert, Activity, Search, Database, Network, ListFilter } from 'lucide-react';
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
    { path: '/investigate', label: 'Investigation Workspace', icon: Search },
    { path: '/transactions', label: 'Transactions', icon: ListFilter },
    { path: '/graph', label: 'Network Graph', icon: Network },
  ];

  return (
    <header className="bg-[#0b0f19] border-b border-slate-800 text-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Platform Identity */}
          <div className="flex items-center space-x-3">
            <Link to="/" className="flex items-center space-x-2.5">
              <div className="p-2 bg-cyan-950 border border-cyan-500/30 rounded-lg text-cyan-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold tracking-wider text-slate-100 text-base font-mono">ABHEDYA-CHAKRA</span>
                  <span className="bg-slate-800 text-cyan-400 border border-cyan-800 text-[10px] font-mono px-1.5 py-0.5 rounded">v0.1</span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono tracking-tight">CYBER FORENSICS & MULE DETECT</div>
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
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-slate-800/90 text-cyan-400 border border-slate-700'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* System & Source Indicator */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded text-xs">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-[11px] text-slate-300 font-mono">DEV DATASET (149k)</span>
            </div>

            <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded text-xs">
              <span className={`w-2 h-2 rounded-full ${apiConnected === true ? 'bg-emerald-500 shadow-sm shadow-emerald-500' : apiConnected === false ? 'bg-rose-500' : 'bg-amber-500'}`} />
              <span className="text-[11px] text-slate-400 font-mono">
                {apiConnected === true ? 'API ONLINE' : apiConnected === false ? 'API OFFLINE' : 'CHECKING...'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
