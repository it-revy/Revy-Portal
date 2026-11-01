import React from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export default function PageHeader({
  title,
  subtitle = null,
  icon: Icon = null,
  iconBg = 'linear-gradient(135deg, #2563eb, #1d4ed8)',
  iconColor = '#ffffff',
  breadcrumbs = null,
  actions = null,
  className = '',
  style = {}
}) {
  const renderBreadcrumbs = () => {
    if (!breadcrumbs) return null;

    if (Array.isArray(breadcrumbs)) {
      return (
        <nav aria-label="Breadcrumb" style={{ marginBottom: '6px' }}>
          <ol
            style={{
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '4px',
              listStyle: 'none',
              margin: 0,
              padding: 0,
              fontSize: '0.8125rem'
            }}
          >
            {breadcrumbs.map((crumb, idx) => {
              const isLast = idx === breadcrumbs.length - 1;
              const label = typeof crumb === 'object' && crumb !== null ? crumb.label : crumb;
              const to = typeof crumb === 'object' && crumb !== null ? crumb.to : null;

              return (
                <li key={idx} style={{ display: 'inline-flex', alignItems: 'center' }}>
                  {to && !isLast ? (
                    <Link
                      to={to}
                      style={{
                        color: 'var(--color-text-secondary, #64748b)',
                        textDecoration: 'none',
                        fontWeight: 500,
                        transition: 'color 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.color = 'var(--color-primary-600, #2563eb)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.color = 'var(--color-text-secondary, #64748b)';
                      }}
                    >
                      {label}
                    </Link>
                  ) : (
                    <span
                      style={{
                        color: isLast ? 'var(--color-text-primary, #0f172a)' : 'var(--color-text-secondary, #64748b)',
                        fontWeight: isLast ? 600 : 400
                      }}
                      aria-current={isLast ? 'page' : undefined}
                    >
                      {label}
                    </span>
                  )}
                  {!isLast && (
                    <ChevronRight
                      size={12}
                      style={{
                        margin: '0 4px',
                        color: 'var(--color-text-muted, #94a3b8)',
                        flexShrink: 0
                      }}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      );
    }

    return <div style={{ marginBottom: '6px' }}>{breadcrumbs}</div>;
  };

  return (
    <div className={`revy-page-header ${className}`.trim()} style={style}>
      <div className="revy-page-header-left">
        {Icon && (
          <div
            className="revy-page-header-icon"
            style={{ background: iconBg, color: iconColor }}
          >
            <Icon size={22} />
          </div>
        )}
        <div>
          {renderBreadcrumbs()}
          <h1 className="revy-page-header-title">{title}</h1>
          {subtitle && <p className="revy-page-header-subtitle">{subtitle}</p>}
        </div>
      </div>

      {actions && <div className="revy-page-header-actions">{actions}</div>}
    </div>
  );
}
