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
  role?: string;
  is_terminal?: boolean;
  x?: number;
  y?: number;
  size?: number;
  color?: string;
  label?: string;
  [key: string]: any;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  transaction_id: string;
  amount: number;
  attributed_amount?: number;
  payment_mode: string;
  narration?: string;
  ip_address?: string;
  size?: number;
  color?: string;
  [key: string]: any;
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

export interface MuleRiskReason {
  code: string;
  family: string;
  points: number;
  observed_value: any;
  threshold?: any;
  description: string;
}

export interface MuleRiskScore {
  account_number: string;
  risk_index: number;
  structural_risk_index?: number;
  behavioral_risk_index?: number;
  multi_modal_confirmation?: boolean;
  investigative_signal?: string;
  investigative_summary?: string;
  risk_band: 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH';
  risk_model_version: string;
  risk_provenance: string;
  risk_computed_at: string | null;
  risk_family_scores: Record<string, number>;
  risk_reasons: MuleRiskReason[];
  risk_disclaimer: string;
}

export interface AttributionRecord {
  attribution_id: string;
  source_row_id: number;
  source_transaction_id: string;
  source_account: string;
  intermediary_account: string;
  source_timestamp: string;
  source_amount: number;
  destination_row_id: number;
  destination_transaction_id: string;
  destination_account: string;
  destination_timestamp: string;
  destination_amount: number;
  attributed_amount: number;
  delay_seconds: number;
  hop_number: number;
  edge_type?: string;
  attribution_policy: string;
  attribution_policy_version: string;
  provenance: string;
  created_at?: string | null;
}

export interface UnallocatedOutflowRecord {
  destination_row_id: number;
  destination_transaction_id: string;
  destination_account: string;
  destination_timestamp: string;
  destination_amount: number;
  attributed_amount: number;
  unallocated_amount: number;
  reason: string;
}

export interface AccountAttributionResponse {
  account_id: string;
  policy_name: string;
  policy_version: string;
  horizon_seconds: number | null;
  total_incoming_volume: number;
  total_outgoing_volume: number;
  total_attributed_volume: number;
  total_unallocated_outflow: number;
  incoming_transaction_count: number;
  outgoing_transaction_count: number;
  attribution_edge_count: number;
  attribution_records: AttributionRecord[];
  unallocated_records: UnallocatedOutflowRecord[];
  provenance: string;
  disclaimer: string;
}

export interface TraceHopSummary {
  hop_number: number;
  sender_account: string;
  receiver_account: string;
  attributed_amount: number;
  edge_count: number;
}

export interface TraceAttributionNode {
  id: string;
  type: string;
  is_root: boolean;
  hop: number;
  inflow_attributed: number;
  outflow_attributed: number;
}

export interface AttributionTraceResponse {
  root_account: string;
  root_row_id?: number | null;
  root_transaction_id?: string | null;
  max_hops: number;
  horizon_seconds?: number | null;
  policy_name: string;
  policy_version: string;
  total_attributed_amount: number;
  total_hops_found: number;
  nodes: TraceAttributionNode[];
  edges: AttributionRecord[];
  hop_summaries: TraceHopSummary[];
  truncated: boolean;
  truncation_reason?: string | null;
  cycles_detected?: string[];
  provenance: string;
  disclaimer: string;
}

export interface TransactionAttributionResponse {
  row_id: number;
  transaction_id: string;
  account_number: string;
  direction: string;
  amount: number;
  timestamp: string;
  attributed_amount: number;
  remaining_or_unallocated_amount: number;
  matched_attributions: AttributionRecord[];
  policy_name: string;
  policy_version: string;
  disclaimer: string;
}

// -------------------------------------------------------------
// Step 6: Blind Victim Investigation Engine Interfaces
// -------------------------------------------------------------
export interface DataProvenance {
  dataset_name: string;
  dataset_rows: number;
  dataset_sha256: string;
  attribution_policy: string;
  attribution_policy_version: string;
  risk_scoring_version: string;
  velocity_classification_version: string;
  integrity_statement: string;
}

export interface VictimAccountSummary {
  account_number: string;
  first_observed_timestamp: string | null;
  last_observed_timestamp: string | null;
  observed_incoming_volume: number;
  observed_outgoing_volume: number;
  observed_net_flow_delta: number;
  incoming_transaction_count: number;
  outgoing_transaction_count: number;
  unique_counterparties: number;
  unique_ip_count: number;
  unique_device_count: number;
  payment_modes: Record<string, number>;
  associated_ifscs: string[];
  associated_ips: string[];
  account_provenance: string;
}

export interface VictimTransactionItem {
  transaction_id: string;
  row_id: number;
  sender_account: string;
  receiver_account: string;
  amount: number;
  timestamp: string;
  payment_mode: string;
  sender_ifsc: string;
  receiver_ifsc: string;
  ip_address: string;
  device_type: string | null;
  narration: string;
  direction: 'INCOMING' | 'OUTGOING';
  provenance: string;
}

export interface VictimRolesSummary {
  l1_collector_candidate: boolean;
  l2_distributor_candidate: boolean;
  l3_terminal_candidate: boolean;
  fan_in: number;
  fan_out: number;
  primary_role_label: string;
  classification_reasons: string[];
  l3_classification_signals: string[];
  provenance: string;
}

export interface VictimVelocitySummary {
  pass_through_candidate: boolean;
  pass_through_ratio: number;
  qualifying_event_count: number;
  outgoing_qualifying_count: number;
  attributed_volume: number;
  median_delay_seconds: number | null;
  rapid_outflow_count: number;
  window_description: string;
  events: any[];
  classification_version: string;
  provenance: string;
}

export interface TerminalAccountEvidence {
  account_number: string;
  hop: number;
  attributed_amount: number;
  primary_role: string;
  risk_index: number | null;
  risk_band: string | null;
  velocity_status: string | null;
  reason_codes: string[];
  provenance: string;
}

export interface InvestigationEvidenceSummary {
  subject_account: string;
  observed_activity: string;
  observed_outflow: number;
  observed_inflow: number;
  temporal_attribution_summary: string;
  max_verified_propagation: number;
  risk_summary: string;
  role_summary: string;
  velocity_summary: string;
  narrative: string;
}

export interface VictimInvestigationResponse {
  investigation_id: string;
  account_number: string;
  status: string;
  generated_at: string;
  data_provenance: DataProvenance;
  account_summary: VictimAccountSummary;
  victim_transactions: VictimTransactionItem[];
  risk: MuleRiskScore;
  roles: VictimRolesSummary;
  velocity: VictimVelocitySummary;
  trace: AttributionTraceResponse;
  terminals: TerminalAccountEvidence[];
  warnings: string[];
  evidence_summary: InvestigationEvidenceSummary;
  disclaimer: string;
}

// -------------------------------------------------------------
// Step 7: Forensic Case File & Evidence Package Interfaces
// -------------------------------------------------------------
export interface CaseFileRequest {
  account_number: string;
  investigation_id?: string | null;
  max_hops?: number;
  horizon_seconds?: number | null;
  max_branches_per_hop?: number;
  include_pdf?: boolean;
  include_json?: boolean;
}

export interface CaseFileMetadata {
  case_file_id: string;
  investigation_id: string;
  subject_account: string;
  status: string;
  created_at: string;
  source_dataset: string;
  dataset_rows: number;
  dataset_sha256: string;
  evidence_snapshot_sha256: string;
  pdf_sha256?: string | null;
  json_sha256?: string | null;
  pdf_download_url?: string | null;
  json_download_url?: string | null;
  disclaimer: string;
}

export interface ObservedFacts {
  subject_account: string;
  total_observed_incoming_volume: number;
  total_observed_outgoing_volume: number;
  observed_net_flow_delta: number;
  incoming_transaction_count: number;
  outgoing_transaction_count: number;
  unique_counterparties: number;
  unique_ip_count: number;
  unique_device_count: number;
  payment_modes_observed: string[];
  first_observed_timestamp?: string | null;
  last_observed_timestamp?: string | null;
  source_transaction_ids: string[];
  source_row_ids: number[];
  provenance: string;
}

export interface OfficialRiskBreakdown {
  risk_index: number;
  risk_band: string;
  scoring_version: string;
  family_points: Record<string, number>;
  evidence_reasons: MuleRiskReason[];
  provenance: string;
}

export interface AttributionSummary {
  root_seed_outflow: number;
  downstream_cumulative_attribution: number;
  max_hops_traversed: number;
  root_seed_edge_count: number;
  downstream_fifo_edge_count: number;
  attribution_policy: string;
  attribution_policy_version: string;
  note: string;
  provenance: string;
}

export interface InvestigationLimitations {
  dataset_observation_window: string;
  ground_truth_status: string;
  legal_nature_disclaimer: string;
  branch_limits_applied: string;
  persistence_limitation?: string;
  is_truncated: boolean;
  truncation_reasons: string[];
  cycles_detected: string[];
}

export interface EvidenceSnapshot {
  snapshot_version: string;
  subject_account: string;
  dataset_name: string;
  dataset_rows: number;
  dataset_sha256: string;
  observed_facts: ObservedFacts;
  transactions_sample: VictimTransactionItem[];
  attribution: AttributionSummary;
  trace_nodes_count: number;
  trace_edges_count: number;
  terminal_accounts: TerminalAccountEvidence[];
  official_risk: OfficialRiskBreakdown;
  velocity_profile: VictimVelocitySummary;
  mule_roles: VictimRolesSummary;
  limitations: InvestigationLimitations;
  provenance_chain: string;
}

export interface CaseFileResponse {
  metadata: CaseFileMetadata;
  evidence_snapshot: EvidenceSnapshot;
  trace: AttributionTraceResponse;
  warnings: string[];
  evidence_narrative: string;
}

// -------------------------------------------------------------
// Step 8: Case Diary + AI-Assisted Officer Narrative Interfaces
// -------------------------------------------------------------

export interface VerifiedFact {
  fact_id: string;
  category: 'SUBJECT' | 'TRANSACTION' | 'RISK' | 'ROLE' | 'VELOCITY' | 'ATTRIBUTION' | 'PROVENANCE' | string;
  code: string;
  statement: string;
  value: any;
  source_type: 'RAW' | 'DERIVED' | 'ATTRIBUTED' | 'CASE_FILE' | string;
  source_reference: string;
  confidence: 'DETERMINISTIC' | 'ANALYTICAL' | 'INFERRED' | string;
  provenance: 'VERIFIED' | 'DERIVED' | 'ATTRIBUTED' | string;
}

export interface DiaryChronologyEvent {
  event_id: string;
  event_type:
    | 'CASE_OPENED'
    | 'ROOT_TRANSACTION'
    | 'ATTRIBUTION_HOP'
    | 'VELOCITY_EVENT'
    | 'RISK_FINDING'
    | 'ROLE_FINDING'
    | 'TERMINAL_ACCOUNT'
    | 'INVESTIGATOR_NOTE'
    | 'CASE_FILE_GENERATED'
    | string;
  timestamp: string | null;
  sort_key: string;
  description: string;
  source_reference: string;
  amount: number | null;
  hop: number | null;
  sender_account: string | null;
  receiver_account: string | null;
  edge_type: string | null;
  provenance: 'VERIFIED' | 'DERIVED' | string;
}

export interface RiskFinding {
  risk_index: number;
  risk_band: string;
  scoring_version: string;
  family_contributions: Record<string, number>;
  top_reason_codes: string[];
  provenance: string;
}

export interface RoleFinding {
  l1_collector_candidate: boolean;
  l2_distributor_candidate: boolean;
  l3_terminal_candidate: boolean;
  primary_role_label: string;
  classification_reasons: string[];
  fan_in: number;
  fan_out: number;
  provenance: string;
}

export interface VelocityFinding {
  pass_through_candidate: boolean;
  pass_through_ratio: number;
  qualifying_event_count: number;
  attributed_volume: number;
  outgoing_qualifying_count: number;
  median_delay_seconds: number | null;
  window_description: string;
  classification_version: string;
  provenance: string;
}

export interface AttributionFinding {
  root_seed_outflow: number;
  downstream_cumulative_attribution: number;
  max_hops_traversed: number;
  root_seed_edge_count: number;
  downstream_fifo_edge_count: number;
  attribution_policy: string;
  attribution_policy_version: string;
  is_truncated: boolean;
  truncation_reasons: string[];
  cycles_detected: string[];
  terminal_account_count: number;
  conservation_note: string;
  provenance: string;
}

export interface DiaryFindings {
  risk: RiskFinding;
  role: RoleFinding;
  velocity: VelocityFinding;
  attribution: AttributionFinding;
  provenance: string;
}

export interface NarrativeValidationResult {
  validation_status: 'PASSED' | 'FAILED' | 'SKIPPED' | string;
  validated_at: string | null;
  checks_performed: string[];
  violations_found: string[];
  fallback_triggered: boolean;
  fallback_reason: string | null;
}

export interface NarrativeMetadata {
  narrative_version: string;
  narrative_source: 'AI_GEMINI' | 'DETERMINISTIC_FALLBACK' | string;
  ai_model: string | null;
  generated_at: string;
  input_fact_count: number;
  input_event_count: number;
  validation: NarrativeValidationResult;
  disclaimer: string;
}

export interface CaseDiary {
  case_diary_id: string;
  case_file_id: string | null;
  investigation_id: string;
  subject_account: string;
  created_at: string;
  updated_at: string;
  status: 'COMPLETED' | 'PARTIAL_EVIDENCE' | 'NARRATIVE_FAILED' | string;
  investigator_notes: string;
  evidence_snapshot_sha256: string;
  data_provenance: Record<string, any>;
  verified_facts: VerifiedFact[];
  chronology: DiaryChronologyEvent[];
  findings: DiaryFindings;
  warnings: string[];
  limitations: Record<string, any>;
  ai_narrative: string | null;
  narrative_metadata: NarrativeMetadata | null;
  persistence_note: string;
}

export interface CaseDiaryRequest {
  account_number: string;
  case_file_id?: string | null;
  max_hops?: number;
  horizon_seconds?: number | null;
  max_branches_per_hop?: number;
  generate_narrative?: boolean;
  investigator_notes?: string;
}

export interface GenerateNarrativeRequest {
  force_deterministic?: boolean;
  investigator_notes?: string | null;
}

export interface CaseDiaryResponse {
  case_diary: CaseDiary;
  generation_time_ms: number;
  disclaimer: string;
}

// -------------------------------------------------------------
// Step 9: Legal Freeze + Bank Requisition Draft Interfaces
// -------------------------------------------------------------

export type LegalDocumentType =
  | 'ACCOUNT_FREEZE_REQUEST'
  | 'RECORD_PRESERVATION_REQUEST'
  | 'BANK_INFORMATION_REQUISITION'
  | 'EVIDENCE_ANNEXURE';

export type LegalDraftStatus = 'REVIEW_REQUIRED' | 'GENERATED' | 'FINALIZED';

export interface LegalDraftRequest {
  subject_account: string;
  document_type?: LegalDocumentType;
  case_file_id?: string | null;
  case_diary_id?: string | null;
  max_hops?: number;
  horizon_seconds?: number | null;
  max_branches_per_hop?: number;
  requesting_authority?: string | null;
  officer_name?: string | null;
  officer_designation?: string | null;
  police_station?: string | null;
  case_reference?: string | null;
  incident_reference?: string | null;
  recipient_bank?: string | null;
  recipient_branch?: string | null;
  requested_action?: string | null;
  preservation_period?: string | null;
  requested_record_categories?: string[] | null;
  investigator_notes?: string | null;
  include_ai_narrative?: boolean;
}

export interface OfficerDetails {
  officer_name: string;
  officer_designation: string;
  police_station: string;
  requesting_authority: string;
  case_reference: string;
  incident_reference: string;
  recipient_bank: string;
  recipient_branch: string;
  requested_action: string;
  preservation_period: string;
  requested_record_categories: string[];
  investigator_notes: string;
}

export interface SubjectAccountLegalEvidence {
  account_number: string;
  first_observed_timestamp: string | null;
  last_observed_timestamp: string | null;
  incoming_transaction_count: number;
  outgoing_transaction_count: number;
  observed_inflow: number;
  observed_outflow: number;
  observed_net_flow_delta: number;
  unique_counterparties: number;
  unique_ip_count: number;
  unique_device_count: number;
  payment_modes: string[];
  associated_ifscs: string[];
  associated_ips: string[];
  disclaimer: string;
}

export interface VerifiedTransactionLegalItem {
  transaction_id: string;
  row_id: number;
  timestamp: string;
  sender_account: string;
  receiver_account: string;
  amount: number;
  payment_mode: string;
  sender_ifsc: string;
  receiver_ifsc: string;
  ip_address: string;
  device_type?: string | null;
  narration: string;
  direction: string;
}

export interface LegalRiskEvidence {
  risk_index: number;
  risk_band: string;
  scoring_version: string;
  family_contributions: Record<string, number>;
  reason_codes: string[];
  statement: string;
}

export interface LegalRoleEvidence {
  l1_collector_candidate: boolean;
  l2_distributor_candidate: boolean;
  l3_terminal_candidate: boolean;
  primary_role_label: string;
  classification_reasons: string[];
  fan_in: number;
  fan_out: number;
}

export interface LegalVelocityEvidence {
  pass_through_candidate: boolean;
  pass_through_ratio: number;
  qualifying_event_count: number;
  attributed_volume: number;
  outgoing_qualifying_count: number;
  median_delay_seconds: number | null;
  window_description: string;
  classification_version: string;
}

export interface LegalAttributionEvidence {
  root_seed_outflow: number;
  downstream_cumulative_attribution: number;
  max_hops_traversed: number;
  root_seed_edge_count: number;
  downstream_fifo_edge_count: number;
  terminal_accounts_count: number;
  terminal_accounts_sample: any[];
  attribution_policy: string;
  attribution_policy_version: string;
  is_truncated: boolean;
  truncation_reasons: string[];
  cycles_detected: string[];
  conservation_note: string;
}

export interface LegalEvidenceSnapshot {
  snapshot_version: string;
  subject_account: SubjectAccountLegalEvidence;
  transactions_sample: VerifiedTransactionLegalItem[];
  risk: LegalRiskEvidence;
  roles: LegalRoleEvidence;
  velocity: LegalVelocityEvidence;
  attribution: LegalAttributionEvidence;
  case_file_id: string | null;
  case_diary_id: string | null;
  dataset_name: string;
  dataset_rows: number;
  dataset_sha256: string;
  evidence_snapshot_sha256: string;
  provenance_chain: string;
}

export interface LegalDraftDocumentSection {
  id: string;
  heading: string;
  content: string;
}

export interface LegalDraftDocument {
  title: string;
  document_type: LegalDocumentType;
  header_notice: string;
  draft_notice: string;
  sections: LegalDraftDocumentSection[];
  plain_text_content: string;
}

export interface LegalDraftPackage {
  package_id: string;
  document_type: LegalDocumentType;
  subject_account: string;
  case_file_id: string | null;
  case_diary_id: string | null;
  investigation_id: string;
  created_at: string;
  status: LegalDraftStatus;
  officer_details: OfficerDetails;
  evidence: LegalEvidenceSnapshot;
  document: LegalDraftDocument;
  evidence_snapshot_sha256: string;
  pdf_sha256: string | null;
  json_sha256: string;
  download_urls: {
    pdf: string;
    json: string;
  };
  draft_disclaimer: string;
  persistence_note: string;
}

export interface LegalDraftResponse {
  draft: LegalDraftPackage;
  generation_time_ms: number;
  disclaimer: string;
}

export interface MuleCandidateItem {
  account_number: string;
  risk_index: number;
  structural_risk_index?: number;
  behavioral_risk_index?: number;
  risk_band: 'LOW' | 'MODERATE' | 'HIGH' | 'VERY_HIGH' | string;
  investigative_signal?: string;
  multi_modal_confirmation?: boolean;
  layer1_candidate: boolean;
  layer2_candidate: boolean;
  layer3_candidate: boolean;
  pass_through_candidate: boolean;
  pass_through_ratio: number | null;
  incoming_volume: number;
  outgoing_volume: number;
  net_flow_delta: number;
  fan_in: number;
  fan_out: number;
  transaction_count: number;
}

export interface MuleIntelligenceSummary {
  total_accounts: number;
  l1_count: number;
  l2_count: number;
  l3_count: number;
  high_risk_count: number;
  velocity_count: number;
}

export interface MuleIntelligenceResponse {
  summary: MuleIntelligenceSummary;
  total_count: number;
  limit: number;
  offset: number;
  items: MuleCandidateItem[];
}
