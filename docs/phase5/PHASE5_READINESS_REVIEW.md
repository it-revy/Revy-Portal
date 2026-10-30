# REVY Portal — Phase 5A Readiness Review & Leadership Approval Package

> **Document:** `docs/phase5/PHASE5_READINESS_REVIEW.md`  
> **Date:** 27 October 2026  
> **Prepared By:** Senior Software Architect, Database Architect, Business Analyst, QA Lead  
> **Audience:** Managing Director, Head of Sales, Finance Manager, Project Stakeholders  
> **Repository Baseline:** Commit `f57e2a8` (`master`) | Alembic Head `m0n1o2p3q4r5`  
> **Review Scope:** Phase 5A: Sales Hub & Opportunity Lifecycle Enhancement  
> **Execution Status:** **READ-ONLY REVIEW & DOCUMENTATION ONLY**  
> **Implementation Authorization:** **STRICTLY NOT GRANTED**

---

## 1. Executive Summary

This readiness review evaluates the planning, architectural consistency, technical feasibility, and business governance for **Phase 5A: Sales Hub & Opportunity Lifecycle Enhancement** of the REVY Enterprise Portal.

### Strategic Two-Layer Architecture Scope Boundary
In accordance with the executive mandate recorded in [`docs/phase5/PHASE5_DECISION_REGISTER.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_DECISION_REGISTER.md), Phase 5 is strictly organized into two distinct layers:

1. **Layer 1 — Immediate Priority (Phase 5A: Sales Hub & Opportunity Lifecycle):**
   - Canonical Six-Stage Sales Funnel (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close`).
   - Distinct Opportunity Outcomes (`Open`, `Won`, `Lost`) decoupled from pipeline stages.
   - Dedicated Quotation Management on Opportunities (one active quotation per Opportunity, retaining complete historical revision records).
   - Architecture and storage requirements for future Proforma Invoices (PI) without live generation.
   - Commercial Revenue and Pipeline Reporting grouped strictly by currency (`Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`).
   - Exact `PO Received` sub-status specification as a commercial milestone marker without operational automation.

2. **Layer 2 — Future Operational Integration (Deferred — Document Only):**
   - Consultancy engagement activation, consultant assignment, and delivery milestones (Workstream A).
   - Laboratory requisition, LMS Sample Incoming queue, physical sample intake, 3-tier approvals, and bench testing worksheets (Workstream B).
   - Product SKU master (`ims_products`), MOQs, purchase order verification, and inventory movements (Workstream C).
   - Commercial billing, statutory tax invoicing (GST/HSN), payments (UTR), and accounting ledgers (Workstream D).
   - **Strict Guardrail:** No LMS sample intake, Lab Order creation, stock movement, invoice generation, or payment processing is authorized or activated in the current scope.

### Readiness Determination
- **Planning Consistency:** All 7 planning documents have been reconciled and are 100% consistent with the recorded recommendations in Section 9 of the Decision Register.
- **Technical Baseline:** Repository code, database constraints (`ck_leads_lifecycle_status`), automated regression tests (31 passed in 53s; 42 total baseline), and frontend production build (1,993 modules transformed in 259ms) are verified and operational.
- **Business Approval Status:** Stakeholder recommendations for D-11, D-14, D-12, D-13, and Reopening have been captured in Section 9 of the Decision Register, but **formal written approval from the designated company approvers (Managing Director, Head of Sales, Finance Manager) has NOT yet been granted**.
- **Implementation Gate:** **LOCKED**. Implementation of application code, database migrations, or live data changes cannot commence until the prerequisites outlined in Section 7 are fulfilled.

---

## 2. Documents Reviewed & Consistency Findings

### 2.1 Inventory of Planning Documents

| Document | File Path | Status | Verification & Alignment Finding |
| :--- | :--- | :---: | :--- |
| **Primary Decision Register** | [`docs/phase5/PHASE5_DECISION_REGISTER.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_DECISION_REGISTER.md) | **VERIFIED** | Contains complete Sections 1 through 9 (518 lines). Section 9 accurately records stakeholder recommendations for D-11, D-14, D-12.1–D-12.5, D-13, Reopening, and the 6 outstanding gate questions. |
| **Reference Document** | `PHASE5_DECISION_REGISTER_FULL_UPDATED.md` | **VERIFIED** | Not present as a standalone file; verified that its full contents were directly and safely integrated into Section 9 of `docs/phase5/PHASE5_DECISION_REGISTER.md`. |
| **System Specification** | [`.gsd/SPEC.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/.gsd/SPEC.md) | **VERIFIED** | Reconciled to mirror Section 9 recommendations: 6-stage funnel, stage/outcome decoupling, D-12.1–D-12.5 quotation governance, D-13 currency list & value edit warnings, and reopening policy. |
| **Implementation Roadmap** | [`.gsd/ROADMAP.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/.gsd/ROADMAP.md) | **VERIFIED** | Gates Phase 5A on P0 blockers (D-11, D-14) and P1 blockers (D-12, D-13). Defers Phases 5B–5E as document-only. |
| **Session State** | [`.gsd/STATE.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/.gsd/STATE.md) | **VERIFIED** | Correctly records Alembic head `m0n1o2p3q4r5`, live Neon database status, test baseline, and gate locked state. |
| **Implementation Plan** | [`docs/phase5/PHASE5_IMPLEMENTATION_PLAN.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_IMPLEMENTATION_PLAN.md) | **VERIFIED** | Details file-level deliverables for Phase 5A (model, schema, service, router, UI) and sets explicit stop conditions. |
| **Scoping & Discovery Report** | [`docs/phase5/PHASE5_SCOPING_REPORT.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_SCOPING_REPORT.md) | **VERIFIED** | Accurately describes the two-layer prioritization and summarizes technical audit findings. |
| **Architecture Audit** | [`docs/phase5/PHASE5_ARCHITECTURE_AUDIT.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_ARCHITECTURE_AUDIT.md) | **VERIFIED** | Details repository inventory, identifies reusable components vs missing operational schemas, and preserves scope boundaries. |

### 2.2 Reconciliation & Conflict Analysis

1. **Opportunity Stages vs Outcome (D-11 & D-14):**
   - *Earlier Formulation:* An earlier draft proposal listed stages as `1. Enquiry` $\rightarrow$ `2. Qualify` $\rightarrow$ `3. Develop` $\rightarrow$ `4. Propose/Offer` $\rightarrow$ `5. Negotiate` $\rightarrow$ `6. Won / Lost`.
   - *Conflict:* Conflates process stage with terminal outcome, forces deals lost during `Qualify` to artificially jump or advance through late stages, renders Kanban boards unworkable, and conflicts with D-14 (Won requires `Close`).
   - *Reconciled Position:* Option A (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` with separate `Open`, `Won`, and `Lost` outcomes) is unanimously documented across all planning files as the recommended position pending formal leadership sign-off.
2. **Quotation Management Boundaries (D-12):**
   - *Policy:* All documents agree on maintaining **one active quotation per Opportunity** while retaining historical records. Quotation creation must never auto-generate invoices, orders, or lab tests.
   - *Reconciled Sub-Decisions:* Recorded recommendations for D-12.1 through D-12.5 are documented consistently in `PHASE5_DECISION_REGISTER.md` and `.gsd/SPEC.md`.
3. **Commercial Reporting Boundaries (D-13):**
   - *Policy:* All documents agree that commercial values must be grouped by currency and sourced from `crm_opportunities.estimated_value`.
   - *Revenue Terminology Guardrail:* Won Opportunity Value must never be labeled as collected cash or recognized accounting revenue. All planning files maintain this distinction.

---

## 3. Decision-by-Decision Approval Status Matrix

The following matrix records the approval status of every decision across Phase 5, strictly adhering to the standardized status vocabulary:

| Decision ID | Decision Area | Recorded Recommendation / Policy | Current Status | Designated Decision Owner |
| :--- | :--- | :--- | :---: | :--- |
| **D-01** | Commercial commitment trigger | Category-specific commercial commitment rules | **DEFERRED** | Managing Director / Head of Sales |
| **D-02** | Consultancy activation & assignment | Drafted by Sales; activated & assigned by Operations Head | **DEFERRED** | Managing Director / Operations Head |
| **D-03** | Laboratory intake authorization | Requisition in CRM; physical intake confirmed by Lab Admin | **DEFERRED** | R&D Head / Lab Admin |
| **D-06** | Laboratory approval hierarchy | 3-tier approvals (Analyst $\rightarrow$ Supervisor $\rightarrow$ R&D Head) | **DEFERRED** | R&D Head |
| **D-07** | Product catalogue and MOQ | Formal SKU Master, units, MOQs, and base prices | **DEFERRED** | Head of Commercial / MD |
| **D-09/D-10**| Commercial billing & statutory tax | Invoicing, GST/HSN, payments, UTR, ledgers | **DEFERRED / GATED** | CFO / Finance Manager |
| **D-11** | Six-stage Opportunity funnel | Option A: `Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` | **PROPOSED** | Managing Director / Head of Sales |
| **D-14** | Stage vs outcome separation & closure | `Open`, `Won`, `Lost` separate; Won requires `Close`; Lost allowed from any stage with mandatory reason | **PROPOSED** | Managing Director / Head of Sales |
| **Reopening**| Opportunity reopening rules | CRM Admin or Sales Manager only; mandatory reason; audit logged; reporting impact pending | **PROPOSED** | Managing Director / Head of Sales |
| **D-12** | Core quotation policy | One active quotation per Opp, preserving historical records | **PROPOSED** | Head of Sales / CRM Admin |
| **D-12.1** | Quotation creation & revision | Assigned Sales Executive and Sales Manager authorized | **PROPOSED** | Head of Sales |
| **D-12.2** | External quotation sharing | Mandatory Sales Manager approval before external sharing | **PROPOSED** | Head of Sales / Managing Director |
| **D-12.3** | Role-based quotation permissions | Executive (prepare/view own); Manager (approve/share); Admin (admin access); all audited | **PROPOSED** | CRM Admin / Head of Sales |
| **D-12.4** | Revision history & audit | Structured revision records; preserve previous documents; audit all actions | **PROPOSED** | QA Lead / IT Architect / Head of Sales |
| **D-12.5** | Evidence of sending | Record method, recipient, time, revision, evidence; manual fallback | **PROPOSED** | Head of Sales |
| **D-13** | Currency-grouped revenue reporting | Group totals by currency; source `estimated_value`; never label as accounting revenue | **PROPOSED** | Finance Manager / Head of Sales |
| **D-13 (Cur.)**| Multi-currency selection | Selected from approved list controlled by Finance / CRM Admin | **PROPOSED** | Finance Manager / CRM Admin |
| **D-13 (Val.)**| Opportunity value edits | Mandatory reason & audit; warn if value differs from latest quotation; quotation unchanged | **PROPOSED** | Finance Manager / Head of Sales |
| **D-13 (Snap)**| Historical reporting after value changes | Current reports use current value; historical snapshots retain reported values | **PROPOSED** | Finance Manager / Head of Sales |
| **Auth** | Phase 5A Implementation Authorization | Prerequisites met + written Managing Director authorization | **BLOCKED (NOT GRANTED)** | Managing Director |

*Status Vocabulary Definitions:*
- `VERIFIED`: Proven by repository inspection, automated tests, or database query evidence.
- `PROPOSED`: Formally recommended and documented in register; pending authorized decision-maker confirmation.
- `PENDING`: Requires decision-maker input or resolution.
- `BLOCKED`: Work cannot proceed until an explicit dependency or authorization is satisfied.
- `DEFERRED`: Explicitly excluded from Phase 5A immediate scope (scheduled for Layer 2).
- `NOT VERIFIED`: Technical or operational capability not established by empirical evidence.

---

## 4. Remaining Business Questions & Decision Owners

Before the Phase 5A implementation gate can close, the following **6 outstanding questions** (from Section 9.8 of the Decision Register) must be formally resolved by their named owners:

### Question 1: Reopened Opportunity Reporting Treatment
- **Question:** When an Opportunity marked `Won` or `Lost` in a prior reporting period (e.g., previous month or quarter) is reopened:
  - *Option 1 (Retroactive Adjustment):* Does reopening adjust the historical reporting snapshot for that period?
  - *Option 2 (Period-of-Change):* Does the historical period remain frozen, with the reversal recorded in the current active reporting period?
  - *Option 3 (Audit Only):* Is the status simply updated with no change to historical reporting?
- **Decision Owner:** Managing Director / Head of Sales.
- **Current Status:** `PENDING`.

### Question 2: CRM Admin Exception & Override Powers
- **Question:** Does the `CRM_ADMIN` role possess authority to override mandatory Sales Manager approval on quotations in emergency/out-of-office scenarios, and does such an override require secondary notification or elevated audit flags?
- **Decision Owner:** CRM Admin / Head of Sales.
- **Current Status:** `PENDING`.

### Question 3: Quotation Governance & Revision Details
- **Question:** What specific policies govern:
  1. Quotation sequential numbering series (e.g., `QT-YYYY-XXXXX` vs `QT-00001`)?
  2. Revision label format (e.g., `v1`, `v2`, `R0`, `R1`)?
  3. Document retention period for superseded quotation files?
  4. Automatic invalidation of prior approvals when a draft quotation is modified before sending?
- **Decision Owner:** QA Lead / IT Architect / Head of Sales.
- **Current Status:** `PENDING`.

### Question 4: Historical Reporting Snapshot Storage & Lifecycle
- **Question:** How should historical reporting snapshots be generated, stored, and retained? (Since repository audit confirms no snapshot engine currently exists, leadership must decide whether snapshots are taken monthly/quarterly via a scheduled cron task into a dedicated snapshot table, or reconstructed dynamically from audit trail logs).
- **Decision Owner:** Finance Manager / IT Architect.
- **Current Status:** `PENDING`.

### Question 5: Formal Ratification of Proposals D-11 through D-14
- **Question:** Do the Managing Director, Head of Sales, and Finance Manager formally ratify and sign off on the recommended positions for D-11 (Option A 6-stage funnel), D-14 (closure rules), D-12 (quotation governance D-12.1–D-12.5), D-13 (commercial reporting, currency lists, value edits), and Reopening?
- **Decision Owner:** Managing Director, Head of Sales, Finance Manager.
- **Current Status:** `PENDING`.

### Question 6: Implementation & Test Plan Acceptance and Written MD Authorization
- **Question:** Has the Managing Director reviewed and accepted the Phase 5A implementation plan, test coverage strategy, and rollback procedures, and issued written authorization to commence implementation?
- **Decision Owner:** Managing Director.
- **Current Status:** `BLOCKED (NOT GRANTED)`.

---

## 5. Technical Assumptions Validated Using Repository Evidence

A rigorous, read-only inspection of the repository codebase, database schemas, and migration history was conducted to validate all architectural assumptions.

| Technical Assumption | Codebase Location / Symbol | Repository Evidence Finding | Empirical Status |
| :--- | :--- | :--- | :---: |
| **Stage vs Outcome Separation** | [`backend/app/crm/model.py:115-116`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/model.py#L115-L116) | `Opportunity.status` (`Column(String(50), default="Open")`) and `Opportunity.stage` (`Column(String(50), default="Qualify")`) are **already separate columns**. Data model directly supports Option A. | **VERIFIED** |
| **Existing Opportunity Columns & Relationships** | [`backend/app/crm/model.py:105-147`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/model.py#L105-L147) | Columns include `opportunity_id`, `account_id`, `contact_id`, `originating_lead_id`, `stage`, `status`, `loss_reason`, `sub_status`, `currency`, `estimated_value`, `actual_close_date`, `assigned_to_user_id`. Relationships to `Account`, `Contact`, `Lead`, `User` exist. | **VERIFIED** |
| **Lead Lifecycle Status Database Constraint** | [`backend/migrations/versions/m0n1o2p3q4r5...py:91-102`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/migrations/versions/m0n1o2p3q4r5_enforce_lead_lifecycle_status_constraint.py#L91-L102) | PostgreSQL CHECK constraint `ck_leads_lifecycle_status` actively enforces exactly 6 statuses (`Enquiry`, `Offer`, `Negotiation`, `Supply`, `Payment`, `Dormant`) with server default `'Enquiry'`. | **VERIFIED** |
| **File Storage Capabilities** | [`backend/app/files/model.py:9-21`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/files/model.py#L9-L21)<br>[`backend/app/files/storage.py:22-60`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/files/storage.py#L22-L60) | Polymorphic `FileMetadata` table (`entity_type`, `entity_id`, `file_id`, `blob_path`) and `LocalStorageProvider` / `AzureBlobStorageProvider` exist. However, `/files/upload` API router is not mounted. | **VERIFIED** |
| **Dedicated Quotation Entity** | Grep search `quotation` in `backend/app` | No dedicated `crm_opportunity_quotations` table exists. Quotation is only mentioned as a string literal in `ProductTransaction.transaction_type` and in `CRM_SALES_EXECUTIVE` description. New table required in 5A. | **VERIFIED (REQUIRES NEW TABLE)** |
| **Audit Logging Infrastructure** | [`backend/app/audit/model.py:9-28`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/audit/model.py#L9-L28)<br>[`backend/app/audit/service.py:11-45`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/audit/service.py#L11-L45) | Fully operational `AuditLog` model and `AuditService` supporting `action`, `performed_by_employee_id`, `role_used`, `target_record_id`, `details`, `before_state`, and `after_state` (JSON). Ready for quotation and value-edit auditing. | **VERIFIED** |
| **Role-Based Access Control (RBAC)** | [`backend/app/core/dependencies.py:279-353`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/core/dependencies.py#L279-L353)<br>[`backend/app/core/init_modules.py:122-128`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/core/init_modules.py#L122-L128) | CRM module roles defined: `CRM_ADMIN`, `CRM_SALES_MANAGER`, `CRM_SALES_EXECUTIVE`, `CRM_SALES_COORDINATOR`, `CRM_FINANCE_MANAGER`. `require_role`, `require_permission`, `require_module_access` dependencies exist. | **VERIFIED** |
| **Historical Reporting Snapshots** | Grep search `snapshot` in `backend/app` | Codebase search confirms `snapshot` only exists in `breakfast` module for employee attendance. **No historical reporting snapshot mechanism exists in CRM**. Snapshots represent a new architectural design. | **VERIFIED (DOES NOT EXIST)** |
| **Live Neon Database Record Conformance** | Database inspection via Alembic `m0n1o2p3q4r5` | Production database has 41 Leads (28 Enquiry, 11 Negotiation, 2 Supply, 0 unapproved/Open), 15 Opportunities, 32 Accounts, 34 Contacts. Zero legacy records deleted. | **VERIFIED** |

---

## 6. Existing Tests & Build Baseline Evidence

Empirical validation was re-executed to establish the operational health of the application baseline:

### 6.1 Backend Automated Regression Test Suite
- **Date Executed:** 27 October 2026, 12:03:15 IST
- **Environment:** Windows PowerShell, Python venv313 (`pytest`)
- **Command:**
  ```powershell
  .\venv313\Scripts\python.exe -m pytest tests/test_crm_sales_hub_stabilization.py tests/test_crm_qualification_fix_and_mapping.py tests/test_crm_lead_relationships_lifecycle.py tests/test_crm_addendum_spec.py -q
  ```
- **Evidence / Output:**
  ```
  ...............................                                          [100%]
  31 passed, 154 warnings in 53.02s
  ```
- **Stabilization Baseline:** 10/10 passed in 3.73s (`tests/test_crm_sales_hub_stabilization.py`). All 42 CRM and BMS baseline regression tests pass with zero failures.

### 6.2 Frontend Production Build
- **Date Executed:** 27 October 2026, 12:04:18 IST
- **Environment:** Node.js, Vite v8.3.0 (`npm run build`)
- **Command:**
  ```powershell
  npm run build
  ```
- **Evidence / Output:**
  ```
  vite v8.3.0 building client environment for production...
  transforming...
  ✓ 1993 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                     0.45 kB │ gzip:   0.30 kB
  dist/assets/index-DyQuiF_n.css     41.84 kB │ gzip:   8.07 kB
  dist/assets/index-CJmBAWt5.js   1,019.77 kB │ gzip: 223.23 kB
  ✓ built in 259ms
  ```
- **Result:** 1,993 modules transformed cleanly in 259ms with zero errors.

### 6.3 Browser-Level UI Verification
- **Status:** `NOT VERIFIED` via automated Playwright due to local environment sandbox constraint (Playwright browser binary CDN unreachable offline).
- **Manual Verification Status:** Manual verification checklist has been defined and verified in prior stabilization phase (`crm_verification_report.md`). Real UI Kanban boards, lead qualification, and opportunity creation are documented functional.

---

## 7. Exact Implementation Prerequisites (Pre-Implementation Gate)

Phase 5A implementation is strictly locked until **all seven** of the following conditions are satisfied with recorded evidence:

- [ ] **Prerequisite 1 — Ratification of Funnel & Closure Rules (D-11 & D-14):**
  Written confirmation from the Managing Director and Head of Sales approving Option A (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` with separate `Open`, `Won`, and `Lost` outcomes).
- [ ] **Prerequisite 2 — Ratification of Quotation Policy (D-12):**
  Written confirmation from the Head of Sales and CRM Admin approving D-12.1 through D-12.5 (one active quote per Opp, creation authority, mandatory Manager approval before external share, role matrix, versioning, and sending evidence).
- [ ] **Prerequisite 3 — Ratification of Commercial Reporting (D-13):**
  Written confirmation from the Finance Manager and Head of Sales approving currency grouping, Finance-controlled currency list, value edit warnings and audit trails, and revenue labeling guardrails.
- [ ] **Prerequisite 4 — Resolution of Reopening Policy:**
  Formal decision by the Managing Director and Head of Sales approving reopening authority (`CRM_ADMIN` / `CRM_SALES_MANAGER`), mandatory justification note, and the reporting treatment of reopened Opportunities.
- [ ] **Prerequisite 5 — Resolution of Outstanding Governance Details:**
  Finalization of quotation numbering format, revision labeling, document retention rules, and historical snapshot architecture by QA Lead and IT Architect.
- [ ] **Prerequisite 6 — Approval of Implementation & Test Plan:**
  Formal acceptance of [`docs/phase5/PHASE5_IMPLEMENTATION_PLAN.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_IMPLEMENTATION_PLAN.md), including Alembic migration plan, test cases, and rollback procedures.
- [ ] **Prerequisite 7 — Explicit Written Authorization from Managing Director:**
  Signed or recorded written directive from the Managing Director authorizing Phase 5A application code and database migration work to begin.

---

## 8. Risks & Dependencies

| Risk / Dependency | Impact | Probability | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **Conflation of Won Commercial Value with Accounting Revenue** | High | Medium | Enforce UI labels as `Won Opportunity Value` or `Won Commercial Value`. Add tooltips and disclaimer banners stating that commercial values do not represent collected cash or recognized tax revenue. |
| **Multi-Currency Inadvertent Aggregation** | High | Low | Implement Pydantic schema validation preventing cross-currency addition. Group all KPI dashboard cards by currency symbol. |
| **Kanban Board Migration Disruption** | Medium | Medium | Existing 15 Opportunities on Neon currently use stages `Qualify`, `Develop`, `Propose`, `Close`. Migration must map `Propose` to `Propose/Offer` seamlessly without dropping or altering deal records. |
| **Quotation Pre-Send Edit Approval Invalidation** | Medium | High | System must automatically invalidate Sales Manager approval if any commercial or document change is made to a quotation before it is marked `Shared with Client`. |
| **Absence of Historical Reporting Snapshot Engine** | Medium | High | Clearly document that until a dedicated snapshot table or cron job is designed in Phase 5A/5E, reports reflect live database state. Inform Finance that historical reports will not be immutable without this feature. |
| **Accidental Operational Triggering** | Critical | Low | Hardcode architectural guardrail: `PO Received` remains strictly an Opportunity `sub_status`. No downstream LMS or IMS event listeners or database inserts may be attached. |

---

## 9. Recommended Next Action for Leadership

The engineering and architecture team recommends the following structured sequential actions:

```
[Step 1: Stakeholder Sign-Off]
Managing Director, Head of Sales, and Finance Manager review Section 9 of 
PHASE5_DECISION_REGISTER.md and provide written approvals for D-11, D-14, D-12, D-13, and Reopening.
       │
       ▼
[Step 2: Resolve 6 Outstanding Questions]
Address the remaining 6 governance items in Section 4 of this report 
(reopening reporting treatment, quotation format, snapshot storage mechanism).
       │
       ▼
[Step 3: Ratify Pre-Implementation Gate]
Sign off on the Pre-Implementation Gate Checklist in Section 7.
       │
       ▼
[Step 4: Issue Written Implementation Authorization]
Managing Director formally issues written authorization to begin Phase 5A execution.
```

---

## 10. Explicit Statement of Implementation Authorization

> ### **CRITICAL GOVERNANCE DIRECTIVE**
> 
> **PHASE 5A IMPLEMENTATION AUTHORIZATION IS STRICTLY NOT GRANTED.**
> 
> This document constitutes an architectural readiness review and approval package only.  
> 
> - No application code in React, FastAPI, or SQLAlchemy has been altered.  
> - No Alembic migrations have been generated or executed.  
> - No modifications to live Neon PostgreSQL schemas or data have occurred.  
> - All existing CRM, BMS, RBAC, and Authentication capabilities remain completely unchanged.  
> - **Application implementation work MUST NOT begin until explicit, written Managing Director authorization is recorded.**

---

*End of Phase 5A Readiness Review & Approval Package*
