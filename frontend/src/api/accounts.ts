import { apiRequest } from './client';
import type { 
  AccountSearchItem, 
  AccountDetail, 
  AccountFeatures, 
  VelocityResponse, 
  MuleRiskScore,
  AccountAttributionResponse,
  AttributionTraceResponse,
  TransactionAttributionResponse,
  VictimInvestigationResponse,
  CaseFileRequest,
  CaseFileResponse,
  CaseDiaryRequest,
  CaseDiaryResponse,
  GenerateNarrativeRequest,
  LegalDraftRequest,
  LegalDraftResponse,
  LegalDraftPackage,
  MuleIntelligenceResponse
} from '../types';

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

export function getAccountRisk(accountId: string): Promise<MuleRiskScore> {
  return apiRequest<MuleRiskScore>(`/accounts/${encodeURIComponent(accountId)}/risk`);
}

export function getAccountAttribution(accountId: string, horizonSeconds?: number): Promise<AccountAttributionResponse> {
  const params = new URLSearchParams();
  if (horizonSeconds !== undefined && horizonSeconds !== null) {
    params.set('horizon_seconds', horizonSeconds.toString());
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<AccountAttributionResponse>(`/accounts/${encodeURIComponent(accountId)}/attribution${query}`);
}

export function getAccountAttributionTrace(
  accountId: string, 
  maxHops: number = 4, 
  horizonSeconds?: number, 
  rootRowId?: number
): Promise<AttributionTraceResponse> {
  const params = new URLSearchParams({ max_hops: maxHops.toString() });
  if (horizonSeconds !== undefined && horizonSeconds !== null) {
    params.set('horizon_seconds', horizonSeconds.toString());
  }
  if (rootRowId !== undefined && rootRowId !== null) {
    params.set('root_row_id', rootRowId.toString());
  }
  return apiRequest<AttributionTraceResponse>(`/accounts/${encodeURIComponent(accountId)}/attribution/trace?${params.toString()}`);
}

export function getTransactionAttribution(transactionId: string, rowId?: number): Promise<TransactionAttributionResponse> {
  const params = new URLSearchParams();
  if (rowId !== undefined && rowId !== null) {
    params.set('row_id', rowId.toString());
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<TransactionAttributionResponse>(`/transactions/${encodeURIComponent(transactionId)}/attribution${query}`);
}

export function getVictimInvestigation(
  accountId: string,
  maxHops: number = 4,
  horizonSeconds?: number,
  maxBranchesPerHop: number = 50
): Promise<VictimInvestigationResponse> {
  const params = new URLSearchParams({
    max_hops: maxHops.toString(),
    max_branches_per_hop: maxBranchesPerHop.toString()
  });
  if (horizonSeconds !== undefined && horizonSeconds !== null) {
    params.set('horizon_seconds', horizonSeconds.toString());
  }
  return apiRequest<VictimInvestigationResponse>(`/investigations/victim/${encodeURIComponent(accountId)}?${params.toString()}`);
}

export function createCaseFile(req: CaseFileRequest): Promise<CaseFileResponse> {
  return apiRequest<CaseFileResponse>('/case-files', {
    method: 'POST',
    body: JSON.stringify(req)
  });
}

export function getCaseFile(caseFileId: string): Promise<CaseFileResponse> {
  return apiRequest<CaseFileResponse>(`/case-files/${encodeURIComponent(caseFileId)}`);
}

export function createCaseDiary(req: CaseDiaryRequest): Promise<CaseDiaryResponse> {
  return apiRequest<CaseDiaryResponse>('/case-diaries', {
    method: 'POST',
    body: JSON.stringify(req)
  });
}

export function getCaseDiary(diaryId: string): Promise<CaseDiaryResponse> {
  return apiRequest<CaseDiaryResponse>(`/case-diaries/${encodeURIComponent(diaryId)}`);
}

export function generateDiaryNarrative(
  diaryId: string,
  req: GenerateNarrativeRequest = {}
): Promise<CaseDiaryResponse> {
  return apiRequest<CaseDiaryResponse>(`/case-diaries/${encodeURIComponent(diaryId)}/generate-narrative`, {
    method: 'POST',
    body: JSON.stringify(req)
  });
}

export function createLegalDraft(req: LegalDraftRequest): Promise<LegalDraftResponse> {
  return apiRequest<LegalDraftResponse>('/legal-freeze/drafts', {
    method: 'POST',
    body: JSON.stringify(req)
  });
}

export function getLegalDraft(draftId: string): Promise<LegalDraftResponse> {
  return apiRequest<LegalDraftResponse>(`/legal-freeze/drafts/${encodeURIComponent(draftId)}`);
}

export function listLegalDrafts(accountNumber?: string): Promise<LegalDraftPackage[]> {
  const params = new URLSearchParams();
  if (accountNumber) params.set('account_number', accountNumber);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<LegalDraftPackage[]>(`/legal-freeze/drafts${query}`);
}

export function getMuleIntelligence(params: {
  role?: string;
  risk_band?: string;
  velocity_only?: boolean;
  min_risk?: number;
  sort_by?: string;
  order?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<MuleIntelligenceResponse> {
  const query = new URLSearchParams();
  if (params.role) query.set('role', params.role);
  if (params.risk_band) query.set('risk_band', params.risk_band);
  if (params.velocity_only) query.set('velocity_only', 'true');
  if (params.min_risk !== undefined) query.set('min_risk', params.min_risk.toString());
  if (params.sort_by) query.set('sort_by', params.sort_by);
  if (params.order) query.set('order', params.order);
  if (params.limit !== undefined) query.set('limit', params.limit.toString());
  if (params.offset !== undefined) query.set('offset', params.offset.toString());
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return apiRequest<MuleIntelligenceResponse>(`/mules${qStr}`);
}


