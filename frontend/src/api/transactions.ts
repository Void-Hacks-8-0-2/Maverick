import { apiRequest } from './client';
import type { PaginatedTransactions } from '../types';

export function getAccountTransactions(
  accountId: string,
  direction: 'in' | 'out' | 'all' = 'all',
  limit: number = 50,
  offset: number = 0
): Promise<PaginatedTransactions> {
  const params = new URLSearchParams({
    direction,
    limit: limit.toString(),
    offset: offset.toString(),
  });
  return apiRequest<PaginatedTransactions>(
    `/accounts/${encodeURIComponent(accountId)}/transactions?${params.toString()}`
  );
}
