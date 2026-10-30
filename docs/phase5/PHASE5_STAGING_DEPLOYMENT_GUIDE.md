# REVY Portal — Phase 5A Staging Deployment & Verification Guide

**Document:** `docs/phase5/PHASE5_STAGING_DEPLOYMENT_GUIDE.md`  
**Milestone:** Phase 5A — Sales Hub & Opportunity Lifecycle Enhancement  
**Status:** Ready for Staging Execution  
**Target Migration:** `n1o2p3q4r5s6`  
**Date:** 27 October 2026  

---

## 1. Safety Policies & Architecture Guardrails

1. **Production Isolation:**
   - The production database is hosted on AWS Neon (`ep-silent-sound-b49uucbd-pooler.c-6.us-east-2.aws.neon.tech/neondb`).
   - The repository contains an active safety interceptor in [`backend/migrations/env.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/migrations/env.py) and [`backend/scripts/run_staging_migration.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/scripts/run_staging_migration.py) that **strictly aborts** if an attempt is made to run staging migrations against the production Neon host.
   - Credentials must never be logged or committed.
2. **Layer 1 Scope Boundary:**
   - Phase 5A covers Sales Hub only (6-stage funnel, quotation lifecycle, manager approvals, deal reopening, currency-grouped reporting).
   - Operational workflows (LMS sample intake, lab worksheets, 3-tier lab approvals, inventory movements, tax invoicing, payments) are strictly excluded.

---

## 2. Step-by-Step Staging Database Provisioning

To execute Phase 5A verification on a real PostgreSQL environment, an isolated staging database must be provisioned. Choose one of the two options below:

### Option A: Neon Staging Branch (Recommended for Cloud Parity)
1. Log into your [Neon Console](https://console.neon.tech).
2. Navigate to the `revy-portal` project.
3. Under **Branches**, click **Create Branch**.
   - Branch Name: `staging-phase5a`
   - Parent: `main` (or latest baseline snapshot)
4. Copy the connection string for `staging-phase5a` (ensure it uses `postgresql://...`).
5. Set the connection string in your local environment or `.env.staging`:
   ```powershell
   $env:STAGING_DATABASE_URL = "postgresql://user:password@ep-staging-branch.us-east-2.aws.neon.tech/neondb?sslmode=require"
   ```

### Option B: Local / Dedicated Staging PostgreSQL
1. Start an isolated PostgreSQL instance (e.g. Docker container or local PostgreSQL service on port 5432):
   ```bash
   docker run --name revy-staging-db -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=revy_staging -p 5432:5432 -d postgres:16-alpine
   ```
2. Set `STAGING_DATABASE_URL`:
   ```powershell
   $env:STAGING_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/revy_staging"
   ```

---

## 3. Running the Staging Migration

### Dry-Run Verification
Before applying changes, execute the dry-run command to test connectivity and verify that the target is NOT production:
```powershell
cd "backend"
.\venv\Scripts\python.exe scripts/run_staging_migration.py --dry-run
```

Expected output:
```
[INFO] Validating STAGING_DATABASE_URL configuration...
[INFO] Resolved target host: <staging-host>
[INFO] Resolved target database: <staging-db>
[INFO] Connection to staging database verified successfully!
[INFO] Safety check passed: Target is NOT production Neon.
[SUCCESS] Dry run passed cleanly.
```

### Applying Migration `n1o2p3q4r5s6`
Apply the migration to staging:
```powershell
.\venv\Scripts\python.exe scripts/run_staging_migration.py
```

Or via Alembic with the staging flag:
```powershell
.\venv\Scripts\python.exe -m alembic -x staging=true upgrade head
```

---

## 4. Post-Migration Verification Queries

Connect to the staging database and run the following queries to verify the schema:

1. **Verify Alembic Revision:**
   ```sql
   SELECT version_num FROM alembic_version;
   -- Expected: n1o2p3q4r5s6
   ```

2. **Verify Table and Primary Key:**
   ```sql
   SELECT table_name, column_name, data_type, is_nullable
   FROM information_schema.columns 
   WHERE table_name = 'crm_opportunity_quotations'
   ORDER BY ordinal_position;
   -- Expected: 32 columns (id, opportunity_id, quotation_number, revision_number, ...)
   ```

3. **Verify Composite Unique Constraint:**
   ```sql
   SELECT conname, pg_get_constraintdef(c.oid)
   FROM pg_constraint c
   JOIN pg_class t ON c.conrelid = t.oid
   WHERE t.relname = 'crm_opportunity_quotations' AND c.contype = 'u';
   -- Expected: uq_crm_opportunity_quotations_num_rev UNIQUE (quotation_number, revision_number)
   ```

4. **Verify Indexes:**
   ```sql
   SELECT indexname, indexdef
   FROM pg_indexes
   WHERE tablename = 'crm_opportunity_quotations';
   -- Expected: 6 indexes (opp_id, status, quotation_number, is_current, created_at, pkey)
   ```

---

## 5. Rollback Procedure (Emergency / Rehearsal Only)

To revert the staging database back to the pre-Phase 5A baseline (`m0n1o2p3q4r5`):

```powershell
cd "backend"
.\venv\Scripts\python.exe -m alembic -x staging=true downgrade m0n1o2p3q4r5
```

Verification after downgrade:
```sql
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_name = 'crm_opportunity_quotations'
);
-- Expected: false
```

*Note: The rollback procedure was verified on a disposable test engine ([`backend/scripts/verify_disposable_rollback.py`](file:///e:/IT%20Development/REVY%20Portal/Revy-Portal/backend/scripts/verify_disposable_rollback.py)) and cleanly drops the table and indexes without residual objects.*

---

## 6. UAT Execution Checklist

Once staging migration is applied:
1. Start the staging backend pointing to `STAGING_DATABASE_URL`:
   ```powershell
   $env:DATABASE_URL = $env:STAGING_DATABASE_URL
   uvicorn app.main:app --host 127.0.0.1 --port 5000
   ```
2. Start the frontend:
   ```powershell
   npm run dev
   ```
3. Execute the 3 UAT tracks:
   - **Track 1 (Sales Executive):** Create quotations, submit for review, share with client, create new revisions.
   - **Track 2 (Sales Manager):** Approve/reject quotations, edit approved quotes to test invalidation, reopen Won/Lost deals.
   - **Track 3 (CRM Admin):** Confirm `CRM_ADMIN` cannot bypass quote approval (HTTP 403), audit trail inspection.
