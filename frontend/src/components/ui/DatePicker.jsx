import React from 'react';
import { Calendar } from 'lucide-react';

export default function DatePicker({
  value = '',
  onChange,
  min,
  max,
  size = 'md', // 'sm' | 'md'
  disabled = false,
  className = '',
  style = {},
  ...props
}) {
  const sizeClass = size === 'sm' ? 'revy-input-sm' : '';

  return (
    <div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center', width: '100%' }}>
      <input
        type="date"
        className={`revy-input ${sizeClass} ${className}`.trim()}
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        disabled={disabled}
        style={{ ...style }}
        {...props}
      />
    </div>
  );
}
