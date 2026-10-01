export interface DatasetSummary {
  row_count: number;
  unique_accounts: number;
  unique_transactions: number;
  payment_modes: Record<string, number>;
  total_amount: number;
  timestamp_available: boolean;
  device_type_available: boolean;
  source_type: string;
}

export interface AccountSearchItem {
  account: string;
  inbound_transaction_count: number;
  outbound_transaction_count: number;
  observed_inflow: number;
  observed_outflow: number;
  dataset_observed_net_movement: number;
}

export interface AccountDetail {
  account_id: string;
  inbound_transaction_count: number;
  outbound_transaction_count: number;
  unique_senders: number;
  unique_receivers: number;
  observed_inflow: number;
  observed_outflow: number;
  dataset_observed_net_movement: number;
  payment_mode_distribution: Record<string, number>;
  associated_ifscs: string[];
  associated_ips: string[];
}

export interface TransactionItem {
  Transaction_ID: string;
  Sender_Account: string;
  Receiver_Account: string;
  Sender_IFSC: string;
  Receiver_IFSC: string;
  Amount: number;
  Timestamp: string | null;
  Payment_Mode: string;
  Narration: string;
  IP_Address: string;
  Device_Type: string | null;
}

export interface PaginatedTransactions {
  account_id: string;
  direction: 'in' | 'out' | 'all';
  total_count: number;
  limit: number;
  offset: number;
  items: TransactionItem[];
}

export interface GraphNode {
  id: string;
  type: string;
  is_root?: boolean;
  hop?: number;
  x?: number;
  y?: number;
  size?: number;
  color?: string;
  label?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  transaction_id: string;
  amount: number;
  payment_mode: string;
  narration?: string;
  ip_address?: string;
  size?: number;
  color?: string;
}

export interface GraphData {
  root_account: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
  node_limit: number;
}

export interface TraceData {
  root_account: string;
  max_hops: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  paths: string[][];
  truncated: boolean;
  node_limit: number;
}
