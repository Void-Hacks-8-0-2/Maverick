/**
 * Step 10 — Transaction Explorer & Timeline Investigation API clients.
 * All filtering, sorting and pagination happens server-side via DuckDB.
 */
import { apiRequest } from './client';

// ─── Transaction Explorer ────────────────────────────────────────────────────

export interface ForensicTransactionItem {
  stable_id: string;
  row_id: number;
  Transaction_ID: string;
  Sender_Account: string;
  Receiver_Account: string;
  Sender_IFSC: string;
  Receiver_IFSC: string;
  Amount: number;
  Timestamp: string;
  Payment_Mode: string;
  Narration: string;
  IP_Address: string;
  Device_Type: string;
  is_duplicate_tx_id: boolean;
}

export interface TransactionExplorerResponse {
  items: ForensicTransactionItem[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  provenance: {
    source: string;
    provenance: string;
    disclaimer: string;
  };
}

export interface TransactionDetailResponse {
  transaction: ForensicTransactionItem;
  investigation_links: Record<string, unknown>;
  provenance: { source: string; provenance: string; disclaimer: string };
}

export interface TransactionExplorerParams {
  transaction_id?: string;
  account_id?: string;
  sender_account?: string;
  receiver_account?: string;
  min_amount?: number;
  max_amount?: number;
  start_time?: string;
  end_time?: string;
  payment_mode?: string;
  device_type?: string;
  ip_address?: string;
  narration?: string;
  sender_ifsc?: string;
  receiver_ifsc?: string;
  sort_by?: 'timestamp' | 'amount' | 'transaction_id';
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export function queryTransactionsExplorer(
  params: TransactionExplorerParams
): Promise<TransactionExplorerResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      qs.set(k, String(v));
    }
  });
  return apiRequest<TransactionExplorerResponse>(`/transactions?${qs.toString()}`);
}

export function getTransactionDetail(
  stableId: string
): Promise<TransactionDetailResponse> {
  return apiRequest<TransactionDetailResponse>(
    `/transactions/${encodeURIComponent(stableId)}`
  );
}

// ─── Timeline Investigation ──────────────────────────────────────────────────

export type TimelineEventType =
  | 'TRANSACTION'
  | 'VELOCITY'
  | 'ATTRIBUTION'
  | 'RISK_ROLE'
  | 'TERMINAL';

export interface TimelineEvent {
  event_id: string;
  event_type: TimelineEventType;
  timestamp: string;
  title: string;
  description: string;
  amount?: number;
  direction?: string;
  source_account?: string;
  destination_account?: string;
  transaction_id?: string;
  source_row_id?: number;
  payment_mode?: string;
  device_type?: string;
  ip_address?: string;
  sender_ifsc?: string;
  receiver_ifsc?: string;
  narration?: string;
  details: Record<string, unknown>;
}

export interface TimelineSummary {
  total_events: number;
  transaction_count: number;
  incoming_volume: number;
  outgoing_volume: number;
  net_volume: number;
  velocity_event_count: number;
  attribution_event_count: number;
  terminal_event_count: number;
  risk_role_findings?: Record<string, unknown> | null;
}

export interface TimelineResponse {
  account_id?: string;
  range: {
    start_time: string;
    end_time: string;
    dataset_min_time: string;
    dataset_max_time: string;
  };
  summary: TimelineSummary;
  events: TimelineEvent[];
  page: number;
  page_size: number;
  total_events: number;
  has_more: boolean;
  provenance: {
    source: string;
    provenance: string;
    step: string;
    disclaimer: string;
  };
}

export interface TimelineParams {
  account_id?: string;
  start_time?: string;
  end_time?: string;
  direction?: 'all' | 'in' | 'out';
  payment_mode?: string;
  device_type?: string;
  event_type?: string;
  page?: number;
  page_size?: number;
}

export function getTimeline(params: TimelineParams): Promise<TimelineResponse> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '' && v !== 'all') {
      qs.set(k, String(v));
    }
  });
  return apiRequest<TimelineResponse>(`/timeline?${qs.toString()}`);
}
