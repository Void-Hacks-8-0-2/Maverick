import { apiRequest } from './client';
import type { GraphData, TraceData } from '../types';

export function getAccountGraph(
  accountId: string,
  maxHops: number = 1,
  maxNodes: number = 500
): Promise<GraphData> {
  const params = new URLSearchParams({
    max_hops: maxHops.toString(),
    max_nodes: maxNodes.toString(),
  });
  return apiRequest<GraphData>(
    `/accounts/${encodeURIComponent(accountId)}/graph?${params.toString()}`
  );
}

export function getAccountTrace(
  accountId: string,
  maxNodes: number = 1000
): Promise<TraceData> {
  const params = new URLSearchParams({
    max_nodes: maxNodes.toString(),
  });
  return apiRequest<TraceData>(
    `/accounts/${encodeURIComponent(accountId)}/trace?${params.toString()}`
  );
}
