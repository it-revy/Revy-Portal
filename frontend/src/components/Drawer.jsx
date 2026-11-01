import React from 'react';
import { X, User, History, Shield, Calendar } from 'lucide-react';

const Drawer = ({ isOpen, onClose, title, children, width = '500px', className = '' }) => {
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
    <>
      <div className="drawer-overlay revy-modal-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        className={`drawer-panel revy-drawer ${className}`.trim()}
        style={{ width: `min(100vw, ${width})`, maxWidth: '100vw' }}
        role="dialog"
        aria-modal="true"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.85rem' }}>
          <h2 style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--color-text-primary)', margin: 0 }}>
            {title}
          </h2>
          <button
            type="button"
            className="revy-btn revy-btn-secondary revy-btn-sm"
            style={{ padding: '0.25rem 0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={onClose}
            aria-label="Close drawer"
          >
            <X size={16} />
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </>
  );
};

export default Drawer;
