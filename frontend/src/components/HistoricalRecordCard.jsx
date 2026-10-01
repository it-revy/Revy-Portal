import React, { useState } from 'react';
import { Calendar, UserX, Coffee, CreditCard, Edit2, DollarSign, History } from 'lucide-react';
import HistoricalRecordEditModal from './HistoricalRecordEditModal';

const HistoricalRecordCard = ({ record, onRecordUpdated }) => {
  const [isEditing, setIsEditing] = useState(false);

  if (!record) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const snackName = record.snack || record.items?.find(i => i.itemType === 'SNACK')?.name || 'None Recorded';
  const snackQty = record.snackQuantity ?? record.snack_quantity ?? record.items?.find(i => i.itemType === 'SNACK')?.quantity ?? '-';
  const snackCost = record.snackCost ?? record.snack_cost ?? record.items?.find(i => i.itemType === 'SNACK')?.total ?? 0;

  const fruitName = record.fruit || record.items?.find(i => i.itemType === 'FRUIT')?.name || 'None Recorded';
  const fruitQty = record.fruitQuantity ?? record.fruit_quantity ?? record.items?.find(i => i.itemType === 'FRUIT')?.quantity ?? '-';
  const fruitCost = record.fruitCost ?? record.fruit_cost ?? record.items?.find(i => i.itemType === 'FRUIT')?.total ?? 0;

  const totalCost = record.totalCost ?? record.total_cost ?? (snackCost + fruitCost);
  const paidBy = record.paidBy ?? record.paid_by ?? 'Not Specified';
  const paymentType = record.paymentType ?? record.payment_type ?? 'Not Specified';
  const dateStr = record.date || record.businessDate || '';

  return (
    <>
      <div className="glass-panel" style={{
        padding: '1.25rem',
        borderLeft: '5px solid #7c3aed',
        background: '#ffffff',
        boxShadow: '0 4px 12px rgba(124, 58, 237, 0.08)',
        marginBottom: '1rem'
      }}>
        {/* Top Header: Date, HISTORICAL Badge & Edit Button */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatDate(dateStr)}
              </span>
              <span className="badge badge-historical">
                HISTORICAL
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.35rem', fontSize: '0.85rem', color: '#6b7280' }}>
              <UserX size={15} color="#7c3aed" />
              <span>Employee: <strong style={{ color: 'var(--text-primary)' }}>Not Recorded</strong></span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {record.sourceId && (
              <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                {record.sourceId}
              </span>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setIsEditing(true)}
              style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Edit2 size={13} /> Edit Historical Record
            </button>
          </div>
        </div>

        {/* Breakdown Grid matching Section 6 Requirements */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
          {/* Snack Info */}
          <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--accent-primary)', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.4rem' }}>
              <Coffee size={14} /> SNACK
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
              {snackName}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Quantity: <strong>{snackQty}</strong>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#16a34a', fontWeight: 600, marginTop: '0.25rem' }}>
              Cost: ₹{snackCost}
            </div>
          </div>

          {/* Fruit Info */}
          <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ea580c', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.4rem' }}>
              <span>🍎</span> FRUIT
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>
              {fruitName}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Quantity: <strong>{fruitQty}</strong>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#16a34a', fontWeight: 600, marginTop: '0.25rem' }}>
              Cost: ₹{fruitCost}
            </div>
          </div>

          {/* Payment & Total Info */}
          <div style={{ background: '#faf5ff', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid #e9d5ff' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#7c3aed', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.4rem' }}>
              <CreditCard size={14} /> EXPENSE & PAYMENT
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Cost:</span>
              <strong style={{ fontSize: '1.15rem', color: '#16a34a' }}>₹{totalCost.toLocaleString('en-IN')}</strong>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Paid By: <strong>{paidBy}</strong>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Payment Type: <strong>{paymentType}</strong>
            </div>
          </div>
        </div>
      </div>

      {isEditing && (
        <HistoricalRecordEditModal
          isOpen={isEditing}
          onClose={() => setIsEditing(false)}
          record={record}
          onSaved={(updated) => {
            setIsEditing(false);
            if (onRecordUpdated) onRecordUpdated(updated);
          }}
        />
      )}
    </>
  );
};

export default HistoricalRecordCard;
