import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Utensils,
  Users,
  FileSpreadsheet,
  PieChart,
  TrendingUp,
  ShieldAlert,
  Settings,
  Coffee,
  ShoppingBag,
  Wallet,
  CalendarRange,
  ChevronLeft,
  ChevronDown,
  X,
  LayoutGrid,
  Menu
} from 'lucide-react';

const BMSSidebar = ({ isMobileOpen, onCloseMobile, isCollapsed: propIsCollapsed, onToggleCollapse }) => {
  const { hasPermission, hasRole } = useAuth();
  const location = useLocation();

  const isBreakfastPath = [
    '/bms/daily-entry',
    '/bms/today-breakfast',
    '/bms/additional-orders',
    '/bms/orders',
    '/bms/breakfast-money',
    '/bms/money',
    '/admin/daily-entry',
    '/admin/today-breakfast',
    '/admin/today-list',
    '/admin/additional-orders',
    '/admin/orders',
    '/admin/breakfast-money'
  ].some(path => location.pathname.startsWith(path));

  const [isCollapsedInternal, setIsCollapsedInternal] = useState(false);
  const isCollapsed = propIsCollapsed !== undefined ? propIsCollapsed : isCollapsedInternal;
  const toggleCollapse = onToggleCollapse || (() => setIsCollapsedInternal(!isCollapsedInternal));
  const [breakfastExpanded, setBreakfastExpanded] = useState(isBreakfastPath || true);

  const handleLinkClick = () => {
    if (onCloseMobile) {
      onCloseMobile();
    }
  };

  const isRouteActive = (canonicalPath, legacyPaths = []) => {
    if (location.pathname === canonicalPath) return true;
    return legacyPaths.some(lp => location.pathname === lp || location.pathname.startsWith(`${lp}/`));
  };

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
            background: '#2563eb',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <Coffee size={20} color="white" />
          </div>
          {(!isCollapsed || isMobileOpen) && (
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'white', lineHeight: 1.1 }}>REVY</h2>
              <span style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Breakfast Platform
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
            marginBottom: '0.65rem',
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

        {/* 1. Today's Entry - Visible for employees who can submit or standard breakfast view */}
        {(hasPermission('breakfast.submit') || hasPermission('breakfast.view')) && (
          <NavLink
            to="/bms/response"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/response', ['/today', '/response', '/breakfast-response', '/bms/today']) ? 'active' : ''}`}
            title="Today's Entry"
          >
            <Utensils size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Today's Entry</span>}
          </NavLink>
        )}

        {/* 2. Breakfast Dropdown / Management Group */}
        {hasPermission('breakfast.view') && (
          <div className="nav-group">
            <button
              type="button"
              onClick={() => {
                if (isCollapsed && !isMobileOpen) {
                  toggleCollapse();
                  setBreakfastExpanded(true);
                } else {
                  setBreakfastExpanded(!breakfastExpanded);
                }
              }}
              className={`nav-dropdown-btn ${isBreakfastPath ? 'active' : ''}`}
              title="Breakfast Management"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: isCollapsed && !isMobileOpen ? 'center' : 'space-between',
                padding: '0.65rem 0.85rem',
                borderRadius: '8px',
                background: isBreakfastPath ? 'rgba(37, 99, 235, 0.12)' : 'transparent',
                border: 'none',
                color: isBreakfastPath ? '#60a5fa' : '#cbd5e1',
                cursor: 'pointer',
                fontWeight: 500,
                fontSize: '0.875rem'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <Coffee size={18} />
                {(!isCollapsed || isMobileOpen) && <span>Breakfast</span>}
              </div>
              {(!isCollapsed || isMobileOpen) && (
                <ChevronDown
                  size={16}
                  style={{
                    transform: breakfastExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease'
                  }}
                />
              )}
            </button>

            {/* Submenu Items */}
            {breakfastExpanded && (!isCollapsed || isMobileOpen) && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.2rem',
                paddingLeft: '1.25rem',
                marginTop: '0.2rem',
                marginBottom: '0.2rem',
                borderLeft: '2px solid rgba(255,255,255,0.1)'
              }}>
                <NavLink
                  to="/bms/daily-entry"
                  onClick={handleLinkClick}
                  className={() => `subnav-item ${isRouteActive('/bms/daily-entry', ['/admin/daily-entry']) ? 'active' : ''}`}
                  title="Daily Entry"
                >
                  <Coffee size={16} />
                  <span>Daily Entry</span>
                </NavLink>

                <NavLink
                  to="/bms/additional-orders"
                  onClick={handleLinkClick}
                  className={() => `subnav-item ${isRouteActive('/bms/additional-orders', ['/admin/additional-orders']) ? 'active' : ''}`}
                  title="Additional Orders"
                >
                  <ShoppingBag size={16} />
                  <span>Additional Orders</span>
                </NavLink>

                <NavLink
                  to="/bms/orders"
                  onClick={handleLinkClick}
                  className={() => `subnav-item ${isRouteActive('/bms/orders', ['/admin/orders']) ? 'active' : ''}`}
                  title="All Orders"
                >
                  <FileSpreadsheet size={16} />
                  <span>All Orders</span>
                </NavLink>

                {hasPermission('breakfast.money.view') && (
                  <NavLink
                    to="/bms/money"
                    onClick={handleLinkClick}
                    className={() => `subnav-item ${isRouteActive('/bms/money', ['/bms/breakfast-money', '/admin/breakfast-money']) ? 'active' : ''}`}
                    title="Breakfast Money"
                  >
                    <Wallet size={16} />
                    <span>Breakfast Money</span>
                  </NavLink>
                )}
              </div>
            )}
          </div>
        )}

        {/* All Orders - for Director if breakfast dropdown is not displayed */}
        {(hasRole('DIRECTOR') || hasRole('Director') || hasRole('CEO') || hasRole('Chief Executive Officer') || hasPermission('breakfast.orders.view')) && !hasPermission('breakfast.view') && (
          <NavLink
            to="/bms/orders"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/orders', ['/admin/orders']) ? 'active' : ''}`}
            title="All Orders"
          >
            <FileSpreadsheet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>All Orders</span>}
          </NavLink>
        )}

        {/* 3. Employees */}
        {hasPermission('breakfast.employee.read') && (
          <NavLink
            to="/bms/employees"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/employees', ['/admin/employees', '/employees']) ? 'active' : ''}`}
            title="Employees"
          >
            <Users size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Employees</span>}
          </NavLink>
        )}

        {/* 4. Public Holidays */}
        {hasPermission('breakfast.view') && (
          <NavLink
            to="/bms/holidays"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/holidays', ['/admin/holidays', '/holidays']) ? 'active' : ''}`}
            title="Public Holidays"
          >
            <CalendarRange size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Public Holidays</span>}
          </NavLink>
        )}

        {/* 5. Reports */}
        {(hasPermission('breakfast.report') || hasPermission('breakfast.money.report') || hasRole('BMS_FINANCE_MANAGER') || hasRole('Finance Manager') || hasRole('FINANCE_MANAGER')) && (
          <NavLink
            to="/bms/reports"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/reports', ['/reports']) ? 'active' : ''}`}
            title="Reports"
          >
            <FileSpreadsheet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Reports</span>}
          </NavLink>
        )}

        {/* Director Dashboard (for users with Director / CEO role) */}
        {(hasRole('DIRECTOR') || hasRole('Director') || hasRole('CEO') || hasRole('Chief Executive Officer')) && (
          <NavLink
            to="/bms/ceo-view"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/ceo-view', ['/ceo-dashboard']) ? 'active' : ''}`}
            title="Directors Dashboard"
          >
            <TrendingUp size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Directors Dashboard</span>}
          </NavLink>
        )}

        {/* Finance Fund Requests */}
        {(hasPermission('finance.breakfast_fund.view') || hasRole('BMS_FINANCE_MANAGER') || hasRole('BMS Finance Manager') || hasRole('FINANCE_MANAGER') || hasRole('Finance Manager')) && (
          <NavLink
            to="/bms/finance"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/finance', ['/finance/fund-requests']) ? 'active' : ''}`}
            title="Finance Fund Requests"
          >
            <Wallet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Finance Fund Requests</span>}
          </NavLink>
        )}

        {/* 6. Audit Logs - IT ADMIN only */}
        {hasPermission('breakfast.audit.view') && (
          <NavLink
            to="/bms/audit-logs"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/audit-logs', ['/audit-logs']) ? 'active' : ''}`}
            title="Audit Logs"
          >
            <ShieldAlert size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Audit Logs</span>}
          </NavLink>
        )}

        {/* 7. Settings - IT ADMIN only */}
        {hasPermission('breakfast.settings.manage') && (
          <NavLink
            to="/bms/settings"
            onClick={handleLinkClick}
            className={() => `nav-item ${isRouteActive('/bms/settings', ['/settings']) ? 'active' : ''}`}
            title="Settings"
          >
            <Settings size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Settings</span>}
          </NavLink>
        )}
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

export default BMSSidebar;
