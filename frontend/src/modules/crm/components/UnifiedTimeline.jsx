import React, { useState } from 'react';
import {
  MessageSquare,
  Mail,
  Phone,
  Users,
  FileText,
  RefreshCw,
  Clock,
  CheckCircle,
  AlertTriangle,
  ArrowUpDown,
  Filter,
  Plus,
  Send,
  Calendar,
  SkipForward,
  ChevronDown,
  ChevronUp,
  User as UserIcon,
  ShieldAlert,
  Sparkles
} from 'lucide-react';
import { formatISTTimestamp, formatDateOnly } from '../../../utils/dateUtils';

export default function UnifiedTimeline({
  timelineItems = [],
  loading = false,
  sortOrder = 'desc',
  onSortChange,
  activeFilter = 'all',
  onFilterChange,
  onOpenLogInteraction,
  onOpenRecordResponse,
  onCompleteActivity,
  onRescheduleActivity,
  onSkipActivity,
  onRefresh,
  canEdit = true
}) {
  const [expandedCardIds, setExpandedCardIds] = useState({});

  const toggleExpand = (id) => {
    setExpandedCardIds(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const formatDateTime = (isoStr) => {
    if (!isoStr) return '—';
    return formatISTTimestamp(isoStr, false);
  };

  const getItemIcon = (item) => {
    const actType = (item.activityType || '').toLowerCase();
    const source = (item.source || '').toLowerCase();
    const itemType = (item.itemType || '').toLowerCase();

    if (itemType === 'status_change' || source.includes('status')) {
      return <RefreshCw size={16} />;
    }
    if (itemType === 'customer_response' || source.includes('response')) {
      return <MessageSquare size={16} />;
    }
    if (actType.includes('email') || actType.includes('mail')) {
      return <Mail size={16} />;
    }
    if (actType.includes('phone') || actType.includes('call')) {
      return <Phone size={16} />;
    }
    if (actType.includes('meeting')) {
      return <Users size={16} />;
    }
    return <FileText size={16} />;
  };

  const getSourceBadgeStyle = (source, itemType) => {
    if (itemType === 'customer_response' || source === 'Customer Response') {
      return { bg: 'rgba(16, 185, 129, 0.12)', color: '#047857', border: '1px solid rgba(16, 185, 129, 0.3)' };
    }
    if (itemType === 'status_change' || source === 'Lead Status Change') {
      return { bg: 'rgba(245, 158, 11, 0.12)', color: '#b45309', border: '1px solid rgba(245, 158, 11, 0.3)' };
    }
    if (source === 'Lead Nurturing') {
      return { bg: 'rgba(59, 130, 246, 0.12)', color: '#1d4ed8', border: '1px solid rgba(59, 130, 246, 0.3)' };
    }
    if (source === 'System' || source === 'System Event') {
      return { bg: 'rgba(100, 116, 139, 0.12)', color: '#475569', border: '1px solid rgba(100, 116, 139, 0.3)' };
    }
    // Manual
    return { bg: 'rgba(139, 92, 246, 0.12)', color: '#6d28d9', border: '1px solid rgba(139, 92, 246, 0.3)' };
  };

  const getStatusBadge = (status, isOverdue) => {
    const s = (status || '').toLowerCase();
    if (isOverdue || s === 'overdue') {
      return <span className="status-badge absent">OVERDUE</span>;
    }
    if (s === 'completed') {
      return <span className="status-badge present">COMPLETED</span>;
    }
    if (s === 'in progress') {
      return <span className="status-badge in-progress">IN PROGRESS</span>;
    }
    if (s === 'skipped') {
      return <span className="status-badge late">SKIPPED</span>;
    }
    if (s === 'cancelled') {
      return <span className="status-badge absent">CANCELLED</span>;
    }
    return <span className="status-badge open">PENDING</span>;
  };

  const filterTabs = [
    { key: 'all', label: 'All Activities' },
    { key: 'nurturing', label: 'Cadence Activities' },
    { key: 'emails', label: 'Emails' },
    { key: 'calls', label: 'Calls' },
    { key: 'meetings', label: 'Meetings' },
    { key: 'notes', label: 'Manual Notes' },
    { key: 'status_changes', label: 'Status Changes' },
    { key: 'responses', label: 'Customer Responses' }
  ];

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: '12px', background: '#ffffff', boxShadow: '0 2px 10px rgba(0,0,0,0.03)' }}>
      {/* Timeline Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          paddingBottom: '1.25rem',
          borderBottom: '1px solid #e2e8f0'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 6px rgba(59, 130, 246, 0.25)'
            }}
          >
            <Clock size={20} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Unified Activity Timeline
            </h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Microsoft Dynamics 365 Sales Hub Interaction History ({timelineItems.length} events)
            </span>
          </div>
        </div>

        {/* Top Timeline Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          {/* Sort Order Toggle */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onSortChange(sortOrder === 'desc' ? 'asc' : 'desc')}
            title="Toggle sort order"
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}
          >
            <ArrowUpDown size={14} />
            <span>{sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}</span>
          </button>

          {/* Refresh Timeline */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            title="Refresh Timeline"
            disabled={loading}
            style={{ padding: '0.45rem 0.65rem' }}
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          </button>

          {canEdit && (
            <>
              {/* Record Customer Response */}
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onOpenRecordResponse}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.8rem',
                  color: '#047857',
                  borderColor: '#a7f3d0',
                  background: '#ecfdf5'
                }}
              >
                <MessageSquare size={14} /> Record Customer Response
              </button>

              {/* Log Manual Interaction */}
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={onOpenLogInteraction}
                style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', fontWeight: 600 }}
              >
                <Plus size={14} /> Log Interaction
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.85rem 0',
          overflowX: 'auto',
          borderBottom: '1px solid #f1f5f9',
          scrollbarWidth: 'none'
        }}
      >
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginRight: '0.35rem' }}>
          <Filter size={13} /> Filter:
        </span>
        {filterTabs.map(tab => (
          <button
            key={tab.key}
            type="button"
            onClick={() => onFilterChange(tab.key)}
            style={{
              padding: '0.3rem 0.65rem',
              borderRadius: '20px',
              border: activeFilter === tab.key ? '1px solid #3b82f6' : '1px solid #e2e8f0',
              background: activeFilter === tab.key ? '#eff6ff' : '#ffffff',
              color: activeFilter === tab.key ? '#1d4ed8' : 'var(--text-secondary)',
              fontSize: '0.78rem',
              fontWeight: activeFilter === tab.key ? 600 : 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Timeline Items List */}
      <div style={{ marginTop: '1.25rem' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
            <p style={{ margin: 0, fontSize: '0.875rem' }}>Loading chronological timeline...</p>
          </div>
        ) : timelineItems.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
            <Clock size={36} color="#cbd5e1" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
            <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No activities found matching this filter.
            </p>
            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem' }}>
              Activities generated by the 5-day cadence or manually logged interactions will appear here in chronological order.
            </p>
          </div>
        ) : (
          <div style={{ position: 'relative', paddingLeft: '2rem' }}>
            {/* Connected Vertical Timeline Rail */}
            <div
              style={{
                position: 'absolute',
                left: '15px',
                top: '12px',
                bottom: '12px',
                width: '2px',
                background: '#e2e8f0'
              }}
            />

            {/* Stacked Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {timelineItems.map((item) => {
                const isExpanded = expandedCardIds[item.id] || false;
                const sourceBadge = getSourceBadgeStyle(item.source, item.itemType);
                const isPendingNurturing = item.itemType === 'nurturing_activity' && (item.status === 'Pending' || item.status === 'In Progress' || item.status === 'Overdue');

                return (
                  <div key={item.id} style={{ position: 'relative' }}>
                    {/* Timeline Node Bullet */}
                    <div
                      style={{
                        position: 'absolute',
                        left: '-2rem',
                        top: '14px',
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: item.isOverdue
                          ? '#ef4444'
                          : item.status === 'Completed'
                          ? '#10b981'
                          : item.itemType === 'customer_response'
                          ? '#10b981'
                          : item.itemType === 'status_change'
                          ? '#f59e0b'
                          : '#3b82f6',
                        color: '#ffffff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: '3px solid #ffffff',
                        boxShadow: '0 2px 5px rgba(0,0,0,0.12)',
                        zIndex: 2
                      }}
                      title={item.source}
                    >
                      {getItemIcon(item)}
                    </div>

                    {/* Stacked Activity Card */}
                    <div
                      style={{
                        background: '#ffffff',
                        border: item.isOverdue
                          ? '1px solid #fecaca'
                          : item.status === 'Completed'
                          ? '1px solid #e2e8f0'
                          : '1px solid #cbd5e1',
                        borderRadius: '10px',
                        padding: '1rem 1.25rem',
                        boxShadow: '0 1px 4px rgba(0,0,0,0.03)',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      {/* Card Header */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            {/* Source Pill */}
                            <span
                              style={{
                                fontSize: '0.68rem',
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                letterSpacing: '0.04em',
                                padding: '0.15rem 0.5rem',
                                borderRadius: '4px',
                                background: sourceBadge.bg,
                                color: sourceBadge.color,
                                border: sourceBadge.border
                              }}
                            >
                              {item.source}
                            </span>

                            {item.stageNumber && (
                              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                                Stage {item.stageNumber}
                              </span>
                            )}

                            {/* Status Badge */}
                            {getStatusBadge(item.status, item.isOverdue)}
                          </div>

                          {/* Card Title */}
                          <h4 style={{ margin: '0.35rem 0 0.15rem 0', fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {item.title}
                          </h4>
                        </div>

                        {/* Date and Time */}
                        <div style={{ textAlign: 'right', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          <div>{formatDateTime(item.timestamp)}</div>
                          {item.dueDate && (
                            <div style={{ fontSize: '0.73rem', marginTop: '2px', color: item.isOverdue ? '#dc2626' : 'var(--text-secondary)' }}>
                              Due: <strong>{formatDateOnly(item.dueDate)}</strong>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Description / Summary */}
                      {item.description && (
                        <div style={{ margin: '0.5rem 0 0.25rem 0', fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                          {item.description}
                        </div>
                      )}

                      {/* Responsible User Info */}
                      {item.responsibleUser && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.45rem' }}>
                          <UserIcon size={12} />
                          <span>
                            Recorded by <strong>{item.responsibleUser.name || item.responsibleUser.username}</strong>
                          </span>
                          {item.code && <span style={{ marginLeft: '0.5rem', color: '#94a3b8' }}>&bull; Ref: {item.code}</span>}
                        </div>
                      )}

                      {/* Expandable Section Details */}
                      {(item.notes || item.outcome || item.skipReason || item.rescheduleReason || item.nextAction) && (
                        <div style={{ marginTop: '0.5rem' }}>
                          <button
                            type="button"
                            onClick={() => toggleExpand(item.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--accent-primary)',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              padding: 0
                            }}
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            <span>{isExpanded ? 'Hide Details' : 'View Notes & Outcomes'}</span>
                          </button>

                          {isExpanded && (
                            <div
                              style={{
                                marginTop: '0.5rem',
                                padding: '0.65rem 0.85rem',
                                background: '#f8fafc',
                                borderRadius: '6px',
                                border: '1px solid #e2e8f0',
                                fontSize: '0.8rem',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.35rem'
                              }}
                            >
                              {item.outcome && (
                                <div>
                                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Outcome: </span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{item.outcome}</span>
                                </div>
                              )}
                              {item.notes && (
                                <div>
                                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Notes: </span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{item.notes}</span>
                                </div>
                              )}
                              {item.nextAction && (
                                <div>
                                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Next Action: </span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{item.nextAction}</span>
                                </div>
                              )}
                              {item.skipReason && (
                                <div style={{ color: '#b45309' }}>
                                  <span style={{ fontWeight: 600 }}>Skip Reason: </span>
                                  <span>{item.skipReason}</span>
                                </div>
                              )}
                              {item.rescheduleReason && (
                                <div style={{ color: '#1d4ed8' }}>
                                  <span style={{ fontWeight: 600 }}>Reschedule Reason: </span>
                                  <span>{item.rescheduleReason}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Direct Inline Action Buttons for Pending Cadence Activities */}
                      {canEdit && isPendingNurturing && (
                        <div
                          style={{
                            marginTop: '0.75rem',
                            paddingTop: '0.75rem',
                            borderTop: '1px dashed #e2e8f0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            gap: '0.5rem'
                          }}
                        >
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => onRescheduleActivity({
                              ...item,
                              activityId: item.rawId || item.activityId || (typeof item.id === 'string' ? item.id.replace(/^act_/, '') : item.id)
                            })}
                            style={{ fontSize: '0.78rem' }}
                          >
                            <Calendar size={13} /> Reschedule
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => onSkipActivity({
                              ...item,
                              activityId: item.rawId || item.activityId || (typeof item.id === 'string' ? item.id.replace(/^act_/, '') : item.id)
                            })}
                            style={{ fontSize: '0.78rem' }}
                          >
                            <SkipForward size={13} /> Skip Stage
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            onClick={() => onCompleteActivity({
                              ...item,
                              activityId: item.rawId || item.activityId || (typeof item.id === 'string' ? item.id.replace(/^act_/, '') : item.id)
                            })}
                            style={{ fontSize: '0.78rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                          >
                            <Send size={13} /> Complete / Confirm Sent
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

