import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Modal({
  isOpen,
  onClose,
  title,
  subtitle = null,
  description = null,
  children,
  footer = null,
  showCloseButton = true,
  maxWidth = '560px',
  className = ''
}) {
  // ESC key listener & body scroll lock
  useEffect(() => {
    if (!isOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sub = subtitle || description;

  return (
    <div
      className="revy-modal-backdrop modal-backdrop crm-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={`revy-modal-card modal-content crm-modal-container crm-modal ${className}`.trim()}
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="revy-modal-header crm-modal-header">
          <div style={{ flex: 1, paddingRight: '1rem' }}>
            {title && (
              <h3
                style={{
                  fontSize: '1.15rem',
                  fontWeight: 600,
                  color: 'var(--color-text-primary, #0f172a)',
                  margin: 0,
                  lineHeight: 1.3
                }}
              >
                {title}
              </h3>
            )}
            {sub && (
              <p
                style={{
                  fontSize: '0.85rem',
                  color: 'var(--color-text-secondary, #475569)',
                  margin: '0.25rem 0 0 0',
                  lineHeight: 1.4
                }}
              >
                {sub}
              </p>
            )}
          </div>
          {showCloseButton && (
            <button
              type="button"
              className="revy-btn revy-btn-secondary revy-btn-sm"
              style={{
                width: '32px',
                height: '32px',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '6px',
                color: 'var(--color-text-muted, #64748b)',
                border: '1px solid var(--color-border, #e2e8f0)',
                background: '#ffffff',
                cursor: 'pointer',
                flexShrink: 0
              }}
              onClick={onClose}
              aria-label="Close dialog"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="revy-modal-body crm-modal-body">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="revy-modal-footer crm-modal-footer">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
