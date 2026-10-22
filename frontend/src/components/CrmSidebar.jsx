import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Layers,
  Users,
  ChevronLeft,
  X,
  LayoutGrid,
  Menu,
  Building,
  Building2,
  Contact,
  ShieldCheck
} from 'lucide-react';

const CrmSidebar = ({
  isMobileOpen,
  onCloseMobile,
  isCollapsed: propIsCollapsed,
  onToggleCollapse
}) => {
  const { user, hasRole, isGlobalAdmin, hasPermission } = useAuth();
  const location = useLocation();

  const [isCollapsedInternal, setIsCollapsedInternal] = useState(false);
  const isCollapsed = propIsCollapsed !== undefined ? propIsCollapsed : isCollapsedInternal;
  const toggleCollapse = onToggleCollapse || (() => setIsCollapsedInternal(!isCollapsedInternal));

  const handleLinkClick = () => {
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  // Only CRM Admins and Global Admins can see and access the CRM User Hub
  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canAccessUserHub = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.user.manage');

  const primaryRole = user?.roles && user.roles.length > 0
    ? user.roles[0].replace(/_/g, ' ')
    : 'CRM USER';

  const isDashboardActive = location.pathname === '/crm' || location.pathname === '/crm/dashboard';
  const isLeadsActive = location.pathname.startsWith('/crm/leads');
  const isAccountsActive = location.pathname.startsWith('/crm/accounts');
  const isContactsActive = location.pathname.startsWith('/crm/contacts');
  const isUserHubActive = location.pathname === '/crm/user-hub' || location.pathname === '/crm/users';

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
            background: 'linear-gradient(135deg, #f59e0b, #d97706)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            boxShadow: '0 4px 10px rgba(245, 158, 11, 0.3)'
          }}>
            <Building size={20} color="white" />
          </div>
          {(!isCollapsed || isMobileOpen) && (
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', lineHeight: 1.1 }}>REVY</h2>
              <span style={{ fontSize: '0.65rem', color: '#fcd34d', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                CRM Portal
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
            color: '#fde68a',
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            textDecoration: 'none',
            fontSize: '0.85rem',
            fontWeight: 600,
            marginBottom: '0.75rem',
            transition: 'all 0.15s ease'
          }}
          title="Return to Central Services Portal"
        >
          <LayoutGrid size={18} color="#f59e0b" style={{ flexShrink: 0 }} />
          {(!isCollapsed || isMobileOpen) && (
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              ← All Services
            </span>
          )}
        </NavLink>

        {/* Primary CRM Navigation Label */}
        {(!isCollapsed || isMobileOpen) && (
          <div style={{
            fontSize: '0.68rem',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: '#64748b',
            padding: '0.4rem 0.5rem 0.2rem',
            fontWeight: 700
          }}>
            Sales Workspace
          </div>
        )}

        {/* 1. Dashboard */}
        <NavLink
          to="/crm/dashboard"
          onClick={handleLinkClick}
          className={`nav-item ${isDashboardActive ? 'active' : ''}`}
          title="CRM Dashboard"
        >
          <LayoutDashboard size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Dashboard</span>}
        </NavLink>

        {/* 2. Leads */}
        <NavLink
          to="/crm/leads"
          onClick={handleLinkClick}
          className={`nav-item ${isLeadsActive ? 'active' : ''}`}
          title="Leads Pipeline"
        >
          <Layers size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Leads</span>}
        </NavLink>

        {/* 3. Accounts */}
        <NavLink
          to="/crm/accounts"
          onClick={handleLinkClick}
          className={`nav-item ${isAccountsActive ? 'active' : ''}`}
          title="Accounts"
        >
          <Building2 size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Accounts</span>}
        </NavLink>

        {/* 4. Contacts */}
        <NavLink
          to="/crm/contacts"
          onClick={handleLinkClick}
          className={`nav-item ${isContactsActive ? 'active' : ''}`}
          title="Contacts"
        >
          <Contact size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Contacts</span>}
        </NavLink>

        {/* Separate Section: CRM Administration (strictly CRM Admin and Global Admins) */}
        {canAccessUserHub && (
          <>
            {(!isCollapsed || isMobileOpen) && (
              <div style={{
                fontSize: '0.68rem',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: '#64748b',
                padding: '0.9rem 0.5rem 0.2rem',
                fontWeight: 700
              }}>
                CRM Administration
              </div>
            )}

            <NavLink
              to="/crm/user-hub"
              onClick={handleLinkClick}
              className={`nav-item ${isUserHubActive ? 'active' : ''}`}
              title="CRM User Hub"
            >
              <Users size={18} />
              {(!isCollapsed || isMobileOpen) && <span>CRM User Hub</span>}
            </NavLink>
          </>
        )}
      </nav>

      {/* Role Badge Info in Sidebar */}
      {(!isCollapsed || isMobileOpen) && (
        <div style={{
          padding: '0.6rem 0.8rem',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: '8px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          marginBottom: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#94a3b8', fontSize: '0.72rem' }}>
            <ShieldCheck size={13} color="#f59e0b" />
            <span style={{ textTransform: 'uppercase', letterSpacing: '0.03em', fontWeight: 600 }}>Active Role</span>
          </div>
          <div style={{ color: '#f8fafc', fontWeight: 600, fontSize: '0.8rem', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {primaryRole}
          </div>
        </div>
      )}

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

export default CrmSidebar;
