import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

const pathNameMap = {
  today: "Today's Entry",
  admin: "Admin",
  dashboard: "Dashboard",
  'today-list': "Today's Breakfast List",
  orders: "Breakfast Orders",
  employees: "Employee Directory",
  holidays: "Public Holidays",
  reports: "Monthly Reports",
  'director-analytics': "Director Analytics",
  'ceo-dashboard': "Director Analytics",
  'audit-logs': "Audit Trail",
  settings: "Settings"
};

const Breadcrumb = () => {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(x => x);

  if (pathnames.length === 0) return null;

  return (
    <nav style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
      <Link to="/today" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Home</Link>
      {pathnames.map((name, index) => {
        const routeTo = `/${pathnames.slice(0, index + 1).join('/')}`;
        const isLast = index === pathnames.length - 1;
        const displayName = pathNameMap[name] || name;

        return (
          <React.Fragment key={name}>
            <ChevronRight size={14} color="var(--text-muted)" />
            {isLast ? (
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{displayName}</span>
            ) : (
              <Link to={routeTo} style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>
                {displayName}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};

export default Breadcrumb;
