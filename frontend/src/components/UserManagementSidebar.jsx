import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  ShieldCheck,
  Layers,
  ChevronLeft,
  X,
  LayoutGrid,
  Menu,
  Shield
} from 'lucide-react';

const UserManagementSidebar = ({
  isMobileOpen,
  onCloseMobile,
  isCollapsed: propIsCollapsed,
  onToggleCollapse,
  onOpenCreateUser,
  onFilterModuleAccess
}) => {
  const { hasRole, hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [isCollapsedInternal, setIsCollapsedInternal] = useState(false);
  const isCollapsed = propIsCollapsed !== undefined ? propIsCollapsed : isCollapsedInternal;
  const toggleCollapse = onToggleCollapse || (() => setIsCollapsedInternal(!isCollapsedInternal));

  const handleLinkClick = () => {
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  const handleCreateUserClick = (e) => {
    e.preventDefault();
    handleLinkClick();
    if (onOpenCreateUser) {
      onOpenCreateUser();
    } else {
      // Dispatch custom window event in case page is already mounted
      window.dispatchEvent(new CustomEvent('revy-open-create-user'));
      if (location.pathname !== '/user-management' && location.pathname !== '/users') {
        navigate('/user-management');
      }
    }
  };

  const handleModuleAccessClick = (e) => {
    handleLinkClick();
    if (onFilterModuleAccess) {
      onFilterModuleAccess();
    } else {
      window.dispatchEvent(new CustomEvent('revy-filter-module-access'));
      if (location.pathname !== '/user-management' && location.pathname !== '/users') {
        navigate('/user-management');
      }
    }
  };

  const isUsersActive = location.pathname === '/user-management' ||
                        location.pathname === '/users' ||
                        location.pathname.startsWith('/user-management/');

  const navContent = (
    <>
      {/* Brand Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: isCollapsed && !isMobileOpen ? 'center' : 'space-between',
        marginBottom: '1rem',
        padding: '0 0.25rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'linear-gradient(135deg, #2563eb, #4f46e5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            boxShadow: '0 4px 10px rgba(37, 99, 235, 0.3)'
          }}>
            <ShieldCheck size={20} color="white" />
          </div>
          {(!isCollapsed || isMobileOpen) && (
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', lineHeight: 1.1 }}>REVY</h2>
              <span style={{ fontSize: '0.65rem', color: '#93c5fd', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                User Management
              </span>
            </div>
          )}
        </div>

        {/* Close button on Mobile */}
        {isMobileOpen && (
          <button
            onClick={onCloseMobile}
            className="sidebar-header-toggle-btn"
            title="Close menu"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Nav List */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', flex: 1, overflowY: 'auto' }}>
        {/* Return to Central Services Portal */}
        <NavLink
          to="/portal"
          onClick={handleLinkClick}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.65rem 0.85rem',
            borderRadius: '8px',
            color: '#93c5fd',
            background: 'rgba(37, 99, 235, 0.15)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            textDecoration: 'none',
            fontSize: '0.85rem',
            fontWeight: 600,
            marginBottom: '0.75rem',
            transition: 'all 0.15s ease'
          }}
          title="Return to Central Services Portal"
        >
          <LayoutGrid size={18} color="#60a5fa" style={{ flexShrink: 0 }} />
          {(!isCollapsed || isMobileOpen) && (
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              ← All Services
            </span>
          )}
        </NavLink>

        {/* Section Label */}
        {(!isCollapsed || isMobileOpen) && (
          <div style={{
            fontSize: '0.68rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#64748b',
            padding: '0.4rem 0.5rem 0.2rem',
            fontWeight: 700
          }}>
            Identity & Access
          </div>
        )}

        {/* 1. Users List */}
        <NavLink
          to="/user-management"
          onClick={handleLinkClick}
          className={`nav-item ${isUsersActive ? 'active' : ''}`}
          title="User Directory"
        >
          <Users size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Users</span>}
        </NavLink>

        {/* 2. Create User Action */}
        <button
          type="button"
          onClick={handleCreateUserClick}
          className="nav-item"
          title="Create System User"
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            textAlign: 'left',
            cursor: 'pointer'
          }}
        >
          <UserPlus size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Create User</span>}
        </button>

        {/* 3. Module Access Management */}
        <button
          type="button"
          onClick={handleModuleAccessClick}
          className="nav-item"
          title="Module Access Control"
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            textAlign: 'left',
            cursor: 'pointer'
          }}
        >
          <Layers size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Module Access</span>}
        </button>
      </nav>

      {/* Sidebar Footer with Collapse / Expand Toggle Button */}
      {!isMobileOpen && (
        <div className="sidebar-footer">
          <button
            onClick={toggleCollapse}
            className={`sidebar-footer-toggle-btn ${isCollapsed ? 'collapsed' : 'expanded'}`}
            title={isCollapsed ? "Expand Sidebar (☰)" : "Collapse Sidebar (<)"}
            aria-label={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {isCollapsed ? (
              <Menu size={20} />
            ) : (
              <>
                <ChevronLeft size={18} />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      )}
    </>
  );

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className={`sidebar sidebar-desktop ${isCollapsed ? 'collapsed' : ''}`}>
        {navContent}
      </aside>

      {/* Mobile Drawer */}
      {isMobileOpen && (
        <>
          <div className="mobile-drawer-overlay" onClick={onCloseMobile} />
          <aside className="mobile-drawer-panel">
            {navContent}
          </aside>
        </>
      )}
    </>
  );
};

export default UserManagementSidebar;
