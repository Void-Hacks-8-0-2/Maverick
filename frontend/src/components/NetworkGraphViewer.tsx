import React, { useEffect, useRef, useState } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { ZoomIn, ZoomOut, RotateCcw, ArrowUpRight } from 'lucide-react';
import type { GraphNode, GraphEdge } from '../types';
import { useNavigate } from 'react-router-dom';

interface NetworkGraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  rootAccountId?: string;
  truncated?: boolean;
  nodeLimit?: number;
  onSelectNode?: (nodeId: string) => void;
  onSelectEdge?: (edge: GraphEdge) => void;
}

export const NetworkGraphViewer: React.FC<NetworkGraphViewerProps> = ({
  nodes,
  edges,
  rootAccountId,
  truncated,
  nodeLimit,
  onSelectNode,
  onSelectEdge,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaInstanceRef = useRef<Sigma | null>(null);
  const navigate = useNavigate();

  const [selectedNode, setSelectedNode] = useState<string | null>(rootAccountId || null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy existing instance if any
    if (sigmaInstanceRef.current) {
      sigmaInstanceRef.current.kill();
      sigmaInstanceRef.current = null;
    }

    if (nodes.length === 0) return;

    // Instantiate directed Graphology graph
    const graph = new Graph({ type: 'directed' });

    // Compute circular or radial layout for initial positions
    const totalNodes = nodes.length;
    const angleStep = (2 * Math.PI) / Math.max(1, totalNodes - (rootAccountId ? 1 : 0));
    let nonRootIdx = 0;

    nodes.forEach((node) => {
      const isRoot = node.id === rootAccountId || node.is_root;
      let x = 0;
      let y = 0;

      if (isRoot) {
        x = 0;
        y = 0;
      } else {
        const radius = node.hop ? node.hop * 120 : 180 + (nonRootIdx % 3) * 60;
        const angle = nonRootIdx * angleStep;
        x = radius * Math.cos(angle);
        y = radius * Math.sin(angle);
        nonRootIdx++;
      }

      graph.addNode(node.id, {
        label: node.id,
        x,
        y,
        size: isRoot ? 14 : 8,
        color: isRoot ? '#06b6d4' : '#64748b',
        type: isRoot ? 'circle' : 'circle',
      });
    });

    // Add edges
    edges.forEach((edge) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        const edgeKey = `${edge.source}->${edge.target}-${edge.transaction_id}`;
        if (!graph.hasEdge(edgeKey)) {
          graph.addEdgeWithKey(edgeKey, edge.source, edge.target, {
            size: Math.min(6, Math.max(1.5, Math.log10(Math.max(1, edge.amount)) * 0.8)),
            color: '#334155',
            label: `₹${edge.amount.toLocaleString()}`,
            rawEdge: edge,
          });
        }
      }
    });

    // Instantiate Sigma renderer
    const renderer = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: true,
      defaultEdgeColor: '#334155',
      defaultNodeColor: '#64748b',
      labelColor: { color: '#cbd5e1' },
      labelFont: 'JetBrains Mono, monospace',
      labelSize: 11,
      minCameraRatio: 0.1,
      maxCameraRatio: 10,
    });

    sigmaInstanceRef.current = renderer;

    // Node click handler
    renderer.on('clickNode', ({ node }) => {
      setSelectedNode(node);
      setSelectedEdge(null);
      if (onSelectNode) onSelectNode(node);
    });

    // Edge click handler
    renderer.on('clickEdge', ({ edge }) => {
      const attr = graph.getEdgeAttributes(edge);
      if (attr.rawEdge) {
        setSelectedEdge(attr.rawEdge);
        setSelectedNode(null);
        if (onSelectEdge) onSelectEdge(attr.rawEdge);
      }
    });

    // Stage click (deselect)
    renderer.on('clickStage', () => {
      setSelectedNode(null);
      setSelectedEdge(null);
    });

    return () => {
      if (sigmaInstanceRef.current) {
        sigmaInstanceRef.current.kill();
        sigmaInstanceRef.current = null;
      }
    };
  }, [nodes, edges, rootAccountId]);

  // Controls
  const handleZoomIn = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedZoom({ duration: 250 });
  };

  const handleZoomOut = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedUnzoom({ duration: 250 });
  };

  const handleReset = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedReset({ duration: 250 });
  };

  return (
    <div className="relative w-full h-[650px] bg-[#070b12] rounded-xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Canvas container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Floating Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex items-center space-x-1.5 bg-slate-900/90 backdrop-blur border border-slate-700/80 p-1.5 rounded-lg shadow-lg">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleReset}
          title="Reset View"
          className="p-1.5 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Truncation & Stats Badge */}
      <div className="absolute top-4 right-4 z-10 flex items-center space-x-2">
        {truncated && (
          <div className="bg-amber-950/80 border border-amber-600/50 text-amber-300 px-2.5 py-1 rounded text-xs font-mono">
            Graph capped at {nodeLimit} nodes
          </div>
        )}
        <div className="bg-slate-900/90 backdrop-blur border border-slate-700/80 px-3 py-1 rounded text-xs text-slate-300 font-mono">
          Nodes: <span className="text-cyan-400 font-bold">{nodes.length}</span> | Edges:{' '}
          <span className="text-cyan-400 font-bold">{edges.length}</span>
        </div>
      </div>

      {/* Selected Entity Inspector Panel */}
      {(selectedNode || selectedEdge) && (
        <div className="absolute bottom-4 right-4 z-10 w-96 bg-slate-900/95 backdrop-blur border border-slate-700 p-4 rounded-xl shadow-2xl text-xs space-y-3">
          {selectedNode && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-[11px] font-mono text-cyan-400 font-semibold uppercase tracking-wider">
                  Account Inspector
                </span>
                {selectedNode === rootAccountId && (
                  <span className="bg-cyan-950 text-cyan-300 border border-cyan-700 text-[10px] px-1.5 py-0.5 rounded">
                    ROOT
                  </span>
                )}
              </div>
              <div className="mt-2 space-y-1.5 font-mono">
                <div className="text-sm font-bold text-slate-100">{selectedNode}</div>
                <div className="text-slate-400 text-[11px]">
                  Involved in this subgraph visualization
                </div>
              </div>
              <div className="mt-3 flex space-x-2">
                <button
                  onClick={() => navigate(`/account/${selectedNode}`)}
                  className="flex-1 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold py-1.5 px-3 rounded text-xs flex items-center justify-center space-x-1 transition"
                >
                  <span>Open Account</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {selectedEdge && (
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-[11px] font-mono text-cyan-400 font-semibold uppercase tracking-wider">
                  Transaction Inspector
                </span>
                <span className="bg-slate-800 text-slate-300 border border-slate-700 text-[10px] px-1.5 py-0.5 rounded font-mono">
                  {selectedEdge.payment_mode}
                </span>
              </div>
              <div className="mt-2 space-y-2 font-mono">
                <div>
                  <span className="text-slate-500 text-[10px] block">TRANSACTION ID</span>
                  <span className="text-slate-200 font-semibold">{selectedEdge.transaction_id}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-slate-500 text-[10px] block">AMOUNT</span>
                    <span className="text-emerald-400 font-bold text-sm">
                      ₹{selectedEdge.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[10px] block">IP ADDRESS</span>
                    <span className="text-slate-300">{selectedEdge.ip_address || 'Unavailable'}</span>
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] block">FLOW</span>
                  <div className="text-[11px] text-slate-300">
                    <span className="text-cyan-400">{selectedEdge.source}</span> →{' '}
                    <span className="text-purple-400">{selectedEdge.target}</span>
                  </div>
                </div>
                {selectedEdge.narration && (
                  <div>
                    <span className="text-slate-500 text-[10px] block">NARRATION</span>
                    <span className="text-slate-400 text-[11px] truncate block">
                      {selectedEdge.narration}
                    </span>
                  </div>
                )}
                <div>
                  <span className="text-slate-500 text-[10px] block">TIMESTAMP / DEVICE</span>
                  <span className="text-slate-500 italic text-[11px]">
                    Unavailable in source PDF dataset
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
