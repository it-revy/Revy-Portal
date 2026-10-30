# PHASE 5 IMPLEMENTATION PLAN & WORK BREAKDOWN

> **Target Platform:** REVY Enterprise Portal  
> **Repository:** `Revy-Portal`  
> **Status:** PROPOSED & GATED (SPEC & PLAN Phase Only — Implementation NOT Started)  
> **Date:** 27 October 2026  
> **Alembic Baseline:** `m0n1o2p3q4r5`  
> **Regression Baseline:** 42 Passing Tests | Clean Vite Build (1,993 modules)  
> **Strategic Two-Layer Focus:**  
> 1. **Current Priority:** Sales Hub & Opportunity Lifecycle Enhancement (Phase 5A)  
> 2. **Future Priority:** Operational Integration (Phases 5B, 5C, 5D, 5E — Document Only)

---

## 1. Phased Implementation Roadmap & Sequencing

In accordance with the Executive Decision Record ([`docs/phase5/PHASE5_DECISION_REGISTER.md`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/docs/phase5/PHASE5_DECISION_REGISTER.md)), Phase 5 implementation is structured into two distinct layers:

```
LAYER 1: IMMEDIATE PRIORITY (Sales Hub & Opportunity Lifecycle)
[Phase 5A: Sales Hub & Opportunity Lifecycle Enhancement]
       │ (Gated on Pre-Implementation Verification Gate Checklist)
       ▼
LAYER 2: FUTURE OPERATIONAL INTEGRATION (Document Only — Gated)
[Phase 5B: Laboratory & LIMS Integration] 
       │ (PO Received Trigger -> Lab Order -> LMS Sample Incoming)
       ▼
[Phase 5C: Product Orders & Inventory Management] 
       │ (PO Received Trigger -> Product Order -> IMS Stock Movements)
       ▼
[Phase 5D: Commercial Billing & Formal Invoicing] 
       │ (Gated on Finance Statutory Specification)
       ▼
[Phase 5E: Cross-Module Integration, Hardening & Release]
```

### Scope Guardrails for Layer 1
- **Immediate implementation is strictly confined to Phase 5A (Sales Hub).**
- No LMS sample incoming screen, physical sample intake, Lab Order creation, inventory movement, invoice generation, or payment processing is authorized in the current phase.

---

## 2. Detailed Work Breakdown: Phase 5A (Sales Hub)

### Objectives
1. Implement the **Six-Stage Sales Funnel** (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close`), mapping existing 4 stages cleanly without loss of historical data.
2. Implement **Quotation Management** on the Opportunity view: maintain **one active quotation per Opportunity**, while retaining full historical records of earlier revisions and superseded quotations.
3. Establish data and storage architecture for a future **Proforma Invoice (PI) Section** (without generating live PIs now).
4. Formalize the exact sub-status **`PO Received`** on Opportunities as the commercial milestone marker without triggering operational actions.
5. Implement executive **Revenue & Pipeline Reporting grouped by currency** (`Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`).
6. Enforce mandatory `loss_reason` on `Lost` Opportunities; require `Close` stage for `Won`.

### Deliverables & File-Level Change Areas

1. **Database Schema & Migrations:**
   - Extend `crm_opportunities` table:
     - Expand `stage` column validation to support the approved 6 stages (`Enquiry`, `Qualify`, `Develop`, `Propose/Offer`, `Negotiate`, `Close`).
     - Add `quotation_count` and `latest_quotation_amount` helper fields.
     - Enforce `loss_reason` check when status is `Lost`.
   - Create `crm_opportunity_quotations` table:
     - `id` VARCHAR(36) PK
     - `quotation_number` VARCHAR(50) (e.g. `QT-00001`)
     - `opportunity_id` VARCHAR(36) FK referencing `crm_opportunities.id`
     - `version` VARCHAR(10) (default `'v1'`)
     - `is_active` BOOLEAN (default True; exactly one active quote per Opp)
     - `quotation_date` DATE
     - `valid_until_date` DATE
     - `amount` NUMERIC(12, 2)
     - `currency` VARCHAR(10) (default `'INR'`)
     - `status` VARCHAR(50) (`Draft`, `Internal Review`, `Shared with Client`, `Accepted`, `Superseded`, `Rejected`)
     - `file_id` VARCHAR(100) referencing `files.file_id` (via polymorphic storage)
     - `notes` TEXT
     - `created_by_id`, `created_at`, `updated_at`
   - Migration file: `versions/<rev>_phase5a_sales_hub_quotations_and_funnel.py`.

2. **Backend Services & API:**
   - Update `Opportunity` model in [`backend/app/crm/model.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/model.py).
   - Add Pydantic schemas in [`backend/app/crm/schema.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/schema.py) (`QuotationCreate`, `QuotationResponse`, `RevenueSummaryMetrics`, `OpportunityStageUpdate`).
   - Implement service methods in [`backend/app/crm/service.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/service.py):
     - `get_sales_funnel_metrics`: Calculates Opportunity counts and commercial values grouped by currency (`won_opportunity_value`, `open_pipeline_value`, `lost_opportunity_value`).
     - `create_quotation_for_opportunity`: Uploads and attaches quote to Opportunity; marks previous active quote as `Superseded`.
     - `list_opportunity_quotations`: Returns versioned history of quotes with active indicator.
     - `update_opportunity_stage`: Moves stage within the approved 6-stage funnel with audit logging.
     - `close_opportunity`: Enforces `loss_reason` for `Lost` or checks `Close` stage for `Won`.
   - Endpoints in [`backend/app/crm/router.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/router.py):
     - `GET /crm/analytics/revenue-metrics`: Returns live revenue and outcome KPI metrics grouped by currency.
     - `POST /crm/opportunities/{id}/quotations`: Add quotation record and document.
     - `GET /crm/opportunities/{id}/quotations`: List quotations for an Opportunity.
     - `PUT /crm/opportunities/{id}/stage`: Update Opportunity stage in 6-stage funnel.
     - `PUT /crm/opportunities/{id}/outcome`: Set outcome to `Won` or `Lost` (with loss reason).

3. **Frontend Implementation:**
   - Update [`CrmOpportunitiesPage.jsx`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/frontend/src/pages/CrmOpportunitiesPage.jsx):
     - Display the approved 6-stage Kanban board (`Enquiry`, `Qualify`, `Develop`, `Propose/Offer`, `Negotiate`, `Close`).
     - Add executive KPI metrics row grouped by currency: Total Opportunities, Open, Won, Lost, Won Opportunity Value, Open Pipeline Value, Lost Opportunity Value.
   - Update [`OpportunityDetailModal.jsx`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/frontend/src/modules/crm/components/OpportunityDetailModal.jsx):
     - Add dedicated **Quotation Section** tab displaying the single active quotation prominently, with an expandable revision history table.
     - Display `PO Received` sub-status badge and commercial indicator.
     - Add architecture placeholder for future PI section.
   - Update [`crmService.js`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/frontend/src/services/crmService.js) with quotation and revenue metric API calls.

---

## 3. Preserved Deferred Scope (Phases 5B, 5C, 5D, 5E — Document Only)

*The following systems remain strictly outside implementation until separately authorized:*
- **Phase 5B (Laboratory & LIMS Commercial Handoff):** Opportunity reaching `PO Received` with requirement `Sample Testing` generating a Lab Order; LMS Sample Incoming section; physical sample receipt confirmation (`SMP-xxxxx`); 3-tier approvals (Analyst $\rightarrow$ Supervisor $\rightarrow$ R&D Head) for FS, Wastewater, BMP, SMA; sample-out/bio-disposal.
- **Phase 5C (Product Orders & Inventory Management):** `ims_products` SKU Master; customer PO verification on `crm_product_orders`; repeat order quick-create; stock movements and dispatch.
- **Phase 5D (Commercial Billing & Payments):** Tax invoices, GST/HSN rules, payment receipts (UTR), and customer ledgers.
- **Phase 5E (Cross-Module Hardening & Release Verification):** End-to-end integration tests, isolated migration verification, and final release gate report.

---

## 4. Pre-Implementation Verification Gate Checklist

Before implementation begins on Phase 5A, the following checklist must be satisfied:
- [ ] **D-11 and D-14 have compatible, approved definitions:** Option A (`Enquiry` $\rightarrow$ `Qualify` $\rightarrow$ `Develop` $\rightarrow$ `Propose/Offer` $\rightarrow$ `Negotiate` $\rightarrow$ `Close` with separate `Open`, `Won`, `Lost` outcomes) officially approved by leadership.
- [ ] **D-12 quotation permissions and approval rules are resolved:** Sub-decisions D-12.1 through D-12.5 confirmed by Head of Sales / MD.
- [ ] **D-13 reporting definitions are approved:** Currency-grouped reporting metrics and labeling safeguards confirmed by finance/sales leadership.
- [ ] **Reopening rules are documented:** Policy for reopening Won/Lost Opportunities approved.
- [ ] **Existing scope and database constraints have been reviewed:** Verified that no existing constraints (`ck_leads_lifecycle_status`) are violated.
- [ ] **Implementation has been explicitly authorized:** Written leadership authorization granted.
- [ ] **A separate implementation and test plan is approved:** Work breakdown, test cases, and rollback procedures accepted.

---

## 5. Explicit Stop Conditions

**EXECUTION IS STRICTLY LOCKED AT THIS POINT.**

Do NOT proceed to implementation until:
1. Business leadership approves Decisions **D-11, D-12, D-13, and D-14**.
2. Leadership provides written sign-off on the Pre-Implementation Verification Gate Checklist.
3. Explicit authorization to begin Phase 5A implementation is granted.

---

*End of Implementation Plan*
