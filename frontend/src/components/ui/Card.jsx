import React from 'react';

export default function Card({
  title = null,
  subtitle = null,
  action = null,
  children,
  footer = null,
  className = '',
  style = {}
}) {
  return (
    <div className={`revy-card ${className}`.trim()} style={style}>
      {(title || action) && (
        <div className="revy-card-header">
          <div>
            {title && (
              <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {title}
              </h3>
            )}
            {subtitle && (
              <p style={{ margin: '4px 0 0 0', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className="revy-card-body">{children}</div>
      {footer && (
        <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border)' }}>
          {footer}
        </div>
      )}
    </div>
  );
}
