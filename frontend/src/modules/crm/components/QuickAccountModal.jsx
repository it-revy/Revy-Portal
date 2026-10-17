import React, { useState, useEffect } from 'react';
import { Building, AlertCircle, Globe } from 'lucide-react';
import crmService from '../../../services/crmService';

const DOMAIN_REGEX = /^(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(?::\d+)?(?:\/[^\s]*)?$/i;

export default function QuickAccountModal({ isOpen, onClose, onAccountCreated }) {
  const [formData, setFormData] = useState({
    name: '',
    industry: '',
    website: '',
    phone: '',
    email: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

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
      industry: '',
      website: '',
      phone: '',
      email: ''
    });
    setError(null);
    setFieldErrors({});

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

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
      errors.name = 'Company / Account name is required.';
    }

    if (formData.website.trim()) {
      const site = formData.website.trim();
      const lower = site.toLowerCase();
      if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) {
        errors.website = 'Unsafe web protocols are not allowed.';
      } else if (!DOMAIN_REGEX.test(site)) {
        errors.website = 'Enter a valid domain or website URL (e.g. renergydynamics.com).';
      }
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
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError(null);

    try {
      const cleanWebsite = formData.website.trim() || undefined;
      const res = await crmService.createAccount({
        name: formData.name.trim(),
        industry: formData.industry.trim() || undefined,
        website: cleanWebsite,
        phone: formData.phone.trim() || undefined,
        email: formData.email.trim() || undefined
      });

      if (res.data.success && res.data.account) {
        onAccountCreated(res.data.account);
        onClose();
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
      if (err.response?.status === 409) {
        setError(err.response.data?.message || 'An account with this name already exists.');
      } else if (err.response?.data?.details) {
        // Map backend validation field errors if available
        setError(err.response.data?.message || 'Validation error while saving account.');
      } else {
        setError(err.response?.data?.message || 'Failed to create account. Please check inputs.');
      }
    } finally {
      setLoading(false);
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
              background: '#e0f2fe',
              color: '#0284c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Building size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>Quick Create Account</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Register a new company entity for CRM enquiries
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
                Company / Account Name <span style={{ color: 'var(--danger)' }}>*</span>
              </label>
              <input
                type="text"
                name="name"
                className={`form-control ${fieldErrors.name ? 'is-invalid' : ''}`}
                placeholder="e.g. Acme Biogas Solutions Ltd"
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
                Industry / Sector <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
              </label>
              <input
                type="text"
                name="industry"
                className="form-control"
                placeholder="e.g. Renewable Energy / Waste Treatment"
                value={formData.industry}
                onChange={handleChange}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500 }}>
                  Phone <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
                </label>
                <input
                  type="text"
                  name="phone"
                  className="form-control"
                  placeholder="+91 9876543210"
                  value={formData.phone}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label" style={{ fontWeight: 500 }}>
                  Email <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
                </label>
                <input
                  type="email"
                  name="email"
                  className={`form-control ${fieldErrors.email ? 'is-invalid' : ''}`}
                  placeholder="contact@company.com"
                  value={formData.email}
                  onChange={handleChange}
                />
                {fieldErrors.email && (
                  <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                    {fieldErrors.email}
                  </div>
                )}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Globe size={14} color="var(--text-muted)" />
                <span>Website / Domain</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>(Optional)</span>
              </label>
              <input
                type="text"
                name="website"
                className={`form-control ${fieldErrors.website ? 'is-invalid' : ''}`}
                placeholder="renergydynamics.com"
                value={formData.website}
                onChange={handleChange}
              />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: 'block' }}>
                Accepts bare domain (e.g. renergydynamics.com) without requiring https://
              </span>
              {fieldErrors.website && (
                <div style={{ color: '#dc2626', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  {fieldErrors.website}
                </div>
              )}
            </div>
          </div>

          <div className="modal-footer" style={{ padding: '0.9rem 1.25rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
