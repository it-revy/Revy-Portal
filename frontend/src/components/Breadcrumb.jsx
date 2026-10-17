import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const BMS_PAGES = {
  today: "Today's Entry",
  response: "Today's Entry",
  'breakfast-response': "Today's Entry",
  dashboard: "Dashboard",
  'daily-entry': "Daily Entry",
  'today-breakfast': "Today's Breakfast",
  'today-list': "Today's Breakfast List",
  'additional-orders': "Additional Orders",
  orders: "Breakfast Orders",
  'breakfast-money': "Breakfast Money",
  'fund-requests': "Finance Fund Requests",
  employees: "Employee Directory",
  holidays: "Public Holidays",
  reports: "Monthly Reports",
  'ceo-dashboard': "Directors Dashboard",
  'audit-logs': "Audit Trail",
  settings: "Settings"
};

const USER_MGMT_PAGES = {
  users: "Users",
  'user-management': "User Directory"
};

const Breadcrumb = () => {
  const location = useLocation();
  const path = location.pathname;

  // No breadcrumb needed on the root portal or login
  if (path === '/' || path === '/portal' || path === '/login') {
    return null;
  }

  // Determine Module Identity
  const isUserMgmt = path.startsWith('/user-management') || path.startsWith('/users');
  const isCRM = path.startsWith('/crm');

  let crumbs = [];

  // 1. Root is always Central Portal
  crumbs.push({
    label: "Portal",
    to: "/portal"
  });

  if (isCRM) {
    // 2. Module: CRM
    crumbs.push({
      label: "CRM",
      to: "/crm/dashboard"
    });

    const segments = path.split('/').filter(Boolean);
    if (segments.length > 1) {
      const second = segments[1];
      if (second === 'dashboard') {
        crumbs.push({ label: "Dashboard", isCurrent: true });
      } else if (second === 'leads') {
        if (segments.length > 2) {
          crumbs.push({ label: "Leads", to: "/crm/leads" });
          crumbs.push({ label: segments[2].toUpperCase().startsWith("LEAD-") ? segments[2].toUpperCase() : "Lead Details", isCurrent: true });
        } else {
          crumbs.push({ label: "Leads", isCurrent: true });
        }
      } else if (second === 'user-hub' || second === 'users') {
        crumbs.push({ label: "CRM User Hub", isCurrent: true });
      } else {
        crumbs.push({ label: second.charAt(0).toUpperCase() + second.slice(1).replace(/-/g, ' '), isCurrent: true });
      }
    }
  } else if (isUserMgmt) {
    // 2. Module: User Management
    crumbs.push({
      label: "User Management",
      to: "/user-management"
    });

    // 3. Sub-page
    crumbs.push({
      label: "Users",
      isCurrent: true
    });
  } else {
    // 2. Module: BMS (Breakfast Management System)
    crumbs.push({
      label: "BMS",
      to: "/breakfast"
    });

    // 3. Sub-page identification
    const segments = path.split('/').filter(Boolean);
    const lastSegment = segments[segments.length - 1] || 'dashboard';
    const pageLabel = BMS_PAGES[lastSegment] ||
                      (segments.includes('employees') ? "Employee Directory" : null) ||
                      (segments.includes('orders') ? "Breakfast Orders" : null) ||
                      (segments.includes('reports') ? "Monthly Reports" : null) ||
                      lastSegment.charAt(0).toUpperCase() + lastSegment.slice(1).replace(/-/g, ' ');

    crumbs.push({
      label: pageLabel,
      isCurrent: true
    });
  }

  return (
    <nav style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', color: 'var(--text-secondary)' }} aria-label="Breadcrumb">
      {crumbs.map((crumb, idx) => {
        const isLast = idx === crumbs.length - 1;

        return (
          <React.Fragment key={crumb.label + idx}>
            {idx > 0 && <ChevronRight size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />}
            {isLast || crumb.isCurrent ? (
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.to}
                style={{
                  color: 'var(--text-secondary)',
                  textDecoration: 'none',
                  transition: 'color 0.15s ease'
                }}
                className="hover-text-primary"
              >
                {crumb.label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
