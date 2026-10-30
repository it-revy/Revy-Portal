import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeft,
  Building,
  User,
  Layers,
  Calendar,
  Clock,
  Phone,
  Mail,
  MapPin,
  Globe,
  Edit,
  RefreshCw,
  Plus,
  MessageSquare,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Briefcase,
  ExternalLink,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import crmService from '../services/crmService';
import LeadStatusModal from '../modules/crm/components/LeadStatusModal';
import CommunicationModal from '../modules/crm/components/CommunicationModal';
import LeadQualifyWizard from '../modules/crm/components/LeadQualifyWizard';
import OpportunityDetailModal from '../modules/crm/components/OpportunityDetailModal';

export default function CrmLeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  const [lead, setLead] = useState(null);
  const [communications, setCommunications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successNotification, setSuccessNotification] = useState(null);
  const [warningNotification, setWarningNotification] = useState(null);

  // Modals
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);
  const [isQualifyWizardOpen, setIsQualifyWizardOpen] = useState(false);
  const [viewContactModal, setViewContactModal] = useState(null);
  const [viewOpportunityModal, setViewOpportunityModal] = useState(null);
  const [selectedOppIdForDetail, setSelectedOppIdForDetail] = useState(null);

  // Add Opportunity Modal State
  const [isAddOppModalOpen, setIsAddOppModalOpen] = useState(false);
  const [newOppFormData, setNewOppFormData] = useState({
    name: '',
    estimatedValue: '',
    stage: 'Qualify',
    businessArea: 'Biogas',
    subStatus: '',
    description: '',
    expectedCloseDate: ''
  });
  const [submittingOpp, setSubmittingOpp] = useState(false);
  const [addOppError, setAddOppError] = useState(null);

  const canEdit = hasPermission('crm.lead.edit');
  const canUpdateStatus = hasPermission('crm.lead.status.update');
  const canLogComm = hasPermission('crm.communication.create') || hasPermission('crm.lead.edit');

  const fetchLeadDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [leadRes, commsRes] = await Promise.all([
        crmService.getLeadById(id),
        crmService.getLeadCommunications(id)
      ]);

      if (leadRes.data.success) {
        setLead(leadRes.data.lead);
      }
      if (commsRes.data.success) {
        setCommunications(commsRes.data.communications || []);
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`Lead with identifier "${id}" not found.`);
      } else {
        setError(err.response?.data?.message || 'Failed to load lead details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchLeadDetails();
  }, [fetchLeadDetails]);



  const formatDateTime = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return isoStr;
    }
  };

  const formatDateOnly = (dateStr) => {
    if (!dateStr) return 'Not scheduled';
    try {
      const cleanDate = dateStr.slice(0, 10);
      const [year, month, day] = cleanDate.split('-').map(Number);
      if (!year || !month || !day) return dateStr;
      const d = new Date(year, month - 1, day);
      return d.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    let badgeClass = 'status-badge';
    if (s === 'enquiry' || s === 'open') badgeClass = 'status-badge open';
    else if (s === 'offer') badgeClass = 'status-badge info';
    else if (s === 'negotiation' || s === 'qualified') badgeClass = 'status-badge in-progress';
    else if (s === 'supply') badgeClass = 'status-badge present';
    else if (s === 'payment') badgeClass = 'status-badge late';
    else if (s === 'dormant' || s === 'disqualified') badgeClass = 'status-badge absent';

    return <span className={badgeClass}>{status}</span>;
  };

  const handleCreateOpportunity = async (e) => {
    e.preventDefault();
    if (!newOppFormData.name.trim()) {
      setAddOppError('Opportunity name is required.');
      return;
    }
    setSubmittingOpp(true);
    setAddOppError(null);
    try {
      const payload = {
        name: newOppFormData.name.trim(),
        estimatedValue: newOppFormData.estimatedValue ? Number(newOppFormData.estimatedValue) : null,
        stage: newOppFormData.stage || 'Qualify',
        businessArea: newOppFormData.businessArea || null,
        subStatus: newOppFormData.subStatus ? newOppFormData.subStatus.trim() : null,
        description: newOppFormData.description ? newOppFormData.description.trim() : null,
        expectedCloseDate: newOppFormData.expectedCloseDate || null
      };
      const res = await crmService.createLeadOpportunity(lead.id, payload);
      if (res.data?.success) {
        setIsAddOppModalOpen(false);
        setNewOppFormData({
          name: '',
          estimatedValue: '',
          stage: 'Qualify',
          businessArea: 'Biogas',
          subStatus: '',
          description: '',
          expectedCloseDate: ''
        });
        setSuccessNotification('New Commercial Opportunity created and linked successfully.');
        fetchLeadDetails();
      }
    } catch (err) {
      setAddOppError(err.response?.data?.message || 'Failed to create opportunity.');
    } finally {
      setSubmittingOpp(false);
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
          <button onClick={() => navigate('/crm/leads')} className="btn btn-primary">
            ← Return to Leads
          </button>
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
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={() => navigate('/crm/leads')}
            className="btn btn-secondary"
            style={{ padding: '0.4rem 0.65rem' }}
            title="Back to Leads Workspace"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--accent-primary)', background: '#eff6ff', padding: '2px 8px', borderRadius: '4px' }}>
                {lead.leadId}
              </span>
              <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700 }}>
                {lead.leadName || lead.displayName || lead.leadId}
              </h1>
              {getStatusBadge(lead.lifecycleStatus)}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Created on {formatDateTime(lead.createdAt)}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          {(!lead.isQualified && !lead.qualifiedAt && lead.lifecycleStatus !== 'Qualified') && (canEdit || canUpdateStatus) && (
            <button
              onClick={() => setIsQualifyWizardOpen(true)}
              className="btn btn-primary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: 'var(--success)',
                borderColor: 'var(--success)',
                color: '#ffffff',
                fontWeight: 600
              }}
            >
              <ShieldCheck size={16} />
              <span>Qualify Lead</span>
            </button>
          )}

          {canEdit && (
            <button
              onClick={() => setIsAddOppModalOpen(true)}
              className="btn btn-primary"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: 'var(--accent-primary)',
                borderColor: 'var(--accent-primary)',
                color: '#ffffff',
                fontWeight: 600
              }}
            >
              <Plus size={15} />
              <span>Add Opportunity</span>
            </button>
          )}

          {canLogComm && (
            <button
              onClick={() => setIsCommModalOpen(true)}
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Plus size={15} />
              <span>Log Interaction</span>
            </button>
          )}

          {canUpdateStatus && (
            <button
              onClick={() => setIsStatusModalOpen(true)}
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <RefreshCw size={14} />
              <span>Change Status</span>
            </button>
          )}

          {canEdit && (
            <button
              onClick={() => navigate(`/crm/leads/${lead.id}/edit`)}
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Edit size={14} />
              <span>Edit Details</span>
            </button>
          )}
        </div>
      </div>

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
                    ? `Lead qualified on ${lead.qualifiedAt ? new Date(lead.qualifiedAt).toLocaleDateString() : '—'}${lead.qualifiedByName ? ` by ${lead.qualifiedByName}` : ''}.`
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
              {canEdit && (
                <button
                  type="button"
                  onClick={() => setIsAddOppModalOpen(true)}
                  className="btn btn-primary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <Plus size={14} />
                  <span>Add Opportunity</span>
                </button>
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
                      <td style={{ fontWeight: 700, color: 'var(--accent-primary)', whiteSpace: 'nowrap' }}>
                        <button
                          type="button"
                          onClick={() => setSelectedOppIdForDetail(opp.id)}
                          style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', fontWeight: 700, cursor: 'pointer', padding: 0 }}
                        >
                          {opp.opportunityId || opp.id}
                        </button>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        <button
                          type="button"
                          onClick={() => setSelectedOppIdForDetail(opp.id)}
                          style={{ background: 'none', border: 'none', textAlign: 'left', font: 'inherit', fontWeight: 600, cursor: 'pointer', padding: 0, color: 'var(--text-primary)' }}
                        >
                          {opp.name}
                        </button>
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
                        <button
                          type="button"
                          onClick={() => setSelectedOppIdForDetail(opp.id)}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No commercial opportunities created yet. Click "+ Add Opportunity" to record a commercial requirement.
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

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.25rem' }}>
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

              <div>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Requirement Types
                </label>
                <div style={{ marginTop: '0.2rem', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {(lead.requirementTypes && lead.requirementTypes.length > 0 ? lead.requirementTypes : [lead.requirementType || 'Consulting']).map((type, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.825rem',
                        fontWeight: 600,
                        background: '#f1f5f9',
                        color: '#334155',
                        border: '1px solid #cbd5e1'
                      }}
                    >
                      {type}
                    </span>
                  ))}
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

              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Rating</label>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '2px' }}>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    background: lead.rating === 'Hot' ? '#fef2f2' : lead.rating === 'Warm' ? '#fffbeb' : '#f0fdf4',
                    color: lead.rating === 'Hot' ? '#b91c1c' : lead.rating === 'Warm' ? '#b45309' : '#15803d'
                  }}>
                    {lead.rating || 'Warm'}
                  </span>
                </div>
              </div>

              {lead.currency && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Currency</label>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{lead.currency}</div>
                </div>
              )}

              {lead.numberOfEmployees !== undefined && lead.numberOfEmployees !== null && (
                <div>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Employees</label>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{lead.numberOfEmployees}</div>
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

          {/* Chronological Communication History Timeline */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <MessageSquare size={18} color="var(--accent-primary)" />
                <span>Communication History ({communications.length})</span>
              </h3>

              {canLogComm && (
                <button
                  onClick={() => setIsCommModalOpen(true)}
                  className="btn btn-secondary"
                  style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                >
                  <Plus size={13} />
                  <span>Log Interaction</span>
                </button>
              )}
            </div>

            {communications.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                <MessageSquare size={32} color="#cbd5e1" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <p style={{ margin: 0, fontSize: '0.875rem' }}>No communication events recorded yet.</p>
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem' }}>
                  Log client calls, introductory emails, or internal discussions to build a complete customer interaction audit trail.
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {communications.map(item => (
                  <div
                    key={item.id}
                    style={{
                      padding: '1rem',
                      background: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.4rem',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: '#eff6ff',
                          color: '#1d4ed8'
                        }}>
                          {item.channel}
                        </span>
                        <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>
                          {item.eventType}
                        </strong>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatDateTime(item.communicationDate || item.createdAt)}
                      </span>
                    </div>

                    <p style={{ margin: '0.35rem 0 0 0', fontSize: '0.875rem', color: '#334155', lineHeight: 1.5 }}>
                      {item.summary}
                    </p>

                    {(item.outcome || item.nextAction) && (
                      <div style={{
                        marginTop: '0.4rem',
                        padding: '0.5rem 0.75rem',
                        background: '#f8fafc',
                        borderRadius: '6px',
                        fontSize: '0.8rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.25rem'
                      }}>
                        {item.outcome && (
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Outcome: </span>
                            <span>{item.outcome}</span>
                          </div>
                        )}
                        {item.nextAction && (
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Next Action: </span>
                            <span>{item.nextAction}</span>
                            {item.followUpDate && (
                              <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                                (Follow-up: {formatDateTime(item.followUpDate)})
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      Logged by <strong>{item.loggedBy?.name || item.loggedBy?.username || 'System User'}</strong> • ID: {item.communicationId}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
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
          onQualifiedSuccess={() => {
            fetchLeadDetails();
          }}
        />
      )}

      {/* Comprehensive Opportunity Detail & Workstream Modal */}
      {selectedOppIdForDetail && (
        <OpportunityDetailModal
          isOpen={Boolean(selectedOppIdForDetail)}
          opportunityId={selectedOppIdForDetail}
          onClose={() => setSelectedOppIdForDetail(null)}
          onOpportunityUpdated={() => fetchLeadDetails()}
        />
      )}

      {/* Add Commercial Opportunity Modal (1:N) */}
      {isAddOppModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => !submittingOpp && setIsAddOppModalOpen(false)}>
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
                    Add Commercial Opportunity
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Link a new requirement or proposal to Lead: <strong>{lead.leadId}</strong>
                  </span>
                </div>
              </div>
              <button
                type="button"
                disabled={submittingOpp}
                onClick={() => setIsAddOppModalOpen(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: '#94a3b8', cursor: 'pointer', lineHeight: 1 }}
                title="Close"
              >
                ✕
              </button>
            </div>

            {addOppError && (
              <div style={{ padding: '0.75rem 1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', color: '#b91c1c', fontSize: '0.825rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={16} />
                <span>{addOppError}</span>
              </div>
            )}

            <form onSubmit={handleCreateOpportunity} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Opportunity Name <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Wastewater Biogas Trial 2026, Annual Testing Batch"
                  className="form-control"
                  value={newOppFormData.name}
                  onChange={(e) => setNewOppFormData({ ...newOppFormData, name: e.target.value })}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    Estimated Value (INR)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    placeholder="e.g. 250000"
                    className="form-control"
                    value={newOppFormData.estimatedValue}
                    onChange={(e) => setNewOppFormData({ ...newOppFormData, estimatedValue: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    Pipeline Stage
                  </label>
                  <select
                    className="form-control"
                    value={newOppFormData.stage}
                    onChange={(e) => setNewOppFormData({ ...newOppFormData, stage: e.target.value })}
                  >
                    <option value="Qualify">Qualify</option>
                    <option value="Develop">Develop</option>
                    <option value="Propose">Propose</option>
                    <option value="Close">Close</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    Business Area
                  </label>
                  <select
                    className="form-control"
                    value={newOppFormData.businessArea}
                    onChange={(e) => setNewOppFormData({ ...newOppFormData, businessArea: e.target.value })}
                  >
                    <option value="Biogas">Biogas</option>
                    <option value="Wastewater Treatment (WWT)">Wastewater Treatment (WWT)</option>
                    <option value="R&D Lab">R&D Lab</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    Expected Close Date
                  </label>
                  <input
                    type="date"
                    className="form-control"
                    value={newOppFormData.expectedCloseDate}
                    onChange={(e) => setNewOppFormData({ ...newOppFormData, expectedCloseDate: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Operational Sub-status (Free Text)
                </label>
                <input
                  type="text"
                  maxLength={255}
                  placeholder="e.g. Waiting for revised quotation, Sample collection to be scheduled..."
                  className="form-control"
                  value={newOppFormData.subStatus}
                  onChange={(e) => setNewOppFormData({ ...newOppFormData, subStatus: e.target.value })}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Unrestricted free-text operational progress note.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                  Scope & Requirements Description
                </label>
                <textarea
                  rows={3}
                  placeholder="Commercial scope details, deliverables, assumptions..."
                  className="form-control"
                  value={newOppFormData.description}
                  onChange={(e) => setNewOppFormData({ ...newOppFormData, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9' }}>
                <button
                  type="button"
                  disabled={submittingOpp}
                  onClick={() => setIsAddOppModalOpen(false)}
                  className="btn btn-secondary"
                  style={{ padding: '0.45rem 1.1rem', fontSize: '0.85rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingOpp}
                  className="btn btn-primary"
                  style={{ padding: '0.45rem 1.25rem', fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  {submittingOpp ? (
                    <>
                      <RefreshCw size={14} className="spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Opportunity</span>
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
