import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Building2,
  Search,
  Plus,
  RefreshCw,
  Edit,
  ExternalLink,
  Phone,
  Mail,
  Globe,
  MapPin,
  X,
  Users,
  Layers,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  Calendar,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import crmService from '../services/crmService';

const DOMAIN_REGEX = /^(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:\/[^\s]*)?$/i;

export default function CrmAccountsPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const [accounts, setAccounts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modals & Drawers
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [accountToEdit, setAccountToEdit] = useState(null);
  const [selectedAccountDetail, setSelectedAccountDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Form states for Create/Edit Modal
  const [modalFormData, setModalFormData] = useState({
    name: '',
    siteName: '',
    industry: '',
    website: '',
    phone: '',
    email: '',
    address: '',
    location: '',
    isActive: true,
    confirmDuplicate: false
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  // Matching state
  const [matchingAccounts, setMatchingAccounts] = useState([]);
  const [isSearchingMatches, setIsSearchingMatches] = useState(false);

  const canCreate = hasPermission('crm.account.create');
  const canEdit = hasPermission('crm.account.edit') || hasPermission('crm.account.create');

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      };
      if (search.trim()) params.search = search.trim();

      const res = await crmService.getAccounts(params);
      if (res.data?.success) {
        setAccounts(res.data.accounts || []);
        setTotalCount(res.data.total || (res.data.accounts || []).length);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load accounts. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Debounced search for matching accounts as user types
  useEffect(() => {
    if (!isCreateModalOpen) {
      setMatchingAccounts([]);
      return;
    }
    const cleanName = modalFormData.name.trim();
    const cleanWeb = modalFormData.website.trim();
    if (cleanName.length < 2 && cleanWeb.length < 3) {
      setMatchingAccounts([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearchingMatches(true);
      try {
        const res = await crmService.getAccountMatches({
          name: cleanName || undefined,
          website: cleanWeb || undefined,
          email: modalFormData.email.trim() || undefined,
          excludeId: accountToEdit?.id
        });
        if (res.data?.success) {
          setMatchingAccounts(res.data.matches || []);
        }
      } catch {
        // non-blocking
      } finally {
        setIsSearchingMatches(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [modalFormData.name, modalFormData.website, modalFormData.email, isCreateModalOpen, accountToEdit]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchAccounts();
  };

  const handleClearSearch = () => {
    setSearch('');
    setPage(1);
  };

  const openCreateModal = () => {
    setAccountToEdit(null);
    setModalFormData({
      name: '',
      siteName: '',
      industry: '',
      website: '',
      phone: '',
      email: '',
      address: '',
      location: '',
      isActive: true,
      confirmDuplicate: false
    });
    setFormError(null);
    setFieldErrors({});
    setMatchingAccounts([]);
    setIsCreateModalOpen(true);
  };

  const openEditModal = (acc) => {
    setAccountToEdit(acc);
    setModalFormData({
      name: acc.name || '',
      siteName: acc.siteName || '',
      industry: acc.industry || '',
      website: acc.website || '',
      phone: acc.phone || '',
      email: acc.email || '',
      address: acc.address || '',
      location: acc.location || '',
      isActive: acc.isActive !== false,
      confirmDuplicate: false
    });
    setFormError(null);
    setFieldErrors({});
    setMatchingAccounts([]);
    setIsCreateModalOpen(true);
  };

  const openDetailDrawer = async (acc) => {
    setSelectedAccountDetail(acc);
    setLoadingDetail(true);
    try {
      const res = await crmService.getAccountById(acc.id);
      if (res.data?.success && res.data?.account) {
        setSelectedAccountDetail(res.data.account);
      }
    } catch {
      // keep fallback
    } finally {
      setLoadingDetail(false);
    }
  };

  const validateForm = () => {
    const errors = {};
    if (!modalFormData.name.trim()) {
      errors.name = 'Company / Account name is required.';
    }
    if (modalFormData.website.trim()) {
      const site = modalFormData.website.trim();
      const lower = site.toLowerCase();
      if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
        errors.website = 'Unsafe web protocols are not allowed.';
      } else if (!DOMAIN_REGEX.test(site)) {
        errors.website = 'Enter a valid domain or website URL (e.g. example.com).';
      }
    }
    if (modalFormData.email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(modalFormData.email.trim())) {
        errors.email = 'Enter a valid email address.';
      }
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveAccount = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setFormSubmitting(true);
    setFormError(null);

    const payload = {
      name: modalFormData.name.trim(),
      siteName: modalFormData.siteName.trim() || undefined,
      industry: modalFormData.industry.trim() || undefined,
      website: modalFormData.website.trim() || undefined,
      phone: modalFormData.phone.trim() || undefined,
      email: modalFormData.email.trim() || undefined,
      address: modalFormData.address.trim() || undefined,
      location: modalFormData.location.trim() || undefined,
      isActive: modalFormData.isActive,
      confirmDuplicate: Boolean(modalFormData.confirmDuplicate)
    };

    try {
      if (accountToEdit) {
        await crmService.updateAccount(accountToEdit.id, payload);
      } else {
        await crmService.createAccount(payload);
      }
      setIsCreateModalOpen(false);
      fetchAccounts();
      if (selectedAccountDetail && selectedAccountDetail.id === accountToEdit?.id) {
        openDetailDrawer({ ...selectedAccountDetail, ...payload });
      }
    } catch (err) {
      if (err.response?.status === 409) {
        const backendMatches = err.response.data?.details?.matches || [];
        if (backendMatches.length > 0) {
          setMatchingAccounts(backendMatches);
        }
        setFormError(
          err.response.data?.message ||
          'An account with this name already exists. If this is a legitimate distinct account, check the confirmation below to proceed.'
        );
      } else {
        setFormError(err.response?.data?.message || 'Failed to save account. Please check inputs.');
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="crm-leads-container">
      {/* Page Header */}
      <div className="crm-page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)'
          }}>
            <Building2 size={22} />
          </div>
          <div>
            <h1 className="crm-page-title" style={{ margin: 0 }}>Accounts Directory</h1>
            <p className="crm-page-subtitle" style={{ margin: 0 }}>
              Enterprise clients, industries, contacts, and linked enquiry leads
            </p>
          </div>
        </div>

        {canCreate && (
          <button onClick={openCreateModal} className="crm-btn crm-btn-primary">
            <Plus size={16} />
            <span>New Account</span>
          </button>
        )}
      </div>

      {/* Toolbar & Search */}
      <div className="crm-toolbar">
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group">
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by company name, account ID, industry, website, or location..."
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

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          <span>Total: <strong>{totalCount}</strong> Accounts</span>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          padding: '0.85rem 1rem',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '10px',
          color: '#b91c1c',
          marginBottom: '1rem',
          fontSize: '0.875rem'
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Table Container */}
      <div className="crm-table-container">
        <table className="crm-table">
          <thead>
            <tr>
              <th style={{ width: '130px' }}>Account ID</th>
              <th>Company Name</th>
              <th>Industry</th>
              <th>Website & Email</th>
              <th>Phone & Location</th>
              <th style={{ width: '100px' }}>Status</th>
              <th className="sticky-actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={26} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
                  <span>Loading accounts...</span>
                </td>
              </tr>
            ) : accounts.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                  <Building2 size={40} color="#cbd5e1" style={{ margin: '0 auto 0.85rem', display: 'block' }} />
                  <h4 style={{ margin: '0 0 0.4rem 0', color: 'var(--text-primary)', fontSize: '1.05rem' }}>No Accounts Found</h4>
                  <p style={{ margin: 0, fontSize: '0.875rem' }}>
                    {search ? `No accounts matching "${search}".` : 'No accounts registered yet. Click "New Account" to add one.'}
                  </p>
                </td>
              </tr>
            ) : (
              accounts.map(acc => (
                <tr key={acc.id}>
                  {/* Account ID */}
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => openDetailDrawer(acc)}
                      className="crm-lead-id-link"
                      title="View Account Details"
                    >
                      <span>{acc.accountId}</span>
                    </button>
                  </td>

                  {/* Name */}
                  <td>
                    <button
                      onClick={() => openDetailDrawer(acc)}
                      style={{ background: 'none', border: 'none', padding: 0, textAlign: 'left', cursor: 'pointer' }}
                      title="View Account Details"
                    >
                      <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {acc.name}
                      </span>
                    </button>
                    {acc.siteName && (
                      <div style={{ fontSize: '0.78rem', color: '#0284c7', fontWeight: 500 }}>
                        Site: {acc.siteName}
                      </div>
                    )}
                    {acc.address && (
                      <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <MapPin size={11} /> {acc.address}
                      </div>
                    )}
                  </td>

                  {/* Industry */}
                  <td>
                    {acc.industry ? (
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.78rem',
                        fontWeight: 600,
                        background: '#f1f5f9',
                        color: '#334155'
                      }}>
                        {acc.industry}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>—</span>
                    )}
                  </td>

                  {/* Website & Email */}
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.82rem' }}>
                      {acc.website && (
                        <a
                          href={acc.website.startsWith('http') ? acc.website : `https://${acc.website}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--accent-primary)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Globe size={12} /> {acc.website.replace(/^https?:\/\//, '')}
                        </a>
                      )}
                      {acc.email && (
                        <div style={{ color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Mail size={12} /> {acc.email}
                        </div>
                      )}
                      {!acc.website && !acc.email && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </div>
                  </td>

                  {/* Phone & Location */}
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.82rem' }}>
                      {acc.phone && (
                        <div style={{ color: 'var(--text-primary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Phone size={12} /> {acc.phone}
                        </div>
                      )}
                      {acc.location && (
                        <div style={{ color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <MapPin size={12} /> {acc.location}
                        </div>
                      )}
                      {!acc.phone && !acc.location && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </div>
                  </td>

                  {/* Status */}
                  <td>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: acc.isActive !== false ? '#ecfdf5' : '#f1f5f9',
                      color: acc.isActive !== false ? '#065f46' : '#64748b'
                    }}>
                      {acc.isActive !== false ? 'Active' : 'Inactive'}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="sticky-actions-col">
                    <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => openDetailDrawer(acc)}
                        className="crm-btn crm-btn-secondary crm-btn-sm"
                        title="View details"
                      >
                        View
                      </button>
                      {canEdit && (
                        <button
                          onClick={() => openEditModal(acc)}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          title="Edit Account"
                        >
                          <Edit size={13} />
                          <span>Edit</span>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div className="crm-pagination-wrap" style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Page {page} of {totalPages}
          </span>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="crm-btn crm-btn-secondary crm-btn-sm"
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="crm-btn crm-btn-secondary crm-btn-sm"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Create / Edit Account Modal */}
      {isCreateModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1100 }} onClick={() => setIsCreateModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '640px', width: '95%', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: '14px' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', background: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: '#eff6ff',
                  color: '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Building2 size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>
                    {accountToEdit ? `Edit Account — ${accountToEdit.accountId}` : 'Create New Account'}
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Enterprise organization details and primary communication channels
                  </span>
                </div>
              </div>
            </div>

            <form onSubmit={handleSaveAccount} noValidate style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
              <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {formError && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.6rem',
                    padding: '0.85rem 1rem',
                    background: '#fef2f2',
                    border: '1px solid #fecaca',
                    borderRadius: '10px',
                    color: '#b91c1c',
                    fontSize: '0.875rem'
                  }}>
                    <AlertCircle size={18} />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Company / Account Name <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-control ${fieldErrors.name ? 'is-invalid' : ''}`}
                    placeholder="e.g. Praj Industries Ltd."
                    value={modalFormData.name}
                    onChange={e => setModalFormData({ ...modalFormData, name: e.target.value })}
                    required
                  />
                  {fieldErrors.name && (
                    <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>{fieldErrors.name}</div>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Client Site Name</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Pune Plant / Unit 2"
                    value={modalFormData.siteName}
                    onChange={e => setModalFormData({ ...modalFormData, siteName: e.target.value })}
                  />
                  <small style={{ color: 'var(--text-muted)' }}>Facility, site, or branch name if this account represents a specific site</small>
                </div>

                {/* Potential Duplicate / Matching Accounts Panel */}
                {matchingAccounts.length > 0 && (
                  <div style={{
                    padding: '0.85rem 1rem',
                    background: '#fffbeb',
                    border: '1px solid #fde68a',
                    borderRadius: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.65rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#92400e', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <AlertCircle size={15} />
                        Potential Matching Accounts Found ({matchingAccounts.length})
                      </span>
                      {isSearchingMatches && (
                        <span style={{ fontSize: '0.75rem', color: '#b45309' }}>Searching...</span>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '160px', overflowY: 'auto' }}>
                      {matchingAccounts.map(m => (
                        <div key={m.id} style={{
                          padding: '0.6rem 0.8rem',
                          background: '#ffffff',
                          border: '1px solid #fef3c7',
                          borderRadius: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem'
                        }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1e293b' }}>{m.name}</span>
                              <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', background: '#eff6ff', padding: '1px 5px', borderRadius: '4px' }}>
                                {m.accountId}
                              </span>
                            </div>
                            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '2px' }}>
                              {m.matchReasons?.map((r, idx) => (
                                <span key={idx} style={{ fontSize: '0.7rem', background: '#fef3c7', color: '#92400e', padding: '1px 6px', borderRadius: '4px', fontWeight: 500 }}>
                                  {r}
                                </span>
                              ))}
                              {m.website && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{m.website}</span>}
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setIsCreateModalOpen(false);
                              openDetailDrawer(m);
                            }}
                            className="crm-btn crm-btn-secondary crm-btn-sm"
                            style={{ flexShrink: 0, fontSize: '0.75rem' }}
                          >
                            Select Existing
                          </button>
                        </div>
                      ))}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingTop: '0.25rem', borderTop: '1px dashed #fde68a' }}>
                      <input
                        type="checkbox"
                        id="confirmDuplicateAccount"
                        checked={modalFormData.confirmDuplicate}
                        onChange={e => setModalFormData({ ...modalFormData, confirmDuplicate: e.target.checked })}
                        style={{ width: '15px', height: '15px', cursor: 'pointer' }}
                      />
                      <label htmlFor="confirmDuplicateAccount" style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: '#78350f', cursor: 'pointer' }}>
                        This is a legitimate distinct account with a similar name
                      </label>
                    </div>
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Industry</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. Bio-Energy, Distilleries, Dairy"
                      value={modalFormData.industry}
                      onChange={e => setModalFormData({ ...modalFormData, industry: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Website</label>
                    <input
                      type="text"
                      className={`form-control ${fieldErrors.website ? 'is-invalid' : ''}`}
                      placeholder="e.g. praj.net"
                      value={modalFormData.website}
                      onChange={e => setModalFormData({ ...modalFormData, website: e.target.value })}
                    />
                    {fieldErrors.website && (
                      <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>{fieldErrors.website}</div>
                    )}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Company Phone</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. +91 20 7180 2000"
                      value={modalFormData.phone}
                      onChange={e => setModalFormData({ ...modalFormData, phone: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Company Email</label>
                    <input
                      type="email"
                      className={`form-control ${fieldErrors.email ? 'is-invalid' : ''}`}
                      placeholder="e.g. info@praj.net"
                      value={modalFormData.email}
                      onChange={e => setModalFormData({ ...modalFormData, email: e.target.value })}
                    />
                    {fieldErrors.email && (
                      <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>{fieldErrors.email}</div>
                    )}
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Office / Plant Location</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Pune, Maharashtra, India"
                    value={modalFormData.location}
                    onChange={e => setModalFormData({ ...modalFormData, location: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Street Address</label>
                  <textarea
                    className="form-control"
                    rows={2}
                    placeholder="Postal address, industrial estate, plot number..."
                    value={modalFormData.address}
                    onChange={e => setModalFormData({ ...modalFormData, address: e.target.value })}
                  />
                </div>

                {accountToEdit && (
                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                    <input
                      type="checkbox"
                      id="accountIsActive"
                      checked={modalFormData.isActive}
                      onChange={e => setModalFormData({ ...modalFormData, isActive: e.target.checked })}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    <label htmlFor="accountIsActive" style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' }}>
                      Account is Active
                    </label>
                  </div>
                )}
              </div>

              <div className="modal-footer" style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '0.65rem' }}>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="crm-btn crm-btn-secondary"
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="crm-btn crm-btn-primary"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? 'Saving...' : (accountToEdit ? 'Save Changes' : 'Create Account')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Account Detail Drawer / Modal */}
      {selectedAccountDetail && (
        <div className="modal-backdrop" style={{ zIndex: 1100 }} onClick={() => setSelectedAccountDetail(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '820px', width: '95%', maxHeight: '92vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: '14px' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', background: '#ffffff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: '#eff6ff',
                  color: '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Building2 size={22} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-primary)', background: '#eff6ff', padding: '2px 8px', borderRadius: '4px' }}>
                      {selectedAccountDetail.accountId}
                    </span>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                      {selectedAccountDetail.name}
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {selectedAccountDetail.industry || 'Enterprise Account'} • {selectedAccountDetail.isActive !== false ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {canEdit && (
                  <button
                    onClick={() => {
                      const acc = selectedAccountDetail;
                      setSelectedAccountDetail(null);
                      openEditModal(acc);
                    }}
                    className="crm-btn crm-btn-secondary crm-btn-sm"
                  >
                    <Edit size={13} /> Edit
                  </button>
                )}
                <button
                  onClick={() => setSelectedAccountDetail(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Account Meta Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Client Site Name</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#0369a1', marginTop: '2px' }}>
                    {selectedAccountDetail.siteName || '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Website</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedAccountDetail.website ? (
                      <a
                        href={selectedAccountDetail.website.startsWith('http') ? selectedAccountDetail.website : `https://${selectedAccountDetail.website}`}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--accent-primary)', textDecoration: 'none' }}
                      >
                        {selectedAccountDetail.website}
                      </a>
                    ) : '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Phone</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedAccountDetail.phone || '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Email</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedAccountDetail.email || '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Location / Address</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {[selectedAccountDetail.location, selectedAccountDetail.address].filter(Boolean).join(' • ') || '—'}
                  </div>
                </div>
              </div>

              {/* Related Contacts Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                    <Users size={16} color="var(--accent-primary)" />
                    <span>Associated Contacts ({selectedAccountDetail.contacts?.length || 0})</span>
                  </h4>
                </div>

                {loadingDetail ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    Loading linked contacts...
                  </div>
                ) : !selectedAccountDetail.contacts || selectedAccountDetail.contacts.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No contacts linked to this account yet.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
                    {selectedAccountDetail.contacts.map(contact => (
                      <div key={contact.id} style={{
                        padding: '0.75rem 1rem',
                        background: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '2px'
                      }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                          {contact.name}
                        </div>
                        {contact.designation && (
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{contact.designation}</div>
                        )}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          {contact.email && <div><Mail size={11} style={{ verticalAlign: 'middle', marginRight: '3px' }} />{contact.email}</div>}
                          {contact.mobileNumber && <div><Phone size={11} style={{ verticalAlign: 'middle', marginRight: '3px' }} />{contact.mobileNumber}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Related Leads Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                    <Layers size={16} color="var(--accent-primary)" />
                    <span>Enquiry Leads ({selectedAccountDetail.leads?.length || 0})</span>
                  </h4>
                </div>

                {loadingDetail ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    Loading linked leads...
                  </div>
                ) : !selectedAccountDetail.leads || selectedAccountDetail.leads.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No leads associated with this account.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {selectedAccountDetail.leads.map(lead => (
                      <div
                        key={lead.id}
                        style={{
                          padding: '0.75rem 1rem',
                          background: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '1rem'
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                              {lead.leadId}
                            </span>
                            <span style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                              {lead.leadName || lead.displayName || lead.leadId}
                            </span>
                            <span style={{
                              padding: '1px 6px',
                              borderRadius: '4px',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              background: lead.businessArea === 'Biogas' ? '#fef3c7' : '#e0f2fe',
                              color: lead.businessArea === 'Biogas' ? '#b45309' : '#0369a1'
                            }}>
                              {lead.businessArea}
                            </span>
                          </div>
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            Requirement: {lead.requirementTypes && lead.requirementTypes.length > 0 ? lead.requirementTypes.join(', ') : lead.requirementType} • Status: {lead.lifecycleStatus}
                          </div>
                        </div>

                        <button
                          onClick={() => {
                            setSelectedAccountDetail(null);
                            navigate(`/crm/leads/${lead.id}`);
                          }}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          style={{ flexShrink: 0 }}
                        >
                          View Lead <ExternalLink size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Related Opportunities Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                    <Briefcase size={16} color="var(--accent-primary)" />
                    <span>Associated Opportunities ({selectedAccountDetail.opportunities?.length || 0})</span>
                  </h4>
                </div>

                {!selectedAccountDetail.opportunities || selectedAccountDetail.opportunities.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No opportunities associated with this account.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
                    {selectedAccountDetail.opportunities.map(opp => (
                      <div key={opp.id} style={{
                        padding: '0.75rem 1rem',
                        background: '#ffffff',
                        border: '1px solid #e2e8f0',
                        borderRadius: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)', background: '#eff6ff', padding: '1px 6px', borderRadius: '4px' }}>
                            {opp.opportunityId}
                          </span>
                          <span style={{
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: '12px',
                            background: opp.status === 'Won' ? '#dcfce7' : opp.status === 'Lost' ? '#fee2e2' : '#e0e7ff',
                            color: opp.status === 'Won' ? '#15803d' : opp.status === 'Lost' ? '#b91c1c' : '#3730a3'
                          }}>
                            {opp.status}
                          </span>
                        </div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                          {opp.name}
                        </div>
                        {opp.estimatedValue != null && (
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            Value: {opp.currency || 'INR'} {Number(opp.estimatedValue).toLocaleString()}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="modal-footer" style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setSelectedAccountDetail(null)}
                className="crm-btn crm-btn-secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
