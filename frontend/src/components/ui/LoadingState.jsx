import React from 'react';

export default function LoadingState({
  message = 'Loading data...',
  size = 'md', // 'sm' | 'md' | 'lg'
  minHeight = '200px',
  className = '',
  style = {}
}) {
  const spinnerSize = size === 'sm' ? '18px' : size === 'lg' ? '32px' : '24px';

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        minHeight,
        color: 'var(--color-text-secondary)',
        ...style
      }}
    >
      <div
        style={{
          width: spinnerSize,
          height: spinnerSize,
          border: '2px solid var(--color-border)',
          borderTopColor: 'var(--color-primary)',
          borderRadius: '50%',
          animation: 'revySpin 0.8s linear infinite'
        }}
      />
      {message && <span style={{ fontSize: 'var(--font-size-sm)' }}>{message}</span>}
    </div>
  );
}
