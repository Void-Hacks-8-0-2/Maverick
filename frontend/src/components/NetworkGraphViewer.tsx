import React, { useEffect, useRef, useState, useMemo } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ArrowUpRight,
  ArrowRight,
  Crosshair,
  Maximize2,
  Minimize2,
} from 'lucide-react';
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

interface ClusterMeta {
  clusterId: string;
  parentId: string;
  memberNodes: GraphNode[];
  memberEdges: GraphEdge[];
  totalVolume: number;
  terminalCount: number;
  roleCounts: Record<string, number>;
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
  const minimapCanvasRef = useRef<HTMLCanvasElement>(null);
  const sigmaInstanceRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const navigate = useNavigate();

  const [selectedNode, setSelectedNode] = useState<string | null>(rootAccountId || null);
  const [selectedCluster, setSelectedCluster] = useState<ClusterMeta | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdge | null>(null);
  const [activeHudFilter, setActiveHudFilter] = useState<'ALL' | 'EGO' | 'TERMINAL'>('ALL');
  const [viewDetailMode, setViewDetailMode] = useState<'OVERVIEW' | 'NETWORK' | 'DETAIL'>('OVERVIEW');
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());

  // Determine if network is dense (>50 nodes)
  const isDenseNetwork = nodes.length > 50;

  // Compute hop stats from input
  const maxHopObserved = useMemo(() => {
    let maxH = 0;
    nodes.forEach((n) => {
      if (n.hop && n.hop > maxH) maxH = n.hop;
    });
    return maxH;
  }, [nodes]);

  // Dynamic layer structural guides for header
  const layerHeaders = useMemo(() => {
    if (maxHopObserved <= 0) return [{ label: 'SUBJECT', color: 'text-cyan-400 font-semibold' }];
    if (maxHopObserved === 1) {
      return [
        { label: 'SUBJECT', color: 'text-cyan-400 font-semibold' },
        { label: 'HOP 1 (RECIPIENTS)', color: 'text-slate-300' },
      ];
    }
    if (maxHopObserved === 2) {
      return [
        { label: 'SUBJECT', color: 'text-cyan-400 font-semibold' },
        { label: 'HOP 1 (INTERMEDIARIES)', color: 'text-purple-300' },
        { label: 'HOP 2 / TERMINALS', color: 'text-rose-400 font-semibold' },
      ];
    }
    if (maxHopObserved === 3) {
      return [
        { label: 'SUBJECT', color: 'text-cyan-400 font-semibold' },
        { label: 'HOP 1', color: 'text-purple-300' },
        { label: 'HOP 2', color: 'text-slate-300' },
        { label: 'TERMINALS', color: 'text-rose-400 font-semibold' },
      ];
    }
    return [
      { label: 'SUBJECT', color: 'text-cyan-400 font-semibold' },
      { label: 'HOP 1', color: 'text-purple-300' },
      { label: 'HOP 2', color: 'text-slate-300' },
      { label: 'HOP 3', color: 'text-slate-300' },
      { label: 'TERMINALS', color: 'text-rose-400 font-semibold' },
    ];
  }, [maxHopObserved]);

  // Main Graphology & Sigma Engine Construction
  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy existing instance if any
    if (sigmaInstanceRef.current) {
      sigmaInstanceRef.current.kill();
      sigmaInstanceRef.current = null;
    }

    if (nodes.length === 0) return;

    // Instantiate directed Graphology multi-graph
    const graph = new Graph({ type: 'directed', multi: true });
    graphRef.current = graph;

    // 1. Group nodes by propagation layer (hop depth) from EXISTING graph data
    const nodeLayer = new Map<string, number>();

    nodes.forEach((node) => {
      const isRoot = node.id === rootAccountId || node.is_root;
      if (isRoot) {
        nodeLayer.set(node.id, 0);
      } else if (typeof node.hop === 'number' && node.hop >= 0) {
        nodeLayer.set(node.id, node.hop);
      }
    });

    // BFS depth fallback if hop property was absent on any node
    if (rootAccountId) {
      const visited = new Set<string>([rootAccountId]);
      let currentHop = [rootAccountId];
      let depth = 0;
      while (currentHop.length > 0 && depth < 10) {
        const nextHop: string[] = [];
        depth++;
        for (const u of currentHop) {
          for (const e of edges) {
            const edgeSrc = e.source;
            const edgeTgt = e.target;
            if (edgeSrc === u && !visited.has(edgeTgt)) {
              visited.add(edgeTgt);
              if (!nodeLayer.has(edgeTgt)) {
                nodeLayer.set(edgeTgt, depth);
              }
              nextHop.push(edgeTgt);
            }
          }
        }
        currentHop = nextHop;
      }
    }

    // Default any remaining unassigned nodes to layer 1
    nodes.forEach((node) => {
      if (!nodeLayer.has(node.id)) {
        nodeLayer.set(node.id, 1);
      }
    });

    let maxLayer = 0;
    nodeLayer.forEach((lvl) => {
      if (lvl > maxLayer) maxLayer = lvl;
    });

    // 2. Incoming and Outgoing edge mappings
    const inEdges = new Map<string, GraphEdge[]>();
    const outEdges = new Map<string, GraphEdge[]>();
    edges.forEach((e) => {
      const inList = inEdges.get(e.target) || [];
      inList.push(e);
      inEdges.set(e.target, inList);

      const outList = outEdges.get(e.source) || [];
      outList.push(e);
      outEdges.set(e.source, outList);
    });

    // 3. Progressive Disclosure: Determine Cluster Aggregations for Dense Networks
    // In OVERVIEW mode for dense networks (>50 nodes), downstream branches (>5 siblings) are aggregated
    const clustersByParent = new Map<string, ClusterMeta>();
    const collapsedMemberIds = new Set<string>();

    if (isDenseNetwork && viewDetailMode === 'OVERVIEW') {
      // Find downstream nodes at layer >= 2 grouped by their incoming parent
      nodes.forEach((node) => {
        const lvl = nodeLayer.get(node.id) ?? 1;
        if (lvl >= 2) {
          const incoming = inEdges.get(node.id) || [];
          const primaryParent = incoming[0]?.source;
          if (primaryParent) {
            let meta = clustersByParent.get(primaryParent);
            if (!meta) {
              meta = {
                clusterId: `cluster_${primaryParent}`,
                parentId: primaryParent,
                memberNodes: [],
                memberEdges: [],
                totalVolume: 0,
                terminalCount: 0,
                roleCounts: {},
              };
              clustersByParent.set(primaryParent, meta);
            }
            meta.memberNodes.push(node);
            const amt = incoming.reduce((s, e) => s + (e.amount || e.attributed_amount || 0), 0);
            meta.totalVolume += amt;
            if (node.is_terminal || node.role === 'L3') meta.terminalCount++;
            const role = node.role || 'INTERMEDIARY';
            meta.roleCounts[role] = (meta.roleCounts[role] || 0) + 1;
            incoming.forEach((e) => meta?.memberEdges.push(e));
          }
        }
      });

      // Collapse clusters that have >= 4 members and are NOT explicitly expanded
      clustersByParent.forEach((meta) => {
        if (meta.memberNodes.length >= 4 && !expandedClusters.has(meta.clusterId)) {
          meta.memberNodes.forEach((n) => collapsedMemberIds.add(n.id));
        }
      });
    }

    // Filter nodes to render (actual nodes not collapsed + cluster glyph nodes)
    const visibleNodes: (GraphNode & { isCluster?: boolean; clusterMeta?: ClusterMeta })[] = [];
    nodes.forEach((node) => {
      if (!collapsedMemberIds.has(node.id)) {
        visibleNodes.push(node);
      }
    });

    // Add aggregate cluster glyphs
    clustersByParent.forEach((meta) => {
      if (meta.memberNodes.length >= 4 && !expandedClusters.has(meta.clusterId)) {
        visibleNodes.push({
          id: meta.clusterId,
          type: 'intermediary',
          is_root: false,
          is_terminal: meta.terminalCount > 0,
          role: 'CLUSTER',
          hop: 2,
          label: `⊞ BRANCH (${meta.memberNodes.length})`,
          isCluster: true,
          clusterMeta: meta,
        });
        nodeLayer.set(meta.clusterId, 2);
      }
    });

    // 4. Compute horizontal layer X coordinates (Left-to-Right propagation zones)
    const getLayerX = (l: number, maxL: number): number => {
      if (maxL <= 0) return 0;
      if (maxL === 1) return l === 0 ? -320 : 320;
      if (maxL === 2) {
        if (l === 0) return -400; // ~10% from left
        if (l === 1) return -120; // ~38% from left
        return 360; // ~86% from left
      }
      if (maxL === 3) {
        if (l === 0) return -400; // ~10%
        if (l === 1) return -180; // ~32%
        if (l === 2) return 80; // ~58%
        return 360; // ~86%
      }
      return -420 + (l / maxL) * 780;
    };

    // 5. Collect visible nodes by layer
    const layerBuckets: Map<number, (typeof visibleNodes)[0][]> = new Map();
    for (let l = 0; l <= maxLayer; l++) {
      layerBuckets.set(l, []);
    }
    visibleNodes.forEach((node) => {
      const l = nodeLayer.get(node.id) ?? 1;
      layerBuckets.get(l)?.push(node);
    });

    // 6. Compute node positions deterministically with parent locality
    const nodePositions = new Map<string, { x: number; y: number }>();

    // Layer 0: Root Subject centered at y = 0
    const l0Nodes = layerBuckets.get(0) || [];
    l0Nodes.forEach((node, idx) => {
      const y = (idx - (l0Nodes.length - 1) / 2) * 60;
      nodePositions.set(node.id, { x: getLayerX(0, maxLayer), y });
    });

    // Layers 1..maxLayer
    for (let l = 1; l <= maxLayer; l++) {
      const layerNodes = layerBuckets.get(l) || [];
      if (layerNodes.length === 0) continue;

      const x = getLayerX(l, maxLayer);

      if (l === 1) {
        layerNodes.sort((a, b) => {
          const aAmt = (inEdges.get(a.id) || []).reduce((s, e) => s + (e.amount || e.attributed_amount || 0), 0);
          const bAmt = (inEdges.get(b.id) || []).reduce((s, e) => s + (e.amount || e.attributed_amount || 0), 0);
          if (Math.abs(bAmt - aAmt) > 0.01) return bAmt - aAmt;
          return a.id.localeCompare(b.id);
        });

        const count = layerNodes.length;
        const spacing = Math.max(46, Math.min(76, 560 / Math.max(1, count - 1)));
        layerNodes.forEach((node, idx) => {
          const y = (idx - (count - 1) / 2) * spacing;
          nodePositions.set(node.id, { x, y: Math.round(y * 10) / 10 });
        });
      } else {
        interface NodeSortItem {
          node: (typeof visibleNodes)[0];
          avgParentY: number;
          totAmt: number;
        }

        const items: NodeSortItem[] = layerNodes.map((node) => {
          if (node.isCluster && node.clusterMeta) {
            const pPos = nodePositions.get(node.clusterMeta.parentId);
            const avgParentY = pPos ? pPos.y : 0;
            return { node, avgParentY, totAmt: node.clusterMeta.totalVolume };
          }
          const incoming = inEdges.get(node.id) || [];
          const parentYs: number[] = [];
          let totAmt = 0;
          incoming.forEach((e) => {
            totAmt += e.amount || e.attributed_amount || 0;
            const pPos = nodePositions.get(e.source);
            if (pPos) parentYs.push(pPos.y);
          });
          const avgParentY = parentYs.length > 0 ? parentYs.reduce((s, v) => s + v, 0) / parentYs.length : 0;
          return { node, avgParentY, totAmt };
        });

        items.sort((a, b) => {
          if (Math.abs(a.avgParentY - b.avgParentY) > 0.01) {
            return a.avgParentY - b.avgParentY;
          }
          if (Math.abs(b.totAmt - a.totAmt) > 0.01) {
            return b.totAmt - a.totAmt;
          }
          return a.node.id.localeCompare(b.node.id);
        });

        const count = items.length;
        const minGap = Math.max(36, Math.min(52, 640 / Math.max(1, count)));

        const assignedY: { id: string; y: number }[] = [];
        let curY = -999999;
        for (const item of items) {
          const targetY = item.avgParentY;
          const y = Math.max(targetY, curY + minGap);
          assignedY.push({ id: item.node.id, y });
          curY = y;
        }

        if (assignedY.length > 0) {
          const minY = assignedY[0].y;
          const maxY = assignedY[assignedY.length - 1].y;
          const mid = (minY + maxY) / 2;
          assignedY.forEach(({ id, y }) => {
            nodePositions.set(id, { x, y: Math.round((y - mid) * 10) / 10 });
          });
        }
      }
    }

    // 7. Add nodes to Graphology with Semantic Zoom Label Policy
    visibleNodes.forEach((node) => {
      const isRoot = node.id === rootAccountId || node.is_root;
      const isTerminal = node.role === 'L3' || node.is_terminal || (node.hop && node.hop >= 2);
      const isDistributor = node.role === 'L2';
      const isCluster = node.isCluster;

      const pos = nodePositions.get(node.id) || { x: 0, y: 0 };

      let baseSize = 9;
      let baseColor = '#475569'; // Muted neutral slate
      let zIndex = 10;
      let label = '';

      if (isRoot) {
        baseSize = 24;
        baseColor = '#00d9ff'; // Cyan Subject anchor
        zIndex = 100;
        label = `★ ${node.id} [SUBJECT]`;
      } else if (isCluster && node.clusterMeta) {
        baseSize = 18;
        baseColor = '#8b5cf6'; // Iris purple cluster
        zIndex = 30;
        label = `⊞ CLUSTER (${node.clusterMeta.memberNodes.length} ACCTS)`;
      } else if (isTerminal) {
        baseSize = 14;
        baseColor = '#f43f5e'; // Rose terminal
        zIndex = 20;
        label = viewDetailMode === 'OVERVIEW' && isDenseNetwork ? '' : `● ${node.id}`;
      } else if (isDistributor) {
        baseSize = 12;
        baseColor = '#8b5cf6'; // Violet distributor
        zIndex = 15;
        label = viewDetailMode === 'OVERVIEW' && isDenseNetwork ? '' : node.id;
      } else {
        // Intermediary
        baseSize = 9;
        baseColor = '#475569';
        label = viewDetailMode === 'DETAIL' || !isDenseNetwork ? node.id : '';
      }

      // If user selected this node, always show its label
      if (node.id === selectedNode) {
        label = node.id;
      }

      graph.addNode(node.id, {
        label,
        x: pos.x,
        y: pos.y,
        size: baseSize,
        color: baseColor,
        baseColor,
        baseSize,
        zIndex,
        isRoot,
        isTerminal,
        isCluster: !!isCluster,
        clusterMeta: node.clusterMeta,
        hop: nodeLayer.get(node.id) ?? node.hop ?? 0,
        rawNode: node,
      });
    });

    // 8. Add edges with directional attributes, constrained weights and arrowheads
    const formatDelay = (seconds?: number) => {
      if (typeof seconds !== 'number' || seconds <= 0) return '';
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60);
      return ` · ${m.toString().padStart(2, '0')}m ${s.toString().padStart(2, '0')}s`;
    };

    // Standard edges
    edges.forEach((edge, idx) => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        const edgeKey = `${edge.source}->${edge.target}-${edge.transaction_id || edge.id || idx}`;
        if (!graph.hasEdge(edgeKey)) {
          const isFromRoot = edge.source === rootAccountId;
          const baseColor = isFromRoot ? '#0ea5e9' : '#8b5cf6';

          const amt = edge.amount || edge.attributed_amount || 0;
          const logAmt = Math.log10(Math.max(10, amt));
          const size = Math.min(4.2, Math.max(2.0, 1.8 + (logAmt - 2.5) * 0.7));

          const amountStr = `₹${Math.round(amt).toLocaleString()}`;
          const delayStr = formatDelay(edge.delay_seconds);
          const edgeLabel = viewDetailMode === 'DETAIL' || !isDenseNetwork ? `${amountStr}${delayStr}` : '';

          graph.addEdgeWithKey(edgeKey, edge.source, edge.target, {
            size,
            baseSize: size,
            color: baseColor,
            baseColor,
            label: edgeLabel,
            rawEdge: edge,
            isFromRoot,
            zIndex: isFromRoot ? 5 : 2,
          });
        }
      }
    });

    // Cluster aggregation edges from parent to cluster glyph
    clustersByParent.forEach((meta) => {
      if (meta.memberNodes.length >= 4 && !expandedClusters.has(meta.clusterId)) {
        if (graph.hasNode(meta.parentId) && graph.hasNode(meta.clusterId)) {
          const edgeKey = `cluster_edge_${meta.parentId}->${meta.clusterId}`;
          if (!graph.hasEdge(edgeKey)) {
            const edgeLabel = `₹${Math.round(meta.totalVolume).toLocaleString()} (${meta.memberNodes.length} ACCTS)`;
            graph.addEdgeWithKey(edgeKey, meta.parentId, meta.clusterId, {
              size: 3.8,
              baseSize: 3.8,
              color: '#8b5cf6',
              baseColor: '#8b5cf6',
              label: edgeLabel,
              zIndex: 8,
              isClusterEdge: true,
            });
          }
        }
      }
    });

    // 9. Instantiate Sigma renderer
    const renderer = new Sigma(graph, containerRef.current, {
      renderEdgeLabels: true,
      defaultEdgeType: 'arrow',
      defaultEdgeColor: '#334155',
      defaultNodeColor: '#475569',
      labelColor: { color: '#e2e8f0' },
      labelFont: 'JetBrains Mono, monospace',
      labelSize: 10,
      labelWeight: '500',
      minCameraRatio: 0.05,
      maxCameraRatio: 10,
    });

    renderer.getCamera().animatedReset({ duration: 0 });
    sigmaInstanceRef.current = renderer;

    // Node click handler (supports cluster expansion or account selection)
    renderer.on('clickNode', ({ node }) => {
      const attr = graph.getNodeAttributes(node);
      if (attr.isCluster && attr.clusterMeta) {
        // Toggle cluster expansion
        setExpandedClusters((prev) => {
          const next = new Set(prev);
          if (next.has(node)) {
            next.delete(node);
          } else {
            next.add(node);
          }
          return next;
        });
        setSelectedCluster(attr.clusterMeta);
        setSelectedNode(null);
        setSelectedEdge(null);
      } else {
        setSelectedNode(node);
        setSelectedCluster(null);
        setSelectedEdge(null);
        if (onSelectNode) onSelectNode(node);
      }
    });

    // Edge click handler
    renderer.on('clickEdge', ({ edge }) => {
      const attr = graph.getEdgeAttributes(edge);
      if (attr.rawEdge) {
        setSelectedEdge(attr.rawEdge);
        setSelectedNode(null);
        setSelectedCluster(null);
        if (onSelectEdge) onSelectEdge(attr.rawEdge);
      }
    });

    // Stage click (deselect / reset spotlight)
    renderer.on('clickStage', () => {
      setSelectedNode(null);
      setSelectedCluster(null);
      setSelectedEdge(null);
    });

    // 10. Draw Minimap Preview
    const updateMinimap = () => {
      const mm = minimapCanvasRef.current;
      if (!mm) return;
      const mctx = mm.getContext('2d');
      if (!mctx) return;

      mctx.clearRect(0, 0, mm.width, mm.height);
      const graphNodes = graph.nodes();
      if (graphNodes.length === 0) return;

      // Scale coordinates into 140x80 canvas
      let minX = 999999,
        maxX = -999999,
        minY = 999999,
        maxY = -999999;
      graphNodes.forEach((n) => {
        const { x, y } = graph.getNodeAttributes(n);
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      });

      const spanX = Math.max(10, maxX - minX);
      const spanY = Math.max(10, maxY - minY);

      graphNodes.forEach((n) => {
        const { x, y, isRoot, isCluster, isTerminal } = graph.getNodeAttributes(n);
        const px = 10 + ((x - minX) / spanX) * (mm.width - 20);
        const py = 10 + ((y - minY) / spanY) * (mm.height - 20);

        mctx.beginPath();
        mctx.arc(px, py, isRoot ? 3.5 : isCluster ? 2.5 : 1.5, 0, Math.PI * 2);
        mctx.fillStyle = isRoot ? '#00d9ff' : isCluster ? '#8b5cf6' : isTerminal ? '#f43f5e' : '#64748b';
        mctx.fill();
      });
    };

    updateMinimap();

    return () => {
      if (sigmaInstanceRef.current) {
        sigmaInstanceRef.current.kill();
        sigmaInstanceRef.current = null;
      }
    };
  }, [nodes, edges, rootAccountId, viewDetailMode, expandedClusters, isDenseNetwork]);

  // Spotlight Mode & HUD Filtering
  useEffect(() => {
    const renderer = sigmaInstanceRef.current;
    const graph = graphRef.current;
    if (!renderer || !graph) return;

    renderer.setSetting('nodeReducer', (node, data) => {
      const res = { ...data };

      // Apply HUD Filter if active
      if (activeHudFilter === 'EGO') {
        const isRoot = node === rootAccountId;
        const isHop1 = data.hop === 1;
        if (!isRoot && !isHop1) {
          res.color = 'rgba(51, 65, 85, 0.14)';
          res.label = '';
          return res;
        }
      } else if (activeHudFilter === 'TERMINAL') {
        const isRoot = node === rootAccountId;
        const isTerminal = data.isTerminal;
        if (!isRoot && !isTerminal) {
          res.color = 'rgba(51, 65, 85, 0.14)';
          res.label = '';
          return res;
        }
      }

      // If a node is selected, spotlight its path and neighbors
      if (selectedNode) {
        const isSelected = node === selectedNode;
        const isNeighbor = graph.areNeighbors(node, selectedNode);
        const isRoot = node === rootAccountId;

        if (isSelected) {
          res.size = (data.baseSize || 10) * 1.3;
          res.color = '#00d9ff';
          res.zIndex = 100;
        } else if (isNeighbor || isRoot) {
          res.color = data.baseColor || '#94a3b8';
          res.zIndex = 10;
        } else {
          // Dim unrelated nodes into background
          res.color = 'rgba(51, 65, 85, 0.14)';
          res.label = '';
          res.size = Math.max(3, (data.baseSize || 8) * 0.7);
        }
      } else {
        res.color = data.baseColor;
        res.size = data.baseSize;
      }

      return res;
    });

    renderer.setSetting('edgeReducer', (edge, data) => {
      const res = { ...data };
      const source = graph.source(edge);
      const target = graph.target(edge);

      if (activeHudFilter === 'EGO') {
        const isFromRoot = source === rootAccountId;
        if (!isFromRoot) {
          res.color = 'rgba(30, 41, 59, 0.08)';
          res.size = 1;
          res.label = '';
          return res;
        }
      } else if (activeHudFilter === 'TERMINAL') {
        const targetNode = graph.getNodeAttributes(target);
        if (!targetNode.isTerminal) {
          res.color = 'rgba(30, 41, 59, 0.08)';
          res.size = 1;
          res.label = '';
          return res;
        }
      }

      if (selectedNode) {
        const isConnected = source === selectedNode || target === selectedNode;
        const isFromRoot = source === rootAccountId;

        if (isConnected) {
          res.color = '#00d9ff';
          res.size = (data.baseSize || 2) * 1.5;
          res.zIndex = 10;
        } else if (isFromRoot) {
          res.color = '#0284c7';
          res.zIndex = 5;
        } else {
          res.color = 'rgba(30, 41, 59, 0.10)';
          res.size = 1;
          res.label = '';
        }
      } else {
        res.color = data.baseColor;
        res.size = data.baseSize;
      }

      return res;
    });

    renderer.refresh();
  }, [selectedNode, selectedEdge, activeHudFilter, rootAccountId]);

  // Controls
  const handleZoomIn = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedZoom({ duration: 200 });
  };

  const handleZoomOut = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedUnzoom({ duration: 200 });
  };

  const handleReset = () => {
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) camera.animatedReset({ duration: 250 });
    setSelectedNode(rootAccountId || null);
    setSelectedCluster(null);
    setSelectedEdge(null);
    setActiveHudFilter('ALL');
  };

  const handleFocusSubject = () => {
    if (!rootAccountId || !graphRef.current) return;
    setSelectedNode(rootAccountId);
    setSelectedCluster(null);
    setSelectedEdge(null);
    const camera = sigmaInstanceRef.current?.getCamera();
    if (camera) {
      camera.animatedReset({ duration: 250 });
    }
  };

  const handleExpandAll = () => {
    setViewDetailMode('NETWORK');
    const allClusterIds = new Set<string>();
    nodes.forEach((n) => allClusterIds.add(`cluster_${n.id}`));
    setExpandedClusters(allClusterIds);
  };

  const handleCollapseAll = () => {
    setViewDetailMode('OVERVIEW');
    setExpandedClusters(new Set());
    setSelectedCluster(null);
  };

  return (
    <div className="relative w-full h-[680px] bg-[#05070a] rounded-2xl border border-white/[0.08] overflow-hidden shadow-2xl">
      {/* Canvas Atmospheric Horizon Texture */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,217,255,0.03)_0%,transparent_75%)] pointer-events-none" />

      {/* Subtle Vertical Layer Propagation Guidelines */}
      <div className="absolute inset-0 pointer-events-none flex justify-between px-16 sm:px-28 opacity-[0.04] z-0">
        <div className="border-r border-dashed border-cyan-400 h-full" />
        <div className="border-r border-dashed border-purple-400 h-full" />
        <div className="border-r border-dashed border-rose-400 h-full" />
      </div>

      {/* Canvas container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Center Structural Guide Bar */}
      <div className="absolute top-3.5 left-1/2 -translate-x-1/2 pointer-events-none hidden lg:flex items-center gap-3 text-[10px] font-mono tracking-widest uppercase select-none z-10 bg-[#070a12]/85 px-4 py-1.5 rounded-full border border-white/[0.06] backdrop-blur-sm shadow-xl">
        {layerHeaders.map((hdr, idx) => (
          <div key={hdr.label} className="flex items-center gap-2">
            <span className={hdr.color}>{hdr.label}</span>
            {idx < layerHeaders.length - 1 && <span className="text-slate-600 font-bold">→</span>}
          </div>
        ))}
      </div>

      {/* Floating Toolbar: Modes, Semantic Zoom & Camera Controls */}
      <div className="absolute top-3.5 left-3.5 z-10 flex flex-wrap items-center gap-2">
        <div className="flex items-center bg-[#070a12]/90 backdrop-blur-md border border-white/[0.08] p-1 rounded-xl shadow-xl text-xs font-mono">
          {/* Detail Mode / Semantic Zoom */}
          <div className="flex items-center gap-1 pr-1.5 border-r border-white/[0.08]">
            <button
              onClick={() => setViewDetailMode('OVERVIEW')}
              title="Overview Mode: Aggregated branches & topology"
              className={`px-2 py-1 rounded text-[11px] transition ${
                viewDetailMode === 'OVERVIEW'
                  ? 'bg-cyan-500/20 text-cyan-300 font-medium border border-cyan-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              OVERVIEW
            </button>
            <button
              onClick={() => setViewDetailMode('NETWORK')}
              title="Network Mode: Display all real accounts"
              className={`px-2 py-1 rounded text-[11px] transition ${
                viewDetailMode === 'NETWORK'
                  ? 'bg-purple-500/20 text-purple-300 font-medium border border-purple-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              NETWORK
            </button>
            <button
              onClick={() => setViewDetailMode('DETAIL')}
              title="Detail Mode: Full node and edge annotations"
              className={`px-2 py-1 rounded text-[11px] transition ${
                viewDetailMode === 'DETAIL'
                  ? 'bg-slate-800 text-slate-100 font-medium border border-white/[0.1]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              DETAIL
            </button>
          </div>

          {/* Expand / Collapse Controls (Only relevant on dense networks) */}
          {isDenseNetwork && (
            <div className="flex items-center gap-1 px-1.5 border-r border-white/[0.08]">
              <button
                onClick={handleExpandAll}
                title="Expand All Clusters into Real Accounts"
                className="px-1.5 py-1 text-[10px] text-slate-400 hover:text-cyan-300 hover:bg-slate-800/60 rounded transition flex items-center gap-1"
              >
                <Maximize2 className="w-3 h-3" />
                <span>EXPAND</span>
              </button>
              <button
                onClick={handleCollapseAll}
                title="Collapse All Clusters to Overview"
                className="px-1.5 py-1 text-[10px] text-slate-400 hover:text-purple-300 hover:bg-slate-800/60 rounded transition flex items-center gap-1"
              >
                <Minimize2 className="w-3 h-3" />
                <span>COLLAPSE</span>
              </button>
            </div>
          )}

          {/* Camera & Focus Subject Controls */}
          <div className="flex items-center gap-1 pl-1">
            <button
              onClick={handleFocusSubject}
              title="Focus Subject Anchor"
              className="px-2 py-1 text-[10px] text-cyan-400 hover:bg-cyan-950/40 rounded transition flex items-center gap-1 font-semibold"
            >
              <Crosshair className="w-3 h-3" />
              <span className="hidden sm:inline">SUBJECT</span>
            </button>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 rounded transition"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 rounded transition"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleReset}
              title="Reset View / Fit Graph"
              className="p-1 text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 rounded transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Selected Spotlight Indicator */}
        {selectedNode && selectedNode !== rootAccountId && (
          <div className="hidden sm:flex items-center gap-1.5 bg-cyan-950/50 border border-cyan-500/40 px-2.5 py-1.5 rounded-xl text-[10px] font-mono text-cyan-300 backdrop-blur-md shadow-lg">
            <Crosshair className="w-3 h-3 text-cyan-400" />
            <span>FOCUS: {selectedNode}</span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-slate-200 ml-1 text-xs"
            >
              &times;
            </button>
          </div>
        )}
      </div>

      {/* Top-Right: Scale Indicator & Forensic Stats Strip */}
      <div className="absolute top-3.5 right-3.5 z-10 flex items-center gap-2">
        {truncated && (
          <div className="bg-amber-950/50 border border-amber-500/30 text-amber-300 px-2.5 py-1.5 rounded-xl text-[10px] font-mono">
            Capped at {nodeLimit} nodes
          </div>
        )}
        <div className="bg-[#070a12]/90 backdrop-blur-md border border-white/[0.08] px-3.5 py-1.5 rounded-xl text-[11px] font-mono text-slate-300 flex items-center gap-3 shadow-xl">
          <div>
            <span>Nodes: </span>
            <span className="text-cyan-300 font-semibold">{nodes.length}</span>
          </div>
          <span className="text-slate-600">&bull;</span>
          <div>
            <span>Edges: </span>
            <span className="text-cyan-300 font-semibold">{edges.length}</span>
          </div>
          {isDenseNetwork && (
            <>
              <span className="text-slate-600">&bull;</span>
              <span className="text-purple-300 text-[10px] font-semibold tracking-wider">
                DENSE NETWORK
              </span>
            </>
          )}
        </div>
      </div>

      {/* Bottom-Left: Subtle Forensic Minimap Preview */}
      <div className="absolute bottom-4 left-4 z-10 hidden sm:block bg-[#070a12]/80 backdrop-blur-md border border-white/[0.08] rounded-xl p-1.5 shadow-2xl pointer-events-none">
        <canvas ref={minimapCanvasRef} width={130} height={70} className="rounded" />
        <div className="flex justify-between items-center px-1 pt-1 text-[9px] font-mono text-slate-400">
          <span>TOPOLOGY MAP</span>
          <span>{nodes.length} ACCTS</span>
        </div>
      </div>

      {/* Bottom-Right Contextual Inspector: Entity or Branch Cluster */}
      {(selectedNode || selectedCluster || selectedEdge) && (
        <div className="absolute bottom-4 right-4 z-10 w-84 sm:w-96 surface-elevated p-4 rounded-2xl shadow-2xl text-xs space-y-3 border border-white/[0.10] animate-in fade-in slide-in-from-bottom-2 duration-150">
          {/* A: Entity Inspector */}
          {selectedNode && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-cyan-400 font-medium uppercase tracking-wider">
                    ENTITY INSPECTOR
                  </span>
                  {selectedNode === rootAccountId && (
                    <span className="bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[9px] px-1.5 py-0.2 rounded font-mono font-medium">
                      SUBJECT ROOT
                    </span>
                  )}
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-slate-400 hover:text-slate-200 text-[11px] font-mono"
                >
                  Close
                </button>
              </div>

              <div className="font-mono space-y-1">
                <div className="text-base font-semibold text-slate-100 select-all">{selectedNode}</div>
                <div className="text-[11px] text-slate-400">
                  {selectedNode === rootAccountId
                    ? 'Root investigation starting entity'
                    : 'Downstream network participant'}
                </div>
              </div>

              {/* Quick Actions Grid */}
              <div className="pt-2 grid grid-cols-2 gap-1.5 font-mono text-[11px]">
                <button
                  onClick={() => navigate(`/victim/${selectedNode}`)}
                  className="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold py-1.5 px-2 rounded-lg flex items-center justify-center gap-1 transition"
                >
                  <span>Investigate</span>
                  <ArrowUpRight className="w-3 h-3" />
                </button>
                <button
                  onClick={() => navigate(`/timeline?account_id=${selectedNode}`)}
                  className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 py-1.5 px-2 rounded-lg transition text-center"
                >
                  Timeline
                </button>
                <button
                  onClick={() => navigate(`/transactions?account=${selectedNode}`)}
                  className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 py-1.5 px-2 rounded-lg transition text-center"
                >
                  Transactions
                </button>
                <button
                  onClick={() => navigate(`/account/${selectedNode}`)}
                  className="bg-slate-800/80 hover:bg-slate-700 text-slate-200 py-1.5 px-2 rounded-lg transition text-center"
                >
                  Profile
                </button>
              </div>
            </div>
          )}

          {/* B: Cluster Inspector */}
          {selectedCluster && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-purple-400 font-semibold uppercase tracking-wider">
                    DOWNSTREAM CLUSTER INSPECTOR
                  </span>
                  <span className="bg-purple-950 text-purple-300 border border-purple-500/30 text-[9px] px-1.5 py-0.2 rounded font-mono">
                    {selectedCluster.memberNodes.length} ACCOUNTS
                  </span>
                </div>
                <button
                  onClick={() => setSelectedCluster(null)}
                  className="text-slate-400 hover:text-slate-200 text-[11px] font-mono"
                >
                  Close
                </button>
              </div>

              <div className="font-mono text-[11px] space-y-1.5">
                <div>
                  <span className="text-slate-400 text-[9px] block uppercase">PARENT DISTRIBUTOR</span>
                  <span className="text-slate-200 font-semibold">{selectedCluster.parentId}</span>
                </div>
                <div className="flex justify-between">
                  <div>
                    <span className="text-slate-400 text-[9px] block uppercase">CUMULATIVE FLOW</span>
                    <span className="text-purple-300 font-semibold text-sm tabular-nums">
                      ₹{Math.round(selectedCluster.totalVolume).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[9px] block uppercase">TERMINAL SINKS</span>
                    <span className="text-rose-400 font-semibold text-sm tabular-nums">
                      {selectedCluster.terminalCount}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={() => {
                    setExpandedClusters((prev) => {
                      const next = new Set(prev);
                      next.add(selectedCluster.clusterId);
                      return next;
                    });
                    setSelectedCluster(null);
                  }}
                  className="w-full bg-purple-600 hover:bg-purple-500 text-white font-mono text-xs py-2 rounded-lg font-semibold transition flex items-center justify-center gap-1.5"
                >
                  <span>EXPAND {selectedCluster.memberNodes.length} ACCOUNTS INTO GRAPH</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* C: Flow Edge Inspector */}
          {selectedEdge && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                <span className="text-[10px] font-mono text-cyan-400 font-medium uppercase tracking-wider">
                  FLOW INSPECTOR
                </span>
                <span className="bg-slate-800 text-slate-300 border border-white/[0.06] text-[10px] px-1.5 py-0.2 rounded font-mono">
                  {selectedEdge.payment_mode}
                </span>
              </div>

              <div className="space-y-2 font-mono text-[11px]">
                <div>
                  <span className="text-slate-400 text-[9px] block uppercase">TRANSACTION ID</span>
                  <span className="text-slate-200 font-medium">{selectedEdge.transaction_id}</span>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-slate-400 text-[9px] block uppercase">FLOW AMOUNT</span>
                    <span className="text-emerald-400 font-semibold text-sm tabular-nums">
                      ₹{selectedEdge.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[9px] block uppercase">IP ADDRESS</span>
                    <span className="text-slate-300">{selectedEdge.ip_address || 'Unavailable'}</span>
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 text-[9px] block uppercase">DIRECTION</span>
                  <div className="text-slate-300 flex items-center gap-1.5 pt-0.5">
                    <span className="text-cyan-300 font-medium">{selectedEdge.source}</span>
                    <span className="text-slate-500">→</span>
                    <span className="text-purple-300 font-medium">{selectedEdge.target}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
