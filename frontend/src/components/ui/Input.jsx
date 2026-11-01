import React, { forwardRef } from 'react';

const Input = forwardRef(function Input(
  {
    type = 'text',
    size = 'md', // 'sm' | 'md'
    error = false,
    icon: Icon = null,
    className = '',
    style = {},
    ...props
  },
  ref
) {
  const sizeClass = size === 'sm' ? 'revy-input-sm' : '';
  const errorClass = error ? 'revy-input-error' : '';
  const combinedClass = `revy-input ${sizeClass} ${errorClass} ${className}`.trim();

  if (Icon) {
    return (
      <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
        <span
          style={{
            position: 'absolute',
            left: '0.75rem',
            color: 'var(--color-text-muted)',
            display: 'flex',
            alignItems: 'center',
            pointerEvents: 'none',
            zIndex: 2
          }}
        >
          <Icon size={size === 'sm' ? 14 : 16} />
        </span>
        <input
          ref={ref}
          type={type}
          className={combinedClass}
          style={{ paddingLeft: '2.25rem', ...style }}
          {...props}
        />
      </div>
    );
  }

  return (
    <input
      ref={ref}
      type={type}
      className={combinedClass}
      style={style}
      {...props}
    />
  );
});

export default Input;
