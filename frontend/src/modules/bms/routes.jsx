import React from 'react';
import { Route, Navigate } from 'react-router-dom';

import EmployeeDailyPage from '../../pages/EmployeeDailyPage';
import AdminDashboardPage from '../../pages/AdminDashboardPage';
import DailyEntryPage from '../../pages/DailyEntryPage';
import BreakfastOrdersPage from '../../pages/BreakfastOrdersPage';
import AdditionalOrdersPage from '../../pages/AdditionalOrdersPage';
import BreakfastMoneyPage from '../../pages/BreakfastMoneyPage';
import FinanceManagerPage from '../../pages/FinanceManagerPage';
import EmployeeManagementPage from '../../pages/EmployeeManagementPage';
import PublicHolidaysPage from '../../pages/PublicHolidaysPage';
import ReportsPage from '../../pages/ReportsPage';
import CEOViewPage from '../../pages/CEOViewPage';
import AuditLogsPage from '../../pages/AuditLogsPage';
import SettingsPage from '../../pages/SettingsPage';
import BMSLayout from '../../layouts/BMSLayout';

export function getBMSRoutes() {
  return [
    // Canonical BMS Routes
    <Route
      key="bms-response"
      path="/bms/response"
      element={
        <BMSLayout>
          <EmployeeDailyPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-today"
      path="/bms/today"
      element={
        <BMSLayout>
          <EmployeeDailyPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-dashboard"
      path="/bms/dashboard"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <AdminDashboardPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-daily-entry"
      path="/bms/daily-entry"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <DailyEntryPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-orders"
      path="/bms/orders"
      element={
        <BMSLayout requiredPermission="breakfast.orders.view">
          <BreakfastOrdersPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-additional-orders"
      path="/bms/additional-orders"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <AdditionalOrdersPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-money"
      path="/bms/money"
      element={
        <BMSLayout requiredPermission="breakfast.money.view">
          <BreakfastMoneyPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-breakfast-money"
      path="/bms/breakfast-money"
      element={<Navigate to="/bms/money" replace />}
    />,
    <Route
      key="bms-finance"
      path="/bms/finance"
      element={
        <BMSLayout requiredPermission="finance.breakfast_fund.view">
          <FinanceManagerPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-employees"
      path="/bms/employees"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <EmployeeManagementPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-holidays"
      path="/bms/holidays"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <PublicHolidaysPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-reports"
      path="/bms/reports"
      element={
        <BMSLayout requiredPermission="breakfast.report">
          <ReportsPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-ceo-view"
      path="/bms/ceo-view"
      element={
        <BMSLayout requiredRole="CEO">
          <CEOViewPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-audit-logs"
      path="/bms/audit-logs"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <AuditLogsPage />
        </BMSLayout>
      }
    />,
    <Route
      key="bms-settings"
      path="/bms/settings"
      element={
        <BMSLayout requiredPermission="breakfast.view">
          <SettingsPage />
        </BMSLayout>
      }
    />,

    // Backward-Compatibility Redirects for Legacy URLs
    <Route key="legacy-today" path="/today" element={<Navigate to="/bms/response" replace />} />,
    <Route key="legacy-response" path="/response" element={<Navigate to="/bms/response" replace />} />,
    <Route key="legacy-breakfast-response" path="/breakfast-response" element={<Navigate to="/bms/response" replace />} />,
    <Route key="legacy-admin-dashboard" path="/admin/dashboard" element={<Navigate to="/bms/dashboard" replace />} />,
    <Route key="legacy-admin-daily-entry" path="/admin/daily-entry" element={<Navigate to="/bms/daily-entry" replace />} />,
    <Route key="legacy-admin-orders" path="/admin/orders" element={<Navigate to="/bms/orders" replace />} />,
    <Route key="legacy-admin-additional-orders" path="/admin/additional-orders" element={<Navigate to="/bms/additional-orders" replace />} />,
    <Route key="legacy-admin-breakfast-money" path="/admin/breakfast-money" element={<Navigate to="/bms/money" replace />} />,
    <Route key="legacy-finance-fund-requests" path="/finance/fund-requests" element={<Navigate to="/bms/finance" replace />} />,
    <Route key="legacy-employees" path="/employees" element={<Navigate to="/bms/employees" replace />} />,
    <Route key="legacy-admin-holidays" path="/admin/holidays" element={<Navigate to="/bms/holidays" replace />} />,
    <Route key="legacy-reports" path="/reports" element={<Navigate to="/bms/reports" replace />} />,
    <Route key="legacy-ceo-dashboard" path="/ceo-dashboard" element={<Navigate to="/bms/ceo-view" replace />} />,
    <Route key="legacy-audit-logs" path="/audit-logs" element={<Navigate to="/bms/audit-logs" replace />} />,
    <Route key="legacy-settings" path="/settings" element={<Navigate to="/bms/settings" replace />} />
  ];
}

export default getBMSRoutes;
