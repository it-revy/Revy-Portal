# REVY Breakfast Management System

A production-grade, enterprise modular monolith for **Breakfast Management** built with **FastAPI**, **PostgreSQL (SQLAlchemy + Alembic)**, and **React**.

Designed as a core foundational module for the **REVY Centralized Enterprise Management System**, featuring unified employee/user models, permission-based RBAC, authoritative financial ledger management, audit trails, and seamless Microsoft Azure / Entra ID readiness.

---

## 🏗️ Architecture Overview

The system follows a clean **Modular Monolith** architecture:

```text
                 EXISTING REACT UI
                        │
                        ▼
              API SERVICE LAYER (frontend/src/services/)
                        │
                        ▼
            FASTAPI GATEWAY (backend/app/main.py)
            Mounted at /api/v1 (Standard) & /api (Legacy Compatibility)
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
      Auth          Employees       Breakfast        Reports
   (JWT / SSO)     (Users & RBAC) (Orders & Ledger) (Excel / CEO)
        │               │               │               │
        └───────────────┴───────┬───────┴───────────────┘
                                ▼
                       SQLAlchemy ORM (2.0)
                                │
                                ▼
                    PostgreSQL Database (Alembic)
```

### Module Structure (`backend/app/`):
```text
backend/app/
├── core/               # App configuration, database pooling, security, RBAC dependencies, logging
├── auth/               # JWT authentication, login, password change, future Entra SSO adapter
├── users/              # User entity, password hashing, active status
├── employees/          # Employee entity, department mapping, participation types, management APIs
├── roles/              # Dynamic roles and granular permissions matrix
├── breakfast/          # Daily responses, cutoff checks, daily entries, additional orders, money ledger
├── audit/              # Comprehensive audit logging across all state-mutating actions
├── notifications/      # In-app notifications foundation (Teams/Email ready)
├── files/              # File storage provider abstraction (Local & Azure Blob Storage)
└── reports/            # Monthly aggregation, working days calculation, 4-sheet Excel generator
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, React Router v6, Tailwind / CSS, Lucide Icons, Axios |
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, Uvicorn, Passlib (Bcrypt), Python-JOSE |
| **ORM & Migrations** | SQLAlchemy 2.0, Alembic |
| **Database** | PostgreSQL 15+ (with SQLite dev/fallback support) |
| **Reporting** | openpyxl (4-sheet formatted Excel workbook), Pandas-ready |
| **Containerization** | Docker, Docker Compose (FastAPI + PostgreSQL + Redis + Frontend) |
| **Cloud Target** | Microsoft Azure (App Service, Azure Database for PostgreSQL, Azure Blob, Entra ID) |

---

## 📋 Prerequisites & Requirements

- **Python**: 3.10 or higher
- **Node.js**: 18.x or 20.x
- **PostgreSQL**: 14+ (or Docker)
- **Git**

---

## 🚀 Installation & Local Setup

### 1. Clone & Set Up Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example template:
```bash
cp .env.example .env
```

Configure your `.env` file:
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/breakfast_db
JWT_SECRET=super_secret_jwt_key_revy_breakfast_32chars
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
APP_TIMEZONE=Asia/Kolkata
HOST=0.0.0.0
PORT=5000
```
*(Note: If PostgreSQL is not running locally, the application automatically falls back to local SQLite `breakfast.db` for instant development).*

### 3. Run Database Migrations (Alembic)

```bash
# Upgrade database to latest revision
alembic upgrade head
```

### 4. Seed Development Accounts & Initial Settings

```bash
python seed/seed_development.py
```

This creates platform roles, permissions, breakfast settings, departments, and 9 standard accounts:
- `vasudev` (IT Admin) — `Vasudev123`
- `faiz` (Breakfast Admin) — `Faiz123`
- `rajneesh` (Breakfast Admin) — `Rajneesh123`
- `jyoti` (Normal Employee) — `Jyoti123`
- `finance.manager` (Finance Manager) — `Finance123`
- Additional test employee accounts

### 5. Start Backend Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```
Interactive API Documentation will be available at:
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`
- Health check: `http://localhost:5000/api/health`

### 6. Set Up and Run React Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Running Automated Tests

A comprehensive Pytest test suite validates all workflows, RBAC enforcement, financial calculations, and reports:

```bash
cd backend
pytest -v tests
```

### Test Coverage Highlights:
- **Authentication**: Login, invalid credentials, password change enforcement, role validation.
- **Breakfast Workflow**: Daily submission cutoff checks, multi-day absence submission, response aggregation.
- **Daily Entry & Orders**: Daily breakfast entry expense calculation, additional order creation, order deletion reversal.
- **Financial Ledger**: End-to-end fund request lifecycle (`Draft` → `Approved` → `Provided` → `Verified`), manual expense deduction, shortfall safety checks, daily/monthly statements.
- **Employee CRUD**: Soft deactivation, designation updates, password reset.
- **Holidays & Settings**: Public holidays, dynamic cutoff time updates, reason catalog.
- **Reporting & Excel**: Monthly summary matrices, CEO dashboard, formatted `.xlsx` export.

---

## 🐳 Docker & Containerization

Run the entire stack (FastAPI, PostgreSQL, Redis, and React Frontend) with a single command:

```bash
docker-compose up --build
```

Services exposed:
- **Frontend**: `http://localhost:5173`
- **FastAPI Backend**: `http://localhost:5000`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

To run in the background:
```bash
docker-compose up -d
```

To stop containers:
```bash
docker-compose down -v
```

---

## 🔄 MongoDB → PostgreSQL Data Migration

To migrate existing production records from MongoDB to the normalized PostgreSQL schema without data loss:

```bash
cd backend
python scripts/migrate_mongodb_to_postgresql.py --mongo-uri "mongodb+srv://user:pass@cluster.mongodb.net/company_platform" --db-name company_platform
```

### Migration Verification Pipeline:
1. Validates connection to MongoDB and PostgreSQL.
2. Migrates platform permissions, roles, and departments.
3. Maps MongoDB `ObjectId` strings to relational entities.
4. Migrates Users and Employees, preserving password hashes and active status.
5. Migrates Settings, Reasons, and Public Holidays.
6. Migrates Breakfast Responses, Multi-day Absences, and Daily Records.
7. Migrates Daily Breakfast Entries and Additional Orders.
8. Migrates Fund Requests and authoritative Financial Ledger Transactions.
9. Migrates Audit Logs.
10. Validates foreign key constraints, transaction balance sums, and prints a detailed summary report.

---

## 🔐 Role-Based Access Control (RBAC)

Authorization is enforced server-side via granular permissions rather than hardcoded role strings:

| Permission Code | Description | Default Roles |
|---|---|---|
| `breakfast.view_own` | View own daily breakfast form and history | EMPLOYEE |
| `breakfast.submit` | Submit YES/NO breakfast response | EMPLOYEE |
| `breakfast.manage` | Manage company records, daily entries, orders | BREAKFAST_ADMIN |
| `breakfast.money.request` | Request money from Finance | BREAKFAST_ADMIN |
| `breakfast.money.receive` | Record funds received | BREAKFAST_ADMIN |
| `finance.breakfast_fund.approve` | Approve breakfast fund request | FINANCE_MANAGER |
| `finance.breakfast_fund.provide` | Provide funds for approved request | FINANCE_MANAGER |
| `breakfast.employee.create` | Add new employees to system | IT_ADMIN |
| `breakfast.dashboard.view` | Access CEO / Executive analytics | CEO |
| `*` | Full system access | IT_ADMIN |

Active role switching via the `X-Role-Used` header allows users with multiple roles to switch contexts dynamically without re-authenticating.

---

## ☁️ Azure Cloud Deployment Guide

The application is structured for native deployment to Microsoft Azure:

### 1. PostgreSQL Database
- Provision an **Azure Database for PostgreSQL Flexible Server**.
- Set the connection string in App Service:
  ```text
  DATABASE_URL=postgresql+psycopg2://<admin>:<password>@<server-name>.postgres.database.azure.com:5432/<dbname>?sslmode=require
  ```

### 2. FastAPI Backend
- Deploy to **Azure App Service (Linux, Python 3.10+)**.
- Startup command:
  ```bash
  alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 5000
  ```

### 3. React Frontend
- Deploy the `frontend/dist` bundle to **Azure Static Web Apps**.
- Configure `staticwebapp.config.json` with fallback routing to `index.html`.

### 4. File Storage
- Configure `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER` in environment variables.
- The `app.files` module automatically routes uploads to **Azure Blob Storage**.

### 5. Microsoft 365 / Entra ID SSO
- Register an app in **Microsoft Entra ID**.
- Configure `ENTRA_CLIENT_ID`, `ENTRA_TENANT_ID`, and `ENTRA_CLIENT_SECRET`.

---

## 📄 License & Confidentiality

Proprietary software of **REVY Environmental Solutions**. All rights reserved.
