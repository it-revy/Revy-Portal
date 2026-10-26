import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Calendar
} from 'lucide-react';
import crmService from '../../../services/crmService';

const STAGES = ['Qualify', 'Develop', 'Propose', 'Close'];

const QUICK_LOSS_REASONS = [
  'Competitor Chosen',
  'Budgetary Constraint',
  'Scope Incompatible',
  'Project Deferred / Cancelled',
  'Client Chose In-House Solution',
  'No Response / Stalled',
  'Technical Feasibility Failed'
];

export default function OpportunityStageModal({ isOpen, onClose, opportunity, onSuccess }) {
  const [targetStage, setTargetStage] = useState('Qualify');
  const [targetStatus, setTargetStatus] = useState('Open');
  const [lossReason, setLossReason] = useState('');
  const [actualCloseDate, setActualCloseDate] = useState(new Date().toISOString().split('T')[0]);
  const [remarks, setRemarks] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen || !opportunity) return;
    setTargetStage(opportunity.stage || 'Qualify');
    setTargetStatus(opportunity.status || 'Open');
    setLossReason(opportunity.lossReason || '');
    setActualCloseDate(
      opportunity.actualCloseDate
        ? opportunity.actualCloseDate.split('T')[0]
        : new Date().toISOString().split('T')[0]
    );
    setRemarks('');
    setError(null);
  }, [isOpen, opportunity]);

  if (!isOpen || !opportunity) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (targetStatus === 'Lost' && !lossReason.trim()) {
      setError('Please provide a loss reason when marking an opportunity as Lost.');
      return;
    }

    if (targetStatus === 'Won' && targetStage !== 'Close') {
      setError('An opportunity must be in the "Close" stage to be marked as Won.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        newStage: targetStage,
        status: targetStatus,
        remarks: remarks.trim() || undefined
      };

      if (targetStatus === 'Lost') {
        payload.lossReason = lossReason.trim();
        payload.actualCloseDate = actualCloseDate || undefined;
      } else if (targetStatus === 'Won') {
        payload.actualCloseDate = actualCloseDate || undefined;
      }

      const res = await crmService.transitionOpportunityStage(opportunity.id, payload);
      if (res.data?.success) {
        if (onSuccess) onSuccess(res.data.opportunity);
        onClose();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update stage. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{
          maxWidth: '560px',
          width: '92%',
          borderRadius: '12px',
          padding: '1.75rem',
          background: '#ffffff',
          boxShadow: 'var(--modal-shadow)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'var(--accent-light)',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <TrendingUp size={22} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Opportunity Stage & Outcome
              </h3>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {opportunity.opportunityId} — <strong>{opportunity.name}</strong>
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: '1.25rem', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {error && (
          <div style={{
            padding: '0.75rem 1rem',
            background: 'var(--danger-bg)',
            border: '1px solid var(--danger-border)',
            borderRadius: '6px',
            color: 'var(--danger-text)',
            fontSize: '0.85rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.15rem' }}>
          {/* Outcome Radio Selector */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              Select Opportunity Outcome:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.65rem' }}>
              <button
                type="button"
                onClick={() => {
                  setTargetStatus('Open');
                  setLossReason('');
                }}
                style={{
                  padding: '0.65rem 0.5rem',
                  borderRadius: '8px',
                  border: targetStatus === 'Open' ? '2px solid var(--accent-primary)' : '1px solid var(--border-color)',
                  background: targetStatus === 'Open' ? 'var(--accent-light)' : '#ffffff',
                  color: targetStatus === 'Open' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <ArrowRight size={15} />
                <span>Open Pipeline</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTargetStatus('Won');
                  setTargetStage('Close');
                  setLossReason('');
                }}
                style={{
                  padding: '0.65rem 0.5rem',
                  borderRadius: '8px',
                  border: targetStatus === 'Won' ? '2px solid var(--success)' : '1px solid var(--border-color)',
                  background: targetStatus === 'Won' ? 'var(--success-bg)' : '#ffffff',
                  color: targetStatus === 'Won' ? 'var(--success)' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <CheckCircle2 size={15} />
                <span>Closed Won</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setTargetStatus('Lost');
                }}
                style={{
                  padding: '0.65rem 0.5rem',
                  borderRadius: '8px',
                  border: targetStatus === 'Lost' ? '2px solid var(--danger)' : '1px solid var(--border-color)',
                  background: targetStatus === 'Lost' ? 'var(--danger-bg)' : '#ffffff',
                  color: targetStatus === 'Lost' ? 'var(--danger)' : 'var(--text-secondary)',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.4rem'
                }}
              >
                <XCircle size={15} />
                <span>Closed Lost</span>
              </button>
            </div>
          </div>

          {/* Target Pipeline Stage (Enabled when Open or transitioning) */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
              Pipeline Stage:
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.4rem' }}>
              {STAGES.map((stg) => {
                const isSelected = targetStage === stg;
                const isDisabled = targetStatus === 'Won' && stg !== 'Close';
                return (
                  <button
                    key={stg}
                    type="button"
                    disabled={isDisabled}
                    onClick={() => setTargetStage(stg)}
                    style={{
                      padding: '0.5rem 0.35rem',
                      borderRadius: '6px',
                      border: isSelected ? '2px solid var(--accent-primary)' : '1px solid var(--border-color)',
                      background: isSelected ? 'var(--accent-light)' : (isDisabled ? '#f1f5f9' : '#ffffff'),
                      color: isSelected ? 'var(--accent-primary)' : (isDisabled ? 'var(--text-muted)' : 'var(--text-primary)'),
                      fontWeight: isSelected ? 700 : 500,
                      fontSize: '0.825rem',
                      cursor: isDisabled ? 'not-allowed' : 'pointer',
                      textAlign: 'center'
                    }}
                  >
                    {stg}
                  </button>
                );
              })}
            </div>
          </div>

          {/* If Lost, mandatory Loss Reason */}
          {targetStatus === 'Lost' && (
            <div style={{ background: '#fef2f2', padding: '0.85rem', borderRadius: '8px', border: '1px solid #fecaca' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--danger-text)', marginBottom: '0.35rem' }}>
                Loss Reason <span style={{ color: 'var(--danger)' }}>*</span>
              </label>

              {/* Quick Pills */}
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                {QUICK_LOSS_REASONS.map((reason) => (
                  <button
                    key={reason}
                    type="button"
                    onClick={() => setLossReason(reason)}
                    style={{
                      fontSize: '0.725rem',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      background: lossReason === reason ? 'var(--danger)' : '#ffffff',
                      color: lossReason === reason ? '#ffffff' : '#7f1d1d',
                      border: '1px solid #fca5a5',
                      cursor: 'pointer'
                    }}
                  >
                    {reason}
                  </button>
                ))}
              </div>

              <textarea
                className="form-control"
                rows={2}
                placeholder="Specific loss rationale (required)..."
                value={lossReason}
                onChange={(e) => setLossReason(e.target.value)}
                style={{ width: '100%', fontSize: '0.85rem' }}
                required
              />
            </div>
          )}

          {/* Actual Close Date for Won or Lost */}
          {(targetStatus === 'Won' || targetStatus === 'Lost') && (
            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                Actual Close Date:
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Calendar size={16} color="var(--text-muted)" />
                <input
                  type="date"
                  className="form-control"
                  value={actualCloseDate}
                  onChange={(e) => setActualCloseDate(e.target.value)}
                  style={{ maxWidth: '200px', fontSize: '0.85rem' }}
                />
              </div>
            </div>
          )}

          {/* Remarks */}
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
              Transition Remarks (Optional):
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Scope refined, client contract verbally agreed..."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              style={{ width: '100%', fontSize: '0.85rem' }}
            />
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ minWidth: '130px' }}
            >
              {loading ? 'Updating...' : 'Confirm Stage'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
