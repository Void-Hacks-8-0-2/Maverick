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
  LegalDraftPackage
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


