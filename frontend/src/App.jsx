import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import CentralPortalPage, { getBreakfastDestination } from './pages/CentralPortalPage';
import EmployeeDailyPage from './pages/EmployeeDailyPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import TodayBreakfastListPage from './pages/TodayBreakfastListPage';
import BreakfastOrdersPage from './pages/BreakfastOrdersPage';
import EmployeeManagementPage from './pages/EmployeeManagementPage';
import PublicHolidaysPage from './pages/PublicHolidaysPage';
import ReportsPage from './pages/ReportsPage';
import CEOViewPage from './pages/CEOViewPage';
import DirectorAnalyticsPage from './pages/DirectorAnalyticsPage';
import AuditLogsPage from './pages/AuditLogsPage';
import SettingsPage from './pages/SettingsPage';

import DailyEntryPage from './pages/DailyEntryPage';
import AdditionalOrdersPage from './pages/AdditionalOrdersPage';
import BreakfastMoneyPage from './pages/BreakfastMoneyPage';
import FinanceManagerPage from './pages/FinanceManagerPage';
import UserManagementPage from './pages/UserManagementPage';

import BMSLayout from './layouts/BMSLayout';
import UserManagementLayout from './layouts/UserManagementLayout';

function AppRoutes() {
  const { user, hasPermission, hasRole, hasModuleAccess, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
        Loading session...
      </div>
    );
  }

  const canAccessBreakfast = () => {
    if (!user) return false;
    return hasModuleAccess('BMS') || hasRole('IT_ADMIN') || hasPermission('*');
  };

  return (
    <Routes>
      {/* Root redirects to Central Portal if logged in, otherwise Login */}
      <Route path="/" element={<Navigate to={user ? "/portal" : "/login"} replace />} />

      {/* Login redirects to Central Portal if already authenticated */}
      <Route path="/login" element={user ? <Navigate to="/portal" replace /> : <LoginPage />} />

      {/* 1. CENTRAL PORTAL (Module Selection) */}
      <Route
        path="/portal"
        element={
          user ? (
            <CentralPortalPage />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* ========================================================================= */}
      {/* 2. USER MANAGEMENT MODULE (Dedicated UserManagementLayout & Sidebar)       */}
      {/* ========================================================================= */}
      <Route
        path="/user-management"
        element={
          <UserManagementLayout>
            <UserManagementPage />
          </UserManagementLayout>
        }
      />
      <Route
        path="/user-management/users"
        element={
          <UserManagementLayout>
            <UserManagementPage />
          </UserManagementLayout>
        }
      />
      {/* Backward-compatible /users path */}
      <Route
        path="/users"
        element={
          <UserManagementLayout>
            <UserManagementPage />
          </UserManagementLayout>
        }
      />

      {/* ========================================================================= */}
      {/* 3. BREAKFAST MANAGEMENT SYSTEM (BMS) (Dedicated BMSLayout & BMSSidebar)    */}
      {/* ========================================================================= */}
      {/* Gateway route for BMS -> forwards to user's role-based breakfast destination */}
      <Route
        path="/breakfast"
        element={
          user ? (
            canAccessBreakfast() ? (
              <Navigate to={getBreakfastDestination(hasPermission, hasRole)} replace />
            ) : (
              <Navigate to="/portal" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/bms"
        element={<Navigate to="/breakfast" replace />}
      />

      {/* BMS: Personal Breakfast Response */}
      <Route
        path="/today"
        element={
          <BMSLayout>
            <EmployeeDailyPage />
          </BMSLayout>
        }
      />
      <Route
        path="/response"
        element={
          <BMSLayout>
            <EmployeeDailyPage />
          </BMSLayout>
        }
      />
      <Route
        path="/breakfast-response"
        element={
          <BMSLayout>
            <EmployeeDailyPage />
          </BMSLayout>
        }
      />

      {/* BMS: Admin Dashboard */}
      <Route
        path="/admin/dashboard"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <AdminDashboardPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/dashboard"
        element={<Navigate to="/admin/dashboard" replace />}
      />

      {/* BMS: Daily Entry */}
      <Route
        path="/admin/daily-entry"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <DailyEntryPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/daily-entry"
        element={<Navigate to="/admin/daily-entry" replace />}
      />

      {/* BMS: Additional Orders */}
      <Route
        path="/admin/additional-orders"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <AdditionalOrdersPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/additional-orders"
        element={<Navigate to="/admin/additional-orders" replace />}
      />

      {/* BMS: Breakfast Money */}
      <Route
        path="/admin/breakfast-money"
        element={
          <BMSLayout requiredPermission="breakfast.money.view">
            <BreakfastMoneyPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/breakfast-money"
        element={<Navigate to="/admin/breakfast-money" replace />}
      />

      {/* BMS: Finance Fund Requests */}
      <Route
        path="/finance/fund-requests"
        element={
          <BMSLayout requiredPermission="finance.breakfast_fund.view">
            <FinanceManagerPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/fund-requests"
        element={<Navigate to="/finance/fund-requests" replace />}
      />

      {/* BMS: Today's Breakfast List */}
      <Route
        path="/admin/today-breakfast"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <TodayBreakfastListPage />
          </BMSLayout>
        }
      />
      <Route
        path="/admin/today-list"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <TodayBreakfastListPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/today-breakfast"
        element={<Navigate to="/admin/today-breakfast" replace />}
      />

      {/* BMS: All Orders */}
      <Route
        path="/admin/orders"
        element={
          <BMSLayout requiredPermission={['breakfast.view', 'breakfast.orders.view']}>
            <BreakfastOrdersPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/orders"
        element={<Navigate to="/admin/orders" replace />}
      />

      {/* BMS: Employees Directory */}
      <Route
        path="/admin/employees"
        element={
          <BMSLayout requiredPermission="breakfast.employee.read">
            <EmployeeManagementPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/employees"
        element={<Navigate to="/admin/employees" replace />}
      />

      {/* BMS: Public Holidays */}
      <Route
        path="/holidays"
        element={
          <BMSLayout requiredPermission="breakfast.view">
            <PublicHolidaysPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/holidays"
        element={<Navigate to="/holidays" replace />}
      />

      {/* BMS: Reports */}
      <Route
        path="/reports"
        element={
          <BMSLayout requiredPermission={['breakfast.report', 'breakfast.money.report']}>
            <ReportsPage />
          </BMSLayout>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <BMSLayout requiredPermission={['breakfast.report', 'breakfast.money.report']}>
            <ReportsPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/reports"
        element={<Navigate to="/reports" replace />}
      />

      {/* BMS: Director Analytics */}
      <Route
        path="/director-analytics"
        element={
          <BMSLayout requiredRole="DIRECTOR_ANALYTICS">
            <DirectorAnalyticsPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/director-analytics"
        element={<Navigate to="/director-analytics" replace />}
      />

      {/* BMS: Directors Dashboard (CEO) */}
      <Route
        path="/ceo-dashboard"
        element={
          <BMSLayout requiredRole="CEO">
            <CEOViewPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/ceo-dashboard"
        element={<Navigate to="/ceo-dashboard" replace />}
      />

      {/* BMS: Audit Logs */}
      <Route
        path="/audit-logs"
        element={
          <BMSLayout requiredPermission="breakfast.audit.view">
            <AuditLogsPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/audit-logs"
        element={<Navigate to="/audit-logs" replace />}
      />

      {/* BMS: Settings */}
      <Route
        path="/settings"
        element={
          <BMSLayout requiredPermission="breakfast.settings.manage">
            <SettingsPage />
          </BMSLayout>
        }
      />
      <Route
        path="/bms/settings"
        element={<Navigate to="/settings" replace />}
      />

      {/* ========================================================================= */}
      {/* 4. FUTURE MODULE PLACEHOLDERS (Disabled / Coming Soon)                     */}
      {/* ========================================================================= */}
      <Route path="/mis/*" element={<Navigate to="/portal" replace />} />
      <Route path="/crm/*" element={<Navigate to="/portal" replace />} />
      <Route path="/lms/*" element={<Navigate to="/portal" replace />} />
      <Route path="/ims/*" element={<Navigate to="/portal" replace />} />
      <Route path="/leave-management/*" element={<Navigate to="/portal" replace />} />
      <Route path="/dwr/*" element={<Navigate to="/portal" replace />} />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to={user ? "/portal" : "/login"} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}
