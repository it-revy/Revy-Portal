import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Layers,
  Search,
  Plus,
  Filter,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Edit,
  Clock,
  Building,
  User,
  AlertCircle,
  RefreshCw,
  Calendar,
  X,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Briefcase
} from 'lucide-react';
import crmService from '../services/crmService';
import LeadStatusModal from '../modules/crm/components/LeadStatusModal';

const SAVED_VIEWS = [
  { id: 'open', label: 'Open Leads', icon: Layers },
  { id: 'all', label: 'All Leads', icon: Briefcase },
  { id: 'unqualified', label: 'Unqualified Leads', icon: XCircle },
  { id: 'my_leads', label: 'My Leads', icon: User },
  { id: 'follow_ups_due', label: 'Follow-ups Due', icon: Clock }
];

export default function CrmLeadsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, hasPermission } = useAuth();

  // URL state
  const currentView = searchParams.get('view') || 'open';
  const urlStatus = searchParams.get('lifecycleStatus') || 'ALL';

  // State
  const [leads, setLeads] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [search, setSearch] = useState('');
  const [businessArea, setBusinessArea] = useState('ALL');
  const [requirementType, setRequirementType] = useState('ALL');
  const [lifecycleStatus, setLifecycleStatus] = useState(urlStatus);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successNotification, setSuccessNotification] = useState(null);
  const [warningNotification, setWarningNotification] = useState(null);

  // Modals
  const [leadForStatus, setLeadForStatus] = useState(null);

  const canCreate = hasPermission('crm.lead.create');
  const canEdit = hasPermission('crm.lead.edit');
  const canChangeStatus = hasPermission('crm.lead.status.update');

  const fetchLeads = useCallback(async (options = {}) => {
    setLoading(true);
    if (!options.silent) {
      setError(null);
    }
    try {
      const params = {
        view: currentView,
        page,
        pageSize,
        sortBy,
        sortOrder
      };

      if (search.trim()) params.search = search.trim();
      if (businessArea !== 'ALL') params.businessArea = businessArea;
      if (requirementType !== 'ALL') params.requirementType = requirementType;
      if (currentView === 'all' && lifecycleStatus !== 'ALL') {
        params.lifecycleStatus = lifecycleStatus;
      }

      const res = await crmService.getLeads(params);
      if (res.data?.success) {
        setLeads(res.data.leads || []);
        setTotalCount(res.data.totalCount || res.data.total || 0);
        setTotalPages(res.data.totalPages || 1);
        return { success: true };
      }
      const msg = res.data?.message || 'Failed to fetch leads.';
      if (!options.silent) setError(msg);
      return { success: false, error: msg };
    } catch (err) {
      const errMsg = err.response?.data?.message || 'Failed to fetch leads. Please check connection and try again.';
      if (!options.silent) {
        setError(errMsg);
      }
      return { success: false, error: errMsg };
    } finally {
      setLoading(false);
    }
  }, [currentView, page, pageSize, sortBy, sortOrder, search, businessArea, requirementType, lifecycleStatus]);

  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessNotification(location.state.successMessage);
      const timer = setTimeout(() => setSuccessNotification(null), 5000);
      window.history.replaceState({}, document.title);
      return () => clearTimeout(timer);
    }
  }, [location.state]);

  const handleLeadSaved = async (savedLead) => {
    setIsCreateModalOpen(false);
    setLeadToEdit(null);
    setError(null);
    setWarningNotification(null);

    const leadIdentifier = savedLead?.leadId || savedLead?.lead_id || savedLead?.leadName || 'Lead';
    const isEditAction = Boolean(leadToEdit);
    const msg = isEditAction
      ? `Lead ${leadIdentifier} updated successfully.`
      : `Lead ${leadIdentifier} created successfully.`;

    setSuccessNotification(msg);
    setTimeout(() => {
      setSuccessNotification(null);
    }, 5000);

    const refreshResult = await fetchLeads({ silent: true });
    if (refreshResult && !refreshResult.success) {
      // If refreshing the list fails after a successful save, display a non-blocking warning
      // such as "Lead saved successfully, but the list could not be refreshed." Do not report that the save failed.
      setWarningNotification('Lead saved successfully, but the list could not be refreshed.');
      setTimeout(() => {
        setWarningNotification(null);
      }, 7000);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleViewChange = (viewId) => {
    setPage(1);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('view', viewId);
    if (viewId !== 'all') {
      newParams.delete('lifecycleStatus');
      setLifecycleStatus('ALL');
    }
    setSearchParams(newParams);
  };

  const handleSortChange = (field) => {
    if (sortBy === field) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLeads();
  };

  const handleClearSearch = () => {
    setSearch('');
    setPage(1);
  };

  // Format calendar date without timezone shift
  const formatDateOnly = (dateStr) => {
    if (!dateStr) return 'Not scheduled';
    try {
      // dateStr can be YYYY-MM-DD or ISO string
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

  // Check if a scheduled date is overdue
  const isOverdue = (dateStr) => {
    if (!dateStr) return false;
    try {
      const cleanDate = dateStr.slice(0, 10);
      const today = new Date();
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      return cleanDate < todayStr;
    } catch {
      return false;
    }
  };

  const isDueToday = (dateStr) => {
    if (!dateStr) return false;
    try {
      const cleanDate = dateStr.slice(0, 10);
      const today = new Date();
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      return cleanDate === todayStr;
    } catch {
      return false;
    }
  };

  return (
    <div className="page-body">
      {/* Top Header */}
      <div className="crm-page-header">
        <div className="crm-page-header-title-group">
          <div className="crm-page-header-icon">
            <Layers size={22} />
          </div>
          <div>
            <h1 className="crm-page-header-title">Leads Workspace</h1>
            <p className="crm-page-header-subtitle">
              Track client enquiries, technical specifications, and scheduled follow-ups
            </p>
          </div>
        </div>

        <div className="crm-page-header-actions">
          <button
            onClick={fetchLeads}
            className="crm-btn crm-btn-secondary"
            title="Refresh Leads"
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>

          {canCreate && (
            <button
              onClick={() => navigate('/crm/leads/new')}
              className="crm-btn crm-btn-primary"
            >
              <Plus size={16} />
              <span>New Lead</span>
            </button>
          )}
        </div>
      </div>

      {/* 5 Saved Views Tabs */}
      <div className="crm-tabs-container">
        {SAVED_VIEWS.map(view => {
          const isActive = currentView === view.id;
          const Icon = view.icon;
          return (
            <button
              key={view.id}
              onClick={() => handleViewChange(view.id)}
              className={`crm-tab-button ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} />
              <span>{view.label}</span>
            </button>
          );
        })}
      </div>

      {/* Filters & Search Toolbar */}
      <div className="crm-toolbar">
        {/* Search Box with Clear Button and Submit */}
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group">
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by Lead ID, Name, Account, Contact, Product..."
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

        {/* Faceted Filter Dropdowns */}
        <div className="crm-toolbar-filters">
          {/* Business Area */}
          <div className="crm-filter-item">
            <label className="crm-filter-label">Business Area:</label>
            <select
              className="form-control crm-select-sm"
              style={{ width: 'auto' }}
              value={businessArea}
              onChange={e => { setBusinessArea(e.target.value); setPage(1); }}
            >
              <option value="ALL">All Areas</option>
              <option value="Biogas">Biogas</option>
              <option value="WWT">WWT</option>
            </select>
          </div>

          {/* Requirement Type */}
          <div className="crm-filter-item">
            <label className="crm-filter-label">Requirement:</label>
            <select
              className="form-control crm-select-sm"
              style={{ width: 'auto' }}
              value={requirementType}
              onChange={e => { setRequirementType(e.target.value); setPage(1); }}
            >
              <option value="ALL">All Types</option>
              <option value="Consulting">Consulting</option>
              <option value="Sample Testing">Sample Testing</option>
              <option value="Product">Product</option>
            </select>
          </div>

          {/* Lifecycle Status (Visible in All Leads view) */}
          {currentView === 'all' && (
            <div className="crm-filter-item">
              <label className="crm-filter-label">Status:</label>
              <select
                className="form-control crm-select-sm"
                style={{ width: 'auto' }}
                value={lifecycleStatus}
                onChange={e => { setLifecycleStatus(e.target.value); setPage(1); }}
              >
                <option value="ALL">All Statuses</option>
                <option value="Enquiry">Enquiry</option>
                <option value="Offer">Offer</option>
                <option value="Negotiation">Negotiation</option>
                <option value="Supply">Supply</option>
                <option value="Payment">Payment</option>
                <option value="Dormant">Dormant</option>
              </select>
            </div>
          )}
        </div>
      </div>

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

      {/* Error state */}
      {error && (
        <div style={{
          padding: '1rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: '8px',
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

      {/* Leads Table Card */}
      <div className="crm-table-card">
        <div className="crm-table-container">
          <table className="crm-table">
            <thead>
              {currentView === 'open' ? (
                /* Open Leads: Lead ID + 4 information groups + Actions */
                <tr>
                  <th
                    onClick={() => handleSortChange('lead_id')}
                    className="sortable"
                    style={{ whiteSpace: 'nowrap', width: '130px', minWidth: '120px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Lead ID</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSortChange('lead_name')}
                    className="sortable"
                    style={{ minWidth: '240px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Lead Title</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th style={{ minWidth: '200px' }}>Account</th>
                  <th style={{ minWidth: '170px' }}>Area & Type</th>
                  <th
                    onClick={() => handleSortChange('next_follow_up_date')}
                    className="sortable"
                    style={{ minWidth: '180px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Next Follow-up</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th className="sticky-actions-col">Actions</th>
                </tr>
              ) : (
                /* Other views: All columns with sticky right Actions */
                <tr>
                  <th
                    onClick={() => handleSortChange('lead_id')}
                    className="sortable"
                    style={{ whiteSpace: 'nowrap', width: '130px', minWidth: '120px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Lead ID</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSortChange('lead_name')}
                    className="sortable"
                    style={{ minWidth: '240px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Lead Title & Specification</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th style={{ minWidth: '200px' }}>Account & Contact</th>
                  <th style={{ minWidth: '170px' }}>Area & Type</th>
                  <th style={{ width: '120px', minWidth: '110px' }}>Status</th>
                  <th style={{ minWidth: '150px' }}>Assigned To</th>
                  <th
                    onClick={() => handleSortChange('next_follow_up_date')}
                    className="sortable"
                    style={{ whiteSpace: 'nowrap', minWidth: '180px' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      <span>Next Follow-up</span>
                      <ArrowUpDown size={13} color="var(--text-muted)" />
                    </div>
                  </th>
                  <th className="sticky-actions-col">Actions</th>
                </tr>
              )}
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={currentView === 'open' ? 6 : 8} style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)' }}>
                    <RefreshCw size={26} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
                    <span>Loading leads workspace...</span>
                  </td>
                </tr>
              ) : leads.length === 0 ? (
                <tr>
                  <td colSpan={currentView === 'open' ? 6 : 8} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                    <div style={{ maxWidth: '380px', margin: '0 auto' }}>
                      <Layers size={40} color="#cbd5e1" style={{ margin: '0 auto 0.85rem', display: 'block' }} />
                      <h4 style={{ margin: '0 0 0.4rem 0', color: 'var(--text-primary)', fontSize: '1.05rem' }}>No Leads Found</h4>
                      <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.5 }}>
                        {search.trim()
                          ? `No records matching "${search}". Try adjusting filters or clearing the search.`
                          : `There are currently no leads in the "${SAVED_VIEWS.find(v => v.id === currentView)?.label}" view.`}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                leads.map(lead => {
                  const overdue = lead.lifecycleStatus !== 'Dormant' && isOverdue(lead.nextFollowUpDate);
                  const dueToday = lead.lifecycleStatus !== 'Dormant' && isDueToday(lead.nextFollowUpDate);

                  if (currentView === 'open') {
                    /* OPEN LEADS VIEW: Lead ID + 4 information groups + Actions */
                    return (
                      <tr key={lead.id}>
                        {/* 1. Lead ID */}
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <button
                            onClick={() => navigate(`/crm/leads/${lead.id}`)}
                            className="crm-lead-id-link"
                            title={`View Lead Details (${lead.leadId})`}
                          >
                            <span>{lead.leadId}</span>
                          </button>
                        </td>

                        {/* 2. Lead Title */}
                        <td>
                          <button
                            onClick={() => navigate(`/crm/leads/${lead.id}`)}
                            className="crm-lead-title-link"
                            style={{ background: 'none', border: 'none', padding: 0, textAlign: 'left', font: 'inherit' }}
                            title="View Lead Details"
                          >
                            <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {lead.leadName || lead.displayName || lead.leadId}
                            </span>
                          </button>
                          <div className="crm-cell-secondary">
                            {lead.requestedProductService || lead.requirementSummary || 'No specification recorded'}
                          </div>
                        </td>

                        {/* 2. Account */}
                        <td>
                          <div className="crm-cell-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <Building size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            <span>{lead.accountName || lead.account?.name || 'Direct Contact (No Account)'}</span>
                          </div>
                          {(lead.contactName || lead.contact?.name) && (
                            <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                              <User size={12} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                              <span>
                                {lead.contactName || lead.contact?.name}
                                {lead.contact?.designation ? ` (${lead.contact.designation})` : ''}
                              </span>
                            </div>
                          )}
                          {lead.connectedDate && (
                            <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#0369a1', fontSize: '0.75rem', marginTop: '2px' }}>
                              <Calendar size={11} color="#0284c7" />
                              <span>Connected: {formatDateOnly(lead.connectedDate)}</span>
                            </div>
                          )}
                        </td>

                        {/* 3. Area & Type */}
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                            <span className={`crm-badge ${lead.businessArea === 'Biogas' ? 'crm-badge-area-biogas' : 'crm-badge-area-wwt'}`}>
                              {lead.businessArea}
                            </span>
                            {(lead.requirementTypes && lead.requirementTypes.length > 0 ? lead.requirementTypes : [lead.requirementType || 'Consulting']).map((type, idx) => (
                              <span key={idx} className="crm-badge crm-badge-type">
                                {type}
                              </span>
                            ))}
                          </div>
                        </td>

                        {/* 4. Next Follow-up */}
                        <td>
                          {lead.nextFollowUpDate ? (
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, fontSize: '0.825rem' }}>
                                {overdue ? (
                                  <span className="crm-badge crm-badge-overdue">
                                    <AlertTriangle size={11} /> OVERDUE
                                  </span>
                                ) : dueToday ? (
                                  <span className="crm-badge" style={{ background: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', fontWeight: 700 }}>
                                    <Clock size={11} /> DUE TODAY
                                  </span>
                                ) : (
                                  <Clock size={12} color="var(--text-muted)" />
                                )}
                                <span style={{ color: overdue ? '#b91c1c' : 'var(--text-primary)' }}>
                                  {formatDateOnly(lead.nextFollowUpDate)}
                                </span>
                              </div>
                              {lead.nextFollowUpAction && (
                                <div
                                  className="crm-cell-secondary"
                                  style={{ maxWidth: '220px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                  title={lead.nextFollowUpAction}
                                >
                                  {lead.nextFollowUpAction}
                                </div>
                              )}
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                              Not scheduled
                            </span>
                          )}
                        </td>

                        {/* Actions */}
                        <td className="sticky-actions-col">
                          <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                            <button
                              onClick={() => navigate(`/crm/leads/${lead.id}`)}
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              title="View Lead Details"
                            >
                              View
                            </button>
                            {canEdit && (
                              <button
                                onClick={() => navigate(`/crm/leads/${lead.id}/edit`)}
                                className="crm-btn crm-btn-secondary crm-btn-sm"
                                title="Edit Lead"
                              >
                                <Edit size={13} />
                                <span>Edit</span>
                              </button>
                            )}
                            {canChangeStatus && (
                              <button
                                onClick={() => setLeadForStatus(lead)}
                                className="crm-btn crm-btn-secondary crm-btn-sm"
                                title="Update Status"
                              >
                                Status
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  }

                  /* OTHER VIEWS: All 8 columns with sticky Actions */
                  return (
                    <tr key={lead.id}>
                      {/* 1. Lead ID */}
                      <td style={{ whiteSpace: 'nowrap' }}>
                        <button
                          onClick={() => navigate(`/crm/leads/${lead.id}`)}
                          className="crm-lead-id-link"
                          title={`View Lead Details (${lead.leadId})`}
                        >
                          <span>{lead.leadId}</span>
                        </button>
                      </td>

                      {/* 2. Lead Title & Specification */}
                      <td>
                        <button
                          onClick={() => navigate(`/crm/leads/${lead.id}`)}
                          className="crm-lead-title-link"
                          style={{ background: 'none', border: 'none', padding: 0, textAlign: 'left', font: 'inherit' }}
                          title="View Lead Details"
                        >
                          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {lead.leadName || lead.displayName || lead.leadId}
                          </span>
                        </button>
                        <div className="crm-cell-secondary">
                          {lead.requestedProductService || lead.requirementSummary || 'No product specification recorded'}
                        </div>
                      </td>

                      {/* 3. Account & Contact */}
                      <td>
                        <div className="crm-cell-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Building size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          <span>{lead.accountName || lead.account?.name || 'Direct Contact (No Account)'}</span>
                        </div>
                        {(lead.contactName || lead.contact?.name) && (
                          <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <User size={12} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                            <span>
                              {lead.contactName || lead.contact?.name}
                              {lead.contact?.designation ? ` (${lead.contact.designation})` : ''}
                            </span>
                          </div>
                        )}
                        {lead.connectedDate && (
                          <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#0369a1', fontSize: '0.75rem', marginTop: '2px' }}>
                            <Calendar size={11} color="#0284c7" />
                            <span>Connected: {formatDateOnly(lead.connectedDate)}</span>
                          </div>
                        )}
                      </td>

                      {/* 4. Area & Type */}
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                          <span className={`crm-badge ${lead.businessArea === 'Biogas' ? 'crm-badge-area-biogas' : 'crm-badge-area-wwt'}`}>
                            {lead.businessArea}
                          </span>
                          {(lead.requirementTypes && lead.requirementTypes.length > 0 ? lead.requirementTypes : [lead.requirementType || 'Consulting']).map((type, idx) => (
                            <span key={idx} className="crm-badge crm-badge-type">
                              {type}
                            </span>
                          ))}
                        </div>
                      </td>

                      {/* 5. Status */}
                      <td>
                        <span className={`crm-badge crm-badge-status-${(lead.lifecycleStatus || 'enquiry').toLowerCase()}`}>
                          {lead.lifecycleStatus}
                        </span>
                      </td>

                      {/* 6. Assigned To */}
                      <td>
                        {lead.assignedToName || lead.assignedTo?.name || lead.assignedTo?.username ? (
                          <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
                            {lead.assignedToName || lead.assignedTo?.name || lead.assignedTo?.username}
                          </span>
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Unassigned
                          </span>
                        )}
                      </td>

                      {/* 7. Next Follow-up */}
                      <td>
                        {lead.nextFollowUpDate ? (
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600, fontSize: '0.82rem' }}>
                              {overdue ? (
                                <span className="crm-badge crm-badge-overdue">
                                  <AlertTriangle size={11} /> OVERDUE
                                </span>
                              ) : dueToday ? (
                                <span className="crm-badge" style={{ background: '#fffbeb', color: '#b45309', border: '1px solid #fde68a', fontWeight: 700 }}>
                                  <Clock size={11} /> DUE TODAY
                                </span>
                              ) : (
                                <Clock size={12} color="var(--text-muted)" />
                              )}
                              <span style={{ color: overdue ? '#b91c1c' : 'inherit' }}>
                                {formatDateOnly(lead.nextFollowUpDate)}
                              </span>
                            </div>
                            {lead.nextFollowUpAction && (
                              <div
                                className="crm-cell-secondary"
                                style={{ maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                title={lead.nextFollowUpAction}
                              >
                                {lead.nextFollowUpAction}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Not scheduled
                          </span>
                        )}
                      </td>

                      {/* 8. Sticky Actions Column */}
                      <td className="sticky-actions-col">
                        <div style={{ display: 'inline-flex', gap: '0.35rem', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => navigate(`/crm/leads/${lead.id}`)}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            title="View Lead Details"
                          >
                            View
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => navigate(`/crm/leads/${lead.id}/edit`)}
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              title="Edit Lead"
                            >
                              <Edit size={12} />
                              <span>Edit</span>
                            </button>
                          )}
                          {canChangeStatus && (
                            <button
                              onClick={() => setLeadForStatus(lead)}
                              className="crm-btn crm-btn-secondary crm-btn-sm"
                              title="Update Status"
                            >
                              Status
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Server-Side Pagination Footer */}
        <div className="crm-pagination-footer">
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Showing <strong>{leads.length}</strong> of <strong>{totalCount}</strong> leads
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}>
              <span>Page size:</span>
              <select
                className="form-control crm-select-sm"
                style={{ width: 'auto' }}
                value={pageSize}
                onChange={e => { setPageSize(Number(e.target.value)); setPage(1); }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <button
                className="crm-btn crm-btn-secondary crm-btn-sm"
                style={{ minWidth: '32px', padding: '0.3rem 0.5rem' }}
                disabled={page <= 1 || loading}
                onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                {page} / {totalPages || 1}
              </span>
              <button
                className="crm-btn crm-btn-secondary crm-btn-sm"
                style={{ minWidth: '32px', padding: '0.3rem 0.5rem' }}
                disabled={page >= totalPages || loading}
                onClick={() => setPage(prev => prev + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>


      {/* Status Transition Modal */}
      {leadForStatus && (
        <LeadStatusModal
          isOpen={Boolean(leadForStatus)}
          onClose={() => setLeadForStatus(null)}
          lead={leadForStatus}
          onStatusUpdated={() => {
            setLeadForStatus(null);
            fetchLeads();
          }}
        />
      )}
    </div>
  );
}
