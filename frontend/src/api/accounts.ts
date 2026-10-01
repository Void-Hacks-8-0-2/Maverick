import { apiRequest } from './client';
import type { AccountSearchItem, AccountDetail } from '../types';

export function searchAccounts(q: string, limit: number = 20): Promise<AccountSearchItem[]> {
  const params = new URLSearchParams({ q, limit: limit.toString() });
  return apiRequest<AccountSearchItem[]>(`/accounts/search?${params.toString()}`);
}

export function getAccountDetail(accountId: string): Promise<AccountDetail> {
  return apiRequest<AccountDetail>(`/accounts/${encodeURIComponent(accountId)}`);
}
