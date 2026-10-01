import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import API from '../services/api';
import {
  Calendar,
  UserX,
  Coffee,
  DollarSign,
  CreditCard,
  Save,
  AlertCircle,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';

const HistoricalRecordEditModal = ({ isOpen, onClose, record, onSaved }) => {
  const [formData, setFormData] = useState({
    date: '',
    snack: '',
    snackQuantity: '',
    snackCost: 0,
    fruit: '',
    fruitQuantity: '',
    fruitCost: 0,
    totalCost: 0,
    paidBy: '',
    paymentType: ''
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (record) {
      setFormData({
        date: record.date || record.businessDate || '',
        snack: record.snack || '',
        snackQuantity: record.snackQuantity ?? record.snack_quantity ?? '',
        snackCost: record.snackCost ?? record.snack_cost ?? 0,
        fruit: record.fruit || '',
        fruitQuantity: record.fruitQuantity ?? record.fruit_quantity ?? '',
        fruitCost: record.fruitCost ?? record.fruit_cost ?? 0,
        totalCost: record.totalCost ?? record.total_cost ?? 0,
        paidBy: record.paidBy ?? record.paid_by ?? '',
        paymentType: record.paymentType ?? record.payment_type ?? ''
      });
      setError(null);
      setSuccess(null);
    }
  }, [record, isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => {
      const next = { ...prev, [field]: value };
      // If user edits snackCost or fruitCost, auto-update totalCost if total was matching sum
      if (field === 'snackCost' || field === 'fruitCost') {
        const sc = field === 'snackCost' ? Number(value) || 0 : Number(prev.snackCost) || 0;
        const fc = field === 'fruitCost' ? Number(value) || 0 : Number(prev.fruitCost) || 0;
        next.totalCost = sc + fc;
      }
      return next;
    });
  };

  const handleRecalculateTotal = () => {
    const sc = Number(formData.snackCost) || 0;
    const fc = Number(formData.fruitCost) || 0;
    setFormData(prev => ({ ...prev, totalCost: sc + fc }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!record) return;

    setSaving(true);
    setError(null);
    setSuccess(null);

    const targetId = record.id || record.recordId || record.sourceId;

    try {
      const payload = {
        date: formData.date,
        snack: formData.snack,
        snackQuantity: formData.snackQuantity,
        snackCost: Number(formData.snackCost) || 0,
        fruit: formData.fruit,
        fruitQuantity: formData.fruitQuantity,
        fruitCost: Number(formData.fruitCost) || 0,
        totalCost: Number(formData.totalCost) || 0,
        paidBy: formData.paidBy,
        paymentType: formData.paymentType
      };

      const res = await API.put(`/breakfast/records/${targetId}`, payload);
      if (res.data.success) {
        setSuccess('Historical record updated successfully!');
        if (onSaved) {
          onSaved(res.data.record);
        }
        setTimeout(() => {
          onClose();
        }, 800);
      } else {
        throw new Error(res.data.message || 'Failed to update historical record');
      }
    } catch (err) {
      console.error('Failed to update historical record:', err);
      setError(err.response?.data?.message || err.message || 'Failed to update record');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Edit Historical Breakfast Record"
    >
      <form onSubmit={handleSubmit} style={{ padding: '0.25rem' }}>
        {/* Header Historical Badge & Employee Notice */}
        <div style={{
          background: '#f5f3ff',
          border: '1px solid #ddd6fe',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          marginBottom: '1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge badge-historical">HISTORICAL</span>
              <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', color: '#6d28d9', fontWeight: 700 }}>
                {record?.recordId || record?.sourceId || 'ID: Historical'}
              </span>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#4b5563', marginTop: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <UserX size={15} color="#7c3aed" />
              <span>Employee: <strong>Not Recorded</strong> (Historical data without individual consumer tracking)</span>
            </div>
          </div>
        </div>

        {error && (
          <div style={{
            background: 'var(--danger-bg)',
            border: '1px solid var(--danger-border)',
            color: 'var(--danger-text)',
            padding: '0.75rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {success && (
          <div style={{
            background: 'var(--success-bg)',
            border: '1px solid var(--success-border)',
            color: 'var(--success-text)',
            padding: '0.75rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <CheckCircle2 size={16} /> {success}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.25rem' }}>
          {/* Business Date */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.8rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Calendar size={14} color="var(--accent-primary)" /> Record Date
            </label>
            <input
              type="date"
              className="form-input"
              value={formData.date}
              onChange={(e) => handleChange('date', e.target.value)}
              required
            />
          </div>

          {/* Snack Section */}
          <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <Coffee size={16} color="var(--accent-primary)" />
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>Snack Details</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Snack Item</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Dalwada, Thepla, Khaman"
                  value={formData.snack}
                  onChange={(e) => handleChange('snack', e.target.value)}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Quantity (Text/Unit)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. 400GM, 1kg, 5pkt"
                  value={formData.snackQuantity}
                  onChange={(e) => handleChange('snackQuantity', e.target.value)}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Snack Cost (₹)</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="form-input"
                  value={formData.snackCost}
                  onChange={(e) => handleChange('snackCost', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Fruit Section */}
          <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <span style={{ fontSize: '1rem' }}>🍎</span>
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>Fruit Details</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Fruit Item</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Mango, Banana, Apple"
                  value={formData.fruit}
                  onChange={(e) => handleChange('fruit', e.target.value)}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Quantity (Text/Unit)</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. 1kg, 500GM, 4plt"
                  value={formData.fruitQuantity}
                  onChange={(e) => handleChange('fruitQuantity', e.target.value)}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Fruit Cost (₹)</label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="form-input"
                  value={formData.fruitCost}
                  onChange={(e) => handleChange('fruitCost', e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Payment & Financial Info */}
          <div style={{ background: '#f8fafc', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <CreditCard size={16} color="var(--success)" />
              <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>Financial & Payment Information</strong>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '0.75rem', alignItems: 'end' }}>
              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Paid By</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Faiz, Company Cash"
                  value={formData.paidBy}
                  onChange={(e) => handleChange('paidBy', e.target.value)}
                />
              </div>

              <div>
                <label className="form-label" style={{ fontSize: '0.75rem' }}>Payment Type</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. GPay, Cash, UPI"
                  value={formData.paymentType}
                  onChange={(e) => handleChange('paymentType', e.target.value)}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                  <label className="form-label" style={{ fontSize: '0.75rem', margin: 0 }}>Total Cost (₹)</label>
                  <button
                    type="button"
                    onClick={handleRecalculateTotal}
                    style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  >
                    Auto-sum
                  </button>
                </div>
                <input
                  type="number"
                  min="0"
                  step="any"
                  className="form-input"
                  style={{ fontWeight: 700, color: '#16a34a' }}
                  value={formData.totalCost}
                  onChange={(e) => handleChange('totalCost', e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Modal Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={saving}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            {saving ? <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Save size={15} />}
            {saving ? 'Saving...' : 'Save Historical Record'}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default HistoricalRecordEditModal;
