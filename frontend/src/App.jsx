import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

import LoginPage from './pages/LoginPage';
import CentralPortalPage, { getBreakfastDestination } from './pages/CentralPortalPage';
import { getBMSRoutes } from './modules/bms';
import UserManagementPage from './pages/UserManagementPage';

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
