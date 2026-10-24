import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeft,
  Save,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Building,
  User,
  Info,
  Phone,
  FileText,
  DollarSign,
  Calendar,
  Globe,
  Mail,
  MapPin,
  CheckCircle2
} from 'lucide-react';
import crmService from '../services/crmService';

const CANONICAL_LEAD_SOURCES = [
  'Website',
  'Email Received',
  'Email Campaign',
  'Cold Outreach',
  'Inbound Call',
  'In-Person Meeting',
  'Investor',
  'Partner',
  'Referral',
  'Social Media',
  'Trade Show / Expo',
  'Other'
];

const CANONICAL_CONTACT_METHODS = ['Email', 'Phone', 'WhatsApp', 'Meeting'];

const CANONICAL_REQUIREMENT_TYPES = ['Consulting', 'Sample Testing', 'Product'];

const CANONICAL_BUSINESS_AREAS = ['Biogas', 'Bio-CNG', 'Wastewater', 'Solid Waste', 'Other'];

const CANONICAL_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP'];

export default function CrmLeadCreatePage() {
  const { id } = useParams(); // If present, edit mode
  const isEditMode = Boolean(id);
  const navigate = useNavigate();
  const { user, hasPermission } = useAuth();

  const [loadingLead, setLoadingLead] = useState(isEditMode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [assignees, setAssignees] = useState([]);
  const [isAdditionalInfoOpen, setIsAdditionalInfoOpen] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  // Form State across 5 sections
  const [formData, setFormData] = useState({
    // Section 1 - Contact
    topic: '',
    firstName: '',
    lastName: '',
    jobTitle: '',
    businessPhone: '',
    mobilePhone: '',
    contactEmail: '',

    // Section 2 - Company
    companyName: '',
    websiteLink: '',
    location: '',
    communicationChannel: 'Email',
    connectedDate: new Date().toISOString().slice(0, 10),
    companyEmail: '',

    // Section 3 - Additional Lead Information
    leadSource: 'Website',
    rating: 'Warm',
    clientStatus: 'New', // New or Existing
    assignedToUserId: '',

    // Section 4 - Description & Business Information
    description: '',
    industry: '',
    numberOfEmployees: '',
    currency: 'INR',
    requirementTypes: [],
    businessArea: 'Biogas',

    // Contact Method
    contactMethods: ['Email'],
    preferredContactMethod: 'Email'
  });

  const [fieldErrors, setFieldErrors] = useState({});

  // Fetch assignees
  useEffect(() => {
    async function loadAssignees() {
      try {
        const res = await crmService.getEligibleAssignees();
        if (res.data?.success) {
          setAssignees(res.data.assignees || []);
        }
      } catch (err) {
        console.error('Failed to load CRM assignees:', err);
      }
    }
    loadAssignees();
  }, []);

  // In edit mode, load existing lead
  useEffect(() => {
    if (!isEditMode) return;
    async function fetchLead() {
      setLoadingLead(true);
      setError(null);
      try {
        const res = await crmService.getLeadById(id);
        if (res.data?.success) {
          const l = res.data.lead;
          setFormData({
            topic: l.leadName || '',
            firstName: l.firstName || (l.contact ? l.contact.name.split(' ')[0] : '') || '',
            lastName: l.lastName || (l.contact ? l.contact.name.split(' ').slice(1).join(' ') : '') || '',
            jobTitle: l.jobTitle || l.contact?.designation || '',
            businessPhone: l.businessPhone || '',
            mobilePhone: l.mobilePhone || l.contact?.mobileNumber || '',
            contactEmail: l.contactEmail || l.contact?.email || '',

            companyName: l.companyName || l.account?.name || '',
            websiteLink: l.websiteLink || l.account?.website || '',
            location: l.location || l.account?.address || '',
            communicationChannel: l.communicationChannel || 'Email',
            connectedDate: l.connectedDate ? l.connectedDate.slice(0, 10) : new Date().toISOString().slice(0, 10),
            companyEmail: l.companyEmail || l.account?.email || '',

            leadSource: l.leadSource || 'Website',
            rating: l.rating || 'Warm',
            clientStatus: l.clientStatus || 'New',
            assignedToUserId: l.assignedToUserId || '',

            description: l.description || l.requirementSummary || '',
            industry: l.industry || l.account?.industry || '',
            numberOfEmployees: l.numberOfEmployees !== null && l.numberOfEmployees !== undefined ? String(l.numberOfEmployees) : '',
            currency: l.currency || 'INR',
            requirementTypes: Array.isArray(l.requirementTypes) ? l.requirementTypes : [],
            businessArea: l.businessArea || 'Biogas',

            contactMethods: l.contactMethods && l.contactMethods.length > 0 ? l.contactMethods : ['Email'],
            preferredContactMethod: l.preferredContactMethod || (l.contactMethods?.[0] || 'Email')
          });
        }
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to load lead details.');
      } finally {
        setLoadingLead(false);
      }
    }
    fetchLead();
  }, [id, isEditMode]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setIsDirty(true);
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const handleRequirementTypeToggle = (type) => {
    setIsDirty(true);
    setFormData(prev => {
      const current = prev.requirementTypes || [];
      let updated;
      if (current.includes(type)) {
        if (current.length === 1) return prev; // Keep at least one
        updated = current.filter(t => t !== type);
      } else {
        updated = [...current, type];
      }
      return { ...prev, requirementTypes: updated };
    });
  };

  const handleContactMethodToggle = (method) => {
    setIsDirty(true);
    setFormData(prev => {
      const current = prev.contactMethods || [];
      let updated;
      if (current.includes(method)) {
        if (current.length === 1) return prev; // Keep at least one
        updated = current.filter(m => m !== method);
      } else {
        updated = [...current, method];
      }

      // If preferred method was removed, pick first remaining
      let preferred = prev.preferredContactMethod;
      if (!updated.includes(preferred)) {
        preferred = updated[0];
      }

      return {
        ...prev,
        contactMethods: updated,
        preferredContactMethod: preferred
      };
    });
  };

  const validateForm = () => {
    const errors = {};

    // Topic/Title or Company Name — at least one must be provided
    const hasTopic = Boolean(formData.topic && formData.topic.trim());
    const hasCompany = Boolean(formData.companyName && formData.companyName.trim());
    if (!hasTopic && !hasCompany) {
      errors.topic = 'Please provide either a Topic/Title or Company Name.';
      errors.companyName = 'Please provide either a Topic/Title or Company Name.';
    }

    // At least one contact method
    if (!formData.contactMethods || formData.contactMethods.length === 0) {
      errors.contactMethods = 'Please select at least one contact method.';
    }

    // Business Area
    if (!formData.businessArea) {
      errors.businessArea = 'Please select a business area.';
    }

    // Date Connected
    if (!formData.connectedDate) {
      errors.connectedDate = 'Date connected is required.';
    }

    // Lead Source
    if (!formData.leadSource) {
      errors.leadSource = 'Please select a lead source.';
    }

    // Validate email formats if entered
    if (formData.contactEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.contactEmail.trim())) {
      errors.contactEmail = 'Please enter a valid contact email address.';
    }
    if (formData.companyEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.companyEmail.trim())) {
      errors.companyEmail = 'Please enter a valid company email address.';
    }

    // Number of employees must be non-negative integer if provided
    if (formData.numberOfEmployees) {
      const num = Number(formData.numberOfEmployees);
      if (isNaN(num) || !Number.isInteger(num) || num < 0) {
        errors.numberOfEmployees = 'Number of employees must be a non-negative integer.';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (shouldClose = false) => {
    if (submitting) return;

    if (!validateForm()) {
      setError('Please resolve the errors highlighted below.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMsg(null);

    const payload = {
      topic: formData.topic.trim() || undefined,
      leadName: formData.topic.trim() || undefined,
      firstName: formData.firstName.trim() || undefined,
      lastName: formData.lastName.trim() || undefined,
      jobTitle: formData.jobTitle.trim() || undefined,
      businessPhone: formData.businessPhone.trim() || undefined,
      mobilePhone: formData.mobilePhone.trim() || undefined,
      contactEmail: formData.contactEmail.trim() || undefined,

      companyName: formData.companyName.trim() || undefined,
      websiteLink: formData.websiteLink.trim() || undefined,
      location: formData.location.trim() || undefined,
      communicationChannel: formData.communicationChannel,
      connectedDate: formData.connectedDate || undefined,
      companyEmail: formData.companyEmail.trim() || undefined,

      leadSource: formData.leadSource,
      rating: formData.rating,
      clientStatus: formData.clientStatus,
      assignedToUserId: formData.assignedToUserId || undefined,

      description: formData.description.trim() || undefined,
      industry: formData.industry.trim() || undefined,
      numberOfEmployees: formData.numberOfEmployees ? parseInt(formData.numberOfEmployees, 10) : undefined,
      currency: formData.currency,
      requirementTypes: formData.requirementTypes,
      businessArea: formData.businessArea,

      contactMethods: formData.contactMethods,
      preferredContactMethod: formData.preferredContactMethod
    };

    let savedLead = null;
    let saveSucceeded = false;

    // STEP 1: Execute network write and isolate it from follow-up actions
    try {
      let res;
      if (isEditMode) {
        res = await crmService.updateLead(id, payload);
      } else {
        res = await crmService.createLead(payload);
      }

      if (res?.data?.success && res.data?.lead) {
        savedLead = res.data.lead;
        saveSucceeded = true;
      } else {
        throw new Error(res?.data?.message || 'Server returned an invalid save response.');
      }
    } catch (err) {
      console.error('Lead save error:', err);
      if (err.response) {
        const serverMsg = err.response.data?.message || err.response.data?.detail || 'Validation error while saving lead.';
        setError(serverMsg);
      } else if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
        setError('Request timed out while waiting for the server. The lead may have already been saved. Please verify the Leads list before retrying to prevent duplicate records.');
      } else if (err.message === 'Network Error' || err.code === 'ERR_NETWORK') {
        setError('Connection Error — Unable to reach the server. Please check your network connection and try again.');
      } else {
        setError(err.message || 'An unexpected error occurred while saving the lead.');
      }
      setSubmitting(false);
      return;
    }

    // STEP 2: Handle post-save navigation and notifications safely
    // Once saveSucceeded is true, the lead IS permanently in the database.
    // Subsequent actions MUST NEVER report that the save failed!
    setIsDirty(false);
    setSubmitting(false);
    const leadCode = savedLead?.leadId || savedLead?.lead_id || 'Lead';

    if (shouldClose) {
      try {
        navigate('/crm/leads', {
          state: {
            successMessage: isEditMode
              ? `Lead ${leadCode} updated successfully.`
              : `Lead ${leadCode} created successfully.`
          }
        });
      } catch (navErr) {
        console.error('Post-save navigation error:', navErr);
        setSuccessMsg(isEditMode ? `Lead ${leadCode} updated successfully.` : `Lead ${leadCode} created successfully.`);
      }
    } else {
      setSuccessMsg(isEditMode ? `Lead ${leadCode} saved successfully.` : `Lead ${leadCode} created successfully.`);
      setTimeout(() => setSuccessMsg(null), 5000);
      if (!isEditMode && savedLead?.id) {
        try {
          navigate(`/crm/leads/${savedLead.id}`, {
            state: {
              successMessage: `Lead ${leadCode} created successfully.`
            }
          });
        } catch (navErr) {
          console.error('Post-save detail navigation error:', navErr);
        }
      }
    }
  };

  const handleCancel = () => {
    if (isDirty) {
      setShowCancelConfirm(true);
    } else {
      navigate('/crm/leads');
    }
  };

  if (loadingLead) {
    return (
      <div className="page-body" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <div style={{ color: 'var(--text-secondary)' }}>Loading lead details...</div>
      </div>
    );
  }

  return (
    <div className="page-body" style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '3rem' }}>
      {/* Breadcrumb & Navigation */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1rem',
        paddingTop: '0.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          <Link to="/crm/dashboard" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>CRM</Link>
          <span>/</span>
          <Link to="/crm/leads" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Leads</Link>
          <span>/</span>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
            {isEditMode ? 'Edit Lead' : 'New Lead'}
          </span>
        </div>
      </div>

      {/* Top Header Command Bar (Dynamics 365 Sales Hub Inspired) */}
      <div className="glass-panel" style={{
        padding: '1.25rem 1.5rem',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        borderLeft: '4px solid var(--accent-primary)',
        boxShadow: 'var(--panel-shadow)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={handleCancel}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                color: 'var(--text-secondary)',
                padding: '0.25rem',
                borderRadius: 'var(--radius-xs)'
              }}
              title="Go back to Leads"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {isEditMode ? `Edit Lead — ${formData.topic || id}` : 'New Lead'}
            </h1>
          </div>
          <p style={{ margin: '0.25rem 0 0 2rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Enter initial enquiry details. Leads capture direct contact and company data without requiring permanent account records.
          </p>
        </div>

        {/* Command Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={handleCancel}
            className="btn btn-secondary"
            disabled={submitting}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <X size={16} />
            <span>Cancel</span>
          </button>
          <button
            type="button"
            onClick={() => handleSubmit(true)}
            className="btn btn-secondary"
            disabled={submitting}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)' }}
          >
            <Save size={16} />
            <span>Save & Close</span>
          </button>
          <button
            type="button"
            onClick={() => handleSubmit(false)}
            className="btn btn-primary"
            disabled={submitting}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Check size={16} />
            <span>{submitting ? 'Saving...' : 'Save'}</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div style={{
          padding: '1rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--danger-text)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {successMsg && (
        <div style={{
          padding: '1rem',
          background: 'var(--success-bg)',
          border: '1px solid var(--success-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--success-text)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <CheckCircle2 size={20} style={{ flexShrink: 0 }} />
          <div>{successMsg}</div>
        </div>
      )}

      {/* Unsaved Changes Confirmation Modal */}
      {showCancelConfirm && (
        <div className="modal-backdrop" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.6)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1050
        }}>
          <div className="glass-panel" style={{
            maxWidth: '450px',
            width: '90%',
            padding: '2rem',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--modal-shadow)'
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Discard unsaved changes?
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
              You have unsaved changes on this Lead form. Are you sure you want to discard them and leave?
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCancelConfirm(false)}
              >
                Keep Editing
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => navigate('/crm/leads')}
              >
                Discard & Leave
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Form Container Grid */}
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(false); }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* SECTION 1 — CONTACT */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--accent-light)',
                color: 'var(--accent-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <User size={18} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  Contact Information
                </h2>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Individual contact details for this enquiry
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
              {/* Topic / Lead Title */}
              <div style={{ gridColumn: '1 / -1' }}>
                <label className="form-label" style={{ fontWeight: 600 }}>
                  Topic / Lead Title <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Required if Company is blank)</span>
                </label>
                <input
                  type="text"
                  name="topic"
                  value={formData.topic}
                  onChange={handleChange}
                  placeholder="e.g. Biogas Plant Expansion - Phase 2"
                  className={`form-input ${fieldErrors.topic ? 'input-error' : ''}`}
                  style={{ width: '100%' }}
                />
                {fieldErrors.topic && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    {fieldErrors.topic}
                  </span>
                )}
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                  Provide either a Topic/Title or Company Name.
                </span>
              </div>

              {/* First Name */}
              <div>
                <label className="form-label">First Name</label>
                <input
                  type="text"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleChange}
                  placeholder="e.g. Rajesh"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Last Name */}
              <div>
                <label className="form-label">Last Name</label>
                <input
                  type="text"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleChange}
                  placeholder="e.g. Sharma"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Job Title */}
              <div>
                <label className="form-label">Job Title / Designation</label>
                <input
                  type="text"
                  name="jobTitle"
                  value={formData.jobTitle}
                  onChange={handleChange}
                  placeholder="e.g. Technical Director"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Contact Email */}
              <div>
                <label className="form-label">Contact Email</label>
                <input
                  type="email"
                  name="contactEmail"
                  value={formData.contactEmail}
                  onChange={handleChange}
                  placeholder="rajesh.sharma@example.com"
                  className={`form-input ${fieldErrors.contactEmail ? 'input-error' : ''}`}
                  style={{ width: '100%' }}
                />
                {fieldErrors.contactEmail && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    {fieldErrors.contactEmail}
                  </span>
                )}
              </div>

              {/* Business Phone */}
              <div>
                <label className="form-label">Business Phone</label>
                <input
                  type="tel"
                  name="businessPhone"
                  value={formData.businessPhone}
                  onChange={handleChange}
                  placeholder="e.g. +91 22 2345 6789"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Mobile Phone */}
              <div>
                <label className="form-label">Mobile Phone</label>
                <input
                  type="tel"
                  name="mobilePhone"
                  value={formData.mobilePhone}
                  onChange={handleChange}
                  placeholder="e.g. +91 98765 43210"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>
            </div>
          </div>

          {/* SECTION 2 — COMPANY */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: '#fef3c7',
                color: '#d97706',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Building size={18} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  Company Information
                </h2>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Organization details (an Account record will only be mapped or created at qualification time)
                </span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
              {/* Company Name */}
              <div>
                <label className="form-label" style={{ fontWeight: 600 }}>
                  Company / Organization Name <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Required if Topic is blank)</span>
                </label>
                <input
                  type="text"
                  name="companyName"
                  value={formData.companyName}
                  onChange={handleChange}
                  placeholder="e.g. GreenTech Bio-Energies Pvt Ltd"
                  className={`form-input ${fieldErrors.companyName ? 'input-error' : ''}`}
                  style={{ width: '100%' }}
                />
                {fieldErrors.companyName && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    {fieldErrors.companyName}
                  </span>
                )}
              </div>

              {/* Website */}
              <div>
                <label className="form-label">Website</label>
                <input
                  type="text"
                  name="websiteLink"
                  value={formData.websiteLink}
                  onChange={handleChange}
                  placeholder="e.g. https://www.greentech-bio.com"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Client Location */}
              <div>
                <label className="form-label">Client Location / Address</label>
                <input
                  type="text"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  placeholder="e.g. Pune, Maharashtra"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Initial Communication Channel */}
              <div>
                <label className="form-label">Initial Communication Channel</label>
                <select
                  name="communicationChannel"
                  value={formData.communicationChannel}
                  onChange={handleChange}
                  className="form-select"
                  style={{ width: '100%' }}
                >
                  <option value="Email">Email</option>
                  <option value="Phone">Phone</option>
                  <option value="WhatsApp">WhatsApp</option>
                  <option value="In-Person Meeting">In-Person Meeting</option>
                  <option value="Website">Website Form</option>
                  <option value="Expo">Trade Show / Expo</option>
                </select>
              </div>

              {/* Date Connected */}
              <div>
                <label className="form-label">Date Connected</label>
                <input
                  type="date"
                  name="connectedDate"
                  value={formData.connectedDate}
                  onChange={handleChange}
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Company Email */}
              <div>
                <label className="form-label">Company Email</label>
                <input
                  type="email"
                  name="companyEmail"
                  value={formData.companyEmail}
                  onChange={handleChange}
                  placeholder="e.g. info@greentech-bio.com"
                  className={`form-input ${fieldErrors.companyEmail ? 'input-error' : ''}`}
                  style={{ width: '100%' }}
                />
                {fieldErrors.companyEmail && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    {fieldErrors.companyEmail}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* SECTION 3 — ADDITIONAL LEAD INFORMATION (Collapsible) */}
          <div className="glass-panel" style={{ borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)', overflow: 'hidden' }}>
            <div
              onClick={() => setIsAdditionalInfoOpen(!isAdditionalInfoOpen)}
              style={{
                padding: '1.25rem 1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
                background: isAdditionalInfoOpen ? 'var(--bg-secondary)' : 'transparent',
                borderBottom: isAdditionalInfoOpen ? '1px solid var(--border-color)' : 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: 'var(--radius-sm)',
                  background: '#f3e8ff',
                  color: '#9333ea',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Info size={18} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                    Additional Lead Information
                  </h2>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Lead Source, Rating, Relationship Status, and Owner assignment
                  </span>
                </div>
              </div>
              <button
                type="button"
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                aria-label="Toggle section"
              >
                {isAdditionalInfoOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>
            </div>

            {isAdditionalInfoOpen && (
              <div style={{ padding: '1.5rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
                  {/* Lead Source */}
                  <div>
                    <label className="form-label">Lead Source</label>
                    <select
                      name="leadSource"
                      value={formData.leadSource}
                      onChange={handleChange}
                      className="form-select"
                      style={{ width: '100%' }}
                    >
                      {CANONICAL_LEAD_SOURCES.map(source => (
                        <option key={source} value={source}>{source}</option>
                      ))}
                    </select>
                  </div>

                  {/* Rating */}
                  <div>
                    <label className="form-label">Rating</label>
                    <select
                      name="rating"
                      value={formData.rating}
                      onChange={handleChange}
                      className="form-select"
                      style={{ width: '100%' }}
                    >
                      <option value="Hot">Hot — Urgent / High Intent</option>
                      <option value="Warm">Warm — Active Interest</option>
                      <option value="Cold">Cold — Future / Exploration</option>
                    </select>
                  </div>

                  {/* Relationship Status: New or Existing */}
                  <div>
                    <label className="form-label">
                      Client Relationship Status
                    </label>
                    <select
                      name="clientStatus"
                      value={formData.clientStatus}
                      onChange={handleChange}
                      className="form-select"
                      style={{ width: '100%' }}
                    >
                      <option value="New">New — First time enquiry</option>
                      <option value="Existing">Existing — Existing client relationship</option>
                    </select>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                      Reflects customer history with REVY (independent of lifecycle status).
                    </span>
                  </div>

                  {/* Lead Owner */}
                  <div>
                    <label className="form-label">Lead Owner</label>
                    <select
                      name="assignedToUserId"
                      value={formData.assignedToUserId}
                      onChange={handleChange}
                      className="form-select"
                      style={{ width: '100%' }}
                    >
                      <option value="">Unassigned</option>
                      {assignees.map(userItem => (
                        <option key={userItem.id} value={userItem.id}>
                          {userItem.name} (@{userItem.username})
                        </option>
                      ))}
                    </select>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                      Restricted to authorized CRM module personnel.
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* DESCRIPTION AND BUSINESS INFORMATION */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: '#dbeafe',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <FileText size={18} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  Description and Business Information
                </h2>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Enquiry details, requirement types, business area, and company profile
                </span>
              </div>
            </div>

            {/* Requirement Types Multi-Select */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label className="form-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                Requirement Types
                <span style={{ fontWeight: 400, color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: '0.5rem' }}>
                  (Optional — select any that apply; can be added later)
                </span>
              </label>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {CANONICAL_REQUIREMENT_TYPES.map(type => {
                  const isChecked = formData.requirementTypes.includes(type);
                  return (
                    <label
                      key={type}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.6rem 1rem',
                        borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${isChecked ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                        background: isChecked ? 'var(--accent-light)' : 'var(--bg-secondary)',
                        color: isChecked ? 'var(--accent-primary)' : 'var(--text-primary)',
                        cursor: 'pointer',
                        fontWeight: isChecked ? 600 : 400,
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleRequirementTypeToggle(type)}
                        style={{ accentColor: 'var(--accent-primary)' }}
                      />
                      <span>{type}</span>
                    </label>
                  );
                })}
              </div>
              {fieldErrors.requirementTypes && (
                <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                  {fieldErrors.requirementTypes}
                </span>
              )}
            </div>

            {/* Description Textarea */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label className="form-label">Description / Enquiry Summary</label>
              <textarea
                name="description"
                rows={4}
                value={formData.description}
                onChange={handleChange}
                placeholder="Enter client's specific requirements, context, plant capacity, or background..."
                className="form-textarea"
                style={{ width: '100%', resize: 'vertical' }}
              />
            </div>

            {/* Business Info Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
              {/* Business Area */}
              <div>
                <label className="form-label">Business Area</label>
                <select
                  name="businessArea"
                  value={formData.businessArea}
                  onChange={handleChange}
                  className="form-select"
                  style={{ width: '100%' }}
                >
                  {CANONICAL_BUSINESS_AREAS.map(ba => (
                    <option key={ba} value={ba}>{ba}</option>
                  ))}
                </select>
              </div>

              {/* Industry */}
              <div>
                <label className="form-label">Industry</label>
                <input
                  type="text"
                  name="industry"
                  value={formData.industry}
                  onChange={handleChange}
                  placeholder="e.g. Distilleries, Sugar, Dairy"
                  className="form-input"
                  style={{ width: '100%' }}
                />
              </div>

              {/* Number of Employees */}
              <div>
                <label className="form-label">Number of Employees</label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  name="numberOfEmployees"
                  value={formData.numberOfEmployees}
                  onChange={handleChange}
                  placeholder="e.g. 150"
                  className={`form-input ${fieldErrors.numberOfEmployees ? 'input-error' : ''}`}
                  style={{ width: '100%' }}
                />
                {fieldErrors.numberOfEmployees && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                    {fieldErrors.numberOfEmployees}
                  </span>
                )}
              </div>

              {/* Currency */}
              <div>
                <label className="form-label">Currency</label>
                <select
                  name="currency"
                  value={formData.currency}
                  onChange={handleChange}
                  className="form-select"
                  style={{ width: '100%' }}
                >
                  {CANONICAL_CURRENCIES.map(curr => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* CONTACT METHOD */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.75rem',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: 'var(--radius-sm)',
                background: '#dcfce7',
                color: '#16a34a',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Phone size={18} />
              </div>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  Contact Method
                </h2>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Allowed channels for client outreach and designation of preferred method
                </span>
              </div>
            </div>

            {/* Multi-select Contact Methods */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label className="form-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>
                Supported Contact Methods <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {CANONICAL_CONTACT_METHODS.map(method => {
                  const isChecked = formData.contactMethods.includes(method);
                  return (
                    <label
                      key={method}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.6rem 1rem',
                        borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${isChecked ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                        background: isChecked ? 'var(--accent-light)' : 'var(--bg-secondary)',
                        color: isChecked ? 'var(--accent-primary)' : 'var(--text-primary)',
                        cursor: 'pointer',
                        fontWeight: isChecked ? 600 : 400,
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => handleContactMethodToggle(method)}
                        style={{ accentColor: 'var(--accent-primary)' }}
                      />
                      <span>{method}</span>
                    </label>
                  );
                })}
              </div>
              {fieldErrors.contactMethods && (
                <span style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.25rem', display: 'block' }}>
                  {fieldErrors.contactMethods}
                </span>
              )}
            </div>

            {/* Preferred Contact Method */}
            <div style={{ maxWidth: '350px' }}>
              <label className="form-label">Preferred Contact Method</label>
              <select
                name="preferredContactMethod"
                value={formData.preferredContactMethod}
                onChange={handleChange}
                className="form-select"
                style={{ width: '100%' }}
              >
                {formData.contactMethods.map(method => (
                  <option key={method} value={method}>{method}</option>
                ))}
              </select>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                Must be one of the selected contact methods above.
              </span>
            </div>
          </div>

          {/* Bottom Actions Bar */}
          <div style={{
            display: 'flex',
            justifyContent: 'flex-end',
            gap: '0.75rem',
            paddingTop: '1rem'
          }}>
            <button
              type="button"
              onClick={handleCancel}
              className="btn btn-secondary"
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => handleSubmit(true)}
              className="btn btn-secondary"
              disabled={submitting}
              style={{ borderColor: 'var(--accent-primary)', color: 'var(--accent-primary)' }}
            >
              Save & Close
            </button>
            <button
              type="button"
              onClick={() => handleSubmit(false)}
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : 'Save'}
            </button>
          </div>

        </div>
      </form>
    </div>
  );
}
