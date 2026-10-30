# PHASE 5 SCOPING & DISCOVERY REPORT

> **Project:** REVY Enterprise Portal  
> **Repository:** `Revy-Portal`  
> **Auditors:** Senior Software Architect, Database Architect, Business Analyst, QA Lead  
> **Date:** 27 October 2026  
> **Status:** Discovery & Scoping Completed (SPEC & PLAN Phase Complete)  
> **Strategic Two-Layer Focus:**  
> 1. **Immediate Scope (Phase 5A):** Sales Hub & Opportunity Lifecycle Enhancement  
> 2. **Future Scope (Phases 5B–5E):** Operational Integration (Document Only)  
> **Implementation Status:** **NOT STARTED — STRICTLY GATED**

---

## 1. Executive Summary

This scoping report presents the technical discovery, repository audit, and implementation planning for **Phase 5 Operations and Sales Hub Enhancements** of the REVY Enterprise Portal.

Following the completion of CRM Sales Hub Stabilization and Gate 3 Remediation (Option A), the baseline repository was verified as 100% clean:
- **Alembic Head:** `m0n1o2p3q4r5` (enforcing PostgreSQL CHECK constraint `ck_leads_lifecycle_status` on Neon).
- **Lead Status Conformance:** 41 Leads on Neon (28 Enquiry, 11 Negotiation, 2 Supply, 0 Open/unapproved). Zero records deleted.
- **Backend Regression Suite:** 42 / 42 passed (100% success in 54.56s).
- **Frontend Production Build:** Vite build cleanly succeeded in 254ms (1,993 modules transformed, 0 errors).

### Executive Two-Layer Prioritization
In accordance with the Executive Decision Record ([`docs/phase5/PHASE5_DECISION_REGISTER.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_DECISION_REGISTER.md)), Phase 5 is structured into two distinct layers:

1. **Current Priority — Sales Hub Enhancement (Phase 5A):**
   - **Six-Stage Funnel (D-11 & D-14):** Recommended position: `Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close`, with separate `Open`, `Won`, `Lost` outcomes (pending leadership approval).
   - **Quotation Management (D-12):** Maintain **one active quotation per Opportunity**, while retaining full revision history. Sub-decisions on creation/approval authority identified with owners.
   - **PI Storage Architecture:** Data requirements for future Proforma Invoices (PI) without generating live PIs now.
   - **Revenue Reporting (D-13):** Display commercial values **grouped by currency** (`Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`).
   - **Milestone Marker:** Formalize `PO Received` as an Opportunity sub-status without operational automation.

2. **Future Priority — Operational Integration (Document Only — Gated):**
   - Connecting `PO Received` Opportunities to downstream operational workflows (Sample Testing $\rightarrow$ Lab Orders $\rightarrow$ LMS Sample Incoming; Products $\rightarrow$ Product Orders $\rightarrow$ IMS stock movements; Consultancy delivery; Billing).
   - **Strict Scope Boundary:** No LMS sample intake, Lab Order creation, inventory movement, invoice generation, or payment processing is authorized in the current Sales Hub scope.

---

## 2. Key Technical Findings & Decision Resolutions

1. **Task 1 — Funnel & Closure Resolution (D-11 & D-14):**
   - Proposed stages: `Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close`.
   - Proposed outcomes: `Open`, `Won`, `Lost` (orthogonal to stages).
   - Won requires the Opportunity to be at `Close`. Lost permitted from any stage with mandatory `loss_reason`.
   - **Conflict Resolved:** Earlier proposal of "Won / Lost" as the 6th stage conflates funnel progression with terminal disposition and forces early lost deals through late stages.
   - Status: Recommended position pending approval; NOT silently treated as approved.
2. **Task 2 — Quotation Policy Clarified (D-12):**
   - One active quotation per Opportunity, retaining historical records.
   - Sub-decisions D-12.1 through D-12.5 listed with decision owners.
   - Architecture requirements for future PI storage prepared without live generation.
3. **Task 3 — Commercial Reporting Clarified (D-13):**
   - Group Opportunity values by currency.
   - Canonical field: `crm_opportunities.estimated_value`.
   - Distinguish Open, Won, and Lost.
   - Values in different currencies must NOT be added together into a single total.
   - Won Opportunity value must NOT be labeled as collected cash or accounting revenue.
   - Currency conversion prerequisites documented.
4. **Task 5 — Preserved Deferred Scope:**
   - Commercial commitment triggers, PO Received automation, consultancy activation/assignment, laboratory requisition/intake, 3-tier approvals, SKU master, and formal billing strictly deferred from immediate implementation.

---

## 3. Remaining Blockers & Pre-Implementation Gate Checklist

Before implementation begins on Phase 5A, the following checklist must be satisfied:
- [ ] **D-11 and D-14 have compatible, approved definitions:** Option A (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` with separate `Open`, `Won`, `Lost` outcomes) officially approved by leadership.
- [ ] **D-12 quotation permissions and approval rules are resolved:** Sub-decisions D-12.1 through D-12.5 confirmed by Head of Sales / MD.
- [ ] **D-13 reporting definitions are approved:** Currency-grouped reporting metrics and labeling safeguards confirmed by finance/sales leadership.
- [ ] **Reopening rules are documented:** Policy for reopening Won/Lost Opportunities approved.
- [ ] **Existing scope and database constraints have been reviewed:** Verified that no existing constraints (`ck_leads_lifecycle_status`) are violated.
- [ ] **Implementation has been explicitly authorized:** Written leadership authorization granted.
- [ ] **A separate implementation and test plan is approved:** Work breakdown, test cases, and rollback procedures accepted.

---

## 4. Confirmation of Non-Execution

**Phase 5 code implementation has NOT started.**

No new application endpoints, database models, migrations, or frontend features have been implemented during this scoping task. All changes are strictly confined to architecture documentation, specification updates, decision registers, and implementation roadmaps.

---

*End of Scoping Report*
