import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Briefcase,
  Building,
  User,
  Layers,
  ExternalLink,
  Edit,
  CheckCircle2,
  Clock,
  AlertCircle,
  Plus,
  RefreshCw,
  FileText,
  Calendar,
  DollarSign,
  Tag,
  Mail,
  Phone,
  Globe,
  MapPin,
  FileDown,
  ArrowLeft,
  Copy,
  Receipt,
  MessageSquare,
  ShieldCheck,
  Check,
  XCircle,
  FileSpreadsheet
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import crmService from '../services/crmService';
import invoiceService from '../services/invoiceService';
import QuotationManagerModal from '../components/crm/QuotationManagerModal';
import InvoicePreparationModal from '../components/crm/InvoicePreparationModal';
import QuotationCatalogueSelector from '../components/crm/QuotationCatalogueSelector';
import { PageHeader, Button } from '../components/ui';

const BUSINESS_AREAS = ['Biogas', 'Wastewater Treatment (WWT)', 'R&D Lab', 'Other'];
const APPROVED_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD'];

export default function CrmOpportunityDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [warningMsg, setWarningMsg] = useState(null);

  // Modals state
  const [isStageModalOpen, setIsStageModalOpen] = useState(false);
  const [quotationModalOpen, setQuotationModalOpen] = useState(false);
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false);
  const [isCommModalOpen, setIsCommModalOpen] = useState(false);

  // Edit Opportunity Overview State
  const [isEditing, setIsEditing] = useState(false);
  const [savingOverview, setSavingOverview] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '',
    currency: 'INR',
    estimatedValue: '',
    expectedCloseDate: '',
    businessArea: '',
    description: '',
    subStatus: '',
    requirementTypes: []
  });

  // Quotations and Invoicing State
  const [activeQuotation, setActiveQuotation] = useState(null);
  const [proformaInvoices, setProformaInvoices] = useState([]);
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [copyingText, setCopyingText] = useState(false);

  // Interaction History State
  const [communications, setCommunications] = useState([]);
  const [loadingComms, setLoadingComms] = useState(false);
  const [commChannelFilter, setCommChannelFilter] = useState('ALL');
  const [submittingComm, setSubmittingComm] = useState(false);
  const [commFormData, setCommFormData] = useState({
    communicationChannel: 'PHONE',
    communicationDate: new Date().toISOString().slice(0, 16),
    subject: '',
    summary: '',
    outcome: 'Follow-up Required',
    nextFollowUpDate: ''
  });

  const userRoles = [
    ...(user?.roles || []),
    user?.role,
    user?.user_metadata?.role
  ].filter(Boolean).map(r => String(r).toUpperCase());

  const isCrmAdminOrManager = userRoles.some(r =>
    ['CRM_ADMIN', 'CRM_MANAGER', 'ADMIN', 'SUPERADMIN', 'DIRECTOR', 'IT_ADMIN'].includes(r)
  );

  const canEdit = hasPermission('crm.opportunity.edit') || hasPermission('crm.lead.edit');
  const canChangeStage = hasPermission('crm.opportunity.edit') || hasPermission('crm.stage.update');

  // Format calendar date
  const formatDateOnly = (dateStr) => {
    if (!dateStr) return '—';
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

  // Format ISO timestamp to readable date-time
  const formatDateTime = (isoStr) => {
    if (!isoStr) return '—';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
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

  // Fetch Opportunity Details
  const fetchOpportunityDetails = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await crmService.getOpportunityById(id);
      const opp = res.data?.opportunity || res.data;
      if (opp) {
        setOpportunity(opp);
        setEditFormData({
          name: opp.name || '',
          currency: opp.currency || 'INR',
          estimatedValue: opp.estimatedValue != null ? String(opp.estimatedValue) : '',
          expectedCloseDate: opp.expectedCloseDate ? opp.expectedCloseDate.slice(0, 10) : '',
          businessArea: opp.businessArea || 'Biogas',
          description: opp.description || opp.requirementSummary || '',
          subStatus: opp.subStatus || '',
          requirementTypes: opp.requirementTypes || []
        });
      }
    } catch (err) {
      console.error('Failed to load opportunity:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load opportunity details.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Fetch Current Quotation and Proforma Invoices
  const fetchQuotationAndInvoices = useCallback(async () => {
    if (!id) return;
    try {
      // 1. Current Quotation
      const quoteRes = await invoiceService.getCurrentQuotation(id);
      if (quoteRes.data?.success) {
        setActiveQuotation(quoteRes.data.quotation || null);
      }

      // 2. Proforma Invoices
      const piRes = await invoiceService.getOpportunityProformaInvoices(id);
      if (piRes.data?.success) {
        setProformaInvoices(piRes.data.proformaInvoices || []);
      }
    } catch (err) {
      console.warn('Failed to load quotation/PI data:', err);
    }
  }, [id]);

  // Fetch Communications (both Opportunity and linked Lead history)
  const fetchCommunications = useCallback(async () => {
    if (!id) return;
    setLoadingComms(true);
    try {
      const oppCommsRes = await crmService.getOpportunityCommunications(id);
      let oppComms = oppCommsRes.data?.communications || [];

      // If opportunity originated from a lead, also fetch lead communications for unified timeline
      if (opportunity?.originatingLead?.id || opportunity?.originatingLeadId) {
        const leadId = opportunity.originatingLead?.id || opportunity.originatingLeadId;
        try {
          const leadCommsRes = await crmService.getLeadCommunications(leadId);
          const leadComms = (leadCommsRes.data?.communications || []).map(c => ({
            ...c,
            isLeadHistory: true
          }));
          oppComms = [...oppComms, ...leadComms];
        } catch (leadErr) {
          console.warn('Failed to load originating lead comms:', leadErr);
        }
      }

      // Sort chronological descending
      oppComms.sort((a, b) => new Date(b.communicationDate || b.createdAt) - new Date(a.communicationDate || a.createdAt));
      setCommunications(oppComms);
    } catch (err) {
      console.error('Failed to load communications:', err);
    } finally {
      setLoadingComms(false);
    }
  }, [id, opportunity]);

  useEffect(() => {
    fetchOpportunityDetails();
  }, [fetchOpportunityDetails]);

  // Stage History state & fetcher
  const [stageHistory, setStageHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchStageHistory = useCallback(async () => {
    if (!id) return;
    setLoadingHistory(true);
    try {
      const res = await crmService.getOpportunityStageHistory(id);
      if (res.data?.success) {
        setStageHistory(res.data.history || []);
      }
    } catch (err) {
      console.error('Failed to load stage history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, [id]);

  useEffect(() => {
    if (opportunity?.id) {
      fetchQuotationAndInvoices();
      fetchCommunications();
      fetchStageHistory();
    }
  }, [opportunity?.id, fetchQuotationAndInvoices, fetchCommunications, fetchStageHistory]);

  // Automated Stage Transition Business Handlers
  const handleConfirmOrder = async () => {
    const notes = window.prompt('Enter work execution / order confirmation details:', 'Order confirmed and execution initiated');
    if (!notes) return;
    try {
      const res = await crmService.confirmOpportunityOrder(id, { workExecutionNotes: notes });
      if (res.data?.success) {
        setSuccessMsg('Order confirmed! Opportunity stage advanced to Supply.');
        setTimeout(() => setSuccessMsg(null), 4000);
        fetchOpportunityDetails();
        fetchStageHistory();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to confirm order.');
    }
  };

  const handleTrackPayment = async () => {
    const ref = window.prompt('Enter payment tracking reference / notes:', 'Payment tracking initiated');
    if (!ref) return;
    try {
      const res = await crmService.trackOpportunityPayment(id, { paymentReference: ref });
      if (res.data?.success) {
        setSuccessMsg('Payment tracking started! Opportunity stage advanced to Payment.');
        setTimeout(() => setSuccessMsg(null), 4000);
        fetchOpportunityDetails();
        fetchStageHistory();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to start payment tracking.');
    }
  };

  const handleMarkDormant = async () => {
    const reason = window.prompt('Enter reason for marking opportunity dormant / on hold:', 'Client delayed project decision');
    if (!reason) return;
    try {
      const res = await crmService.markOpportunityDormant(id, { dormantReason: reason });
      if (res.data?.success) {
        setSuccessMsg('Opportunity moved to Dormant stage.');
        setTimeout(() => setSuccessMsg(null), 4000);
        fetchOpportunityDetails();
        fetchStageHistory();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to mark opportunity dormant.');
    }
  };

  const handleReactivate = async () => {
    if (!window.confirm('Reactivate this dormant opportunity back to Enquiry stage?')) return;
    try {
      const res = await crmService.reactivateOpportunity(id);
      if (res.data?.success) {
        setSuccessMsg('Opportunity reactivated to Enquiry stage.');
        setTimeout(() => setSuccessMsg(null), 4000);
        fetchOpportunityDetails();
        fetchStageHistory();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reactivate opportunity.');
    }
  };

  // Handle Save Overview
  const handleSaveOverview = async (e) => {
    e.preventDefault();
    setSavingOverview(true);
    setError(null);
    try {
      await crmService.updateOpportunity(id, {
        name: editFormData.name.trim(),
        currency: editFormData.currency,
        estimatedValue: editFormData.estimatedValue ? Number(editFormData.estimatedValue) : null,
        expectedCloseDate: editFormData.expectedCloseDate || null,
        businessArea: editFormData.businessArea,
        description: editFormData.description.trim(),
        subStatus: editFormData.subStatus ? editFormData.subStatus.trim() : null
      });
      setIsEditing(false);
      setSuccessMsg('Opportunity overview updated successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update opportunity overview.');
    } finally {
      setSavingOverview(false);
    }
  };

  // Handle Log Interaction Submit
  const handleLogInteraction = async (e) => {
    e.preventDefault();
    if (!commFormData.summary.trim()) {
      alert('Interaction notes / description is required.');
      return;
    }
    setSubmittingComm(true);
    try {
      await crmService.addOpportunityCommunication(id, {
        communicationChannel: commFormData.communicationChannel,
        communicationDate: commFormData.communicationDate ? new Date(commFormData.communicationDate).toISOString() : new Date().toISOString(),
        subject: commFormData.subject.trim() || undefined,
        summary: commFormData.summary.trim(),
        outcome: commFormData.outcome || undefined,
        nextFollowUpDate: commFormData.nextFollowUpDate ? new Date(commFormData.nextFollowUpDate).toISOString() : undefined
      });
      setIsCommModalOpen(false);
      setCommFormData({
        communicationChannel: 'PHONE',
        communicationDate: new Date().toISOString().slice(0, 16),
        subject: '',
        summary: '',
        outcome: 'Follow-up Required',
        nextFollowUpDate: ''
      });
      setSuccessMsg('Interaction logged successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
      fetchCommunications();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to log interaction.');
    } finally {
      setSubmittingComm(false);
    }
  };

  // Handle Copy Quotation Text
  const handleCopyQuotationText = async () => {
    if (!activeQuotation?.id) return;
    setCopyingText(true);
    try {
      const res = await invoiceService.getQuotationEmailText(activeQuotation.id);
      const text = res.data?.emailText || '';
      if (text) {
        await navigator.clipboard.writeText(text);
        setSuccessMsg('Quotation text copied to clipboard! Ready to paste into Email or WhatsApp.');
        setTimeout(() => setSuccessMsg(null), 4000);
      } else {
        alert('No formatted quotation text returned.');
      }
    } catch (err) {
      alert('Failed to copy quotation text: ' + (err.response?.data?.message || err.message));
    } finally {
      setCopyingText(false);
    }
  };

  // Stage Badge helper
  const getStageBadgeStyle = (stage) => {
    switch (stage) {
      case 'Enquiry':
        return { background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' };
      case 'Offer':
        return { background: '#ede9fe', color: '#6d28d9', border: '1px solid #ddd6fe' };
      case 'Negotiation':
        return { background: '#fef3c7', color: '#b45309', border: '1px solid #fde68a' };
      case 'Supply':
        return { background: '#ecfeff', color: '#0e7490', border: '1px solid #a5f3fc' };
      case 'Payment':
        return { background: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0' };
      case 'Dormant':
        return { background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1' };
      default:
        return { background: '#f8fafc', color: '#334155', border: '1px solid #e2e8f0' };
    }
  };

  // Filtered Communications
  const filteredCommunications = communications.filter(comm => {
    if (commChannelFilter === 'ALL') return true;
    return comm.communicationChannel === commChannelFilter;
  });

  if (loading) {
    return (
      <div className="page-body" style={{ textAlign: 'center', padding: '5rem 0', color: 'var(--text-secondary)' }}>
        <RefreshCw size={28} className="spin" style={{ margin: '0 auto 1rem', display: 'block', color: 'var(--accent-primary)' }} />
        Loading opportunity details and commercial records...
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', maxWidth: '540px', margin: '3rem auto' }}>
          <AlertCircle size={40} color="var(--danger)" style={{ margin: '0 auto 1rem', display: 'block' }} />
          <h2 style={{ marginBottom: '0.75rem', color: 'var(--danger)' }}>Unable to View Opportunity</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error || 'Opportunity not found.'}</p>
          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            <button
              onClick={() => fetchOpportunityDetails()}
              className="btn btn-primary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <RefreshCw size={15} /> Try Again
            </button>
            <button onClick={() => navigate('/crm/opportunities')} className="btn btn-secondary">
              ← Return to Opportunities
            </button>
          </div>
        </div>
      </div>
    );
  }

  const stageStyle = getStageBadgeStyle(opportunity.stage);

  return (
    <div className="page-body">
      {/* Success Notification Banner */}
      {successMsg && (
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
            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#065f46', fontSize: '1.2rem', lineHeight: 1 }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* Warning Notification Banner */}
      {warningMsg && (
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
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} style={{ color: '#d97706', flexShrink: 0 }} />
            <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>{warningMsg}</span>
          </div>
          <button
            onClick={() => setWarningMsg(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontSize: '1.2rem', lineHeight: 1 }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}

      {/* A. Opportunity Header */}
      <PageHeader
        title={opportunity.name}
        subtitle={`Opportunity ID: ${opportunity.opportunityId || opportunity.id} • Created on ${formatDateTime(opportunity.createdAt)}`}
        breadcrumbs={[
          { label: 'CRM', to: '/crm/dashboard' },
          { label: 'Opportunities', to: '/crm/opportunities' },
          { label: opportunity.opportunityId || opportunity.id }
        ]}
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            {/* Sales Stage Badge */}
            <span
              style={{
                ...stageStyle,
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.825rem',
                fontWeight: 700,
                letterSpacing: '0.02em',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              Stage: {opportunity.stage || 'Enquiry'}
            </span>

            {/* Status Badge */}
            <span
              className={`status-badge ${
                opportunity.status === 'Won'
                  ? 'success'
                  : opportunity.status === 'Lost'
                  ? 'danger'
                  : 'open'
              }`}
            >
              {opportunity.status || 'Open'}
            </span>

            {/* Owner Tag */}
            {opportunity.assignedToName && (
              <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px', background: '#f8fafc', padding: '4px 8px', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                <User size={13} />
                <span>{opportunity.assignedToName}</span>
              </span>
            )}

            {/* Edit Overview Action */}
            {canEdit && (
              <Button
                variant="secondary"
                size="md"
                icon={Edit}
                onClick={() => setIsEditing(!isEditing)}
              >
                {isEditing ? 'Cancel Edit' : 'Edit Overview'}
              </Button>
            )}

            {/* Automated Stage Business Transition Actions */}
            {opportunity?.stage === 'PI Issued' && (
              <Button
                variant="primary"
                size="md"
                icon={CheckCircle2}
                onClick={handleConfirmOrder}
                title="Confirm client order and initiate supply execution"
              >
                Confirm Order & Supply
              </Button>
            )}

            {opportunity?.stage === 'Supply' && (
              <Button
                variant="primary"
                size="md"
                icon={DollarSign}
                onClick={handleTrackPayment}
                title="Commence payment collection and outstanding tracking"
              >
                Track Payment
              </Button>
            )}

            {opportunity?.stage !== 'Dormant' && (
              <Button
                variant="secondary"
                size="md"
                icon={Clock}
                onClick={handleMarkDormant}
                title="Mark opportunity inactive or put on hold"
              >
                Mark Dormant
              </Button>
            )}

            {opportunity?.stage === 'Dormant' && (
              <Button
                variant="primary"
                size="md"
                icon={RefreshCw}
                onClick={handleReactivate}
                title="Reactivate dormant opportunity"
              >
                Reactivate
              </Button>
            )}

            {/* Back Action */}
            <Button
              variant="secondary"
              size="md"
              icon={ArrowLeft}
              onClick={() => navigate('/crm/opportunities')}
            >
              Opportunities
            </Button>
          </div>
        }
      />

      {/* Main 2-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', alignItems: 'start', marginTop: '1rem' }}>
        {/* Left Column: Details, Quotations & Invoicing, Log Interaction */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* B. Opportunity Details & Scope Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Briefcase size={18} color="var(--accent-primary)" />
                <span>Opportunity Details & Scope</span>
              </h3>
              {canEdit && !isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  style={{ background: 'none', border: 'none', color: 'var(--accent-primary)', cursor: 'pointer', fontSize: '0.825rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                >
                  <Edit size={13} />
                  <span>Edit Details</span>
                </button>
              )}
            </div>

            {isEditing ? (
              <form onSubmit={handleSaveOverview} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Opportunity Title *</label>
                  <input
                    type="text"
                    className="crm-input"
                    value={editFormData.name}
                    onChange={e => setEditFormData({ ...editFormData, name: e.target.value })}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Business Area</label>
                    <select
                      className="crm-select"
                      value={editFormData.businessArea}
                      onChange={e => setEditFormData({ ...editFormData, businessArea: e.target.value })}
                    >
                      {BUSINESS_AREAS.map(a => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Expected Close Date</label>
                    <input
                      type="date"
                      className="crm-input"
                      value={editFormData.expectedCloseDate}
                      onChange={e => setEditFormData({ ...editFormData, expectedCloseDate: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Currency</label>
                    <select
                      className="crm-select"
                      value={editFormData.currency}
                      onChange={e => setEditFormData({ ...editFormData, currency: e.target.value })}
                    >
                      {APPROVED_CURRENCIES.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Estimated Deal Value</label>
                    <input
                      type="number"
                      className="crm-input"
                      placeholder="0.00"
                      value={editFormData.estimatedValue}
                      onChange={e => setEditFormData({ ...editFormData, estimatedValue: e.target.value })}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Description / Technical Scope</label>
                  <textarea
                    className="crm-input"
                    rows={3}
                    value={editFormData.description}
                    onChange={e => setEditFormData({ ...editFormData, description: e.target.value })}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <Button type="button" variant="secondary" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary" disabled={savingOverview}>
                    {savingOverview ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </form>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* 2-column key metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Estimated Value
                    </span>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '0.2rem' }}>
                      {opportunity.currency || 'INR'} {Number(opportunity.estimatedValue || 0).toLocaleString()}
                    </div>
                  </div>

                  <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Expected Close Date
                    </span>
                    <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                      {formatDateOnly(opportunity.expectedCloseDate)}
                    </div>
                  </div>
                </div>

                {/* Attributes Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Business Area
                    </label>
                    <div style={{ marginTop: '0.25rem' }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.825rem',
                        fontWeight: 600,
                        background: opportunity.businessArea === 'Biogas' ? '#fef3c7' : '#e0f2fe',
                        color: opportunity.businessArea === 'Biogas' ? '#b45309' : '#0369a1'
                      }}>
                        {opportunity.businessArea || 'Biogas'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Requirement Types
                    </label>
                    <div style={{ marginTop: '0.25rem', display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                      {(opportunity.requirementTypes && opportunity.requirementTypes.length > 0 ? opportunity.requirementTypes : ['Consulting']).map((type, idx) => (
                        <span
                          key={idx}
                          style={{
                            padding: '2px 7px',
                            borderRadius: '4px',
                            fontSize: '0.78rem',
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

                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Opportunity Source
                    </label>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                      {opportunity.originatingLead?.leadSource || opportunity.opportunitySource || 'Qualified Lead'}
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Owner / Assigned To
                    </label>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.25rem' }}>
                      {opportunity.assignedToName || 'Unassigned'}
                    </div>
                  </div>
                </div>

                {/* Scope & Description */}
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                    Scope of Work & Technical Description
                  </label>
                  <div style={{
                    marginTop: '0.35rem',
                    padding: '0.85rem 1rem',
                    background: '#f8fafc',
                    borderRadius: '8px',
                    border: '1px solid #e2e8f0',
                    fontSize: '0.875rem',
                    color: opportunity.description || opportunity.requirementSummary ? '#1e293b' : 'var(--text-muted)',
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap'
                  }}>
                    {opportunity.description || opportunity.requirementSummary || 'No detailed scope of work recorded for this opportunity.'}
                  </div>
                </div>

                {/* Closed Reason (if Won or Lost) */}
                {(opportunity.status === 'Won' || opportunity.status === 'Lost') && (
                  <div style={{
                    padding: '0.85rem 1rem',
                    borderRadius: '8px',
                    background: opportunity.status === 'Won' ? '#f0fdf4' : '#fef2f2',
                    border: `1px solid ${opportunity.status === 'Won' ? '#bbf7d0' : '#fecaca'}`,
                    color: opportunity.status === 'Won' ? '#166534' : '#991b1b',
                    fontSize: '0.85rem'
                  }}>
                    <strong>{opportunity.status === 'Won' ? 'Won Reason:' : 'Loss Reason:'}</strong>{' '}
                    <span>{opportunity.wonReason || opportunity.lossReason || 'No specific reason documented.'}</span>
                  </div>
                )}

                {/* Metadata Timestamps */}
                <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.75rem', color: 'var(--text-muted)', paddingTop: '0.5rem', borderTop: '1px solid #f1f5f9' }}>
                  <span>Created: {formatDateTime(opportunity.createdAt)}</span>
                  <span>Updated: {formatDateTime(opportunity.updatedAt)}</span>
                </div>
              </div>
            )}
          </div>

          {/* F. Quotations & Invoicing Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FileText size={18} color="var(--accent-primary)" />
                  <span>Quotations & Commercial Invoicing</span>
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Manage commercial quotations, laboratory catalogue pricing, and Proforma Invoices (PI).
                </span>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <Button
                  variant="primary"
                  size="sm"
                  icon={Plus}
                  onClick={() => setQuotationModalOpen(true)}
                >
                  {activeQuotation ? 'Edit Quotation' : 'Create Quotation'}
                </Button>

                {activeQuotation && (
                  <>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={Copy}
                      onClick={handleCopyQuotationText}
                      disabled={copyingText}
                    >
                      {copyingText ? 'Copying...' : 'Copy Quotation Text'}
                    </Button>

                    <Button
                      variant="secondary"
                      size="sm"
                      icon={Receipt}
                      onClick={() => setInvoiceModalOpen(true)}
                      style={{ background: '#ecfdf5', borderColor: '#a7f3d0', color: '#047857', fontWeight: 600 }}
                    >
                      Prepare Proforma Invoice
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Current Quotation Summary Card */}
            {activeQuotation ? (
              <div style={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                padding: '1.25rem',
                marginBottom: '1rem',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        {activeQuotation.title || 'Standard Commercial Quotation'}
                      </span>
                      <span style={{
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontSize: '0.725rem',
                        fontWeight: 700,
                        background: activeQuotation.status === 'Approved' ? '#dcfce7' : '#eff6ff',
                        color: activeQuotation.status === 'Approved' ? '#166534' : '#1d4ed8'
                      }}>
                        {activeQuotation.status || 'Draft'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Quotation #{' '}
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#334155' }}>
                        {activeQuotation.quotationNumber || 'Pending'}
                      </span>{' '}
                      • Rev {activeQuotation.revisionNumber || 1} • Issued on {formatDateOnly(activeQuotation.quotationDate)}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Grand Total</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
                      ₹{Number(activeQuotation.amount || 0).toLocaleString()}
                    </div>
                    {activeQuotation.totalTax > 0 && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        (Subtotal: ₹{Number(activeQuotation.subtotal || 0).toLocaleString()} + Tax: ₹{Number(activeQuotation.totalTax || 0).toLocaleString()})
                      </div>
                    )}
                  </div>
                </div>

                {/* Interactive Catalogue Line Items */}
                <QuotationCatalogueSelector
                  quotationId={activeQuotation.id}
                  currency={activeQuotation.currency || opportunity.currency || 'INR'}
                  onTotalChanged={() => fetchQuotationAndInvoices()}
                />
              </div>
            ) : (
              <div style={{
                padding: '2rem',
                textAlign: 'center',
                background: '#f8fafc',
                border: '1px dashed var(--border-color)',
                borderRadius: '8px',
                marginBottom: '1rem'
              }}>
                <FileSpreadsheet size={32} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <h4 style={{ margin: '0 0 0.25rem 0', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  No Active Quotation
                </h4>
                <p style={{ margin: '0 0 1rem 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Create a commercial quotation with laboratory catalogue services, packages, and custom items.
                </p>
                <Button
                  variant="primary"
                  size="sm"
                  icon={Plus}
                  onClick={() => setQuotationModalOpen(true)}
                >
                  Create Quotation
                </Button>
              </div>
            )}

            {/* Saved Proforma Invoices (PI) Section */}
            <div style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Receipt size={16} />
                  <span>Proforma Invoices & Revisions ({proformaInvoices.length})</span>
                </h4>
                {activeQuotation && isCrmAdminOrManager && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingInvoice(null);
                      setInvoiceModalOpen(true);
                    }}
                    style={{ background: 'none', border: 'none', color: '#047857', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Plus size={13} />
                    <span>New Proforma Invoice</span>
                  </button>
                )}
              </div>

              {proformaInvoices.length === 0 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.75rem', background: '#f8fafc', borderRadius: '6px' }}>
                  No Proforma Invoices issued yet for this deal. Click &quot;Prepare Proforma Invoice&quot; to generate an official PI.
                </div>
              ) : (
                <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                    <thead>
                      <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                        <th style={{ padding: '8px 12px' }}>PI Number</th>
                        <th style={{ padding: '8px 12px' }}>Revision</th>
                        <th style={{ padding: '8px 12px' }}>Date</th>
                        <th style={{ padding: '8px 12px', textAlign: 'right' }}>Total Amount</th>
                        <th style={{ padding: '8px 12px', textAlign: 'center' }}>Status</th>
                        <th style={{ padding: '8px 12px', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {proformaInvoices.map(pi => (
                        <tr key={pi.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>
                            {pi.piNumber}
                          </td>
                          <td style={{ padding: '8px 12px', color: '#6d28d9', fontWeight: 600 }}>
                            Rev {pi.currentRevisionNumber || 1}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            {formatDateOnly(pi.piDate || pi.createdAt)}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700 }}>
                            {pi.currency || 'INR'} {Number(pi.grandTotal || 0).toLocaleString()}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              background: '#ecfdf5',
                              color: '#047857'
                            }}>
                              {pi.status || 'Issued'}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '0.4rem', alignItems: 'center' }}>
                              {isCrmAdminOrManager && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingInvoice(pi);
                                    setInvoiceModalOpen(true);
                                  }}
                                  className="crm-btn crm-btn-secondary crm-btn-sm"
                                  style={{ padding: '2px 7px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '3px', cursor: 'pointer' }}
                                  title="Edit Proforma Invoice"
                                >
                                  <Edit size={11} />
                                  <span>Edit PI</span>
                                </button>
                              )}
                              <a
                                href={invoiceService.getInvoiceHtmlUrl(pi.id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="crm-btn crm-btn-secondary crm-btn-sm"
                                style={{ padding: '2px 7px', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                                title="Open Print View / PDF"
                              >
                                <FileDown size={11} />
                                <span>Print / PDF</span>
                              </a>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* E. Log Interaction & Interaction History Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Clock size={18} color="var(--accent-primary)" />
                  <span>Interaction History & Touchpoints</span>
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Chronological record of client calls, meetings, technical discussions, and proposals.
                </span>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <Button
                  variant="primary"
                  size="sm"
                  icon={Plus}
                  onClick={() => setIsCommModalOpen(true)}
                >
                  Log Interaction
                </Button>
              </div>
            </div>

            {/* Channel Filters */}
            <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
              {['ALL', 'PHONE', 'EMAIL', 'MEETING', 'SITE_VISIT', 'WHATSAPP', 'NOTE'].map(ch => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setCommChannelFilter(ch)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    border: '1px solid',
                    borderColor: commChannelFilter === ch ? 'var(--accent-primary)' : '#e2e8f0',
                    background: commChannelFilter === ch ? '#eff6ff' : '#ffffff',
                    color: commChannelFilter === ch ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontWeight: commChannelFilter === ch ? 700 : 500,
                    cursor: 'pointer'
                  }}
                >
                  {ch === 'ALL' ? 'All Channels' : ch.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Communications Timeline */}
            {loadingComms ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                Loading interaction records...
              </div>
            ) : filteredCommunications.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', background: '#f8fafc', border: '1px dashed #e2e8f0', borderRadius: '8px' }}>
                <MessageSquare size={28} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>No Interactions Logged</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Click &quot;Log Interaction&quot; to record calls, emails, or on-site visits with this client.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {filteredCommunications.map((comm) => (
                  <div
                    key={comm.id}
                    style={{
                      padding: '0.85rem 1rem',
                      background: comm.isLeadHistory ? '#fbfcfe' : '#ffffff',
                      border: `1px solid ${comm.isLeadHistory ? '#e2e8f0' : '#cbd5e1'}`,
                      borderLeft: `4px solid ${comm.isLeadHistory ? '#94a3b8' : 'var(--accent-primary)'}`,
                      borderRadius: '6px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.35rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          background: '#f1f5f9',
                          color: '#334155'
                        }}>
                          {comm.communicationChannel || 'NOTE'}
                        </span>
                        {comm.isLeadHistory && (
                          <span style={{
                            padding: '1px 5px',
                            borderRadius: '3px',
                            fontSize: '0.68rem',
                            fontWeight: 600,
                            background: '#fef3c7',
                            color: '#b45309'
                          }}>
                            Lead History
                          </span>
                        )}
                        <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                          {comm.subject || `${comm.communicationChannel} Interaction`}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatDateTime(comm.communicationDate || comm.createdAt)}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                      {comm.summary || comm.notes || 'No description provided.'}
                    </div>

                    {(comm.outcome || comm.nextFollowUpDate) && (
                      <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', paddingTop: '0.4rem', borderTop: '1px dashed #f1f5f9', fontSize: '0.75rem' }}>
                        {comm.outcome && (
                          <span style={{ color: '#0369a1', fontWeight: 600 }}>
                            Outcome: {comm.outcome}
                          </span>
                        )}
                        {comm.nextFollowUpDate && (
                          <span style={{ color: '#b45309', fontWeight: 500 }}>
                            Next Follow-up: {formatDateOnly(comm.nextFollowUpDate)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Account Details, Contact Details, Originating Lead */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* C. Account Details Panel */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
              <h4 style={{
                margin: 0,
                fontSize: '0.95rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--text-primary)'
              }}>
                <Building size={16} color="var(--accent-primary)" />
                <span>Account Details</span>
              </h4>
              {opportunity.account && (
                <Link
                  to={`/crm/accounts?search=${encodeURIComponent(opportunity.account.name)}`}
                  style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', display: 'inline-flex', alignItems: 'center', gap: '2px', textDecoration: 'none', fontWeight: 600 }}
                  title="View Account Profile"
                >
                  <span>Open Account</span>
                  <ExternalLink size={10} />
                </Link>
              )}
            </div>

            {opportunity.account ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                <div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                    {opportunity.account.name}
                  </div>
                  {opportunity.account.accountId && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      Account ID: <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#334155' }}>{opportunity.account.accountId}</span>
                    </div>
                  )}
                  {opportunity.account.customerId && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      Customer ID: <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#0369a1' }}>{opportunity.account.customerId}</span>
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
                  {/* Website */}
                  <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                      <Globe size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      Website:
                    </span>
                    <div style={{ minWidth: 0, wordBreak: 'break-word' }}>
                      {opportunity.account.website ? (
                        <a
                          href={opportunity.account.website.startsWith('http') ? opportunity.account.website : `https://${opportunity.account.website}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500, display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <span>{opportunity.account.website.replace(/^https?:\/\//i, '').replace(/\/$/, '')}</span>
                          <ExternalLink size={11} style={{ opacity: 0.7 }} />
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>
                      )}
                    </div>
                  </div>

                  {/* Location / Address */}
                  <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                      <MapPin size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      Address:
                    </span>
                    <span style={{ color: '#1e293b', fontWeight: 500, wordBreak: 'break-word' }}>
                      {opportunity.account.address || opportunity.account.billingAddress || opportunity.account.city || '—'}
                    </span>
                  </div>

                  {/* GSTIN */}
                  {opportunity.account.gstNumber && (
                    <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                        <Tag size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                        GSTIN:
                      </span>
                      <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#334155' }}>
                        {opportunity.account.gstNumber}
                      </span>
                    </div>
                  )}

                  {/* Email */}
                  {opportunity.account.email && (
                    <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                        <Mail size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                        Email:
                      </span>
                      <a
                        href={`mailto:${opportunity.account.email}`}
                        style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                      >
                        {opportunity.account.email}
                      </a>
                    </div>
                  )}

                  {/* Phone */}
                  {opportunity.account.phone && (
                    <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                        <Phone size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                        Phone:
                      </span>
                      <a
                        href={`tel:${opportunity.account.phone}`}
                        style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                      >
                        {opportunity.account.phone}
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                No parent Account record linked to this opportunity.
              </div>
            )}
          </div>

          {/* D. Contact Details Panel */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
              <h4 style={{
                margin: 0,
                fontSize: '0.95rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--text-primary)'
              }}>
                <User size={16} color="var(--accent-primary)" />
                <span>Primary Contact Details</span>
              </h4>
              {opportunity.contact && (
                <Link
                  to={`/crm/contacts?search=${encodeURIComponent(opportunity.contact.name)}`}
                  style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', display: 'inline-flex', alignItems: 'center', gap: '2px', textDecoration: 'none', fontWeight: 600 }}
                  title="View Contact Profile"
                >
                  <span>Open Contact</span>
                  <ExternalLink size={10} />
                </Link>
              )}
            </div>

            {opportunity.contact ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                <div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0f172a', lineHeight: 1.3 }}>
                    {opportunity.contact.name}
                  </div>
                  {opportunity.contact.designation && (
                    <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                      {opportunity.contact.designation}
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
                  {/* Email */}
                  <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                      <Mail size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      Email:
                    </span>
                    <div style={{ minWidth: 0, wordBreak: 'break-word' }}>
                      {opportunity.contact.email ? (
                        <a
                          href={`mailto:${opportunity.contact.email}`}
                          style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                        >
                          {opportunity.contact.email}
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>
                      )}
                    </div>
                  </div>

                  {/* Phone */}
                  <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                      <Phone size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      Phone:
                    </span>
                    <div style={{ minWidth: 0, wordBreak: 'break-word' }}>
                      {opportunity.contact.mobileNumber || opportunity.contact.phone ? (
                        <a
                          href={`tel:${opportunity.contact.mobileNumber || opportunity.contact.phone}`}
                          style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}
                        >
                          {opportunity.contact.mobileNumber || opportunity.contact.phone}
                        </a>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>—</span>
                      )}
                    </div>
                  </div>

                  {/* Account relationship */}
                  <div style={{ display: 'grid', gridTemplateColumns: '72px 1fr', gap: '0.5rem', alignItems: 'baseline', fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 500 }}>
                      <Building size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      Account:
                    </span>
                    <span style={{ color: '#1e293b', fontWeight: 600 }}>
                      {opportunity.contact.accountName || opportunity.account?.name || 'Direct Contact'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic', padding: '0.5rem 0' }}>
                No primary Contact record linked to this opportunity.
              </div>
            )}
          </div>

          {/* G. Originating Lead & Commercial Context */}
          {(opportunity.originatingLead || opportunity.originatingLeadId) && (
            <div className="glass-panel" style={{ padding: '1.25rem', background: '#f8fafc', borderLeft: '4px solid #0284c7' }}>
              <h4 style={{
                margin: '0 0 0.75rem 0',
                fontSize: '0.95rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--text-primary)'
              }}>
                <Layers size={16} color="#0284c7" />
                <span>Originating Lead Context</span>
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.825rem' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)' }}>Lead Title & ID:</div>
                  <Link
                    to={`/crm/leads/${opportunity.originatingLead?.id || opportunity.originatingLeadId}`}
                    style={{ color: '#0284c7', fontWeight: 700, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '3px' }}
                  >
                    <span>{opportunity.originatingLead?.leadName || 'Originating Lead'} ({opportunity.originatingLead?.leadId || opportunity.originatingLeadNumber || 'LEAD'})</span>
                    <ExternalLink size={11} />
                  </Link>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #e2e8f0', paddingTop: '0.5rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Lifecycle Status:</span>
                  <span style={{ fontWeight: 600, color: '#166534' }}>
                    {opportunity.originatingLead?.lifecycleStatus || 'Qualified'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Original Source:</span>
                  <span style={{ fontWeight: 500 }}>
                    {opportunity.originatingLead?.leadSource || 'Direct'}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* H. Automated Stage History Audit Trail */}
          <div className="glass-panel" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
              <h4 style={{
                margin: 0,
                fontSize: '0.95rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: 'var(--text-primary)'
              }}>
                <Clock size={16} color="var(--accent-primary)" />
                <span>Stage History ({stageHistory.length})</span>
              </h4>
              <button
                onClick={fetchStageHistory}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                title="Refresh stage history"
              >
                <RefreshCw size={13} className={loadingHistory ? 'spin' : ''} />
              </button>
            </div>

            {loadingHistory ? (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '0.75rem' }}>
                Loading stage history...
              </div>
            ) : stageHistory.length === 0 ? (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', padding: '0.75rem' }}>
                No stage transitions recorded yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {stageHistory.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      padding: '0.65rem 0.75rem',
                      background: '#f8fafc',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                      fontSize: '0.8rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}>
                        <span style={{ color: 'var(--text-muted)' }}>{item.previousStage || 'Start'}</span>
                        <span>&rarr;</span>
                        <span style={{ color: 'var(--accent-primary)' }}>{item.newStage}</span>
                      </div>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {item.createdAt ? formatDateTime(item.createdAt) : ''}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-secondary)' }}>
                      <strong>Event:</strong> {item.triggeringEvent}
                      {item.triggeringUserName && <span> &bull; {item.triggeringUserName}</span>}
                    </div>
                    {item.remarks && (
                      <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontStyle: 'italic' }}>
                        &ldquo;{item.remarks}&rdquo;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quotation Manager Modal */}
      {quotationModalOpen && (
        <QuotationManagerModal
          isOpen={quotationModalOpen}
          onClose={() => {
            setQuotationModalOpen(false);
            fetchQuotationAndInvoices();
          }}
          opportunity={opportunity}
          onQuotationSaved={(savedQuote) => {
            setActiveQuotation(savedQuote);
            fetchQuotationAndInvoices();
            setSuccessMsg('Quotation saved successfully.');
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
          onApproveAndCreateInvoice={(savedQuote) => {
            setQuotationModalOpen(false);
            setActiveQuotation(savedQuote);
            setInvoiceModalOpen(true);
          }}
        />
      )}

      {/* Invoice Preparation Modal */}
      {invoiceModalOpen && (activeQuotation || editingInvoice) && (
        <InvoicePreparationModal
          isOpen={invoiceModalOpen}
          onClose={() => {
            setInvoiceModalOpen(false);
            setEditingInvoice(null);
            fetchQuotationAndInvoices();
          }}
          opportunity={opportunity}
          quotation={activeQuotation}
          editingInvoice={editingInvoice}
          onInvoiceCreated={(piData) => {
            setEditingInvoice(null);
            fetchQuotationAndInvoices();
            setSuccessMsg(`Proforma Invoice ${piData?.piNumber || ''} created successfully.`);
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
          onInvoiceUpdated={(piData) => {
            setEditingInvoice(null);
            fetchQuotationAndInvoices();
            setSuccessMsg(`Proforma Invoice ${piData?.piNumber || ''} updated successfully.`);
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
        />
      )}

      {/* Log Interaction Modal */}
      {isCommModalOpen && (
        <div className="crm-modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1100
        }}>
          <div className="crm-modal" style={{
            background: '#ffffff',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '560px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.15)',
            border: '1px solid var(--border-color)',
            overflow: 'hidden'
          }}>
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Clock size={18} color="var(--accent-primary)" />
                <span>Log Opportunity Interaction</span>
              </h3>
              <button
                type="button"
                onClick={() => setIsCommModalOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', color: 'var(--text-muted)' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogInteraction} style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Interaction Channel</label>
                  <select
                    className="crm-select"
                    value={commFormData.communicationChannel}
                    onChange={e => setCommFormData({ ...commFormData, communicationChannel: e.target.value })}
                  >
                    <option value="PHONE">Phone Call</option>
                    <option value="EMAIL">Email</option>
                    <option value="MEETING">Meeting</option>
                    <option value="SITE_VISIT">Site Visit</option>
                    <option value="WHATSAPP">WhatsApp</option>
                    <option value="NOTE">Internal Note</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Date and Time</label>
                  <input
                    type="datetime-local"
                    className="crm-input"
                    value={commFormData.communicationDate}
                    onChange={e => setCommFormData({ ...commFormData, communicationDate: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Subject / Topic</label>
                <input
                  type="text"
                  className="crm-input"
                  placeholder="e.g. Discussed bio-catalyst pricing with Plant Head"
                  value={commFormData.subject}
                  onChange={e => setCommFormData({ ...commFormData, subject: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Description / Notes *</label>
                <textarea
                  className="crm-input"
                  rows={4}
                  placeholder="Record summary of discussion, client questions, commercial expectations, or next steps..."
                  value={commFormData.summary}
                  onChange={e => setCommFormData({ ...commFormData, summary: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Outcome</label>
                  <select
                    className="crm-select"
                    value={commFormData.outcome}
                    onChange={e => setCommFormData({ ...commFormData, outcome: e.target.value })}
                  >
                    <option value="Follow-up Required">Follow-up Required</option>
                    <option value="Proposal Sent">Proposal Sent</option>
                    <option value="Quotation Approved">Quotation Approved</option>
                    <option value="Decision Pending">Decision Pending</option>
                    <option value="No Answer">No Answer</option>
                    <option value="Completed">Completed</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Next Follow-up Date (Optional)</label>
                  <input
                    type="date"
                    className="crm-input"
                    value={commFormData.nextFollowUpDate}
                    onChange={e => setCommFormData({ ...commFormData, nextFollowUpDate: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                <Button type="button" variant="secondary" onClick={() => setIsCommModalOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={submittingComm}>
                  {submittingComm ? 'Logging...' : 'Save Interaction'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
