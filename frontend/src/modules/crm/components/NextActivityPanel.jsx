import React from 'react';
import {
  Clock,
  AlertTriangle,
  CheckCircle,
  Play,
  Pause,
  XCircle,
  Calendar,
  User,
  Mail,
  Phone,
  Users,
  FileText,
  ChevronRight,
  Send,
  SkipForward
} from 'lucide-react';
import { formatDateOnly } from '../../../utils/dateUtils';

export default function NextActivityPanel({
  nextActivity,
  nurturingState,
  onCompleteActivity,
  onRescheduleActivity,
  onSkipActivity,
  onPauseNurturing,
  onResumeNurturing,
  canEdit = true
}) {
  if (!nurturingState && !nextActivity) {
    return null;
  }

  const isPaused = nextActivity?.isPaused || nurturingState?.status === 'Paused';
  const isCompleted = nurturingState?.status === 'Completed';
  const isCancelled = nurturingState?.status === 'Cancelled';
  const act = nextActivity?.activityId ? nextActivity : null;

  const getActivityIcon = (type) => {
    const t = (type || '').toLowerCase();
    if (t.includes('email') || t.includes('mail')) return <Mail size={18} />;
    if (t.includes('phone') || t.includes('call')) return <Phone size={18} />;
    if (t.includes('meeting')) return <Users size={18} />;
    return <FileText size={18} />;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Not scheduled';
    return formatDateOnly(dateStr);
  };

  return (
    <div
      className="glass-panel"
      style={{
        padding: '1.25rem 1.5rem',
        borderRadius: '10px',
        borderLeft: act?.isOverdue
          ? '4px solid #ef4444'
          : isPaused
          ? '4px solid #f59e0b'
          : isCompleted
          ? '4px solid #10b981'
          : '4px solid #3b82f6',
        background: '#ffffff',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
        marginBottom: '1.25rem'
      }}
    >
      {/* Top Banner / Stage Indicator */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: '0.2rem 0.6rem',
              borderRadius: '4px',
              background: isPaused
                ? 'rgba(245, 158, 11, 0.15)'
                : isCompleted
                ? 'rgba(16, 185, 129, 0.15)'
                : act?.isOverdue
                ? 'rgba(239, 68, 68, 0.15)'
                : 'rgba(59, 130, 246, 0.12)',
              color: isPaused
                ? '#b45309'
                : isCompleted
                ? '#047857'
                : act?.isOverdue
                ? '#b91c1c'
                : '#1d4ed8'
            }}
          >
            {isPaused
              ? 'Workflow Paused'
              : isCompleted
              ? 'Workflow Completed'
              : isCancelled
              ? 'Workflow Cancelled'
              : `Stage ${act?.stageNumber || nurturingState?.currentStage || 1} of 10`}
          </span>

          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Microsoft Dynamics 365 Sales Hub Cadence
          </span>
        </div>

        {/* Global Pause/Resume Control */}
        {canEdit && !isCompleted && !isCancelled && (
          <div>
            {isPaused ? (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onResumeNurturing}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: '#047857' }}
              >
                <Play size={14} /> Resume Cadence
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onPauseNurturing}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', color: '#b45309' }}
              >
                <Pause size={14} /> Pause Cadence
              </button>
            )}
          </div>
        )}
      </div>

      {/* Main Content Body */}
      {isPaused ? (
        <div style={{ padding: '0.5rem 0', display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <AlertTriangle size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '1rem', fontWeight: 600, color: '#92400e' }}>
              Automatic Follow-up Communications Paused
            </h4>
            <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {nextActivity?.pauseReason || nurturingState?.pauseReason || 'Cadence paused due to recorded customer response or manual user intervention. Automatic reminders are on hold until manually resumed.'}
            </p>
            {canEdit && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={onResumeNurturing}
                style={{ fontSize: '0.8rem' }}
              >
                Resume Nurturing Workflow
              </button>
            )}
          </div>
        </div>
      ) : isCompleted ? (
        <div style={{ padding: '0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <CheckCircle size={22} color="#10b981" />
          <div>
            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#065f46' }}>
              Lead Nurturing Workflow Completed
            </h4>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              All cadence activities have been successfully conducted or concluded.
            </p>
          </div>
        </div>
      ) : isCancelled ? (
        <div style={{ padding: '0.5rem 0', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <XCircle size={22} color="#6b7280" />
          <div>
            <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#374151' }}>
              Nurturing Cadence Concluded
            </h4>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Reason: {nurturingState?.stopReason || 'Nurturing was discontinued.'}
            </p>
          </div>
        </div>
      ) : act ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div
                style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '8px',
                  background: act.isOverdue ? '#fee2e2' : '#eff6ff',
                  color: act.isOverdue ? '#dc2626' : '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}
              >
                {getActivityIcon(act.activityType)}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {act.subject}
                  </h3>
                  <span className={`status-badge ${act.isOverdue ? 'absent' : 'open'}`} style={{ fontSize: '0.72rem' }}>
                    {act.isOverdue ? `OVERDUE (${act.overdueDays}d)` : 'PENDING'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '0.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Calendar size={13} color="var(--text-muted)" />
                    Due: <strong style={{ color: act.isOverdue ? '#dc2626' : 'inherit' }}>{formatDate(act.dueDate)}</strong>
                  </span>
                  {!act.isOverdue && act.remainingDays !== undefined && (
                    <span style={{ color: 'var(--text-muted)' }}>
                      ({act.remainingDays === 0 ? 'Due Today' : `${act.remainingDays} days remaining`})
                    </span>
                  )}
                  {act.owner && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <User size={13} color="var(--text-muted)" />
                      Owner: <strong>{act.owner.name || act.owner.username}</strong>
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Direct Action Buttons */}
            {canEdit && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onRescheduleActivity(act)}
                  title="Reschedule activity due date"
                  style={{ fontSize: '0.8rem' }}
                >
                  <Calendar size={14} /> Reschedule
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSkipActivity(act)}
                  title="Skip this activity stage"
                  style={{ fontSize: '0.8rem' }}
                >
                  <SkipForward size={14} /> Skip
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onCompleteActivity(act)}
                  style={{ fontSize: '0.82rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <Send size={14} /> Mark Complete / Confirm Sent
                </button>
              </div>
            )}
          </div>

          {act.description && (
            <div
              style={{
                marginTop: '0.75rem',
                padding: '0.65rem 0.85rem',
                background: '#f8fafc',
                borderRadius: '6px',
                border: '1px solid #e2e8f0',
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.45
              }}
            >
              {act.description}
            </div>
          )}
        </div>
      ) : (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
          No pending activity currently scheduled.
        </div>
      )}
    </div>
  );
}

