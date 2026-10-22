import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layers,
  Building,
  User,
  Plus,
  AlertCircle,
  ExternalLink,
  Globe,
  Calendar,
  CheckCircle2,
  FileText
} from 'lucide-react';
import crmService from '../../../services/crmService';
import QuickAccountModal from './QuickAccountModal';
import QuickContactModal from './QuickContactModal';

const DOMAIN_REGEX = /^(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:\/[^\s]*)?$/i;

export const ACTIVE_LEAD_SOURCES = ['Email Received'];

export const REQUIREMENT_TYPE_OPTIONS = ['Consulting', 'Sample Testing', 'Product'];

export const parseRequirementTypes = (lead) => {
  if (!lead) return ['Sample Testing'];
  if (Array.isArray(lead.requirementTypes) && lead.requirementTypes.length > 0) {
    return lead.requirementTypes;
  }
  if (lead.requirementType) {
    if (lead.requirementType === 'Direct Product/Service') return ['Product'];
    if (lead.requirementType === 'Undetermined') return ['Consulting'];
    if (REQUIREMENT_TYPE_OPTIONS.includes(lead.requirementType)) return [lead.requirementType];
    return ['Sample Testing'];
  }
  return ['Sample Testing'];
};

export default function LeadModal({
  isOpen,
  onClose,
  onLeadSaved,
  leadToEdit = null
}) {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    leadName: '',
    businessArea: 'Biogas',
    requirementTypes: ['Sample Testing'],
    requirementType: 'Sample Testing',
    requestedProductService: '',
    requirementSummary: '',
    leadSource: 'Email Received',
    connectedDate: '',
    communicationChannel: 'Email',
    accountId: '',
    contactId: '',
    additionalContactIds: [],
    assignedToUserId: '',
    remarks: '',
    nextFollowUpDate: '',
    nextFollowUpAction: '',
    location: '',
    siteName: ''
  });

  const [accounts, setAccounts] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [assignees, setAssignees] = useState([]);

  const [isQuickAccountOpen, setIsQuickAccountOpen] = useState(false);
  const [isQuickContactOpen, setIsQuickContactOpen] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [duplicateConflict, setDuplicateConflict] = useState(null);

  const isEdit = Boolean(leadToEdit);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    setError(null);
    setFieldErrors({});
    setDuplicateConflict(null);
    loadInitialData();

      if (leadToEdit) {
        const initialReqs = parseRequirementTypes(leadToEdit);
        const additionalIds = leadToEdit.additionalContactIds || (Array.isArray(leadToEdit.additionalContacts) ? leadToEdit.additionalContacts.map(c => c.id) : []);
        setFormData({
          leadName: leadToEdit.leadName || '',
          businessArea: leadToEdit.businessArea || 'Biogas',
          requirementTypes: initialReqs,
          requirementType: initialReqs[0] || 'Sample Testing',
          requestedProductService: leadToEdit.requestedProductService || '',
          requirementSummary: leadToEdit.requirementSummary || '',
          leadSource: leadToEdit.leadSource || 'Email Received',
          connectedDate: leadToEdit.connectedDate ? leadToEdit.connectedDate.slice(0, 10) : '',
          communicationChannel: leadToEdit.communicationChannel || 'Email',
          accountId: leadToEdit.accountId || leadToEdit.account?.id || '',
          contactId: leadToEdit.contactId || leadToEdit.contact?.id || '',
          additionalContactIds: additionalIds,
          assignedToUserId: leadToEdit.assignedToUserId || leadToEdit.assignedTo?.id || '',
          remarks: leadToEdit.remarks || '',
          // Pure date-only string YYYY-MM-DD
          nextFollowUpDate: leadToEdit.nextFollowUpDate ? leadToEdit.nextFollowUpDate.slice(0, 10) : '',
          nextFollowUpAction: leadToEdit.nextFollowUpAction || '',
          location: leadToEdit.location || '',
          siteName: leadToEdit.siteName || ''
        });
      } else {
        setFormData({
          leadName: '',
          businessArea: 'Biogas',
          requirementTypes: ['Sample Testing'],
          requirementType: 'Sample Testing',
          requestedProductService: '',
          requirementSummary: '',
          leadSource: 'Email Received',
          connectedDate: '',
          communicationChannel: 'Email',
          accountId: '',
          contactId: '',
          additionalContactIds: [],
          assignedToUserId: '',
          remarks: '',
          nextFollowUpDate: '',
          nextFollowUpAction: '',
          location: '',
          siteName: ''
        });
      }

      return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, leadToEdit]);

  // Load Accounts, Contacts, and Assignees
  const loadInitialData = async () => {
    try {
      const [accRes, assigneesRes] = await Promise.all([
        crmService.getAccounts({ limit: 100 }),
        crmService.getEligibleAssignees()
      ]);

      let loadedAccounts = accRes.data?.success ? (accRes.data.accounts || []) : [];
      if (leadToEdit?.account && !loadedAccounts.some(a => a.id === leadToEdit.account.id)) {
        loadedAccounts = [leadToEdit.account, ...loadedAccounts];
      } else if (leadToEdit?.accountId && !loadedAccounts.some(a => a.id === leadToEdit.accountId)) {
        loadedAccounts = [{ id: leadToEdit.accountId, accountId: leadToEdit.accountId, name: leadToEdit.accountName || 'Current Account' }, ...loadedAccounts];
      }
      setAccounts(loadedAccounts);

      if (assigneesRes.data?.success) {
        setAssignees(assigneesRes.data.assignees || []);
      }

      const initialAccId = leadToEdit?.accountId || leadToEdit?.account?.id || '';
      await fetchContacts(initialAccId, leadToEdit);
    } catch {
      // Non-blocking
    }
  };

  const fetchContacts = async (accId = '', leadCtx = leadToEdit) => {
    try {
      const params = { limit: 100 };
      if (accId) {
        params.accountId = accId;
        params.includeUnassigned = true;
      }
      const res = await crmService.getContacts(params);
      let loadedContacts = res.data?.success ? (res.data.contacts || []) : [];

      // Ensure currently attached contact is present in options list
      if (leadCtx?.contact && !loadedContacts.some(c => c.id === leadCtx.contact.id)) {
        loadedContacts = [leadCtx.contact, ...loadedContacts];
      } else if (leadCtx?.contactId && !loadedContacts.some(c => c.id === leadCtx.contactId)) {
        loadedContacts = [{
          id: leadCtx.contactId,
          contactId: leadCtx.contact?.contactId || leadCtx.contactId,
          name: leadCtx.contactName || leadCtx.contact?.name || 'Current Contact',
          email: leadCtx.contactEmail || leadCtx.contact?.email,
          mobileNumber: leadCtx.contactPhone || leadCtx.contact?.mobileNumber,
          accountId: leadCtx.accountId || leadCtx.account?.id
        }, ...loadedContacts];
      }
      setContacts(loadedContacts);
    } catch {
      // Non-blocking
    }
  };

  const handleAccountChange = async (accId) => {
    setFormData(prev => {
      // If currently selected contact belongs to a different non-empty account, clear contactId
      const currentContact = contacts.find(c => c.id === prev.contactId);
      const shouldKeepContact = currentContact && (!currentContact.accountId || currentContact.accountId === accId);
      const keptAdditional = (prev.additionalContactIds || []).filter(id => {
        const con = contacts.find(c => c.id === id);
        return con && (!con.accountId || con.accountId === accId);
      });
      return {
        ...prev,
        accountId: accId,
        contactId: shouldKeepContact ? prev.contactId : '',
        additionalContactIds: keptAdditional
      };
    });
    await fetchContacts(accId);
  };

  const handleContactChange = (e) => {
    const selectedContactId = e.target.value;
    const selectedContact = contacts.find(c => c.id === selectedContactId);

    setFormData(prev => {
      const nextState = {
        ...prev,
        contactId: selectedContactId,
        additionalContactIds: (prev.additionalContactIds || []).filter(id => id !== selectedContactId)
      };
      // If contact belongs to an account and account is not set, auto-populate accountId
      if (selectedContact?.accountId && !prev.accountId) {
        nextState.accountId = selectedContact.accountId;
      }
      return nextState;
    });

    if (fieldErrors.contactId) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next.contactId;
        return next;
      });
    }
    if (error) setError(null);
  };

  const handleAdditionalContactToggle = (contactId) => {
    setFormData(prev => {
      const current = prev.additionalContactIds || [];
      const exists = current.includes(contactId);
      const updated = exists ? current.filter(id => id !== contactId) : [...current, contactId];
      return {
        ...prev,
        additionalContactIds: updated
      };
    });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (error) setError(null);
    if (duplicateConflict) setDuplicateConflict(null);
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleAccountCreated = async (newAcc) => {
    if (!newAcc || !newAcc.id) return;
    setAccounts(prev => [newAcc, ...prev.filter(a => a.id !== newAcc.id)]);
    setFormData(prev => ({ ...prev, accountId: newAcc.id }));
    // Fetch contacts with includeUnassigned so user can immediately assign an existing or unassigned contact
    await fetchContacts(newAcc.id);
  };

  const handleContactCreated = (newContact) => {
    if (!newContact || !newContact.id) return;
    setContacts(prev => [newContact, ...prev.filter(c => c.id !== newContact.id)]);
    setFormData(prev => ({
      ...prev,
      contactId: newContact.id,
      accountId: newContact.accountId || prev.accountId
    }));
  };

  const handleRequirementTypeToggle = (type) => {
    setFormData(prev => {
      const current = prev.requirementTypes || [];
      const exists = current.includes(type);
      const updated = exists ? current.filter(t => t !== type) : [...current, type];
      return {
        ...prev,
        requirementTypes: updated,
        requirementType: updated[0] || ''
      };
    });
    if (fieldErrors.requirementTypes) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next.requirementTypes;
        return next;
      });
    }
  };

  const validate = () => {
    const errors = {};
    // Lead Title / Name is optional per Phase 1 spec
    if (!formData.businessArea) {
      errors.businessArea = 'Business Area is required (Biogas or WWT).';
    }
    if (!formData.requirementTypes || formData.requirementTypes.length === 0) {
      errors.requirementTypes = 'At least one requirement type must be selected (Consulting, Sample Testing, or Product).';
    }
    if (!formData.contactId) {
      errors.contactId = 'Primary Contact is mandatory. Please select or quick-create a contact.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setError(null);
    setDuplicateConflict(null);
    setSubmitting(true);

    const payload = {
      leadName: formData.leadName.trim() || undefined,
      businessArea: formData.businessArea,
      requirementTypes: formData.requirementTypes,
      requirementType: formData.requirementTypes[0] || 'Sample Testing',
      requestedProductService: formData.requestedProductService.trim() || undefined,
      requirementSummary: formData.requirementSummary.trim() || undefined,
      leadSource: formData.leadSource || 'Email Received',
      communicationChannel: formData.communicationChannel || 'Email',
      contactId: formData.contactId,
      additionalContactIds: formData.additionalContactIds || [],
      accountId: formData.accountId ? formData.accountId : (isEdit ? null : undefined),
      assignedToUserId: formData.assignedToUserId ? formData.assignedToUserId : (isEdit ? null : undefined),
      remarks: formData.remarks.trim() || undefined,
      connectedDate: formData.connectedDate || undefined,
      // Date only: YYYY-MM-DD (pure calendar date)
      nextFollowUpDate: formData.nextFollowUpDate || undefined,
      nextFollowUpAction: formData.nextFollowUpAction.trim() || undefined,
      location: formData.location.trim() || undefined,
      siteName: formData.siteName.trim() || undefined
    };

    try {
      let res;
      if (isEdit) {
        res = await crmService.updateLead(leadToEdit.id, payload);
      } else {
        res = await crmService.createLead(payload);
      }

      if (res.data?.success && res.data?.lead) {
        onLeadSaved(res.data.lead);
        onClose();
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
      if (err.response?.status === 409) {
        const conflictDetails = err.response.data?.details || {};
        setDuplicateConflict({
          message: err.response.data?.message || 'An active open lead already exists for this client with this requirement specification.',
          existingLeadId: conflictDetails.existingLeadId,
          existingLeadNumber: conflictDetails.existingLeadNumber,
          existingLeadName: conflictDetails.existingLeadName
        });
      } else if (err.response?.data?.details && Array.isArray(err.response.data.details)) {
        // Map backend validation errors to fields
        const errMap = {};
        err.response.data.details.forEach(item => {
          const field = item.loc?.[item.loc.length - 1];
          if (field) errMap[field] = item.msg;
        });
        setFieldErrors(errMap);
        setError(err.response.data.message || 'Please correct the validation errors in the form.');
      } else {
        setError(err.response?.data?.message || 'Failed to save lead. Please check the entered data.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenExistingLead = (existingId) => {
    onClose();
    navigate(`/crm/leads/${existingId}`);
  };

  if (!isOpen) return null;

  const selectedAccount = accounts.find(a => a.id === formData.accountId);
  const eligibleAdditionalContacts = contacts.filter(c =>
    c.id !== formData.contactId &&
    (!formData.accountId || !c.accountId || c.accountId === formData.accountId)
  );

  return (
    <>
      <div className="modal-backdrop" style={{ zIndex: 1100 }} onClick={onClose}>
        <div
          className="modal-content"
          style={{ maxWidth: '840px', width: '95%', maxHeight: '92vh', display: 'flex', flexDirection: 'column', borderRadius: '14px', overflow: 'hidden' }}
          onClick={e => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', background: '#ffffff' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: '#fef3c7',
                color: '#d97706',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Layers size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#0f172a' }}>
                  {isEdit ? `Edit Lead — ${leadToEdit.leadId}` : 'Create New Lead'}
                </h3>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {isEdit ? 'Update prospect information, requirement scope, and follow-up plan' : 'Capture prospective client enquiry and assign sales representative'}
                </span>
              </div>
            </div>
          </div>

          {/* Form Content */}
          <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
            <div className="modal-body" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Duplicate Open Lead Conflict Alert */}
              {duplicateConflict && (
                <div style={{
                  padding: '1rem',
                  background: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.6rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#b45309', fontWeight: 600 }}>
                    <AlertCircle size={18} />
                    <span>Duplicate Active Lead Conflict</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.875rem', color: '#92400e', lineHeight: 1.5 }}>
                    {duplicateConflict.message}
                  </p>
                  {duplicateConflict.existingLeadId && (
                    <div style={{ marginTop: '0.25rem' }}>
                      <button
                        type="button"
                        onClick={() => handleOpenExistingLead(duplicateConflict.existingLeadId)}
                        className="btn btn-secondary"
                        style={{
                          fontSize: '0.8rem',
                          padding: '0.45rem 0.9rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          background: '#ffffff',
                          borderColor: '#f59e0b',
                          color: '#b45309'
                        }}
                      >
                        <ExternalLink size={14} />
                        <span>View Open Lead ({duplicateConflict.existingLeadNumber || 'Open Lead'})</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* General Error Alert */}
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
                  fontSize: '0.875rem'
                }}>
                  <AlertCircle size={18} style={{ flexShrink: 0 }} />
                  <span>{error}</span>
                </div>
              )}

              {/* Section 1: Client & Stakeholder Information */}
              <div style={{
                background: '#f8fafc',
                padding: '1.1rem',
                borderRadius: '10px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#334155', fontWeight: 600, fontSize: '0.9rem' }}>
                  <Building size={16} color="var(--accent-primary)" />
                  <span>Client Identification & Contact</span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                  {/* Account Lookup (Optional) */}
                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <label className="form-label" style={{ margin: 0, fontWeight: 600 }}>
                        Company / Account <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 400 }}>(Optional)</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setIsQuickAccountOpen(true)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-primary)',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        <Plus size={13} /> Quick Create Account
                      </button>
                    </div>
                    <select
                      name="accountId"
                      className="form-control"
                      value={formData.accountId}
                      onChange={e => handleAccountChange(e.target.value)}
                    >
                      <option value="">-- No Account (Direct Contact / Early Lead) --</option>
                      {accounts.map(acc => (
                        <option key={acc.id} value={acc.id}>
                          {acc.name} ({acc.accountId})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Contact Lookup (Mandatory) */}
                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <label className="form-label" style={{ margin: 0, fontWeight: 600 }}>
                        Primary Contact <span style={{ color: 'var(--danger)' }}>*</span>
                      </label>
                      <button
                        type="button"
                        onClick={() => setIsQuickContactOpen(true)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-primary)',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        <Plus size={13} /> Quick Create Contact
                      </button>
                    </div>
                    <select
                      name="contactId"
                      className={`form-control ${fieldErrors.contactId ? 'is-invalid' : ''}`}
                      value={formData.contactId}
                      onChange={handleContactChange}
                      required
                    >
                      <option value="">-- Select Contact --</option>
                      {contacts.map(c => (
                        <option key={c.id} value={c.id}>
                          {c.name} {c.designation ? `(${c.designation})` : ''} • {c.email || c.mobileNumber || c.contactId}
                        </option>
                      ))}
                    </select>
                    {fieldErrors.contactId && (
                      <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                        {fieldErrors.contactId}
                      </div>
                    )}
                  </div>
                </div>

                {/* Additional Contacts (Optional Multi-Select) */}
                <div style={{ marginTop: '0.25rem', paddingTop: '0.75rem', borderTop: '1px dashed #cbd5e1' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                    <label className="form-label" style={{ margin: 0, fontWeight: 600 }}>
                      Additional Contacts / Related Contacts <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 400 }}>(Optional)</span>
                    </label>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      Select other contacts from this account
                    </span>
                  </div>
                  {eligibleAdditionalContacts.length === 0 ? (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.35rem 0' }}>
                      {formData.accountId ? 'No other contacts found for this account.' : 'Select an Account or create more contacts to attach additional stakeholders.'}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '130px', overflowY: 'auto', padding: '0.25rem 0' }}>
                      {eligibleAdditionalContacts.map(c => {
                        const isChecked = (formData.additionalContactIds || []).includes(c.id);
                        return (
                          <label
                            key={c.id}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.45rem',
                              padding: '0.35rem 0.65rem',
                              borderRadius: '6px',
                              background: isChecked ? '#e0f2fe' : '#ffffff',
                              border: isChecked ? '1.5px solid #0284c7' : '1px solid #cbd5e1',
                              fontSize: '0.8rem',
                              cursor: 'pointer',
                              userSelect: 'none',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleAdditionalContactToggle(c.id)}
                              style={{ cursor: 'pointer' }}
                            />
                            <span style={{ fontWeight: isChecked ? 600 : 400, color: isChecked ? '#0369a1' : '#334155' }}>
                              {c.name} {c.designation ? `(${c.designation})` : ''}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* Section 2: Enquiry Details & Categorization */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Lead Title / Name <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 400 }}>(Optional)</span>
                  </label>
                  <input
                    type="text"
                    name="leadName"
                    className={`form-control ${fieldErrors.leadName ? 'is-invalid' : ''}`}
                    placeholder="e.g. 1000 TPD Biomethanation Inoculum Supply (Defaults to Lead ID if left blank)"
                    value={formData.leadName}
                    onChange={handleChange}
                  />
                  {fieldErrors.leadName && (
                    <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                      {fieldErrors.leadName}
                    </div>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Business Area <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <select
                    name="businessArea"
                    className="form-control"
                    value={formData.businessArea}
                    onChange={handleChange}
                    required
                  >
                    <option value="Biogas">Biogas</option>
                    <option value="WWT">WWT (Wastewater Treatment)</option>
                  </select>
                </div>
              </div>

              {/* Requirement Types: Exactly Three Independent Multi-Select Checkboxes */}
              <div className="form-group" style={{ background: '#f8fafc', padding: '0.9rem 1rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                <label className="form-label" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span>
                    Requirement Type <span style={{ color: 'var(--danger)' }}>*</span>
                  </span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    Select any one, two, or all three options
                  </span>
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '0.25rem' }}>
                  {REQUIREMENT_TYPE_OPTIONS.map(opt => {
                    const checked = (formData.requirementTypes || []).includes(opt);
                    return (
                      <label
                        key={opt}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.55rem',
                          cursor: 'pointer',
                          padding: '0.5rem 0.85rem',
                          borderRadius: '8px',
                          background: checked ? '#eff6ff' : '#ffffff',
                          border: checked ? '1.5px solid #2563eb' : '1.5px solid #cbd5e1',
                          fontWeight: checked ? 600 : 500,
                          color: checked ? '#1d4ed8' : '#334155',
                          fontSize: '0.875rem',
                          userSelect: 'none',
                          transition: 'all 0.15s ease'
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => handleRequirementTypeToggle(opt)}
                          style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                        />
                        <span>{opt}</span>
                      </label>
                    );
                  })}
                </div>
                {fieldErrors.requirementTypes && (
                  <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.45rem' }}>
                    {fieldErrors.requirementTypes}
                  </div>
                )}
              </div>

              {/* Section 3: Technical Requirement Specification (OPTIONAL) */}
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span>Requested Product / Service Specification</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 400 }}>(Optional for early enquiries)</span>
                  </div>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                    When provided, checked for duplicate active leads
                  </span>
                </label>
                <input
                  type="text"
                  name="requestedProductService"
                  className="form-control"
                  placeholder="e.g. Bio-Culture Specialized Bacterial Consortium - 5000L (or leave blank if requirement is not yet specified)"
                  value={formData.requestedProductService}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500 }}>
                  Requirement Summary / Technical Scope <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Optional)</span>
                </label>
                <textarea
                  name="requirementSummary"
                  className="form-control"
                  rows={2}
                  placeholder="Feedstock type, daily plant capacity, COD/BOD parameters, or client timeline..."
                  value={formData.requirementSummary}
                  onChange={handleChange}
                />
              </div>

              {/* Section 4: Source, Channel, Connected Date & Assignment */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Lead Source <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <select
                    name="leadSource"
                    className="form-control"
                    value={formData.leadSource}
                    onChange={handleChange}
                    required
                  >
                    {formData.leadSource && !ACTIVE_LEAD_SOURCES.includes(formData.leadSource) && (
                      <option value={formData.leadSource}>{formData.leadSource} (Historical)</option>
                    )}
                    {ACTIVE_LEAD_SOURCES.map(source => (
                      <option key={source} value={source}>{source}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Calendar size={14} color="var(--text-muted)" />
                    <span>Connected Date</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem', fontWeight: 400 }}>(Date only)</span>
                  </label>
                  <input
                    type="date"
                    name="connectedDate"
                    className="form-control"
                    value={formData.connectedDate}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Communication Channel</label>
                  <select
                    name="communicationChannel"
                    className="form-control"
                    value={formData.communicationChannel}
                    onChange={handleChange}
                  >
                    <option value="Email">Email</option>
                    <option value="Phone / Call">Phone / Call</option>
                    <option value="In-Person Meeting">In-Person Meeting</option>
                    <option value="WhatsApp">WhatsApp</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Assigned Team Member</label>
                  <select
                    name="assignedToUserId"
                    className="form-control"
                    value={formData.assignedToUserId}
                    onChange={handleChange}
                  >
                    <option value="">-- Unassigned (Lead Pool) --</option>
                    {assignees.map(u => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({u.roleName || u.roleCode})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Section 5: Follow-up Date & Remarks */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Calendar size={14} color="var(--text-muted)" />
                    <span>Next Follow-up Date</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Date only)</span>
                  </label>
                  <input
                    type="date"
                    name="nextFollowUpDate"
                    className="form-control"
                    value={formData.nextFollowUpDate}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 500 }}>
                    Next Follow-up Action <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Optional)</span>
                  </label>
                  <input
                    type="text"
                    name="nextFollowUpAction"
                    className="form-control"
                    placeholder="e.g. Send technical datasheet & follow up on call"
                    value={formData.nextFollowUpAction}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500 }}>
                  Remarks / Context Summary <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Optional)</span>
                </label>
                <textarea
                  name="remarks"
                  className="form-control"
                  rows={2}
                  placeholder="Key background notes, customer status, or preliminary requirements..."
                  value={formData.remarks}
                  onChange={handleChange}
                />
              </div>

              {/* Section 6: Site / Location Details */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 500 }}>
                    Plant / Site Name <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Optional)</span>
                  </label>
                  <input
                    type="text"
                    name="siteName"
                    className="form-control"
                    placeholder="e.g. Unit 2 Vadodara Plant"
                    value={formData.siteName}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 500 }}>
                    Location / City <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>(Optional)</span>
                  </label>
                  <input
                    type="text"
                    name="location"
                    className="form-control"
                    placeholder="e.g. Surat, Gujarat"
                    value={formData.location}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="modal-footer" style={{ padding: '1rem 1.5rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? (isEdit ? 'Updating Lead...' : 'Creating Lead...') : (isEdit ? 'Save Changes' : 'Create Lead')}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Sub-modals for quick creating accounts and contacts */}
      <QuickAccountModal
        isOpen={isQuickAccountOpen}
        onClose={() => setIsQuickAccountOpen(false)}
        onAccountCreated={handleAccountCreated}
      />

      <QuickContactModal
        isOpen={isQuickContactOpen}
        onClose={() => setIsQuickContactOpen(false)}
        onContactCreated={handleContactCreated}
        defaultAccountId={formData.accountId}
        defaultAccountName={selectedAccount?.name}
      />
    </>
  );
}
