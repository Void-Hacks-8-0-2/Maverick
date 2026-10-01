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

export interface RoleReason {
  code: string;
  observed_value: number;
  threshold: number;
  description: string;
}

export interface AccountFeatures {
  account_number: string;
  incoming_txn_count: number;
  outgoing_txn_count: number;
  incoming_volume: number;
  outgoing_volume: number;
  net_flow_delta: number;
  fan_in: number;
  fan_out: number;
  unique_counterparties: number;
  outflow_to_inflow_ratio: number;
  inflow_to_outflow_ratio: number;
  first_seen_timestamp: string | null;
  last_seen_timestamp: string | null;
  activity_span_seconds: number;
  active_day_count: number;
  active_hour_count: number;
  transactions_per_active_day: number;
  incoming_amount_min: number;
  incoming_amount_max: number;
  incoming_amount_mean: number;
  incoming_amount_median: number;
  incoming_amount_stddev: number;
  outgoing_amount_min: number;
  outgoing_amount_max: number;
  outgoing_amount_mean: number;
  outgoing_amount_median: number;
  outgoing_amount_stddev: number;
  unique_device_count: number;
  android_txn_count: number;
  ios_txn_count: number;
  windows_browser_txn_count: number;
  web_emulator_txn_count: number;
  linux_script_txn_count: number;
  web_emulator_ratio: number;
  linux_script_ratio: number;
  unique_ip_count: number;
  transactions_per_unique_ip: number;
  top_ip_transaction_count: number;
  top_ip_transaction_ratio: number;
  upi_txn_count: number;
  imps_txn_count: number;
  neft_txn_count: number;
  rtgs_txn_count: number;
  upi_ratio: number;
  imps_ratio: number;
  neft_ratio: number;
  rtgs_ratio: number;
  unique_narration_count: number;
  empty_narration_count: number;
  narration_repeat_ratio: number;
  unique_active_dates: number;
  unique_active_hours: number;
  night_transaction_count: number;
  night_transaction_ratio: number;
  layer1_candidate: boolean;
  layer2_candidate: boolean;
  layer3_candidate: boolean;
  layer1_reasons: RoleReason[];
  layer2_reasons: RoleReason[];
  layer3_reasons: RoleReason[];
  layer1_signal_count: number;
  layer2_signal_count: number;
  layer3_signal_count: number;
  mule_risk_index: number | null;
  risk_factors: string | null;
  cycle_indicator: boolean | null;
  pass_through_ratio: number | null;
  pass_through_event_count: number | null;
  median_incoming_to_outgoing_seconds: number | null;
  rapid_outflow_count: number | null;
  pass_through_candidate: boolean | null;
  pass_through_incoming_volume: number | null;
  pass_through_attributed_volume: number | null;
  pass_through_outgoing_transaction_count: number | null;
  pass_through_outgoing_volume: number | null;
  under_3_minute_event_count: number | null;
  over_15_minute_event_count: number | null;
  velocity_classification_version: string | null;
  velocity_classification_computed_at: string | null;
  velocity_classification_provenance: string | null;
  feature_version: string;
  computed_at: string;
  provenance: string;
  classification_version: string;
  classification_computed_at: string;
  classification_provenance: string;
}

export interface VelocityEvent {
  incoming_transaction_id: string;
  outgoing_transaction_id: string;
  incoming_timestamp: string;
  outgoing_timestamp: string;
  delay_seconds: number;
  incoming_amount: number;
  outgoing_amount: number;
  attributed_amount: number;
  window: string;
  provenance: string;
}

export interface VelocityResponse {
  account_id: string;
  event_count: number;
  qualifying_window: string;
  window_min_seconds: number;
  window_max_seconds: number;
  provenance: string;
  events: VelocityEvent[];
}
