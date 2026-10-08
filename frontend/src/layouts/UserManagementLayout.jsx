import React, { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import UserManagementSidebar from '../components/UserManagementSidebar';
import Header from '../components/Header';
import ForcePasswordChangeModal from '../components/ForcePasswordChangeModal';

export default function UserManagementLayout({ children }) {
  const { user, loading, hasPermission, hasRole } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('revy_user_sidebar_collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebarCollapse = () => {
    setSidebarCollapsed(prev => {
      const next = !prev;
      try {
        localStorage.setItem('revy_user_sidebar_collapsed', String(next));
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

  const canManageUsers = hasRole('IT_ADMIN') ||
                         hasRole('DIRECTOR') ||
                         hasRole('USER_MANAGEMENT_ADMIN') ||
                         hasPermission('*') ||
                         hasPermission('users.view') ||
                         hasPermission('users.create') ||
                         hasPermission('users.edit');

  if (!canManageUsers) {
    return (
      <div className="app-container">
        <ForcePasswordChangeModal />
        <UserManagementSidebar
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
                You do not have administrative privileges to access User Management.
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
      <UserManagementSidebar
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
