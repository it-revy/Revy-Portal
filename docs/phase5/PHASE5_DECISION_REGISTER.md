# REVY Portal — Phase 5 Business-Policy Decision Record

**Document:** `docs/phase5/PHASE5_DECISION_REGISTER.md`  

**Date:** 27 October 2026  

**Status:** Draft for leadership approval  

**Execution stage:** SPEC & PLAN only  

**Implementation authorization:** NOT GRANTED

---

## 1. Executive Summary

REVY Portal Phase 5 planning follows a strict two-layer architecture:

### Layer 1 — Immediate Priority: Sales Hub & Opportunity Lifecycle

- Define the six-stage Opportunity sales funnel.

- Organize quotations within individual Opportunities (one active quotation per Opportunity, retaining historical records).

- Prepare architecture and data requirements for future Proforma Invoice (PI) storage (without generating live PIs now).

- Track Opportunity outcomes: `Open`, `Won`, and `Lost`.

- Display Opportunity counts and commercial values grouped by currency (`Won Opportunity Value`, `Open Pipeline Value`, `Lost Opportunity Value`).

- Record `PO Received` as a commercial milestone sub-status without triggering operational workflows.

### Layer 2 — Future Operational Integration (Document Only — Gated)

- Consultancy delivery management.

- Laboratory and LMS integration.

- Product orders and inventory management.

- Formal invoicing, taxation, and payment processing.

- Cross-module integration and final release verification.

Layer 2 remains documentation-only until separately authorized. The current scope does not authorize laboratory intake, Lab Order creation, stock movements, invoice generation, or payment processing.

---

## 2. Decision Register Matrix

| ID | Decision Area | Recommended Position Pending Approval | Status | Decision Owner |

|---|---|---|---|---|

| **D-01** | Commercial commitment trigger | Category-specific commercial authorization | Proposed; future scope | Managing Director / Head of Sales |

| **D-02** | Consultancy activation and assignment | Sales drafts; Director / Operations Head activates and assigns | Proposed; future scope | Managing Director / Operations Head |

| **D-03** | Laboratory intake authorization | CRM requisition followed by physical sample intake by Lab Admin | Proposed; future scope | R&D Head / Lab Admin |

| **D-06** | Laboratory approval hierarchy | Analyst → Lab Supervisor → R&D Head → Lab Admin dispatch | Proposed; future scope | R&D Head |

| **D-07** | Product catalogue and MOQ | Company supplies an approved SKU master before implementation | Prerequisite pending | Head of Commercial / MD |

| **D-09/D-10** | Billing and tax rules | Billing scope and statutory rules require separate approval | Gated | CFO / Finance Manager |

| **D-11** | Six-stage Opportunity funnel | `Enquiry` → `Qualify` → `Develop` → `Propose/Offer` → `Negotiate` → `Close` | **Recommended position pending approval** | Managing Director / Head of Sales |

| **D-12** | Quotation management | One active quotation per Opportunity, retaining historical records | **Proposed; sub-decisions pending** | Head of Sales / CRM Admin |

| **D-13** | Revenue reporting | Group Opportunity commercial values by currency | **Proposed; definitions pending** | Finance Manager / Head of Sales |

| **D-14** | Opportunity closure rules | Won requires `Close` stage; Lost requires reason from any stage | **Recommended position pending approval** | Managing Director / Head of Sales |

*Note: No position in this table is represented as approved company policy until leadership explicitly confirms it.*

---

## 3. Task 1 Resolution: D-11 and D-14 — Opportunity Stages and Closure Rules

### 3.1 Recommended Position (Pending Leadership Approval)

#### Recommended Opportunity Stages

The recommended canonical progression through the sales pipeline consists of six sequential stages:

1. `Enquiry` — Initial customer requirement logged and under preliminary review.

2. `Qualify` — Customer need, technical fit, and commercial viability assessed.

3. `Develop` — Solution engineered, sizing/feasibility determined, and commercial scope detailed.

4. `Propose/Offer` — Formal proposal or quotation prepared and submitted to the customer.

5. `Negotiate` — Commercial, legal, payment terms, or pricing adjustments actively negotiated.

6. `Close` — Final commitment milestone where contract execution, formal PO receipt, or commercial finalization occurs.

#### Opportunity Outcomes

Opportunity outcomes represent commercial disposition and must remain **strictly separate concepts** from pipeline stages:

- `Open` — Represents an active, nonterminal Opportunity progressing through the pipeline.

- `Won` — Represents an Opportunity where a binding commercial agreement or purchase order has been achieved.

- `Lost` — Represents an Opportunity that was abandoned, cancelled, or won by a competitor.

#### Closure Rules

- **Won Rule:** An Opportunity must be at the `Close` stage to be marked `Won`. Marking an Opportunity `Won` requires appropriate role permission and is audited with actor, timestamp, and close date.

- **Lost Rule:** An Opportunity may be marked `Lost` from **any approved pipeline stage** (e.g., disqualified during `Qualify`, rejected during `Propose/Offer`, or abandoned during `Negotiate`). A non-empty `loss_reason` is **mandatory**; the action is audited with actor and timestamp.

- **Open Rule:** Represents any Opportunity that has not reached a terminal outcome (`Won` or `Lost`), regardless of its current stage.

### 3.2 Conflict Analysis: Why Literal "Won / Lost" as the 6th Stage is Flawed

The earlier proposal supplied for REVY listed the six stages as:

\(\text{1. Enquiry} \longrightarrow \text{2. Qualify} \longrightarrow \text{3. Develop} \longrightarrow \text{4. Propose/Offer} \longrightarrow \text{5. Negotiate} \longrightarrow \text{6. Won / Lost}\)

This earlier formulation creates severe architectural, operational, and data conflicts:

1. **Conflating Pipeline Stage with Terminal Outcome:**

   - A pipeline stage represents *where an Opportunity sits in the evaluation and sales process*.

   - An outcome represents *how the commercial negotiation concluded* (`Won` or `Lost`).

   - Combining `Won / Lost` into a single sixth stage collapses these two orthogonal dimensions into one ambiguous column.

2. **Premature Funnel Progression for Lost Deals:**

   - Deals can be lost at early stages: an enquiry might fail initial feasibility during `Qualify`, or pricing might be rejected during `Propose/Offer`.

   - If `Won / Lost` were the sixth stage, the system would either force salespeople to advance failed deals through `Develop`, `Propose/Offer`, and `Negotiate` just to mark them "Lost", distorting sales velocity metrics, or create an artificial jump to stage 6.

3. **Ambiguity on the Kanban Board:**

   - A Kanban column titled "Won / Lost" would display successful closed-won revenue deals alongside cancelled or lost deals in the same column, making visual pipeline management impossible.

4. **Conflict with D-14 Closure Prerequisite:**

   - Under D-14, marking an Opportunity `Won` requires it to reach the final closing step (`Close`). Naming that step `Close` provides a clean milestone where final contracts and POs are gathered, after which the outcome is set to `Won`.

**Status of Recommendation:** Option A (`Enquiry` \(\rightarrow\) `Qualify` \(\rightarrow\) `Develop` \(\rightarrow\) `Propose/Offer` \(\rightarrow\) `Negotiate` \(\rightarrow\) `Close` with separate `Open`/`Won`/`Lost` outcomes) is the **recommended architectural position**, pending formal leadership approval. It is NOT yet approved company policy.

### 3.3 Reopening Rules (Unresolved)

The rules governing the reopening of `Won` or `Lost` Opportunities remain **unresolved**:

- Who is authorized to reopen a closed Opportunity? (e.g., `CRM_ADMIN` only, or `CRM_SALES_MANAGER`?)

- Is a mandatory reopening justification note required?

- How should historical KPI reporting treat reopened Opportunities? (e.g., does reopening a Won Opportunity subtract its value from previously reported monthly Won Revenue?)

- **Decision Owner:** Managing Director / Head of Sales.

---

## 4. Task 2 Resolution: D-12 — Quotation Policy

### 4.1 Proposed Core Rule

**Maintain one active quotation per Opportunity, while retaining full historical records of earlier revisions and superseded quotations.**

### 4.2 Proposed Requirements

- Each quotation record is linked directly to a specific Opportunity (`Opportunity.id`).

- The Opportunity detail view will provide a dedicated **Quotation Section**.

- Quotation documents (`PDF`/`DOCX`) will be stored using the platform's existing generic file-storage service ([`FileMetadata`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/files/model.py#L9)).

- When a revised quotation is created, it becomes the **Active** quotation; the previous quotation is automatically marked **Superseded**, preserving its full document history, amount, and timestamp.

- Quotation records must capture:

  - Quotation sequential identifier (e.g., `QT-00001`)

  - Revision label (e.g., `v1`, `v2`, `v3`)

  - Quotation date and valid-until date

  - Commercial amount and currency

  - Status: `Draft`, `Internal Review`, `Shared with Client`, `Accepted`, `Superseded`, `Rejected`

  - Associated document file reference (`file_id`)

  - Creator and modifier user attribution

- **Operational Boundary:** A quotation record organizes commercial proposals; it must **never** auto-create a product order, laboratory submission, invoice, or payment record.

### 4.3 Remaining Pending Decisions (Sub-Decisions)

The following quotation governance questions remain **unresolved and require business leadership approval**:

| Sub-Decision ID | Question | Options Under Consideration | Status | Required Decision Owner |

|---|---|---|:---:|---|

| **D-12.1** | Who can create and revise quotations? | Sales Executive assigned to deal vs Sales Manager only | **Pending** | Head of Sales |

| **D-12.2** | Is approval required before sharing a quotation externally? | Mandatory Sales Manager approval vs Self-approval below threshold | **Pending** | Head of Sales / MD |

| **D-12.3** | Which roles can view, download, approve, or share quotations? | Role-based matrix (`CRM_ADMIN`, `CRM_SALES_MANAGER`, `CRM_SALES_EXECUTIVE`) | **Pending** | CRM Admin / Head of Sales |

| **D-12.4** | How are revisions and approval history recorded? | Structured audit log table vs document version log | **Pending** | QA Lead / IT Architect |

| **D-12.5** | What evidence confirms a quote was sent to the customer? | Client email integration log vs manual timestamp checkoff | **Pending** | Head of Sales |

### 4.4 Future Proforma Invoice (PI) Section

A dedicated **Proforma Invoice (PI)** section is planned for each Opportunity in a future operational phase.

- **Current Scope Restriction:** Current planning must **not** generate PI documents, invoice numbers, GST calculations, or payment records. A PI must never be represented as a tax invoice or proof of payment.

---

## 5. Task 3 Resolution: D-13 — Commercial Revenue Reporting

### 5.1 Proposed Core Rule

**Display Opportunity commercial values grouped by currency, rather than combining amounts from different currencies into one misleading total.**

### 5.2 Canonical Data Source

- The canonical source of truth for an Opportunity's commercial value is [`crm_opportunities.estimated_value`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/app/crm/model.py#L115) (Numeric(12, 2)), alongside `crm_opportunities.currency` (VARCHAR(10), default `'INR'`).

- Do not create an unrelated duplicate revenue field without a documented architectural need.

### 5.3 Reporting Metrics Structure

The Sales Hub dashboard and reports must distinguish between `Open`, `Won`, and `Lost` outcomes, reporting counts and values grouped by currency:

| Metric Name | Calculation Rule | Currency Handling | Labeling Safeguard |

|---|---|---|---|

| **Total Opportunities** | Count of Opportunities in selected scope | N/A (Record count) | Record count |

| **Open Opportunities** | Count of Opportunities with outcome `Open` | N/A (Record count) | Record count |

| **Won Opportunities** | Count of Opportunities with outcome `Won` | N/A (Record count) | Record count |

| **Lost Opportunities** | Count of Opportunities with outcome `Lost` | N/A (Record count) | Record count |

| **Won Opportunity Value** | \(\sum(\text{estimated\\\_value})\) for `outcome == 'Won'` | **Grouped by currency** (e.g., INR X, USD Y) | Must NOT be labeled as collected cash or accounting revenue |

| **Open Pipeline Value** | \(\sum(\text{estimated\\\_value})\) for `outcome == 'Open'` | **Grouped by currency** (e.g., INR X, USD Y) | Forward-looking pipeline estimate |

| **Lost Opportunity Value** | \(\sum(\text{estimated\\\_value})\) for `outcome == 'Lost'` | **Grouped by currency** (e.g., INR X, USD Y) | Unrealized commercial potential |

### 5.4 Reporting Safeguards & Currency Policy

1. **No Cross-Currency Aggregation:** Amounts in different currencies (e.g., INR, USD, EUR) must **never** be added together into a single sum without an approved conversion mechanism.

2. **Revenue Terminology Guardrail:** The sum of Won Opportunity values must be labeled as `Won Opportunity Value` or `Won Commercial Value`. It must **never** be presented as recognized accounting revenue, cash collected, or issued tax invoices.

3. **Currency Conversion Prerequisites:** If consolidated single-currency reporting is required in the future, leadership must provide:

   - An approved exchange-rate data source (e.g., RBI official reference rate or fixed monthly rate table).

   - An exchange-rate date policy (date of Opportunity creation vs date of Won outcome vs current date).

   - A reporting rule defining how currency fluctuation gains/losses are treated.

### 5.5 Unresolved Commercial Reporting Questions

- Should multi-currency Opportunity creation be restricted to specific enterprise roles, or open to all sales reps?

- Who is authorized to edit Opportunity value after a quotation has been issued?

- How should commercial value amendments affect historical monthly/quarterly reports?

- **Decision Owner:** Finance Manager / Head of Sales.

---

## 6. Task 5: Preserved Deferred Scope (Future Layer 2)

The following operational systems and workflows are strictly **deferred from immediate implementation** and remain document-only until separately authorized:

1. **Commercial Commitment Triggers & PO Received Automation (D-01):**

   - Setting the Opportunity sub-status to `PO Received` records a commercial milestone in the Sales Hub, but must **not** trigger automatic Lab Order creation, sample incoming records, or product order generation.

2. **Consultancy Activation and Assignment (D-02):**

   - Lead consultant assignment, engagement activation, and delivery milestone sign-offs remain deferred.

3. **Laboratory Requisition & Physical Sample Intake (D-03):**

   - Creation of Lab Orders and the LMS Sample Incoming section remain deferred. A sample must not be marked physically received merely because an Opportunity or requisition exists.

4. **Laboratory Approval Hierarchy & Worksheets (D-06):**

   - 3-tier approvals (Analyst \(\rightarrow\) Supervisor \(\rightarrow\) R&D Head), bench testing worksheets for FS, Wastewater, BMP, and SMA, and sample-out/disposal tracking remain deferred.

5. **Product Catalogue & MOQ Rules (D-07):**

   - Implementation of `ims_products` SKU Master, MOQs, base pricing, and stock movements remains deferred until the company supplies the official SKU master.

6. **Commercial Billing, Tax, & Payment Reconciliation (D-09 / D-10):**

   - Generation of tax invoices, GST/HSN calculations, payment receipts, UTR numbers, and accounting ledgers remains gated under Phase 5D.

---

## 7. Remaining Blockers & Pre-Implementation Gate

### 7.1 Priority Blocker Hierarchy

| Priority | Blocker ID | Description | Required Action | Responsible Decision Owner |

|:---:|---|---|---|---|

| **P0** | **D-11** | Six-Stage Funnel Definition | Approve Option A (`Enquiry` \(\rightarrow\) `Qualify` \(\rightarrow\) `Develop` \(\rightarrow\) `Propose/Offer` \(\rightarrow\) `Negotiate` \(\rightarrow\) `Close`) | Managing Director / Head of Sales |

| **P0** | **D-14** | Stage / Outcome Compatibility | Confirm closure rules (Won requires `Close`; Lost permitted from any stage with reason) | Managing Director / Head of Sales |

| **P1** | **D-12** | Quotation Policy & Permissions | Confirm quotation approval, versioning, sharing, and role permissions | Head of Sales / CRM Admin |

| **P1** | **D-13** | Revenue Reporting & Currencies | Confirm currency grouping and commercial value terminology | Finance Manager / Head of Sales |

| **P1** | **Reopening** | Opportunity Reopening Rules | Approve reopening permissions, mandatory reasons, and reporting rules | Managing Director / Head of Sales |

| **Deferred** | D-01/D-02/D-03/D-06 | Operational Workflows | Resolve before implementing corresponding operational modules | Operations Head / R&D Head |

| **Deferred** | D-07 | Product SKU Master | Supply approved SKU codes, MOQs, units, and base prices | Commercial Head / MD |

| **Gated** | D-09/D-10 | Billing Scope & Taxes | Approve finance specification before Phase 5D | CFO / Finance Manager |

### 7.2 Pre-Implementation Verification Gate Checklist

Before implementation begins on Phase 5A, the following checklist must be completely satisfied:

- [ ] **D-11 and D-14 have compatible, approved definitions:** Leadership officially signs off on Option A (or approved alternative) separating the 6 pipeline stages from the 3 outcomes.

- [ ] **D-12 quotation permissions and approval rules are resolved:** Sub-decisions D-12.1 through D-12.5 are answered and signed off.

- [ ] **D-13 reporting definitions are approved:** Currency-grouped reporting metrics and labeling safeguards are confirmed by finance/sales leadership.

- [ ] **Reopening rules are documented:** Policy for reopening Won/Lost Opportunities and its audit/reporting impact is approved.

- [ ] **Existing scope and database constraints have been reviewed:** Verified that no existing constraints (such as `ck_leads_lifecycle_status`) are violated.

- [ ] **Implementation has been explicitly authorized:** Written leadership authorization granted to commence Phase 5A code changes.

- [ ] **A separate implementation and test plan is approved:** Work breakdown, test cases, and rollback procedures are formally accepted.

---

## 8. Implementation Guardrails & Approval Record

### 8.1 Implementation Guardrails

Until the pre-implementation gate checklist is satisfied:

- Do not implement application code.

- Do not create or apply database migrations.

- Do not alter live Neon database records or schema.

- Do not modify CRM UI or API code.

- Do not generate Proforma Invoices, tax invoices, or payment records.

- Do not create Lab Orders or LMS sample intake records.

- Do not implement inventory reservation or product dispatch.

- Preserve existing authentication, RBAC, BMS, Accounts, Contacts, and CRM functionality.

### 8.2 Approval Record

| Decision | Proposed Position | Approval Status | Approver | Date |

|---|---|---|---|---|

| **D-01** | Category-specific commitment trigger | Proposed; deferred | Pending | Pending |

| **D-02** | Consultancy activation and assignment | Proposed; deferred | Pending | Pending |

| **D-03** | Laboratory intake authorization | Proposed; deferred | Pending | Pending |

| **D-06** | Laboratory approval hierarchy | Proposed; deferred | Pending | Pending |

| **D-07** | Product catalogue and MOQ | Prerequisite pending | Pending | Pending |

| **D-09/D-10** | Billing and tax rules | Gated | Pending | Pending |

| **D-11** | Six-stage funnel (Option A Recommended) | **Proposed; P0 approval pending** | Pending | Pending |

| **D-12** | One active quote per Opp with history | **Proposed; P1 approval pending** | Pending | Pending |

| **D-13** | Revenue reporting grouped by currency | **Proposed; P1 approval pending** | Pending | Pending |

| **D-14** | Won requires Close; Lost requires reason | **Proposed; P0 approval pending** | Pending | Pending |

---

**Execution Status: SPEC & PLAN ONLY. Phase 5 implementation is NOT authorized.**
9. Leadership Decision Questionnaire — Recorded Recommendations
Recorded on: 27 October 2026
Status: Recommendations captured from the project stakeholder; formal leadership approval remains pending.
Authority note: These responses are recommendations for review. They are not evidence that the Managing Director, Head of Sales, Finance Manager, or any other company approver has formally approved the policies. This section supplements the earlier decision register and does not authorize implementation.
9.1 D-11 — Opportunity Stages
Recommended position: Option A — six stages ending in Close.
1. Enquiry
2. Qualify
3. Develop
4. Propose/Offer
5. Negotiate
6. Close
Opportunity outcome remains a separate dimension with the values Open, Won, and Lost. An Opportunity must be at Close before it can be marked Won.

Status: Recommended; Managing Director / Head of Sales approval pending.
9.2 D-14 — Lost Outcome Rule
Recommended position: An Opportunity may be marked Lost from any approved pipeline stage. A non-empty loss reason is mandatory, and the action must be audited.

Status: Recommended; Managing Director / Head of Sales approval pending.
9.3 Opportunity Reopening Policy
Recommended position:
- Only CRM Admin or Sales Manager may reopen a closed Opportunity.
- A reopening reason is mandatory.
- Record the actor, timestamp, and reason in the audit trail.
- Historical KPI/reporting treatment for reopened Won/Lost Opportunities still requires an explicit definition. In particular, leadership must decide how reopening affects previously reported monthly or quarterly snapshots.
Status: Recommended; Managing Director / Head of Sales approval pending.
9.4 D-12 — Quotation Governance
Core proposal: Maintain one active quotation per Opportunity while retaining historical quotation records and revisions. Quotations must not automatically create product orders, laboratory submissions, invoices, or payment records.
D-12.1 — Creation and Revision Authority
Assigned Sales Executives may create and revise quotations for their own assigned Opportunities. Sales Managers may also create and revise quotations.

Status: Recommended; Head of Sales approval pending.
D-12.2 — Approval Before External Sharing
Sales Manager approval is mandatory before every quotation is shared externally with a customer. A revised quotation must go through the approval process again before external sharing.

Status: Recommended; Head of Sales / Managing Director approval pending.
D-12.3 — Role Permissions
- Assigned Sales Executive: View, download, and prepare quotations for their assigned Opportunities.
- Sales Manager: View, download, approve, and share quotations.
- CRM Admin: Administrative access.
- Audit: All quotation actions must be audited.
The exact administrative permission boundaries and any exception/override powers must be confirmed in the final role-permission matrix.

Status: Recommended; CRM Admin / Head of Sales approval pending.
D-12.4 — Revision History and Audit
Maintain structured quotation revision records and preserve every previous quotation document. Audit creation, edits, approvals, rejections, superseding, and sharing, including the responsible actor and timestamp.

Status: Recommended; QA Lead / IT Architect and relevant business-owner review pending.
D-12.5 — Evidence of Sending
Record the sending method, recipient, date/time, quotation revision, and available evidence of sending. If email integration is unavailable, require manual confirmation recording the sender and timestamp.

Status: Recommended; Head of Sales approval pending.
Additional quotation implementation details still to resolve
Before implementation, confirm the quotation identifier and revision-numbering policy, document retention requirements, how approval is invalidated after edits, whether CRM Admin may override Sales Manager approval, and how access to historical/superseded documents is controlled. Do not infer answers that have not been approved.
9.5 D-13 — Commercial Reporting and Currency
Multi-Currency Permissions
All authorized CRM Sales users may select a currency from an approved list controlled by Finance / CRM Admin.

Status: Recommended; Finance Manager / Head of Sales approval pending.
Opportunity Value Edits After Quotation Issuance
Authorized users may edit the Opportunity estimated value with a mandatory reason and audit log. Warn the user if the estimated value differs from the latest quotation. The quotation itself remains unchanged unless separately revised and approved.

Status: Recommended; Finance Manager / Head of Sales approval pending.
Historical Reporting After Value Changes
Preserve old and new values, reasons, and timestamps in the audit trail. Current reports use the current Opportunity value. Historical snapshots retain the value previously reported.

Status: Recommended; Finance Manager / Head of Sales approval pending.
Reporting safeguards
- Use crm_opportunities.estimated_value as the proposed canonical commercial value field, with the Opportunity currency.
- Group commercial values by currency; do not add different currencies into a single total without an approved conversion mechanism.
- Distinguish Won Opportunity Value from collected cash, issued tax invoices, and recognized accounting revenue.
- If currency conversion is later required, leadership must approve the exchange-rate source, rate date policy, and reporting method.
- The reporting design must define how historical snapshots are generated and retained; do not claim that snapshot capability already exists unless verified in the codebase.
Status: Recommended; Finance Manager / Head of Sales approval pending.
9.6 Implementation Authorization
Recommended authorization process:
1. Relevant Sales and Finance decision owners approve the policies within their areas.
2. The reopening policy and its audit/reporting impact are resolved.
3. The implementation and test plan, including regression tests and rollback procedures, is reviewed and accepted.
4. Existing application scope, RBAC, and database constraints are reviewed.
5. The Managing Director provides written approval to commence Phase 5A.
Implementation remains unauthorized until the required approvals and written Managing Director authorization have actually been granted. The questionnaire responses alone do not grant implementation permission.

Status: Recommended process; authorization not granted.
9.7 Updated Decision Status Summary
Decision	Recorded recommendation	Current status	Decision owner(s)
D-11	Six stages ending in Close; separate Open/Won/Lost outcomes	Pending formal approval	Managing Director / Head of Sales
D-14	Lost from any approved stage with mandatory reason; Won requires Close	Pending formal approval	Managing Director / Head of Sales
Reopening	CRM Admin or Sales Manager; mandatory reason and audit; reporting impact to be resolved	Partly unresolved; approval pending	Managing Director / Head of Sales
D-12.1	Assigned Sales Executive and Sales Manager can create/revise within defined scope	Pending approval	Head of Sales
D-12.2	Mandatory Sales Manager approval before every external share	Pending approval	Head of Sales / Managing Director
D-12.3	Role-based quotation permissions; audit all actions	Pending approval	CRM Admin / Head of Sales
D-12.4	Structured revision records, preserve previous documents, audit lifecycle actions	Pending approval and technical review	QA Lead / IT Architect / business owner
D-12.5	Record sending method, recipient, time, revision, and evidence; manual fallback if email integration unavailable	Pending approval	Head of Sales
D-13 currency permissions	Authorized Sales users select from Finance/CRM Admin-approved currency list	Pending approval	Finance Manager / Head of Sales
D-13 value edits	Reason and audit required; warn on mismatch; quotation unchanged unless separately revised/approved	Pending approval	Finance Manager / Head of Sales
D-13 historical reporting	Current reports use current value; historical snapshots preserve previously reported value	Pending approval; snapshot implementation details to confirm	Finance Manager / Head of Sales
Implementation authorization	Relevant Sales/Finance approvals, accepted implementation/test plan, then written MD approval	NOT GRANTED	Managing Director


9.8 Outstanding Questions Before the Gate Can Close
1. What is the approved reporting treatment when a Won or Lost Opportunity is reopened?
2. What precise permission exceptions, if any, can CRM Admin exercise over quotation approvals and sharing?
3. What quotation retention, identifier, revision numbering, and post-edit reapproval rules will apply?
4. What mechanism defines and retains historical reporting snapshots?
5. Are the proposed D-11, D-14, D-12, D-13, and reopening policies formally approved by the named decision owners?
6. Has the implementation/test plan been accepted, and has written Managing Director authorization been issued?
These items must be answered or explicitly dispositioned by the appropriate owners before the pre-implementation gate is declared complete.
9.9 Non-Execution Confirmation
This register update is documentation only. It does not implement application behavior, create or alter migrations, change the live database, or authorize Phase 5A implementation. All implementation guardrails in Section 8 remain in force.
Final execution status: SPEC & PLAN ONLY. Implementation authorization is NOT GRANTED.