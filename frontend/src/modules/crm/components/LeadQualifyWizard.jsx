import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  X,
  Check,
  ArrowRight,
  Building,
  User,
  Briefcase,
  AlertCircle,
  CheckCircle2,
  Search,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Info
} from 'lucide-react';
import crmService from '../../../services/crmService';

const WIZARD_STEPS = [
  { id: 1, title: 'Review Lead', icon: Info },
  { id: 2, title: 'Account', icon: Building },
  { id: 3, title: 'Contact', icon: User },
  { id: 4, title: 'Opportunity', icon: Briefcase },
  { id: 5, title: 'Confirm & Qualify', icon: ShieldCheck }
];

export default function LeadQualifyWizard({ lead, isOpen, onClose, onQualifiedSuccess }) {
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState(1);
  const [loadingMatches, setLoadingMatches] = useState(true);
  const [matches, setMatches] = useState({
    matchingAccounts: [],
    matchingContacts: [],
    suggestedAccount: null,
    suggestedContact: null
  });

  // Account Step State
  const [accountAction, setAccountAction] = useState('create'); // 'create' or 'reuse'
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [selectedAccountObj, setSelectedAccountObj] = useState(null);
  const [reuseAccountSiteChoice, setReuseAccountSiteChoice] = useState('lead'); // 'existing' or 'lead'
  const [newAccountData, setNewAccountData] = useState({
    name: '',
    siteName: '',
    website: '',
    email: '',
    phone: '',
    address: '',
    industry: ''
  });
  const [accountSearchQuery, setAccountSearchQuery] = useState('');
  const [searchedAccounts, setSearchedAccounts] = useState([]);
  const [searchingAccounts, setSearchingAccounts] = useState(false);

  // Contact Step State
  const [contactAction, setContactAction] = useState('create'); // 'create' or 'reuse'
  const [selectedContactId, setSelectedContactId] = useState('');
  const [selectedContactObj, setSelectedContactObj] = useState(null);
  const [newContactData, setNewContactData] = useState({
    name: '',
    email: '',
    mobileNumber: '',
    designation: ''
  });
  const [contactSearchQuery, setContactSearchQuery] = useState('');
  const [searchedContacts, setSearchedContacts] = useState([]);
  const [searchingContacts, setSearchingContacts] = useState(false);

  // Opportunity Step State
  const [opportunityData, setOpportunityData] = useState({
    name: '',
    estimatedValue: '',
    currency: 'INR',
    description: '',
    assignedToUserId: ''
  });

  // Client Relationship Classification State (New vs Existing)
  const [clientRelationship, setClientRelationship] = useState('New');

  // Submission State
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [qualificationResult, setQualificationResult] = useState(null);

  // Initialize data from lead
  useEffect(() => {
    if (!lead || !isOpen) return;

    setCurrentStep(1);
    setQualificationResult(null);
    setSubmitError(null);
    setReuseAccountSiteChoice('lead');

    // Derived lead contact name
    let leadPersonName = '';
    if (lead.firstName || lead.lastName) {
      leadPersonName = `${lead.firstName || ''} ${lead.lastName || ''}`.trim();
    } else if (lead.contact?.name) {
      leadPersonName = lead.contact.name;
    } else if (lead.contactName) {
      leadPersonName = lead.contactName;
    }

    // Default company details (Business Phone and Company Email belong to Account)
    const compName = lead.companyName || lead.account?.name || (lead.leadName ? `${lead.leadName} Company` : '');
    setNewAccountData({
      name: compName,
      siteName: lead.siteName || lead.account?.siteName || '',
      website: lead.websiteLink || lead.account?.website || '',
      email: lead.companyEmail || lead.account?.email || '',
      phone: lead.businessPhone || lead.account?.phone || '',
      address: lead.location || lead.account?.address || '',
      industry: lead.industry || lead.account?.industry || ''
    });

    // Default contact details (Mobile Phone and Contact Email belong to Contact)
    setNewContactData({
      name: leadPersonName || (lead.leadName ? `${lead.leadName} Contact` : 'Primary Contact'),
      email: lead.contactEmail || lead.contact?.email || '',
      mobileNumber: lead.mobilePhone || lead.contact?.mobileNumber || '',
      designation: lead.jobTitle || lead.contact?.designation || ''
    });

    // Default opportunity details
    setOpportunityData({
      name: lead.leadName || `Opportunity — ${compName || lead.leadId}`,
      estimatedValue: '',
      currency: lead.currency || 'INR',
      description: lead.description || lead.requirementSummary || '',
      assignedToUserId: lead.assignedToUserId || ''
    });

    // Load matches from backend
    async function loadMatches() {
      setLoadingMatches(true);
      try {
        const res = await crmService.getLeadQualificationMatches(lead.id);
        if (res.data?.success) {
          const matchData = res.data;
          setMatches(matchData);

          // If there is an existing account linked to lead or exact match, default to reuse
          if (lead.accountId || lead.account?.id) {
            setAccountAction('reuse');
            setSelectedAccountId(lead.accountId || lead.account?.id);
            setSelectedAccountObj(lead.account || null);
          } else if (matchData.suggestedAccount) {
            setAccountAction('reuse');
            setSelectedAccountId(matchData.suggestedAccount.id);
            setSelectedAccountObj(matchData.suggestedAccount);
          } else {
            setAccountAction('create');
          }

          // If there is an existing contact linked to lead or match, default
          if (lead.contactId || lead.contact?.id) {
            setContactAction('reuse');
            setSelectedContactId(lead.contactId || lead.contact?.id);
            setSelectedContactObj(lead.contact || null);
          } else if (matchData.suggestedContact) {
            setContactAction('reuse');
            setSelectedContactId(matchData.suggestedContact.id);
            setSelectedContactObj(matchData.suggestedContact);
          } else {
            setContactAction('create');
          }
          // Set suggested client classification
          if (matchData.suggestedClientStatus) {
            setClientRelationship(matchData.suggestedClientStatus);
          } else if (lead.clientStatus) {
            setClientRelationship(lead.clientStatus);
          }
        }
      } catch (err) {
        console.error('Failed to load qualification matches:', err);
      } finally {
        setLoadingMatches(false);
      }
    }

    loadMatches();
  }, [lead, isOpen]);

  // Dynamic account search
  const handleSearchAccounts = async (query) => {
    setAccountSearchQuery(query);
    if (!query || query.trim().length < 2) {
      setSearchedAccounts([]);
      return;
    }
    setSearchingAccounts(true);
    try {
      const res = await crmService.getAccounts({ search: query.trim(), limit: 10 });
      if (res.data?.success) {
        setSearchedAccounts(res.data.accounts || []);
      }
    } catch (err) {
      console.error('Account search failed:', err);
    } finally {
      setSearchingAccounts(false);
    }
  };

  // Dynamic contact search
  const handleSearchContacts = async (query) => {
    setContactSearchQuery(query);
    if (!query || query.trim().length < 2) {
      setSearchedContacts([]);
      return;
    }
    setSearchingContacts(true);
    try {
      const targetAccId = accountAction === 'reuse' ? selectedAccountId : null;
      const res = await crmService.getContacts({
        search: query.trim(),
        accountId: targetAccId || undefined,
        limit: 10
      });
      if (res.data?.success) {
        setSearchedContacts(res.data.contacts || []);
      }
    } catch (err) {
      console.error('Contact search failed:', err);
    } finally {
      setSearchingContacts(false);
    }
  };

  if (!isOpen || !lead) return null;

  // Validation before proceeding to next step
  const handleNext = () => {
    setSubmitError(null);

    if (currentStep === 1) {
      if (lead.lifecycleStatus === 'Disqualified') {
        setSubmitError("Cannot qualify a Disqualified Lead. Disqualified leads must be reopened to 'Open' before qualification.");
        return;
      }
    }

    if (currentStep === 2) {
      // Validate Account Step
      if (accountAction === 'reuse') {
        if (!selectedAccountId) {
          setSubmitError('Please select an existing account to reuse, or choose Create New Account.');
          return;
        }
      } else {
        if (!newAccountData.name || !newAccountData.name.trim()) {
          setSubmitError('Account Name is required to create a new account.');
          return;
        }
      }
    }

    if (currentStep === 3) {
      // Validate Contact Step (Primary Contact)
      if (contactAction === 'reuse') {
        if (!selectedContactId) {
          setSubmitError('Please select an existing contact to designate as Primary Contact, or choose Create New Contact.');
          return;
        }
        if (selectedAccountObj?.id && selectedContactObj?.accountId && selectedContactObj.accountId !== selectedAccountObj.id) {
          setSubmitError(`Selected contact '${selectedContactObj.name}' belongs to a different account (${selectedContactObj.accountName || selectedContactObj.accountId}). Please select a contact from the chosen account or create a new contact.`);
          return;
        }
      } else {
        if (!newContactData.name || !newContactData.name.trim()) {
          setSubmitError('Primary Contact Name is required.');
          return;
        }
      }
    }

    if (currentStep === 4) {
      // Validate Opportunity Step
      if (!opportunityData.name || !opportunityData.name.trim()) {
        setSubmitError('Opportunity Name is required.');
        return;
      }
    }

    setCurrentStep(prev => Math.min(prev + 1, 5));
  };

  const handleBack = () => {
    setSubmitError(null);
    setCurrentStep(prev => Math.max(prev - 1, 1));
  };

  // Execute Qualification
  const handleConfirmQualify = async () => {
    setSubmitting(true);
    setSubmitError(null);

    const resolvedSite = accountAction === 'create'
      ? (newAccountData.siteName?.trim() || undefined)
      : (reuseAccountSiteChoice === 'lead' ? (lead.siteName?.trim() || undefined) : (selectedAccountObj?.siteName?.trim() || undefined));

    const payload = {
      account: {
        action: accountAction,
        accountId: accountAction === 'reuse' ? selectedAccountId : undefined,
        name: accountAction === 'create' ? newAccountData.name.trim() : undefined,
        siteName: resolvedSite,
        website: newAccountData.website.trim() || undefined,
        email: newAccountData.email.trim() || undefined,
        phone: newAccountData.phone.trim() || undefined,
        address: newAccountData.address.trim() || undefined,
        industry: newAccountData.industry.trim() || undefined
      },
      contact: {
        action: contactAction,
        contactId: contactAction === 'reuse' ? selectedContactId : undefined,
        name: contactAction === 'create' ? newContactData.name.trim() : undefined,
        email: newContactData.email.trim() || undefined,
        mobileNumber: newContactData.mobileNumber.trim() || undefined,
        designation: newContactData.designation.trim() || undefined
      },
      opportunityName: opportunityData.name.trim(),
      opportunityDescription: opportunityData.description.trim() || undefined,
      estimatedValue: opportunityData.estimatedValue ? parseFloat(opportunityData.estimatedValue) : undefined,
      assignedToUserId: opportunityData.assignedToUserId || undefined,
      clientStatus: clientRelationship
    };

    try {
      const res = await crmService.qualifyLead(lead.id, payload);
      if (res.data?.success) {
        setQualificationResult(res.data);
        if (onQualifiedSuccess) {
          onQualifiedSuccess(res.data);
        }
      } else {
        setSubmitError(res.data?.message || 'Qualification was not successful.');
      }
    } catch (err) {
      console.error('Lead qualification error:', err);
      const msg = err.response?.data?.detail || err.response?.data?.message || 'Qualification transaction failed. Changes were rolled back.';
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1050,
      padding: '1rem'
    }}>
      <div className="glass-panel" style={{
        maxWidth: '820px',
        width: '100%',
        maxHeight: '92vh',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 'var(--radius-lg)',
        boxShadow: 'var(--modal-shadow)',
        overflow: 'hidden',
        background: 'var(--bg-secondary)'
      }}>
        {/* Wizard Header */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-primary)'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                background: 'var(--accent-light)',
                color: 'var(--accent-primary)',
                fontWeight: 700,
                fontSize: '0.8rem',
                padding: '2px 8px',
                borderRadius: '4px'
              }}>
                {lead.leadId}
              </span>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                Qualify Lead to Opportunity
              </h2>
            </div>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.825rem', color: 'var(--text-muted)' }}>
              Dynamics 365 Sales Hub workflow: Review, associate or create Account & Contact, and launch Opportunity
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '0.25rem' }}
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Stepper Progress Bar */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-color)',
          background: '#ffffff',
          overflowX: 'auto'
        }}>
          {WIZARD_STEPS.map((step) => {
            const isCompleted = currentStep > step.id || Boolean(qualificationResult);
            const isCurrent = currentStep === step.id && !qualificationResult;

            return (
              <div
                key={step.id}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.85rem 1rem',
                  borderBottom: isCurrent ? '3px solid var(--accent-primary)' : '3px solid transparent',
                  color: isCurrent ? 'var(--accent-primary)' : isCompleted ? 'var(--success)' : 'var(--text-muted)',
                  background: isCurrent ? 'var(--accent-light)' : 'transparent',
                  fontWeight: isCurrent ? 600 : 500,
                  fontSize: '0.85rem',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{
                  width: '22px',
                  height: '22px',
                  borderRadius: '50%',
                  background: isCurrent ? 'var(--accent-primary)' : isCompleted ? 'var(--success)' : 'var(--border-color)',
                  color: isCurrent || isCompleted ? '#ffffff' : 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700
                }}>
                  {isCompleted ? <Check size={13} /> : step.id}
                </div>
                <span>{step.title}</span>
              </div>
            );
          })}
        </div>

        {/* Error Alert */}
        {submitError && (
          <div style={{
            margin: '1rem 1.75rem 0 1.75rem',
            padding: '0.85rem 1rem',
            background: 'var(--danger-bg)',
            border: '1px solid var(--danger-border)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--danger-text)',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem'
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <div>{submitError}</div>
          </div>
        )}

        {/* Wizard Body (Scrollable) */}
        <div style={{ padding: '1.5rem 1.75rem', overflowY: 'auto', flex: 1 }}>

          {/* SUCCESS STATE */}
          {qualificationResult ? (
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'var(--success-bg)',
                color: 'var(--success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1rem'
              }}>
                <CheckCircle2 size={36} />
              </div>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                Lead Successfully Qualified!
              </h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.925rem', maxWidth: '520px', margin: '0 auto 1.75rem' }}>
                All records were committed transactionally. The lead has been converted to an active Opportunity with linked Account and Contact.
              </p>

              {/* Record Summary Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', textAlign: 'left', marginBottom: '2rem' }}>
                {/* Account Card */}
                <div style={{
                  padding: '1rem',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-primary)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#d97706', marginBottom: '0.4rem' }}>
                      <Building size={16} />
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Account</span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                      {qualificationResult.account?.name || '—'}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      Code: {qualificationResult.account?.accountId || '—'}
                    </div>
                  </div>
                  {qualificationResult.account?.name && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                      <Link
                        to={`/crm/accounts?search=${encodeURIComponent(qualificationResult.account.name)}`}
                        style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <span>View Account</span>
                        <ExternalLink size={11} />
                      </Link>
                    </div>
                  )}
                </div>

                {/* Contact Card */}
                {qualificationResult.contact && (
                  <div style={{
                    padding: '1rem',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-primary)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-primary)', marginBottom: '0.4rem' }}>
                        <User size={16} />
                        <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Contact</span>
                      </div>
                      <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                        {qualificationResult.contact?.name || '—'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        {qualificationResult.contact?.designation || qualificationResult.contact?.email || '—'}
                      </div>
                    </div>
                    {qualificationResult.contact?.name && (
                      <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)' }}>
                        <Link
                          to={`/crm/contacts?search=${encodeURIComponent(qualificationResult.contact.name)}`}
                          style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                        >
                          <span>View Contact</span>
                          <ExternalLink size={11} />
                        </Link>
                      </div>
                    )}
                  </div>
                )}

                {/* Opportunity Card */}
                <div style={{
                  padding: '1rem',
                  border: '1px solid var(--accent-light)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--accent-light)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-primary)', marginBottom: '0.4rem' }}>
                      <Briefcase size={16} />
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>Opportunity</span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--accent-primary)' }}>
                      {qualificationResult.opportunity?.name || '—'}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      Code: {qualificationResult.opportunity?.opportunityId || '—'}
                    </div>
                  </div>
                  {qualificationResult.opportunity?.opportunityId && (
                    <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                      <Link
                        to={`/crm/opportunities?search=${encodeURIComponent(qualificationResult.opportunity.opportunityId)}`}
                        style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 700, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                      >
                        <span>View Opportunity</span>
                        <ExternalLink size={11} />
                      </Link>
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    onClose();
                    navigate('/crm/leads');
                  }}
                >
                  Return to Leads
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    onClose();
                    navigate(`/crm/opportunities?search=${encodeURIComponent(qualificationResult.opportunity?.opportunityId || '')}`);
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <Briefcase size={15} />
                  <span>View in Pipeline</span>
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => {
                    onClose();
                    if (onQualifiedSuccess) {
                      onQualifiedSuccess(qualificationResult);
                    }
                  }}
                >
                  View Lead Details
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* STEP 1: REVIEW LEAD */}
              {currentStep === 1 && (
                <div>
                  <div style={{
                    padding: '0.85rem 1rem',
                    background: 'var(--accent-light)',
                    borderRadius: 'var(--radius-sm)',
                    marginBottom: '1.25rem',
                    fontSize: '0.875rem',
                    color: 'var(--accent-hover)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <Info size={18} />
                    <span>
                      Review the lead enquiry details below. In the next steps, you can match or create the company Account and primary Contact.
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
                    {/* Contact Info Box */}
                    <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.6rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <User size={15} color="var(--accent-primary)" />
                        <span>Contact Information</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        <div><strong>Name:</strong> {lead.firstName || lead.lastName ? `${lead.firstName || ''} ${lead.lastName || ''}`.trim() : (lead.contactName || '—')}</div>
                        <div><strong>Job Title:</strong> {lead.jobTitle || lead.contact?.designation || '—'}</div>
                        <div><strong>Email:</strong> {lead.contactEmail || lead.contact?.email || '—'}</div>
                        <div><strong>Phone:</strong> {lead.mobilePhone || lead.businessPhone || lead.contact?.mobileNumber || '—'}</div>
                      </div>
                    </div>

                    {/* Company Info Box */}
                    <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.6rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Building size={15} color="#d97706" />
                        <span>Company Information</span>
                      </div>
                      <div style={{ fontSize: '0.85rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        <div><strong>Company:</strong> {lead.companyName || lead.account?.name || '—'}</div>
                        <div><strong>Website:</strong> {lead.websiteLink || lead.account?.website || '—'}</div>
                        <div><strong>Location:</strong> {lead.location || lead.account?.address || '—'}</div>
                        <div><strong>Company Email:</strong> {lead.companyEmail || lead.account?.email || '—'}</div>
                      </div>
                    </div>

                    {/* Enquiry Specifications */}
                    <div style={{ gridColumn: '1 / -1', padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.6rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Briefcase size={15} color="#16a34a" />
                        <span>Enquiry Details</span>
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        <div><strong>Requirement Types:</strong> {lead.requirementTypes?.join(', ') || lead.requirementType || 'Consulting'}</div>
                        <div><strong>Business Area:</strong> {lead.businessArea || 'Biogas'}</div>
                        <div><strong>Lead Source:</strong> {lead.leadSource || 'Website'}</div>
                        <div><strong>Rating:</strong> {lead.rating || 'Warm'}</div>
                        <div><strong>Relationship:</strong> {lead.clientStatus || 'New'}</div>
                        <div><strong>Owner:</strong> {lead.assignedToName || 'Unassigned'}</div>
                      </div>
                      {lead.description && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)', borderTop: '1px dashed var(--border-color)', paddingTop: '0.5rem' }}>
                          <strong>Description:</strong> {lead.description}
                        </div>
                      )}
                    </div>

                    {/* Client Relationship Classification */}
                    <div style={{ gridColumn: '1 / -1', padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <ShieldCheck size={16} color="var(--accent-primary)" />
                          <span>Client Relationship Classification</span>
                        </div>
                        {matches.suggestedClientStatus && (
                          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-primary)', background: 'var(--accent-light)', padding: '2px 8px', borderRadius: '4px' }}>
                            Suggested: {matches.suggestedClientStatus}
                          </span>
                        )}
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                        Dynamics 365 Sales classification: Specify whether this organization represents a New Client or an Existing Client relationship.
                      </p>
                      <div style={{ display: 'flex', gap: '1.5rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                          <input
                            type="radio"
                            name="clientRelationship"
                            value="New"
                            checked={clientRelationship === 'New'}
                            onChange={() => setClientRelationship('New')}
                          />
                          <span>New Client</span>
                        </label>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                          <input
                            type="radio"
                            name="clientRelationship"
                            value="Existing"
                            checked={clientRelationship === 'Existing'}
                            onChange={() => setClientRelationship('Existing')}
                          />
                          <span>Existing Client</span>
                        </label>
                      </div>
                    </div>

                    {/* Additional Contacts (if any attached to lead) */}
                    {lead.additionalContacts && lead.additionalContacts.length > 0 && (
                      <div style={{ gridColumn: '1 / -1', padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', background: '#f8fafc' }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '0.6rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <User size={15} color="#0284c7" />
                          <span>Additional Contacts ({lead.additionalContacts.length})</span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                          {lead.additionalContacts.map((c, idx) => (
                            <div key={c.id || idx} style={{ padding: '0.6rem 0.75rem', background: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.8rem' }}>
                              <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.name}</div>
                              <div style={{ color: 'var(--text-muted)' }}>{c.designation || c.email || c.mobileNumber || '—'}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* STEP 2: ACCOUNT MATCHING & SELECTION */}
              {currentStep === 2 && (
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    Resolve Account Association
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                    Choose whether to reuse an existing verified Account or create a new Account record from this lead.
                  </p>

                  {/* Matching Accounts Suggestions if any */}
                  {matches.matchingAccounts && matches.matchingAccounts.length > 0 && (
                    <div style={{
                      padding: '1rem',
                      background: '#fffbeb',
                      border: '1px solid #fde68a',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: '1.25rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#92400e', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.6rem' }}>
                        <Sparkles size={16} />
                        <span>Potential Account Matches Identified ({matches.matchingAccounts.length})</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {matches.matchingAccounts.map(acc => (
                          <div
                            key={acc.id}
                            onClick={() => {
                              setAccountAction('reuse');
                              setSelectedAccountId(acc.id);
                              setSelectedAccountObj(acc);
                            }}
                            style={{
                              padding: '0.6rem 0.8rem',
                              background: selectedAccountId === acc.id ? '#ffffff' : 'rgba(255, 255, 255, 0.7)',
                              border: selectedAccountId === acc.id ? '2px solid #d97706' : '1px solid #fcd34d',
                              borderRadius: 'var(--radius-sm)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem'
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#78350f' }}>
                                {acc.name} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#92400e' }}>({acc.accountId})</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: '#92400e' }}>
                                {acc.website || acc.email || acc.address || 'No additional contact info'}
                              </div>
                              {acc.matchReasons && acc.matchReasons.length > 0 && (
                                <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.2rem' }}>
                                  {acc.matchReasons.map(r => (
                                    <span key={r} style={{ fontSize: '0.675rem', background: '#fef3c7', padding: '1px 5px', borderRadius: '3px', color: '#b45309' }}>
                                      {r}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                            >
                              {selectedAccountId === acc.id ? 'Selected' : 'Select'}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Radio Choice: Reuse vs Create */}
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem' }}>
                    <label style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1rem',
                      border: `2px solid ${accountAction === 'reuse' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                      background: accountAction === 'reuse' ? 'var(--accent-light)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.9rem'
                    }}>
                      <input
                        type="radio"
                        name="accountAction"
                        checked={accountAction === 'reuse'}
                        onChange={() => setAccountAction('reuse')}
                      />
                      <span>Reuse Existing Account</span>
                    </label>

                    <label style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1rem',
                      border: `2px solid ${accountAction === 'create' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                      background: accountAction === 'create' ? 'var(--accent-light)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.9rem'
                    }}>
                      <input
                        type="radio"
                        name="accountAction"
                        checked={accountAction === 'create'}
                        onChange={() => setAccountAction('create')}
                      />
                      <span>Create New Account</span>
                    </label>
                  </div>

                  {accountAction === 'reuse' ? (
                    <div>
                      <label className="form-label">Search / Select Existing Account</label>
                      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                        <div style={{ position: 'relative', flex: 1 }}>
                          <input
                            type="text"
                            placeholder="Type account name to search..."
                            value={accountSearchQuery}
                            onChange={(e) => handleSearchAccounts(e.target.value)}
                            className="form-input"
                            style={{ width: '100%', paddingLeft: '2.2rem' }}
                          />
                          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                        </div>
                      </div>
                      {searchingAccounts && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '-0.25rem 0 0.5rem 0' }}>Searching accounts...</p>}

                      {searchedAccounts.length > 0 && (
                        <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem' }}>
                          {searchedAccounts.map(a => (
                            <div
                              key={a.id}
                              onClick={() => {
                                setSelectedAccountId(a.id);
                                setSelectedAccountObj(a);
                              }}
                              style={{
                                padding: '0.5rem 0.75rem',
                                borderBottom: '1px solid var(--border-color)',
                                cursor: 'pointer',
                                background: selectedAccountId === a.id ? 'var(--accent-light)' : 'transparent',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                              }}
                            >
                              <div>
                                <span style={{ fontWeight: 600 }}>{a.name}</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>({a.accountId})</span>
                              </div>
                              {selectedAccountId === a.id && <Check size={16} color="var(--accent-primary)" />}
                            </div>
                          ))}
                        </div>
                      )}

                      {selectedAccountObj && (
                        <div style={{ padding: '0.85rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', marginTop: '0.5rem' }}>
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>Selected Account for Reuse:</span>
                          <div style={{ fontWeight: 600, fontSize: '0.95rem', marginTop: '0.2rem' }}>{selectedAccountObj.name} ({selectedAccountObj.accountId})</div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                            {selectedAccountObj.website || selectedAccountObj.email || selectedAccountObj.phone || selectedAccountObj.address}
                          </div>

                          {/* Client Site Name Alignment / Choice */}
                          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-primary)' }}>
                              Client Site Name Resolution:
                            </div>
                            {selectedAccountObj.siteName && lead.siteName && selectedAccountObj.siteName.toLowerCase() !== lead.siteName.toLowerCase() ? (
                              <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '0.65rem 0.85rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                                <div style={{ marginBottom: '0.45rem', color: '#92400e', lineHeight: 1.4 }}>
                                  Existing Account site: <strong>{selectedAccountObj.siteName}</strong><br />
                                  Lead client site: <strong>{lead.siteName}</strong>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer', fontWeight: 500 }}>
                                    <input
                                      type="radio"
                                      name="reuseAccountSiteChoice"
                                      checked={reuseAccountSiteChoice === 'existing'}
                                      onChange={() => setReuseAccountSiteChoice('existing')}
                                    />
                                    <span>Keep existing site ({selectedAccountObj.siteName})</span>
                                  </label>
                                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer', fontWeight: 500 }}>
                                    <input
                                      type="radio"
                                      name="reuseAccountSiteChoice"
                                      checked={reuseAccountSiteChoice === 'lead'}
                                      onChange={() => setReuseAccountSiteChoice('lead')}
                                    />
                                    <span>Update to Lead's site ({lead.siteName})</span>
                                  </label>
                                </div>
                              </div>
                            ) : (
                              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                Site Name: <strong>{lead.siteName || selectedAccountObj.siteName || '(None specified)'}</strong>
                                {lead.siteName && !selectedAccountObj.siteName && (
                                  <span style={{ color: '#047857', marginLeft: '0.5rem', fontWeight: 500 }}>
                                    (Will assign Lead's Client Site Name "{lead.siteName}" to this Account)
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label">Account / Company Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                        <input
                          type="text"
                          value={newAccountData.name}
                          onChange={(e) => setNewAccountData({ ...newAccountData, name: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Client Site Name</label>
                        <input
                          type="text"
                          placeholder="e.g. Pune Plant / Unit 2"
                          value={newAccountData.siteName}
                          onChange={(e) => setNewAccountData({ ...newAccountData, siteName: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                          Prefilled from Lead Client Site Name
                        </span>
                      </div>
                      <div>
                        <label className="form-label">Website</label>
                        <input
                          type="text"
                          value={newAccountData.website}
                          onChange={(e) => setNewAccountData({ ...newAccountData, website: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Company Email</label>
                        <input
                          type="email"
                          value={newAccountData.email}
                          onChange={(e) => setNewAccountData({ ...newAccountData, email: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Business Phone</label>
                        <input
                          type="text"
                          placeholder="Company / office phone"
                          value={newAccountData.phone}
                          onChange={(e) => setNewAccountData({ ...newAccountData, phone: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Industry</label>
                        <input
                          type="text"
                          value={newAccountData.industry}
                          onChange={(e) => setNewAccountData({ ...newAccountData, industry: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 3: CONTACT MATCHING & SELECTION */}
              {currentStep === 3 && (
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    Resolve Contact Association
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                    Select an existing Contact or create a new Contact linked to the selected Account.
                  </p>

                  {/* Contact Matching Suggestions */}
                  {matches.matchingContacts && matches.matchingContacts.length > 0 && (
                    <div style={{
                      padding: '1rem',
                      background: '#eff6ff',
                      border: '1px solid #bfdbfe',
                      borderRadius: 'var(--radius-md)',
                      marginBottom: '1.25rem'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#1e40af', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.6rem' }}>
                        <Sparkles size={16} />
                        <span>Potential Contact Matches Identified ({matches.matchingContacts.length})</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {matches.matchingContacts.map(con => (
                          <div
                            key={con.id}
                            onClick={() => {
                              setContactAction('reuse');
                              setSelectedContactId(con.id);
                              setSelectedContactObj(con);
                            }}
                            style={{
                              padding: '0.6rem 0.8rem',
                              background: selectedContactId === con.id ? '#ffffff' : 'rgba(255, 255, 255, 0.7)',
                              border: selectedContactId === con.id ? '2px solid var(--accent-primary)' : '1px solid #93c5fd',
                              borderRadius: 'var(--radius-sm)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem'
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#1e3a8a' }}>
                                {con.name} <span style={{ fontSize: '0.75rem', fontWeight: 400, color: '#3b82f6' }}>({con.contactId})</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>
                                {con.email || con.mobileNumber || con.designation} {con.accountName ? `• Account: ${con.accountName}` : ''}
                              </div>
                              {con.matchReasons && con.matchReasons.length > 0 && (
                                <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.2rem' }}>
                                  {con.matchReasons.map(r => (
                                    <span key={r} style={{ fontSize: '0.675rem', background: '#dbeafe', padding: '1px 5px', borderRadius: '3px', color: '#1d4ed8' }}>
                                      {r}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem' }}
                            >
                              {selectedContactId === con.id ? 'Selected' : 'Select'}
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Radio Choice: Reuse vs Create */}
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem' }}>
                    <label style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1rem',
                      border: `2px solid ${contactAction === 'reuse' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                      background: contactAction === 'reuse' ? 'var(--accent-light)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.9rem'
                    }}>
                      <input
                        type="radio"
                        name="contactAction"
                        checked={contactAction === 'reuse'}
                        onChange={() => setContactAction('reuse')}
                      />
                      <span>Reuse Existing Contact</span>
                    </label>

                    <label style={{
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1rem',
                      border: `2px solid ${contactAction === 'create' ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                      background: contactAction === 'create' ? 'var(--accent-light)' : 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.9rem'
                    }}>
                      <input
                        type="radio"
                        name="contactAction"
                        checked={contactAction === 'create'}
                        onChange={() => setContactAction('create')}
                      />
                      <span>Create New Contact</span>
                    </label>
                  </div>

                  {contactAction === 'reuse' ? (
                    <div>
                      <label className="form-label">Search / Select Existing Contact</label>
                      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                        <div style={{ position: 'relative', flex: 1 }}>
                          <input
                            type="text"
                            placeholder="Type contact name, phone, or email to search..."
                            value={contactSearchQuery}
                            onChange={(e) => handleSearchContacts(e.target.value)}
                            className="form-input"
                            style={{ width: '100%', paddingLeft: '2.2rem' }}
                          />
                          <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                        </div>
                      </div>
                      {searchingContacts && <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: '-0.25rem 0 0.5rem 0' }}>Searching contacts...</p>}

                      {searchedContacts.length > 0 && (
                        <div style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem' }}>
                          {searchedContacts.map(c => (
                            <div
                              key={c.id}
                              onClick={() => {
                                setSelectedContactId(c.id);
                                setSelectedContactObj(c);
                              }}
                              style={{
                                padding: '0.5rem 0.75rem',
                                borderBottom: '1px solid var(--border-color)',
                                cursor: 'pointer',
                                background: selectedContactId === c.id ? 'var(--accent-light)' : 'transparent',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center'
                              }}
                            >
                              <div>
                                <span style={{ fontWeight: 600 }}>{c.name}</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                                  ({c.contactId}) {c.accountName ? `— ${c.accountName}` : ''}
                                </span>
                              </div>
                              {selectedContactId === c.id && <Check size={16} color="var(--accent-primary)" />}
                            </div>
                          ))}
                        </div>
                      )}

                      {selectedContactObj && (
                        <div style={{ padding: '0.75rem', background: 'var(--bg-primary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', marginTop: '0.5rem' }}>
                          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-primary)', textTransform: 'uppercase' }}>Selected Primary Contact for Reuse:</span>
                          <div style={{ fontWeight: 600, fontSize: '0.95rem', marginTop: '0.2rem' }}>{selectedContactObj.name} ({selectedContactObj.contactId})</div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{selectedContactObj.email || selectedContactObj.mobileNumber}</div>
                        </div>
                      )}

                      {/* Account Mismatch Warning */}
                      {selectedAccountObj?.id && selectedContactObj?.accountId && selectedContactObj.accountId !== selectedAccountObj.id && (
                        <div style={{ marginTop: '0.75rem', padding: '0.75rem 1rem', background: 'var(--danger-bg)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius-sm)', color: 'var(--danger-text)', fontSize: '0.825rem', display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
                          <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                          <div>
                            <strong>Account Mismatch:</strong> Selected contact '{selectedContactObj.name}' belongs to another Account ({selectedContactObj.accountName || selectedContactObj.accountId}).
                            The Opportunity's Primary Contact must belong to the selected Opportunity Account. Please select a contact from the chosen account or create a new contact.
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label">Full Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                        <input
                          type="text"
                          value={newContactData.name}
                          onChange={(e) => setNewContactData({ ...newContactData, name: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Email</label>
                        <input
                          type="email"
                          value={newContactData.email}
                          onChange={(e) => setNewContactData({ ...newContactData, email: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Mobile Number</label>
                        <input
                          type="tel"
                          value={newContactData.mobileNumber}
                          onChange={(e) => setNewContactData({ ...newContactData, mobileNumber: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Job Title / Designation</label>
                        <input
                          type="text"
                          value={newContactData.designation}
                          onChange={(e) => setNewContactData({ ...newContactData, designation: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 4: OPPORTUNITY SPECIFICATIONS */}
              {currentStep === 4 && (
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    Opportunity Details
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                    Confirm the Opportunity parameters. Lead requirement specifications and client history will carry forward automatically.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                      <label className="form-label">Opportunity Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                      <input
                        type="text"
                        value={opportunityData.name}
                        onChange={(e) => setOpportunityData({ ...opportunityData, name: e.target.value })}
                        className="form-input"
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                      <div>
                        <label className="form-label">Estimated Value (Optional)</label>
                        <input
                          type="number"
                          min="0"
                          step="any"
                          placeholder="e.g. 500000"
                          value={opportunityData.estimatedValue}
                          onChange={(e) => setOpportunityData({ ...opportunityData, estimatedValue: e.target.value })}
                          className="form-input"
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div>
                        <label className="form-label">Currency</label>
                        <input
                          type="text"
                          value={opportunityData.currency}
                          disabled
                          className="form-input"
                          style={{ width: '100%', background: 'var(--bg-primary)' }}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="form-label">Opportunity Description / Scope</label>
                      <textarea
                        rows={3}
                        value={opportunityData.description}
                        onChange={(e) => setOpportunityData({ ...opportunityData, description: e.target.value })}
                        className="form-textarea"
                        style={{ width: '100%', resize: 'vertical' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 5: CONFIRM AND QUALIFY */}
              {currentStep === 5 && (
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
                    Confirm Qualification
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
                    Please review the planned records before committing. This transaction will link the Lead, Account, Contact, and Opportunity together.
                  </p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Classification Summary */}
                    <div style={{ padding: '0.85rem 1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', background: 'var(--bg-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>Client Classification</span>
                      <span style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        background: clientRelationship === 'Existing' ? '#ecfdf5' : '#eff6ff',
                        color: clientRelationship === 'Existing' ? '#065f46' : '#1e40af'
                      }}>
                        {clientRelationship} Client
                      </span>
                    </div>

                    {/* Account Summary */}
                    <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Account Action</span>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: accountAction === 'reuse' ? '#ecfdf5' : '#eff6ff',
                          color: accountAction === 'reuse' ? '#065f46' : '#1e40af'
                        }}>
                          {accountAction === 'reuse' ? 'Reuse Existing Account' : 'Create New Account'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.35rem' }}>
                        <div><strong>Name:</strong> {accountAction === 'reuse' ? (selectedAccountObj?.name || selectedAccountId) : newAccountData.name}</div>
                        <div><strong>Client Site Name:</strong> {(accountAction === 'create' ? (newAccountData.siteName || lead.siteName) : (reuseAccountSiteChoice === 'lead' ? (lead.siteName || selectedAccountObj?.siteName) : (selectedAccountObj?.siteName || lead.siteName))) || '—'}</div>
                        <div><strong>Business Phone:</strong> {accountAction === 'reuse' ? (selectedAccountObj?.phone || lead.businessPhone || '—') : (newAccountData.phone || '—')}</div>
                        <div><strong>Company Email:</strong> {accountAction === 'reuse' ? (selectedAccountObj?.email || lead.companyEmail || '—') : (newAccountData.email || '—')}</div>
                      </div>
                    </div>

                    {/* Contact Summary */}
                    <div style={{ padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Primary Contact</span>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: contactAction === 'reuse' ? '#ecfdf5' : '#eff6ff',
                          color: contactAction === 'reuse' ? '#065f46' : '#1e40af'
                        }}>
                          {contactAction === 'reuse' ? 'Reuse Existing Contact' : 'Create New Contact'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.35rem' }}>
                        <div><strong>Name:</strong> {contactAction === 'reuse' ? (selectedContactObj?.name || selectedContactId) : newContactData.name}</div>
                        <div><strong>Mobile Phone:</strong> {contactAction === 'reuse' ? (selectedContactObj?.mobileNumber || '—') : (newContactData.mobileNumber || '—')}</div>
                        <div><strong>Email:</strong> {contactAction === 'reuse' ? (selectedContactObj?.email || '—') : (newContactData.email || '—')}</div>
                        <div><strong>Designation:</strong> {contactAction === 'reuse' ? (selectedContactObj?.designation || '—') : (newContactData.designation || '—')}</div>
                      </div>
                    </div>

                    {/* Opportunity Summary */}
                    <div style={{ padding: '1rem', border: '1px solid var(--accent-light)', borderRadius: 'var(--radius-md)', background: 'var(--accent-light)' }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-hover)', marginBottom: '0.4rem' }}>
                        Opportunity to Create
                      </div>
                      <div style={{ fontSize: '0.875rem', color: 'var(--accent-hover)' }}>
                        <div><strong>Name:</strong> {opportunityData.name}</div>
                        {opportunityData.estimatedValue && (
                          <div><strong>Est. Value:</strong> {opportunityData.currency} {Number(opportunityData.estimatedValue).toLocaleString()}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

        </div>

        {/* Wizard Footer Controls */}
        {!qualificationResult && (
          <div style={{
            padding: '1rem 1.75rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-primary)'
          }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={currentStep === 1 ? onClose : handleBack}
              disabled={submitting}
            >
              {currentStep === 1 ? 'Cancel' : 'Back'}
            </button>

            <div>
              {currentStep < 5 ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleNext}
                  disabled={submitting || loadingMatches}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <span>Next</span>
                  <ArrowRight size={16} />
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConfirmQualify}
                  disabled={submitting}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', background: 'var(--success)', borderColor: 'var(--success)' }}
                >
                  <ShieldCheck size={18} />
                  <span>{submitting ? 'Executing Qualification...' : 'Confirm & Qualify'}</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
