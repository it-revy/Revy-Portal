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
  Building2,
  ShieldCheck
} from 'lucide-react';

export const SYSTEM_MODULES = [
  {
    id: 'mis',
    name: 'MIS',
    title: 'Management Information System',
    description: 'Executive analytics, operational metrics, cross-department dashboards, and high-level KPIs.',
    icon: BarChart3,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#4f46e5',
    category: 'Analytics & Management'
  },
  {
    id: 'breakfast',
    name: 'Breakfast',
    title: 'Breakfast Management System',
    description: 'Daily meal attendance, catering orders, cutoff enforcement, attendance history, and authoritative money ledger.',
    icon: UtensilsCrossed,
    enabled: true,
    badge: 'Active & Online',
    accentColor: '#2563eb',
    category: 'Employee Services'
  },
  {
    id: 'lims',
    name: 'LIMS',
    title: 'Laboratory Information Management',
    description: 'Environmental sample tracking, biological/chemical test workflows, QA/QC audits, and digital lab certificates.',
    icon: FlaskConical,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#0891b2',
    category: 'Laboratory Operations'
  },
  {
    id: 'inventory',
    name: 'Inventory',
    title: 'Inventory & Consumables',
    description: 'Lab chemical reagents, hardware consumables, safety equipment, batch expiries, and automated reorder points.',
    icon: Boxes,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#7c3aed',
    category: 'Supply Chain & Lab'
  },
  {
    id: 'leave',
    name: 'Leave Management',
    title: 'Leave & Attendance System',
    description: 'Employee leave balance tracking, sick/casual leave applications, approval hierarchies, and team holiday schedules.',
    icon: CalendarCheck,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#059669',
    category: 'Human Resources'
  },
  {
    id: 'dwr',
    name: 'DWR',
    title: 'Daily Work Reports',
    description: 'Daily task logging, on-site project activities, progress reporting, and manager sign-off workflows.',
    icon: ClipboardList,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#d97706',
    category: 'Operations & Field'
  },
  {
    id: 'reports',
    name: 'Reports',
    title: 'Enterprise Reports & Audit',
    description: 'Consolidated statutory reports, platform audit trail analysis, compliance reports, and multi-format data exports.',
    icon: FileSpreadsheet,
    enabled: false,
    badge: 'Coming Soon',
    accentColor: '#db2777',
    category: 'Compliance & Audit'
  }
];

export const getBreakfastDestination = (hasPermission) => {
  if (hasPermission('breakfast.view')) return '/admin/dashboard';
  if (hasPermission('breakfast.dashboard.view')) return '/ceo-dashboard';
  if (hasPermission('finance.breakfast_fund.view')) return '/finance/fund-requests';
  return '/today';
};

export default function CentralPortalPage() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [inactiveModal, setInactiveModal] = useState(null);

  // Check if user has permission to access Breakfast module
  const hasBreakfastAccess = () => {
    if (!user) return false;
    const breakfastPerms = [
      '*',
      'breakfast.view',
      'breakfast.view_own',
      'breakfast.submit',
      'breakfast.manage',
      'breakfast.report',
      'breakfast.dashboard.view',
      'finance.breakfast_fund.view'
    ];
    return breakfastPerms.some((p) => hasPermission(p));
  };

  const canAccessBreakfast = hasBreakfastAccess();

  const handleModuleClick = (mod) => {
    if (mod.id === 'breakfast') {
      if (canAccessBreakfast) {
        const targetRoute = getBreakfastDestination(hasPermission);
        navigate(targetRoute);
      } else {
        setInactiveModal({
          name: mod.name,
          title: mod.title,
          isPermissionDenied: true,
          message: 'Your current account or role does not have authorization to access the Breakfast Management module. Please contact your IT Administrator.'
        });
      }
      return;
    }

    // Inactive placeholder modules
    setInactiveModal({
      name: mod.name,
      title: mod.title,
      isPermissionDenied: false,
      message: `The ${mod.title} (${mod.name}) module is currently under active development as part of the REVY Centralized Enterprise Platform roadmap.`
    });
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
            <div className="portal-brand-logo">
              <Building2 size={22} color="#ffffff" />
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
                <span className="portal-user-name">{user?.name || 'Authorized User'}</span>
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
            <h1 className="portal-hero-title">Select a System Module</h1>
            <p className="portal-hero-desc">
              Welcome back, <strong>{user?.name}</strong>. Choose an authorized enterprise module below to launch your workspace.
            </p>
            <div className="portal-stats-row">
              <span className="portal-stat-badge active-stat">
                <span className="stat-dot green"></span>
                1 Active Operational Module
              </span>
              <span className="portal-stat-badge pending-stat">
                <span className="stat-dot amber"></span>
                6 Modules Scheduled in Enterprise Roadmap
              </span>
            </div>
          </section>

          {/* Module Selection Grid */}
          <section className="portal-modules-grid" aria-label="Available System Modules">
            {SYSTEM_MODULES.map((mod) => {
              const IconComponent = mod.icon;
              const isBreakfast = mod.id === 'breakfast';
              const isEnabled = isBreakfast && canAccessBreakfast;
              const isRestricted = isBreakfast && !canAccessBreakfast;

              return (
                <div
                  key={mod.id}
                  className={`portal-module-card ${isEnabled ? 'card-enabled' : 'card-disabled'}`}
                  onClick={() => handleModuleClick(mod)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      handleModuleClick(mod);
                    }
                  }}
                  aria-disabled={!isEnabled}
                >
                  <div className="portal-card-top">
                    <div
                      className="portal-module-icon-wrap"
                      style={{
                        background: isEnabled ? `${mod.accentColor}18` : '#f1f5f9',
                        color: isEnabled ? mod.accentColor : '#94a3b8',
                        borderColor: isEnabled ? `${mod.accentColor}30` : '#e2e8f0'
                      }}
                    >
                      <IconComponent size={26} />
                    </div>

                    <div className="portal-card-badges">
                      {isEnabled && (
                        <span className="portal-badge badge-active">
                          <CheckCircle2 size={12} style={{ marginRight: '4px' }} />
                          {mod.badge}
                        </span>
                      )}
                      {isRestricted && (
                        <span className="portal-badge badge-restricted">
                          <Lock size={12} style={{ marginRight: '4px' }} />
                          Access Restricted
                        </span>
                      )}
                      {!isBreakfast && (
                        <span className="portal-badge badge-coming-soon">
                          <Lock size={12} style={{ marginRight: '4px' }} />
                          {mod.badge}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="portal-card-content">
                    <span className="portal-card-category">{mod.category}</span>
                    <h3 className="portal-card-title">{mod.name}</h3>
                    <h4 className="portal-card-subtitle">{mod.title}</h4>
                    <p className="portal-card-desc">{mod.description}</p>
                  </div>

                  <div className="portal-card-bottom">
                    {isEnabled ? (
                      <div className="portal-action-cta cta-active">
                        <span>Launch Module</span>
                        <ArrowRight size={16} className="cta-arrow" />
                      </div>
                    ) : isRestricted ? (
                      <div className="portal-action-cta cta-disabled">
                        <span>Permission Required</span>
                        <Lock size={14} />
                      </div>
                    ) : (
                      <div className="portal-action-cta cta-disabled">
                        <span>Under Development</span>
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
                    {inactiveModal.name} Module
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
