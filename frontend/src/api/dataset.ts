import { apiRequest } from './client';
import type { DatasetSummary } from '../types';

export function getHealth(): Promise<{ status: string; service: string }> {
  return apiRequest<{ status: string; service: string }>('/health');
}

export function getDatasetSummary(): Promise<DatasetSummary> {
  return apiRequest<DatasetSummary>('/dataset/summary');
}
