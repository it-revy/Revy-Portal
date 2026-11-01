import React from 'react';
import { X } from 'lucide-react';

const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  showCloseButton = true,
  maxWidth = '560px',
  className = ''
}) => {
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="revy-modal-backdrop modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div
        className={`revy-modal-card modal-content ${className}`.trim()}
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="revy-modal-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 1.25rem', borderBottom: '1px solid var(--color-border)' }}>
          {title && (
            <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
              {title}
            </h2>
          )}
          {showCloseButton && (
            <button
              type="button"
              className="revy-btn revy-btn-secondary revy-btn-sm"
              style={{ padding: '0.25rem 0.5rem', marginLeft: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              onClick={onClose}
              aria-label="Close dialog"
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="revy-modal-body" style={{ padding: '1.25rem', overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;
