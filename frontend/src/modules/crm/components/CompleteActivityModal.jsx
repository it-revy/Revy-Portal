import React, { useState, useEffect } from 'react';
import { Send, AlertCircle, Info } from 'lucide-react';
import crmService from '../../../services/crmService';

export default function CompleteActivityModal({
  isOpen,
  onClose,
  activity,
  lead,
  onActivityCompleted
}) {
  const [formData, setFormData] = useState({
    notes: '',
    outcome: 'Sent successfully',
    emailMessageReference: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !activity) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);

    setFormData({
      notes: '',
      outcome: activity.activityType === 'Email' ? 'Email sent successfully' : 'Completed successfully',
      emailMessageReference: ''
    });
    setError(null);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, activity, onClose]);

  if (!isOpen || !activity || !lead) return null;

  const isEmail = activity.activityType === 'Email';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        notes: formData.notes.trim() || undefined,
        outcome: formData.outcome.trim() || undefined,
        emailMessageReference: formData.emailMessageReference.trim() || undefined
      };

      const targetActId = activity.rawId || activity.activityId || (typeof activity.id === 'string' ? activity.id.replace(/^act_/, '') : activity.id);
      const res = await crmService.completeNurturingActivity(lead.id, targetActId, payload);
      if (res.data.success) {
        onActivityCompleted(res.data.nurturing);
        onClose();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to complete activity. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '520px', width: '92%', borderRadius: '12px', overflow: 'hidden' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header" style={{ padding: '1.1rem 1.25rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: '#eff6ff',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Send size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                {isEmail ? 'Confirm Sent / Mark Complete' : 'Complete Nurturing Activity'}
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

            <div
              style={{
                padding: '0.75rem 1rem',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '0.85rem'
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Activity: </span>
              <strong>{activity.subject}</strong> ({activity.activityType})
              <div style={{ marginTop: '0.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Client: <strong>{lead.companyName || lead.leadName}</strong> &bull; Contact: <strong>{lead.contactEmail || lead.businessPhone || 'Primary Contact'}</strong>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                Outcome / Delivery Status
              </label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Sent introductory deck, Meeting conducted, Voicemail left..."
                value={formData.outcome}
                onChange={e => setFormData({ ...formData, outcome: e.target.value })}
              />
            </div>

            {isEmail && (
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  Email Subject / Reference ID <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(Optional)</span>
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Intro: REVY Bio-solutions capabilities - Ref #1042"
                  value={formData.emailMessageReference}
                  onChange={e => setFormData({ ...formData, emailMessageReference: e.target.value })}
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                Completion Notes / Summary
              </label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Enter key discussion takeaways, customized proposal points mentioned, or customer feedback..."
                value={formData.notes}
                onChange={e => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>

            <div
              style={{
                padding: '0.75rem',
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '6px',
                fontSize: '0.8rem',
                color: '#1e40af',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.5rem'
              }}
            >
              <Info size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Automatic Log Interaction:</strong> Completing this activity will automatically create an interaction history entry in the chronological timeline and schedule the subsequent 5-day cadence stage.
              </div>
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Confirming...' : 'Confirm & Complete'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

