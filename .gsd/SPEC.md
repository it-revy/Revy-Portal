# SPEC.md — REVY Portal Phase 5 Operations & Sales Hub Specifications

> **Status**: `PROPOSED / GATED FOR IMPLEMENTATION` (CRM Sales Hub Baseline: `FINALIZED & VERIFIED`)  
> **Repository:** `Revy-Portal`  
> **Current Alembic Head:** `m0n1o2p3q4r5`  
> **Execution Stage:** `SPEC & PLAN ONLY`  
> **Strategic Two-Layer Priority:**
> 1. **Layer 1 — Immediate Priority (Sales Hub):** Six-Stage Sales Funnel (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` recommended), Quotation Management (one active quote per Opp), PI Storage Architecture (no live generation), Opportunity Outcomes (`Open`, `Won`, `Lost`), Revenue & Pipeline Reporting (grouped by currency), `PO Received` Sub-status Specification.
> 2. **Layer 2 — Future Priority (Document Only — Gated):** Operational Integration (`PO Received` $\rightarrow$ Lab Order $\rightarrow$ LMS Sample Incoming; Product Orders $\rightarrow$ IMS; Invoicing & Payments).  
> **Last Updated:** 2026-10-27

---

## 1. Executive Vision & Two-Layer Strategy

The REVY Enterprise Portal serves as the unified operational backbone for REVY Environmental Solutions. Following the stabilization of the **CRM Sales Hub** (Leads, Accounts, Contacts, Opportunities), Phase 5 is structured into two distinct layers:

1. **Layer 1 — Current Priority: Sales Hub Enhancement:**
   - Define the **Six-Stage Sales Funnel** (recommended position: `Enquiry`, `Qualify`, `Develop`, `Propose/Offer`, `Negotiate`, `Close`, pending leadership approval).
   - Implement **Quotation Management** on the Opportunity view (maintaining one active quotation per Opportunity, while preserving full revision history).
   - Prepare architecture and data requirements for future **Proforma Invoice (PI)** storage without generating live PIs now.
   - Enforce rigorous **Opportunity Outcomes** (`Open`, `Won`, `Lost`) completely distinct from pipeline stages.
   - Implement executive **Revenue & Pipeline Reporting** with commercial values grouped by currency (`Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`).
   - Define the exact Opportunity sub-status **`PO Received`** as the commercial milestone marker.

2. **Layer 2 — Future Priority: Operational Integration (Document Only — Gated):**
   - Connect a `PO Received` Opportunity to downstream workflows:
     - *Sample Testing:* Create a Lab Order and display expected samples in a future **LMS Sample Incoming** section for Lab Admin confirmation.
     - *Products:* Create product order workflows after customer PO verification.
     - *Consultancy:* Follow separately approved consultancy engagement activation and consultant assignment.
     - *Commercial Invoicing:* Formal tax invoicing, GST calculations, and payment reconciliation (gated under Phase 5D / Phase 6).
   - **Strict Scope Guardrail:** No LMS sample intake, Lab Order creation, inventory movement, invoice generation, or payment processing is authorized in the current Sales Hub scope.

---

## 2. Mandatory Preserved Baseline: Stabilized CRM Sales Hub

The following core rules are verified in production (Alembic `m0n1o2p3q4r5`, PostgreSQL CHECK constraint `ck_leads_lifecycle_status`) and must be strictly preserved:

### 2.1 Lead Status Governance
- Exactly six approved Lead lifecycle statuses:
  1. `Enquiry` (System-wide default for all new leads)
  2. `Offer`
  3. `Negotiation`
  4. `Supply`
  5. `Payment`
  6. `Dormant`
- Statuses `Open`, `Qualified`, `Disqualified`, `Won`, `Lost`, or `Closed` are **strictly prohibited** as Lead lifecycle statuses.
- Lead qualification remains completely decoupled from lifecycle status: qualifying a lead sets `is_qualified`, `qualified_at`, `qualified_by_id`, links Account, Contact, and Opportunity, and transitions the lead to a legitimate business status (`Offer`, `Negotiation`, etc.).

### 2.2 Opportunity Architecture
- **1:N Cardinality:** One Lead supports multiple Opportunities via `Opportunity.originating_lead_id`.
- **Pipeline Stage vs. Outcome Status:** Pipeline stage represents funnel progression; outcome status represents commercial disposition (`Open`, `Won`, `Lost`).
- **Free-Text `sub_status`:** `crm_opportunities.sub_status` (VARCHAR(255), nullable, editable, clearable) captures user operational notes without altering pipeline stage or lead lifecycle status.

### 2.3 Operational Safeguard Barrier
- **Strict Boundary:** Qualifying a Lead or moving an Opportunity stage is **strictly prohibited from auto-creating laboratory sample submissions, consultancy engagements, product shipments, stock movements, or invoices**.

---

## 3. Immediate Functional Scope: Sales Hub Enhancements

### 3.1 D-11 & D-14: Recommended Funnel & Closure Position (Pending Leadership Approval)

#### Recommended Opportunity Stages
The recommended canonical progression through the sales pipeline consists of six sequential stages:
1. `Enquiry` — Initial customer requirement logged and under preliminary review.
2. `Qualify` — Customer need, technical fit, and commercial viability assessed.
3. `Develop` — Solution engineered, sizing/feasibility determined, and commercial scope detailed.
4. `Propose/Offer` — Formal proposal or quotation prepared and submitted to the customer.
5. `Negotiate` — Commercial, legal, payment terms, or pricing adjustments actively negotiated.
6. `Close` — Final commitment milestone where contract execution, formal PO receipt, or commercial finalization occurs.

#### Opportunity Outcomes (Strictly Distinct from Stages)
- `Open` — Represents an active, nonterminal Opportunity progressing through the pipeline.
- `Won` — Represents an Opportunity where a binding commercial agreement or purchase order has been achieved.
- `Lost` — Represents an Opportunity that was abandoned, cancelled, or won by a competitor.

#### Closure Rules
- **Won Rule:** An Opportunity must be at the `Close` stage to be marked `Won`. Marking an Opportunity `Won` requires appropriate role permission and is audited with actor, timestamp, and close date.
- **Lost Rule:** An Opportunity may be marked `Lost` from **any approved pipeline stage** (e.g., disqualified during `Qualify`, rejected during `Propose/Offer`, or abandoned during `Negotiate`). A non-empty `loss_reason` is **mandatory**; the action is audited with actor and timestamp.
- **Open Rule:** Represents any Opportunity that has not reached a terminal outcome (`Won` or `Lost`), regardless of its current stage.

#### Architectural Conflict Analysis: Why Literal "Won / Lost" as the 6th Stage is Flawed
The earlier proposal supplied for REVY listed the six stages as `Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Won / Lost`. This creates severe architectural and operational conflicts:
1. **Conflating Funnel Progression with Disposition:** A stage describes *where the deal is in the process*; an outcome describes *how the deal concluded*. Combining them into a single sixth stage collapses these two dimensions into one ambiguous column.
2. **Forced Progression of Lost Deals:** Deals are frequently lost at early stages (e.g. failing feasibility during `Qualify`). Having `Won / Lost` as the sixth stage would either force failed deals through all intervening stages or create an artificial skip, distorting pipeline velocity analytics.
3. **Kanban Ambiguity:** A column named `Won / Lost` would display closed successful revenue deals alongside rejected deals in the same view.
4. **Closing Milestone Requirement:** Separating the 6th stage as `Close` provides a clear operational stage where contracts/POs are finalized, upon which the outcome is set to `Won`.

*Status: Option A is the recommended position pending leadership approval. It is NOT yet approved company policy.*

#### Reopening Policy (Recommended Position — Pending Approval)
- **Authority:** Restricted to `CRM_ADMIN` or `CRM_SALES_MANAGER` only.
- **Justification:** Non-empty reopening reason is mandatory.
- **Audit:** Record actor, timestamp, and justification reason in the system audit trail.
- **Reporting Impact (Unresolved):** Leadership must decide how reopening affects previously reported monthly/quarterly snapshots (e.g. whether reopening a Won deal subtracts from historical reported periods).
- *Status: Recommended; Managing Director / Head of Sales approval pending.*

### 3.2 D-12: Quotation Management (One Active Quote per Opportunity)
- **Proposed Rule:** Maintain **one active quotation per Opportunity**, while retaining full historical records of earlier revisions and superseded quotations.
- **Functional Requirements:**
  - Dedicated Quotation section on the Opportunity view.
  - Quotation documents (`PDF`/`DOCX`) uploaded using existing generic `FileMetadata` storage.
  - When a revised quotation is created, it becomes the **Active** quotation; the previous quotation is automatically marked **Superseded**, preserving its full document history, amount, and timestamp.
  - Capture quotation revision info (v1, v2), amount, currency, validity date, and status.
  - Potential statuses: `Draft`, `Internal Review`, `Shared with Client`, `Accepted`, `Superseded`, `Rejected`.
  - **Operational Boundary:** A quotation must not automatically create an order, laboratory submission, invoice, or payment record.
- **Recorded Recommendations on Sub-Decisions (Pending Leadership Approval):**
  - **D-12.1 Creation & Revision:** Assigned Sales Executives can create and revise quotations for their assigned Opportunities; Sales Managers can also create and revise. *(Status: Recommended; Head of Sales approval pending)*.
  - **D-12.2 Approval Before Sharing:** Sales Manager approval is mandatory before every quotation is shared externally with a customer. Any revised quotation must be reapproved before external sharing. *(Status: Recommended; Head of Sales / MD approval pending)*.
  - **D-12.3 Role Permissions:** Role-based permissions matrix: Assigned Sales Executive (view, download, prepare own); Sales Manager (view, download, approve, share); CRM Admin (administrative access). Audit all quotation actions. *(Status: Recommended; CRM Admin / Head of Sales approval pending)*.
  - **D-12.4 Revision History & Audit:** Maintain structured revision records, preserve all previous quotation documents, and audit creation, edits, approvals, rejections, superseding, and sharing with actor and timestamp. *(Status: Recommended; QA Lead / IT Architect review pending)*.
  - **D-12.5 Evidence of Sending:** Record sending method, recipient, date/time, quotation revision, and sending evidence. If email integration is unavailable, require manual confirmation recording sender and timestamp. *(Status: Recommended; Head of Sales approval pending)*.
  - **Remaining Quotation Details to Resolve:** Quotation identifier series, revision numbering scheme, retention period, post-edit reapproval invalidation rules, and whether CRM Admin has override powers.

### 3.3 Proforma Invoice (PI) Section — Architecture & Storage Requirements
- Architect data requirements for future PI storage associated with the Opportunity.
- **Strict Prohibition:** Do NOT generate live PI documents, invoice numbers, GST calculations, or payment records in this phase. A PI must never be treated as a tax invoice or proof of payment.

### 3.4 D-13: Opportunity Revenue Reporting Grouped by Currency
- **Proposed Rule:** Display commercial values **grouped by currency**, rather than combining amounts from different currencies into one misleading total.
- **Canonical Data Source:** [`crm_opportunities.estimated_value`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/model.py#L115) (Numeric(12, 2)), alongside `crm_opportunities.currency` (VARCHAR(10), default `'INR'`).
- **Recorded Recommendations (Pending Leadership Approval):**
  - **Multi-Currency Permissions:** All authorized CRM Sales users may select a currency from an approved list controlled by Finance / CRM Admin.
  - **Value Edits After Quotation:** Authorized users may edit Opportunity estimated value with mandatory reason and audit log; warn if estimated value differs from latest quotation; quotation itself remains unchanged unless separately revised and approved.
  - **Historical Reporting After Value Changes:** Preserve old and new values, reasons, and timestamps in audit trail. Current reports use current value; historical snapshots retain the values previously reported.
- **Proposed Summary Metrics:**
  - **Total Opportunities:** Total count of Opportunities in reporting scope.
  - **Open Opportunities:** Count of Opportunities with outcome `Open`.
  - **Won Opportunities:** Count of Opportunities with outcome `Won`.
  - **Lost Opportunities:** Count of Opportunities with outcome `Lost`.
  - **Won Opportunity Value:** Sum of estimated values for Won Opportunities, **grouped by currency**.
  - **Open Pipeline Value:** Sum of estimated values for Open Opportunities, **grouped by currency**.
  - **Lost Opportunity Value:** Sum of estimated values for Lost Opportunities, **grouped by currency**.
- **Reporting Safeguards & Currency Policy:**
  - Amounts in different currencies must **never** be added together into a single total without an approved conversion mechanism.
  - Label as `Won Opportunity Value` or `Won Commercial Value`; do NOT label as collected cash or recognized accounting revenue without an approved accounting definition.
  - If currency conversion is later required, leadership must approve exchange-rate source, rate date policy, and treatment of currency fluctuations.
  - The reporting design must define how historical snapshots are generated and retained (no snapshot engine currently exists in codebase).
- *Status: Recommended positions pending leadership approval.*

### 3.5 PO Received Sub-Status Specification
- An Opportunity can be assigned the exact sub-status `PO Received` when a client issues a formal Purchase Order.
- `PO Received` is an Opportunity sub-status, not a Lead lifecycle status or pipeline stage.
- Setting `PO Received` in Phase 5A records the commercial milestone, but must **not** trigger automatic downstream operational records until Layer 2 is explicitly authorized.

---

## 4. Preserved Deferred Scope (Future Layer 2 — Document Only)

The following operational systems and workflows are strictly **deferred from immediate implementation** and remain document-only until separately authorized:

1. **Commercial Commitment Triggers & PO Received Automation (D-01):**
   - Setting `PO Received` sub-status must NOT trigger automatic Lab Order creation, sample incoming records, or product order generation.
2. **Consultancy Activation and Assignment (D-02):**
   - Lead consultant assignment, engagement activation, and delivery milestone sign-offs remain deferred.
3. **Laboratory Requisition & Physical Sample Intake (D-03):**
   - Creation of Lab Orders and the LMS Sample Incoming section remain deferred. A sample must not be marked physically received merely because an Opportunity or requisition exists.
4. **Laboratory Approval Hierarchy & Worksheets (D-06):**
   - 3-tier approvals (Analyst $\rightarrow$ Supervisor $\rightarrow$ R&D Head), bench testing worksheets for FS, Wastewater, BMP, and SMA, and sample-out/disposal tracking remain deferred.
5. **Product Catalogue & MOQ Rules (D-07):**
   - Implementation of `ims_products` SKU Master, MOQs, base pricing, and stock movements remains deferred until the company supplies the official SKU master.
6. **Commercial Billing, Tax, & Payment Reconciliation (D-09 / D-10):**
   - Generation of tax invoices, GST/HSN calculations, payment receipts, UTR numbers, and accounting ledgers remains gated under Phase 5D.

---

## 5. Pre-Implementation Verification Gate Checklist

Before implementation begins on Phase 5A, the following checklist must be completely satisfied:
- [ ] **D-11 and D-14 have compatible, approved definitions:** Leadership officially signs off on Option A (or approved alternative) separating the 6 pipeline stages from the 3 outcomes.
- [ ] **D-12 quotation permissions and approval rules are resolved:** Sub-decisions D-12.1 through D-12.5 are answered and signed off.
- [ ] **D-13 reporting definitions are approved:** Currency-grouped reporting metrics and labeling safeguards are confirmed by finance/sales leadership.
- [ ] **Reopening rules are documented:** Policy for reopening Won/Lost Opportunities and its audit/reporting impact is approved.
- [ ] **Existing scope and database constraints have been reviewed:** Verified that no existing constraints (such as `ck_leads_lifecycle_status`) are violated.
- [ ] **Implementation has been explicitly authorized:** Written leadership authorization granted to commence Phase 5A code changes.
- [ ] **A separate implementation and test plan is approved:** Work breakdown, test cases, and rollback procedures are formally accepted.

---

## 6. Execution Stop & Implementation Lock

**EXECUTION IS STRICTLY LOCKED AT SPEC AND PLAN.**

No application code, database migrations, or live data modifications are authorized. Next implementation steps will be planned only after leadership resolves P0 blockers (D-11 and D-14) and ratifies P1 policies (D-12, D-13).

---

*SPEC.md — REVY Enterprise Portal Architecture*
