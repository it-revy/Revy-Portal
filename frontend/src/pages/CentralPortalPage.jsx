import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  UtensilsCrossed,
  BarChart3,
  FlaskConical,
  Boxes,
  CalendarCheck,
  ClipboardList,
  FileSpreadsheet,
  ArrowRight,
  Lock,
  LogOut,
  Sparkles,
  Info,
  CheckCircle2,
  X,
  ShieldCheck,
  Building,
  Users
} from 'lucide-react';

export const SYSTEM_MODULES = [
  {
    id: 'breakfast',
    code: 'BMS',
    name: 'BMS',
    subtitle: 'Breakfast Management System',
    title: 'Breakfast Management System',
    description: 'Daily meal attendance, catering orders, cutoff enforcement, attendance history, and authoritative money ledger.',
    icon: UtensilsCrossed,
    isOpenToAll: false,
    badge: 'Module Role Managed',
    accentColor: '#2563eb',
    category: 'Employee Services'
  },
  {
    id: 'crm',
    code: 'CRM',
    name: 'CRM',
    subtitle: 'Customer Relationship Management',
    title: 'Customer Relationship Management',
    description: 'Client accounts, lead pipeline, sales tracking, and customer communications.',
    icon: Building,
    isOpenToAll: false,
    badge: 'Module Role Managed',
    accentColor: '#f59e0b',
    category: 'Sales & Growth'
  },
  {
    id: 'lms',
    code: 'LMS',
    name: 'LMS',
    subtitle: 'Laboratory Management System',
    title: 'Laboratory Management System',
    description: 'Environmental sample tracking, biological/chemical test workflows, QA/QC audits, and digital lab certificates.',
    icon: FlaskConical,
    isOpenToAll: false,
    badge: 'Module Role Managed',
    accentColor: '#0891b2',
    category: 'Laboratory Operations'
  },
  {
    id: 'mis',
    code: 'MIS',
    name: 'MIS',
    subtitle: 'Management Information System',
    title: 'Management Information System',
    description: 'Executive analytics, operational metrics, cross-department dashboards, and high-level KPIs.',
    icon: BarChart3,
    isOpenToAll: true,
    badge: 'Open to All',
    accentColor: '#4f46e5',
    category: 'Analytics & Management'
  },
  {
    id: 'dwr',
    code: 'DWR',
    name: 'DWR',
    subtitle: 'Daily Work Report',
    title: 'Daily Work Report',
    description: 'Daily task logging, on-site project activities, progress reporting, and manager sign-off workflows.',
    icon: ClipboardList,
    isOpenToAll: true,
    badge: 'Open to All',
    accentColor: '#d97706',
    category: 'Operations & Field'
  },
  {
    id: 'reports',
    code: 'REPORTS',
    name: 'Reports',
    subtitle: 'Statutory & Audit Reports',
    title: 'Statutory & Audit Reports',
    description: 'Consolidated statutory reports, platform audit trail analysis, compliance reports, and multi-format data exports.',
    icon: FileSpreadsheet,
    isOpenToAll: true,
    badge: 'Open to All',
    accentColor: '#db2777',
    category: 'Compliance & Audit'
  }
];

export const getBreakfastDestination = (hasPermission, hasRole = () => false) => {
  if (hasRole('CEO') || hasRole('Chief Executive Officer')) return '/ceo-dashboard';
  if (hasRole('DIRECTOR_ANALYTICS') || hasRole('Director Analytics')) return '/director-analytics';
  if (hasRole('FINANCE_MANAGER') || hasRole('Finance Manager')) return '/finance/fund-requests';
  if (hasPermission('breakfast.orders.view')) return '/admin/orders';
  if (hasPermission('breakfast.view')) return '/admin/dashboard';
  if (hasPermission('finance.breakfast_fund.view')) return '/finance/fund-requests';
  return '/today';
};

export default function CentralPortalPage() {
  const { user, logout, hasPermission, hasRole, hasModuleAccess, getModuleRole } = useAuth();
  const navigate = useNavigate();
  const [inactiveModal, setInactiveModal] = useState(null);

  const canManageUsers = hasRole('IT_ADMIN') || hasPermission('*') || hasPermission('users.view') || hasPermission('users.create');

  // Build the list of modules, prepending User Management for Admins
  const displayModules = [...SYSTEM_MODULES];
  if (canManageUsers) {
    displayModules.unshift({
      id: 'users',
      code: 'USERS',
      name: 'User Management',
      subtitle: 'Identity & Access Control',
      title: 'User & System Identity Management',
      description: 'Create system users, assign hierarchical managers, and control business module memberships.',
      icon: Users,
      isOpenToAll: false,
      badge: 'System Admin',
      accentColor: '#2563eb',
      category: 'Platform Administration'
    });
  }

  const handleModuleClick = (mod) => {
    // 1. User Management (Admin only)
    if (mod.id === 'users') {
      navigate('/users');
      return;
    }

    // 2. BMS (Breakfast Management System)
    if (mod.code === 'BMS') {
      if (hasModuleAccess('BMS')) {
        const targetRoute = getBreakfastDestination(hasPermission, hasRole);
        navigate(targetRoute);
      } else {
        setInactiveModal({
          name: mod.name,
          title: mod.title,
          isPermissionDenied: true,
          message: 'Your current account does not have membership in the Breakfast Management System (BMS). Please contact your IT Administrator to be added.'
        });
      }
      return;
    }

    // 3. Universal modules (MIS, DWR, Reports) - Open to all authenticated users
    if (mod.isOpenToAll) {
      if (mod.code === 'REPORTS') {
        navigate('/admin/reports');
        return;
      }
      setInactiveModal({
        name: mod.name,
        title: mod.subtitle || mod.title,
        isPermissionDenied: false,
        message: `The ${mod.name} (${mod.subtitle || mod.title}) workspace is available to all employees. Dedicated workflow components are scheduled in the next platform release.`
      });
      return;
    }

    // 4. Restricted Business Modules (CRM, LMS)
    if (hasModuleAccess(mod.code)) {
      const assignedRole = getModuleRole(mod.code);
      setInactiveModal({
        name: mod.name,
        title: mod.subtitle || mod.title,
        isPermissionDenied: false,
        message: `Your account is active in ${mod.name} with role: ${assignedRole || 'Member'}. The full workflow dashboard for ${mod.name} is currently being connected.`
      });
    } else {
      setInactiveModal({
        name: mod.name,
        title: mod.subtitle || mod.title,
        isPermissionDenied: true,
        message: `Access Restricted: Your account has not been added to ${mod.name}. Please contact your system administrator for access.`
      });
    }
  };

  const primaryRole = user?.roles && user.roles.length > 0
    ? user.roles[0].replace(/_/g, ' ')
    : 'USER';

  return (
    <div className="portal-root">
      {/* Top Enterprise Header */}
      <header className="portal-topbar">
        <div className="portal-topbar-inner">
          <div className="portal-brand-block">
            <div className="portal-brand-logo" style={{ background: '#ffffff', border: '1px solid #e2e8f0', overflow: 'hidden', padding: '3px' }}>
              <img src="/favicon.png" alt="REVY Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="portal-brand-name">REVY</span>
                <span className="portal-env-pill">Enterprise Portal</span>
              </div>
              <span className="portal-brand-subtitle">Central Management System</span>
            </div>
          </div>

          <div className="portal-topbar-right">
            <div className="portal-user-chip">
              <div className="portal-user-avatar">
                {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="portal-user-info">
                <span className="portal-user-name">{user?.name || user?.username || 'Authorized User'}</span>
                <span className="portal-user-role">
                  <ShieldCheck size={11} style={{ marginRight: '3px' }} />
                  {primaryRole} {user?.employeeId ? `• ${user.employeeId}` : ''}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              className="portal-signout-btn"
              title="Sign Out of Portal"
              aria-label="Sign Out"
            >
              <LogOut size={16} />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="portal-content">
        <div className="portal-container">
          {/* Welcome Banner */}
          <section className="portal-hero">
            <div className="portal-hero-tag">
              <Sparkles size={14} color="#2563eb" />
              <span>Unified Management Workspace</span>
            </div>
            <h1 className="portal-hero-title">Select Services</h1>
            <p className="portal-hero-desc">
              Welcome back, <strong>{user?.name || user?.username}</strong>. Choose an authorized enterprise service below to launch your workspace.
            </p>
            <div className="portal-stats-row">
              <span className="portal-stat-badge active-stat">
                <span className="stat-dot green"></span>
                Universal Access Active (MIS, DWR, Reports)
              </span>
              <span className="portal-stat-badge pending-stat">
                <span className="stat-dot amber"></span>
                Module-Based Access Enforced
              </span>
            </div>
          </section>

          {/* Service Selection Grid */}
          <section className="portal-modules-grid" aria-label="Available Services">
            {displayModules.map((mod) => {
              const IconComponent = mod.icon;
              const isUsers = mod.id === 'users';
              const isUniversal = mod.isOpenToAll;
              const hasAccess = isUsers ? canManageUsers : (isUniversal || hasModuleAccess(mod.code));

              return (
                <div
                  key={mod.id}
                  className={`portal-module-card ${hasAccess ? 'card-enabled' : 'card-disabled'}`}
                  onClick={() => handleModuleClick(mod)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleModuleClick(mod);
                    }
                  }}
                  aria-disabled={!hasAccess}
                >
                  <div className="portal-card-top">
                    <div
                      className="portal-module-icon-wrap"
                      style={{
                        background: hasAccess ? `${mod.accentColor}18` : '#f1f5f9',
                        color: hasAccess ? mod.accentColor : '#94a3b8',
                        borderColor: hasAccess ? `${mod.accentColor}30` : '#e2e8f0'
                      }}
                    >
                      <IconComponent size={26} />
                    </div>

                    <div className="portal-card-badges">
                      {hasAccess ? (
                        <span className="portal-badge badge-active">
                          <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
                          {mod.badge}
                        </span>
                      ) : (
                        <span className="portal-badge badge-restricted">
                          <Lock size={12} style={{ marginRight: '4px' }} />
                          Membership Required
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="portal-card-content">
                    <span className="portal-card-category">{mod.category}</span>
                    <h3 className="portal-card-title">{mod.name}</h3>
                    <h4 className="portal-card-subtitle">{mod.subtitle || mod.title}</h4>
                    <p className="portal-card-desc">{mod.description}</p>
                  </div>

                  <div className="portal-card-bottom">
                    {hasAccess ? (
                      <div className="portal-action-cta cta-active">
                        <span>Open Service</span>
                        <ArrowRight size={16} className="cta-arrow" />
                      </div>
                    ) : (
                      <div className="portal-action-cta cta-disabled">
                        <span>Not Enrolled</span>
                        <Lock size={14} />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="portal-footer">
        <div className="portal-footer-inner">
          <p>© {new Date().getFullYear()} REVY Environmental Solutions. All rights reserved.</p>
          <p className="portal-footer-tech">
            REVY Centralized Enterprise Management System • FastAPI + PostgreSQL
          </p>
        </div>
      </footer>

      {/* Inactive / Restricted Module Modal */}
      {inactiveModal && (
        <div className="modal-backdrop" onClick={() => setInactiveModal(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '480px', padding: '2rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '10px',
                    background: inactiveModal.isPermissionDenied ? '#fef2f2' : '#eff6ff',
                    color: inactiveModal.isPermissionDenied ? '#dc2626' : '#2563eb',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  {inactiveModal.isPermissionDenied ? <Lock size={22} /> : <Info size={22} />}
                </div>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {inactiveModal.name} Service
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {inactiveModal.title}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setInactiveModal(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '4px'
                }}
                aria-label="Close dialog"
              >
                <X size={20} />
              </button>
            </div>

            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
              {inactiveModal.message}
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                className="btn btn-primary"
                onClick={() => setInactiveModal(null)}
                style={{ minWidth: '100px' }}
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
