import React, { useState, useEffect, useRef } from 'react';
import {
  Building2,
  CreditCard,
  UserCheck,
  FileText,
  Save,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Plus,
  Trash2,
  ShieldAlert,
  Upload
} from 'lucide-react';
import { invoiceService } from '../../../services/invoiceService';
import { useAuth } from '../../../context/AuthContext';
import { PageHeader, Button } from '../../../components/ui';

export default function CompanyInvoiceConfigPage() {
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();
  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const isAdmin = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.settings.manage');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    companyName: 'REVY Environmental Solutions Pvt. Ltd.',
    registeredAddress: '',
    gstin: '',
    pan: '',
    contactEmail: '',
    contactPhone: '',
    website: '',
    logoUrl: '/images/logo.png',
    bankName: '',
    accountName: '',
    accountNumber: '',
    ifscCode: '',
    branch: '',
    swiftCode: '',
    upiId: '',
    signatoryName: '',
    signatoryTitle: '',
    signatureImageUrl: '',
    defaultTerms: [],
    defaultNotes: ''
  });

  const [termsText, setTermsText] = useState('');
  const [uploadingSig, setUploadingSig] = useState(false);
  const [sigError, setSigError] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await invoiceService.getCompanySettings();
      if (res.data) {
        const d = res.data;
        setFormData({
          companyName: d.companyName || '',
          registeredAddress: d.registeredAddress || '',
          gstin: d.gstin || '',
          pan: d.pan || '',
          contactEmail: d.contactEmail || '',
          contactPhone: d.contactPhone || '',
          website: d.website || '',
          logoUrl: d.logoUrl || '/images/logo.png',
          bankName: d.bankName || '',
          accountName: d.accountName || '',
          accountNumber: d.accountNumber || '',
          ifscCode: d.ifscCode || '',
          branch: d.branch || '',
          swiftCode: d.swiftCode || '',
          upiId: d.upiId || '',
          signatoryName: d.signatoryName || '',
          signatoryTitle: d.signatoryTitle || '',
          signatureImageUrl: d.signatureImageUrl || '',
          defaultTerms: d.defaultTerms || [],
          defaultNotes: d.defaultNotes || ''
        });
        setTermsText((d.defaultTerms || []).join('\n'));
      }
    } catch (err) {
      console.error('Failed to load company settings:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load company invoice settings.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignatureFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset input so re-selecting same file triggers onChange
    e.target.value = '';

    // Validate format: PNG, JPG, JPEG
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    const ext = file.name.split('.').pop()?.toLowerCase();
    const validExts = ['png', 'jpg', 'jpeg'];
    if (!validTypes.includes(file.type) && !validExts.includes(ext)) {
      setSigError('Invalid file type. Please upload a PNG, JPG, or JPEG signature image.');
      return;
    }

    // Validate size: 5MB max
    const maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
      setSigError('File size exceeds the 5MB limit. Please choose a smaller image.');
      return;
    }

    setUploadingSig(true);
    setSigError(null);
    try {
      const uploadData = new FormData();
      uploadData.append('file', file);
      const res = await invoiceService.uploadSignatureImage(uploadData);
      if (res.data) {
        setFormData(prev => ({
          ...prev,
          signatureImageUrl: res.data.signatureImageUrl
        }));
        setSuccessMsg('Authorised signature image uploaded successfully!');
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err) {
      console.error('Failed to upload signature image:', err);
      setSigError(err.response?.data?.detail || err.response?.data?.message || 'Failed to upload signature image.');
    } finally {
      setUploadingSig(false);
    }
  };

  const handleRemoveSignature = async () => {
    if (!window.confirm('Are you sure you want to remove the authorised signature image? Generated invoices will not contain a signature.')) {
      return;
    }

    setUploadingSig(true);
    setSigError(null);
    try {
      await invoiceService.deleteSignatureImage();
      setFormData(prev => ({
        ...prev,
        signatureImageUrl: ''
      }));
      setSuccessMsg('Signature image removed successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      console.error('Failed to delete signature image:', err);
      setSigError(err.response?.data?.detail || err.response?.data?.message || 'Failed to remove signature image.');
    } finally {
      setUploadingSig(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!isAdmin) {
      alert('You do not have permission to update company and invoice settings.');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      // Split terms text by newline into array of non-empty strings
      const termsList = termsText
        .split('\n')
        .map(t => t.trim())
        .filter(t => t.length > 0);

      const payload = {
        ...formData,
        defaultTerms: termsList
      };

      const res = await invoiceService.updateCompanySettings(payload);
      if (res.data) {
        setSuccessMsg('Company & Invoice Configuration updated successfully!');
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    } catch (err) {
      console.error('Failed to save company settings:', err);
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to update company settings.');
    } finally {
      setSaving(false);
    }
  };

  if (!isAdmin) {
    return (
      <div style={{ padding: '2.5rem', maxWidth: '700px', margin: '0 auto', textAlign: 'center' }}>
        <ShieldAlert size={48} color="#ef4444" style={{ margin: '0 auto 1rem' }} />
        <h2 style={{ fontSize: '1.3rem', color: '#f8fafc' }}>Access Restricted</h2>
        <p style={{ color: '#94a3b8' }}>
          Only CRM Administrators and IT Administrators have permission to manage Company & Invoice Configuration.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: '3.5rem', textAlign: 'center', color: '#94a3b8' }}>
        <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 0.75rem', opacity: 0.7 }} />
        <p>Loading company configuration...</p>
      </div>
    );
  }

  return (
    <div className="crm-page-container" style={{ padding: '1.5rem', maxWidth: '1000px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', margin: 0, display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Building2 size={26} color="#f59e0b" />
            Company & Invoice Configuration
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.85rem', margin: '4px 0 0' }}>
            Configure organization branding, bank credentials, signatory details, and default terms for Proforma Invoices.
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.45rem',
            backgroundColor: '#0284c7',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            padding: '0.6rem 1.25rem',
            fontSize: '0.88rem',
            fontWeight: 600,
            cursor: saving ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 10px rgba(2, 132, 199, 0.3)',
            opacity: saving ? 0.7 : 1
          }}
        >
          <Save size={16} />
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {successMsg && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid #10b981',
          borderRadius: '8px',
          color: '#a7f3d0',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.88rem'
        }}>
          <CheckCircle size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#fca5a5',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.88rem'
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {/* Section 1: Company Profile */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
            <Building2 size={20} color="#38bdf8" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Company Details & Tax Identifiers
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Company Name *</label>
              <input
                type="text"
                value={formData.companyName}
                onChange={e => handleChange('companyName', e.target.value)}
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>GSTIN *</label>
              <input
                type="text"
                value={formData.gstin}
                onChange={e => handleChange('gstin', e.target.value)}
                placeholder="24ABCDE1234F1Z5"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>PAN *</label>
              <input
                type="text"
                value={formData.pan}
                onChange={e => handleChange('pan', e.target.value)}
                placeholder="ABCDE1234F"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Contact Email</label>
              <input
                type="email"
                value={formData.contactEmail}
                onChange={e => handleChange('contactEmail', e.target.value)}
                placeholder="accounts@revy.co.in"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Contact Phone</label>
              <input
                type="text"
                value={formData.contactPhone}
                onChange={e => handleChange('contactPhone', e.target.value)}
                placeholder="+91-XXXXXXXXXX"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Website</label>
              <input
                type="text"
                value={formData.website}
                onChange={e => handleChange('website', e.target.value)}
                placeholder="https://revy.co.in"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Registered Office Address *</label>
              <textarea
                rows={2}
                value={formData.registeredAddress}
                onChange={e => handleChange('registeredAddress', e.target.value)}
                placeholder="Full official registered address"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>
          </div>
        </div>

        {/* Section 2: Bank Account Details */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
            <CreditCard size={20} color="#34d399" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Bank Account Details for Wire / NEFT
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Bank Name *</label>
              <input
                type="text"
                value={formData.bankName}
                onChange={e => handleChange('bankName', e.target.value)}
                placeholder="e.g. HDFC Bank"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Beneficiary / Account Name *</label>
              <input
                type="text"
                value={formData.accountName}
                onChange={e => handleChange('accountName', e.target.value)}
                placeholder="REVY Environmental Solutions Pvt. Ltd."
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Account Number *</label>
              <input
                type="text"
                value={formData.accountNumber}
                onChange={e => handleChange('accountNumber', e.target.value)}
                placeholder="502000XXXXXXX"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>IFSC Code *</label>
              <input
                type="text"
                value={formData.ifscCode}
                onChange={e => handleChange('ifscCode', e.target.value)}
                placeholder="HDFC000XXXX"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Branch Name</label>
              <input
                type="text"
                value={formData.branch}
                onChange={e => handleChange('branch', e.target.value)}
                placeholder="Vadodara Main Branch"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>UPI ID (Optional)</label>
              <input
                type="text"
                value={formData.upiId}
                onChange={e => handleChange('upiId', e.target.value)}
                placeholder="revy@upi"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>
          </div>
        </div>

        {/* Section 3: Authorised Signatory */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
            <UserCheck size={20} color="#f59e0b" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Authorised Signatory
            </h3>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Signatory Name *</label>
              <input
                type="text"
                value={formData.signatoryName}
                onChange={e => handleChange('signatoryName', e.target.value)}
                placeholder="e.g. Vanita Prasad / Authorised Signatory"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Designation / Title</label>
              <input
                type="text"
                value={formData.signatoryTitle}
                onChange={e => handleChange('signatoryTitle', e.target.value)}
                placeholder="Director / Authorized Representative"
                style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
              />
            </div>

            {/* Authorised Signature Upload Component */}
            <div style={{ gridColumn: '1 / -1', marginTop: '0.5rem', paddingTop: '1rem', borderTop: '1px solid #334155' }}>
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                style={{ display: 'none' }}
                onChange={handleSignatureFileSelect}
              />

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.6rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div>
                  <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f8fafc', display: 'block' }}>
                    Authorised Signature Image
                  </label>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    Supports PNG, JPG, or JPEG (max 5MB). Automatically applied to all generated Proforma Invoices.
                  </span>
                </div>

                {!formData.signatureImageUrl && (
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingSig}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      backgroundColor: '#0284c7',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '0.45rem 0.9rem',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      cursor: uploadingSig ? 'not-allowed' : 'pointer'
                    }}
                  >
                    <Upload size={15} />
                    <span>{uploadingSig ? 'Uploading...' : 'Upload Signature Image'}</span>
                  </button>
                )}
              </div>

              {sigError && (
                <div style={{
                  padding: '0.6rem 0.85rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  color: '#fca5a5',
                  marginBottom: '0.75rem',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <AlertCircle size={15} />
                  <span>{sigError}</span>
                </div>
              )}

              {formData.signatureImageUrl ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '1.25rem',
                  padding: '1rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  flexWrap: 'wrap'
                }}>
                  {/* Signature Preview Frame */}
                  <div style={{
                    backgroundColor: '#ffffff',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    border: '1px solid #e2e8f0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    minWidth: '180px',
                    minHeight: '70px',
                    maxWidth: '260px'
                  }}>
                    <img
                      src={formData.signatureImageUrl}
                      alt="Authorised Signatory Signature"
                      style={{ maxHeight: '65px', maxWidth: '100%', objectFit: 'contain', display: 'block' }}
                      onError={(e) => {
                        e.target.style.display = 'none';
                        const parent = e.target.parentElement;
                        if (parent && !parent.querySelector('.sig-fallback-text')) {
                          const fallback = document.createElement('span');
                          fallback.className = 'sig-fallback-text';
                          fallback.innerText = 'Preview Unavailable';
                          fallback.style.color = '#64748b';
                          fallback.style.fontSize = '0.75rem';
                          parent.appendChild(fallback);
                        }
                      }}
                    />
                  </div>

                  {/* Actions & Status */}
                  <div style={{ flex: 1, minWidth: '220px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#34d399', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                      <CheckCircle size={15} />
                      <span>Signature active on Proforma Invoices</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                      Signatory: {formData.signatoryName || 'Authorised Signatory'} ({formData.signatoryTitle || 'Designation'})
                    </p>

                    <div style={{ display: 'flex', gap: '0.6rem' }}>
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploadingSig}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          backgroundColor: '#334155',
                          color: '#f8fafc',
                          border: '1px solid #475569',
                          borderRadius: '5px',
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.78rem',
                          fontWeight: 500,
                          cursor: uploadingSig ? 'not-allowed' : 'pointer'
                        }}
                      >
                        <Upload size={14} />
                        <span>{uploadingSig ? 'Uploading...' : 'Replace Image'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={handleRemoveSignature}
                        disabled={uploadingSig}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          backgroundColor: 'rgba(239, 68, 68, 0.15)',
                          color: '#fca5a5',
                          border: '1px solid #ef4444',
                          borderRadius: '5px',
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.78rem',
                          fontWeight: 500,
                          cursor: uploadingSig ? 'not-allowed' : 'pointer'
                        }}
                      >
                        <Trash2 size={14} />
                        <span>Remove Image</span>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{
                  padding: '1.5rem',
                  border: '1px dashed #475569',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(15, 23, 42, 0.5)',
                  textAlign: 'center',
                  color: '#94a3b8'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.5rem' }}>
                    <div style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '50%',
                      backgroundColor: '#334155',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Upload size={20} color="#94a3b8" />
                    </div>
                  </div>
                  <h4 style={{ margin: '0 0 0.25rem', color: '#f1f5f9', fontSize: '0.9rem', fontWeight: 600 }}>
                    No Signature Image Uploaded
                  </h4>
                  <p style={{ margin: '0 0 1rem', fontSize: '0.78rem', color: '#64748b', maxWidth: '420px', marginInline: 'auto' }}>
                    No signature is currently configured. Proforma Invoices will generate with a blank signature block.
                  </p>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadingSig}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      backgroundColor: '#0284c7',
                      color: 'white',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '0.5rem 1rem',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      cursor: uploadingSig ? 'not-allowed' : 'pointer'
                    }}
                  >
                    <Upload size={15} />
                    <span>{uploadingSig ? 'Uploading...' : 'Upload Signature Image'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 4: Default Invoice Terms and Conditions */}
        <div style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '1.25rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
            <FileText size={20} color="#a855f7" />
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Default Terms & Conditions (One per line)
            </h3>
          </div>

          <div>
            <textarea
              rows={5}
              value={termsText}
              onChange={e => setTermsText(e.target.value)}
              placeholder="Enter each default term on a new line..."
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#0f172a',
                border: '1px solid #475569',
                borderRadius: '6px',
                color: 'white',
                fontSize: '0.85rem',
                lineHeight: 1.5,
                fontFamily: 'inherit'
              }}
            />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '4px', display: 'block' }}>
              These terms will automatically populate on newly generated Proforma Invoices and Quotations.
            </span>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8' }}>Default Footer Note</label>
            <input
              type="text"
              value={formData.defaultNotes}
              onChange={e => handleChange('defaultNotes', e.target.value)}
              placeholder="This is a computer generated document and valid without stamp."
              style={{ width: '100%', marginTop: '4px', padding: '0.5rem', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '6px', color: 'white', fontSize: '0.85rem' }}
            />
          </div>
        </div>

        {/* Submit */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
          <button
            type="submit"
            disabled={saving}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backgroundColor: '#0284c7',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '0.75rem 1.75rem',
              fontSize: '0.92rem',
              fontWeight: 700,
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1
            }}
          >
            <Save size={18} />
            {saving ? 'Saving Changes...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
}
