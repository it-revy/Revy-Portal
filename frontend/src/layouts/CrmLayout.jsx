import React, { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import CrmSidebar from '../components/CrmSidebar';
import Header from '../components/Header';
import ForcePasswordChangeModal from '../components/ForcePasswordChangeModal';

export default function CrmLayout({ children, requiredPermission = null, requiredRole = null }) {
  const { user, loading, hasPermission, hasRole, hasModuleAccess, isGlobalAdmin } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('revy_crm_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed(prev => {
      const next = !prev;
      try {
        localStorage.setItem('revy_crm_sidebar_collapsed', String(next));
      } catch {}
      return next;
    });
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
        Loading CRM workspace...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);

  const canAccessCrm = globalAdminActive ||
                       hasModuleAccess('CRM') ||
                       hasRole('CRM_ADMIN') ||
                       hasRole('CRM_SALES_MANAGER') ||
                       hasRole('CRM_SALES_REP') ||
                       hasRole('CRM_SALES_EXECUTIVE') ||
                       hasRole('CRM_SALES_COORDINATOR') ||
                       hasRole('CRM_PRE_SALES') ||
                       hasRole('CRM_FINANCE_MANAGER') ||
                       hasPermission('crm.lead.view') ||
                       hasPermission('crm.dashboard.view') ||
                       hasPermission('crm.user.manage') ||
                       hasPermission('*');

  // If page requires specific permission or role (e.g. User Hub requiring crm.user.manage)
  const isPageAuthorized = !requiredPermission || globalAdminActive || hasPermission(requiredPermission) || (requiredRole && hasRole(requiredRole));

  if (!canAccessCrm || !isPageAuthorized) {
    return (
      <div className="app-container">
        <ForcePasswordChangeModal />
        <CrmSidebar
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
            <div className="glass-panel" style={{ padding: '3.5rem 2rem', textAlign: 'center', maxWidth: '600px', margin: '3rem auto' }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: 'var(--danger-bg)',
                color: 'var(--danger)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.5rem',
                fontSize: '1.5rem',
                fontWeight: 700
              }}>
                !
              </div>
              <h2 style={{ color: 'var(--danger)', marginBottom: '0.75rem' }}>403 — Access Denied</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', lineHeight: 1.6 }}>
                {!canAccessCrm
                  ? 'Your account does not have active membership in the Customer Relationship Management (CRM) module. Please contact your CRM Administrator to request access.'
                  : 'You do not have the necessary permissions to access this administrative section.'}
              </p>
              <Link to="/portal" className="btn btn-primary" style={{ display: 'inline-flex', gap: '0.5rem', textDecoration: 'none' }}>
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
      <CrmSidebar
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
