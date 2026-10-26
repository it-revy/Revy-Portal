import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Briefcase,
  Search,
  RefreshCw,
  Building,
  User,
  X,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Kanban,
  List,
  Clock,
  GitBranch,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import crmService from '../services/crmService';
import OpportunityDetailModal from '../modules/crm/components/OpportunityDetailModal';
import OpportunityStageModal from '../modules/crm/components/OpportunityStageModal';

const STAGES = ['Qualify', 'Develop', 'Propose', 'Close'];
const BUSINESS_AREAS = ['Biogas', 'Wastewater Treatment (WWT)', 'R&D Lab', 'Other'];

export default function CrmOpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const urlSearch = searchParams.get('search') || '';
  const urlView = searchParams.get('view') || 'open';
  const urlMode = searchParams.get('mode') || 'kanban'; // 'kanban' or 'table'

  // Workspace View Mode: 'kanban' or 'table'
  const [viewMode, setViewMode] = useState(urlMode);

  // Filter states
  const [search, setSearch] = useState(urlSearch);
  const [presetView, setPresetView] = useState(urlView); // 'all', 'open', 'my', 'won', 'lost'
  const [stageFilter, setStageFilter] = useState('ALL');
  const [businessAreaFilter, setBusinessAreaFilter] = useState('ALL');

  // Data states
  const [opportunities, setOpportunities] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Pipeline summary KPI metrics
  const [pipelineSummary, setPipelineSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modals state
  const [detailModalOppId, setDetailModalOppId] = useState(null);
  const [stageModalOpp, setStageModalOpp] = useState(null);

  // Fetch KPI Summary
  const fetchSummary = useCallback(async () => {
    try {
      const res = await crmService.getPipelineSummary();
      if (res.data?.success) {
        setPipelineSummary(res.data);
      }
    } catch (err) {
      console.error('Failed to load pipeline summary:', err);
    }
  }, []);

  // Fetch Opportunities
  const fetchOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        limit: viewMode === 'kanban' ? 100 : pageSize,
        offset: viewMode === 'kanban' ? 0 : (page - 1) * pageSize
      };

      if (search.trim()) params.search = search.trim();
      if (presetView !== 'all') params.view = presetView;
      if (stageFilter !== 'ALL') params.stage = stageFilter;
      if (businessAreaFilter !== 'ALL') params.businessArea = businessAreaFilter;

      const res = await crmService.getOpportunities(params);
      if (res.data?.success) {
        setOpportunities(res.data.opportunities || []);
        setTotalCount(res.data.totalCount || res.data.count || (res.data.opportunities || []).length);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load opportunities. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [page, search, presetView, stageFilter, businessAreaFilter, viewMode]);

  useEffect(() => {
    fetchOpportunities();
    fetchSummary();
  }, [fetchOpportunities, fetchSummary]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchOpportunities();
  };

  const handleClearSearch = () => {
    setSearch('');
    setPage(1);
  };

  const handleOpportunityUpdated = (updatedOpp) => {
    fetchOpportunities();
    fetchSummary();
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  // Helper for status badge
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
            fontSize: '0.725rem',
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
            fontSize: '0.725rem',
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
            fontSize: '0.725rem',
            fontWeight: 700,
            textTransform: 'uppercase'
          }}>
            Open
          </span>
        );
    }
  };

  // Group opportunities by stage for Kanban View
  const kanbanColumns = STAGES.map(stage => {
    const oppsInStage = opportunities.filter(o => o.stage === stage);
    const stageSum = oppsInStage
      .filter(o => o.status === 'Open')
      .reduce((acc, curr) => acc + (Number(curr.estimatedValue) || 0), 0);
    return {
      stage,
      opportunities: oppsInStage,
      totalValue: stageSum
    };
  });

  return (
    <div className="crm-page-container">
      {/* Page Header Command Bar */}
      <div className="crm-page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            <Link to="/crm/dashboard" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>CRM</Link>
            <span>/</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Opportunity Pipeline</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
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
              <Briefcase size={22} />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Opportunity Pipeline Workspace
              </h1>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Visual Kanban progression, multi-requirement routing, and deliverable milestone governance
              </p>
            </div>
          </div>
        </div>

        <div className="crm-page-header-actions" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* View Mode Toggle */}
          <div style={{
            display: 'flex',
            background: '#f1f5f9',
            padding: '3px',
            borderRadius: '8px',
            border: '1px solid var(--border-color)'
          }}>
            <button
              type="button"
              onClick={() => {
                setViewMode('kanban');
                setSearchParams({ mode: 'kanban', view: presetView });
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                background: viewMode === 'kanban' ? '#ffffff' : 'transparent',
                color: viewMode === 'kanban' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: 'pointer',
                boxShadow: viewMode === 'kanban' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none'
              }}
            >
              <Kanban size={15} />
              <span>Kanban</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setViewMode('table');
                setSearchParams({ mode: 'table', view: presetView });
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '6px 12px',
                borderRadius: '6px',
                border: 'none',
                background: viewMode === 'table' ? '#ffffff' : 'transparent',
                color: viewMode === 'table' ? 'var(--accent-primary)' : 'var(--text-secondary)',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: 'pointer',
                boxShadow: viewMode === 'table' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none'
              }}
            >
              <List size={15} />
              <span>Table</span>
            </button>
          </div>

          <button
            onClick={() => {
              fetchOpportunities();
              fetchSummary();
            }}
            className="crm-btn crm-btn-secondary"
            title="Refresh Pipeline"
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Authoritative Pipeline KPI Summary Banner */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '1.25rem'
      }}>
        {/* Open Value */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Open Pipeline Value
            </span>
            <TrendingUp size={16} color="var(--accent-primary)" />
          </div>
          <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            INR {(pipelineSummary?.totalOpenValue || 0).toLocaleString()}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {pipelineSummary?.byStatus?.Open || 0} active open opportunities
          </span>
        </div>

        {/* Total Opportunities */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Total Opportunities
            </span>
            <Briefcase size={16} color="#d97706" />
          </div>
          <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {pipelineSummary?.totalCount || 0}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            All pipeline entries generated from Leads
          </span>
        </div>

        {/* Closed Won */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--success-text)', textTransform: 'uppercase' }}>
              Closed Won
            </span>
            <CheckCircle2 size={16} color="var(--success)" />
          </div>
          <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--success)' }}>
            {pipelineSummary?.byStatus?.Won || 0}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Won commercial deals
          </span>
        </div>

        {/* Closed Lost */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--danger-text)', textTransform: 'uppercase' }}>
              Closed Lost
            </span>
            <XCircle size={16} color="var(--danger)" />
          </div>
          <div style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--danger)' }}>
            {pipelineSummary?.byStatus?.Lost || 0}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Audit-tracked loss reasons
          </span>
        </div>
      </div>

      {/* Toolbar & Filters */}
      <div className="crm-toolbar" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group" style={{ flex: 1, minWidth: '240px' }}>
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by ID, Opportunity Name, Account..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            {search && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="crm-search-clear-btn"
                title="Clear search"
              >
                <X size={15} />
              </button>
            )}
          </div>
          <button type="submit" className="crm-btn crm-btn-secondary crm-btn-sm" style={{ height: '38px' }}>
            Search
          </button>
        </form>

        {/* Preset View Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>View:</span>
          <select
            value={presetView}
            onChange={(e) => {
              setPresetView(e.target.value);
              setPage(1);
            }}
            className="form-control"
            style={{ minWidth: '120px', height: '38px', fontSize: '0.825rem' }}
          >
            <option value="open">Open Pipeline</option>
            <option value="all">All Opportunities</option>
            <option value="my">My Assigned</option>
            <option value="won">Closed Won</option>
            <option value="lost">Closed Lost</option>
          </select>
        </div>

        {/* Stage Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>Stage:</span>
          <select
            value={stageFilter}
            onChange={(e) => {
              setStageFilter(e.target.value);
              setPage(1);
            }}
            className="form-control"
            style={{ minWidth: '120px', height: '38px', fontSize: '0.825rem' }}
          >
            <option value="ALL">All Stages</option>
            {STAGES.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        {/* Business Area Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.825rem', color: 'var(--text-muted)' }}>Area:</span>
          <select
            value={businessAreaFilter}
            onChange={(e) => {
              setBusinessAreaFilter(e.target.value);
              setPage(1);
            }}
            className="form-control"
            style={{ minWidth: '130px', height: '38px', fontSize: '0.825rem' }}
          >
            <option value="ALL">All Areas</option>
            {BUSINESS_AREAS.map(ba => (
              <option key={ba} value={ba}>{ba}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div style={{
          padding: '0.85rem 1rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--danger-text)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* VIEW MODE 1: KANBAN BOARD */}
      {viewMode === 'kanban' ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
          minHeight: '520px',
          alignItems: 'start'
        }}>
          {kanbanColumns.map(({ stage, opportunities: colOpps, totalValue }) => (
            <div
              key={stage}
              style={{
                background: '#f8fafc',
                borderRadius: '10px',
                border: '1px solid var(--border-color)',
                display: 'flex',
                flexDirection: 'column',
                maxHeight: 'calc(100vh - 280px)',
                overflow: 'hidden'
              }}
            >
              {/* Column Header */}
              <div style={{
                padding: '0.85rem 1rem',
                borderBottom: '2px solid var(--border-color)',
                background: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: stage === 'Close' ? 'var(--success)' : 'var(--accent-primary)'
                    }} />
                    <strong style={{ fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                      {stage}
                    </strong>
                    <span style={{
                      fontSize: '0.75rem',
                      background: '#f1f5f9',
                      padding: '2px 7px',
                      borderRadius: '12px',
                      fontWeight: 700,
                      color: 'var(--text-secondary)'
                    }}>
                      {colOpps.length}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    INR {totalValue.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Column Cards Container */}
              <div style={{
                padding: '0.75rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                overflowY: 'auto',
                flex: 1
              }}>
                {colOpps.length === 0 ? (
                  <div style={{
                    padding: '2rem 1rem',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: '0.825rem'
                  }}>
                    No opportunities in {stage}
                  </div>
                ) : (
                  colOpps.map(opp => (
                    <div
                      key={opp.id}
                      onClick={() => setDetailModalOppId(opp.id)}
                      style={{
                        background: '#ffffff',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        padding: '0.85rem',
                        boxShadow: 'var(--card-shadow)',
                        cursor: 'pointer',
                        transition: 'transform 0.15s ease, box-shadow 0.15s ease'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0,0,0,0.1)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = 'var(--card-shadow)';
                      }}
                    >
                      {/* Top Bar with ID and Status */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                          {opp.opportunityId}
                        </span>
                        {getStatusBadge(opp.status)}
                      </div>

                      {/* Opportunity Name */}
                      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.4rem', lineHeight: 1.3 }}>
                        {opp.name}
                      </div>

                      {/* Account & Contact */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem', marginBottom: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {opp.accountName && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <Building size={13} color="#d97706" />
                            <span style={{ fontWeight: 500 }}>{opp.accountName}</span>
                          </div>
                        )}
                        {opp.contactName && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <User size={13} color="var(--accent-primary)" />
                            <span>{opp.contactName}</span>
                          </div>
                        )}
                      </div>

                      {/* Requirement Tags */}
                      {opp.requirementTypes && opp.requirementTypes.length > 0 && (
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                          {opp.requirementTypes.map(rt => (
                            <span key={rt} style={{ fontSize: '0.675rem', background: '#f1f5f9', color: '#475569', padding: '1px 5px', borderRadius: '3px' }}>
                              {rt}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Bottom Footer: Value and Indicators */}
                      <div style={{
                        borderTop: '1px solid #f1f5f9',
                        paddingTop: '0.5rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#0f172a' }}>
                          {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                            `INR ${Number(opp.estimatedValue).toLocaleString()}`
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400, fontSize: '0.75rem' }}>Not specified</span>
                          )}
                        </div>

                        {/* Counts (Milestones & Workstreams) */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {opp.milestoneCount > 0 && (
                            <span title={`${opp.milestoneCount} Milestones`} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                              <Clock size={12} />
                              <span>{opp.milestoneCount}</span>
                            </span>
                          )}
                          {opp.workstreamCount > 0 && (
                            <span title={`${opp.workstreamCount} Workstreams`} style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                              <GitBranch size={12} />
                              <span>{opp.workstreamCount}</span>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Stage Action Button */}
                      <div style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setStageModalOpp(opp);
                          }}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          style={{ fontSize: '0.75rem', padding: '3px 8px', height: 'auto' }}
                        >
                          <TrendingUp size={12} style={{ marginRight: '4px' }} />
                          <span>Advance</span>
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* VIEW MODE 2: TABLE VIEW */
        <div className="glass-panel" style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
          <div className="table-responsive">
            <table className="crm-table">
              <thead>
                <tr>
                  <th style={{ width: '130px' }}>Opportunity ID</th>
                  <th style={{ minWidth: '220px' }}>Opportunity Name</th>
                  <th style={{ minWidth: '180px' }}>Account</th>
                  <th style={{ minWidth: '160px' }}>Primary Contact</th>
                  <th style={{ width: '120px' }}>Stage</th>
                  <th style={{ width: '130px' }}>Estimated Value</th>
                  <th style={{ width: '100px' }}>Status</th>
                  <th style={{ width: '100px' }}>Governance</th>
                  <th style={{ width: '110px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)' }}>
                      <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
                      <span>Loading opportunities...</span>
                    </td>
                  </tr>
                ) : opportunities.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                      <Briefcase size={36} color="#cbd5e1" style={{ margin: '0 auto 0.75rem', display: 'block' }} />
                      <h4 style={{ margin: '0 0 0.35rem', color: 'var(--text-primary)', fontSize: '1rem' }}>No Opportunities Found</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem' }}>
                        {search.trim() || stageFilter !== 'ALL' || presetView !== 'all'
                          ? 'No opportunities match your filter criteria.'
                          : 'Opportunities are generated when Leads are qualified.'}
                      </p>
                    </td>
                  </tr>
                ) : (
                  opportunities.map((opp) => (
                    <tr key={opp.id}>
                      <td style={{ whiteSpace: 'nowrap' }}>
                        <button
                          onClick={() => setDetailModalOppId(opp.id)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--accent-primary)',
                            fontWeight: 700,
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            padding: 0
                          }}
                        >
                          {opp.opportunityId}
                        </button>
                      </td>

                      <td>
                        <button
                          onClick={() => setDetailModalOppId(opp.id)}
                          style={{ background: 'none', border: 'none', padding: 0, textAlign: 'left', font: 'inherit', cursor: 'pointer' }}
                        >
                          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>
                            {opp.name}
                          </span>
                        </button>
                        {opp.requirementTypes && opp.requirementTypes.length > 0 && (
                          <div style={{ display: 'flex', gap: '4px', marginTop: '3px', flexWrap: 'wrap' }}>
                            {opp.requirementTypes.map(rt => (
                              <span key={rt} style={{ fontSize: '0.7rem', background: '#f1f5f9', padding: '1px 5px', borderRadius: '3px', color: '#475569' }}>
                                {rt}
                              </span>
                            ))}
                          </div>
                        )}
                      </td>

                      <td>
                        {opp.accountName ? (
                          <Link
                            to={`/crm/accounts?search=${encodeURIComponent(opp.accountName)}`}
                            style={{ color: 'var(--text-primary)', fontWeight: 600, textDecoration: 'none', fontSize: '0.875rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                          >
                            <Building size={14} color="#d97706" />
                            <span>{opp.accountName}</span>
                          </Link>
                        ) : '—'}
                      </td>

                      <td>
                        {opp.contactName ? (
                          <Link
                            to={`/crm/contacts?search=${encodeURIComponent(opp.contactName)}`}
                            style={{ color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.875rem', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                          >
                            <User size={14} color="var(--accent-primary)" />
                            <span>{opp.contactName}</span>
                          </Link>
                        ) : '—'}
                      </td>

                      <td>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: opp.stage === 'Close' ? '#dcfce7' : '#eff6ff',
                          color: opp.stage === 'Close' ? '#166534' : '#1d4ed8',
                          fontWeight: 700,
                          fontSize: '0.75rem'
                        }}>
                          {opp.stage}
                        </span>
                      </td>

                      <td style={{ whiteSpace: 'nowrap', fontWeight: 600, fontSize: '0.875rem' }}>
                        {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                          <span>{opp.currency || 'INR'} {Number(opp.estimatedValue).toLocaleString()}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontStyle: 'italic' }}>Not specified</span>
                        )}
                      </td>

                      <td>
                        {getStatusBadge(opp.status)}
                      </td>

                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          <span title={`${opp.milestoneCount || 0} Milestones`}>
                            {opp.milestoneCount || 0} MS
                          </span>
                          <span>•</span>
                          <span title={`${opp.workstreamCount || 0} Workstreams`}>
                            {opp.workstreamCount || 0} WS
                          </span>
                        </div>
                      </td>

                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.35rem' }}>
                          <button
                            onClick={() => setStageModalOpp(opp)}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="Advance Stage"
                          >
                            Stage
                          </button>
                          <button
                            onClick={() => setDetailModalOppId(opp.id)}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="View Opportunity Details"
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Table Server-Side Pagination Footer */}
          <div className="crm-pagination-footer" style={{
            padding: '0.85rem 1.25rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.85rem',
            color: 'var(--text-secondary)'
          }}>
            <div>
              Showing <strong>{opportunities.length}</strong> of <strong>{totalCount}</strong> opportunities
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <button
                className="crm-btn crm-btn-secondary crm-btn-sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ fontWeight: 600 }}>
                {page} / {totalPages}
              </span>
              <button
                className="crm-btn crm-btn-secondary crm-btn-sm"
                disabled={page >= totalPages || loading}
                onClick={() => setPage(prev => prev + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Opportunity Detail Modal */}
      {detailModalOppId && (
        <OpportunityDetailModal
          isOpen={!!detailModalOppId}
          opportunityId={detailModalOppId}
          onClose={() => setDetailModalOppId(null)}
          onOpportunityUpdated={handleOpportunityUpdated}
        />
      )}

      {/* Opportunity Stage Transition Modal */}
      {stageModalOpp && (
        <OpportunityStageModal
          isOpen={!!stageModalOpp}
          opportunity={stageModalOpp}
          onClose={() => setStageModalOpp(null)}
          onSuccess={handleOpportunityUpdated}
        />
      )}
    </div>
  );
}
