import React from 'react';
import Modal from '../Modal';
import Button from './Button';
import { AlertTriangle } from 'lucide-react';

export default function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed with this action?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'danger', // 'danger' | 'primary'
  loading = false
}) {
  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      showCloseButton={!loading}
      maxWidth="480px"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            {cancelText}
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} loading={loading}>
            {confirmText}
          </Button>
        </>
      }
    >
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
        <div
          style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: confirmVariant === 'danger' ? 'var(--color-danger-bg, #fef2f2)' : 'var(--color-primary-subtle, #eff6ff)',
            color: confirmVariant === 'danger' ? 'var(--color-danger, #dc2626)' : 'var(--color-primary, #2563eb)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <AlertTriangle size={20} />
        </div>
        <div style={{ flex: 1 }}>
          <p style={{ margin: 0, fontSize: '0.95rem', color: 'var(--color-text-primary, #0f172a)', lineHeight: 1.5 }}>
            {message}
          </p>
        </div>
      </div>
    </Modal>
  );
}
