import React, { useState, useEffect } from 'react';
import { MessageSquare, AlertCircle, Info, Calendar } from 'lucide-react';
import crmService from '../../../services/crmService';

const EVENT_TYPES = [
  'Introductory email sent',
  'Introductory call with client',
  'Email received from client',
  'Phone call with client',
  'In-person client meeting',
  'Technical discussion with client',
  'Discussion with REVY colleague (Internal)',
  'Internal laboratory review',
  'Proposal / Quote follow-up',
  'Other'
];

export default function CommunicationModal({
  isOpen,
  onClose,
  leadId,
  leadName,
  onCommunicationLogged
}) {
  const [formData, setFormData] = useState({
    channel: 'Phone / Call',
    eventType: 'Introductory call with client',
    summary: '',
    outcome: '',
    nextAction: '',
    followUpDate: '',
    communicationDate: new Date().toISOString().slice(0, 16)
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    setFormData({
      channel: 'Phone / Call',
      eventType: 'Introductory call with client',
      summary: '',
      outcome: '',
      nextAction: '',
      followUpDate: '',
      communicationDate: new Date().toISOString().slice(0, 16)
    });
    setError(null);
    setFieldErrors({});

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const isInternal = formData.eventType.includes('Internal') || formData.eventType.includes('colleague');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (error) setError(null);
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const validate = () => {
    const errors = {};
    if (!formData.summary.trim()) {
      errors.summary = 'Interaction summary / key takeaways are required.';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        channel: formData.channel,
        eventType: formData.eventType,
        summary: formData.summary.trim(),
        outcome: formData.outcome.trim() || undefined,
        nextAction: formData.nextAction.trim() || undefined,
        followUpDate: formData.followUpDate || undefined, // Date only: YYYY-MM-DD
        date: formData.communicationDate ? new Date(formData.communicationDate).toISOString() : undefined
      };

      const res = await crmService.addLeadCommunication(leadId, payload);
      if (res.data.success && res.data.communication) {
        onCommunicationLogged(res.data.communication);
        onClose();
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to record communication. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '560px', width: '92%', borderRadius: '12px', overflow: 'hidden' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header" style={{ padding: '1.1rem 1.25rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#e0e7ff',
              color: '#4f46e5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <MessageSquare size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>Log Client Communication</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Record client touchpoints, calls, emails, or internal discussions
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.25rem' }}>
            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '8px',
                color: '#b91c1c',
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
              fontSize: '0.85rem'
            }}>
              <span style={{ color: 'var(--text-muted)' }}>Active Lead: </span>
              <strong>{leadName}</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600 }}>Channel</label>
                <select
                  name="channel"
                  className="form-control"
                  value={formData.channel}
                  onChange={handleChange}
                >
                  <option value="Phone / Call">Phone / Call</option>
                  <option value="Email">Email</option>
                  <option value="In-Person Meeting">In-Person Meeting</option>
                  <option value="WhatsApp">WhatsApp</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600 }}>Interaction Type</label>
                <select
                  name="eventType"
                  className="form-control"
                  value={formData.eventType}
                  onChange={handleChange}
                >
                  {EVENT_TYPES.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600 }}>
                Interaction Date & Time (Timestamp)
              </label>
              <input
                type="datetime-local"
                name="communicationDate"
                className="form-control"
                value={formData.communicationDate}
                onChange={handleChange}
              />
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600 }}>
                Discussion Summary / Notes <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <textarea
                name="summary"
                className={`form-control ${fieldErrors.summary ? 'is-invalid' : ''}`}
                rows={3}
                placeholder="Key technical points discussed, client feedback, feedstock questions..."
                value={formData.summary}
                onChange={handleChange}
                required
              />
              {fieldErrors.summary && (
                <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  {fieldErrors.summary}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 500 }}>
                Outcome / Key Decisions <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
              </label>
              <input
                type="text"
                name="outcome"
                className="form-control"
                placeholder="e.g. Client requested sample pricing and technical deck"
                value={formData.outcome}
                onChange={handleChange}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500 }}>
                  Next Action <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
                </label>
                <input
                  type="text"
                  name="nextAction"
                  className="form-control"
                  placeholder="e.g. Follow up on proposal review"
                  value={formData.nextAction}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Calendar size={13} color="var(--text-muted)" />
                  <span>Next Follow-up Date</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Date only)</span>
                </label>
                <input
                  type="date"
                  name="followUpDate"
                  className="form-control"
                  value={formData.followUpDate}
                  onChange={handleChange}
                />
              </div>
            </div>

            {/* Note regarding last_connected_date */}
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '0.45rem',
              padding: '0.65rem 0.85rem',
              background: isInternal ? '#f1f5f9' : '#eff6ff',
              border: `1px solid ${isInternal ? '#cbd5e1' : '#bfdbfe'}`,
              borderRadius: '8px',
              fontSize: '0.78rem',
              color: isInternal ? '#475569' : '#1e40af'
            }}>
              <Info size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
              <span>
                {isInternal
                  ? 'Internal discussions with colleagues are recorded in communication history but do not advance the client "Last Connected Date".'
                  : 'Client-facing interactions automatically advance the lead\'s "Last Connected Date".'}
              </span>
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Record Communication'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
