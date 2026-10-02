# OPERATION "ABHEDYA-CHAKRA" — LIVE HACKATHON DEMO FLOW

This is an operational demonstration guide designed for a 6–8 minute high-level technical presentation of the Abhedya-Chakra Financial Cyber-Forensics Platform.

---

### DEMO FLOW SUMMARY TABLE

| Stage | Screen / Route | Focus Area | Key Takeaway | Duration |
| :--- | :--- | :--- | :--- | :--- |
| **1. Command Center** | `/` | 15-Day Dataset Overview | 2M rows ingested, sub-10ms analytics over 24,873 accounts | 30s |
| **2. Account Lookup** | `/` → `/victim` | Quick Jump (`KKBK10000402`) | Instant blind intake from victim complaint | 20s |
| **3. Victim Investigation** | `/victim/KKBK10000402` | Executive Evidence Summary | Rapid extraction of observed flow & attribution | 40s |
| **4. Mule Risk Scoring** | `/victim` (Risk Tab) | 6-Family Mule Risk Index | Multi-factor risk breakdown (70/100 HIGH) | 40s |
| **5. Velocity Detection** | `/victim` (Velocity Tab) | 3–15 Min Rapid Pass-Through | Deterministic paired events showing money laundering speed | 45s |
| **6. Topology & Graph** | `/graph?account=KKBK10000402` | Sigma.js Multi-Hop Canvas | Visual separation of structural vs attribution edges | 45s |
| **7. 4-Hop Attribution** | `/victim` (Attribution Tab) | Strict FIFO Conservation | Exact tracking of root seed money across 4 hops | 45s |
| **8. Forensic Timeline** | `/timeline?account_id=...` | Chronological Event Stream | Temporal alignment of transactions, velocity, & alerts | 40s |
| **9. Transaction Explorer** | `/transactions` | High-Density Audit Table | Row-level forensic details, duplicate ID detection | 35s |
| **10. Evidence Case File** | `/case-file` | Sealed Package & PDF | Cryptographic SHA-256 seal of atomic evidence | 40s |
| **11. Case Diary & AI** | `/diary` | Verified Facts & Narrative | AI narrative strictly downstream of atomic facts | 45s |
| **12. Legal Freeze Order** | `/legal-freeze` | Draft Requisition Generator | Formal draft notices under Section 91/102 CrPC (Draft Only) | 40s |

---

## STEP-BY-STEP OPERATIONAL GUIDE

### 1. COMMAND CENTER (`/`)
- **Action**: Presenter starts on the home screen.
- **Show**: 2M transactions verified indicator, 15-day observation metrics, 24,873 accounts, distribution of L1, L2, L3 mule candidates.
- **Talking Point**: "Abhedya-Chakra processes full production-scale banking datasets locally with zero external leaks and sub-10ms analytical queries."

### 2. ENTER VICTIM ACCOUNT
- **Action**: Type `KKBK10000402` into the Command Center search bar or click the benchmark accelerator chip.
- **Show**: Immediate navigation to the Victim Investigation module.
- **Talking Point**: "From a first-information report (FIR) or victim complaint, the investigator enters the compromised account."

### 3. VICTIM INVESTIGATION (`/victim/KKBK10000402`)
- **Action**: Review the 4 Top KPI cards and Executive Evidence Summary.
- **Show**: Inflow (₹4.73L), Outflow (₹4.86L), Net Flow Delta (-₹12.8K), and Attributed Volume across hops.
- **Talking Point**: "The platform instantly calculates deterministic inflows, outflows, and net flow deltas without making unverified assumptions about overall bank balances."

### 4. MULE RISK EVALUATION
- **Action**: Switch to the "Risk & Velocity" tab.
- **Show**: Mule Risk Index score (70.0/100, HIGH Risk Band) and point contributions across the 6 families (Flow Structure, Velocity, Automation, Network Structure, Transaction Behavior, Role Support).
- **Talking Point**: "The score is not a black-box LLM hallucination—it is an explainable, deterministic mathematical index grounded in verifiable features."

### 5. 3–15 MINUTE PASS-THROUGH VELOCITY
- **Action**: Scroll to the Velocity diagnostic section.
- **Show**: Paired qualifying events showing funds received and dispatched within 3 to 15 minutes.
- **Talking Point**: "Rapid pass-through detection catches automated and mule-assisted layering where funds are dumped within minutes of arrival."

### 6. INVESTIGATION GRAPH (`/graph`)
- **Action**: Click "View Network" or navigate to `/graph?account=KKBK10000402`.
- **Show**: High-performance Sigma.js webGL graph. Zoom in, click an intermediary node, view the Inspector Drawer, and demonstrate the `Investigate` and `Timeline` actions.
- **Talking Point**: "Graphology and Sigma render complete 4-hop subgraphs with zero lag. Investigators can inspect individual nodes and jump seamlessly between topological and temporal views."

### 7. 4-HOP FIFO ATTRIBUTION
- **Action**: Return to `/victim` and view the "Terminal Accounts" section.
- **Show**: Downstream terminal recipient accounts identified at Hop 2, Hop 3, and Hop 4, along with exact attributed amounts.
- **Talking Point**: "Strict FIFO attribution guarantees money conservation—funds attributed to downstream accounts cannot exceed the victim's original outbound transfer."

### 8. FORENSIC TIMELINE (`/timeline`)
- **Action**: Open `/timeline?account_id=KKBK10000402`.
- **Show**: Chronological timeline filtering by event types (Transactions, Velocity, FIFO Attribution, Risk). Click an event to expand atomic details.
- **Talking Point**: "Investigators see a coherent 15-day narrative of what happened, down to the second, highlighting velocity bursts and attribution milestones."

### 9. TRANSACTION EXPLORER (`/transactions`)
- **Action**: Navigate to `/transactions`. Search or filter by account or amount.
- **Show**: High-density transaction table. Click a row to open the slide-over Transaction Detail Drawer showing stable source row identities and duplicate transaction notices.
- **Talking Point**: "Every transaction is tied to an immutable source row ID, device footprint, and IP address."

### 10. FORENSIC CASE FILE (`/case-file`)
- **Action**: Navigate to `/case-file` (or click "Create Case File" from Victim Investigation).
- **Show**: Evidence snapshot SHA-256 seal, PDF report download, package JSON download, and atomic observed facts.
- **Talking Point**: "Evidence is bundled into an immutable, cryptographically sealed case file ready for preservation and judicial submission."

### 11. CASE DIARY & AI-ASSISTED NARRATIVE (`/diary`)
- **Action**: Navigate to `/diary?account=KKBK10000402`.
- **Show**: Court-ready chronology, atomic verified facts categorized by domain, and the AI-assisted officer narrative with the prominent disclaimer: `AI-ASSISTED NARRATIVE GENERATED FROM VERIFIED FACTS`.
- **Talking Point**: "AI is strictly used downstream to draft officer narratives from verified facts—it never invents evidence, calculates risk, or adjudicates guilt."

### 12. LEGAL FREEZE DRAFT GENERATOR (`/legal-freeze`)
- **Action**: Navigate to `/legal-freeze?account=KKBK10000402`.
- **Show**: Account Freeze Request draft template, Officer details, Bank Nodal details, and the top disclaimer: `DRAFT DOCUMENT — SUBJECT TO INVESTIGATOR AND LEGAL AUTHORITY REVIEW`.
- **Talking Point**: "The system generates ready-to-sign statutory draft notices for bank nodal officers, closing the loop from complaint intake to asset preservation."
