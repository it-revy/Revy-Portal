# REVY CRM Module — Core Architecture, APIs, RBAC & Workflows

## 1. Overview & Architectural Scope
The **REVY Customer Relationship Management (CRM)** module provides comprehensive customer account tracking, contact governance, lead lifecycle management, and chronological customer interaction history within the REVY Enterprise Portal.

The module strictly enforces centralized Role-Based Access Control (RBAC), multi-channel interaction tracking, concurrency-safe sequential ID generation (`LEAD-00001`, `ACC-00001`, `CON-00001`, `COM-00001`), and database-level duplicate open lead prevention.

---

## 2. Canonical Data Models & Database Migrations

### Tables & Relational Schema:
- **`crm_accounts`**: Corporate client entities with normalized company name, industry, website, phone, email, address, and status.
- **`crm_contacts`**: Individual stakeholder contacts with name, designation, email, mobile number, and optional `account_id` foreign key. Contacts can exist independently or linked to an Account.
- **`crm_sequences`**: Pessimistic row-locking sequence generator supporting concurrent transactional generation of zero-padded identifiers.
- **`leads`**: Central lead pipeline records with:
  - `lead_id`: Human-readable identifier (`LEAD-00001`).
  - `lead_name`: Descriptive opportunity title.
  - `business_area`: Strictly constrained to `Biogas` or `WWT`.
  - `requirement_type`: Constrained to `Direct Product/Service`, `Sample Testing`, or `Undetermined`.
  - `requested_product_service`: Exact client specification.
  - `normalized_requirement`: Lowercased, stripped, whitespace-collapsed string for duplicate detection.
  - `lifecycle_status`: `Open`, `Qualified`, or `Disqualified`.
  - `contact_id`: Mandatory foreign key referencing `crm_contacts.id`.
  - `account_id`: Optional foreign key referencing `crm_accounts.id`.
  - `assigned_to_user_id`: Foreign key referencing active portal user with an eligible CRM role.
  - `last_connected_date`: Timestamp updated only upon qualifying client-facing interactions.
  - `next_follow_up_date` & `next_follow_up_action`: Next scheduled interaction details.
  - `remarks`: Latest summary context.
- **`lead_communication_history`**: Chronological log of interactions (`COM-00001`) with channel, event type, communication date, summary, outcome, next action, follow-up date, and logging user attribution.

### Database Migrations Applied:
1. **`c1r2m3l4e5a6`**: Initial CRM schema (`accounts`, `contacts`, `crm_sequences`, `leads`, `lead_communication_history`).
2. **`d1e2f3a4b5c6`**: Added `normalized_requirement` column and two partial unique indexes:
   - `uq_open_lead_account_product`: Unique on `(account_id, normalized_requirement)` WHERE `lifecycle_status = 'Open' AND account_id IS NOT NULL`.
   - `uq_open_lead_contact_product`: Unique on `(contact_id, normalized_requirement)` WHERE `lifecycle_status = 'Open' AND account_id IS NULL`.

---

## 3. CRM Roles & RBAC Matrix

Access is governed by active user membership in the `CRM` module with one of the canonical CRM roles:

| Role Code | Role Name | Leads View | Lead Create / Edit | Status Transition | Log Interactions | Dashboard Metrics | CRM User Hub (`crm.user.manage`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `CRM_ADMIN` | CRM Administrator | Yes | Yes | Yes | Yes | Yes | **Yes** |
| `CRM_SALES_MANAGER` | CRM Sales Manager | Yes | Yes | Yes | Yes | Yes | No |
| `CRM_SALES_REP` | CRM Sales Representative | Yes | Yes | Yes | Yes | Yes | No |
| `CRM_PRE_SALES` | CRM Pre-Sales Technical | Yes | Yes (Technical) | No | Yes | Yes | No |
| `CRM_FINANCE_MANAGER` | CRM Finance Manager | **Read-Only** | No | No | No | **Read-Only** | No |
| *Non-CRM Users* | Portal / BMS Employees | Blocked (403) | Blocked (403) | Blocked (403) | Blocked (403) | Blocked (403) | Blocked (403) |

*Global System Roles (`IT_ADMIN`, `DIRECTOR`) inherit full operational and administrative authority across all modules.*

---

## 4. API Endpoints & Specification

All endpoints are dual-mounted under `/api/v1` and `/api` and require a valid Bearer JWT.

### Dashboard & Analytics:
- `GET /crm/dashboard/metrics`: Live database aggregation of `totalLeads`, `openLeads`, `qualifiedLeads`, `disqualifiedLeads`, `myLeads`, `followUpsDue`, and `overdueFollowUps`.

### Leads Management:
- `GET /crm/leads`: Search, filter, sort, and paginate leads.
  - Query parameters: `view` (`open`, `all`, `unqualified`, `my_leads`, `follow_ups_due`), `search`, `businessArea`, `requirementType`, `lifecycleStatus`, `assignedToUserId`, `accountId`, `sortBy`, `sortOrder`, `page`, `pageSize`.
- `GET /crm/leads/{id}`: Detailed lead record including joined Account, Contact, and Assignee data.
- `POST /crm/leads`: Create lead. Validates duplicate open leads, active CRM assignee, and required contact. Returns HTTP `409 Conflict` on duplicates.
- `PUT /crm/leads/{id}`: Update lead specifications, follow-ups, or reassign lead.
- `PUT /crm/leads/{id}/status`: Transition lifecycle status (`Open`, `Qualified`, `Disqualified`) with mandatory transition remarks. Enforces duplicate check if reopening to `Open`.

### Communications & Interaction History:
- `GET /crm/leads/{id}/communications`: Chronological list of recorded interactions.
- `POST /crm/leads/{id}/communications`: Record customer interaction. Automatically advances `last_connected_date` if the event is a qualifying client-facing milestone.

### Accounts & Contacts:
- `GET /crm/accounts`: Search and list corporate accounts.
- `GET /crm/accounts/{id}`: Account details with associated contacts.
- `POST /crm/accounts`: Duplicate-aware account quick-create (HTTP 409 if company name exists).
- `GET /crm/contacts`: Search and list contacts (filter by `accountId`).
- `GET /crm/contacts/{id}`: Contact details.
- `POST /crm/contacts`: Duplicate-aware contact quick-create (HTTP 409 if email or phone exists).
- `GET /crm/assignees`: List active portal users with active CRM roles eligible for lead assignment.

### CRM User Hub (Admin Only):
- `GET /crm/users`: Search and list portal users with CRM membership status, role, and assigned lead counts.
- `GET /crm/roles`: List CRM assignable roles.
- `POST /crm/users/{id}/access`: Enable or disable CRM access (disabling preserves historical leads, ownership, and audit attribution).
- `PUT /crm/users/{id}/role`: Assign or change user's CRM role.

---

## 5. Saved-View Definitions & Metric Semantics

### Saved Views in Leads Workspace:
1. **Open Leads (`view=open`)**:
   - Queries `lifecycle_status = 'Open'`.
   - Represents the active pool of client enquiries currently undergoing technical evaluation, sizing, or negotiation.
2. **All Leads (`view=all`)**:
   - Returns all leads regardless of status. Allows optional faceted filtering by `lifecycleStatus` (`Open`, `Qualified`, `Disqualified`).
3. **Unqualified Leads (`view=unqualified`)**:
   - **Confirmed Business Definition**: Leads that have been evaluated and determined not to meet commercial or technical feasibility criteria (persisted as `Disqualified` in the backend lifecycle status).
   - Leads awaiting initial evaluation remain in the `Open Leads` view.
4. **My Leads (`view=my_leads`)**:
   - Filtered to leads assigned to the currently authenticated user (`assigned_to_user_id == current_user.id`).
5. **Follow-ups Due (`view=follow_ups_due`)**:
   - Queries open leads where `next_follow_up_date` is within the next 24 hours (`<= now + 24 hours`) or currently overdue (`< now`).

---

## 6. Duplicate Open Lead Rule & ID Generation

### Duplicate Rule:
- A new lead is rejected with HTTP `409 Conflict` if an active lead (`lifecycle_status = 'Open'`) already exists for:
  - The same `account_id` and `normalized_requirement` (when Account is provided).
  - The same `contact_id` and `normalized_requirement` (when no Account is provided).
- Distinct requested products/services for the same client are permitted.
- New leads are permitted for previously matching requirements once the earlier lead transitions to `Qualified` or `Disqualified`.
- Partial unique database indexes (`uq_open_lead_account_product`, `uq_open_lead_contact_product`) guarantee race-condition safety under concurrent client submissions.

---

## 7. Frontend Routes & UI Structure

- `/crm/dashboard`: Live KPI metrics cards, quick navigation, and pipeline summary.
- `/crm/leads`: Primary leads pipeline workspace with tabs for the 5 saved views, search, faceted filters, allowlisted sorting, server-side pagination, and quick-create modals.
- `/crm/leads/:id`: Comprehensive lead detail dossier with specification breakdown, remarks summary, chronological communication timeline, and status transition dialogs.
- `/crm/user-hub`: Administrative access management interface visible strictly to `CRM_ADMIN` and global administrators.

---

## 8. Verification & Test Commands

### Backend Automated Test Suites:
```powershell
# CRM Core Services & APIs (9 tests)
pytest tests/test_crm_core_services_and_apis.py -v

# CRM User Hub & RBAC Suite (10 tests)
pytest tests/test_crm_user_hub_and_rbac.py -v

# Centralized System Roles & Core Auth Regressions (10 tests)
pytest tests/test_centralized_system_roles.py tests/test_auth.py -v

# BMS Master Workflow Regressions (7 tests)
pytest tests/test_breakfast_master_workflow.py -v
```

### Frontend Production Build:
```powershell
npm run build
```
*Result: Clean bundle build in ~515ms with 0 compilation errors.*

### Environment Notes:
- SQLite test suite uses database file locks; PostgreSQL production database natively supports row-level locks and partial unique indexes for high-throughput concurrency.
- Browser-level testing: No standalone Playwright or Cypress suite was configured in the repository; all endpoint contracts, payload serialization, and authorization rules are verified via TestClient and Vite build validation.
