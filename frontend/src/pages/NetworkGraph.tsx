import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Search,
  Network,
  Loader2,
  ArrowRight,
  GitBranch
} from 'lucide-react';
import { getAccountGraph, getAccountTrace } from '../api/graph';
import type { GraphNode, GraphEdge, GraphData, TraceData } from '../types';
import { NetworkGraphViewer } from '../components/NetworkGraphViewer';

export const NetworkGraph: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialAccount = searchParams.get('account') || 'KKBK10000000';
  const initialMode = (searchParams.get('mode') as 'ego' | 'trace') || 'ego';

  const [accountId, setAccountId] = useState(initialAccount);
  const [inputAccount, setInputAccount] = useState(initialAccount);
  const [mode, setMode] = useState<'ego' | 'trace'>(initialMode);
  const [maxHops, setMaxHops] = useState(1);

  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [paths, setPaths] = useState<string[][]>([]);
  const [truncated, setTruncated] = useState(false);
  const [nodeLimit, setNodeLimit] = useState(500);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accountId) return;

    setLoading(true);
    setError(null);

    if (mode === 'ego') {
      getAccountGraph(accountId, maxHops, 500)
        .then((res: GraphData) => {
          setNodes(res.nodes);
          setEdges(res.edges);
          setPaths([]);
          setTruncated(res.truncated);
          setNodeLimit(res.node_limit);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || 'Failed to load account graph');
          setLoading(false);
        });
    } else {
      getAccountTrace(accountId, 1000)
        .then((res: TraceData) => {
          setNodes(res.nodes);
          setEdges(res.edges);
          setPaths(res.paths || []);
          setTruncated(res.truncated);
          setNodeLimit(res.node_limit);
          setLoading(false);
        })
        .catch((err) => {
          setError(err.message || 'Failed to perform 4-hop structural trace');
          setLoading(false);
        });
    }
  }, [accountId, mode, maxHops]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputAccount.trim()) return;
    setAccountId(inputAccount.trim());
    setSearchParams({ account: inputAccount.trim(), mode });
  };

  const handleModeChange = (newMode: 'ego' | 'trace') => {
    setMode(newMode);
    setSearchParams({ account: accountId, mode: newMode });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header and Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
              {mode === 'ego' ? 'Structural Topology Graph' : '4-Hop Deterministic Trace'}
            </span>
            <span className="bg-slate-800 text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded">
              Base v0.1
            </span>
          </div>
          <h1 className="text-xl font-bold font-mono text-slate-100 tracking-wide mt-1">
            Network Traversal & Money-Flow Graph
          </h1>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Mode Switcher */}
          <div className="flex bg-slate-900 border border-slate-700/80 rounded-lg p-0.5 text-xs font-mono">
            <button
              onClick={() => handleModeChange('ego')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
                mode === 'ego'
                  ? 'bg-cyan-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              <span>Ego Graph</span>
            </button>
            <button
              onClick={() => handleModeChange('trace')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition ${
                mode === 'trace'
                  ? 'bg-purple-600 text-white font-bold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>4-Hop Trace</span>
            </button>
          </div>

          {/* Hop Selector for Ego mode */}
          {mode === 'ego' && (
            <div className="flex items-center space-x-1 bg-slate-900 border border-slate-700/80 px-2 py-1 rounded-lg text-xs font-mono text-slate-300">
              <span>Hops:</span>
              {[1, 2, 3].map((h) => (
                <button
                  key={h}
                  onClick={() => setMaxHops(h)}
                  className={`px-2 py-0.5 rounded text-xs transition ${
                    maxHops === h ? 'bg-slate-700 text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {h}
                </button>
              ))}
            </div>
          )}

          {/* Account Search input */}
          <form onSubmit={handleSubmit} className="flex gap-1.5">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={inputAccount}
                onChange={(e) => setInputAccount(e.target.value)}
                placeholder="Target Account..."
                className="bg-[#0b0f19] border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition w-44"
              />
            </div>
            <button
              type="submit"
              className="bg-cyan-600 hover:bg-cyan-500 text-white px-3 py-1.5 rounded-lg text-xs font-mono font-semibold transition"
            >
              Run
            </button>
          </form>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-800 rounded-xl text-xs font-mono text-rose-300">
          {error}
        </div>
      )}

      {/* Main Canvas Viewport */}
      {loading ? (
        <div className="h-[650px] flex flex-col items-center justify-center bg-[#070b12] rounded-xl border border-slate-800">
          <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mb-3" />
          <span className="font-mono text-xs text-slate-400">
            {mode === 'trace' ? 'Traversing multi-hop forward flows...' : 'Extracting network topology graph...'}
          </span>
        </div>
      ) : (
        <NetworkGraphViewer
          nodes={nodes}
          edges={edges}
          rootAccountId={accountId}
          truncated={truncated}
          nodeLimit={nodeLimit}
        />
      )}

      {/* Multi-Hop Path Inspector in Trace Mode */}
      {mode === 'trace' && paths.length > 0 && (
        <div className="bg-[#0b0f19] border border-slate-800 p-5 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-purple-400 font-semibold uppercase tracking-wider">
              Discovered Deterministic Forward Paths ({paths.length})
            </span>
            <span className="text-[11px] font-mono text-slate-500">
              Structural path traversal without temporal FIFO claims
            </span>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {paths.map((p, idx) => (
              <div
                key={idx}
                className="bg-slate-900/60 border border-slate-800/80 p-2.5 rounded-lg flex items-center space-x-2 text-xs font-mono overflow-x-auto"
              >
                <span className="text-slate-500 text-[10px] w-6 shrink-0">#{idx + 1}</span>
                {p.map((node, nodeIdx) => (
                  <React.Fragment key={nodeIdx}>
                    <button
                      onClick={() => navigate(`/account/${node}`)}
                      className={`hover:underline shrink-0 ${
                        nodeIdx === 0
                          ? 'text-cyan-400 font-bold'
                          : nodeIdx === p.length - 1
                          ? 'text-emerald-400 font-bold'
                          : 'text-slate-300'
                      }`}
                    >
                      {node}
                    </button>
                    {nodeIdx < p.length - 1 && (
                      <ArrowRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
