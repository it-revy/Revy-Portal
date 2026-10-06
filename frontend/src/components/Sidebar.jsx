import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Utensils,
  LayoutDashboard,
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
  ChevronRight,
  ChevronDown,
  X,
  LayoutGrid,
  Menu
} from 'lucide-react';

const Sidebar = ({ isMobileOpen, onCloseMobile, isCollapsed: propIsCollapsed, onToggleCollapse }) => {
  const { hasPermission, hasRole } = useAuth();
  const location = useLocation();

  const isBreakfastPath = [
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

        {/* Collapse button on Desktop Header (when expanded) */}
        {!isMobileOpen && !isCollapsed && (
          <button
            onClick={toggleCollapse}
            className="sidebar-header-toggle-btn"
            title="Collapse Sidebar (<)"
            aria-label="Collapse Sidebar"
          >
            <ChevronLeft size={16} />
          </button>
        )}

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

      {/* Prominent Expand Button when Collapsed at Top */}
      {!isMobileOpen && isCollapsed && (
        <button
          onClick={toggleCollapse}
          className="sidebar-expand-top-btn"
          title="Expand Sidebar (☰)"
          aria-label="Expand Sidebar"
        >
          <Menu size={20} />
        </button>
      )}

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

        {/* 1. Dashboard - FIRST Navigation Item for Admins */}
        {hasPermission('breakfast.view') && (
          <NavLink
            to="/admin/dashboard"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Dashboard"
          >
            <LayoutDashboard size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Dashboard</span>}
          </NavLink>
        )}

        {/* Orders link for CEO (when breakfast.view is not present) */}
        {!hasPermission('breakfast.view') && (hasRole('CEO') || hasRole('Chief Executive Officer') || hasPermission('breakfast.orders.view')) && (
          <NavLink
            to="/admin/orders"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="All Orders"
          >
            <FileSpreadsheet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>All Orders</span>}
          </NavLink>
        )}

        {/* Common Breakfast Response - For ALL Authenticated Users */}
        <NavLink
          to="/today"
          onClick={handleLinkClick}
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          title="Breakfast Response"
        >
          <Utensils size={18} />
          {(!isCollapsed || isMobileOpen) && <span>Breakfast Response</span>}
        </NavLink>

        {/* 2. Breakfast Dropdown Accordion */}
        {hasPermission('breakfast.view') && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <button
              onClick={() => setBreakfastExpanded(!breakfastExpanded)}
              className={`nav-item nav-dropdown-btn ${isBreakfastPath ? 'active-parent' : ''}`}
              style={{
                width: '100%',
                justifyContent: (isCollapsed && !isMobileOpen) ? 'center' : 'space-between',
                background: 'none',
                border: 'none',
                cursor: 'pointer'
              }}
              title="Breakfast Submenu"
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
                  to="/admin/daily-entry"
                  onClick={handleLinkClick}
                  className={({ isActive }) => `subnav-item ${isActive ? 'active' : ''}`}
                  title="Daily Entry"
                >
                  <Coffee size={16} />
                  <span>Daily Entry</span>
                </NavLink>

                <NavLink
                  to="/admin/today-breakfast"
                  onClick={handleLinkClick}
                  className={({ isActive }) => `subnav-item ${isActive ? 'active' : ''}`}
                  title="Today's Breakfast"
                >
                  <Utensils size={16} />
                  <span>Today's Breakfast</span>
                </NavLink>

                <NavLink
                  to="/admin/additional-orders"
                  onClick={handleLinkClick}
                  className={({ isActive }) => `subnav-item ${isActive ? 'active' : ''}`}
                  title="Additional Orders"
                >
                  <ShoppingBag size={16} />
                  <span>Additional Orders</span>
                </NavLink>

                <NavLink
                  to="/admin/orders"
                  onClick={handleLinkClick}
                  className={({ isActive }) => `subnav-item ${isActive ? 'active' : ''}`}
                  title="All Orders"
                >
                  <FileSpreadsheet size={16} />
                  <span>All Orders</span>
                </NavLink>

                {hasPermission('breakfast.money.view') && (
                  <NavLink
                    to="/admin/breakfast-money"
                    onClick={handleLinkClick}
                    className={({ isActive }) => `subnav-item ${isActive ? 'active' : ''}`}
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

        {/* All Orders - for CEO if breakfast dropdown is not displayed */}
        {(hasRole('CEO') || hasRole('Chief Executive Officer') || hasPermission('breakfast.orders.view')) && !hasPermission('breakfast.view') && (
          <NavLink
            to="/admin/orders"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="All Orders"
          >
            <FileSpreadsheet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>All Orders</span>}
          </NavLink>
        )}

        {/* 3. Employees */}
        {hasPermission('breakfast.employee.read') && (
          <NavLink
            to="/admin/employees"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Employees"
          >
            <Users size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Employees</span>}
          </NavLink>
        )}

        {/* 4. Public Holidays */}
        {hasPermission('breakfast.view') && (
          <NavLink
            to="/holidays"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Public Holidays"
          >
            <CalendarRange size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Public Holidays</span>}
          </NavLink>
        )}

        {/* 5. Reports */}
        {(hasPermission('breakfast.report') || hasPermission('breakfast.money.report') || hasRole('FINANCE_MANAGER') || hasRole('Finance Manager')) && (
          <NavLink
            to="/reports"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Reports"
          >
            <FileSpreadsheet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Reports</span>}
          </NavLink>
        )}

        {/* CEO Dashboard (ONLY for users with CEO role) */}
        {(hasRole('CEO') || hasRole('Chief Executive Officer')) && (
          <NavLink
            to="/ceo-dashboard"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="CEO Dashboard"
          >
            <TrendingUp size={18} />
            {(!isCollapsed || isMobileOpen) && <span>CEO Dashboard</span>}
          </NavLink>
        )}

        {/* Director Analytics (ONLY for users with DIRECTOR_ANALYTICS role) */}
        {(hasRole('DIRECTOR_ANALYTICS') || hasRole('Director Analytics')) && (
          <NavLink
            to="/director-analytics"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Director Analytics"
          >
            <PieChart size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Director Analytics</span>}
          </NavLink>
        )}

        {/* Finance Fund Requests */}
        {(hasPermission('finance.breakfast_fund.view') || hasRole('FINANCE_MANAGER') || hasRole('Finance Manager')) && (
          <NavLink
            to="/finance/fund-requests"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Finance Fund Requests"
          >
            <Wallet size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Finance Fund Requests</span>}
          </NavLink>
        )}

        {/* 6. Audit Logs - IT ADMIN only */}
        {hasPermission('breakfast.audit.view') && (
          <NavLink
            to="/audit-logs"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            title="Audit Logs"
          >
            <ShieldAlert size={18} />
            {(!isCollapsed || isMobileOpen) && <span>Audit Logs</span>}
          </NavLink>
        )}

        {/* 7. Settings - IT ADMIN only */}
        {hasPermission('breakfast.settings.manage') && (
          <NavLink
            to="/settings"
            onClick={handleLinkClick}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
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

export default Sidebar;
