---
milestone: phase-5-operations
version: 1.3.0
updated: 2026-10-27T11:46:00+05:30
current_status: scoping-complete
immediate_priority: sales-hub-opportunity-lifecycle
future_priority: operational-integration-document-only
implementation_authorization: not-granted
gate_status: pre-implementation-gate-locked
---

# Roadmap — REVY Portal Phase 5 Operations & Sales Hub

> **Milestone Strategy:** Structured into two sequential priorities:  
> 1. **Immediate Implementation Priority (Sales Hub):** Six-Stage Sales Funnel (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` recommended), Quotation Management (one active quote per Opp), PI Storage Architecture, Opportunity Outcomes (`Open`, `Won`, `Lost`), Revenue & Pipeline Reporting (grouped by currency).  
> 2. **Future Operational Integration (Document Only):** PO Received Trigger, Lab Orders, LMS Sample Incoming, Product Orders, Inventory Movements, and Billing.  
> **Governance:** Pre-Implementation Gating (SPEC & PLAN Phase Complete; Implementation strictly locked until authorized).

---

## Completed Baseline Milestones

- [x] **Sales Hub & Opportunities Stabilization:**
  - 6 approved Lead statuses (`Enquiry`, `Offer`, `Negotiation`, `Supply`, `Payment`, `Dormant`) with `Enquiry` as default.
  - PostgreSQL CHECK constraint `ck_leads_lifecycle_status` actively enforced on Neon.
  - Opportunity 1:N cardinality, 4 pipeline stages, outcome statuses, and free-text `sub_status`.
  - Lead qualification decoupled from lifecycle status.
  - Gate 3 Remediation applied safely (`m0n1o2p3q4r5`). 42/42 regression tests passing. Clean Vite build (1,993 modules).

---

## Phase 5 Implementation Phases

### Phase 5A: Sales Hub & Opportunity Lifecycle Enhancement (Immediate Priority)
- **Status:** 📋 Ready for Planning Sign-Off (**Gated on P0 Blockers: D-11, D-14; P1 Blockers: D-12, D-13**)
- **Objective:** Modernize the Opportunity lifecycle with a verified six-stage funnel, a dedicated Quotation section (one active quote per Opportunity), architecture requirements for future Proforma Invoices (PI), Opportunity outcomes (`Open`, `Won`, `Lost`), revenue visibility metrics grouped by currency, and `PO Received` sub-status specification.
- **Key Deliverables:**
  - **Six-Stage Sales Funnel (D-11 - P0 Blocker):** Ratify recommended position: `Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` with separate `Open`, `Won`, `Lost` outcomes. Map existing 4 stages (`Qualify`, `Develop`, `Propose`, `Close`) cleanly to the 6 stages without loss of historical stage data.
  - **Quotation Section (D-12 - P1 Blocker):** Dedicated Opportunity section maintaining **one active quotation per Opportunity** while preserving full revision history. File uploads via `FileMetadata`. Resolve sub-decisions D-12.1 through D-12.5 (creation authority, external sharing approvals, role permissions, versioning tracking).
  - **Proforma Invoice (PI) Architecture:** Data schema and document attachment specification for future PI storage (no live generation or numbering in this phase).
  - **PO Received Sub-status:** Formalize `PO Received` as an Opportunity sub-status for commercial commitment tracking (without triggering premature operational dispatch).
  - **Revenue & Outcome Analytics (D-13 - P1 Blocker):** Executive dashboard metrics **grouped by currency**: Total Opportunities, Open, Won, Lost, `Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`.
  - **Closure & Reopening Workflow (D-14 - P0 Blocker):** Enforce mandatory `loss_reason` on `Lost` opportunities; Won requires `Close` stage; define reopening authority.
- **Prerequisites:** Leadership sign-off on P0 blockers (D-11, D-14) and P1 policies (D-12, D-13).
- **Risks:** Conflating Won Opportunity commercial value with accounting cash collections; breaking existing Opportunity Kanban view during 6-stage migration.
- **Testing Requirements:** Stage transition tests, quotation attachment tests, currency-grouped revenue summation tests, regression tests on existing 41 Leads and 15 Opportunities.
- **Exit Criteria:** Six-stage funnel operational; Quotation section functioning with one active quote per Opp; summary revenue metrics reporting accurately grouped by currency; 100% regression tests passing.

---

### Phase 5B: Laboratory & LIMS Commercial Handoff (Future Priority — Document Only)
- **Status:** ⏸️ Deferred from Immediate Scope (Gated on Decisions D-01, D-03, D-06)
- **Objective:** Transition an Opportunity with requirement `Sample Testing` and verified `PO Received` sub-status into an authorized Lab Order, displaying expected samples in a dedicated **LMS Sample Incoming** section.
- **Key Deliverables (Future):**
  - Lab Order generation from verified `PO Received` Opportunities.
  - LMS Sample Incoming view visible to Lab Admin and Lab Supervisor.
  - Physical sample receipt confirmation by Lab Admin (barcoded `SMP-xxxxx`, storage temp, condition).
  - Bench parameter testing worksheets for Faecal Sludge (FS), Wastewater Treatment (WWT), BMP Analysis, and SMA Analysis.
  - 3-tier approval hierarchy ($\text{Analyst} \rightarrow \text{Supervisor} \rightarrow \text{R\&D Head} \rightarrow \text{Lab Admin Dispatch}$).
  - Sample-out and bio-disposal tracking.
- **Prerequisites:** Phase 5A complete; Decisions D-01, D-03, D-06 approved.
- **Scope Restriction:** Strictly deferred. No LMS code, tables, or endpoints to be built in the immediate Sales Hub phase.

---

### Phase 5C: Product Orders & Inventory Management (Future Priority — Document Only)
- **Status:** ⏸️ Deferred from Immediate Scope (Gated on Decisions D-01, D-07)
- **Objective:** Establish master product catalogue (`ims_products`), enforce customer purchase order (PO) verification, support repeat orders, and track stock allocation and dispatch.
- **Key Deliverables (Future):**
  - Canonical `ims_products` SKU Master (official SKUs, UoM, MOQ, base pricing supplied by leadership).
  - Customer purchase order verification workflow on `crm_product_orders` (`customer_po_number`, PO document upload, verification flag).
  - Repeat order quick-create workflow for existing Accounts.
  - Inventory movement ledger and dispatch challan logging.
- **Prerequisites:** Phase 5B complete; official SKU master and MOQ values provided (Decision D-07).
- **Scope Restriction:** Strictly deferred. No product ordering or inventory movement code to be built now.

---

### Phase 5D: Commercial Billing and Payments (Explicitly Gated)
- **Status:** ⏸️ Gated Pending Business Policy Approval (Decisions D-09, D-10)
- **Objective:** Implement tax invoices, statutory GST calculations, payment receipts, UTR reconciliation, and receivables tracking.
- **Key Deliverables (Future):**
  - Invoicing tables (`billing_invoices`, `billing_invoice_items`, `billing_payments`, `billing_payment_allocations`).
  - Invoice PDF generator with consecutive statutory series.
  - Payment recording and receipt generation.
- **Prerequisites:** Formal written specification of tax structures, HSN/SAC codes, and invoice numbering from Finance Leadership.
- **Scope Restriction:** Gated and excluded from current scope.

---

### Phase 5E: Cross-Module Integration, Hardening & Release Verification
- **Status:** 📋 Scoped (Final Release Gate)
- **Objective:** Validate end-to-end user journeys; execute isolated database migration upgrade/downgrade verification; perform comprehensive browser UI verification.
- **Key Deliverables:**
  - End-to-end integration test suite.
  - Isolated migration rehearsal and verification report.
  - Final Release Gate audit report (`docs/phase5/PHASE5_RELEASE_REPORT.md`).
- **Exit Criteria:** All regression suites pass; clean production build; zero unverified business rules; release gate signed off.

---

## Pre-Implementation Verification Gate Checklist

Before implementation begins on Phase 5A, the following checklist must be completely satisfied:
- [ ] **D-11 and D-14 have compatible, approved definitions:** Leadership signs off on Option A (`Enquiry`, `Qualify`, `Develop`, `Propose/Offer`, `Negotiate`, `Close` with separate `Open`, `Won`, `Lost` outcomes).
- [ ] **D-12 quotation permissions and approval rules are resolved:** Sub-decisions D-12.1 through D-12.5 are approved.
- [ ] **D-13 reporting definitions are approved:** Currency-grouped reporting metrics and labeling safeguards are confirmed by finance/sales leadership.
- [ ] **Reopening rules are documented:** Policy for reopening Won/Lost Opportunities and its audit/reporting impact is approved.
- [ ] **Existing scope and database constraints have been reviewed:** Verified that no existing constraints (such as `ck_leads_lifecycle_status`) are violated.
- [ ] **Implementation has been explicitly authorized:** Written leadership authorization granted to commence Phase 5A code changes.
- [ ] **A separate implementation and test plan is approved:** Work breakdown, test cases, and rollback procedures are formally accepted.

---

## Phase Progress Summary

| Phase | Description | Priority Layer | Status | Prerequisites | Exit Criteria Met |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **Baseline** | Sales Hub Stabilization & Gate 3 Remediation | Baseline | ✅ Complete | None | Yes (42/42 tests pass) |
| **5A** | Sales Hub & Opportunity Lifecycle Enhancement | **Layer 1 (Immediate)** | 📋 Ready | **D-11, D-14 (P0); D-12, D-13 (P1)** | Pending Sign-Off |
| **5B** | Laboratory & LIMS Commercial Handoff | Layer 2 (Future) | ⏸️ Deferred | D-01, D-03, D-06 | Document Only |
| **5C** | Product Orders & Inventory | Layer 2 (Future) | ⏸️ Deferred | D-01, D-07 | Document Only |
| **5D** | Billing & Invoicing (Gated) | Layer 2 (Future) | ⏸️ Gated | D-09, D-10 | Gated |
| **5E** | Cross-Module Hardening & Release | Layer 2 (Future) | 📋 Scoped | 5A, 5B, 5C | Pending Execution |

---

*Phase 5 Implementation Roadmap — GSD Web Profile*
