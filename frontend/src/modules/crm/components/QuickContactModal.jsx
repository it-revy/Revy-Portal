import React, { useState, useEffect } from 'react';
import { User, AlertCircle, Building, Mail, Phone, Briefcase } from 'lucide-react';
import crmService from '../../../services/crmService';

export default function QuickContactModal({
  isOpen,
  onClose,
  onContactCreated,
  defaultAccountId = null,
  defaultAccountName = null
}) {
  const [formData, setFormData] = useState({
    name: '',
    designation: '',
    email: '',
    mobileNumber: '',
    accountId: defaultAccountId || ''
  });
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const fetchAccounts = async () => {
    try {
      const res = await crmService.getAccounts({ limit: 100 });
      if (res.data.success) {
        setAccounts(res.data.accounts || []);
      }
    } catch {
      // Non-critical fallback
    }
  };

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);

    setFormData({
      name: '',
      designation: '',
      email: '',
      mobileNumber: '',
      accountId: defaultAccountId || ''
    });
    setError(null);
    setFieldErrors({});
    if (!defaultAccountId) {
      fetchAccounts();
    }

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, defaultAccountId]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (error) setError(null);
    if (fieldErrors[name]) {
      setFieldErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const validate = () => {
    const errors = {};
    if (!formData.name.trim()) {
      errors.name = 'Contact name is required.';
    }

    if (formData.email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email.trim())) {
        errors.email = 'Enter a valid email address.';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (loading) return;
    if (!validate()) return;

    setLoading(true);
    setError(null);

    let res = null;
    let createFailed = false;

    try {
      res = await crmService.createContact({
        name: formData.name.trim(),
        designation: formData.designation.trim() || undefined,
        email: formData.email.trim() || undefined,
        mobileNumber: formData.mobileNumber.trim() || undefined,
        accountId: formData.accountId || undefined
      });
    } catch (err) {
      createFailed = true;
      if (err.response?.status === 409) {
        setError(err.response.data?.message || 'A contact with this email or mobile number already exists.');
      } else if (err.response?.status === 401 || err.response?.status === 403) {
        setError(err.response.data?.message || 'Permission denied. You cannot create contacts.');
      } else if (err.response?.status >= 500) {
        setError('A server error occurred while creating the contact. Please try again or contact support.');
      } else if (err.message === 'Network Error' || err.code === 'ERR_NETWORK') {
        setError('Network error. Unable to reach the server. Please try again.');
      } else {
        setError(err.response?.data?.message || err.message || 'Failed to create contact. Please verify inputs.');
      }
    } finally {
      setLoading(false);
    }

    if (createFailed) return;

    if (res && res.data?.success && res.data?.contact) {
      const newContact = res.data.contact;
      if (typeof onClose === 'function') {
        try {
          onClose();
        } catch (closeErr) {
          console.error('Error closing QuickContactModal:', closeErr);
        }
      }
      if (typeof onContactCreated === 'function') {
        try {
          onContactCreated(newContact);
        } catch (cbErr) {
          console.error('Error in onContactCreated callback:', cbErr);
        }
      }
    } else {
      setError('Unexpected server response. Please try again.');
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={onClose}>
      <div
        className="modal-content"
        style={{ maxWidth: '520px', width: '92%', borderRadius: '12px', overflow: 'hidden' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header" style={{ padding: '1.1rem 1.25rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: '#fef3c7',
              color: '#d97706',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>Quick Create Contact</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Add a new client stakeholder or technical contact
              </span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.25rem' }}>
            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: '8px',
                color: '#b91c1c',
                fontSize: '0.875rem'
              }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 600 }}>
                Full Name <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                type="text"
                name="name"
                className={`form-control ${fieldErrors.name ? 'is-invalid' : ''}`}
                placeholder="e.g. Dr. Ramesh Verma"
                value={formData.name}
                onChange={handleChange}
                autoFocus
                required
              />
              {fieldErrors.name && (
                <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  {fieldErrors.name}
                </div>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 500 }}>
                Associated Company / Account <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
              </label>
              {defaultAccountId && defaultAccountName ? (
                <div style={{
                  padding: '0.65rem 0.85rem',
                  background: '#f1f5f9',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  color: '#334155',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <Building size={15} color="var(--accent-primary)" />
                  <strong>{defaultAccountName}</strong>
                </div>
              ) : (
                <select
                  name="accountId"
                  className="form-control"
                  value={formData.accountId}
                  onChange={handleChange}
                >
                  <option value="">-- No Account (Independent Contact) --</option>
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.accountId})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 500 }}>
                Designation / Role <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
              </label>
              <input
                type="text"
                name="designation"
                className="form-control"
                placeholder="e.g. Technical Director / Plant Head"
                value={formData.designation}
                onChange={handleChange}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Mail size={13} color="var(--text-muted)" />
                  <span>Email</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
                </label>
                <input
                  type="email"
                  name="email"
                  className={`form-control ${fieldErrors.email ? 'is-invalid' : ''}`}
                  placeholder="ramesh@company.com"
                  value={formData.email}
                  onChange={handleChange}
                />
                {fieldErrors.email && (
                  <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                    {fieldErrors.email}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Phone size={13} color="var(--text-muted)" />
                  <span>Mobile</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
                </label>
                <input
                  type="text"
                  name="mobileNumber"
                  className="form-control"
                  placeholder="+91 9876543210"
                  value={formData.mobileNumber}
                  onChange={handleChange}
                />
              </div>
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating Contact...' : 'Create Contact'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
