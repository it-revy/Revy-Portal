import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
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
  XCircle,
  FileText,
  Calendar,
  DollarSign,
  Edit3
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import crmService from '../services/crmService';
import OpportunityDetailModal from '../modules/crm/components/OpportunityDetailModal';
import OpportunityStageModal from '../modules/crm/components/OpportunityStageModal';

const STAGES = ['Enquiry', 'Qualify', 'Develop', 'Propose/Offer', 'Negotiate', 'Close'];

const STAGE_ORDER = {
  'Enquiry': 0,
  'Qualify': 1,
  'Develop': 2,
  'Propose': 3,
  'Propose/Offer': 3,
  'Negotiate': 4,
  'Close': 5
};

const BUSINESS_AREAS = ['Biogas', 'Wastewater Treatment (WWT)', 'R&D Lab', 'Solid Waste', 'Other'];

const OUTCOMES = [
  { value: 'ALL', label: 'All Outcomes' },
  { value: 'Open Pipeline', label: 'Open Pipeline' },
  { value: 'Closed Won', label: 'Closed Won' },
  { value: 'Closed Lost', label: 'Closed Lost' }
];

export default function CrmOpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();

  // Authoritative role check for backward movement
  const isManager = hasRole('CRM_SALES_MANAGER') || hasRole('CRM_ADMIN') || hasRole('IT_ADMIN') || hasRole('DIRECTOR');

  const urlSearch = searchParams.get('search') || '';
  const urlView = searchParams.get('view') || 'all';
  const urlMode = searchParams.get('mode') || 'kanban'; // 'kanban' or 'table'

  // Workspace View Mode: 'kanban' or 'table'
  const [viewMode, setViewMode] = useState(urlMode);

  // Filter states
  const [search, setSearch] = useState(urlSearch);
  const [presetView, setPresetView] = useState(urlView); // 'all', 'open', 'my', 'won', 'lost'
  const [stageFilter, setStageFilter] = useState('ALL');
  const [outcomeFilter, setOutcomeFilter] = useState('ALL');
  const [businessAreaFilter, setBusinessAreaFilter] = useState('ALL');
  const [ownerFilter, setOwnerFilter] = useState('ALL');

  // Assignees for table filter
  const [assignees, setAssignees] = useState([]);

  // Data states
  const [opportunities, setOpportunities] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Pipeline summary KPI metrics
  const [pipelineSummary, setPipelineSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Drag-and-drop state
  const [draggedOpp, setDraggedOpp] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);

  // Modals state
  const [detailModalOppId, setDetailModalOppId] = useState(null);
  const [stageModalOpp, setStageModalOpp] = useState(null);

  // Load assignees on mount
  useEffect(() => {
    async function loadAssignees() {
      try {
        const res = await crmService.getEligibleAssignees();
        if (res.data?.success) {
          setAssignees(res.data.assignees || []);
        }
      } catch (err) {
        console.error('Failed to load assignees:', err);
      }
    }
    loadAssignees();
  }, []);

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
      const baseParams = {};
      if (search.trim()) baseParams.search = search.trim();
      if (businessAreaFilter !== 'ALL') baseParams.businessArea = businessAreaFilter;

      if (viewMode === 'table') {
        // Table view filters
        if (presetView !== 'all') baseParams.view = presetView;
        if (stageFilter !== 'ALL') baseParams.stage = stageFilter;
        if (outcomeFilter !== 'ALL') baseParams.outcome = outcomeFilter;
        if (ownerFilter !== 'ALL') baseParams.owner = ownerFilter;

        const res = await crmService.getOpportunities({
          ...baseParams,
          limit: pageSize,
          offset: (page - 1) * pageSize
        });

        if (res.data?.success) {
          setOpportunities(res.data.opportunities || []);
          setTotalCount(res.data.totalCount ?? res.data.count ?? (res.data.opportunities || []).length);
        } else {
          throw new Error(res.data?.message || 'Failed to load opportunities');
        }
      } else {
        // KANBAN VIEW: Use supported page size limit (max 100 per backend schema Query(50, ge=1, le=100))
        // Supports pipelines of any size: fetches initial page of 100, then subsequent pages if totalCount > 100
        const KANBAN_CHUNK = 100;
        const firstRes = await crmService.getOpportunities({
          ...baseParams,
          limit: KANBAN_CHUNK,
          offset: 0
        });

        if (!firstRes.data?.success) {
          throw new Error(firstRes.data?.message || 'Failed to load opportunities');
        }

        let allOpps = firstRes.data.opportunities || [];
        const total = firstRes.data.totalCount ?? firstRes.data.count ?? allOpps.length;

        if (total > KANBAN_CHUNK) {
          const pagesCount = Math.ceil(total / KANBAN_CHUNK);
          const additionalPromises = [];
          for (let p = 1; p < pagesCount; p++) {
            additionalPromises.push(
              crmService.getOpportunities({
                ...baseParams,
                limit: KANBAN_CHUNK,
                offset: p * KANBAN_CHUNK
              })
            );
          }
          const responses = await Promise.all(additionalPromises);
          for (const r of responses) {
            if (r.data?.success && Array.isArray(r.data.opportunities)) {
              allOpps = allOpps.concat(r.data.opportunities);
            }
          }
        }

        setOpportunities(allOpps);
        setTotalCount(total);
      }
    } catch (err) {
      console.error('Error fetching opportunities:', err);
      let msg = 'Failed to load opportunities. Please try again.';
      if (err.response?.data?.message) {
        msg = err.response.data.message;
      } else if (err.response?.data?.detail) {
        const d = err.response.data.detail;
        msg = Array.isArray(d) ? d.map(item => item.msg || JSON.stringify(item)).join(', ') : String(d);
      } else if (err.message) {
        msg = err.message;
      }
      setError(msg);
      setOpportunities([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, presetView, stageFilter, outcomeFilter, businessAreaFilter, ownerFilter, viewMode]);

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

  const handleOpportunityUpdated = () => {
    fetchOpportunities();
    fetchSummary();
  };

  // Drag and Drop Handlers
  const handleDragStart = (e, opp) => {
    setDraggedOpp(opp);
    e.dataTransfer.setData('text/plain', opp.id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, stage) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverColumn !== stage) {
      setDragOverColumn(stage);
    }
  };

  const handleDragLeave = (e, stage) => {
    if (dragOverColumn === stage) {
      setDragOverColumn(null);
    }
  };

  const handleDrop = (e, targetStage) => {
    e.preventDefault();
    setDragOverColumn(null);
    if (!draggedOpp) return;

    const currentStage = draggedOpp.stage === 'Propose' ? 'Propose/Offer' : draggedOpp.stage;
    if (currentStage === targetStage) {
      setDraggedOpp(null);
      return;
    }

    const currentOrder = STAGE_ORDER[currentStage] ?? 0;
    const targetOrder = STAGE_ORDER[targetStage] ?? 0;

    // Backward transition permission check
    if (targetOrder < currentOrder && !isManager) {
      setError(`Permission Denied: Moving an opportunity backward from "${currentStage}" to "${targetStage}" requires Sales Manager or Administrator role.`);
      setDraggedOpp(null);
      return;
    }

    // Do NOT persist immediately! Navigate to dedicated Opportunity Edit page with targetStage
    const oppIdToNavigate = draggedOpp.id;
    setDraggedOpp(null);
    navigate(`/crm/opportunities/${oppIdToNavigate}/edit?targetStage=${encodeURIComponent(targetStage)}`);
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  // Helper for outcome badge with accessible labels and high contrast
  const getOutcomeBadge = (opp) => {
    const status = opp.status;
    if (status === 'Won') {
      return (
        <span
          style={{
            background: '#dcfce7',
            color: '#166534',
            border: '1px solid #86efac',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.725rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            textTransform: 'uppercase'
          }}
          aria-label="Outcome: Closed Won"
        >
          <CheckCircle2 size={11} />
          Closed Won
        </span>
      );
    }
    if (status === 'Lost') {
      return (
        <span
          style={{
            background: '#fee2e2',
            color: '#991b1b',
            border: '1px solid #fca5a5',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.725rem',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
            textTransform: 'uppercase'
          }}
          aria-label="Outcome: Closed Lost"
        >
          <XCircle size={11} />
          Closed Lost
        </span>
      );
    }
    return (
      <span
        style={{
          background: 'var(--accent-light)',
          color: 'var(--accent-primary)',
          border: '1px solid var(--accent-light)',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '0.725rem',
          fontWeight: 700,
          textTransform: 'uppercase'
        }}
        aria-label="Outcome: Open Pipeline"
      >
        Open Pipeline
      </span>
    );
  };

  // Group opportunities by canonical 6 stages for Kanban View
  // Display both open and closed opportunities on the Kanban board.
  // Closed Won and Closed Lost appear in the Close column.
  const kanbanColumns = STAGES.map(stage => {
    const oppsInStage = opportunities.filter(o => {
      if (stage === 'Propose/Offer') {
        return o.stage === 'Propose/Offer' || o.stage === 'Propose';
      }
      return o.stage === stage;
    });

    const openSum = oppsInStage
      .filter(o => o.status === 'Open')
      .reduce((acc, curr) => acc + (Number(curr.estimatedValue) || 0), 0);

    const wonSum = oppsInStage
      .filter(o => o.status === 'Won')
      .reduce((acc, curr) => acc + (Number(curr.estimatedValue) || 0), 0);

    return {
      stage,
      opportunities: oppsInStage,
      openValue: openSum,
      wonValue: wonSum
    };
  });

  return (
    <div className="page-body">
      {/* Page Header Command Bar */}
      <div className="crm-page-header">
        <div className="crm-page-header-title-group">
          <div className="crm-page-header-icon" style={{ background: 'linear-gradient(135deg, #2563eb, #1d4ed8)' }}>
            <Briefcase size={22} />
          </div>
          <div>
            <h1 className="crm-page-header-title">Opportunity Pipeline Workspace</h1>
            <p className="crm-page-header-subtitle">
              Visual 6-stage Kanban progression, commercial outcome governance, and drag-and-drop workflow
            </p>
          </div>
        </div>

        <div className="crm-page-header-actions">
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
                setSearchParams({ mode: 'kanban' });
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

      {/* Pipeline KPI Summary Banner */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
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
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', minHeight: '2rem' }}>
            {pipelineSummary?.openPipelineValueByCurrency && Object.keys(pipelineSummary.openPipelineValueByCurrency).length > 0 ? (
              Object.entries(pipelineSummary.openPipelineValueByCurrency).map(([curr, val]) => (
                <div key={curr} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                  {curr} {Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              ))
            ) : (
              <div>INR {(pipelineSummary?.totalOpenValue || 0).toLocaleString()}</div>
            )}
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
            {pipelineSummary?.totalCount || totalCount || opportunities.length}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Across all 6 canonical pipeline stages
          </span>
        </div>

        {/* Closed Won */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--success-text)', textTransform: 'uppercase' }}>
              Closed Won Value
            </span>
            <CheckCircle2 size={16} color="var(--success)" />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)', minHeight: '2rem' }}>
            {pipelineSummary?.wonOpportunityValueByCurrency && Object.keys(pipelineSummary.wonOpportunityValueByCurrency).length > 0 ? (
              Object.entries(pipelineSummary.wonOpportunityValueByCurrency).map(([curr, val]) => (
                <div key={curr} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                  {curr} {Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              ))
            ) : (
              <div>{pipelineSummary?.byStatus?.Won || 0} deals won</div>
            )}
          </div>
          <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
            {pipelineSummary?.byStatus?.Won || 0} won deals • Signed commitments
          </span>
        </div>

        {/* Closed Lost */}
        <div className="glass-panel" style={{ padding: '1rem 1.25rem', borderRadius: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--danger-text)', textTransform: 'uppercase' }}>
              Closed Lost Value
            </span>
            <XCircle size={16} color="var(--danger)" />
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)', minHeight: '2rem' }}>
            {pipelineSummary?.lostOpportunityValueByCurrency && Object.keys(pipelineSummary.lostOpportunityValueByCurrency).length > 0 ? (
              Object.entries(pipelineSummary.lostOpportunityValueByCurrency).map(([curr, val]) => (
                <div key={curr} style={{ fontSize: '1rem', lineHeight: '1.4' }}>
                  {curr} {Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
              ))
            ) : (
              <div>{pipelineSummary?.byStatus?.Lost || 0} deals lost</div>
            )}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {pipelineSummary?.byStatus?.Lost || 0} deals • Audit-tracked loss reasons
          </span>
        </div>
      </div>

      {/* Toolbar & Filters */}
      <div className="crm-toolbar">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group">
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by ID, Opportunity Name, Account, Contact..."
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

        {/* Filters */}
        <div className="crm-toolbar-filters">
          {/* Table View ONLY Filters */}
          {viewMode === 'table' && (
            <>
              {/* View Filter */}
              <div className="crm-filter-item">
                <label className="crm-filter-label">View:</label>
                <select
                  value={presetView}
                  onChange={(e) => {
                    setPresetView(e.target.value);
                    setPage(1);
                  }}
                  className="form-control crm-select-sm"
                  style={{ width: 'auto', minWidth: '120px' }}
                >
                  <option value="all">All Opportunities</option>
                  <option value="open">Open Pipeline</option>
                  <option value="my">My Assigned</option>
                  <option value="won">Closed Won</option>
                  <option value="lost">Closed Lost</option>
                </select>
              </div>

              {/* Stage Filter */}
              <div className="crm-filter-item">
                <label className="crm-filter-label">Stage:</label>
                <select
                  value={stageFilter}
                  onChange={(e) => {
                    setStageFilter(e.target.value);
                    setPage(1);
                  }}
                  className="form-control crm-select-sm"
                  style={{ width: 'auto', minWidth: '120px' }}
                >
                  <option value="ALL">All Stages</option>
                  {STAGES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Outcome Filter */}
              <div className="crm-filter-item">
                <label className="crm-filter-label">Outcome:</label>
                <select
                  value={outcomeFilter}
                  onChange={(e) => {
                    setOutcomeFilter(e.target.value);
                    setPage(1);
                  }}
                  className="form-control crm-select-sm"
                  style={{ width: 'auto', minWidth: '130px' }}
                >
                  {OUTCOMES.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {/* Owner Filter */}
              <div className="crm-filter-item">
                <label className="crm-filter-label">Owner:</label>
                <select
                  value={ownerFilter}
                  onChange={(e) => {
                    setOwnerFilter(e.target.value);
                    setPage(1);
                  }}
                  className="form-control crm-select-sm"
                  style={{ width: 'auto', minWidth: '130px' }}
                >
                  <option value="ALL">All Owners</option>
                  {assignees.map(a => (
                    <option key={a.id} value={a.id}>{a.name || a.username}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {/* Business Area Filter (Available in both views) */}
          <div className="crm-filter-item">
            <label className="crm-filter-label">Area:</label>
            <select
              value={businessAreaFilter}
              onChange={(e) => {
                setBusinessAreaFilter(e.target.value);
                setPage(1);
              }}
              className="form-control crm-select-sm"
              style={{ width: 'auto', minWidth: '120px' }}
            >
              <option value="ALL">All Areas</option>
              {BUSINESS_AREAS.map(ba => (
                <option key={ba} value={ba}>{ba}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error notification banner with actionable Retry */}
      {error && (
        <div style={{
          padding: '0.85rem 1.25rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: '8px',
          color: 'var(--danger-text)',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          boxShadow: '0 1px 3px rgba(239, 68, 68, 0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <div>
              <strong>Failed to load opportunities: </strong>
              <span>{error}</span>
            </div>
          </div>
          <button
            onClick={() => {
              fetchOpportunities();
              fetchSummary();
            }}
            className="crm-btn crm-btn-secondary crm-btn-sm"
            style={{ borderColor: 'var(--danger-border)', color: 'var(--danger-text)', background: '#ffffff' }}
          >
            <RefreshCw size={13} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Loading state indicator */}
      {loading && opportunities.length === 0 && (
        <div style={{
          padding: '4rem 1rem',
          textAlign: 'center',
          color: 'var(--text-secondary)',
          background: '#ffffff',
          borderRadius: '8px',
          border: '1px solid var(--crm-border)',
          marginBottom: '1.25rem'
        }}>
          <RefreshCw size={28} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--crm-primary)' }} />
          <h4 style={{ margin: '0 0 0.35rem', color: 'var(--crm-text-primary)', fontSize: '1.05rem' }}>Loading Opportunities...</h4>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--crm-text-muted)' }}>
            Retrieving commercial pipeline records across all stages
          </p>
        </div>
      )}

      {/* VIEW MODE 1: KANBAN BOARD */}
      {viewMode === 'kanban' && (!loading || opportunities.length > 0) && (
        <div className="crm-kanban-board-wrapper">
          <div className="crm-kanban-board-grid">
            {kanbanColumns.map(({ stage, opportunities: colOpps, openValue, wonValue }) => {
              const isDragTarget = dragOverColumn === stage;

              return (
                <div
                  key={stage}
                  onDragOver={(e) => handleDragOver(e, stage)}
                  onDragLeave={(e) => handleDragLeave(e, stage)}
                  onDrop={(e) => handleDrop(e, stage)}
                  className={`crm-kanban-column ${isDragTarget ? 'drag-over' : ''}`}
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
                        <strong style={{ fontSize: '0.925rem', color: 'var(--text-primary)' }}>
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
                      <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        {stage === 'Close' ? (
                          <span>Won: INR {wonValue.toLocaleString()}</span>
                        ) : (
                          <span>Open: INR {openValue.toLocaleString()}</span>
                        )}
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
                        padding: '2.5rem 1rem',
                        textAlign: 'center',
                        color: 'var(--text-muted)',
                        fontSize: '0.825rem',
                        border: '1px dashed #e2e8f0',
                        borderRadius: '8px'
                      }}>
                        No opportunities in {stage}
                      </div>
                    ) : (
                      colOpps.map(opp => {
                        const isWon = opp.status === 'Won';
                        const isLost = opp.status === 'Lost';

                        let cardBg = '#ffffff';
                        let cardBorder = 'var(--border-color)';
                        if (isWon) {
                          cardBg = '#f0fdf4';
                          cardBorder = '#86efac';
                        } else if (isLost) {
                          cardBg = '#fef2f2';
                          cardBorder = '#fca5a5';
                        }

                        return (
                          <div
                            key={opp.id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, opp)}
                            onClick={() => setDetailModalOppId(opp.id)}
                            className="crm-kanban-card"
                            style={{
                              background: cardBg,
                              border: `1px solid ${cardBorder}`
                            }}
                            title="Click to view details, or drag to request stage transition"
                          >
                            {/* Top Bar: Code and Outcome Badge */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                                {opp.opportunityId}
                              </span>
                              {getOutcomeBadge(opp)}
                            </div>

                            {/* 1. Opportunity Name */}
                            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.45rem', lineHeight: 1.35 }}>
                              {opp.name}
                            </div>

                            {/* 2. Primary Account and/or Primary Contact */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginBottom: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              {opp.accountName ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }} title={`Account: ${opp.accountName}`}>
                                  <Building size={13} color="#d97706" style={{ flexShrink: 0 }} />
                                  <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {opp.accountName}
                                  </span>
                                </div>
                              ) : null}
                              {opp.contactName ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }} title={`Primary Contact: ${opp.contactName}`}>
                                  <User size={13} color="var(--accent-primary)" style={{ flexShrink: 0 }} />
                                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {opp.contactName}
                                  </span>
                                </div>
                              ) : null}
                              {!opp.accountName && !opp.contactName && (
                                <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.75rem' }}>
                                  Unassigned Entity
                                </span>
                              )}
                            </div>

                            {/* 3. Owner */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.45rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--text-muted)' }}>Owner:</span>
                              <span style={{ fontWeight: 500 }}>
                                {opp.assignedToName || 'Unassigned'}
                              </span>
                            </div>

                            {/* 4. Commercial Amount & 5. Expected Close Date */}
                            <div style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '0.5rem',
                              padding: '4px 6px',
                              background: isWon ? '#dcfce7' : (isLost ? '#fee2e2' : '#f8fafc'),
                              borderRadius: '4px',
                              fontSize: '0.775rem'
                            }}>
                              <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                                {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                                  `${opp.currency || 'INR'} ${Number(opp.estimatedValue).toLocaleString()}`
                                ) : (
                                  <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontWeight: 400 }}>No value</span>
                                )}
                              </div>
                              {opp.expectedCloseDate && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '3px', color: 'var(--text-muted)' }} title={`Expected close: ${opp.expectedCloseDate.slice(0, 10)}`}>
                                  <Calendar size={12} />
                                  <span>{opp.expectedCloseDate.slice(0, 10)}</span>
                                </div>
                              )}
                            </div>

                            {/* Loss reason note if Lost */}
                            {isLost && opp.lossReason && (
                              <div style={{
                                marginBottom: '0.45rem',
                                padding: '3px 6px',
                                background: '#fef2f2',
                                border: '1px dashed #fca5a5',
                                borderRadius: '4px',
                                fontSize: '0.725rem',
                                color: '#991b1b',
                                lineHeight: 1.25
                              }}>
                                <strong>Loss Reason: </strong>
                                <span>{opp.lossReason}</span>
                              </div>
                            )}

                            {/* Card Action Bar */}
                            <div style={{
                              borderTop: '1px solid rgba(0,0,0,0.06)',
                              paddingTop: '0.45rem',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                {opp.businessArea || 'Biogas'}
                              </span>

                              <div style={{ display: 'flex', gap: '0.35rem' }}>
                                <Link
                                  to={`/crm/opportunities/${opp.id}/edit`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="crm-btn crm-btn-secondary crm-btn-sm"
                                  style={{
                                    fontSize: '0.725rem',
                                    padding: '2px 8px',
                                    height: 'auto',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    textDecoration: 'none'
                                  }}
                                  title="Open full Opportunity Edit form"
                                >
                                  <Edit3 size={11} />
                                  <span>Edit</span>
                                </Link>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setStageModalOpp(opp);
                                  }}
                                  className="crm-btn crm-btn-secondary crm-btn-sm"
                                  style={{
                                    fontSize: '0.725rem',
                                    padding: '2px 8px',
                                    height: 'auto',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px'
                                  }}
                                >
                                  <TrendingUp size={11} />
                                  <span>Stage</span>
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* VIEW MODE 2: TABLE VIEW */}
      {viewMode === 'table' && (!loading || opportunities.length > 0) && (
        <div className="crm-table-card">
          <div className="crm-table-container">
            <table className="crm-table">
              <thead>
                <tr>
                  <th style={{ width: '130px' }}>Opportunity ID</th>
                  <th style={{ minWidth: '220px' }}>Opportunity Name</th>
                  <th style={{ minWidth: '180px' }}>Primary Account</th>
                  <th style={{ minWidth: '160px' }}>Primary Contact</th>
                  <th style={{ width: '110px' }}>Stage</th>
                  <th style={{ width: '130px' }}>Outcome</th>
                  <th style={{ width: '130px' }}>Commercial Value</th>
                  <th style={{ width: '130px' }}>Owner</th>
                  <th style={{ width: '110px' }}>Close Date</th>
                  <th className="sticky-actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {opportunities.length === 0 ? (
                  <tr>
                    <td colSpan={10} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                      <Briefcase size={36} color="#cbd5e1" style={{ margin: '0 auto 0.75rem', display: 'block' }} />
                      <h4 style={{ margin: '0 0 0.35rem', color: 'var(--text-primary)', fontSize: '1rem' }}>No Opportunities Found</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem' }}>
                        No opportunities match your filter criteria. Adjust your filters or create an opportunity from Leads.
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
                        {opp.subStatus && (
                          <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Sub-status: {opp.subStatus}
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
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.8rem' }}>—</span>
                        )}
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
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.8rem' }}>—</span>
                        )}
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

                      <td>
                        {getOutcomeBadge(opp)}
                      </td>

                      <td style={{ whiteSpace: 'nowrap', fontWeight: 600, fontSize: '0.875rem' }}>
                        {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                          <span>{opp.currency || 'INR'} {Number(opp.estimatedValue).toLocaleString()}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontStyle: 'italic' }}>Not specified</span>
                        )}
                      </td>

                      <td>
                        <span style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                          {opp.assignedToName || 'Unassigned'}
                        </span>
                      </td>

                      <td>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {opp.expectedCloseDate ? opp.expectedCloseDate.slice(0, 10) : '—'}
                        </span>
                      </td>

                      <td className="sticky-actions-col">
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.35rem' }}>
                          <Link
                            to={`/crm/opportunities/${opp.id}/edit`}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="Edit Opportunity"
                            style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '2px' }}
                          >
                            <Edit3 size={12} />
                            <span>Edit</span>
                          </Link>
                          <button
                            onClick={() => setStageModalOpp(opp)}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="Advance / Transition Stage"
                          >
                            Stage
                          </button>
                          <button
                            onClick={() => setDetailModalOppId(opp.id)}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="View Full Details"
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
          <div className="crm-pagination-footer">
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
