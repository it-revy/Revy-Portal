import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import { CalendarRange, Plus, Trash2, ShieldAlert } from 'lucide-react';

import { PageHeader, Button } from '../components/ui';

const PublicHolidaysPage = () => {
  const [holidays, setHolidays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({ date: '', name: '' });

  const { hasRole } = useAuth();

  useEffect(() => {
    fetchHolidays();
  }, []);

  const fetchHolidays = async () => {
    try {
      const res = await API.get('/holidays');
      if (res.data.success) {
        setHolidays(res.data.holidays);
      }
    } catch (err) {
      console.error('Failed to fetch holidays:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddHoliday = async (e) => {
    e.preventDefault();
    try {
      const res = await API.post('/holidays', formData);
      if (res.data.success) {
        setShowModal(false);
        setFormData({ date: '', name: '' });
        fetchHolidays();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to add holiday');
    }
  };

  const handleDeleteHoliday = async (holidayId) => {
    if (!window.confirm(`Delete public holiday ${holidayId}?`)) return;
    try {
      const res = await API.delete(`/holidays/${holidayId}`);
      if (res.data.success) {
        fetchHolidays();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to delete holiday');
    }
  };

  return (
    <div className="page-body">
      <PageHeader
        title="Public Holidays Management"
        subtitle="Days marked as public holidays automatically bypass daily breakfast requirements"
        icon={CalendarRange}
        actions={
          hasRole('IT_ADMIN') && (
            <Button
              variant="primary"
              onClick={() => setShowModal(true)}
              icon={Plus}
            >
              Add Public Holiday
            </Button>
          )
        }
      />

      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Holiday ID</th>
                <th>Holiday Date</th>
                <th>Holiday Name</th>
                <th>Status</th>
                <th>Created By</th>
                {hasRole('IT_ADMIN') && <th style={{ textAlign: 'right' }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '2rem' }}>Loading holidays...</td></tr>
              ) : holidays.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '2rem' }}>No public holidays configured.</td></tr>
              ) : (
                holidays.map(h => (
                  <tr key={h.holidayId}>
                    <td><span style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>{h.holidayId}</span></td>
                    <td>
                      <strong style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                        {h.date}
                      </strong>
                    </td>
                    <td><strong>{h.name}</strong></td>
                    <td><span className="badge badge-success">{h.status}</span></td>
                    <td style={{ color: 'var(--text-secondary)' }}>{h.createdBy}</td>
                    {hasRole('IT_ADMIN') && (
                      <td style={{ textAlign: 'right' }}>
                        <button className="btn btn-secondary" style={{ color: 'var(--danger)', padding: '0.35rem 0.6rem' }} onClick={() => handleDeleteHoliday(h.holidayId)}>
                          <Trash2 size={15} /> Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Add Public Holiday (IT_ADMIN)</h2>
            <form onSubmit={handleAddHoliday} style={{ marginTop: '1.25rem' }}>
              <div className="form-group">
                <label className="form-label">Holiday Date *</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Holiday Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Christmas or Republic Day"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Holiday</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PublicHolidaysPage;
