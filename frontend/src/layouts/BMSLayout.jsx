import React, { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import BMSSidebar from '../components/BMSSidebar';
import Header from '../components/Header';
import ForcePasswordChangeModal from '../components/ForcePasswordChangeModal';

export default function BMSLayout({ children, requiredPermission, requiredRole }) {
  const { user, loading, hasPermission, hasRole, hasModuleAccess } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('revy_bms_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed(prev => {
      const next = !prev;
      try {
        localStorage.setItem('revy_bms_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const checkAccess = () => {
    // 1. Enforce BMS membership (unless superadmin or Director)
    if (!hasModuleAccess('BMS') && !hasRole('IT_ADMIN') && !hasRole('DIRECTOR') && !hasPermission('*')) {
      return false;
    }

    if (hasRole('IT_ADMIN') || hasRole('DIRECTOR') || hasPermission('*')) return true;

    // 2. Role-specific check if provided
    if (requiredRole) {
      if (Array.isArray(requiredRole)) {
        return requiredRole.some(r => hasRole(r));
      }
      return hasRole(requiredRole);
    }

    // 3. Finance & Director role conveniences
    if (hasRole('BMS_FINANCE_MANAGER') || hasRole('Finance Manager') || hasRole('FINANCE_MANAGER')) {
      if (typeof requiredPermission === 'string' && (requiredPermission.startsWith('finance.') || requiredPermission.startsWith('breakfast.money.') || requiredPermission === 'breakfast.report')) return true;
      if (Array.isArray(requiredPermission) && requiredPermission.some(p => p.startsWith('finance.') || p.startsWith('breakfast.money.') || p === 'breakfast.report')) return true;
    }

    if (hasRole('DIRECTOR') || hasRole('Director') || hasRole('CEO') || hasRole('Chief Executive Officer') || hasRole('BMS_DIRECTOR_ANALYTICS') || hasRole('Director Analytics')) {
      if (typeof requiredPermission === 'string' && (requiredPermission === 'breakfast.orders.view' || requiredPermission === 'breakfast.view')) return true;
      if (Array.isArray(requiredPermission) && requiredPermission.some(p => p === 'breakfast.orders.view' || p === 'breakfast.view')) return true;
    }

    // 4. Default permission check
    if (!requiredPermission) {
      return true;
    }

    if (Array.isArray(requiredPermission)) {
      return requiredPermission.some(p => hasPermission(p));
    }
    return hasPermission(requiredPermission);
  };

  if (!checkAccess()) {
    return (
      <div className="app-container">
        <ForcePasswordChangeModal />
        <BMSSidebar
          isMobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />
        <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
          <Header
            onToggleMobile={() => setMobileOpen(!mobileOpen)}
            sidebarCollapsed={sidebarCollapsed}
            onToggleCollapse={toggleSidebarCollapse}
          />
          <div className="page-body">
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
              <h2 style={{ color: 'var(--danger)', marginBottom: '1rem' }}>403 - Permission Denied</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                Your account does not have authorization to view this section of Breakfast Management.
              </p>
              <Link to="/portal" className="btn btn-primary" style={{ display: 'inline-flex', gap: '0.5rem' }}>
                ← Return to Services Portal
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
      <BMSSidebar
        isMobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebarCollapse}
      />
      <div className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Header
          onToggleMobile={() => setMobileOpen(!mobileOpen)}
          sidebarCollapsed={sidebarCollapsed}
          onToggleCollapse={toggleSidebarCollapse}
        />
        {children}
      </div>
    </div>
  );
}
