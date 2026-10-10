import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Utensils,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  History,
  CalendarRange,
  Edit3,
  Calendar,
  Trash2,
  PlusCircle,
  HelpCircle,
  Info
} from 'lucide-react';
import { formatISTTimestamp, formatISTTime } from '../utils/dateUtils';

const EmployeeDailyPage = () => {
  const { user } = useAuth();
  const [activeSubTab, setActiveSubTab] = useState('SINGLE_DAY');
  const [statusData, setStatusData] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [editingMode, setEditingMode] = useState(false);

  // Single Day Form State (for normal participants)
  const [response, setResponse] = useState('YES');
  const [reasonCode, setReasonCode] = useState('');
  const [reasonText, setReasonText] = useState('');

  // Multi-Day Absence Form State (for normal participants)
  const [fromDate, setFromDate] = useState(new Date().toISOString().substring(0, 10));
  const [toDate, setToDate] = useState(new Date().toISOString().substring(0, 10));
  const [multiReasonCode, setMultiReasonCode] = useState('ON_LEAVE');
  const [multiReasonText, setMultiReasonText] = useState('');

  // Permanent Non-Taker Specific-Date Request State
  const [tempRequests, setTempRequests] = useState([]);
  const [tempDate, setTempDate] = useState(new Date().toISOString().substring(0, 10));
  const [tempQuantity, setTempQuantity] = useState(1.0);
  const [tempNotes, setTempNotes] = useState('');
  const [editingTempReq, setEditingTempReq] = useState(null);
  const [tempSubmitting, setTempSubmitting] = useState(false);

  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchTodayStatus();
    fetchHistory();
    fetchTemporaryRequests();
  }, []);

  const fetchTodayStatus = async () => {
    try {
      const res = await API.get('/breakfast/today');
      if (res.data.success) {
        setStatusData(res.data);
        if (res.data.businessDate) {
          setTempDate(res.data.businessDate);
        }
        if (res.data.todayRecord) {
          setResponse(res.data.todayRecord.response === 'NO' ? 'NO' : 'YES');
          setReasonCode(res.data.todayRecord.reasonCode || '');
          setReasonText(res.data.todayRecord.reasonText || '');
        } else {
          setResponse('YES');
          setReasonCode('');
          setReasonText('');
          setEditingMode(false);
        }
      }
    } catch (err) {
      console.error('Failed to fetch status:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await API.get('/breakfast/history');
      if (res.data.success) {
        setHistory(res.data.records);
      }
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  };

  const fetchTemporaryRequests = async () => {
    try {
      const res = await API.get('/breakfast/temporary-requests');
      if (res.data.success) {
        setTempRequests(res.data.requests || []);
      }
    } catch (err) {
      console.error('Failed to fetch temporary requests:', err);
    }
  };

  const handleSingleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);

    if (response === 'NO') {
      if (!reasonCode) {
        setMessage({ type: 'danger', text: 'Please select a reason for not taking breakfast.' });
        return;
      }
      if (reasonCode === 'OTHER' && !reasonText.trim()) {
        setMessage({ type: 'danger', text: 'Please specify the reason text when "Other" is selected.' });
        return;
      }
    }

    setSubmitting(true);
    try {
      const res = await API.post('/breakfast/submit', {
        businessDate: statusData?.targetDate || statusData?.businessDate,
        response,
        reasonCode: response === 'NO' ? reasonCode : null,
        reasonText: response === 'NO' ? reasonText : null
      });

      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setEditingMode(false);
        fetchTodayStatus();
        fetchHistory();
        fetchTemporaryRequests();
      }
    } catch (err) {
      setMessage({
        type: 'danger',
        text: err.response?.data?.message || 'Failed to submit status.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleMultiSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);

    if (fromDate > toDate) {
      setMessage({ type: 'danger', text: 'From Date must be before or equal to To Date.' });
      return;
    }

    if (multiReasonCode === 'OTHER' && !multiReasonText.trim()) {
      setMessage({ type: 'danger', text: 'Please specify reason text when "Other" is selected.' });
      return;
    }

    setSubmitting(true);
    try {
      const res = await API.post('/breakfast/multi-day-absence', {
        fromDate,
        toDate,
        reasonCode: multiReasonCode,
        reasonText: multiReasonText
      });

      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        fetchTodayStatus();
        fetchHistory();
      }
    } catch (err) {
      setMessage({
        type: 'danger',
        text: err.response?.data?.message || 'Failed to submit multi-day absence.'
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Specific-Date Request for Permanent Non-Takers
  const handleTemporaryRequestSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);

    const qty = parseFloat(tempQuantity);
    if (isNaN(qty) || qty <= 0) {
      setMessage({ type: 'danger', text: 'Please specify a valid quantity greater than 0.' });
      return;
    }

    if (!tempDate) {
      setMessage({ type: 'danger', text: 'Please select a date for the breakfast request.' });
      return;
    }

    // Check duplicate if not editing existing
    if (!editingTempReq) {
      const existing = tempRequests.find(r => r.requestedDate === tempDate && r.status !== 'CANCELLED');
      if (existing) {
        setMessage({
          type: 'danger',
          text: `A breakfast request already exists for date ${tempDate} (${existing.quantity} portions). You can edit or cancel that request below instead of creating a duplicate.`
        });
        return;
      }
    }

    setTempSubmitting(true);
    try {
      if (editingTempReq) {
        const res = await API.put(`/breakfast/temporary-requests/${editingTempReq.requestId}`, {
          quantity: qty,
          notes: tempNotes
        });
        if (res.data.success) {
          setMessage({ type: 'success', text: res.data.message || 'Request updated successfully' });
          setEditingTempReq(null);
          setTempNotes('');
          fetchTemporaryRequests();
          fetchTodayStatus();
          fetchHistory();
        }
      } else {
        const res = await API.post('/breakfast/temporary-request', {
          requestedDate: tempDate,
          quantity: qty,
          notes: tempNotes
        });
        if (res.data.success) {
          setMessage({ type: 'success', text: res.data.message || 'Specific-date request submitted successfully' });
          setTempNotes('');
          fetchTemporaryRequests();
          fetchTodayStatus();
          fetchHistory();
        }
      }
    } catch (err) {
      setMessage({
        type: 'danger',
        text: err.response?.data?.message || 'Failed to submit specific-date request.'
      });
    } finally {
      setTempSubmitting(false);
    }
  };

  const handleStartEditTempReq = (req) => {
    setEditingTempReq(req);
    setTempDate(req.requestedDate);
    setTempQuantity(req.quantity);
    setTempNotes(req.notes || '');
    window.scrollTo({ top: 300, behavior: 'smooth' });
  };

  const handleCancelEditingTempReq = () => {
    setEditingTempReq(null);
    setTempNotes('');
    setTempQuantity(1.0);
    if (statusData?.businessDate) {
      setTempDate(statusData.businessDate);
    }
  };

  const handleCancelTempRequest = async (requestId, reqDate) => {
    if (!window.confirm(`Are you sure you want to cancel your breakfast request for ${reqDate}?`)) {
      return;
    }
    try {
      const res = await API.delete(`/breakfast/temporary-requests/${requestId}`);
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message || 'Request cancelled successfully' });
        if (editingTempReq && editingTempReq.requestId === requestId) {
          handleCancelEditingTempReq();
        }
        fetchTemporaryRequests();
        fetchTodayStatus();
        fetchHistory();
      }
    } catch (err) {
      setMessage({
        type: 'danger',
        text: err.response?.data?.message || 'Failed to cancel request.'
      });
    }
  };

  if (loading) {
    return <div className="page-body">Loading today's status...</div>;
  }

  const isPerm = ['PERMANENT_NOT_TAKING', 'PERMANENT_NON_TAKER', 'NON_TAKER'].includes((statusData?.participationType || '').toUpperCase());
  const hasExistingResponse = !!statusData?.todayRecord;
  const existingReqForSelectedDate = tempRequests.find(r => r.requestedDate === tempDate && r.status !== 'CANCELLED');
  const todayTempReq = tempRequests.find(r => r.requestedDate === statusData?.businessDate && r.status !== 'CANCELLED');

  return (
    <div className="page-body">
      {/* Header Greeting */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Utensils size={24} color="var(--accent-primary)" /> My Breakfast Response
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', fontSize: '0.85rem' }}>
            Logged in as: <strong>{user?.name}</strong> ({user?.employeeId})
          </p>
        </div>
      </div>

      {/* Breakfast Request Window Banner (Section 10 Requirement) */}
      <div className="panel-card" style={{
        padding: '1.25rem 1.5rem',
        marginBottom: '1.5rem',
        borderLeft: `5px solid ${statusData?.isWindowOpen ? 'var(--success)' : 'var(--danger)'}`,
        background: statusData?.isWindowOpen ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Breakfast Request – {statusData?.targetDateFormatted || statusData?.businessDate}
            </div>

            {statusData?.isWindowOpen ? (
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.2rem' }}>Request Window:</div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.95rem' }}>
                  {statusData?.windowStartDisplay}
                  <br />
                  to
                  <br />
                  {statusData?.windowEndDisplay}
                </div>
              </div>
            ) : (
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                <div style={{ fontWeight: 700, color: 'var(--danger-text)', marginBottom: '0.25rem' }}>
                  Request Window Closed
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  Requests were accepted from:
                  <div style={{ fontFamily: 'monospace', marginTop: '0.2rem' }}>
                    {statusData?.windowStartDisplay}
                    <br />
                    to
                    <br />
                    {statusData?.windowEndDisplay}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
              Status:
            </div>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              padding: '0.45rem 1rem',
              borderRadius: '9999px',
              fontWeight: 800,
              fontSize: '0.9rem',
              background: statusData?.isWindowOpen ? '#10b981' : '#ef4444',
              color: '#ffffff',
              letterSpacing: '0.05em'
            }}>
              <Clock size={16} /> {statusData?.windowStatus || (statusData?.isWindowOpen ? 'OPEN' : 'CLOSED')}
            </span>
          </div>
        </div>
      </div>

      {statusData?.isPublicHoliday && (
        <div style={{
          background: 'var(--info-bg)',
          border: '1px solid #93c5fd',
          color: 'var(--info-text)',
          padding: '0.85rem 1.25rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem'
        }}>
          <CalendarRange size={20} color="var(--info)" />
          <div>
            <strong style={{ fontSize: '0.9rem', display: 'block' }}>Public Holiday ({statusData.holidayName})</strong>
            <span style={{ fontSize: '0.8rem' }}>Daily response is not required today.</span>
          </div>
        </div>
      )}

      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          border: `1px solid ${message.type === 'success' ? '#a7f3d0' : '#fca5a5'}`,
          color: message.type === 'success' ? 'var(--success-text)' : 'var(--danger-text)',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem'
        }}>
          {message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
          {message.text}
        </div>
      )}

      {/* ===================== PERMANENT NON-TAKER VIEW ===================== */}
      {isPerm ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Permanent Non-Taker Profile Notice Card */}
          <div className="panel-card" style={{ padding: '1.5rem', borderLeft: '4px solid var(--warning)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
                  <AlertTriangle size={20} color="var(--warning)" />
                  <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Permanent Non-Breakfast Participant</h3>
                  <span className="badge badge-warning" style={{ fontSize: '0.75rem' }}>
                    Permanent Non-Taker
                  </span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', margin: 0, maxWidth: '700px' }}>
                  Your employee profile is permanently set to <strong>Non-Taker</strong>. You are normally excluded from regular breakfast catering. However, you can submit a <strong>one-day request for any specific date</strong> when you wish to have breakfast. Your permanent Non-Taker status remains unchanged.
                </p>
              </div>

              {todayTempReq && (
                <div style={{
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  <CheckCircle2 size={18} color="#10b981" />
                  <div>
                    <span style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 600, display: 'block' }}>TODAY'S ONE-DAY REQUEST</span>
                    <strong style={{ color: '#065f46', fontSize: '0.85rem' }}>
                      {todayTempReq.quantity} Portion{todayTempReq.quantity !== 1 ? 's' : ''} Confirmed
                    </strong>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* One-Day Request Form Card */}
          <div className="panel-card" style={{ padding: '1.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                  <Calendar size={20} color="var(--accent-primary)" />
                  {editingTempReq ? `Edit Request for ${editingTempReq.requestedDate}` : 'Request Breakfast for a Specific Date'}
                </h2>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem', margin: 0 }}>
                  Submitting this request will include you in the breakfast count <strong>for this specific date only</strong>.
                </p>
              </div>
              {editingTempReq && (
                <button className="btn btn-secondary" onClick={handleCancelEditingTempReq} style={{ fontSize: '0.8rem' }}>
                  Cancel Edit
                </button>
              )}
            </div>

            {/* Warning if request already exists for selected date (when not editing) */}
            {!editingTempReq && existingReqForSelectedDate && (
              <div style={{
                background: 'rgba(59, 130, 246, 0.1)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                padding: '0.85rem 1rem',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '1.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.75rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Info size={18} color="#2563eb" />
                  <div>
                    <strong style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                      Request Already Active for {tempDate}
                    </strong>
                    <span style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Status: <strong>{existingReqForSelectedDate.status}</strong> • Quantity: <strong>{existingReqForSelectedDate.quantity} portion(s)</strong>
                      {existingReqForSelectedDate.notes ? ` • Note: ${existingReqForSelectedDate.notes}` : ''}
                    </span>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                    onClick={() => handleStartEditTempReq(existingReqForSelectedDate)}
                  >
                    <Edit3 size={13} /> Edit Quantity
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem', color: 'var(--danger-text)' }}
                    onClick={() => handleCancelTempRequest(existingReqForSelectedDate.requestId, existingReqForSelectedDate.requestedDate)}
                  >
                    <Trash2 size={13} /> Cancel
                  </button>
                </div>
              </div>
            )}

            <form onSubmit={handleTemporaryRequestSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Requested Date *
                  </label>
                  <input
                    type="date"
                    className="form-input"
                    value={tempDate}
                    onChange={(e) => setTempDate(e.target.value)}
                    disabled={!!editingTempReq}
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                    Select the exact date you need breakfast
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Quantity (Portions) *
                  </label>
                  <input
                    type="number"
                    step="any"
                    min="0.1"
                    max="100.0"
                    className="form-input"
                    value={tempQuantity}
                    onChange={(e) => setTempQuantity(e.target.value)}
                    required
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                    Supports decimal values (e.g. 0.5, 1, 1.5, 2.25, 10.75)
                  </span>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label className="form-label">
                  Reason / Notes (Optional)
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Early client meeting, Team training breakfast, Celebration"
                  value={tempNotes}
                  onChange={(e) => setTempNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={tempSubmitting || (!editingTempReq && !!existingReqForSelectedDate)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <PlusCircle size={16} />
                  {tempSubmitting
                    ? 'Processing...'
                    : editingTempReq
                    ? 'Save Updated Quantity'
                    : 'Submit Specific-Date Request'}
                </button>
                {editingTempReq && (
                  <button type="button" className="btn btn-secondary" onClick={handleCancelEditingTempReq}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>

          {/* Specific-Date Requests History Table */}
          <div className="panel-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontSize: '1.05rem', margin: '0 0 1rem 0' }}>
              <CalendarRange size={18} color="var(--accent-primary)" />
              My Specific-Date Breakfast Requests
            </h3>

            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Requested Date</th>
                    <th>Quantity</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Notes</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {tempRequests.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                        No specific-date breakfast requests submitted yet. Use the form above to request breakfast for a chosen date.
                      </td>
                    </tr>
                  ) : (
                    tempRequests.map(req => {
                      const isConfirmed = req.status === 'CONFIRMED';
                      return (
                        <tr key={req.requestId || req.id}>
                          <td>
                            <strong style={{ color: 'var(--text-primary)' }}>{req.requestedDate}</strong>
                          </td>
                          <td>
                            <span className="badge badge-secondary" style={{ fontWeight: 600 }}>
                              {req.quantity} {req.quantity === 1 ? 'Portion' : 'Portions'}
                            </span>
                          </td>
                          <td>
                            <span className={`badge ${isConfirmed ? 'badge-success' : 'badge-danger'}`}>
                              {req.status}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                              {req.createdAt ? new Date(req.createdAt).toLocaleDateString() : '—'}
                            </span>
                          </td>
                          <td>
                            <span style={{ fontSize: '0.85rem' }}>
                              {req.notes || '—'}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            {isConfirmed ? (
                              <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => handleStartEditTempReq(req)}
                                  title="Edit Quantity / Notes"
                                >
                                  <Edit3 size={13} /> Edit
                                </button>
                                <button
                                  className="btn btn-secondary"
                                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--danger-text)' }}
                                  onClick={() => handleCancelTempRequest(req.requestId, req.requestedDate)}
                                  title="Cancel Request"
                                >
                                  <Trash2 size={13} /> Cancel
                                </button>
                              </div>
                            ) : (
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Cancelled</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* ===================== REGULAR TAKER VIEW ===================== */
        <div className="panel-card" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Sub Tab Switcher */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.6rem', flexWrap: 'wrap' }}>
            <button
              className={`btn ${activeSubTab === 'SINGLE_DAY' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveSubTab('SINGLE_DAY')}
              style={{ fontSize: '0.8rem' }}
            >
              <Utensils size={15} /> Today's Response
            </button>
            <button
              className={`btn ${activeSubTab === 'MULTI_DAY' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveSubTab('MULTI_DAY')}
              style={{ fontSize: '0.8rem' }}
            >
              <CalendarRange size={15} /> Planned Non-Breakfast Period
            </button>
          </div>

          {activeSubTab === 'SINGLE_DAY' ? (
            <div>
              {/* If response exists and not editing mode, show clean status display */}
              {hasExistingResponse && !editingMode ? (
                <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>TODAY'S SUBMITTED STATUS</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginTop: '0.35rem', flexWrap: 'wrap' }}>
                        <span className={`badge ${statusData.todayRecord.response === 'YES' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '0.9rem', padding: '0.35rem 0.75rem' }}>
                          {statusData.todayRecord.response === 'YES' ? '✓ TAKING BREAKFAST' : '✕ NOT TAKING'}
                        </span>
                        {statusData.todayRecord.response === 'NO' && (
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            Reason: <strong>{statusData.todayRecord.reasonText || statusData.todayRecord.reasonCode}</strong>
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        Submitted at: {formatISTTimestamp(statusData.todayRecord.submittedAt)} IST
                      </div>
                    </div>

                    {statusData?.isWindowOpen && (
                      <button className="btn btn-secondary" onClick={() => setEditingMode(true)} style={{ fontSize: '0.8rem' }}>
                        <Edit3 size={14} /> Change Response
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                /* YES / NO Submission Form */
                <div>
                  {!statusData?.isWindowOpen ? (
                    <div style={{ background: 'var(--danger-bg)', color: 'var(--danger-text)', padding: '1.25rem', borderRadius: 'var(--radius-sm)', fontSize: '0.875rem' }}>
                      <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>Request Window Closed</div>
                      <div>
                        Requests for {statusData?.targetDateFormatted || statusData?.businessDate} were accepted from {statusData?.windowStartDisplay} to {statusData?.windowEndDisplay}.
                      </div>
                    </div>
                  ) : (
                    <form onSubmit={handleSingleSubmit}>
                      <div style={{ marginBottom: '1.25rem' }}>
                        <label className="form-label" style={{ marginBottom: '0.6rem', display: 'block' }}>
                          Will you take breakfast on {statusData?.targetDateFormatted || statusData?.businessDate}?
                        </label>
                        <div className="form-grid-2">
                          <button
                            type="button"
                            className={`btn ${response === 'YES' ? 'btn-success' : 'btn-secondary'}`}
                            style={{ padding: '0.85rem', fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                            onClick={() => setResponse('YES')}
                          >
                            <CheckCircle2 size={20} />
                            Taking Breakfast
                          </button>
                          <button
                            type="button"
                            className={`btn ${response === 'NO' ? 'btn-danger' : 'btn-secondary'}`}
                            style={{ padding: '0.85rem', fontSize: '1rem', fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                            onClick={() => setResponse('NO')}
                          >
                            <XCircle size={20} />
                            Not Taking Breakfast
                          </button>
                        </div>
                      </div>

                      {/* Progressive Disclosure: Reason selector when NO is chosen */}
                      {response === 'NO' && (
                        <div className="glass-card" style={{ marginBottom: '1.25rem', background: '#f8fafc' }}>
                          <div className="form-group">
                            <label className="form-label">Why are you not taking breakfast? *</label>
                            <select
                              className="form-select"
                              value={reasonCode}
                              onChange={(e) => setReasonCode(e.target.value)}
                              required
                            >
                              <option value="">-- Choose Reason --</option>
                              {statusData?.reasons?.map(r => (
                                <option key={r.code} value={r.code}>{r.label}</option>
                              ))}
                            </select>
                          </div>

                          {reasonCode === 'OTHER' && (
                            <div className="form-group" style={{ marginTop: '0.75rem' }}>
                              <label className="form-label">Please specify the reason * (Mandatory Text)</label>
                              <input
                                type="text"
                                className="form-input"
                                placeholder="Enter specific reason..."
                                value={reasonText}
                                onChange={(e) => setReasonText(e.target.value)}
                                required
                              />
                            </div>
                          )}
                        </div>
                      )}

                      <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <button
                          type="submit"
                          className="btn btn-primary"
                          disabled={submitting}
                        >
                          {submitting ? 'Saving...' : hasExistingResponse ? 'Save Updated Answer' : 'Submit Response'}
                        </button>
                        {editingMode && (
                          <button type="button" className="btn btn-secondary" onClick={() => setEditingMode(false)}>
                            Cancel
                          </button>
                        )}
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* Multi-Day Planned Absence */
            <div>
              <h3 style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>Planned Non-Breakfast Period</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '1rem' }}>
                Specify planned non-participation dates (e.g. Leave, Business Travel, Personal Absence).
              </p>

              <form onSubmit={handleMultiSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">From Date *</label>
                    <input
                      type="date"
                      className="form-input"
                      value={fromDate}
                      onChange={(e) => setFromDate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">To Date *</label>
                    <input
                      type="date"
                      className="form-input"
                      value={toDate}
                      onChange={(e) => setToDate(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Reason for Absence *</label>
                  <select
                    className="form-select"
                    value={multiReasonCode}
                    onChange={(e) => setMultiReasonCode(e.target.value)}
                    required
                  >
                    {statusData?.reasons?.map(r => (
                      <option key={r.code} value={r.code}>{r.label}</option>
                    ))}
                  </select>
                </div>

                {multiReasonCode === 'OTHER' && (
                  <div className="form-group" style={{ marginBottom: '1rem' }}>
                    <label className="form-label">Please specify the reason * (Mandatory)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Provide details..."
                      value={multiReasonText}
                      onChange={(e) => setMultiReasonText(e.target.value)}
                      required
                    />
                  </div>
                )}

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submitting}
                >
                  {submitting ? 'Saving Period...' : 'Save Planned Non-Breakfast Period'}
                </button>
              </form>
            </div>
          )}
        </div>
      )}

      {/* History Table */}
      <div className="panel-card" style={{ padding: '1.5rem' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem', fontSize: '1rem' }}>
          <History size={16} color="var(--accent-primary)" />
          Recent Breakfast Response History
        </h3>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Business Date</th>
                <th>Requested Response</th>
                <th>Actual Status</th>
                <th>Reason / Description</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem' }}>
                    No submission history found.
                  </td>
                </tr>
              ) : (
                history.map(rec => (
                  <tr key={rec._id || rec.id}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{rec.businessDate}</strong></td>
                    <td>
                      <span className={`badge ${rec.response === 'YES' ? 'badge-success' : 'badge-danger'}`}>
                        {rec.response === 'YES' ? '✓ TAKING' : '✕ NOT TAKING'}
                      </span>
                    </td>
                    <td>
                      {rec.actualStatus ? (
                        <span className={`badge ${rec.actualStatus === 'TAKEN' ? 'badge-success' : 'badge-warning'}`}>
                          {rec.actualStatus}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
                      )}
                    </td>
                    <td>{rec.response === 'YES' ? '—' : rec.reasonText || rec.reasonCode}</td>
                    <td><span className="badge badge-secondary">{rec.source || 'EMPLOYEE'}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default EmployeeDailyPage;
