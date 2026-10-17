import React, { useState, useEffect } from 'react';
import { AlertTriangle, AlertCircle, RefreshCw } from 'lucide-react';
import crmService from '../../../services/crmService';

export default function LeadStatusModal({
  isOpen,
  onClose,
  lead,
  onStatusUpdated
}) {
  const [newStatus, setNewStatus] = useState(lead?.lifecycleStatus || 'Qualified');
  const [remarks, setRemarks] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !lead) return null;

  const currentStatus = lead.lifecycleStatus;
  const isReopening = newStatus === 'Open' && currentStatus !== 'Open';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newStatus === currentStatus) {
      setError('Please select a different lifecycle status.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await crmService.transitionLeadStatus(lead.id, {
        status: newStatus,
        remarks: remarks.trim() || undefined
      });

      if (res.data.success) {
        onStatusUpdated(res.data.lead);
        onClose();
      }
    } catch (err) {
      if (err.response?.status === 409) {
        setError(err.response.data?.message || 'Cannot reopen: another open lead already exists for this client with this requirement.');
      } else {
        setError(err.response?.data?.message || 'Failed to update lead status. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '480px' }} onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <RefreshCw size={20} color="var(--accent-primary)" />
            <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Change Lead Lifecycle Status</h3>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem',
                background: 'var(--danger-bg)',
                border: '1px solid var(--danger-border)',
                borderRadius: '8px',
                color: 'var(--danger-text)',
                fontSize: '0.875rem'
              }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <div style={{
              padding: '0.75rem 1rem',
              background: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
              fontSize: '0.875rem'
            }}>
              <span style={{ color: 'var(--text-muted)' }}>Lead: </span>
              <strong>{lead.leadName}</strong> ({lead.leadId})
              <div style={{ marginTop: '0.25rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Current Status: </span>
                <span className={`status-badge ${currentStatus.toLowerCase()}`}>
                  {currentStatus}
                </span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600 }}>
                Select New Status <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <select
                className="form-control"
                value={newStatus}
                onChange={e => setNewStatus(e.target.value)}
              >
                <option value="Open">Open (Active Investigation / Enquiry)</option>
                <option value="Qualified">Qualified (Client verified & project confirmed)</option>
                <option value="Disqualified">Disqualified (Budget mismatch, lost, or irrelevant)</option>
              </select>
            </div>

            {isReopening && (
              <div style={{
                padding: '0.75rem',
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '6px',
                color: '#92400e',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <AlertTriangle size={15} style={{ flexShrink: 0 }} />
                <span>Reopening this lead will enforce duplicate checks against any existing open leads for this client.</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">
                Transition Remarks / Reason
              </label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Explain why this status transition is taking place (e.g. client budget finalized, technical feasibility approved)..."
                value={remarks}
                onChange={e => setRemarks(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Update Status'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
