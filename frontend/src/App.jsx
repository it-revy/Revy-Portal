import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import ChangePasswordPage from './pages/ChangePasswordPage';
import CentralPortalPage, { getBreakfastDestination } from './pages/CentralPortalPage';
import { getBMSRoutes } from './modules/bms';
import UserManagementPage from './pages/UserManagementPage';

import UserManagementLayout from './layouts/UserManagementLayout';
import CrmLayout from './layouts/CrmLayout';
import CrmDashboardPage from './pages/CrmDashboardPage';
import CrmLeadsPage from './pages/CrmLeadsPage';
import CrmLeadCreatePage from './pages/CrmLeadCreatePage';
import CrmLeadDetailPage from './pages/CrmLeadDetailPage';
import CrmAccountsPage from './pages/CrmAccountsPage';
import CrmOpportunitiesPage from './pages/CrmOpportunitiesPage';
import CrmContactsPage from './pages/CrmContactsPage';
import CrmUserHubPage from './pages/CrmUserHubPage';

function AppRoutes() {
  const { user, hasPermission, hasRole, hasModuleAccess, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
        Loading session...
      </div>
    );
  }

  // Mandatory Password Change Barrier:
  // If user has forcePasswordChange flag set, isolate access strictly to /change-password
  if (user && user.forcePasswordChange) {
    return (
      <Routes>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="*" element={<Navigate to="/change-password" replace />} />
      </Routes>
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

      {/* Forced Password Change Route (accessible directly if requested) */}
      <Route
        path="/change-password"
        element={user ? <ChangePasswordPage /> : <Navigate to="/login" replace />}
      />

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
      {/* 3. BREAKFAST MANAGEMENT SYSTEM (BMS) (Modular routes from modules/bms)     */}
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

      {/* Modular BMS routes and backward-compatible redirects */}
      {getBMSRoutes()}

      {/* ========================================================================= */}
      {/* 4. CUSTOMER RELATIONSHIP MANAGEMENT (CRM) MODULE                          */}
      {/* ========================================================================= */}
      <Route path="/crm" element={<Navigate to="/crm/dashboard" replace />} />
      <Route
        path="/crm/dashboard"
        element={
          <CrmLayout>
            <CrmDashboardPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/leads"
        element={
          <CrmLayout>
            <CrmLeadsPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/leads/new"
        element={
          <CrmLayout>
            <CrmLeadCreatePage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/leads/:id/edit"
        element={
          <CrmLayout>
            <CrmLeadCreatePage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/leads/:id"
        element={
          <CrmLayout>
            <CrmLeadDetailPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/accounts"
        element={
          <CrmLayout>
            <CrmAccountsPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/opportunities"
        element={
          <CrmLayout>
            <CrmOpportunitiesPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/contacts"
        element={
          <CrmLayout>
            <CrmContactsPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/user-hub"
        element={
          <CrmLayout requiredPermission="crm.user.manage" requiredRole="CRM_ADMIN">
            <CrmUserHubPage />
          </CrmLayout>
        }
      />
      <Route
        path="/crm/users"
        element={<Navigate to="/crm/user-hub" replace />}
      />

      {/* ========================================================================= */}
      {/* 5. FUTURE MODULE PLACEHOLDERS (Disabled / Coming Soon)                     */}
      {/* ========================================================================= */}
      <Route path="/mis/*" element={<Navigate to="/portal" replace />} />
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
