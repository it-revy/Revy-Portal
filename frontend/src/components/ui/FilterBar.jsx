import React from 'react';
import { RotateCcw } from 'lucide-react';
import Button from './Button';

export default function FilterBar({
  children,
  onReset = null,
  resetLabel = 'Reset Filters',
  hasActiveFilters = false,
  className = '',
  style = {}
}) {
  return (
    <div className={`revy-filter-bar ${className}`.trim()} style={style}>
      <div className="revy-filter-group" style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
        {children}
      </div>

      {onReset && (
        <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon={RotateCcw}
            onClick={onReset}
            title={resetLabel}
          >
            {resetLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
