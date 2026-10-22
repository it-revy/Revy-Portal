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
  ChevronRight
} from 'lucide-react';
import crmService from '../services/crmService';
import LeadModal from '../modules/crm/components/LeadModal';
import LeadStatusModal from '../modules/crm/components/LeadStatusModal';
import CommunicationModal from '../modules/crm/components/CommunicationModal';

export default function CrmLeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  const [lead, setLead] = useState(null);
  const [communications, setCommunications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);

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
    if (s === 'open') badgeClass = 'status-badge open';
    else if (s === 'qualified') badgeClass = 'status-badge present';
    else if (s === 'disqualified') badgeClass = 'status-badge absent';

    return <span className={badgeClass}>{status}</span>;
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
          {canLogComm && (
            <button
              onClick={() => setIsCommModalOpen(true)}
              className="btn btn-primary"
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
              onClick={() => setIsEditModalOpen(true)}
              className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Edit size={14} />
              <span>Edit Details</span>
            </button>
          )}
        </div>
      </div>

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
          {/* Company / Account Card */}
          {(() => {
            const accountData = lead.account || (lead.accountId ? {
              id: lead.accountId,
              accountId: lead.account?.accountId || lead.accountId,
              name: lead.accountName || lead.account?.name || 'Associated Account',
              industry: lead.account?.industry,
              phone: lead.account?.phone,
              email: lead.account?.email,
              website: lead.account?.website,
              address: lead.account?.address
            } : null);

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
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                        {accountData.name}
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
            const contactData = lead.contact || (lead.contactId ? {
              id: lead.contactId,
              contactId: lead.contact?.contactId || lead.contactId,
              name: lead.contactName || lead.contact?.name || 'Primary Contact',
              designation: lead.contact?.designation,
              email: lead.contactEmail || lead.contact?.email,
              mobileNumber: lead.contactPhone || lead.contact?.mobileNumber,
              accountName: lead.contact?.accountName || lead.accountName
            } : null);

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
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                        {contactData.name}
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

      {/* Edit Modal */}
      {isEditModalOpen && (
        <LeadModal
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onLeadSaved={() => fetchLeadDetails()}
          leadToEdit={lead}
        />
      )}

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
    </div>
  );
}
