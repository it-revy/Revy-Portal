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
  CheckCircle2,
  X,
  ShieldCheck,
  Building,
  Users,
  Clock
} from 'lucide-react';

/**
 * Authoritative 9 Services in exact order specified:
 * 1. MIS
 * 2. BMS — Breakfast Management System
 * 3. CRM
 * 4. LMS
 * 5. IMS
 * 6. Leave Management
 * 7. User Management
 * 8. DWR
 * 9. Reports
 */
export const PORTAL_SERVICES = [
  {
    id: 'mis',
    code: 'MIS',
    name: 'MIS',
    subtitle: 'Management Information System',
    title: 'Management Information System',
    description: 'Executive analytics, operational metrics, cross-department dashboards, and high-level enterprise KPIs.',
    icon: BarChart3,
    isClickable: false,
    accentColor: '#4f46e5',
    category: 'Analytics & Management'
  },
  {
    id: 'bms',
    code: 'BMS',
    name: 'BMS',
    subtitle: 'Breakfast Management System',
    title: 'Breakfast Management System',
    description: 'Daily meal attendance, catering orders, cutoff enforcement, attendance history, and authoritative money ledger.',
    icon: UtensilsCrossed,
    isClickable: true,
    accentColor: '#2563eb',
    category: 'Employee Services'
  },
  {
    id: 'crm',
    code: 'CRM',
    name: 'CRM',
    subtitle: 'Customer Relationship Management',
    title: 'Customer Relationship Management',
    description: 'Client accounts, lead pipeline, sales tracking, proposal generation, and corporate customer communications.',
    icon: Building,
    isClickable: false,
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
    isClickable: false,
    accentColor: '#0891b2',
    category: 'Laboratory Operations'
  },
  {
    id: 'ims',
    code: 'IMS',
    name: 'IMS',
    subtitle: 'Inventory Management System',
    title: 'Inventory Management System',
    description: 'Track plant materials, lab consumables, hardware inventory, real-time stock alerts, and procurement requisitions.',
    icon: Boxes,
    isClickable: false,
    accentColor: '#10b981',
    category: 'Supply & Inventory'
  },
  {
    id: 'leave',
    code: 'LEAVE',
    name: 'Leave Management',
    subtitle: 'Leave & Attendance Portal',
    title: 'Leave & Attendance Management',
    description: 'Employee leave requests, manager approvals, vacation balance tracking, and corporate attendance calendar.',
    icon: CalendarCheck,
    isClickable: false,
    accentColor: '#8b5cf6',
    category: 'Human Resources'
  },
  {
    id: 'users',
    code: 'USERS',
    name: 'User Management',
    subtitle: 'Identity & Access Control',
    title: 'User & System Identity Management',
    description: 'Create system users, assign hierarchical reporting managers, and control business module memberships and roles.',
    icon: Users,
    isClickable: true,
    accentColor: '#2563eb',
    category: 'Platform Administration'
  },
  {
    id: 'dwr',
    code: 'DWR',
    name: 'DWR',
    subtitle: 'Daily Work Report',
    title: 'Daily Work Report',
    description: 'Daily task logging, on-site project activities, progress reporting, and manager sign-off workflows.',
    icon: ClipboardList,
    isClickable: false,
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
    isClickable: false,
    accentColor: '#db2777',
    category: 'Compliance & Audit'
  }
];

export const getBreakfastDestination = (hasPermission, hasRole = () => false) => {
  if (hasRole('DIRECTOR') || hasRole('Director') || hasRole('CEO') || hasRole('Chief Executive Officer')) return '/bms/ceo-view';
  if (hasRole('BMS_DIRECTOR_ANALYTICS') || hasRole('Director Analytics') || hasRole('DIRECTOR_ANALYTICS') || hasRole('BMS Director Analytics')) return '/bms/director-analytics';
  if (hasRole('BMS_FINANCE_MANAGER') || hasRole('Finance Manager') || hasRole('FINANCE_MANAGER') || hasRole('BMS Finance Manager')) return '/bms/finance';
  if (hasPermission('breakfast.orders.view')) return '/bms/orders';
  if (hasPermission('breakfast.view')) return '/bms/dashboard';
  if (hasPermission('finance.breakfast_fund.view')) return '/bms/finance';
  return '/bms/response';
};

export default function CentralPortalPage() {
  const { user, logout, hasPermission, hasRole, hasModuleAccess } = useAuth();
  const navigate = useNavigate();
  const [inactiveModal, setInactiveModal] = useState(null);

  const canManageUsers = hasRole('IT_ADMIN') ||
                         hasRole('DIRECTOR') ||
                         hasRole('USER_MANAGEMENT_ADMIN') ||
                         hasModuleAccess('USERS') ||
                         hasPermission('*') ||
                         hasPermission('users.view') ||
                         hasPermission('users.create') ||
                         hasPermission('users.edit');

  const handleModuleClick = (mod) => {
    // 1. If service is disabled / coming soon: do not navigate
    if (!mod.isClickable) {
      return;
    }

    // 2. BMS (Breakfast Management System)
    if (mod.code === 'BMS') {
      if (hasModuleAccess('BMS') || hasRole('IT_ADMIN') || hasRole('DIRECTOR') || hasPermission('*')) {
        const targetRoute = getBreakfastDestination(hasPermission, hasRole);
        navigate(targetRoute);
      } else {
        setInactiveModal({
          name: mod.name,
          title: mod.title,
          isPermissionDenied: true,
          message: 'Your current account does not have membership in the Breakfast Management System (BMS). Please contact your IT Administrator to be enrolled.'
        });
      }
      return;
    }

    // 3. User Management
    if (mod.id === 'users' || mod.code === 'USERS') {
      if (canManageUsers) {
        navigate('/user-management');
      } else {
        setInactiveModal({
          name: mod.name,
          title: mod.title,
          isPermissionDenied: true,
          message: 'Access Restricted: You must have IT Administrator, Director, or User Management Admin privileges to access User Management.'
        });
      }
      return;
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
                Active: BMS & User Management
              </span>
              <span className="portal-stat-badge pending-stat">
                <span className="stat-dot amber"></span>
                Module-Specific Navigation Enforced
              </span>
            </div>
          </section>

          {/* Service Selection Grid - EXACT 9 SERVICES */}
          <section className="portal-modules-grid" aria-label="Available Services">
            {PORTAL_SERVICES.map((mod) => {
              const IconComponent = mod.icon;
              const isClickable = mod.isClickable;

              // Access check for clickable services
              let hasAccess = false;
              if (mod.code === 'BMS') {
                hasAccess = hasModuleAccess('BMS') || hasRole('IT_ADMIN') || hasPermission('*');
              } else if (mod.code === 'USERS') {
                hasAccess = canManageUsers;
              }

              return (
                <div
                  key={mod.id}
                  className={`portal-module-card ${isClickable ? (hasAccess ? 'card-enabled' : 'card-disabled') : 'card-disabled is-coming-soon'}`}
                  onClick={() => handleModuleClick(mod)}
                  role={isClickable ? 'button' : 'region'}
                  tabIndex={isClickable ? 0 : -1}
                  onKeyDown={(e) => {
                    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      handleModuleClick(mod);
                    }
                  }}
                  aria-disabled={!isClickable || !hasAccess}
                  style={!isClickable ? { opacity: 0.65, cursor: 'not-allowed' } : {}}
                >
                  <div className="portal-card-top">
                    <div
                      className="portal-module-icon-wrap"
                      style={{
                        background: isClickable && hasAccess ? `${mod.accentColor}18` : '#f1f5f9',
                        color: isClickable && hasAccess ? mod.accentColor : '#94a3b8',
                        borderColor: isClickable && hasAccess ? `${mod.accentColor}30` : '#e2e8f0'
                      }}
                    >
                      <IconComponent size={26} />
                    </div>

                    <div className="portal-card-badges">
                      {isClickable ? (
                        hasAccess ? (
                          <span className="portal-badge badge-active">
                            <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
                            {mod.code === 'USERS' ? 'System Admin' : 'Active Service'}
                          </span>
                        ) : (
                          <span className="portal-badge badge-restricted">
                            <Lock size={12} style={{ marginRight: '4px' }} />
                            Membership Required
                          </span>
                        )
                      ) : (
                        <span
                          className="portal-badge"
                          style={{
                            background: '#f1f5f9',
                            color: '#64748b',
                            border: '1px solid #cbd5e1'
                          }}
                        >
                          <Clock size={12} style={{ marginRight: '4px' }} />
                          Coming Soon
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
                    {isClickable ? (
                      hasAccess ? (
                        <div className="portal-action-cta cta-active">
                          <span>Open Service</span>
                          <ArrowRight size={16} className="cta-arrow" />
                        </div>
                      ) : (
                        <div className="portal-action-cta cta-disabled">
                          <span>Membership Required</span>
                          <Lock size={14} />
                        </div>
                      )
                    ) : (
                      <div
                        className="portal-action-cta cta-disabled"
                        style={{
                          background: '#f8fafc',
                          color: '#94a3b8',
                          border: '1px solid #e2e8f0',
                          cursor: 'not-allowed'
                        }}
                      >
                        <span>Coming Soon</span>
                        <Lock size={13} />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </section>
        </div>
      </main>

      {/* Access Restriction Modal */}
      {inactiveModal && (
        <div className="portal-modal-backdrop" onClick={() => setInactiveModal(null)}>
          <div className="portal-modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="portal-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '8px',
                  background: 'rgba(239, 68, 68, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ef4444'
                }}>
                  <Lock size={18} />
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>{inactiveModal.name}</h4>
                  <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{inactiveModal.title}</span>
                </div>
              </div>
              <button
                className="portal-modal-close"
                onClick={() => setInactiveModal(null)}
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>

            <div className="portal-modal-body">
              <p style={{ margin: 0, color: '#334155', lineHeight: 1.5, fontSize: '0.9rem' }}>
                {inactiveModal.message}
              </p>
            </div>

            <div className="portal-modal-footer">
              <button
                onClick={() => setInactiveModal(null)}
                className="btn btn-secondary"
                style={{ minWidth: '90px' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
