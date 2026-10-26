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
  Check
} from 'lucide-react';
import crmService from '../../../services/crmService';
import OpportunityStageModal from './OpportunityStageModal';

const STAGES = ['Qualify', 'Develop', 'Propose', 'Close'];
const BUSINESS_AREAS = ['Biogas', 'Wastewater Treatment (WWT)', 'R&D Lab', 'Other'];

export default function OpportunityDetailModal({
  isOpen,
  onClose,
  opportunityId,
  onOpportunityUpdated
}) {
  const [activeTab, setActiveTab] = useState('overview'); // overview, routing, milestones
  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Stage modal state
  const [isStageModalOpen, setIsStageModalOpen] = useState(false);

  // Edit Opportunity Overview State
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: '',
    estimatedValue: '',
    expectedCloseDate: '',
    businessArea: '',
    description: ''
  });
  const [savingOverview, setSavingOverview] = useState(false);

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
          estimatedValue: opp.estimatedValue !== null && opp.estimatedValue !== undefined ? opp.estimatedValue : '',
          expectedCloseDate: opp.expectedCloseDate ? opp.expectedCloseDate.split('T')[0] : '',
          businessArea: opp.businessArea || 'Biogas',
          description: opp.description || ''
        });
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load opportunity.');
    } finally {
      setLoading(false);
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
      fetchWorkstreams();
      fetchMilestones();
      setActiveTab('overview');
      setIsEditing(false);
      setRoutingSuccessMsg(null);
    }
  }, [isOpen, opportunityId, fetchOpportunityDetails, fetchWorkstreams, fetchMilestones]);

  if (!isOpen) return null;

  // Handle Save Overview
  const handleSaveOverview = async (e) => {
    e.preventDefault();
    setSavingOverview(true);
    setError(null);
    try {
      const payload = {
        name: editFormData.name.trim(),
        estimatedValue: editFormData.estimatedValue ? Number(editFormData.estimatedValue) : null,
        expectedCloseDate: editFormData.expectedCloseDate || null,
        businessArea: editFormData.businessArea || null,
        description: editFormData.description ? editFormData.description.trim() : null
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

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                            Estimated Value (INR)
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

                      {/* Top Metric Cards */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
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

              {/* TAB 2: REQUIREMENT ROUTING (PHASE 4B) */}
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
    </div>
  );
}
