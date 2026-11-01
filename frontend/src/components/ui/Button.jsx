import React from 'react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'danger' | 'success' | 'outline' | 'ghost'
  size = 'md',        // 'sm' | 'md' | 'lg'
  icon: Icon = null,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  type = 'button',
  className = '',
  style = {},
  onClick,
  ...props
}) {
  const variantClass = `revy-btn-${variant}`;
  const sizeClass = size !== 'md' ? `revy-btn-${size}` : '';
  const combinedClassName = `revy-btn ${variantClass} ${sizeClass} ${className}`.trim();

  return (
    <button
      type={type}
      className={combinedClassName}
      disabled={disabled || loading}
      onClick={onClick}
      style={style}
      {...props}
    >
      {loading ? (
        <span
          className="revy-spinner"
          style={{
            width: '14px',
            height: '14px',
            border: '2px solid rgba(255, 255, 255, 0.3)',
            borderTopColor: '#ffffff',
            borderRadius: '50%',
            animation: 'revySpin 0.8s linear infinite',
            marginRight: children ? '6px' : '0'
          }}
        />
      ) : (
        Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 14 : 16} />
      )}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={size === 'sm' ? 14 : 16} />}
    </button>
  );
}
