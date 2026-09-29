import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

import Sidebar from './components/Sidebar';
import Header from './components/Header';

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
import AuditLogsPage from './pages/AuditLogsPage';
import SettingsPage from './pages/SettingsPage';

import DailyEntryPage from './pages/DailyEntryPage';
import AdditionalOrdersPage from './pages/AdditionalOrdersPage';
import BreakfastMoneyPage from './pages/BreakfastMoneyPage';
import FinanceManagerPage from './pages/FinanceManagerPage';

import ForcePasswordChangeModal from './components/ForcePasswordChangeModal';

const ProtectedLayout = ({ children, requiredPermission }) => {
  const { user, loading, hasPermission } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const checkPermission = () => {
    if (!requiredPermission) {
      // Require at least basic breakfast access for breakfast routes
      const baseBreakfastPerms = [
        '*',
        'breakfast.view',
        'breakfast.view_own',
        'breakfast.submit',
        'breakfast.manage',
        'breakfast.report',
        'breakfast.dashboard.view',
        'finance.breakfast_fund.view'
      ];
      return baseBreakfastPerms.some(p => hasPermission(p));
    }
    if (Array.isArray(requiredPermission)) {
      return requiredPermission.some(p => hasPermission(p));
    }
    return hasPermission(requiredPermission);
  };

  if (!checkPermission()) {
    return (
      <div className="app-container">
        <ForcePasswordChangeModal />
        <Sidebar isMobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
        <div className="main-content">
          <Header onToggleMobile={() => setMobileOpen(!mobileOpen)} />
          <div className="page-body">
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
              <h2 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>403 - Permission Denied</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                Your current role does not have authorization to view this section.
              </p>
              <Link to="/portal" className="btn btn-primary" style={{ display: 'inline-flex', gap: '0.5rem' }}>
                ← Return to Module Portal
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <ForcePasswordChangeModal />
      <Sidebar isMobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div className="main-content">
        <Header onToggleMobile={() => setMobileOpen(!mobileOpen)} />
        {children}
      </div>
    </div>
  );
};

function AppRoutes() {
  const { user, hasPermission, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
        Loading session...
      </div>
    );
  }

  const canAccessBreakfast = () => {
    if (!user) return false;
    const perms = [
      '*',
      'breakfast.view',
      'breakfast.view_own',
      'breakfast.submit',
      'breakfast.manage',
      'breakfast.report',
      'breakfast.dashboard.view',
      'finance.breakfast_fund.view'
    ];
    return perms.some(p => hasPermission(p));
  };

  return (
    <Routes>
      {/* Root redirects to Central Portal if logged in, otherwise Login */}
      <Route path="/" element={<Navigate to={user ? "/portal" : "/login"} replace />} />

      {/* Login redirects to Central Portal if already authenticated */}
      <Route path="/login" element={user ? <Navigate to="/portal" replace /> : <LoginPage />} />

      {/* NEW Central Module Selection Portal (Protected) */}
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

      {/* Gateway route for Breakfast Module -> forwards to user's role-based dashboard */}
      <Route
        path="/breakfast"
        element={
          user ? (
            canAccessBreakfast() ? (
              <Navigate to={getBreakfastDestination(hasPermission)} replace />
            ) : (
              <Navigate to="/portal" replace />
            )
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* Common Breakfast Response - Accessible by ANY authenticated user with breakfast permission */}
      <Route
        path="/today"
        element={
          <ProtectedLayout>
            <EmployeeDailyPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/response"
        element={
          <ProtectedLayout>
            <EmployeeDailyPage />
          </ProtectedLayout>
        }
      />
      <Route
        path="/breakfast-response"
        element={
          <ProtectedLayout>
            <EmployeeDailyPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/dashboard"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <AdminDashboardPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/daily-entry"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <DailyEntryPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/additional-orders"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <AdditionalOrdersPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/breakfast-money"
        element={
          <ProtectedLayout requiredPermission="breakfast.money.view">
            <BreakfastMoneyPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/finance/fund-requests"
        element={
          <ProtectedLayout requiredPermission="finance.breakfast_fund.view">
            <FinanceManagerPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/today-breakfast"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <TodayBreakfastListPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/today-list"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <TodayBreakfastListPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/orders"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <BreakfastOrdersPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/employees"
        element={
          <ProtectedLayout requiredPermission="breakfast.employee.read">
            <EmployeeManagementPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/holidays"
        element={
          <ProtectedLayout requiredPermission="breakfast.view">
            <PublicHolidaysPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/reports"
        element={
          <ProtectedLayout requiredPermission={['breakfast.report', 'breakfast.money.report']}>
            <ReportsPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/admin/reports"
        element={
          <ProtectedLayout requiredPermission={['breakfast.report', 'breakfast.money.report']}>
            <ReportsPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/ceo-dashboard"
        element={
          <ProtectedLayout requiredPermission="breakfast.dashboard.view">
            <CEOViewPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/audit-logs"
        element={
          <ProtectedLayout requiredPermission="breakfast.audit.view">
            <AuditLogsPage />
          </ProtectedLayout>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedLayout requiredPermission="breakfast.settings.manage">
            <SettingsPage />
          </ProtectedLayout>
        }
      />

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
