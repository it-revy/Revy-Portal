import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Briefcase,
  Building,
  User,
  Layers,
  ExternalLink,
  Edit3,
  CheckCircle2,
  Clock,
  AlertCircle,
  Plus,
  Trash2,
  TrendingUp,
  RefreshCw,
  GitBranch,
  ShieldCheck,
  Check,
  FileText,
  Send,
  CheckSquare,
  RotateCcw,
  FileCheck,
  AlertTriangle
} from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import crmService from '../../../services/crmService';
import OpportunityStageModal from './OpportunityStageModal';

const STAGES = ['Enquiry', 'Qualify', 'Develop', 'Propose/Offer', 'Negotiate', 'Close'];
const BUSINESS_AREAS = ['Biogas', 'Wastewater Treatment (WWT)', 'R&D Lab', 'Other'];
const APPROVED_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD'];

export default function OpportunityDetailModal({
  isOpen,
  onClose,
  opportunityId,
  onOpportunityUpdated
}) {
  const { user, activeRole } = useAuth();
  const userRoles = [
    ...(user?.roles || []),
    activeRole
  ].filter(Boolean);
  const isSalesManager = userRoles.some(r => ['CRM_SALES_MANAGER', 'CRM_ADMIN', 'Admin', 'SuperAdmin', 'IT_ADMIN'].includes(r));
  const canReopenDeal = userRoles.some(r => ['CRM_ADMIN', 'Admin', 'SuperAdmin', 'IT_ADMIN', 'DIRECTOR', 'Director'].includes(r));

  const [activeTab, setActiveTab] = useState('overview'); // overview, quotations, routing, milestones
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Stage modal state
  const [isStageModalOpen, setIsStageModalOpen] = useState(false);

  // Edit Opportunity Overview State
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '',
    currency: 'INR',
    estimatedValue: '',
    estimatedValueChangeReason: '',
    expectedCloseDate: '',
    businessArea: '',
    description: '',
    subStatus: ''
  });
  const [savingOverview, setSavingOverview] = useState(false);

  // Quotations State (Phase 5A)
  const [quotations, setQuotations] = useState([]);
  const [activeQuotation, setActiveQuotation] = useState(null);
  const [loadingQuotations, setLoadingQuotations] = useState(false);
  const [quotationModalOpen, setQuotationModalOpen] = useState(false);
  const [quotationModalMode, setQuotationModalMode] = useState('create'); // 'create', 'edit', 'revise'
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [quotationFormData, setQuotationFormData] = useState({
    title: '',
    amount: '',
    currency: 'INR',
    quotationDate: new Date().toISOString().split('T')[0],
    validUntilDate: '',
    termsAndConditions: '',
    notes: '',
    documentName: ''
  });
  const [savingQuotation, setSavingQuotation] = useState(false);

  // Approval Modal State
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);
  const [approvalAction, setApprovalAction] = useState('approve');
  const [rejectionReason, setRejectionReason] = useState('');
  const [processingApproval, setProcessingApproval] = useState(false);

  // Share Modal State
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [shareFormData, setShareFormData] = useState({
    sentMethod: 'Email',
    sentTo: '',
    sendingEvidence: ''
  });
  const [processingShare, setProcessingShare] = useState(false);

  // Reopen Modal State
  const [reopenModalOpen, setReopenModalOpen] = useState(false);
  const [reopenReason, setReopenReason] = useState('');
  const [reopenStage, setReopenStage] = useState('Close');
  const [processingReopen, setProcessingReopen] = useState(false);

  // Workstreams (Phase 4B)
  const [workstreams, setWorkstreams] = useState([]);
  const [loadingWorkstreams, setLoadingWorkstreams] = useState(false);
  const [routingRequirements, setRoutingRequirements] = useState(false);
  const [routingSuccessMsg, setRoutingSuccessMsg] = useState(null);

  // Milestones (Phase 4C)
  const [milestones, setMilestones] = useState([]);
  const [loadingMilestones, setLoadingMilestones] = useState(false);
  const [isAddingMilestone, setIsAddingMilestone] = useState(false);
  const [milestoneFormData, setMilestoneFormData] = useState({
    title: '',
    description: '',
    workstreamType: '',
    dueDate: '',
    plannedStartDate: '',
    assignedToUserId: ''
  });
  const [savingMilestone, setSavingMilestone] = useState(false);
  const [assignees, setAssignees] = useState([]);

  // Fetch full opportunity detail
  const fetchOpportunityDetails = useCallback(async () => {
    if (!opportunityId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await crmService.getOpportunityById(opportunityId);
      if (res.data?.success) {
        const opp = res.data.opportunity;
        setOpportunity(opp);
        setEditFormData({
          name: opp.name || '',
          currency: opp.currency || 'INR',
          estimatedValue: opp.estimatedValue !== null && opp.estimatedValue !== undefined ? opp.estimatedValue : '',
          estimatedValueChangeReason: '',
          expectedCloseDate: opp.expectedCloseDate ? opp.expectedCloseDate.split('T')[0] : '',
          businessArea: opp.businessArea || 'Biogas',
          description: opp.description || '',
          subStatus: opp.subStatus || opp.sub_status || ''
        });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load opportunity.');
    } finally {
      setLoading(false);
    }
  }, [opportunityId]);

  // Fetch quotations (Phase 5A)
  const fetchQuotations = useCallback(async () => {
    if (!opportunityId) return;
    setLoadingQuotations(true);
    try {
      const res = await crmService.getOpportunityQuotations(opportunityId);
      if (res.data?.success) {
        setQuotations(res.data.quotations || []);
        setActiveQuotation(res.data.activeQuotation || null);
      }
    } catch (err) {
      console.error('Failed to load quotations:', err);
    } finally {
      setLoadingQuotations(false);
    }
  }, [opportunityId]);

  // Fetch workstreams
  const fetchWorkstreams = useCallback(async () => {
    if (!opportunityId) return;
    setLoadingWorkstreams(true);
    try {
      const res = await crmService.getOpportunityWorkstreams(opportunityId);
      if (res.data?.success) {
        setWorkstreams(res.data.workstreams || []);
      }
    } catch (err) {
      console.error('Failed to load workstreams:', err);
    } finally {
      setLoadingWorkstreams(false);
    }
  }, [opportunityId]);

  // Fetch milestones
  const fetchMilestones = useCallback(async () => {
    if (!opportunityId) return;
    setLoadingMilestones(true);
    try {
      const res = await crmService.getOpportunityMilestones(opportunityId);
      if (res.data?.success) {
        setMilestones(res.data.milestones || []);
      }
    } catch (err) {
      console.error('Failed to load milestones:', err);
    } finally {
      setLoadingMilestones(false);
    }
  }, [opportunityId]);

  // Load assignees
  useEffect(() => {
    crmService.getEligibleAssignees()
      .then(res => {
        if (res.data?.success) {
          setAssignees(res.data.assignees || []);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (isOpen && opportunityId) {
      fetchOpportunityDetails();
      fetchQuotations();
      fetchWorkstreams();
      fetchMilestones();
      setActiveTab('overview');
      setIsEditing(false);
      setRoutingSuccessMsg(null);
    }
  }, [isOpen, opportunityId, fetchOpportunityDetails, fetchQuotations, fetchWorkstreams, fetchMilestones]);

  if (!isOpen) return null;

  // Handle Save Overview
  const handleSaveOverview = async (e) => {
    e.preventDefault();
    setSavingOverview(true);
    setError(null);
    try {
      const payload = {
        name: editFormData.name.trim(),
        currency: editFormData.currency || 'INR',
        estimatedValue: editFormData.estimatedValue ? Number(editFormData.estimatedValue) : null,
        estimatedValueChangeReason: editFormData.estimatedValueChangeReason ? editFormData.estimatedValueChangeReason.trim() : undefined,
        expectedCloseDate: editFormData.expectedCloseDate || null,
        businessArea: editFormData.businessArea || null,
        description: editFormData.description ? editFormData.description.trim() : null,
        subStatus: editFormData.subStatus !== undefined ? (editFormData.subStatus.trim() || null) : null
      };

      const res = await crmService.updateOpportunity(opportunity.id, payload);
      if (res.data?.success) {
        setOpportunity(res.data.opportunity);
        setIsEditing(false);
        if (onOpportunityUpdated) onOpportunityUpdated(res.data.opportunity);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update opportunity details.');
    } finally {
      setSavingOverview(false);
    }
  };

  // Quotation Management Handlers (Phase 5A)
  const handleOpenQuotationModal = (mode = 'create', quote = null) => {
    setQuotationModalMode(mode);
    setSelectedQuotation(quote);
    if (mode === 'create') {
      setQuotationFormData({
        title: `Quotation for ${opportunity?.name || ''}`,
        amount: opportunity?.estimatedValue !== null && opportunity?.estimatedValue !== undefined ? opportunity.estimatedValue : '',
        currency: opportunity?.currency || 'INR',
        quotationDate: new Date().toISOString().split('T')[0],
        validUntilDate: '',
        termsAndConditions: 'Standard REVY commercial delivery and payment terms apply.',
        notes: '',
        documentName: ''
      });
    } else if (mode === 'edit' && quote) {
      setQuotationFormData({
        title: quote.title || '',
        amount: quote.amount || '',
        currency: quote.currency || 'INR',
        quotationDate: quote.quotationDate ? quote.quotationDate.split('T')[0] : '',
        validUntilDate: quote.validUntilDate ? quote.validUntilDate.split('T')[0] : '',
        termsAndConditions: quote.termsAndConditions || '',
        notes: quote.notes || '',
        documentName: quote.documentName || ''
      });
    } else if (mode === 'revise' && quote) {
      setQuotationFormData({
        title: quote.title || '',
        amount: quote.amount || '',
        currency: quote.currency || 'INR',
        quotationDate: new Date().toISOString().split('T')[0],
        validUntilDate: quote.validUntilDate ? quote.validUntilDate.split('T')[0] : '',
        termsAndConditions: quote.termsAndConditions || '',
        notes: `Revised from ${quote.version}`,
        documentName: ''
      });
    }
    setQuotationModalOpen(true);
  };

  const handleSaveQuotation = async (e) => {
    e.preventDefault();
    setSavingQuotation(true);
    setError(null);
    try {
      const payload = {
        title: quotationFormData.title.trim(),
        amount: Number(quotationFormData.amount) || 0,
        currency: quotationFormData.currency,
        quotationDate: quotationFormData.quotationDate || undefined,
        validUntilDate: quotationFormData.validUntilDate || undefined,
        termsAndConditions: quotationFormData.termsAndConditions?.trim() || undefined,
        notes: quotationFormData.notes?.trim() || undefined,
        documentName: quotationFormData.documentName?.trim() || undefined
      };

      if (quotationModalMode === 'create') {
        await crmService.createOpportunityQuotation(opportunity.id, payload);
      } else if (quotationModalMode === 'revise' && selectedQuotation) {
        await crmService.reviseOpportunityQuotation(opportunity.id, selectedQuotation.id, payload);
      } else if (quotationModalMode === 'edit' && selectedQuotation) {
        await crmService.updateOpportunityQuotation(opportunity.id, selectedQuotation.id, payload);
      }

      setQuotationModalOpen(false);
      fetchQuotations();
      fetchOpportunityDetails();
      if (onOpportunityUpdated) onOpportunityUpdated(opportunity);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save quotation.');
    } finally {
      setSavingQuotation(false);
    }
  };

  const handleSubmitQuotationForReview = async (quoteId) => {
    try {
      await crmService.submitQuotationForReview(opportunity.id, quoteId);
      fetchQuotations();
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to submit quotation for review.');
    }
  };

  const handleApproveOrRejectQuotation = async (e) => {
    e.preventDefault();
    if (approvalAction === 'reject' && !rejectionReason.trim()) {
      setError('Please provide a rejection reason.');
      return;
    }
    setProcessingApproval(true);
    try {
      await crmService.approveQuotation(opportunity.id, activeQuotation.id, {
        action: approvalAction,
        reason: rejectionReason.trim() || undefined
      });
      setApprovalModalOpen(false);
      setRejectionReason('');
      fetchQuotations();
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to process quotation approval.');
    } finally {
      setProcessingApproval(false);
    }
  };

  const handleShareQuotation = async (e) => {
    e.preventDefault();
    if (!shareFormData.sentTo.trim()) {
      setError('Please provide a recipient (sentTo).');
      return;
    }
    setProcessingShare(true);
    try {
      await crmService.markQuotationShared(opportunity.id, activeQuotation.id, {
        sentMethod: shareFormData.sentMethod,
        sentTo: shareFormData.sentTo.trim(),
        sendingEvidence: shareFormData.sendingEvidence?.trim() || undefined
      });
      setShareModalOpen(false);
      fetchQuotations();
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to record quotation sharing.');
    } finally {
      setProcessingShare(false);
    }
  };

  const handleReopenOpportunity = async (e) => {
    e.preventDefault();
    if (!reopenReason.trim()) {
      setError('Please provide a mandatory justification reason to reopen this opportunity.');
      return;
    }
    setProcessingReopen(true);
    try {
      const res = await crmService.reopenOpportunity(opportunity.id, {
        reason: reopenReason.trim(),
        reopenStage: reopenStage
      });
      if (res.data?.success) {
        setOpportunity(res.data.opportunity);
        setReopenModalOpen(false);
        setReopenReason('');
        if (onOpportunityUpdated) onOpportunityUpdated(res.data.opportunity);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reopen opportunity.');
    } finally {
      setProcessingReopen(false);
    }
  };

  // Handle Route Requirements (Phase 4B)
  const handleRouteRequirements = async () => {
    setRoutingRequirements(true);
    setRoutingSuccessMsg(null);
    setError(null);
    try {
      const res = await crmService.routeOpportunityRequirements(opportunity.id, {
        requirementTypes: opportunity.requirementTypes || []
      });
      if (res.data?.success) {
        setRoutingSuccessMsg(res.data.message || 'Requirements routed successfully.');
        setWorkstreams(res.data.routedWorkstreams || []);
        fetchOpportunityDetails();
        if (onOpportunityUpdated) onOpportunityUpdated({ ...opportunity, workstreamCount: (res.data.routedWorkstreams || []).length });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to route requirements.');
    } finally {
      setRoutingRequirements(false);
    }
  };

  // Handle Create Milestone (Phase 4C)
  const handleCreateMilestone = async (e) => {
    e.preventDefault();
    if (!milestoneFormData.title.trim()) return;

    setSavingMilestone(true);
    setError(null);
    try {
      const payload = {
        title: milestoneFormData.title.trim(),
        description: milestoneFormData.description ? milestoneFormData.description.trim() : undefined,
        workstreamType: milestoneFormData.workstreamType || undefined,
        dueDate: milestoneFormData.dueDate || undefined,
        plannedStartDate: milestoneFormData.plannedStartDate || undefined,
        assignedToUserId: milestoneFormData.assignedToUserId || undefined
      };

      const res = await crmService.createOpportunityMilestone(opportunity.id, payload);
      if (res.data?.success) {
        setIsAddingMilestone(false);
        setMilestoneFormData({
          title: '',
          description: '',
          workstreamType: '',
          dueDate: '',
          plannedStartDate: '',
          assignedToUserId: ''
        });
        fetchMilestones();
        fetchOpportunityDetails();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create milestone.');
    } finally {
      setSavingMilestone(false);
    }
  };

  // Quick Milestone Status Transition
  const handleMilestoneStatus = async (milestoneId, newStatus) => {
    try {
      await crmService.transitionMilestoneStatus(milestoneId, { status: newStatus });
      fetchMilestones();
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update milestone status.');
    }
  };

  // Delete Milestone
  const handleDeleteMilestone = async (milestoneId) => {
    if (!window.confirm('Are you sure you want to delete this milestone?')) return;
    try {
      await crmService.deleteMilestone(milestoneId);
      fetchMilestones();
      fetchOpportunityDetails();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to delete milestone.');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Won':
        return (
          <span style={{
            background: 'var(--success-bg)',
            color: 'var(--success)',
            border: '1px solid var(--success-border)',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            Won
          </span>
        );
      case 'Lost':
        return (
          <span style={{
            background: 'var(--danger-bg)',
            color: 'var(--danger)',
            border: '1px solid var(--danger-border)',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            Lost
          </span>
        );
      case 'Open':
      default:
        return (
          <span style={{
            background: 'var(--accent-light)',
            color: 'var(--accent-primary)',
            border: '1px solid var(--accent-light)',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            Open
          </span>
        );
    }
  };

  const currentStageIndex = STAGES.indexOf(opportunity?.stage || 'Qualify');

  return (
    <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{
          maxWidth: '840px',
          width: '94%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: '12px',
          padding: 0,
          background: '#ffffff',
          boxShadow: 'var(--modal-shadow)',
          overflow: 'hidden'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Header */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderBottom: '1px solid var(--border-color)',
          background: '#f8fafc',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'var(--accent-light)',
              color: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Briefcase size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  {opportunity?.opportunityId || 'Loading...'}
                </span>
                {opportunity && getStatusBadge(opportunity.status)}
                {opportunity?.businessArea && (
                  <span style={{ fontSize: '0.725rem', background: '#e2e8f0', color: '#475569', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                    {opportunity.businessArea}
                  </span>
                )}
              </div>
              <h2 style={{ margin: '0.2rem 0 0', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {opportunity?.name || 'Opportunity Details'}
              </h2>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {opportunity && canReopenDeal && (opportunity.status === 'Won' || opportunity.status === 'Lost') && (
              <button
                type="button"
                className="crm-btn crm-btn-secondary crm-btn-sm"
                onClick={() => setReopenModalOpen(true)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#b45309', borderColor: '#fde68a', background: '#fffbeb' }}
                title="Reopen closed opportunity to active funnel"
              >
                <RotateCcw size={15} />
                <span>Reopen Opportunity</span>
              </button>
            )}
            {opportunity && (
              <Link
                to={`/crm/opportunities/${opportunity.id}/edit`}
                className="crm-btn crm-btn-secondary crm-btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                title="Open dedicated opportunity edit page"
              >
                <Edit3 size={15} />
                <span>Edit</span>
              </Link>
            )}
            <button
              type="button"
              className="crm-btn crm-btn-secondary crm-btn-sm"
              onClick={() => setIsStageModalOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <TrendingUp size={15} />
              <span>Change Stage / Outcome</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1 }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Stage Progress Stepper */}
        {opportunity && (
          <div style={{ padding: '0.75rem 1.75rem', background: '#ffffff', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
              {STAGES.map((stg, idx) => {
                const isPassed = idx < currentStageIndex;
                const isCurrent = idx === currentStageIndex;
                return (
                  <div
                    key={stg}
                    style={{
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      position: 'relative'
                    }}
                  >
                    <div style={{
                      width: '100%',
                      height: '6px',
                      borderRadius: '3px',
                      background: isCurrent ? 'var(--accent-primary)' : (isPassed ? 'var(--success)' : '#e2e8f0'),
                      marginBottom: '0.35rem'
                    }} />
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: isCurrent ? 700 : 500,
                      color: isCurrent ? 'var(--accent-primary)' : (isPassed ? 'var(--success-text)' : 'var(--text-muted)')
                    }}>
                      {stg}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Tab Headers */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', background: '#f8fafc', padding: '0 1.75rem' }}>
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'overview' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: activeTab === 'overview' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer'
            }}
          >
            Overview & Details
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('quotations')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'quotations' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: activeTab === 'quotations' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}
          >
            <FileText size={15} />
            <span>Quotations</span>
            {quotations.length > 0 && (
              <span style={{ background: '#e0e7ff', color: '#4338ca', fontSize: '0.7rem', padding: '1px 6px', borderRadius: '10px' }}>
                {quotations.length}
              </span>
            )}
            {opportunity?.hasQuotationMismatch && (
              <span title="Active quotation amount differs from opportunity estimated value" style={{ display: 'inline-flex', alignItems: 'center', color: '#b45309' }}>
                <AlertTriangle size={13} />
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('routing')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'routing' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: activeTab === 'routing' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}
          >
            <GitBranch size={15} />
            <span>Requirement Routing</span>
            {workstreams.length > 0 && (
              <span style={{ background: '#e0e7ff', color: '#4338ca', fontSize: '0.7rem', padding: '1px 6px', borderRadius: '10px' }}>
                {workstreams.length}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('milestones')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              background: 'none',
              borderBottom: activeTab === 'milestones' ? '2px solid var(--accent-primary)' : '2px solid transparent',
              color: activeTab === 'milestones' ? 'var(--accent-primary)' : 'var(--text-secondary)',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}
          >
            <Clock size={15} />
            <span>Milestones</span>
            {milestones.length > 0 && (
              <span style={{ background: '#e0e7ff', color: '#4338ca', fontSize: '0.7rem', padding: '1px 6px', borderRadius: '10px' }}>
                {milestones.length}
              </span>
            )}
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem 1.75rem' }}>
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

          {routingSuccessMsg && (
            <div style={{
              padding: '0.75rem 1rem',
              background: 'var(--success-bg)',
              border: '1px solid var(--success-border)',
              borderRadius: '6px',
              color: 'var(--success-text)',
              fontSize: '0.85rem',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <CheckCircle2 size={16} />
              <span>{routingSuccessMsg}</span>
            </div>
          )}

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
              <span>Loading opportunity details...</span>
            </div>
          ) : !opportunity ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
              Opportunity not found.
            </div>
          ) : (
            <>
              {/* TAB 1: OVERVIEW */}
              {activeTab === 'overview' && (
                <div>
                  {isEditing ? (
                    <form onSubmit={handleSaveOverview} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>Edit Opportunity</h4>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            onClick={() => setIsEditing(false)}
                            disabled={savingOverview}
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            className="crm-btn crm-btn-primary crm-btn-sm"
                            disabled={savingOverview}
                          >
                            {savingOverview ? 'Saving...' : 'Save Changes'}
                          </button>
                        </div>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                          Opportunity Name *
                        </label>
                        <input
                          type="text"
                          className="form-control"
                          value={editFormData.name}
                          onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                          required
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr 1fr', gap: '1rem' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                            Currency
                          </label>
                          <select
                            className="form-control"
                            value={editFormData.currency}
                            onChange={(e) => setEditFormData({ ...editFormData, currency: e.target.value })}
                          >
                            {APPROVED_CURRENCIES.map(curr => (
                              <option key={curr} value={curr}>{curr}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                            Estimated Value
                          </label>
                          <input
                            type="number"
                            step="0.01"
                            className="form-control"
                            value={editFormData.estimatedValue}
                            onChange={(e) => setEditFormData({ ...editFormData, estimatedValue: e.target.value })}
                          />
                        </div>

                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                            Expected Close Date
                          </label>
                          <input
                            type="date"
                            className="form-control"
                            value={editFormData.expectedCloseDate}
                            onChange={(e) => setEditFormData({ ...editFormData, expectedCloseDate: e.target.value })}
                          />
                        </div>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                          Reason for Value Change (Audit Track)
                        </label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. Scope revised after customer technical review"
                          value={editFormData.estimatedValueChangeReason}
                          onChange={(e) => setEditFormData({ ...editFormData, estimatedValueChangeReason: e.target.value })}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                          Business Area
                        </label>
                        <select
                          className="form-control"
                          value={editFormData.businessArea}
                          onChange={(e) => setEditFormData({ ...editFormData, businessArea: e.target.value })}
                        >
                          {BUSINESS_AREAS.map(ba => (
                            <option key={ba} value={ba}>{ba}</option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                          Operational Sub-status (Free Text)
                        </label>
                        <input
                          type="text"
                          maxLength={255}
                          placeholder="e.g. Waiting for revised quotation, Sample collection to be scheduled..."
                          className="form-control"
                          value={editFormData.subStatus}
                          onChange={(e) => setEditFormData({ ...editFormData, subStatus: e.target.value })}
                        />
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          Free-text operational progress note (max 255 chars).
                        </span>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                          Scope & Requirements Description
                        </label>
                        <textarea
                          rows={3}
                          className="form-control"
                          value={editFormData.description}
                          onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                        />
                      </div>
                    </form>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          onClick={() => setIsEditing(true)}
                          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                        >
                          <Edit3 size={14} />
                          <span>Edit Details</span>
                        </button>
                      </div>

                      {/* Commercial Mismatch Warning Banner */}
                      {opportunity.hasQuotationMismatch && (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.65rem',
                          padding: '0.75rem 1rem',
                          background: '#fffbeb',
                          border: '1px solid #fde68a',
                          borderRadius: '8px',
                          color: '#92400e',
                          fontSize: '0.85rem'
                        }}>
                          <AlertTriangle size={18} style={{ flexShrink: 0, color: '#d97706' }} />
                          <div>
                            <strong>Commercial Value Mismatch:</strong> Active quotation amount (
                            {opportunity.activeQuotationCurrency} {Number(opportunity.activeQuotationAmount).toLocaleString()}
                            ) differs from the opportunity estimated value (
                            {opportunity.currency || 'INR'} {Number(opportunity.estimatedValue).toLocaleString()}
                            ). Check the <strong>Quotations</strong> tab to review or synchronize.
                          </div>
                        </div>
                      )}

                      {/* Top Metric Cards */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem' }}>
                        <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Estimated Value
                          </span>
                          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0f172a', marginTop: '0.2rem' }}>
                            {opportunity.estimatedValue !== null && opportunity.estimatedValue !== undefined ? (
                              `${opportunity.currency || 'INR'} ${Number(opportunity.estimatedValue).toLocaleString()}`
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>Not specified</span>
                            )}
                          </div>
                        </div>

                        <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Current Stage
                          </span>
                          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '0.2rem' }}>
                            {opportunity.stage}
                          </div>
                        </div>

                        <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Sub-status
                          </span>
                          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: (opportunity.subStatus || opportunity.sub_status) ? '#0f172a' : 'var(--text-muted)', marginTop: '0.2rem', fontStyle: (opportunity.subStatus || opportunity.sub_status) ? 'normal' : 'italic' }}>
                            {opportunity.subStatus || opportunity.sub_status || 'None'}
                          </div>
                        </div>

                        <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Expected Close
                          </span>
                          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                            {opportunity.expectedCloseDate ? new Date(opportunity.expectedCloseDate).toLocaleDateString() : '—'}
                          </div>
                        </div>
                      </div>

                      {/* Account & Contact */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', background: '#ffffff', border: '1px solid var(--border-color)', padding: '1rem', borderRadius: '8px' }}>
                        <div>
                          <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Account
                          </label>
                          <div style={{ marginTop: '0.25rem' }}>
                            {opportunity.accountName ? (
                              <Link
                                to={`/crm/accounts?search=${encodeURIComponent(opportunity.accountName)}`}
                                style={{ color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                              >
                                <Building size={15} color="#d97706" />
                                <span>{opportunity.accountName}</span>
                                <ExternalLink size={12} />
                              </Link>
                            ) : '—'}
                          </div>
                        </div>

                        <div>
                          <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Primary Contact
                          </label>
                          <div style={{ marginTop: '0.25rem' }}>
                            {opportunity.contactName ? (
                              <Link
                                to={`/crm/contacts?search=${encodeURIComponent(opportunity.contactName)}`}
                                style={{ color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                              >
                                <User size={15} />
                                <span>{opportunity.contactName}</span>
                                <ExternalLink size={12} />
                              </Link>
                            ) : '—'}
                          </div>
                        </div>
                      </div>

                      {/* If Lost, show Loss Reason */}
                      {opportunity.status === 'Lost' && opportunity.lossReason && (
                        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '0.85rem 1rem', borderRadius: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: 'var(--danger-text)', fontWeight: 700, textTransform: 'uppercase' }}>
                            Loss Reason & Analysis
                          </span>
                          <p style={{ margin: '0.25rem 0 0', color: 'var(--danger-text)', fontSize: '0.9rem', fontWeight: 600 }}>
                            {opportunity.lossReason}
                          </p>
                        </div>
                      )}

                      {/* Provenance & Lead Link */}
                      {opportunity.originatingLeadId && (
                        <div>
                          <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Originating Lead
                          </label>
                          <div style={{ marginTop: '0.25rem' }}>
                            <Link
                              to={`/crm/leads/${opportunity.originatingLeadId}`}
                              style={{ color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                            >
                              <Layers size={14} />
                              <span>View Qualified Lead ({opportunity.originatingLeadNumber || 'Lead'})</span>
                              <ExternalLink size={12} />
                            </Link>
                          </div>
                        </div>
                      )}

                      {/* Description */}
                      {opportunity.description && (
                        <div>
                          <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Scope / Description
                          </label>
                          <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)', background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0', whiteSpace: 'pre-wrap', lineHeight: 1.5, fontSize: '0.875rem' }}>
                            {opportunity.description}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: QUOTATIONS (PHASE 5A) */}
              {activeTab === 'quotations' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        Opportunity Quotations & Commercial Governance
                      </h4>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                        Manage formal commercial offers, multi-revision versions, manager approvals, and client sharing records.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="crm-btn crm-btn-primary"
                      onClick={() => handleOpenQuotationModal('create')}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <Plus size={16} />
                      <span>New Quotation</span>
                    </button>
                  </div>

                  {/* Commercial Value Mismatch Notice */}
                  {opportunity.hasQuotationMismatch && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.65rem',
                      padding: '0.75rem 1rem',
                      background: '#fffbeb',
                      border: '1px solid #fde68a',
                      borderRadius: '8px',
                      color: '#92400e',
                      fontSize: '0.85rem'
                    }}>
                      <AlertTriangle size={18} style={{ flexShrink: 0, color: '#d97706' }} />
                      <div>
                        <strong>Commercial Value Mismatch Alert:</strong> Active quotation value is{' '}
                        <strong>{activeQuotation?.currency} {Number(activeQuotation?.amount).toLocaleString()}</strong>, which differs from this opportunity's estimated value of{' '}
                        <strong>{opportunity.currency || 'INR'} {Number(opportunity.estimatedValue).toLocaleString()}</strong>.
                      </div>
                    </div>
                  )}

                  {/* Active Quotation Section */}
                  {loadingQuotations ? (
                    <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      <RefreshCw size={20} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                      <span>Loading quotations...</span>
                    </div>
                  ) : activeQuotation ? (
                    <div style={{
                      padding: '1.25rem',
                      background: '#ffffff',
                      borderRadius: '10px',
                      border: '2px solid var(--accent-light)',
                      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                            <span style={{
                              background: 'var(--accent-primary)',
                              color: '#ffffff',
                              fontSize: '0.725rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '4px'
                            }}>
                              ACTIVE QUOTATION
                            </span>
                            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                              {activeQuotation.quotationNumber} ({activeQuotation.version})
                            </span>
                            <span style={{
                              fontSize: '0.725rem',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontWeight: 700,
                              background: activeQuotation.status === 'Approved' ? '#dcfce7' : (
                                activeQuotation.status === 'Shared' ? '#eff6ff' : (
                                  activeQuotation.status === 'Under Review' ? '#fef3c7' : (
                                    activeQuotation.status === 'Rejected' ? '#fee2e2' : '#f1f5f9'
                                  )
                                )
                              ),
                              color: activeQuotation.status === 'Approved' ? '#166534' : (
                                activeQuotation.status === 'Shared' ? '#1d4ed8' : (
                                  activeQuotation.status === 'Under Review' ? '#92400e' : (
                                    activeQuotation.status === 'Rejected' ? '#b91c1c' : '#475569'
                                  )
                                )
                              )
                            }}>
                              {activeQuotation.status}
                            </span>
                          </div>
                          <h4 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {activeQuotation.title}
                          </h4>
                        </div>

                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                            Quotation Total
                          </span>
                          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
                            {activeQuotation.currency} {Number(activeQuotation.amount).toLocaleString()}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', padding: '0.75rem 0', borderTop: '1px solid #f1f5f9', borderBottom: '1px solid #f1f5f9' }}>
                        <div>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Quotation Date</span>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{activeQuotation.quotationDate ? new Date(activeQuotation.quotationDate).toLocaleDateString() : '—'}</div>
                        </div>
                        <div>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Valid Until</span>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{activeQuotation.validUntilDate ? new Date(activeQuotation.validUntilDate).toLocaleDateString() : '—'}</div>
                        </div>
                        <div>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Document Reference</span>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{activeQuotation.documentName || 'No document attached'}</div>
                        </div>
                        <div>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Created By</span>
                          <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{activeQuotation.createdByName || 'System'}</div>
                        </div>
                      </div>

                      {activeQuotation.termsAndConditions && (
                        <div style={{ marginTop: '0.75rem' }}>
                          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Commercial Terms</span>
                          <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', background: '#f8fafc', padding: '0.5rem', borderRadius: '4px', marginTop: '0.25rem', whiteSpace: 'pre-wrap' }}>
                            {activeQuotation.termsAndConditions}
                          </div>
                        </div>
                      )}

                      {/* Approval / Rejection Metadata */}
                      {activeQuotation.approvedAt && (
                        <div style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '6px', fontSize: '0.8rem', color: '#166534', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <ShieldCheck size={16} />
                          <span>Approved by <strong>{activeQuotation.approvedByName || 'Sales Manager'}</strong> on {new Date(activeQuotation.approvedAt).toLocaleString()}</span>
                        </div>
                      )}

                      {activeQuotation.rejectionReason && (
                        <div style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px', fontSize: '0.8rem', color: '#b91c1c' }}>
                          <strong>Rejection Reason:</strong> {activeQuotation.rejectionReason}
                        </div>
                      )}

                      {/* Sharing Metadata */}
                      {activeQuotation.sentAt && (
                        <div style={{ marginTop: '0.75rem', padding: '0.65rem 0.85rem', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '6px', fontSize: '0.8rem', color: '#1e40af' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
                            <Send size={14} />
                            <span>Shared via <strong>{activeQuotation.sentMethod}</strong> to <strong>{activeQuotation.sentTo}</strong> on {new Date(activeQuotation.sentAt).toLocaleString()} by <strong>{activeQuotation.sentByName || 'User'}</strong></span>
                          </div>
                          {activeQuotation.sendingEvidence && (
                            <div style={{ fontSize: '0.75rem', color: '#3b82f6', marginTop: '0.2rem' }}>
                              Evidence / Ref: {activeQuotation.sendingEvidence}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Action Bar for Active Quotation */}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem', flexWrap: 'wrap' }}>
                        {activeQuotation.status === 'Draft' && (
                          <>
                            <button
                              type="button"
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              onClick={() => handleOpenQuotationModal('edit', activeQuotation)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                            >
                              <Edit3 size={14} />
                              <span>Edit Draft</span>
                            </button>
                            <button
                              type="button"
                              className="crm-btn crm-btn-primary crm-btn-sm"
                              onClick={() => handleSubmitQuotationForReview(activeQuotation.id)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                            >
                              <Send size={14} />
                              <span>Submit for Review</span>
                            </button>
                          </>
                        )}

                        {activeQuotation.status === 'Under Review' && (
                          <>
                            {isSalesManager ? (
                              <button
                                type="button"
                                className="crm-btn crm-btn-primary crm-btn-sm"
                                onClick={() => {
                                  setApprovalAction('approve');
                                  setRejectionReason('');
                                  setApprovalModalOpen(true);
                                }}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: '#16a34a', borderColor: '#16a34a' }}
                              >
                                <CheckSquare size={14} />
                                <span>Review & Approve / Reject</span>
                              </button>
                            ) : (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', alignSelf: 'center' }}>
                                Awaiting Sales Manager Review
                              </span>
                            )}
                            <button
                              type="button"
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              onClick={() => handleOpenQuotationModal('edit', activeQuotation)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                            >
                              <Edit3 size={14} />
                              <span>Edit</span>
                            </button>
                          </>
                        )}

                        {(activeQuotation.status === 'Approved' || activeQuotation.status === 'Shared') && (
                          <>
                            {activeQuotation.status === 'Approved' && (
                              <button
                                type="button"
                                className="crm-btn crm-btn-primary crm-btn-sm"
                                onClick={() => {
                                  setShareFormData({
                                    sentMethod: 'Email',
                                    sentTo: opportunity?.contactEmail || '',
                                    sendingEvidence: ''
                                  });
                                  setShareModalOpen(true);
                                }}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: '#2563eb', borderColor: '#2563eb' }}
                              >
                                <Send size={14} />
                                <span>Mark Shared with Client</span>
                              </button>
                            )}
                            <button
                              type="button"
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              onClick={() => handleOpenQuotationModal('revise', activeQuotation)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                              title="Create a new revision based on this quotation"
                            >
                              <Plus size={14} />
                              <span>New Revision</span>
                            </button>
                            <button
                              type="button"
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              onClick={() => handleOpenQuotationModal('edit', activeQuotation)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                              title="Editing an approved quote will reset status to Draft"
                            >
                              <Edit3 size={14} />
                              <span>Edit Quote</span>
                            </button>
                          </>
                        )}

                        {activeQuotation.status === 'Rejected' && (
                          <button
                            type="button"
                            className="crm-btn crm-btn-primary crm-btn-sm"
                            onClick={() => handleOpenQuotationModal('revise', activeQuotation)}
                            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                          >
                            <Plus size={14} />
                            <span>Create Revised Quotation</span>
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      textAlign: 'center',
                      padding: '2.5rem 1rem',
                      background: '#f8fafc',
                      borderRadius: '8px',
                      border: '1px dashed var(--border-color)',
                      color: 'var(--text-muted)'
                    }}>
                      <FileText size={36} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                      <p style={{ margin: '0 0 0.75rem', fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        No quotations created yet
                      </p>
                      <p style={{ margin: '0 0 1rem', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
                        Prepare and record a commercial quotation to formalize pricing and terms for this opportunity.
                      </p>
                      <button
                        type="button"
                        className="crm-btn crm-btn-primary crm-btn-sm"
                        onClick={() => handleOpenQuotationModal('create')}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                      >
                        <Plus size={15} />
                        <span>Create First Quotation</span>
                      </button>
                    </div>
                  )}

                  {/* Revision History Table */}
                  {quotations.length > 0 && (
                    <div style={{ marginTop: '0.5rem' }}>
                      <h5 style={{ margin: '0 0 0.65rem', fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        Quotation Revision History ({quotations.length})
                      </h5>
                      <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem', textAlign: 'left' }}>
                          <thead style={{ background: '#f8fafc', borderBottom: '1px solid var(--border-color)' }}>
                            <tr>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Quote #</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Rev</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Status</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Amount</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Date</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Valid Until</th>
                              <th style={{ padding: '0.65rem 0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Actions</th>
                            </tr>
                          </thead>
                          <tbody>
                            {quotations.map(q => (
                              <tr
                                key={q.id}
                                style={{
                                  borderBottom: '1px solid #f1f5f9',
                                  background: q.isActive ? '#f0fdf4' : '#ffffff'
                                }}
                              >
                                <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>
                                  {q.quotationNumber}
                                  {q.isActive && (
                                    <span style={{ marginLeft: '0.35rem', fontSize: '0.65rem', background: '#16a34a', color: '#ffffff', padding: '1px 4px', borderRadius: '3px' }}>
                                      Active
                                    </span>
                                  )}
                                </td>
                                <td style={{ padding: '0.65rem 0.75rem' }}>{q.version}</td>
                                <td style={{ padding: '0.65rem 0.75rem' }}>
                                  <span style={{
                                    fontSize: '0.725rem',
                                    padding: '1px 6px',
                                    borderRadius: '4px',
                                    fontWeight: 600,
                                    background: q.status === 'Approved' ? '#dcfce7' : (
                                      q.status === 'Shared' ? '#eff6ff' : (
                                        q.status === 'Under Review' ? '#fef3c7' : (
                                          q.status === 'Rejected' ? '#fee2e2' : '#f1f5f9'
                                        )
                                      )
                                    ),
                                    color: q.status === 'Approved' ? '#166534' : (
                                      q.status === 'Shared' ? '#1d4ed8' : (
                                        q.status === 'Under Review' ? '#92400e' : (
                                          q.status === 'Rejected' ? '#b91c1c' : '#475569'
                                        )
                                      )
                                    )
                                  }}>
                                    {q.status}
                                  </span>
                                </td>
                                <td style={{ padding: '0.65rem 0.75rem', fontWeight: 600 }}>
                                  {q.currency} {Number(q.amount).toLocaleString()}
                                </td>
                                <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-secondary)' }}>
                                  {q.quotationDate ? new Date(q.quotationDate).toLocaleDateString() : '—'}
                                </td>
                                <td style={{ padding: '0.65rem 0.75rem', color: 'var(--text-secondary)' }}>
                                  {q.validUntilDate ? new Date(q.validUntilDate).toLocaleDateString() : '—'}
                                </td>
                                <td style={{ padding: '0.65rem 0.75rem' }}>
                                  <button
                                    type="button"
                                    className="crm-btn crm-btn-secondary crm-btn-sm"
                                    onClick={() => handleOpenQuotationModal('edit', q)}
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
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: REQUIREMENT ROUTING (PHASE 4B) */}
              {activeTab === 'routing' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        Multi-Requirement Workstream Routing
                      </h4>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                        Route selected commercial requirements to downstream operational systems idempotently.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="crm-btn crm-btn-primary"
                      onClick={handleRouteRequirements}
                      disabled={routingRequirements}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <GitBranch size={16} />
                      <span>{routingRequirements ? 'Routing...' : 'Route to Workstreams'}</span>
                    </button>
                  </div>

                  {/* Active Requirement Types Pill Bar */}
                  <div style={{ background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                      Selected Requirements:
                    </span>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
                      {opportunity.requirementTypes && opportunity.requirementTypes.length > 0 ? (
                        opportunity.requirementTypes.map(rt => (
                          <span
                            key={rt}
                            style={{
                              background: '#eff6ff',
                              color: '#1d4ed8',
                              border: '1px solid #bfdbfe',
                              padding: '3px 10px',
                              borderRadius: '12px',
                              fontSize: '0.8rem',
                              fontWeight: 600
                            }}
                          >
                            ✓ {rt}
                          </span>
                        ))
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No requirements tagged</span>
                      )}
                    </div>
                  </div>

                  {/* Downstream Safeguard Notice */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.65rem 0.85rem',
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '6px',
                    color: '#15803d',
                    fontSize: '0.8rem'
                  }}>
                    <ShieldCheck size={16} />
                    <span>
                      <strong>Enterprise Downstream Safeguard:</strong> Workstream routing creates draft operational links. Invoices, charges, or lab testing runs are strictly NOT auto-generated.
                    </span>
                  </div>

                  {/* Routed Workstreams List */}
                  <div>
                    <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      Routed Downstream Workstreams ({workstreams.length})
                    </h5>

                    {loadingWorkstreams ? (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                        <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                        <span>Loading workstreams...</span>
                      </div>
                    ) : workstreams.length === 0 ? (
                      <div style={{
                        textAlign: 'center',
                        padding: '2.5rem 1rem',
                        background: '#f8fafc',
                        borderRadius: '8px',
                        border: '1px dashed var(--border-color)',
                        color: 'var(--text-muted)'
                      }}>
                        <GitBranch size={32} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                        <p style={{ margin: 0, fontSize: '0.85rem' }}>
                          No workstreams routed yet. Click <strong>Route to Workstreams</strong> above to dispatch requirements.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {workstreams.map((ws) => (
                          <div
                            key={ws.id}
                            style={{
                              padding: '1rem',
                              border: '1px solid var(--border-color)',
                              borderRadius: '8px',
                              background: '#ffffff',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                                <span style={{
                                  fontSize: '0.725rem',
                                  fontWeight: 700,
                                  textTransform: 'uppercase',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  background: ws.type === 'consulting' ? '#e0e7ff' : (ws.type === 'sample_testing' ? '#fef3c7' : '#ecfdf5'),
                                  color: ws.type === 'consulting' ? '#3730a3' : (ws.type === 'sample_testing' ? '#92400e' : '#065f46')
                                }}>
                                  {ws.type.replace('_', ' ')}
                                </span>
                                <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                                  {ws.recordNumber}
                                </strong>
                              </div>
                              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                {ws.title}
                              </div>
                            </div>

                            <div style={{ textAlign: 'right' }}>
                              <span style={{
                                fontSize: '0.75rem',
                                fontWeight: 700,
                                padding: '2px 8px',
                                borderRadius: '4px',
                                background: '#f1f5f9',
                                color: '#475569'
                              }}>
                                Status: {ws.status}
                              </span>
                              {ws.details?.agreedFee !== undefined && ws.details.agreedFee > 0 && (
                                <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                                  Agreed Fee: INR {Number(ws.details.agreedFee).toLocaleString()}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 3: MILESTONES (PHASE 4C) */}
              {activeTab === 'milestones' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                        Opportunity Milestones & Governance
                      </h4>
                      <p style={{ margin: '0.2rem 0 0', fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                        Track critical deliverables, due dates, and operational completions (Asia/Kolkata).
                      </p>
                    </div>

                    {!isAddingMilestone && (
                      <button
                        type="button"
                        className="crm-btn crm-btn-primary crm-btn-sm"
                        onClick={() => setIsAddingMilestone(true)}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                      >
                        <Plus size={15} />
                        <span>Add Milestone</span>
                      </button>
                    )}
                  </div>

                  {/* Add Milestone Form */}
                  {isAddingMilestone && (
                    <form
                      onSubmit={handleCreateMilestone}
                      style={{
                        padding: '1.15rem',
                        background: '#f8fafc',
                        borderRadius: '8px',
                        border: '1px solid var(--accent-light)'
                      }}
                    >
                      <h5 style={{ margin: '0 0 0.75rem', fontSize: '0.875rem', fontWeight: 700 }}>
                        Create New Milestone
                      </h5>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                            Milestone Title *
                          </label>
                          <input
                            type="text"
                            className="form-control"
                            placeholder="e.g. Laboratory Feedstock Slurry Characterization"
                            value={milestoneFormData.title}
                            onChange={(e) => setMilestoneFormData({ ...milestoneFormData, title: e.target.value })}
                            required
                          />
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                          <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                              Due Date (IST)
                            </label>
                            <input
                              type="date"
                              className="form-control"
                              value={milestoneFormData.dueDate}
                              onChange={(e) => setMilestoneFormData({ ...milestoneFormData, dueDate: e.target.value })}
                            />
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                              Assignee
                            </label>
                            <select
                              className="form-control"
                              value={milestoneFormData.assignedToUserId}
                              onChange={(e) => setMilestoneFormData({ ...milestoneFormData, assignedToUserId: e.target.value })}
                            >
                              <option value="">Unassigned</option>
                              {assignees.map(a => (
                                <option key={a.id} value={a.id}>{a.name} ({a.username})</option>
                              ))}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                            Description & Deliverables
                          </label>
                          <textarea
                            rows={2}
                            className="form-control"
                            placeholder="Deliverable details..."
                            value={milestoneFormData.description}
                            onChange={(e) => setMilestoneFormData({ ...milestoneFormData, description: e.target.value })}
                          />
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.25rem' }}>
                          <button
                            type="button"
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            onClick={() => setIsAddingMilestone(false)}
                            disabled={savingMilestone}
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            className="crm-btn crm-btn-primary crm-btn-sm"
                            disabled={savingMilestone}
                          >
                            {savingMilestone ? 'Creating...' : 'Create Milestone'}
                          </button>
                        </div>
                      </div>
                    </form>
                  )}

                  {/* Milestones List */}
                  {loadingMilestones ? (
                    <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                      <span>Loading milestones...</span>
                    </div>
                  ) : milestones.length === 0 ? (
                    <div style={{
                      textAlign: 'center',
                      padding: '2.5rem 1rem',
                      background: '#f8fafc',
                      borderRadius: '8px',
                      border: '1px dashed var(--border-color)',
                      color: 'var(--text-muted)'
                    }}>
                      <Clock size={32} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                      <p style={{ margin: 0, fontSize: '0.85rem' }}>
                        No milestones created yet. Add deliverables to track project progress.
                      </p>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                      {milestones.map((m) => (
                        <div
                          key={m.id}
                          style={{
                            padding: '1rem',
                            borderRadius: '8px',
                            border: m.isOverdue ? '1px solid #fca5a5' : '1px solid var(--border-color)',
                            background: m.isOverdue ? '#fff5f5' : '#ffffff',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '1rem'
                          }}
                        >
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                              <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                                {m.milestoneId}
                              </strong>
                              {/* Status Badge */}
                              <span style={{
                                fontSize: '0.725rem',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                fontWeight: 700,
                                background: m.status === 'Completed' ? '#dcfce7' : (m.status === 'Cancelled' ? '#f1f5f9' : '#eff6ff'),
                                color: m.status === 'Completed' ? '#166534' : (m.status === 'Cancelled' ? '#475569' : '#1d4ed8')
                              }}>
                                {m.status}
                              </span>

                              {/* Overdue Badge */}
                              {m.isOverdue && (
                                <span style={{
                                  fontSize: '0.7rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  fontWeight: 700,
                                  background: '#fee2e2',
                                  color: '#b91c1c'
                                }}>
                                  OVERDUE
                                </span>
                              )}
                            </div>

                            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {m.title}
                            </div>

                            {m.description && (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                                {m.description}
                              </div>
                            )}

                            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                              {m.dueDate && (
                                <span>Due: <strong>{new Date(m.dueDate).toLocaleDateString()}</strong></span>
                              )}
                              {m.assignedToName && (
                                <span>Assignee: <strong>{m.assignedToName}</strong></span>
                              )}
                            </div>
                          </div>

                          {/* Milestone Quick Actions */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            {m.status !== 'Completed' && (
                              <button
                                type="button"
                                className="crm-btn crm-btn-secondary crm-btn-sm"
                                onClick={() => handleMilestoneStatus(m.id, 'Completed')}
                                title="Mark Complete"
                                style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
                              >
                                <Check size={14} />
                                <span>Complete</span>
                              </button>
                            )}

                            {m.status === 'Completed' && (
                              <button
                                type="button"
                                className="crm-btn crm-btn-secondary crm-btn-sm"
                                onClick={() => handleMilestoneStatus(m.id, 'In Progress')}
                                title="Reopen to In Progress"
                              >
                                Reopen
                              </button>
                            )}

                            <button
                              type="button"
                              onClick={() => handleDeleteMilestone(m.id)}
                              style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                              title="Delete Milestone"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: '0.85rem 1.75rem',
          borderTop: '1px solid var(--border-color)',
          background: '#f8fafc',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center'
        }}>
          <button type="button" className="crm-btn crm-btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      {/* Stage Transition Modal */}
      {isStageModalOpen && (
        <OpportunityStageModal
          isOpen={isStageModalOpen}
          onClose={() => setIsStageModalOpen(false)}
          opportunity={opportunity}
          onSuccess={(updated) => {
            setOpportunity(updated);
            if (onOpportunityUpdated) onOpportunityUpdated(updated);
          }}
        />
      )}

      {/* Sub-Modal 1: Quotation Modal (Create / Edit / Revise) */}
      {quotationModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={() => setQuotationModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '580px', width: '92%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff', boxShadow: 'var(--modal-shadow)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={20} color="var(--accent-primary)" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                  {quotationModalMode === 'create' ? 'Create New Quotation' : (quotationModalMode === 'revise' ? `Revise Quotation (${selectedQuotation?.version} → v${(selectedQuotation?.revisionNumber || 1) + 1})` : `Edit Quotation (${selectedQuotation?.version})`)}
                </h3>
              </div>
              <button type="button" onClick={() => setQuotationModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveQuotation} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Quotation Title *
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Commercial Proposal for Biogas Upgrade Plant"
                  value={quotationFormData.title}
                  onChange={(e) => setQuotationFormData({ ...quotationFormData, title: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                    Currency *
                  </label>
                  <select
                    className="form-control"
                    value={quotationFormData.currency}
                    onChange={(e) => setQuotationFormData({ ...quotationFormData, currency: e.target.value })}
                    required
                  >
                    {APPROVED_CURRENCIES.map(curr => (
                      <option key={curr} value={curr}>{curr}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                    Total Commercial Amount *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    className="form-control"
                    placeholder="0.00"
                    value={quotationFormData.amount}
                    onChange={(e) => setQuotationFormData({ ...quotationFormData, amount: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                    Quotation Date
                  </label>
                  <input
                    type="date"
                    className="form-control"
                    value={quotationFormData.quotationDate}
                    onChange={(e) => setQuotationFormData({ ...quotationFormData, quotationDate: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                    Valid Until Date
                  </label>
                  <input
                    type="date"
                    className="form-control"
                    value={quotationFormData.validUntilDate}
                    onChange={(e) => setQuotationFormData({ ...quotationFormData, validUntilDate: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Document / Proposal Reference
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. REVY_Proposal_Biogas_2026_v1.pdf"
                  value={quotationFormData.documentName}
                  onChange={(e) => setQuotationFormData({ ...quotationFormData, documentName: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Commercial Terms & Conditions
                </label>
                <textarea
                  rows={2}
                  className="form-control"
                  placeholder="Payment milestones, validity, warranty..."
                  value={quotationFormData.termsAndConditions}
                  onChange={(e) => setQuotationFormData({ ...quotationFormData, termsAndConditions: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Internal Notes
                </label>
                <textarea
                  rows={2}
                  className="form-control"
                  placeholder="Internal review notes or pricing assumptions..."
                  value={quotationFormData.notes}
                  onChange={(e) => setQuotationFormData({ ...quotationFormData, notes: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary crm-btn-sm"
                  onClick={() => setQuotationModalOpen(false)}
                  disabled={savingQuotation}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-primary crm-btn-sm"
                  disabled={savingQuotation}
                >
                  {savingQuotation ? 'Saving...' : (quotationModalMode === 'create' ? 'Create Quotation' : (quotationModalMode === 'revise' ? 'Create Revision' : 'Update Quotation'))}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sub-Modal 2: Approval Modal (Approve / Reject) */}
      {approvalModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={() => setApprovalModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '480px', width: '90%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff', boxShadow: 'var(--modal-shadow)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckSquare size={20} color="var(--accent-primary)" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                  Review Quotation ({activeQuotation?.quotationNumber} {activeQuotation?.version})
                </h3>
              </div>
              <button type="button" onClick={() => setApprovalModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleApproveOrRejectQuotation} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  Manager Decision *
                </label>
                <div style={{ display: 'flex', gap: '1rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontWeight: 600, color: '#166534' }}>
                    <input
                      type="radio"
                      name="approvalAction"
                      value="approve"
                      checked={approvalAction === 'approve'}
                      onChange={() => setApprovalAction('approve')}
                    />
                    Approve Quotation
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontWeight: 600, color: '#b91c1c' }}>
                    <input
                      type="radio"
                      name="approvalAction"
                      value="reject"
                      checked={approvalAction === 'reject'}
                      onChange={() => setApprovalAction('reject')}
                    />
                    Reject Quotation
                  </label>
                </div>
              </div>

              {approvalAction === 'reject' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--danger-text)', marginBottom: '0.25rem' }}>
                    Rejection Reason *
                  </label>
                  <textarea
                    rows={3}
                    className="form-control"
                    placeholder="Specify the reason for rejection (pricing adjustment needed, incorrect terms, etc.)..."
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    required
                  />
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary crm-btn-sm"
                  onClick={() => setApprovalModalOpen(false)}
                  disabled={processingApproval}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={`crm-btn crm-btn-sm ${approvalAction === 'approve' ? 'crm-btn-primary' : 'crm-btn-secondary'}`}
                  style={approvalAction === 'approve' ? { background: '#16a34a', borderColor: '#16a34a' } : { color: '#b91c1c', borderColor: '#fca5a5', background: '#fee2e2' }}
                  disabled={processingApproval}
                >
                  {processingApproval ? 'Processing...' : (approvalAction === 'approve' ? 'Confirm Approval' : 'Confirm Rejection')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sub-Modal 3: Share Modal (Mark Quotation Shared) */}
      {shareModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={() => setShareModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '480px', width: '90%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff', boxShadow: 'var(--modal-shadow)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Send size={20} color="var(--accent-primary)" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                  Record External Quotation Sharing
                </h3>
              </div>
              <button type="button" onClick={() => setShareModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleShareQuotation} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Delivery / Sharing Method *
                </label>
                <select
                  className="form-control"
                  value={shareFormData.sentMethod}
                  onChange={(e) => setShareFormData({ ...shareFormData, sentMethod: e.target.value })}
                  required
                >
                  <option value="Email">Email</option>
                  <option value="WhatsApp">WhatsApp</option>
                  <option value="Courier">Courier / Physical Delivery</option>
                  <option value="Hand Delivery">Hand Delivery</option>
                  <option value="Client Portal">Client Portal</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Recipient (Email / Phone / Contact Name) *
                </label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. client@example.com or procurement manager"
                  value={shareFormData.sentTo}
                  onChange={(e) => setShareFormData({ ...shareFormData, sentTo: e.target.value })}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Sharing Evidence / Audit Reference
                </label>
                <textarea
                  rows={2}
                  className="form-control"
                  placeholder="e.g. Sent via Gmail from sales@revy.com with subject 'REVY Proposal QT-00001'"
                  value={shareFormData.sendingEvidence}
                  onChange={(e) => setShareFormData({ ...shareFormData, sendingEvidence: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary crm-btn-sm"
                  onClick={() => setShareModalOpen(false)}
                  disabled={processingShare}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-primary crm-btn-sm"
                  disabled={processingShare}
                >
                  {processingShare ? 'Recording...' : 'Mark as Shared'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sub-Modal 4: Reopen Deal Modal */}
      {reopenModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1300 }} onClick={() => setReopenModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '480px', width: '90%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff', boxShadow: 'var(--modal-shadow)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <RotateCcw size={20} color="#b45309" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#92400e' }}>
                  Reopen Opportunity
                </h3>
              </div>
              <button type="button" onClick={() => setReopenModalOpen(false)} style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: 'var(--text-muted)' }}>
                ✕
              </button>
            </div>

            <form onSubmit={handleReopenOpportunity} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div style={{ padding: '0.65rem 0.85rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '6px', fontSize: '0.8rem', color: '#92400e' }}>
                <strong>Reopening Controls:</strong> Reopening resets the opportunity outcome to <strong>Open</strong>, clears the close date and loss reason, and logs an immutable audit event.
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Return Opportunity to Stage *
                </label>
                <select
                  className="form-control"
                  value={reopenStage}
                  onChange={(e) => setReopenStage(e.target.value)}
                  required
                >
                  {STAGES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                  Mandatory Reopening Justification *
                </label>
                <textarea
                  rows={3}
                  className="form-control"
                  placeholder="Provide explicit business rationale for reopening this closed deal (e.g. Client requested revised scope and budget)..."
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                <button
                  type="button"
                  className="crm-btn crm-btn-secondary crm-btn-sm"
                  onClick={() => setReopenModalOpen(false)}
                  disabled={processingReopen}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-primary crm-btn-sm"
                  style={{ background: '#b45309', borderColor: '#b45309' }}
                  disabled={processingReopen}
                >
                  {processingReopen ? 'Reopening...' : 'Confirm Reopen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
