import React from 'react';

export default function FilterField({
  label = null,
  layout = 'horizontal', // 'horizontal' | 'stacked'
  children,
  className = '',
  style = {}
}) {
  const isStacked = layout === 'stacked';

  return (
    <div
      className={`revy-filter-item ${className}`.trim()}
      style={{
        display: isStacked ? 'flex' : 'inline-flex',
        flexDirection: isStacked ? 'column' : 'row',
        alignItems: isStacked ? 'flex-start' : 'center',
        gap: isStacked ? '4px' : '8px',
        ...style
      }}
    >
      {label && (
        <label
          className="revy-filter-label"
          style={{
            fontSize: 'var(--font-size-sm)',
            fontWeight: 500,
            color: 'var(--color-text-secondary)',
            whiteSpace: 'nowrap'
          }}
        >
          {label}
        </label>
      )}
      {children}
    </div>
  );
}
