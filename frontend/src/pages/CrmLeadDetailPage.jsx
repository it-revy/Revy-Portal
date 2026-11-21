import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Building,
  User,
  Phone,
  Mail,
  MapPin,
  Globe,
  Edit,
  RefreshCw,
  Plus,
  Briefcase,
  Clock,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  XCircle
} from 'lucide-react';
import crmService from '../services/crmService';
import LeadStatusModal from '../modules/crm/components/LeadStatusModal';
import CommunicationModal from '../modules/crm/components/CommunicationModal';
import LeadQualifyWizard from '../modules/crm/components/LeadQualifyWizard';
import NextActivityPanel from '../modules/crm/components/NextActivityPanel';
import UnifiedTimeline from '../modules/crm/components/UnifiedTimeline';
import CustomerResponseModal from '../modules/crm/components/CustomerResponseModal';
import CompleteActivityModal from '../modules/crm/components/CompleteActivityModal';
import ActivityActionModal from '../modules/crm/components/ActivityActionModal';
import { PageHeader, Button } from '../components/ui';
import { formatISTTimestamp, formatISTDate, formatDateOnly } from '../utils/dateUtils';

export default function CrmLeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const [lead, setLead] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successNotification, setSuccessNotification] = useState(null);
  const [warningNotification, setWarningNotification] = useState(null);

  // Nurturing & Unified Timeline State
  const [nurturingState, setNurturingState] = useState(null);
  const [nextActivity, setNextActivity] = useState(null);
  const [timelineItems, setTimelineItems] = useState([]);
  const [timelineSort, setTimelineSort] = useState('desc');
  const [timelineFilter, setTimelineFilter] = useState('all');
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Modals
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);
  const [isQualifyWizardOpen, setIsQualifyWizardOpen] = useState(false);
  const [viewContactModal, setViewContactModal] = useState(null);
  const [viewOpportunityModal, setViewOpportunityModal] = useState(null);
  const [selectedOppIdForDetail, setSelectedOppIdForDetail] = useState(null);

  // Nurturing Action Modals
  const [completeActivityModal, setCompleteActivityModal] = useState(null);
  const [actionActivityModal, setActionActivityModal] = useState(null);
  const [isCustomerResponseModalOpen, setIsCustomerResponseModalOpen] = useState(false);

  // Unqualify Lead Modal State
  const [isUnqualifyModalOpen, setIsUnqualifyModalOpen] = useState(false);
  const [disqualificationReason, setDisqualificationReason] = useState('');
  const [unqualifyError, setUnqualifyError] = useState(null);
  const [submittingUnqualify, setSubmittingUnqualify] = useState(false);

  const canEdit = hasPermission('crm.lead.edit');
  const canUpdateStatus = hasPermission('crm.lead.status.update');
  const canLogComm = hasPermission('crm.communication.create') || hasPermission('crm.lead.edit');
  const canUnqualify = (canEdit || canUpdateStatus) &&
    lead &&
    !lead.isQualified &&
    !lead.qualifiedAt &&
    !lead.convertedAt &&
    !lead.opportunityId &&
    lead.lifecycleStatus !== 'Dormant' &&
    lead.lifecycleStatus !== 'Disqualified' &&
    !lead.disqualificationReason;

  const fetchLeadDetails = useCallback(async () => {
    const cleanId = (id || '').trim();
    if (!cleanId) {
      setError('Invalid lead identifier.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [leadRes, nurturingRes, nextActRes, timelineRes] = await Promise.all([
        crmService.getLeadById(cleanId),
        crmService.getLeadNurturing(cleanId).catch(() => ({ data: { success: false } })),
        crmService.getLeadNextActivity(cleanId).catch(() => ({ data: { success: false } })),
        crmService.getLeadTimeline(cleanId, { sort: timelineSort, filter: timelineFilter }).catch(() => ({ data: { success: false, timeline: [] } }))
      ]);

      if (leadRes.data?.success) {
        setLead(leadRes.data.lead);
      }
      if (nurturingRes.data?.success) {
        setNurturingState(nurturingRes.data.nurturing);
      }
      if (nextActRes.data?.success) {
        setNextActivity(nextActRes.data.nextActivity);
      }
      if (timelineRes.data?.success) {
        setTimelineItems(timelineRes.data.timeline || []);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`Lead with identifier "${cleanId}" not found.`);
      } else {
        setError(err.response?.data?.message || 'Failed to load lead details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id, timelineSort, timelineFilter]);

  const handleTimelineFilterChange = async (filterKey) => {
    setTimelineFilter(filterKey);
    setTimelineLoading(true);
    try {
      const res = await crmService.getLeadTimeline(id, { sort: timelineSort, filter: filterKey });
      if (res.data?.success) {
        setTimelineItems(res.data.timeline || []);
      }
    } catch (err) {
      console.error('Failed to filter timeline:', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleTimelineSortChange = async (newSort) => {
    setTimelineSort(newSort);
    setTimelineLoading(true);
    try {
      const res = await crmService.getLeadTimeline(id, { sort: newSort, filter: timelineFilter });
      if (res.data?.success) {
        setTimelineItems(res.data.timeline || []);
      }
    } catch (err) {
      console.error('Failed to sort timeline:', err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handlePauseNurturing = async () => {
    if (!window.confirm('Pause automatic lead nurturing cadence for this lead? Pending reminder emails and calls will be put on hold.')) return;
    try {
      const res = await crmService.pauseNurturing(id, { reason: 'User paused cadence from Lead Details panel.' });
      if (res.data.success) {
        fetchLeadDetails();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to pause nurturing.');
    }
  };

  const handleResumeNurturing = async () => {
    try {
      const res = await crmService.resumeNurturing(id, {});
      if (res.data.success) {
        fetchLeadDetails();
      }
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to resume nurturing.');
    }
  };

  useEffect(() => {
    fetchLeadDetails();
  }, [fetchLeadDetails]);



  const formatDateTime = (isoStr) => {
    if (!isoStr) return '—';
    return formatISTTimestamp(isoStr, false);
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    let badgeClass = 'status-badge';
    if (s === 'new' || s === 'open') badgeClass = 'status-badge open';
    else if (s === 'contacted') badgeClass = 'status-badge info';
    else if (s === 'in discussion' || s === 'in-discussion') badgeClass = 'status-badge in-progress';
    else if (s === 'qualified') badgeClass = 'status-badge success';
    else if (s === 'dormant') badgeClass = 'status-badge absent';
    else if (s === 'disqualified') badgeClass = 'status-badge danger';

    return <span className={badgeClass}>{status}</span>;
  };

  const handleUnqualifyLead = async (e) => {
    e.preventDefault();
    if (!disqualificationReason.trim()) {
      setUnqualifyError('Disqualification reason is mandatory.');
      return;
    }
    setSubmittingUnqualify(true);
    setUnqualifyError(null);
    try {
      await crmService.unqualifyLead(lead.id, { reason: disqualificationReason.trim() });
      setIsUnqualifyModalOpen(false);
      setDisqualificationReason('');
      setSuccessNotification(`Lead ${lead.leadId} has been marked as unqualified.`);
      fetchLeadDetails();
    } catch (err) {
      setUnqualifyError(err.response?.data?.message || err.response?.data?.detail || 'Failed to unqualify lead.');
    } finally {
      setSubmittingUnqualify(false);
    }
  };

  if (loading) {
    return (
      <div className="page-body" style={{ textAlign: 'center', padding: '5rem 0', color: 'var(--text-secondary)' }}>
        <RefreshCw size={28} className="spin" style={{ margin: '0 auto 1rem', display: 'block' }} />
        Loading lead dossier and interaction history...
      </div>
    );
  }

  if (error || !lead) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', maxWidth: '540px', margin: '3rem auto' }}>
          <AlertCircle size={40} color="var(--danger)" style={{ margin: '0 auto 1rem', display: 'block' }} />
          <h2 style={{ marginBottom: '0.75rem', color: 'var(--danger)' }}>Unable to View Lead</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error || 'Lead not found.'}</p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            <button
              onClick={() => fetchLeadDetails()}
              className="btn btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <RefreshCw size={15} /> Try Again
            </button>
            <button onClick={() => navigate('/crm/leads')} className="btn btn-secondary">
              ← Return to Leads
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-body">
      {/* Success Notification Banner */}
      {successNotification && (
        <div style={{
          padding: '0.85rem 1rem',
          background: '#ecfdf5',
          border: '1px solid #a7f3d0',
          borderRadius: '8px',
          color: '#065f46',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          boxShadow: '0 2px 6px rgba(16, 185, 129, 0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle2 size={18} style={{ color: '#059669', flexShrink: 0 }} />
            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>{successNotification}</span>
          </div>
          <button
            onClick={() => setSuccessNotification(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#065f46', fontSize: '1.2rem', lineHeight: 1 }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* Non-blocking Warning Notification */}
      {warningNotification && (
        <div style={{
          padding: '0.85rem 1rem',
          background: '#fffbeb',
          border: '1px solid #fde68a',
          borderRadius: '8px',
          color: '#92400e',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          boxShadow: '0 2px 6px rgba(245, 158, 11, 0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} style={{ color: '#d97706', flexShrink: 0 }} />
            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>{warningNotification}</span>
          </div>
          <button
            onClick={() => setWarningNotification(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontSize: '1.2rem', lineHeight: 1 }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* Top Navigation & Action Bar */}
      <PageHeader
        title={lead.leadName || lead.displayName || lead.leadId}
        subtitle={`Created on ${formatDateTime(lead.createdAt)}`}
        breadcrumbs={[
          { label: 'CRM', to: '/crm/dashboard' },
          { label: 'Leads', to: '/crm/leads' },
          { label: lead.leadId || 'Lead Details' }
        ]}
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            {getStatusBadge(lead.lifecycleStatus)}

            {(!lead.isQualified && !lead.qualifiedAt && lead.lifecycleStatus !== 'Qualified' && !lead.opportunityId) && (canEdit || canUpdateStatus) ? (
              <Button
                variant="primary"
                onClick={() => setIsQualifyWizardOpen(true)}
                icon={ShieldCheck}
                style={{ background: 'var(--color-success)', borderColor: 'var(--color-success)' }}
              >
                Qualify Lead
              </Button>
            ) : (lead.isQualified || lead.qualifiedAt || lead.lifecycleStatus === 'Qualified' || lead.opportunityId) ? (
              <Button
                variant="primary"
                onClick={() => navigate(`/crm/opportunities/${lead.opportunityId || lead.opportunity?.id}`)}
                icon={Briefcase}
                style={{ background: 'var(--accent-primary)', borderColor: 'var(--accent-primary)' }}
              >
                View Opportunity
              </Button>
            ) : null}

            {canUnqualify && (
              <Button
                variant="secondary"
                onClick={() => setIsUnqualifyModalOpen(true)}
                icon={XCircle}
                style={{ color: 'var(--color-danger, #ef4444)', borderColor: 'var(--color-danger, #ef4444)' }}
              >
                Unqualify
              </Button>
            )}

            {canLogComm && (
              <Button
                variant="secondary"
                onClick={() => setIsCommModalOpen(true)}
                icon={Plus}
              >
                Log Interaction
              </Button>
            )}

            {canUpdateStatus && (
              <Button
                variant="secondary"
                onClick={() => setIsStatusModalOpen(true)}
                icon={RefreshCw}
              >
                Change Status
              </Button>
            )}

            {canEdit && (
              <Button
                variant="secondary"
                onClick={() => navigate(`/crm/leads/${lead.id}/edit`)}
                icon={Edit}
              >
                Edit Details
              </Button>
            )}
          </div>
        }
      />

      {/* Disqualification Reason Banner */}
      {lead.disqualificationReason && (
        <div style={{
          marginBottom: 'var(--space-4)',
          padding: '0.85rem 1.25rem',
          borderRadius: '8px',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
          color: '#991b1b'
        }}>
          <XCircle size={20} style={{ color: '#ef4444', flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong style={{ fontSize: '0.9rem', display: 'block', marginBottom: '0.2rem' }}>
              Lead Disqualified ({lead.lifecycleStatus})
            </strong>
            <span style={{ fontSize: '0.85rem' }}>
              Reason: {lead.disqualificationReason}
            </span>
          </div>
        </div>
      )}

      {/* Commercial Opportunities (1:N) & Qualification Status */}
      {((lead.opportunities && lead.opportunities.length > 0) || lead.opportunity || lead.isQualified || lead.qualifiedAt || lead.lifecycleStatus === 'Qualified') && (
        <div className="glass-panel" style={{
          padding: '1.25rem 1.5rem',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1.5rem',
          border: '1px solid #e2e8f0',
          background: '#ffffff'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '1rem',
            flexWrap: 'wrap',
            gap: '0.75rem'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '38px',
                height: '38px',
                borderRadius: '8px',
                background: 'var(--accent-light)',
                color: 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Briefcase size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Commercial Opportunities ({lead.opportunities?.length || (lead.opportunity ? 1 : 0)})
                </h3>
                <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {lead.isQualified || lead.qualifiedAt
                    ? `Lead qualified on ${lead.qualifiedAt ? formatISTDate(lead.qualifiedAt) : '—'}${lead.qualifiedByName ? ` by ${lead.qualifiedByName}` : ''}.`
                    : 'Track multiple commercial requirements, offers, and proposals for this lead.'}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {lead.account && (
                <Link
                  to={`/crm/accounts?search=${encodeURIComponent(lead.account.name)}`}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <Building size={14} color="#d97706" />
                  <span>{lead.account.name}</span>
                </Link>
              )}
              {lead.contact && (
                <Link
                  to={`/crm/contacts?search=${encodeURIComponent(lead.contact.name)}`}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <User size={14} />
                  <span>{lead.contact.name}</span>
                </Link>
              )}

            </div>
          </div>

          {/* Opportunity List Table */}
          {((lead.opportunities && lead.opportunities.length > 0) || lead.opportunity) ? (
            <div className="table-responsive">
              <table className="crm-table" style={{ fontSize: '0.85rem' }}>
                <thead>
                  <tr>
                    <th style={{ width: '120px' }}>Opp ID</th>
                    <th>Opportunity Name</th>
                    <th style={{ width: '100px' }}>Stage</th>
                    <th style={{ width: '140px' }}>Sub-status</th>
                    <th style={{ width: '120px' }}>Est. Value</th>
                    <th style={{ width: '90px' }}>Status</th>
                    <th style={{ width: '90px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {(lead.opportunities && lead.opportunities.length > 0
                    ? lead.opportunities
                    : [lead.opportunity]
                  ).map((opp) => (
                    <tr key={opp.id}>
                      <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                        <Link
                          to={`/crm/opportunities/${opp.id}`}
                          style={{ color: 'var(--accent-primary)', fontWeight: 700, textDecoration: 'none' }}
                          title="View Dedicated Opportunity Page"
                        >
                          {opp.opportunityId || opp.id}
                        </Link>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        <Link
                          to={`/crm/opportunities/${opp.id}`}
                          style={{ textDecoration: 'none', color: 'var(--text-primary)' }}
                          title="View Dedicated Opportunity Page"
                        >
                          {opp.name}
                        </Link>
                      </td>
                      <td>
                        <span style={{
                          padding: '2px 7px',
                          borderRadius: '4px',
                          fontSize: '0.725rem',
                          fontWeight: 700,
                          background: opp.stage === 'Close' ? '#dcfce7' : '#eff6ff',
                          color: opp.stage === 'Close' ? '#166534' : '#1d4ed8'
                        }}>
                          {opp.stage || 'Qualify'}
                        </span>
                      </td>
                      <td>
                        {opp.subStatus || opp.sub_status ? (
                          <span style={{ fontSize: '0.75rem', color: '#334155', fontWeight: 500 }} title={opp.subStatus || opp.sub_status}>
                            {(opp.subStatus || opp.sub_status).length > 20
                              ? `${(opp.subStatus || opp.sub_status).substring(0, 20)}...`
                              : (opp.subStatus || opp.sub_status)}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontStyle: 'italic' }}>—</span>
                        )}
                      </td>
                      <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                        {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                          `${opp.currency || 'INR'} ${Number(opp.estimatedValue).toLocaleString()}`
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400 }}>—</span>
                        )}
                      </td>
                      <td>
                        <span style={{
                          padding: '2px 7px',
                          borderRadius: '4px',
                          fontSize: '0.725rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          background: opp.status === 'Won' ? 'var(--success-bg)' : opp.status === 'Lost' ? 'var(--danger-bg)' : 'var(--accent-light)',
                          color: opp.status === 'Won' ? 'var(--success)' : opp.status === 'Lost' ? 'var(--danger)' : 'var(--accent-primary)'
                        }}>
                          {opp.status || 'Open'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <Link
                          to={`/crm/opportunities/${opp.id}`}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          style={{ padding: '2px 8px', fontSize: '0.75rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}
                          title="View Dedicated Opportunity Page"
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No commercial opportunities created yet. Commercial opportunities are linked via Lead Qualification.
            </div>
          )}
        </div>
      )}

      {/* Main Grid: 2 Columns */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start' }}>
        {/* Left Column: Requirements & Communication Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Requirement Overview Card */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Briefcase size={18} color="var(--accent-primary)" />
              <span>Business Requirement & Specification</span>
            </h3>

            <div style={{ marginBottom: '1.25rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Business Area
                </label>
                <div style={{ marginTop: '0.2rem' }}>
                  <span style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    background: lead.businessArea === 'Biogas' ? '#fef3c7' : '#e0f2fe',
                    color: lead.businessArea === 'Biogas' ? '#b45309' : '#0369a1'
                  }}>
                    {lead.businessArea}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Requested Product / Service Specification
              </label>
              <div style={{
                marginTop: '0.35rem',
                padding: '0.75rem 1rem',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '0.95rem',
                fontWeight: 600,
                color: '#0f172a'
              }}>
                {lead.requestedProductService || (
                  <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400 }}>
                    Not specified yet (Early Enquiry)
                  </span>
                )}
              </div>
            </div>

            {lead.requirementSummary && (
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Requirement Summary / Scope
                </label>
                <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {lead.requirementSummary}
                </p>
              </div>
            )}

            {/* Site / Location Info */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', paddingTop: '1rem', borderTop: '1px solid #f1f5f9' }}>
              {lead.siteName && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Site / Plant Name</label>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{lead.siteName}</div>
                </div>
              )}
              {lead.location && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Location</label>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <MapPin size={13} color="var(--text-muted)" />
                    <span>{lead.location}</span>
                  </div>
                </div>
              )}
              {lead.websiteLink && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Website / Document Link</label>
                  <div>
                    {(() => {
                      const raw = (lead.websiteLink || '').trim();
                      if (raw.toLowerCase().startsWith('javascript:') || raw.toLowerCase().startsWith('data:')) {
                        return <span style={{ fontSize: '0.875rem', color: '#b91c1c' }}>Unsafe link blocked</span>;
                      }
                      const safeUrl = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
                      const displayDomain = raw.replace(/^https?:\/\//i, '').replace(/\/$/, '');
                      return (
                        <a
                          href={safeUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: '0.875rem', color: 'var(--accent-primary)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}
                        >
                          <Globe size={14} />
                          <span>{displayDomain}</span>
                        </a>
                      );
                    })()}
                  </div>
                </div>
              )}
            </div>

            {/* Description & Contact Preferences */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', paddingTop: '1rem', borderTop: '1px solid #f1f5f9' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Client Relationship</label>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: lead.clientStatus === 'Existing' ? '#0369a1' : '#15803d' }}>
                  {lead.clientStatus || 'New'}
                </div>
              </div>

              {lead.currency && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Currency</label>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{lead.currency}</div>
                </div>
              )}

              {lead.contactMethods && lead.contactMethods.length > 0 && (
                <div style={{ gridColumn: '1 / -1', marginTop: '0.25rem' }}>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.35rem' }}>
                    Contact Method Preferences
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                    {lead.contactMethods.map((m, idx) => (
                      <span
                        key={idx}
                        style={{
                          fontSize: '0.78rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: m === lead.preferredContactMethod ? '#dcfce7' : '#f1f5f9',
                          color: m === lead.preferredContactMethod ? '#166534' : '#334155',
                          border: m === lead.preferredContactMethod ? '1px solid #86efac' : '1px solid #cbd5e1',
                          fontWeight: m === lead.preferredContactMethod ? 600 : 400
                        }}
                      >
                        {m} {m === lead.preferredContactMethod ? '★ Preferred' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {lead.description && (
              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #f1f5f9' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Detailed Enquiry Description
                </label>
                <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                  {lead.description}
                </p>
              </div>
            )}
          </div>

          {/* Current Remarks & Follow-up Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Clock size={18} color="var(--accent-primary)" />
              <span>Current Status & Follow-up Actions</span>
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Next Follow-up Date
                </span>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: '0.2rem' }}>
                  {formatDateOnly(lead.nextFollowUpDate)}
                </div>
              </div>

              <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Next Follow-up Action
                </span>
                <div style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: '0.2rem' }}>
                  {lead.nextFollowUpAction || 'None defined'}
                </div>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Latest Remarks Summary
              </label>
              <div style={{
                marginTop: '0.35rem',
                padding: '0.75rem 1rem',
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                fontSize: '0.875rem',
                color: lead.remarks ? '#334155' : 'var(--text-muted)',
                lineHeight: 1.6,
                fontStyle: lead.remarks ? 'normal' : 'italic'
              }}>
                {lead.remarks || 'No remarks recorded yet. Remarks are preserved as the latest summary alongside chronological communication history below.'}
              </div>
            </div>
          </div>

          {/* Next Activity Panel (Microsoft Dynamics 365 Sales Hub approach) */}
          <NextActivityPanel
            nextActivity={nextActivity}
            nurturingState={nurturingState}
            onCompleteActivity={(act) => setCompleteActivityModal(act)}
            onRescheduleActivity={(act) => setActionActivityModal({ activity: act, actionType: 'reschedule' })}
            onSkipActivity={(act) => setActionActivityModal({ activity: act, actionType: 'skip' })}
            onPauseNurturing={handlePauseNurturing}
            onResumeNurturing={handleResumeNurturing}
            canEdit={canEdit}
          />

          {/* Unified Activity Timeline (Dynamics 365 Sales Hub stacked layout) */}
          <UnifiedTimeline
            timelineItems={timelineItems}
            loading={timelineLoading}
            sortOrder={timelineSort}
            onSortChange={handleTimelineSortChange}
            activeFilter={timelineFilter}
            onFilterChange={handleTimelineFilterChange}
            onOpenLogInteraction={() => setIsCommModalOpen(true)}
            onOpenRecordResponse={() => setIsCustomerResponseModalOpen(true)}
            onCompleteActivity={(act) => setCompleteActivityModal(act)}
            onRescheduleActivity={(act) => setActionActivityModal({ activity: act, actionType: 'reschedule' })}
            onSkipActivity={(act) => setActionActivityModal({ activity: act, actionType: 'skip' })}
            onRefresh={() => fetchLeadDetails()}
            canEdit={canEdit}
          />
        </div>

        {/* Right Column: Account, Contact, and Lead Ownership */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Linked Opportunity Card (if qualified) */}
          {(lead.opportunity || lead.opportunityId) && (
            <div className="glass-panel" style={{
              padding: '1.25rem',
              borderLeft: '4px solid var(--accent-primary)',
              background: '#f8fafc'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <h4 style={{
                  margin: 0,
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--text-primary)'
                }}>
                  <Briefcase size={16} color="var(--accent-primary)" />
                  <span>Linked Opportunity</span>
                </h4>
                <span style={{
                  fontSize: '0.72rem',
                  background: 'var(--accent-light)',
                  color: 'var(--accent-primary)',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontWeight: 700
                }}>
                  {lead.opportunity?.status || 'Open'}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div>
                  <button
                    type="button"
                    onClick={() => setViewOpportunityModal(lead.opportunity || { id: lead.opportunityId, name: lead.opportunityName || 'Linked Opportunity' })}
                    style={{
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      color: 'var(--accent-primary)',
                      fontSize: '1.05rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      textAlign: 'left',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                    onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                    title="Click to view Opportunity details"
                  >
                    <span>{lead.opportunityName || lead.opportunity?.name || 'Linked Opportunity'}</span>
                    <ExternalLink size={12} />
                  </button>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                    Opportunity ID: <span style={{ fontWeight: 600, color: '#334155' }}>{lead.opportunity?.opportunityId || lead.opportunityId}</span>
                  </div>
                </div>

                {lead.opportunity?.estimatedValue && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <strong>Estimated Value:</strong> {lead.opportunity?.currency || 'INR'} {Number(lead.opportunity.estimatedValue).toLocaleString()}
                  </div>
                )}

                <div style={{ paddingTop: '0.5rem', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => setViewOpportunityModal(lead.opportunity || { id: lead.opportunityId, name: lead.opportunityName || 'Linked Opportunity' })}
                    className="crm-btn crm-btn-secondary crm-btn-sm"
                    style={{ flex: 1 }}
                  >
                    View Details
                  </button>
                  <Link
                    to="/crm/opportunities"
                    className="crm-btn crm-btn-secondary crm-btn-sm"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', textDecoration: 'none' }}
                  >
                    <span>Pipeline</span>
                    <ExternalLink size={11} />
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Company / Account Card */}
          {(() => {
            const accountData = lead.account || (lead.accountId ? {
              id: lead.accountId,
              accountId: lead.account?.accountId || lead.accountId,
              name: lead.accountName || lead.account?.name || 'Associated Account',
              siteName: lead.account?.siteName || lead.siteName,
              industry: lead.account?.industry || lead.industry,
              phone: lead.account?.phone || lead.businessPhone,
              email: lead.account?.email || lead.companyEmail,
              website: lead.account?.website || lead.websiteLink,
              address: lead.account?.address || lead.location
            } : (lead.companyName ? {
              id: null,
              accountId: null,
              name: lead.companyName,
              siteName: lead.siteName,
              industry: lead.industry,
              phone: lead.businessPhone,
              email: lead.companyEmail,
              website: lead.websiteLink,
              address: lead.location,
              isLeadOwned: true
            } : null));

            return (
              <div className="glass-panel" style={{ padding: '1.25rem' }}>
                <h4 style={{
                  margin: '0 0 0.85rem 0',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--text-primary)'
                }}>
                  <Building size={16} color="var(--accent-primary)" />
                  <span>Company / Account</span>
                </h4>

                {accountData ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.4rem' }}>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                          {accountData.name}
                        </div>
                        {accountData.isLeadOwned && (
                          <span style={{ fontSize: '0.72rem', background: '#fef3c7', color: '#b45309', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                            Lead Company (Unqualified)
                          </span>
                        )}
                      </div>
                      {accountData.accountId && (
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                          Account ID: <span style={{ fontWeight: 600, color: '#334155' }}>{accountData.accountId}</span>
                        </div>
                      )}
                    </div>

                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.55rem',
                      borderTop: '1px solid #f1f5f9',
                      paddingTop: '0.75rem',
                      marginTop: '0.25rem'
                    }}>
                      {/* Client Site Name */}
                      {accountData.siteName && (
                        <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                            <Building size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            Site Name:
                          </span>
                          <span style={{ color: '#0369a1', fontWeight: 600, wordBreak: 'break-word' }}>
                            {accountData.siteName}
                          </span>
                        </div>
                      )}

                      {/* Industry */}
                      {accountData.industry && (
                        <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                            <Briefcase size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            Industry:
                          </span>
                          <span style={{ color: '#1e293b', fontWeight: 500, wordBreak: 'break-word' }}>
                            {accountData.industry}
                          </span>
                        </div>
                      )}

                      {/* Website */}
                      <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                          <Globe size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          Website:
                        </span>
                        <div style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {accountData.website ? (
                            <a
                              href={accountData.website.startsWith('http') ? accountData.website : `https://${accountData.website}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                            >
                              <span>{accountData.website.replace(/^https?:\/\//i, '').replace(/\/$/, '')}</span>
                              <ExternalLink size={11} style={{ opacity: 0.7 }} />
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                          )}
                        </div>
                      </div>

                      {/* Primary Phone */}
                      <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                          <Phone size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          Phone:
                        </span>
                        <div style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {accountData.phone ? (
                            <a
                              href={`tel:${accountData.phone}`}
                              style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                            >
                              {accountData.phone}
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                          )}
                        </div>
                      </div>

                      {/* Email */}
                      <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                          <Mail size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          Email:
                        </span>
                        <div style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {accountData.email ? (
                            <a
                              href={`mailto:${accountData.email}`}
                              style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                            >
                              {accountData.email}
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                          )}
                        </div>
                      </div>

                      {/* Location / Address */}
                      {accountData.address && (
                        <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                            <MapPin size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            Location:
                          </span>
                          <span style={{ color: '#1e293b', fontWeight: 500, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {accountData.address}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic' }}>
                    No parent company account associated with this lead.
                  </div>
                )}
              </div>
            );
          })()}

          {/* Primary Contact Card */}
          {(() => {
            const leadPersonName = (lead.firstName || lead.lastName)
              ? `${lead.firstName || ''} ${lead.lastName || ''}`.trim()
              : (lead.contactName || null);

            const contactData = lead.contact || (lead.contactId ? {
              id: lead.contactId,
              contactId: lead.contact?.contactId || lead.contactId,
              name: lead.contactName || lead.contact?.name || 'Primary Contact',
              designation: lead.contact?.designation || lead.jobTitle,
              email: lead.contactEmail || lead.contact?.email,
              mobileNumber: lead.contactPhone || lead.contact?.mobileNumber || lead.mobilePhone,
              accountName: lead.contact?.accountName || lead.accountName
            } : (leadPersonName || lead.contactEmail || lead.mobilePhone ? {
              id: null,
              contactId: null,
              name: leadPersonName || 'Direct Contact',
              designation: lead.jobTitle,
              email: lead.contactEmail,
              mobileNumber: lead.mobilePhone,
              accountName: lead.companyName,
              isLeadOwned: true
            } : null));

            return (
              <div className="glass-panel" style={{ padding: '1.25rem' }}>
                <h4 style={{
                  margin: '0 0 0.85rem 0',
                  fontSize: '0.95rem',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--text-primary)'
                }}>
                  <User size={16} color="var(--accent-primary)" />
                  <span>Primary Contact</span>
                </h4>

                {contactData ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.4rem' }}>
                        <button
                          type="button"
                          onClick={() => setViewContactModal(contactData)}
                          style={{
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            fontSize: '1.1rem',
                            fontWeight: 700,
                            color: '#0f172a',
                            lineHeight: 1.3,
                            cursor: 'pointer',
                            textAlign: 'left',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.color = '#2563eb'}
                          onMouseLeave={(e) => e.currentTarget.style.color = '#0f172a'}
                          title="Click to view Contact details"
                        >
                          <span>{contactData.name}</span>
                          <ExternalLink size={13} style={{ opacity: 0.6 }} />
                        </button>
                        {contactData.isLeadOwned && (
                          <span style={{ fontSize: '0.72rem', background: '#dbeafe', color: '#1e40af', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                            Lead Contact (Unqualified)
                          </span>
                        )}
                      </div>
                      {contactData.designation && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500, marginTop: '0.15rem' }}>
                          {contactData.designation}
                        </div>
                      )}
                      {contactData.contactId && (
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                          Contact ID: <span style={{ fontWeight: 600, color: '#334155' }}>{contactData.contactId}</span>
                        </div>
                      )}
                    </div>

                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.55rem',
                      borderTop: '1px solid #f1f5f9',
                      paddingTop: '0.75rem',
                      marginTop: '0.25rem'
                    }}>
                      {/* Mobile Number */}
                      <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                          <Phone size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          Mobile:
                        </span>
                        <div style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {contactData.mobileNumber ? (
                            <a
                              href={`tel:${contactData.mobileNumber}`}
                              style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                            >
                              {contactData.mobileNumber}
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                          )}
                        </div>
                      </div>

                      {/* Email */}
                      <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                          <Mail size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          Email:
                        </span>
                        <div style={{ minWidth: 0, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                          {contactData.email ? (
                            <a
                              href={`mailto:${contactData.email}`}
                              style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                              onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                              onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                            >
                              {contactData.email}
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                          )}
                        </div>
                      </div>

                      {/* Associated Account */}
                      {contactData.accountName && (
                        <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                            <Building size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            Account:
                          </span>
                          <span style={{ color: '#1e293b', fontWeight: 500, wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                            {contactData.accountName}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--danger)', fontSize: '0.85rem' }}>
                    No contact specified.
                  </div>
                )}
              </div>
            );
          })()}

          {/* Additional / Related Contacts Card */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <h4 style={{
              margin: '0 0 0.85rem 0',
              fontSize: '0.95rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: 'var(--text-primary)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <User size={16} color="#0284c7" />
                <span>Additional Contacts ({lead.additionalContacts ? lead.additionalContacts.length : 0})</span>
              </div>
            </h4>

            {lead.additionalContacts && lead.additionalContacts.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {lead.additionalContacts.map((c, idx) => (
                  <div
                    key={c.id || idx}
                    style={{
                      padding: '0.75rem',
                      background: '#f8fafc',
                      borderRadius: '8px',
                      border: '1px solid #e2e8f0',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.35rem'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <button
                        type="button"
                        onClick={() => setViewContactModal(c)}
                        style={{
                          background: 'none',
                          border: 'none',
                          padding: 0,
                          color: '#2563eb',
                          fontWeight: 600,
                          fontSize: '0.92rem',
                          cursor: 'pointer',
                          textAlign: 'left',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem'
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.textDecoration = 'underline'}
                        onMouseLeave={(e) => e.currentTarget.style.textDecoration = 'none'}
                        title="Click to view Contact details"
                      >
                        <span>{c.name}</span>
                        <ExternalLink size={12} />
                      </button>
                      {c.contactId && (
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {c.contactId}
                        </span>
                      )}
                    </div>
                    {c.designation && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {c.designation}
                      </div>
                    )}
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                      {c.email && (
                        <a
                          href={`mailto:${c.email}`}
                          style={{ color: 'var(--text-secondary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <Mail size={11} /> {c.email}
                        </a>
                      )}
                      {c.mobileNumber && (
                        <a
                          href={`tel:${c.mobileNumber}`}
                          style={{ color: 'var(--text-secondary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <Phone size={11} /> {c.mobileNumber}
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic' }}>
                No additional contacts attached to this lead.
              </div>
            )}
          </div>

          {/* Ownership & Metadata Card */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <h4 style={{ margin: '0 0 0.85rem 0', fontSize: '0.95rem', fontWeight: 600 }}>
              Lead Governance & Timeline
            </h4>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Assigned Owner: </span>
                <strong>
                  {lead.assignedTo?.name || lead.assignedTo?.username || lead.assignedToName || 'Unassigned (General Pool)'}
                </strong>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Lead Source: </span>
                <span style={{ fontWeight: 600 }}>{lead.leadSource || 'Website'}</span>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Initial Channel: </span>
                <span style={{ fontWeight: 600 }}>{lead.communicationChannel || 'Email'}</span>
              </div>

              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '0.6rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Connected Date: </span>
                <div style={{ fontWeight: 600, color: lead.connectedDate ? '#0f172a' : 'var(--text-muted)', marginTop: '2px' }}>
                  {lead.connectedDate ? formatDateOnly(lead.connectedDate) : 'Not specified'}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Last Connected Date: </span>
                <div style={{ fontWeight: 600, color: lead.lastConnectedDate ? '#0f172a' : 'var(--text-muted)', marginTop: '2px' }}>
                  {formatDateTime(lead.lastConnectedDate)}
                </div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Created By: </span>
                <div>{lead.createdBy?.name || lead.createdBy?.username || lead.createdByName || 'Portal User'}</div>
              </div>

              <div>
                <span style={{ color: 'var(--text-muted)' }}>Last Updated: </span>
                <div>{formatDateTime(lead.updatedAt)}</div>
              </div>
            </div>
          </div>
        </div>
      </div>


      {/* Status Transition Modal */}
      {isStatusModalOpen && (
        <LeadStatusModal
          isOpen={isStatusModalOpen}
          onClose={() => setIsStatusModalOpen(false)}
          lead={lead}
          onStatusUpdated={() => fetchLeadDetails()}
        />
      )}

      {/* Communication Modal */}
      {isCommModalOpen && (
        <CommunicationModal
          isOpen={isCommModalOpen}
          onClose={() => setIsCommModalOpen(false)}
          leadId={lead.id}
          leadName={lead.leadName}
          onCommunicationLogged={() => fetchLeadDetails()}
        />
      )}

      {/* Complete Nurturing Activity Modal */}
      {completeActivityModal && (
        <CompleteActivityModal
          isOpen={Boolean(completeActivityModal)}
          onClose={() => setCompleteActivityModal(null)}
          activity={completeActivityModal}
          lead={lead}
          onActivityCompleted={() => fetchLeadDetails()}
        />
      )}

      {/* Reschedule or Skip Activity Modal */}
      {actionActivityModal && (
        <ActivityActionModal
          isOpen={Boolean(actionActivityModal)}
          onClose={() => setActionActivityModal(null)}
          activity={actionActivityModal.activity}
          actionType={actionActivityModal.actionType}
          lead={lead}
          onActionSuccess={() => fetchLeadDetails()}
        />
      )}

      {/* Record Customer Response Modal */}
      {isCustomerResponseModalOpen && (
        <CustomerResponseModal
          isOpen={isCustomerResponseModalOpen}
          onClose={() => setIsCustomerResponseModalOpen(false)}
          lead={lead}
          onResponseRecorded={() => fetchLeadDetails()}
        />
      )}

      {/* Contact Details View Modal / Panel */}
      {viewContactModal && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setViewContactModal(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '480px', width: '92%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: '#e0f2fe',
                  color: '#0284c7',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <User size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                    {viewContactModal.name}
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {viewContactModal.contactId ? `Contact ID: ${viewContactModal.contactId}` : 'Contact Details'}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewContactModal(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}
                title="Close"
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Designation</span>
                <span style={{ fontWeight: 500, color: '#1e293b' }}>
                  {viewContactModal.designation || 'Not specified'}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Email</span>
                <div>
                  {viewContactModal.email ? (
                    <a href={`mailto:${viewContactModal.email}`} style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>
                      {viewContactModal.email}
                    </a>
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Mobile</span>
                <div>
                  {viewContactModal.mobileNumber ? (
                    <a href={`tel:${viewContactModal.mobileNumber}`} style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>
                      {viewContactModal.mobileNumber}
                    </a>
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Not provided</span>
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '110px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Account</span>
                <span style={{ fontWeight: 500, color: '#1e293b' }}>
                  {viewContactModal.accountName || lead.accountName || lead.account?.name || 'Direct Contact / No Account'}
                </span>
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setViewContactModal(null)}
                style={{ padding: '0.45rem 1.1rem', fontSize: '0.85rem' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Opportunity Details View Modal */}
      {viewOpportunityModal && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setViewOpportunityModal(null)}>
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
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: 'var(--accent-light)',
                  color: 'var(--accent-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Briefcase size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                    {viewOpportunityModal.name || 'Opportunity Details'}
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Opportunity ID: <strong style={{ color: '#0f172a' }}>{viewOpportunityModal.opportunityId || viewOpportunityModal.id}</strong>
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewOpportunityModal(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}
                title="Close"
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Status</span>
                <div>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    background: viewOpportunityModal.status === 'Won' ? 'var(--success-bg)' : 'var(--accent-light)',
                    color: viewOpportunityModal.status === 'Won' ? 'var(--success)' : 'var(--accent-primary)'
                  }}>
                    {viewOpportunityModal.status || 'Open'}
                  </span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Estimated Value</span>
                <span style={{ fontWeight: 600, color: '#0f172a' }}>
                  {viewOpportunityModal.estimatedValue !== null && viewOpportunityModal.estimatedValue !== undefined ? (
                    `${viewOpportunityModal.currency || 'INR'} ${Number(viewOpportunityModal.estimatedValue).toLocaleString()}`
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400 }}>Not specified</span>
                  )}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Account</span>
                <div>
                  {viewOpportunityModal.accountName || lead.accountName || lead.account?.name ? (
                    <Link
                      to={`/crm/accounts?search=${encodeURIComponent(viewOpportunityModal.accountName || lead.accountName || lead.account?.name)}`}
                      style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <Building size={13} color="#d97706" />
                      <span>{viewOpportunityModal.accountName || lead.accountName || lead.account?.name}</span>
                      <ExternalLink size={11} />
                    </Link>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Primary Contact</span>
                <div>
                  {viewOpportunityModal.contactName || lead.contactName || lead.contact?.name ? (
                    <Link
                      to={`/crm/contacts?search=${encodeURIComponent(viewOpportunityModal.contactName || lead.contactName || lead.contact?.name)}`}
                      style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    >
                      <User size={13} />
                      <span>{viewOpportunityModal.contactName || lead.contactName || lead.contact?.name}</span>
                      <ExternalLink size={11} />
                    </Link>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>—</span>
                  )}
                </div>
              </div>

              {viewOpportunityModal.description && (
                <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Description</span>
                  <div style={{ color: 'var(--text-secondary)', background: '#f8fafc', padding: '0.5rem 0.75rem', borderRadius: '6px', border: '1px solid #f1f5f9', whiteSpace: 'pre-wrap' }}>
                    {viewOpportunityModal.description}
                  </div>
                </div>
              )}
            </div>

            <div style={{ marginTop: '1.5rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Link
                to="/crm/opportunities"
                style={{ color: 'var(--accent-primary)', fontSize: '0.85rem', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
              >
                <span>View in Opportunities Pipeline</span>
                <ExternalLink size={13} />
              </Link>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setViewOpportunityModal(null)}
                style={{ padding: '0.45rem 1.1rem', fontSize: '0.85rem' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Qualification Wizard */}
      {isQualifyWizardOpen && (
        <LeadQualifyWizard
          lead={lead}
          isOpen={isQualifyWizardOpen}
          onClose={() => setIsQualifyWizardOpen(false)}
          onQualifiedSuccess={(result) => {
            setIsQualifyWizardOpen(false);
            fetchLeadDetails();
            const oppCode = result?.opportunity?.opportunityId || result?.opportunity_id || '';
            const oppSuffix = oppCode ? ` into Opportunity ${oppCode}` : '';
            setSuccessNotification(`Lead ${lead.leadId || ''} successfully qualified${oppSuffix}!`);
            setTimeout(() => setSuccessNotification(null), 5000);
          }}
        />
      )}

      {/* Unqualify Lead Confirmation Modal */}
      {isUnqualifyModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => !submittingUnqualify && setIsUnqualifyModalOpen(false)}>
          <div
            className="modal-content"
            style={{
              maxWidth: '520px',
              width: '92%',
              borderRadius: '12px',
              padding: '1.75rem',
              background: '#ffffff',
              boxShadow: 'var(--modal-shadow)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: '#fef2f2',
                  color: '#ef4444',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <XCircle size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                    Unqualify Lead
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Lead: <strong>{lead.leadId}</strong>
                  </span>
                </div>
              </div>
              <button
                type="button"
                disabled={submittingUnqualify}
                onClick={() => setIsUnqualifyModalOpen(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}
                title="Close"
              >
                ✕
              </button>
            </div>

            <p style={{ margin: '0 0 1rem 0', color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.5 }}>
              Unqualifying this lead will set its lifecycle status to <strong>Dormant</strong> and record the disqualification reason in the timeline.
            </p>

            {unqualifyError && (
              <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.825rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={16} />
                <span>{unqualifyError}</span>
              </div>
            )}

            <form onSubmit={handleUnqualifyLead} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Disqualification Reason <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Enter the business reason for unqualifying this lead (e.g. Budget constraints, Not a fit for microbial bio-culture solutions, Project indefinitely deferred)..."
                  className="form-control"
                  value={disqualificationReason}
                  onChange={(e) => {
                    setDisqualificationReason(e.target.value);
                    if (unqualifyError) setUnqualifyError(null);
                  }}
                  style={{ width: '100%', resize: 'vertical' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9' }}>
                <button
                  type="button"
                  disabled={submittingUnqualify}
                  onClick={() => setIsUnqualifyModalOpen(false)}
                  className="btn btn-secondary"
                  style={{ padding: '0.45rem 1.1rem', fontSize: '0.85rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingUnqualify || !disqualificationReason.trim()}
                  className="btn btn-danger"
                  style={{
                    padding: '0.45rem 1.25rem',
                    fontSize: '0.85rem',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    background: '#ef4444',
                    borderColor: '#ef4444',
                    color: '#ffffff'
                  }}
                >
                  {submittingUnqualify ? (
                    <>
                      <RefreshCw size={14} className="spin" />
                      <span>Unqualifying...</span>
                    </>
                  ) : (
                    <span>Confirm Unqualify</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
