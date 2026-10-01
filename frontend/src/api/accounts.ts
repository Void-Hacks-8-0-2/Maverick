import { apiRequest } from './client';
import type { AccountSearchItem, AccountDetail, AccountFeatures, VelocityResponse } from '../types';

export function searchAccounts(q: string, limit: number = 20): Promise<AccountSearchItem[]> {
  const params = new URLSearchParams({ q, limit: limit.toString() });
  return apiRequest<AccountSearchItem[]>(`/accounts/search?${params.toString()}`);
}

export function getAccountDetail(accountId: string): Promise<AccountDetail> {
  return apiRequest<AccountDetail>(`/accounts/${encodeURIComponent(accountId)}`);
}

export function getAccountFeatures(accountId: string): Promise<AccountFeatures> {
  return apiRequest<AccountFeatures>(`/accounts/${encodeURIComponent(accountId)}/features`);
}

export function getAccountVelocity(accountId: string): Promise<VelocityResponse> {
  return apiRequest<VelocityResponse>(`/accounts/${encodeURIComponent(accountId)}/velocity`);
}
