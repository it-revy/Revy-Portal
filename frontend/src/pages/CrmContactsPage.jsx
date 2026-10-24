import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Contact,
  Search,
  Plus,
  RefreshCw,
  Edit,
  ExternalLink,
  Phone,
  Mail,
  Building,
  Briefcase,
  X,
  Layers,
  AlertCircle,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import crmService from '../services/crmService';

export default function CrmContactsPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const [contacts, setContacts] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [search, setSearch] = useState('');
  const [filterAccountId, setFilterAccountId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modals & Drawers
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [contactToEdit, setContactToEdit] = useState(null);
  const [selectedContactDetail, setSelectedContactDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Form states for Create/Edit Modal
  const [modalFormData, setModalFormData] = useState({
    name: '',
    designation: '',
    email: '',
    mobileNumber: '',
    accountId: '',
    isActive: true,
    confirmDuplicate: false
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  // Matching state
  const [matchingContacts, setMatchingContacts] = useState([]);
  const [isSearchingMatches, setIsSearchingMatches] = useState(false);

  const canCreate = hasPermission('crm.contact.create');
  const canEdit = hasPermission('crm.contact.edit') || hasPermission('crm.contact.create');

  // Load account lookup options
  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const res = await crmService.getAccounts({ limit: 200 });
        if (res.data?.success) {
          setAccounts(res.data.accounts || []);
        }
      } catch {
        // non-blocking
      }
    };
    loadAccounts();
  }, []);

  const fetchContacts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        includeUnassigned: true
      };
      if (search.trim()) params.search = search.trim();
      if (filterAccountId) params.accountId = filterAccountId;

      const res = await crmService.getContacts(params);
      if (res.data?.success) {
        setContacts(res.data.contacts || []);
        setTotalCount(res.data.total || (res.data.contacts || []).length);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load contacts. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [page, search, filterAccountId]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  // Debounced search for matching contacts
  useEffect(() => {
    if (!isModalOpen) {
      setMatchingContacts([]);
      return;
    }
    const cleanEmail = modalFormData.email.trim();
    const cleanPhone = modalFormData.mobileNumber.trim();
    const cleanName = modalFormData.name.trim();

    if (!cleanEmail && cleanPhone.length < 6 && cleanName.length < 3) {
      setMatchingContacts([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearchingMatches(true);
      try {
        const res = await crmService.getContactMatches({
          name: cleanName || undefined,
          email: cleanEmail || undefined,
          mobileNumber: cleanPhone || undefined,
          accountId: modalFormData.accountId || undefined,
          excludeId: contactToEdit?.id
        });
        if (res.data?.success) {
          setMatchingContacts(res.data.matches || []);
        }
      } catch {
        // non-blocking
      } finally {
        setIsSearchingMatches(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [modalFormData.email, modalFormData.mobileNumber, modalFormData.name, modalFormData.accountId, isModalOpen, contactToEdit]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchContacts();
  };

  const handleClearSearch = () => {
    setSearch('');
    setPage(1);
  };

  const openCreateModal = () => {
    setContactToEdit(null);
    setModalFormData({
      name: '',
      designation: '',
      email: '',
      mobileNumber: '',
      accountId: filterAccountId || '',
      isActive: true,
      confirmDuplicate: false
    });
    setFormError(null);
    setFieldErrors({});
    setMatchingContacts([]);
    setIsModalOpen(true);
  };

  const openEditModal = (c) => {
    setContactToEdit(c);
    setModalFormData({
      name: c.name || '',
      designation: c.designation || '',
      email: c.email || '',
      mobileNumber: c.mobileNumber || '',
      accountId: c.accountId || c.account?.id || '',
      isActive: c.isActive !== false,
      confirmDuplicate: false
    });
    setFormError(null);
    setFieldErrors({});
    setMatchingContacts([]);
    setIsModalOpen(true);
  };

  const openDetailDrawer = async (c) => {
    setSelectedContactDetail(c);
    setLoadingDetail(true);
    try {
      const res = await crmService.getContactById(c.id);
      if (res.data?.success && res.data?.contact) {
        setSelectedContactDetail(res.data.contact);
      }
    } catch {
      // fallback
    } finally {
      setLoadingDetail(false);
    }
  };

  const validateForm = () => {
    const errors = {};
    if (!modalFormData.name.trim()) {
      errors.name = 'Contact full name is required.';
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

  const handleSaveContact = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setFormSubmitting(true);
    setFormError(null);

    const payload = {
      name: modalFormData.name.trim(),
      designation: modalFormData.designation.trim() || undefined,
      email: modalFormData.email.trim() || undefined,
      mobileNumber: modalFormData.mobileNumber.trim() || undefined,
      accountId: modalFormData.accountId || (contactToEdit ? null : undefined),
      isActive: modalFormData.isActive,
      confirmDuplicate: Boolean(modalFormData.confirmDuplicate)
    };

    try {
      if (contactToEdit) {
        await crmService.updateContact(contactToEdit.id, payload);
      } else {
        await crmService.createContact(payload);
      }
      setIsModalOpen(false);
      fetchContacts();
      if (selectedContactDetail && selectedContactDetail.id === contactToEdit?.id) {
        openDetailDrawer({ ...selectedContactDetail, ...payload });
      }
    } catch (err) {
      if (err.response?.status === 409) {
        const backendMatches = err.response.data?.details?.matches || [];
        if (backendMatches.length > 0) {
          setMatchingContacts(backendMatches);
        }
        setFormError(
          err.response.data?.message ||
          'A contact with this email or mobile number already exists. If this is a legitimate distinct contact, check the confirmation below to proceed.'
        );
      } else {
        setFormError(err.response?.data?.message || 'Failed to save contact. Please check inputs.');
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
            background: 'linear-gradient(135deg, #10b981, #059669)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.25)'
          }}>
            <Contact size={22} />
          </div>
          <div>
            <h1 className="crm-page-title" style={{ margin: 0 }}>Contacts Directory</h1>
            <p className="crm-page-subtitle" style={{ margin: 0 }}>
              Individual client stakeholders, designations, and associated enterprise accounts
            </p>
          </div>
        </div>

        {canCreate && (
          <button onClick={openCreateModal} className="crm-btn crm-btn-primary">
            <Plus size={16} />
            <span>New Contact</span>
          </button>
        )}
      </div>

      {/* Toolbar & Filters */}
      <div className="crm-toolbar">
        <form onSubmit={handleSearchSubmit} className="crm-toolbar-search-group">
          <div className="crm-search-input-wrap">
            <Search size={16} className="crm-search-icon" />
            <input
              type="text"
              className="form-control crm-search-input"
              placeholder="Search by contact name, contact ID, email, phone, designation..."
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

        <div className="crm-toolbar-filters">
          <div className="crm-filter-item">
            <label className="crm-filter-label">Filter Account:</label>
            <select
              className="form-control crm-select-sm"
              style={{ width: 'auto', minWidth: '180px' }}
              value={filterAccountId}
              onChange={e => {
                setFilterAccountId(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Accounts</option>
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.accountId})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          <span>Total: <strong>{totalCount}</strong> Contacts</span>
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

      {/* Contacts Table */}
      <div className="crm-table-container">
        <table className="crm-table">
          <thead>
            <tr>
              <th style={{ width: '130px' }}>Contact ID</th>
              <th>Full Name & Designation</th>
              <th>Linked Account</th>
              <th>Email Address</th>
              <th>Mobile Number</th>
              <th style={{ width: '100px' }}>Status</th>
              <th className="sticky-actions-col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-secondary)' }}>
                  <RefreshCw size={26} className="spin" style={{ margin: '0 auto 0.75rem', display: 'block', color: 'var(--accent-primary)' }} />
                  <span>Loading contacts...</span>
                </td>
              </tr>
            ) : contacts.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '4rem 1rem', color: 'var(--text-muted)' }}>
                  <Contact size={40} color="#cbd5e1" style={{ margin: '0 auto 0.85rem', display: 'block' }} />
                  <h4 style={{ margin: '0 0 0.4rem 0', color: 'var(--text-primary)', fontSize: '1.05rem' }}>No Contacts Found</h4>
                  <p style={{ margin: 0, fontSize: '0.875rem' }}>
                    {search ? `No contacts matching "${search}".` : 'No contacts found. Click "New Contact" to add one.'}
                  </p>
                </td>
              </tr>
            ) : (
              contacts.map(c => (
                <tr key={c.id}>
                  {/* Contact ID */}
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => openDetailDrawer(c)}
                      className="crm-lead-id-link"
                      title="View Contact Details"
                    >
                      <span>{c.contactId}</span>
                    </button>
                  </td>

                  {/* Name & Designation */}
                  <td>
                    <button
                      onClick={() => openDetailDrawer(c)}
                      style={{ background: 'none', border: 'none', padding: 0, textAlign: 'left', cursor: 'pointer' }}
                      title="View Contact Details"
                    >
                      <span style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {c.name}
                      </span>
                    </button>
                    {c.designation && (
                      <div className="crm-cell-secondary" style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Briefcase size={11} /> {c.designation}
                      </div>
                    )}
                  </td>

                  {/* Linked Account */}
                  <td>
                    {c.account?.name || c.accountName ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem', fontWeight: 500, color: '#1e293b' }}>
                        <Building size={13} color="var(--accent-primary)" />
                        <span>{c.account?.name || c.accountName}</span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
                        Direct Contact (No Account)
                      </span>
                    )}
                  </td>

                  {/* Email */}
                  <td>
                    {c.email ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                        <Mail size={12} color="var(--text-muted)" />
                        <span>{c.email}</span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>—</span>
                    )}
                  </td>

                  {/* Phone */}
                  <td>
                    {c.mobileNumber ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.82rem', color: 'var(--text-primary)' }}>
                        <Phone size={12} color="var(--text-muted)" />
                        <span>{c.mobileNumber}</span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      background: c.isActive !== false ? '#ecfdf5' : '#f1f5f9',
                      color: c.isActive !== false ? '#065f46' : '#64748b'
                    }}>
                      {c.isActive !== false ? 'Active' : 'Inactive'}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="sticky-actions-col">
                    <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => openDetailDrawer(c)}
                        className="crm-btn crm-btn-secondary crm-btn-sm"
                        title="View details"
                      >
                        View
                      </button>
                      {canEdit && (
                        <button
                          onClick={() => openEditModal(c)}
                          className="crm-btn crm-btn-secondary crm-btn-sm"
                          title="Edit Contact"
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

      {/* Create / Edit Contact Modal */}
      {isModalOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1100 }} onClick={() => setIsModalOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '600px', width: '95%', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: '14px' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', background: '#ffffff' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: '#ecfdf5',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Contact size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>
                    {contactToEdit ? `Edit Contact — ${contactToEdit.contactId}` : 'Create New Contact'}
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Client stakeholder details and enterprise account linkage
                  </span>
                </div>
              </div>
            </div>

            <form onSubmit={handleSaveContact} noValidate style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
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
                    Full Name <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <input
                    type="text"
                    className={`form-control ${fieldErrors.name ? 'is-invalid' : ''}`}
                    placeholder="e.g. Dr. Rajesh Sharma"
                    value={modalFormData.name}
                    onChange={e => setModalFormData({ ...modalFormData, name: e.target.value })}
                    required
                  />
                  {fieldErrors.name && (
                    <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>{fieldErrors.name}</div>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Designation / Title</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Chief Technical Officer, Plant Manager"
                    value={modalFormData.designation}
                    onChange={e => setModalFormData({ ...modalFormData, designation: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Associate with Account (Company)</label>
                  <select
                    className="form-control"
                    value={modalFormData.accountId}
                    onChange={e => setModalFormData({ ...modalFormData, accountId: e.target.value })}
                  >
                    <option value="">-- No Account (Independent / Direct Client) --</option>
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>
                        {acc.name} ({acc.accountId})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Email Address</label>
                    <input
                      type="email"
                      className={`form-control ${fieldErrors.email ? 'is-invalid' : ''}`}
                      placeholder="e.g. rajesh.sharma@example.com"
                      value={modalFormData.email}
                      onChange={e => setModalFormData({ ...modalFormData, email: e.target.value })}
                    />
                    {fieldErrors.email && (
                      <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>{fieldErrors.email}</div>
                    )}
                  </div>

                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>Mobile Number</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="e.g. +91 98765 43210"
                      value={modalFormData.mobileNumber}
                      onChange={e => setModalFormData({ ...modalFormData, mobileNumber: e.target.value })}
                    />
                  </div>
                </div>

                {/* Potential Duplicate / Matching Contacts Panel */}
                {matchingContacts.length > 0 && (
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
                        Potential Matching Contacts Found ({matchingContacts.length})
                      </span>
                      {isSearchingMatches && (
                        <span style={{ fontSize: '0.75rem', color: '#b45309' }}>Searching...</span>
                      )}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '160px', overflowY: 'auto' }}>
                      {matchingContacts.map(m => (
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
                              <span style={{ fontSize: '0.75rem', color: '#059669', background: '#ecfdf5', padding: '1px 5px', borderRadius: '4px' }}>
                                {m.contactId}
                              </span>
                              {m.accountName && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>({m.accountName})</span>
                              )}
                            </div>
                            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '2px' }}>
                              {m.matchReasons?.map((r, idx) => (
                                <span key={idx} style={{ fontSize: '0.7rem', background: '#fef3c7', color: '#92400e', padding: '1px 6px', borderRadius: '4px', fontWeight: 500 }}>
                                  {r}
                                </span>
                              ))}
                              {m.email && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{m.email}</span>}
                              {m.mobileNumber && <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{m.mobileNumber}</span>}
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setIsModalOpen(false);
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
                        id="confirmDuplicateContact"
                        checked={modalFormData.confirmDuplicate}
                        onChange={e => setModalFormData({ ...modalFormData, confirmDuplicate: e.target.checked })}
                        style={{ width: '15px', height: '15px', cursor: 'pointer' }}
                      />
                      <label htmlFor="confirmDuplicateContact" style={{ margin: 0, fontSize: '0.8rem', fontWeight: 600, color: '#78350f', cursor: 'pointer' }}>
                        This is a legitimate distinct contact with the same contact info
                      </label>
                    </div>
                  </div>
                )}

                {contactToEdit && (
                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                    <input
                      type="checkbox"
                      id="contactIsActive"
                      checked={modalFormData.isActive}
                      onChange={e => setModalFormData({ ...modalFormData, isActive: e.target.checked })}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    <label htmlFor="contactIsActive" style={{ margin: 0, fontSize: '0.9rem', fontWeight: 600, cursor: 'pointer' }}>
                      Contact is Active
                    </label>
                  </div>
                )}
              </div>

              <div className="modal-footer" style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', background: '#f8fafc', display: 'flex', justifyContent: 'flex-end', gap: '0.65rem' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
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
                  {formSubmitting ? 'Saving...' : (contactToEdit ? 'Save Changes' : 'Create Contact')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Contact Detail Modal */}
      {selectedContactDetail && (
        <div className="modal-backdrop" style={{ zIndex: 1100 }} onClick={() => setSelectedContactDetail(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '780px', width: '95%', maxHeight: '90vh', overflow: 'hidden', display: 'flex', flexDirection: 'column', borderRadius: '14px' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', background: '#ffffff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: '#ecfdf5',
                  color: '#059669',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Contact size={22} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#059669', background: '#ecfdf5', padding: '2px 8px', borderRadius: '4px' }}>
                      {selectedContactDetail.contactId}
                    </span>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                      {selectedContactDetail.name}
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {selectedContactDetail.designation || 'Stakeholder'} • {selectedContactDetail.isActive !== false ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {canEdit && (
                  <button
                    onClick={() => {
                      const c = selectedContactDetail;
                      setSelectedContactDetail(null);
                      openEditModal(c);
                    }}
                    className="crm-btn crm-btn-secondary crm-btn-sm"
                  >
                    <Edit size={13} /> Edit
                  </button>
                )}
                <button
                  onClick={() => setSelectedContactDetail(null)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Meta Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: '#f8fafc', padding: '1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Linked Account</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '2px', color: '#1e293b' }}>
                    {selectedContactDetail.account?.name || selectedContactDetail.accountName || 'Direct Contact (No Account)'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Email Address</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedContactDetail.email || '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Mobile Number</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedContactDetail.mobileNumber || '—'}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Designation</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500, marginTop: '2px' }}>
                    {selectedContactDetail.designation || '—'}
                  </div>
                </div>
              </div>

              {/* Associated Leads Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                    <Layers size={16} color="var(--accent-primary)" />
                    <span>Related Enquiry Leads ({selectedContactDetail.leads?.length || 0})</span>
                  </h4>
                </div>

                {loadingDetail ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                    <RefreshCw size={18} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    Loading related leads...
                  </div>
                ) : !selectedContactDetail.leads || selectedContactDetail.leads.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No leads associated with this contact yet.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {selectedContactDetail.leads.map(lead => (
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
                            setSelectedContactDetail(null);
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

              {/* Associated Opportunities Section */}
              <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e293b' }}>
                    <Briefcase size={16} color="var(--accent-primary)" />
                    <span>Associated Opportunities ({selectedContactDetail.opportunities?.length || 0})</span>
                  </h4>
                </div>

                {!selectedContactDetail.opportunities || selectedContactDetail.opportunities.length === 0 ? (
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No opportunities associated with this contact.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.75rem' }}>
                    {selectedContactDetail.opportunities.map(opp => (
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
                onClick={() => setSelectedContactDetail(null)}
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
