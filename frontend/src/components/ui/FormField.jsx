import React from 'react';

export default function FormField({
  label = null,
  required = false,
  error = null,
  helpText = null,
  children,
  className = '',
  style = {}
}) {
  return (
    <div className={`revy-form-group ${className}`.trim()} style={style}>
      {label && (
        <label className={`revy-form-label ${required ? 'required' : ''}`}>
          {label}
        </label>
      )}
      {children}
      {error && (
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-danger)', marginTop: '2px' }}>
          {error}
        </span>
      )}
      {helpText && !error && (
        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: '2px' }}>
          {helpText}
        </span>
      )}
    </div>
  );
}
