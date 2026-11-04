import React, { useState, useEffect } from 'react';
import { MessageSquare, AlertCircle, PhoneCall, Mail, Users, CheckCircle } from 'lucide-react';
import crmService from '../../../services/crmService';

export default function CustomerResponseModal({
  isOpen,
  onClose,
  lead,
  onResponseRecorded
}) {
  const [formData, setFormData] = useState({
    channel: 'Email',
    outcome: 'Interested',
    responseNotes: '',
    targetLifecycleStatus: 'Negotiation',
    pauseNurturing: true
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);

    setFormData({
      channel: 'Email',
      outcome: 'Interested',
      responseNotes: '',
      targetLifecycleStatus: 'Negotiation',
      pauseNurturing: true
    });
    setError(null);

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !lead) return null;

  const handleOutcomeChange = (newOutcome) => {
    let suggestedStatus = lead.lifecycleStatus;
    if (newOutcome === 'Interested' || newOutcome === 'Meeting Requested') {
      suggestedStatus = 'Negotiation';
    } else if (newOutcome === 'Not Interested') {
      suggestedStatus = 'Dormant';
    }
    setFormData(prev => ({
      ...prev,
      outcome: newOutcome,
      targetLifecycleStatus: suggestedStatus
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.responseNotes.trim()) {
      setError('Response notes and client feedback are required.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        channel: formData.channel,
        outcome: formData.outcome,
        responseNotes: formData.responseNotes.trim(),
        targetLifecycleStatus: formData.targetLifecycleStatus || undefined,
        pauseNurturing: Boolean(formData.pauseNurturing)
      };

      const res = await crmService.recordCustomerResponse(lead.id, payload);
      if (res.data.success) {
        onResponseRecorded(res.data.nurturing);
        onClose();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to record customer response.');
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
                background: '#dcfce7',
                color: '#16a34a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <MessageSquare size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Record Customer Response</h3>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {lead.leadName} ({lead.leadId})
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

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  Response Channel <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <select
                  className="form-control"
                  value={formData.channel}
                  onChange={e => setFormData({ ...formData, channel: e.target.value })}
                >
                  <option value="Email">Email</option>
                  <option value="Phone / Call">Phone / Call</option>
                  <option value="WhatsApp">WhatsApp</option>
                  <option value="In-Person Meeting">In-Person Meeting</option>
                  <option value="Virtual Meeting">Virtual Meeting</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                  Outcome / Sentiment <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <select
                  className="form-control"
                  value={formData.outcome}
                  onChange={e => handleOutcomeChange(e.target.value)}
                >
                  <option value="Interested">Interested (Ready for Commercial Scope)</option>
                  <option value="Meeting Requested">Meeting Requested</option>
                  <option value="Callback Requested">Callback Requested</option>
                  <option value="Information Requested">Information / Specs Requested</option>
                  <option value="Not Interested">Not Interested / Closed</option>
                  <option value="Budget Constraint">Budget Constraint</option>
                  <option value="Other">Other Response</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                Customer Feedback / Discussion Notes <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Document client feedback, specific interest areas, questions raised, or agreed next steps..."
                value={formData.responseNotes}
                onChange={e => setFormData({ ...formData, responseNotes: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                Synchronize Lead Lifecycle Status
              </label>
              <select
                className="form-control"
                value={formData.targetLifecycleStatus}
                onChange={e => setFormData({ ...formData, targetLifecycleStatus: e.target.value })}
              >
                <option value="Enquiry">Enquiry (Remain in Enquiry)</option>
                <option value="Offer">Offer (Prepare Commercial Offer)</option>
                <option value="Negotiation">Negotiation (Commercial Scope & Pricing)</option>
                <option value="Supply">Supply (Execution Phase)</option>
                <option value="Payment">Payment (Payment Follow-up)</option>
                <option value="Dormant">Dormant (Archive / Not Interested)</option>
              </select>
            </div>

            <div
              style={{
                padding: '0.75rem',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem'
              }}
            >
              <input
                type="checkbox"
                id="pauseCadence"
                checked={formData.pauseNurturing}
                onChange={e => setFormData({ ...formData, pauseNurturing: e.target.checked })}
                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
              />
              <label htmlFor="pauseCadence" style={{ fontSize: '0.82rem', margin: 0, cursor: 'pointer', color: 'var(--text-primary)' }}>
                <strong>Pause automatic nurturing cadence</strong> (Recommended: stops pending automatic reminder emails/calls)
              </label>
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Recording...' : 'Record Response'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

