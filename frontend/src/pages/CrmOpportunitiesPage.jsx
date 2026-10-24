import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Briefcase,
  Search,
  RefreshCw,
  ExternalLink,
  Building,
  User,
  X,
  Layers,
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  FileText
} from 'lucide-react';
import crmService from '../services/crmService';

export default function CrmOpportunitiesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { hasPermission } = useAuth();

  const urlSearch = searchParams.get('search') || '';

  const [opportunities, setOpportunities] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [search, setSearch] = useState(urlSearch);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Detail Modal
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const fetchOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      };
      if (search.trim()) params.search = search.trim();
      if (statusFilter !== 'ALL') params.status = statusFilter;

      const res = await crmService.getOpportunities(params);
      if (res.data?.success) {
        setOpportunities(res.data.opportunities || []);
        setTotalCount(res.data.count || (res.data.opportunities || []).length);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load opportunities. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchOpportunities();
  }, [fetchOpportunities]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchOpportunities();
  };

  const handleClearSearch = () => {
    setSearch('');
    setPage(1);
  };

  const handleOpenDetail = async (opp) => {
    setSelectedOpportunity(opp);
    setLoadingDetail(true);
    try {
      const res = await crmService.getOpportunityById(opp.id);
      if (res.data?.success) {
        setSelectedOpportunity(res.data.opportunity);
      }
    } catch (err) {
      console.error('Failed to load full opportunity detail:', err);
    } finally {
      setLoadingDetail(false);
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

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="crm-page-container">
      {/* Top Header Command Bar */}
      <div className="crm-page-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            <Link to="/crm/dashboard" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>CRM</Link>
            <span>/</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Opportunities</span>
          </div>
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
              <Briefcase size={22} />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                Opportunities
              </h1>
              <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Qualified sales pipeline created through Lead qualification
              </p>
            </div>
          </div>
        </div>

        <div className="crm-page-header-actions">
          <button
            onClick={fetchOpportunities}
            className="crm-btn crm-btn-secondary"
            title="Refresh Opportunities"
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Toolbar & Filters */}
      <div className="crm-toolbar" style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group" style={{ flex: 1, minWidth: '260px' }}>
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by Opportunity ID, Name, Account..."
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="form-control"
            style={{ minWidth: '130px', height: '38px', fontSize: '0.85rem' }}
          >
            <option value="ALL">All Statuses</option>
            <option value="Open">Open</option>
            <option value="Won">Won</option>
            <option value="Lost">Lost</option>
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

      {/* Table Card */}
      <div className="glass-panel" style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="crm-table">
            <thead>
              <tr>
                <th style={{ width: '130px' }}>Opportunity ID</th>
                <th style={{ minWidth: '220px' }}>Opportunity Name</th>
                <th style={{ minWidth: '200px' }}>Account</th>
                <th style={{ minWidth: '180px' }}>Primary Contact</th>
                <th style={{ width: '140px' }}>Estimated Value</th>
                <th style={{ width: '110px' }}>Status</th>
                <th style={{ minWidth: '140px' }}>Originating Lead</th>
                <th style={{ width: '100px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)' }}>
                    <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
                    <span>Loading opportunities...</span>
                  </td>
                </tr>
              ) : opportunities.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                    <Briefcase size={36} color="#cbd5e1" style={{ margin: '0 auto 0.75rem', display: 'block' }} />
                    <h4 style={{ margin: '0 0 0.35rem', color: 'var(--text-primary)', fontSize: '1rem' }}>No Opportunities Found</h4>
                    <p style={{ margin: 0, fontSize: '0.85rem' }}>
                      {search.trim() || statusFilter !== 'ALL'
                        ? 'No opportunities match your filter criteria.'
                        : 'Opportunities are created when Leads are qualified through the Qualify Lead workflow.'}
                    </p>
                  </td>
                </tr>
              ) : (
                opportunities.map((opp) => (
                  <tr key={opp.id}>
                    {/* Opportunity ID */}
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <button
                        onClick={() => handleOpenDetail(opp)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-primary)',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          padding: 0
                        }}
                        title="View Opportunity Details"
                      >
                        {opp.opportunityId}
                      </button>
                    </td>

                    {/* Name & Scope */}
                    <td>
                      <button
                        onClick={() => handleOpenDetail(opp)}
                        style={{
                          background: 'none',
                          border: 'none',
                          padding: 0,
                          textAlign: 'left',
                          font: 'inherit',
                          cursor: 'pointer'
                        }}
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

                    {/* Account */}
                    <td>
                      {opp.accountName ? (
                        <Link
                          to={`/crm/accounts?search=${encodeURIComponent(opp.accountName)}`}
                          style={{
                            color: 'var(--text-primary)',
                            fontWeight: 600,
                            textDecoration: 'none',
                            fontSize: '0.875rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}
                        >
                          <Building size={14} color="#d97706" />
                          <span>{opp.accountName}</span>
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>
                      )}
                    </td>

                    {/* Contact */}
                    <td>
                      {opp.contactName ? (
                        <Link
                          to={`/crm/contacts?search=${encodeURIComponent(opp.contactName)}`}
                          style={{
                            color: 'var(--text-primary)',
                            textDecoration: 'none',
                            fontSize: '0.875rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}
                        >
                          <User size={14} color="var(--accent-primary)" />
                          <span>{opp.contactName}</span>
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>
                      )}
                    </td>

                    {/* Estimated Value */}
                    <td style={{ whiteSpace: 'nowrap', fontWeight: 600, fontSize: '0.875rem' }}>
                      {opp.estimatedValue !== null && opp.estimatedValue !== undefined ? (
                        <span>
                          {opp.currency || 'INR'} {Number(opp.estimatedValue).toLocaleString()}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontStyle: 'italic' }}>
                          Not specified
                        </span>
                      )}
                    </td>

                    {/* Status */}
                    <td>
                      {getStatusBadge(opp.status)}
                    </td>

                    {/* Originating Lead */}
                    <td>
                      {opp.originatingLeadId ? (
                        <Link
                          to={`/crm/leads/${opp.originatingLeadId}`}
                          style={{
                            color: 'var(--accent-primary)',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            textDecoration: 'none',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem'
                          }}
                        >
                          <Layers size={13} />
                          <span>{opp.originatingLeadNumber || 'View Lead'}</span>
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Direct Opportunity</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <button
                        onClick={() => handleOpenDetail(opp)}
                        className="crm-btn crm-btn-secondary crm-btn-sm"
                        title="View Opportunity Details"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server-Side Pagination Footer */}
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

      {/* Opportunity Details Modal */}
      {selectedOpportunity && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setSelectedOpportunity(null)}>
          <div
            className="modal-content"
            style={{
              maxWidth: '640px',
              width: '92%',
              borderRadius: '12px',
              padding: '1.75rem',
              background: '#ffffff',
              boxShadow: 'var(--modal-shadow)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
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
                  <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {selectedOpportunity.name}
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Opportunity ID: <strong style={{ color: 'var(--text-primary)' }}>{selectedOpportunity.opportunityId}</strong>
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedOpportunity(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.3rem', color: 'var(--text-muted)', cursor: 'pointer', lineHeight: 1 }}
                title="Close"
              >
                ✕
              </button>
            </div>

            {loadingDetail ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                <RefreshCw size={20} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <span>Loading details...</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem' }}>
                {/* Status & Value Row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', background: '#f8fafc', padding: '0.85rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Status
                    </label>
                    <div style={{ marginTop: '0.2rem' }}>
                      {getStatusBadge(selectedOpportunity.status)}
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Estimated Value
                    </label>
                    <div style={{ marginTop: '0.2rem', fontWeight: 700, fontSize: '1rem', color: '#0f172a' }}>
                      {selectedOpportunity.estimatedValue !== null && selectedOpportunity.estimatedValue !== undefined ? (
                        `${selectedOpportunity.currency || 'INR'} ${Number(selectedOpportunity.estimatedValue).toLocaleString()}`
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontStyle: 'italic', fontSize: '0.875rem' }}>Not specified</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Account & Contact Row */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Associated Account
                    </label>
                    <div style={{ marginTop: '0.25rem' }}>
                      {selectedOpportunity.accountName ? (
                        <Link
                          to={`/crm/accounts?search=${encodeURIComponent(selectedOpportunity.accountName)}`}
                          style={{ color: 'var(--accent-primary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                        >
                          <Building size={14} color="#d97706" />
                          <span>{selectedOpportunity.accountName}</span>
                          <ExternalLink size={12} />
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Primary Contact
                    </label>
                    <div style={{ marginTop: '0.25rem' }}>
                      {selectedOpportunity.contactName ? (
                        <Link
                          to={`/crm/contacts?search=${encodeURIComponent(selectedOpportunity.contactName)}`}
                          style={{ color: 'var(--accent-primary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                        >
                          <User size={14} />
                          <span>{selectedOpportunity.contactName}</span>
                          <ExternalLink size={12} />
                        </Link>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Originating Lead */}
                {selectedOpportunity.originatingLeadId && (
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Originating Lead
                    </label>
                    <div style={{ marginTop: '0.25rem' }}>
                      <Link
                        to={`/crm/leads/${selectedOpportunity.originatingLeadId}`}
                        style={{ color: 'var(--accent-primary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                      >
                        <Layers size={14} />
                        <span>Lead Record {selectedOpportunity.originatingLeadNumber ? `(${selectedOpportunity.originatingLeadNumber})` : ''}</span>
                        <ExternalLink size={12} />
                      </Link>
                    </div>
                  </div>
                )}

                {/* Requirement Types */}
                {selectedOpportunity.requirementTypes && selectedOpportunity.requirementTypes.length > 0 && (
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Requirement Types
                    </label>
                    <div style={{ display: 'flex', gap: '6px', marginTop: '0.25rem', flexWrap: 'wrap' }}>
                      {selectedOpportunity.requirementTypes.map(rt => (
                        <span key={rt} style={{ padding: '2px 8px', borderRadius: '4px', background: '#f1f5f9', color: '#334155', fontWeight: 600, fontSize: '0.8rem' }}>
                          {rt}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Description / Scope */}
                {selectedOpportunity.description && (
                  <div>
                    <label style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>
                      Scope / Description
                    </label>
                    <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', background: '#f8fafc', padding: '0.75rem', borderRadius: '6px', border: '1px solid #f1f5f9', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                      {selectedOpportunity.description}
                    </p>
                  </div>
                )}

                {/* Audit Governance Row */}
                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <div>
                    <span>Owner: </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{selectedOpportunity.assignedToName || 'Unassigned'}</strong>
                  </div>
                  <div>
                    <span>Created: </span>
                    <strong style={{ color: 'var(--text-primary)' }}>{selectedOpportunity.createdAt ? new Date(selectedOpportunity.createdAt).toLocaleDateString() : '—'}</strong>
                  </div>
                </div>

                {/* Modal Footer Actions */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setSelectedOpportunity(null)}
                  >
                    Close
                  </button>
                  {selectedOpportunity.originatingLeadId && (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => navigate(`/crm/leads/${selectedOpportunity.originatingLeadId}`)}
                    >
                      View Originating Lead
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
