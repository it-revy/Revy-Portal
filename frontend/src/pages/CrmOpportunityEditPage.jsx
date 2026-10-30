import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeft,
  Save,
  Check,
  X,
  AlertCircle,
  Building,
  User,
  Briefcase,
  TrendingUp,
  DollarSign,
  Calendar,
  FileText,
  CheckCircle2,
  Lock,
  ArrowRight
} from 'lucide-react';
import crmService from '../services/crmService';

const CANONICAL_STAGES = [
  'Enquiry',
  'Qualify',
  'Develop',
  'Propose/Offer',
  'Negotiate',
  'Close'
];

const STAGE_ORDER = {
  'Enquiry': 0,
  'Qualify': 1,
  'Develop': 2,
  'Propose': 3,
  'Propose/Offer': 3,
  'Negotiate': 4,
  'Close': 5
};

const BUSINESS_AREAS = [
  'Biogas',
  'Wastewater Treatment (WWT)',
  'R&D Lab',
  'Solid Waste',
  'Other'
];

const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP'];

export default function CrmOpportunityEditPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const targetStageParam = searchParams.get('targetStage');
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();

  // Authoritative Role Checks
  const isManager = hasRole('CRM_SALES_MANAGER') || hasRole('CRM_ADMIN') || hasRole('IT_ADMIN') || hasRole('DIRECTOR');
  const isAdmin = hasRole('CRM_ADMIN') || hasRole('IT_ADMIN') || hasRole('DIRECTOR');

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  // Lookups
  const [accounts, setAccounts] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [assignees, setAssignees] = useState([]);

  // Original Saved Opportunity State
  const [originalOpp, setOriginalOpp] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    opportunityCode: '',
    accountId: '',
    contactId: '',
    stage: 'Enquiry',
    status: 'Open', // 'Open', 'Won', 'Lost'
    outcomeLabel: 'Open Pipeline', // 'Open Pipeline', 'Closed Won', 'Closed Lost'
    lossReason: '',
    actualCloseDate: '',
    businessArea: 'Biogas',
    estimatedValue: '',
    currency: 'INR',
    expectedCloseDate: '',
    assignedToUserId: '',
    subStatus: '',
    description: '',
    reopenReason: ''
  });

  const [fieldErrors, setFieldErrors] = useState({});

  // 1. Load Lookups (Accounts, Contacts, Assignees)
  useEffect(() => {
    async function loadLookups() {
      try {
        const [accRes, contRes, assRes] = await Promise.allSettled([
          crmService.getAccounts({ limit: 100 }),
          crmService.getContacts({ limit: 100 }),
          crmService.getEligibleAssignees()
        ]);

        if (accRes.status === 'fulfilled' && accRes.value.data?.success) {
          setAccounts(accRes.value.data.accounts || []);
        }
        if (contRes.status === 'fulfilled' && contRes.value.data?.success) {
          setContacts(contRes.value.data.contacts || []);
        }
        if (assRes.status === 'fulfilled' && assRes.value.data?.success) {
          setAssignees(assRes.value.data.assignees || []);
        }
      } catch (err) {
        console.error('Failed to load lookup data:', err);
      }
    }
    loadLookups();
  }, []);

  // 2. Load Opportunity Data
  useEffect(() => {
    async function fetchOpportunity() {
      setLoading(true);
      setError(null);
      try {
        const res = await crmService.getOpportunityById(id);
        if (res.data?.success && res.data.opportunity) {
          const opp = res.data.opportunity;
          setOriginalOpp(opp);

          let initialStage = opp.stage || 'Enquiry';
          if (initialStage === 'Propose') initialStage = 'Propose/Offer';

          let initialStatus = opp.status || 'Open';
          let initialOutcome = 'Open Pipeline';
          if (initialStatus === 'Won') initialOutcome = 'Closed Won';
          if (initialStatus === 'Lost') initialOutcome = 'Closed Lost';

          // If targetStage was passed from drag-and-drop workflow
          let pendingStage = initialStage;
          let pendingStatus = initialStatus;
          let pendingOutcome = initialOutcome;

          if (targetStageParam && CANONICAL_STAGES.includes(targetStageParam)) {
            pendingStage = targetStageParam;
            if (pendingStage === 'Close') {
              // If moving to Close, default to Won unless already Lost
              if (pendingStatus !== 'Won' && pendingStatus !== 'Lost') {
                pendingStatus = 'Won';
                pendingOutcome = 'Closed Won';
              }
            } else {
              // If moving to earlier stage, outcome becomes Open Pipeline
              pendingStatus = 'Open';
              pendingOutcome = 'Open Pipeline';
            }
          }

          setFormData({
            name: opp.name || '',
            opportunityCode: opp.opportunityId || id,
            accountId: opp.accountId || opp.account_id || '',
            contactId: opp.contactId || opp.contact_id || '',
            stage: pendingStage,
            status: pendingStatus,
            outcomeLabel: pendingOutcome,
            lossReason: opp.lossReason || '',
            actualCloseDate: opp.actualCloseDate ? opp.actualCloseDate.slice(0, 10) : '',
            businessArea: opp.businessArea || 'Biogas',
            estimatedValue: opp.estimatedValue !== null && opp.estimatedValue !== undefined ? String(opp.estimatedValue) : '',
            currency: opp.currency || 'INR',
            expectedCloseDate: opp.expectedCloseDate ? opp.expectedCloseDate.slice(0, 10) : '',
            assignedToUserId: opp.assignedToUserId || opp.assigned_to_user_id || '',
            subStatus: opp.subStatus || opp.sub_status || '',
            description: opp.description || '',
            reopenReason: ''
          });

          // Mark dirty if targetStage was applied
          if (targetStageParam && targetStageParam !== initialStage) {
            setIsDirty(true);
          }
        } else {
          throw new Error(res.data?.message || 'Opportunity not found.');
        }
      } catch (err) {
        console.error('Error loading opportunity:', err);
        setError(err.response?.data?.message || err.message || 'Failed to load opportunity.');
      } finally {
        setLoading(false);
      }
    }

    if (id) {
      fetchOpportunity();
    }
  }, [id, targetStageParam]);

  // Stage change handler
  const handleStageChange = (newStage) => {
    setIsDirty(true);
    const originalStage = originalOpp?.stage === 'Propose' ? 'Propose/Offer' : (originalOpp?.stage || 'Enquiry');
    const origOrder = STAGE_ORDER[originalStage] ?? 0;
    const newOrder = STAGE_ORDER[newStage] ?? 0;

    // Check backward movement permission
    if (newOrder < origOrder && !isManager) {
      setError(`Permission Denied: Moving opportunity backward from "${originalStage}" to "${newStage}" requires Sales Manager or Administrator role.`);
      return;
    } else {
      if (error && error.includes('Permission Denied')) setError(null);
    }

    // Check reopening guard if original deal was Won/Lost and moving back to open pipeline
    if (originalOpp && (originalOpp.status === 'Won' || originalOpp.status === 'Lost') && newStage !== 'Close') {
      if (!isAdmin) {
        setError('Permission Denied: Only CRM Administrators can reopen a Closed Won or Closed Lost opportunity.');
        return;
      }
    }

    setFormData(prev => {
      let nextStatus = prev.status;
      let nextOutcome = prev.outcomeLabel;

      if (newStage === 'Close') {
        if (nextStatus !== 'Won' && nextStatus !== 'Lost') {
          nextStatus = 'Won';
          nextOutcome = 'Closed Won';
        }
      } else {
        nextStatus = 'Open';
        nextOutcome = 'Open Pipeline';
      }

      return {
        ...prev,
        stage: newStage,
        status: nextStatus,
        outcomeLabel: nextOutcome
      };
    });
  };

  // Outcome change handler (only applicable when stage is 'Close')
  const handleOutcomeChange = (newOutcome) => {
    setIsDirty(true);
    setFormData(prev => {
      let nextStatus = 'Open';
      if (newOutcome === 'Closed Won') nextStatus = 'Won';
      if (newOutcome === 'Closed Lost') nextStatus = 'Lost';

      return {
        ...prev,
        outcomeLabel: newOutcome,
        status: nextStatus,
        actualCloseDate: (!prev.actualCloseDate && (nextStatus === 'Won' || nextStatus === 'Lost'))
          ? new Date().toISOString().slice(0, 10)
          : prev.actualCloseDate
      };
    });
  };

  // Field change handler
  const handleChange = (e) => {
    const { name, value } = e.target;
    setIsDirty(true);
    setFormData(prev => ({ ...prev, [name]: value }));

    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  // Client-side validation enforcing business rules
  const validateForm = () => {
    const errors = {};

    // 1. Name required
    if (!formData.name || !formData.name.trim()) {
      errors.name = 'Opportunity name is required.';
    }

    // 2. Primary relationship rule: at least one of accountId or contactId
    const hasAccount = Boolean(formData.accountId);
    const hasContact = Boolean(formData.contactId);
    if (!hasAccount && !hasContact) {
      errors.relationships = 'At least one of Primary Account or Primary Contact must be selected.';
      errors.accountId = 'Select Primary Account or Primary Contact.';
      errors.contactId = 'Select Primary Account or Primary Contact.';
    }

    // 3. Amount non-negative
    if (formData.estimatedValue !== '' && formData.estimatedValue !== null) {
      const val = Number(formData.estimatedValue);
      if (isNaN(val) || val < 0) {
        errors.estimatedValue = 'Commercial value must be a non-negative number (0 or greater).';
      }
    }

    // 4. Close stage & outcome consistency
    if (formData.stage === 'Close') {
      if (formData.status !== 'Won' && formData.status !== 'Lost') {
        errors.outcome = 'An opportunity in the Close stage must have outcome set to Closed Won or Closed Lost.';
      }
      if (formData.status === 'Lost' && (!formData.lossReason || !formData.lossReason.trim())) {
        errors.lossReason = 'Mandatory loss reason is required when marking an opportunity as Closed Lost.';
      }
    } else {
      if (formData.status === 'Won' || formData.status === 'Lost') {
        errors.stage = 'Closed Won and Closed Lost opportunities must be in the Close stage.';
      }
    }

    // 5. Backward movement permission
    const originalStage = originalOpp?.stage === 'Propose' ? 'Propose/Offer' : (originalOpp?.stage || 'Enquiry');
    const origOrder = STAGE_ORDER[originalStage] ?? 0;
    const newOrder = STAGE_ORDER[formData.stage] ?? 0;
    if (newOrder < origOrder && !isManager) {
      errors.stage = `Moving backward to "${formData.stage}" requires Sales Manager role.`;
    }

    // 6. Reopening permission
    if (originalOpp && (originalOpp.status === 'Won' || originalOpp.status === 'Lost') && formData.stage !== 'Close') {
      if (!isAdmin) {
        errors.stage = 'Only CRM Administrators can reopen closed opportunities.';
      }
      if (!formData.reopenReason || !formData.reopenReason.trim()) {
        errors.reopenReason = 'A justification reason is required to reopen a closed opportunity.';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Submit Handler
  const handleSubmit = async (shouldReturn = false) => {
    if (submitting) return;

    if (!validateForm()) {
      setError('Please resolve the errors highlighted below.');
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccessMsg(null);

    try {
      // Check if reopening closed deal
      const wasClosed = originalOpp && (originalOpp.status === 'Won' || originalOpp.status === 'Lost');
      const isReopening = wasClosed && formData.stage !== 'Close';

      if (isReopening) {
        // Reopen explicitly first
        await crmService.reopenOpportunity(id, {
          reopenStage: formData.stage,
          reason: formData.reopenReason.trim()
        });
      }

      // Update opportunity core fields
      const payload = {
        name: formData.name.trim(),
        accountId: formData.accountId || null,
        contactId: formData.contactId || null,
        stage: formData.stage,
        status: formData.status,
        lossReason: formData.status === 'Lost' ? (formData.lossReason.trim() || null) : null,
        actualCloseDate: (formData.status === 'Won' || formData.status === 'Lost')
          ? (formData.actualCloseDate ? `${formData.actualCloseDate}T00:00:00` : new Date().toISOString())
          : null,
        businessArea: formData.businessArea || null,
        estimatedValue: formData.estimatedValue !== '' ? Number(formData.estimatedValue) : null,
        currency: formData.currency,
        expectedCloseDate: formData.expectedCloseDate ? `${formData.expectedCloseDate}T00:00:00` : null,
        assignedToUserId: formData.assignedToUserId || null,
        subStatus: formData.subStatus.trim() || null,
        description: formData.description.trim() || null
      };

      const res = await crmService.updateOpportunity(id, payload);

      if (res.data?.success && res.data.opportunity) {
        setSuccessMsg('Opportunity successfully updated and changes confirmed.');
        setIsDirty(false);
        setOriginalOpp(res.data.opportunity);

        if (shouldReturn) {
          setTimeout(() => {
            navigate('/crm/opportunities');
          }, 600);
        }
      } else {
        throw new Error(res.data?.message || 'Failed to save opportunity updates.');
      }
    } catch (err) {
      console.error('Save Opportunity error:', err);
      const msg = err.response?.data?.message || err.response?.data?.detail || err.message || 'Error updating opportunity.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (isDirty) {
      setShowCancelConfirm(true);
    } else {
      navigate('/crm/opportunities');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Loading Opportunity Data...</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Retrieving CRM record and relationship links</div>
      </div>
    );
  }

  const isPendingTransition = targetStageParam && originalOpp && targetStageParam !== (originalOpp.stage === 'Propose' ? 'Propose/Offer' : originalOpp.stage);
  const wasClosedOriginally = originalOpp && (originalOpp.status === 'Won' || originalOpp.status === 'Lost');
  const isReopeningMode = wasClosedOriginally && formData.stage !== 'Close';

  return (
    <div className="page-body" style={{ maxWidth: '1100px' }}>
      {/* Top Header Command Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.825rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
            <Link to="/crm/dashboard" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>CRM</Link>
            <span>/</span>
            <Link to="/crm/opportunities" style={{ color: 'var(--text-muted)', textDecoration: 'none' }}>Opportunities</Link>
            <span>/</span>
            <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{formData.opportunityCode}</span>
            <span>/</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Edit</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
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
              title="Return to Opportunities"
            >
              <ArrowLeft size={20} />
            </button>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              Edit Opportunity — {formData.name || formData.opportunityCode}
            </h1>
          </div>
          <p style={{ margin: '0.25rem 0 0 2rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Review and confirm stage progressions, commercial terms, and account relationships.
          </p>
        </div>

        {/* Action Buttons */}
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
            <span>Save & Return</span>
          </button>
          <button
            type="button"
            onClick={() => handleSubmit(false)}
            className="btn btn-primary"
            disabled={submitting}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <Check size={16} />
            <span>{submitting ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      {/* Pending Drag-and-Drop Stage Transition Banner */}
      {isPendingTransition && (
        <div style={{
          padding: '1.25rem',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: '#dbeafe',
            color: '#1d4ed8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <TrendingUp size={22} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1e40af', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>Pending Stage Transition:</span>
              <span style={{ textDecoration: 'line-through', opacity: 0.7 }}>
                {originalOpp.stage === 'Propose' ? 'Propose/Offer' : originalOpp.stage}
              </span>
              <ArrowRight size={16} />
              <span style={{ background: '#dbeafe', padding: '2px 8px', borderRadius: '4px' }}>
                {formData.stage}
              </span>
            </div>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: '#1e3a8a' }}>
              Drag-and-drop initiated this stage move. Per REVY CRM governance, changes are not persisted until you explicitly verify required details and click Save.
            </p>
          </div>
        </div>
      )}

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
              You have unsaved changes or a pending stage transition. If you discard, the opportunity will remain in its original stage ({originalOpp?.stage}).
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
                onClick={() => navigate('/crm/opportunities')}
              >
                Discard & Leave
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Form Form Grid */}
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(false); }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* SECTION 1: OPPORTUNITY BASICS */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
              <Briefcase size={20} color="var(--accent-primary)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                1. Opportunity Information
              </h2>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {/* Opportunity Code (Read-only) */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Opportunity ID
                </label>
                <input
                  type="text"
                  className="form-control"
                  value={formData.opportunityCode}
                  readOnly
                  style={{ background: '#f8fafc', color: 'var(--text-secondary)', cursor: 'not-allowed', fontWeight: 600 }}
                />
              </div>

              {/* Opportunity Name */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Opportunity Title / Name <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <input
                  type="text"
                  name="name"
                  className={`form-control ${fieldErrors.name ? 'is-invalid' : ''}`}
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g. BMP Test & Characterization"
                />
                {fieldErrors.name && (
                  <div style={{ color: 'var(--danger)', fontSize: '0.775rem', marginTop: '0.25rem' }}>
                    {fieldErrors.name}
                  </div>
                )}
              </div>

              {/* Business Area */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Business Area
                </label>
                <select
                  name="businessArea"
                  className="form-control"
                  value={formData.businessArea}
                  onChange={handleChange}
                >
                  {BUSINESS_AREAS.map(ba => (
                    <option key={ba} value={ba}>{ba}</option>
                  ))}
                </select>
              </div>

              {/* Estimated Value & Currency */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Estimated Commercial Value (&ge; 0)
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <select
                    name="currency"
                    className="form-control"
                    value={formData.currency}
                    onChange={handleChange}
                    style={{ width: '90px' }}
                  >
                    {CURRENCIES.map(curr => (
                      <option key={curr} value={curr}>{curr}</option>
                    ))}
                  </select>
                  <input
                    type="number"
                    name="estimatedValue"
                    min="0"
                    step="0.01"
                    className={`form-control ${fieldErrors.estimatedValue ? 'is-invalid' : ''}`}
                    value={formData.estimatedValue}
                    onChange={handleChange}
                    placeholder="0.00"
                    style={{ flex: 1 }}
                  />
                </div>
                {fieldErrors.estimatedValue && (
                  <div style={{ color: 'var(--danger)', fontSize: '0.775rem', marginTop: '0.25rem' }}>
                    {fieldErrors.estimatedValue}
                  </div>
                )}
              </div>

              {/* Expected Close Date */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Expected Close Date
                </label>
                <input
                  type="date"
                  name="expectedCloseDate"
                  className="form-control"
                  value={formData.expectedCloseDate}
                  onChange={handleChange}
                />
              </div>

              {/* Owner / Assigned User */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Opportunity Owner
                </label>
                <select
                  name="assignedToUserId"
                  className="form-control"
                  value={formData.assignedToUserId}
                  onChange={handleChange}
                >
                  <option value="">-- Unassigned --</option>
                  {assignees.map(a => (
                    <option key={a.id} value={a.id}>
                      {a.name || a.username} ({a.activeRole || 'Sales Rep'})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* SECTION 2: RELATIONSHIP GOVERNANCE (ACCOUNT OR CONTACT REQUIRED) */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Building size={20} color="#d97706" />
                <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  2. Primary Account & Contact Links
                </h2>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-primary)', fontWeight: 600, background: '#eff6ff', padding: '2px 8px', borderRadius: '4px' }}>
                At least one required
              </span>
            </div>
            <p style={{ margin: '0 0 1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              An opportunity must be associated with a Primary Account, a Primary Contact, or both. An opportunity cannot exist detached from both entities.
            </p>

            {fieldErrors.relationships && (
              <div style={{
                padding: '0.75rem 1rem',
                background: 'var(--danger-bg)',
                border: '1px solid var(--danger-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--danger-text)',
                marginBottom: '1rem',
                fontSize: '0.825rem'
              }}>
                {fieldErrors.relationships}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {/* Primary Account */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Primary Account
                </label>
                <select
                  name="accountId"
                  className={`form-control ${fieldErrors.accountId ? 'is-invalid' : ''}`}
                  value={formData.accountId}
                  onChange={handleChange}
                >
                  <option value="">-- None Selected --</option>
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.accountId})
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                  Optional if Primary Contact is provided.
                </span>
              </div>

              {/* Primary Contact */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Primary Contact
                </label>
                <select
                  name="contactId"
                  className={`form-control ${fieldErrors.contactId ? 'is-invalid' : ''}`}
                  value={formData.contactId}
                  onChange={handleChange}
                >
                  <option value="">-- None Selected --</option>
                  {contacts.map(cont => (
                    <option key={cont.id} value={cont.id}>
                      {cont.name} {cont.accountName ? `— (${cont.accountName})` : ''}
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                  Optional if Primary Account is provided.
                </span>
              </div>
            </div>
          </div>

          {/* SECTION 3: PIPELINE STAGE & OUTCOME GOVERNANCE */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <TrendingUp size={20} color="var(--accent-primary)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                3. Stage & Outcome Governance
              </h2>
            </div>
            <p style={{ margin: '0 0 1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Enforces pipeline business rules: Close stage requires Closed Won or Closed Lost. Earlier stages must have outcome set to Open Pipeline. Moving backward requires Sales Manager permissions.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
              {/* Pipeline Stage */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Pipeline Stage <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <select
                  className={`form-control ${fieldErrors.stage ? 'is-invalid' : ''}`}
                  value={formData.stage}
                  onChange={(e) => handleStageChange(e.target.value)}
                >
                  {CANONICAL_STAGES.map((stg) => {
                    const originalStage = originalOpp?.stage === 'Propose' ? 'Propose/Offer' : (originalOpp?.stage || 'Enquiry');
                    const origOrder = STAGE_ORDER[originalStage] ?? 0;
                    const stgOrder = STAGE_ORDER[stg] ?? 0;
                    const isBackward = stgOrder < origOrder;
                    const disabled = isBackward && !isManager;

                    return (
                      <option key={stg} value={stg} disabled={disabled}>
                        {stg} {disabled ? '(Requires Sales Manager)' : ''}
                      </option>
                    );
                  })}
                </select>
                {fieldErrors.stage && (
                  <div style={{ color: 'var(--danger)', fontSize: '0.775rem', marginTop: '0.25rem' }}>
                    {fieldErrors.stage}
                  </div>
                )}
                {!isManager && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Lock size={12} />
                    <span>Backward stage transitions disabled for non-manager role.</span>
                  </div>
                )}
              </div>

              {/* Opportunity Outcome */}
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Opportunity Outcome <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                {formData.stage === 'Close' ? (
                  <select
                    className={`form-control ${fieldErrors.outcome ? 'is-invalid' : ''}`}
                    value={formData.outcomeLabel}
                    onChange={(e) => handleOutcomeChange(e.target.value)}
                  >
                    <option value="Closed Won">Closed Won</option>
                    <option value="Closed Lost">Closed Lost</option>
                  </select>
                ) : (
                  <input
                    type="text"
                    className="form-control"
                    value="Open Pipeline"
                    readOnly
                    style={{ background: '#f8fafc', color: 'var(--text-secondary)', cursor: 'not-allowed', fontWeight: 600 }}
                  />
                )}
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                  {formData.stage === 'Close'
                    ? 'Close stage requires an explicit Won or Lost determination.'
                    : 'Earlier pipeline stages strictly maintain Open Pipeline outcome.'}
                </span>
              </div>
            </div>

            {/* Mandatory Loss Reason if Closed Lost */}
            {formData.status === 'Lost' && (
              <div style={{
                marginBottom: '1.25rem',
                padding: '1rem',
                background: 'var(--danger-bg)',
                border: '1px solid var(--danger-border)',
                borderRadius: 'var(--radius-sm)'
              }}>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, color: 'var(--danger-text)', marginBottom: '0.35rem' }}>
                  Mandatory Loss Reason <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <textarea
                  name="lossReason"
                  className={`form-control ${fieldErrors.lossReason ? 'is-invalid' : ''}`}
                  rows={2}
                  value={formData.lossReason}
                  onChange={handleChange}
                  placeholder="Specify why this deal was lost (e.g., pricing competition, project cancelled, technical unfeasibility)..."
                />
                {fieldErrors.lossReason && (
                  <div style={{ color: 'var(--danger)', fontSize: '0.775rem', marginTop: '0.25rem' }}>
                    {fieldErrors.lossReason}
                  </div>
                )}
              </div>
            )}

            {/* Reopening Justification if Deal was closed and is now moving to open pipeline */}
            {isReopeningMode && (
              <div style={{
                marginBottom: '1.25rem',
                padding: '1rem',
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: 'var(--radius-sm)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                  <AlertCircle size={16} color="#d97706" />
                  <strong style={{ fontSize: '0.85rem', color: '#b45309' }}>
                    Reopening Closed Opportunity (Admin Authorization Required)
                  </strong>
                </div>
                <p style={{ margin: '0 0 0.5rem', fontSize: '0.8rem', color: '#92400e' }}>
                  This deal was previously {originalOpp.status === 'Won' ? 'Closed Won' : 'Closed Lost'}. Reopening moves it back into active pipeline.
                </p>
                <textarea
                  name="reopenReason"
                  className={`form-control ${fieldErrors.reopenReason ? 'is-invalid' : ''}`}
                  rows={2}
                  value={formData.reopenReason}
                  onChange={handleChange}
                  placeholder="Provide authoritative business justification for reopening this closed opportunity..."
                />
                {fieldErrors.reopenReason && (
                  <div style={{ color: 'var(--danger)', fontSize: '0.775rem', marginTop: '0.25rem' }}>
                    {fieldErrors.reopenReason}
                  </div>
                )}
              </div>
            )}

            {/* Actual Close Date (when Closed Won or Closed Lost) */}
            {(formData.status === 'Won' || formData.status === 'Lost') && (
              <div style={{ maxWidth: '320px' }}>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Actual Close Date
                </label>
                <input
                  type="date"
                  name="actualCloseDate"
                  className="form-control"
                  value={formData.actualCloseDate}
                  onChange={handleChange}
                />
              </div>
            )}
          </div>

          {/* SECTION 4: SUB-STATUS & SUMMARY */}
          <div className="glass-panel" style={{ padding: '1.5rem', borderRadius: 'var(--radius-md)', boxShadow: 'var(--card-shadow)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1.25rem' }}>
              <FileText size={20} color="var(--accent-primary)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                4. Operational Notes & Sub-status
              </h2>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Sub-status / Action Item Note
                </label>
                <input
                  type="text"
                  name="subStatus"
                  className="form-control"
                  value={formData.subStatus}
                  onChange={handleChange}
                  placeholder="e.g. Awaiting client revised biomass sample, Quotation pending MD signoff"
                />
              </div>

              <div>
                <label className="form-label" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  Requirement Description
                </label>
                <textarea
                  name="description"
                  className="form-control"
                  rows={4}
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Detailed notes regarding scope, customer technical constraints, commercial timeline, deliverables..."
                />
              </div>
            </div>
          </div>

          {/* Bottom Action Footer */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '0.5rem' }}>
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
              Save & Return
            </button>
            <button
              type="button"
              onClick={() => handleSubmit(false)}
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>

        </div>
      </form>
    </div>
  );
}
