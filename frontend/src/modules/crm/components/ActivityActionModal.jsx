import React, { useState, useEffect } from 'react';
import { Calendar, SkipForward, AlertCircle } from 'lucide-react';
import crmService from '../../../services/crmService';

export default function ActivityActionModal({
  isOpen,
  onClose,
  actionType, // 'reschedule' or 'skip'
  activity,
  lead,
  onActionSuccess
}) {
  const [newDueDate, setNewDueDate] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !activity) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);

    const defaultDate = activity.dueDate
      ? activity.dueDate.slice(0, 10)
      : new Date().toISOString().slice(0, 10);

    setNewDueDate(defaultDate);
    setReason('');
    setError(null);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activity, onClose]);

  if (!isOpen || !activity || !lead) return null;

  const isReschedule = actionType === 'reschedule';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError(`A reason is required to ${isReschedule ? 'reschedule' : 'skip'} this activity.`);
      return;
    }

    if (isReschedule && !newDueDate) {
      setError('Please select a valid new due date.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const targetActId = activity.rawId || activity.activityId || (typeof activity.id === 'string' ? activity.id.replace(/^act_/, '') : activity.id);
      if (isReschedule) {
        const payload = {
          newDueDate,
          reason: reason.trim()
        };
        const res = await crmService.rescheduleNurturingActivity(lead.id, targetActId, payload);
        if (res.data.success) {
          onActionSuccess(res.data.nurturing);
          onClose();
        }
      } else {
        const payload = {
          reason: reason.trim()
        };
        const res = await crmService.skipNurturingActivity(lead.id, targetActId, payload);
        if (res.data.success) {
          onActionSuccess(res.data.nurturing);
          onClose();
        }
      }
    } catch (err) {
      setError(err.response?.data?.message || `Failed to ${actionType} activity.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '480px', width: '92%', borderRadius: '12px', overflow: 'hidden' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header" style={{ padding: '1.1rem 1.25rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: isReschedule ? '#eff6ff' : '#fff7ed',
                color: isReschedule ? '#2563eb' : '#ea580c',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {isReschedule ? <Calendar size={18} /> : <SkipForward size={18} />}
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                {isReschedule ? 'Reschedule Activity' : 'Skip Nurturing Stage'}
              </h3>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Stage {activity.stageNumber}: {activity.subject}
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {error && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  background: 'var(--danger-bg)',
                  border: '1px solid var(--danger-border)',
                  borderRadius: '8px',
                  color: 'var(--danger-text)',
                  fontSize: '0.85rem'
                }}
              >
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            {isReschedule && (
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  New Due Date <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <input
                  type="date"
                  className="form-control"
                  value={newDueDate}
                  onChange={e => setNewDueDate(e.target.value)}
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                Reason <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <textarea
                className="form-control"
                rows={3}
                placeholder={
                  isReschedule
                    ? 'Explain why this activity is being rescheduled (e.g. client contact travelling, requested delayed follow-up)...'
                    : 'Explain why this stage is being skipped (e.g. client requested immediate quotation, stage redundant)...'
                }
                value={reason}
                onChange={e => setReason(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : isReschedule ? 'Reschedule Activity' : 'Skip Stage'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

