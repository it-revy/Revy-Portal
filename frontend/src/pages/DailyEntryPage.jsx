import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import HistoricalRecordCard from '../components/HistoricalRecordCard';
import {
  Calendar,
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  UserX,
  Plus,
  Trash2,
  DollarSign,
  Save,
  AlertCircle,
  FileCheck,
  Edit2,
  RefreshCw
} from 'lucide-react';

const DailyEntryPage = () => {
  const { hasPermission } = useAuth();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().substring(0, 10));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Section: Breakfast Items (Optional, starts empty or with saved items)
  const [breakfastItems, setBreakfastItems] = useState([]);

  // Section: Common Items (Optional, starts empty or with saved items)
  const [commonItems, setCommonItems] = useState([]);

  // Inline Actual Status Edit State for Applicable Employee Status List
  const [editingEmpId, setEditingEmpId] = useState(null);
  const [editingStatus, setEditingStatus] = useState('TAKEN');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    fetchDailyEntryData();
  }, [selectedDate]);

  const fetchDailyEntryData = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await API.get(`/breakfast/daily-entry?date=${selectedDate}`);
      if (res.data.success) {
        setData(res.data);
        const takingCount = res.data.summary?.takingCount || 0;

        if (res.data.existingEntry) {
          setBreakfastItems(res.data.existingEntry.breakfastItems || []);
          setCommonItems(res.data.existingEntry.commonItems || []);
        } else {
          // Default optional items initially empty or customizable by user
          setBreakfastItems([]);
          setCommonItems([]);
        }
      }
    } catch (err) {
      console.error('Failed to fetch daily entry data:', err);
      setMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to load daily entry data.' });
    } finally {
      setLoading(false);
    }
  };

  const handleActualStatusChange = async (employeeId, actualStatus) => {
    setUpdatingStatus(true);
    setMessage(null);
    try {
      const res = await API.put('/breakfast/actual-status', {
        employeeId,
        businessDate: selectedDate,
        actualStatus
      });
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setEditingEmpId(null);
        fetchDailyEntryData();
      }
    } catch (err) {
      setMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to update actual status' });
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Breakfast Item Handlers
  const addBreakfastItem = () => {
    const actualResponseQty = data?.summary?.actualResponseQuantity ?? data?.summary?.actualTakenCount ?? 0;
    setBreakfastItems([...breakfastItems, { name: '', unitPrice: 0, quantity: actualResponseQty }]);
  };

  const updateBreakfastItem = (index, field, value) => {
    const updated = [...breakfastItems];
    updated[index][field] = value;
    setBreakfastItems(updated);
  };

  const removeBreakfastItem = (index) => {
    setBreakfastItems(breakfastItems.filter((_, i) => i !== index));
  };

  // Common Item Handlers
  const addCommonItem = () => {
    setCommonItems([...commonItems, { name: '', unitPrice: 0, quantity: 1 }]);
  };

  const updateCommonItem = (index, field, value) => {
    const updated = [...commonItems];
    updated[index][field] = value;
    setCommonItems(updated);
  };

  const removeCommonItem = (index) => {
    setCommonItems(commonItems.filter((_, i) => i !== index));
  };

  // Quantities & Calculations
  const employeeRequestQuantity = data?.summary?.employeeRequestQuantity ?? data?.summary?.takingCount ?? 0;
  const actualResponseQuantity = data?.summary?.actualResponseQuantity ?? data?.summary?.actualTakenCount ?? 0;
  const totalQuantity = data?.summary?.totalQuantity ?? actualResponseQuantity;

  const itemsTotal = Number(breakfastItems.reduce((sum, item) => {
    if (!item.name || !item.name.trim()) return sum;
    const price = parseFloat(item.unitPrice) || 0;
    const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : actualResponseQuantity;
    return sum + (price * qty);
  }, 0).toFixed(2));

  const commonTotal = Number(commonItems.reduce((sum, item) => {
    if (!item.name || !item.name.trim()) return sum;
    const price = parseFloat(item.unitPrice) || 0;
    const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : 1;
    return sum + (price * qty);
  }, 0).toFixed(2));

  const grandTotal = Number((itemsTotal + commonTotal).toFixed(2));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);

    try {
      const res = await API.post('/breakfast/daily-entry', {
        businessDate: selectedDate,
        breakfastItems,
        commonItems,
        totalQuantity,
        actualResponseQuantity,
        employeeRequestQuantity
      });

      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        fetchDailyEntryData();
      }
    } catch (err) {
      setMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to save daily entry' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <RefreshCw size={32} color="var(--accent-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          <h3 style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading Daily Entry workstation...</h3>
        </div>
      </div>
    );
  }

  const summary = data?.summary || {};
  const isExisting = !!data?.existingEntry;
  const currentFundBalance = data?.fundMetrics?.currentBalance || 0;
  const balanceAfterEntry = currentFundBalance - grandTotal;
  const canEditActual = hasPermission('breakfast.manage');

  return (
    <div className="page-body">
      {/* Header & Date Selector */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.4rem' }}>
            <FileCheck color="var(--accent-primary)" /> Daily Entry Workstation
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.2rem', fontSize: '0.85rem' }}>
            Authoritative daily breakfast planning, employee request snapshot & cash entry
          </p>
        </div>

        <div className="panel-card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Calendar size={18} color="var(--accent-primary)" />
          <div>
            <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>BUSINESS DATE</label>
            <input
              type="date"
              className="form-input"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{ border: 'none', padding: 0, fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)', background: 'transparent' }}
            />
          </div>
        </div>
      </div>

      {data?.hasHistorical && data?.historicalRecords?.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge badge-historical" style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                HISTORICAL BREAKFAST RECORD
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                ({data.historicalRecords.length} historical {data.historicalRecords.length === 1 ? 'entry' : 'entries'} on {selectedDate})
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Employee Not Recorded • Preserved expense & quantity data
            </span>
          </div>
          {data.historicalRecords.map((hr, idx) => (
            <HistoricalRecordCard
              key={hr.id || hr.recordId || idx}
              record={hr}
              onRecordUpdated={fetchDailyEntryData}
            />
          ))}
        </div>
      )}

      {isExisting && (
        <div style={{
          background: 'var(--info-bg)',
          border: '1px solid #93c5fd',
          color: 'var(--info-text)',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
          fontSize: '0.85rem'
        }}>
          ℹ️ Daily Entry already exists for <strong>{selectedDate}</strong> (Saved by {data.existingEntry.createdBy}). Editing existing record.
        </div>
      )}

      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          border: `1px solid ${message.type === 'success' ? '#a7f3d0' : '#fca5a5'}`,
          color: message.type === 'success' ? 'var(--success-text)' : 'var(--danger-text)',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          {message.text}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid-metrics" style={{ marginBottom: '1.5rem' }}>
        <div className="glass-panel metric-card" style={{ padding: '1rem' }}>
          <div>
            <div className="metric-label">APPLICABLE EMPLOYEES</div>
            <div className="metric-val">{summary.applicableCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Excludes Perm & Leave</span>
          </div>
          <Users size={32} color="var(--accent-primary)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #3b82f6' }}>
          <div>
            <div className="metric-label">EMPLOYEE REQUEST QTY</div>
            <div className="metric-val" style={{ color: '#2563eb' }}>{employeeRequestQuantity}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Requested TAKING</span>
          </div>
          <CheckCircle2 size={32} color="#2563eb" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid var(--success)' }}>
          <div>
            <div className="metric-label">ACTUAL RESPONSE QTY</div>
            <div className="metric-val" style={{ color: 'var(--success)' }}>{actualResponseQuantity}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Actually Served / Taken</span>
          </div>
          <CheckCircle2 size={32} color="var(--success)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #059669', background: 'linear-gradient(135deg, rgba(5, 150, 105, 0.08) 0%, rgba(16, 185, 129, 0.02) 100%)' }}>
          <div>
            <div className="metric-label" style={{ fontWeight: 700, color: '#059669' }}>TOTAL QUANTITY</div>
            <div className="metric-val" style={{ color: '#059669', fontWeight: 800 }}>{totalQuantity}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Based on Actual Response</span>
          </div>
          <FileCheck size={32} color="#059669" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid var(--danger)' }}>
          <div>
            <div className="metric-label">NOT TAKING</div>
            <div className="metric-val" style={{ color: 'var(--danger)' }}>{summary.notTakingCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Opted out with reason</span>
          </div>
          <XCircle size={32} color="var(--danger)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid var(--warning)' }}>
          <div>
            <div className="metric-label">NO RESPONSE</div>
            <div className="metric-val" style={{ color: 'var(--warning)' }}>{summary.noResponseCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pending response</span>
          </div>
          <Clock size={32} color="var(--warning)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #64748b' }}>
          <div>
            <div className="metric-label">LEAVE EXCLUDED</div>
            <div className="metric-val" style={{ color: '#475569' }}>{summary.onLeave || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>On Leave (Excluded)</span>
          </div>
          <UserX size={32} color="#64748b" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1rem', borderLeft: '4px solid #475569' }}>
          <div>
            <div className="metric-label">PERMANENT NOT TAKING</div>
            <div className="metric-val" style={{ color: '#334155' }}>{summary.permanentNotTaking || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Permanent Non-Takers</span>
          </div>
          <UserX size={32} color="#475569" opacity={0.8} />
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Section: Applicable Employee Status List */}
        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={18} color="var(--accent-primary)" />
            Applicable Employee Status List ({data?.applicableEmployees?.length || 0})
          </h3>

          {/* Desktop Table View */}
          <div className="table-container desktop-only" style={{ maxHeight: '380px', overflowY: 'auto' }}>
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Employee Request</th>
                  <th>Actual Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {data?.applicableEmployees?.length === 0 ? (
                  <tr><td colSpan="5" style={{ textAlign: 'center', padding: '2rem' }}>No applicable employees for this date.</td></tr>
                ) : (
                  data.applicableEmployees.map(emp => (
                    <tr key={emp.employeeId}>
                      <td>
                        <strong>{emp.employeeName}</strong>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>{emp.employeeId}</span>
                      </td>
                      <td>{emp.department}</td>
                      <td>
                        <span className={`badge ${
                          emp.response === 'TAKING' ? 'badge-success' :
                          emp.response === 'NOT_TAKING' ? 'badge-danger' : 'badge-warning'
                        }`}>
                          {emp.response === 'TAKING' ? '✓ TAKING' :
                           emp.response === 'NOT_TAKING' ? '✕ NOT TAKING' : '⏳ NO RESPONSE'}
                        </span>
                      </td>
                      <td>
                        {editingEmpId === emp.employeeId ? (
                          <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                            <select
                              className="form-select"
                              value={editingStatus}
                              onChange={(e) => setEditingStatus(e.target.value)}
                              style={{ padding: '0.2rem 0.4rem', fontSize: '0.8rem', width: '130px' }}
                            >
                              <option value="TAKEN">TAKEN</option>
                              <option value="NOT_TAKEN">NOT_TAKEN</option>
                              <option value="NO_RESPONSE">NO_RESPONSE</option>
                            </select>
                            <button
                              type="button"
                              className="btn btn-primary"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                              disabled={updatingStatus}
                              onClick={() => handleActualStatusChange(emp.employeeId, editingStatus)}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              style={{ padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}
                              onClick={() => setEditingEmpId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <span className={`badge ${
                              emp.actualStatus === 'TAKEN' ? 'badge-success' :
                              emp.actualStatus === 'NOT_TAKEN' ? 'badge-danger' : 'badge-warning'
                            }`}>
                              {emp.actualStatus === 'TAKEN' ? 'TAKEN' :
                               emp.actualStatus === 'NOT_TAKEN' ? 'NOT_TAKEN' : 'NO_RESPONSE'}
                            </span>
                            {emp.actualStatusSource === 'ADMIN_OVERRIDE' && (
                              <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Override</span>
                            )}
                          </div>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {canEditActual && editingEmpId !== emp.employeeId && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => { setEditingEmpId(emp.employeeId); setEditingStatus(emp.actualStatus || 'TAKEN'); }}
                          >
                            <Edit2 size={13} /> Edit
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View (< 768px) */}
          <div className="mobile-only" style={{ flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
            {data?.applicableEmployees?.length === 0 ? (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>No applicable employees for this date.</div>
            ) : (
              data.applicableEmployees.map(emp => (
                <div key={emp.employeeId} className="glass-card" style={{ padding: '0.85rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div>
                      <strong style={{ fontSize: '0.95rem' }}>{emp.employeeName}</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>{emp.employeeId} • {emp.department}</span>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem', fontSize: '0.8rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.7rem' }}>REQUEST</span>
                      <span className={`badge ${
                        emp.response === 'TAKING' ? 'badge-success' :
                        emp.response === 'NOT_TAKING' ? 'badge-danger' : 'badge-warning'
                      }`}>
                        {emp.response}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.7rem' }}>ACTUAL</span>
                      <span className={`badge ${
                        emp.actualStatus === 'TAKEN' ? 'badge-success' :
                        emp.actualStatus === 'NOT_TAKEN' ? 'badge-danger' : 'badge-warning'
                      }`}>
                        {emp.actualStatus}
                      </span>
                    </div>
                  </div>

                  {canEditActual && (
                    <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                      <select
                        className="form-select"
                        value={emp.actualStatus || 'NO_RESPONSE'}
                        onChange={(e) => handleActualStatusChange(emp.employeeId, e.target.value)}
                        style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem', width: 'auto' }}
                      >
                        <option value="TAKEN">Set TAKEN</option>
                        <option value="NOT_TAKEN">Set NOT_TAKEN</option>
                        <option value="NO_RESPONSE">Set NO_RESPONSE</option>
                      </select>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Section: Breakfast Items (Optional) */}
        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <DollarSign size={18} color="var(--success)" />
                Breakfast Items <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Optional — Per Taking Employee)</span>
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Items calculated by Unit Price × Quantity (Default quantity: {actualResponseQuantity} actual response quantity served)
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={addBreakfastItem} style={{ fontSize: '0.8rem' }}>
              <Plus size={14} /> Add Item
            </button>
          </div>

          {breakfastItems.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', background: '#f8fafc', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--border-color)' }}>
              No breakfast items added yet. Click <strong>[ Add Item ]</strong> to add optional menu items.
            </div>
          ) : (
            breakfastItems.map((item, idx) => {
              const price = parseFloat(item.unitPrice) || 0;
              const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : actualResponseQuantity;
              const itemTotal = Number((price * qty).toFixed(2));

              return (
                <div key={idx} className="item-input-row">
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Item Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Thepla, Poha, Idli"
                      value={item.name}
                      onChange={(e) => updateBreakfastItem(idx, 'name', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Unit Price (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="any"
                      className="form-input"
                      value={item.unitPrice}
                      onChange={(e) => updateBreakfastItem(idx, 'unitPrice', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Quantity</label>
                    <input
                      type="number"
                      min="0"
                      step="any"
                      className="form-input"
                      placeholder={`${actualResponseQuantity}`}
                      value={item.quantity}
                      onChange={(e) => updateBreakfastItem(idx, 'quantity', e.target.value)}
                    />
                  </div>
                  <div className="item-total-col">
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Total (₹)</label>
                    <div style={{ padding: '0.55rem', background: '#ffffff', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', fontWeight: 700, color: 'var(--text-primary)', minHeight: '42px', display: 'flex', alignItems: 'center' }}>
                      ₹{itemTotal}
                    </div>
                  </div>
                  <div className="item-remove-cell">
                    <button type="button" className="btn btn-secondary" onClick={() => removeBreakfastItem(idx)} style={{ color: 'var(--danger)', padding: '0.55rem', minWidth: '42px' }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Section: Common / Shared Breakfast Items (Optional) */}
        <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Plus size={18} color="var(--accent-primary)" />
                Common / Shared Breakfast Items <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>(Optional — Group Expenses)</span>
              </h3>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Shared items (Fruits, Milk, Tea, Water) not tied to individual headcount
              </p>
            </div>
            <button type="button" className="btn btn-secondary" onClick={addCommonItem} style={{ fontSize: '0.8rem' }}>
              <Plus size={14} /> Add Common Item
            </button>
          </div>

          {commonItems.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', background: '#f8fafc', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--border-color)' }}>
              No common items added yet. Click <strong>[ Add Common Item ]</strong> to add shared group expenses.
            </div>
          ) : (
            commonItems.map((item, idx) => {
              const price = parseFloat(item.unitPrice) || 0;
              const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : 1;
              const itemTotal = Number((price * qty).toFixed(2));

              return (
                <div key={idx} className="item-input-row">
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Common Item Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Shared Fruits, Milk, Tea"
                      value={item.name}
                      onChange={(e) => updateCommonItem(idx, 'name', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Price (₹)</label>
                    <input
                      type="number"
                      min="0"
                      step="any"
                      className="form-input"
                      value={item.unitPrice}
                      onChange={(e) => updateCommonItem(idx, 'unitPrice', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Quantity</label>
                    <input
                      type="number"
                      min="0"
                      step="any"
                      className="form-input"
                      placeholder="1"
                      value={item.quantity}
                      onChange={(e) => updateCommonItem(idx, 'quantity', e.target.value)}
                    />
                  </div>
                  <div className="item-total-col">
                    <label className="form-label" style={{ fontSize: '0.75rem' }}>Total (₹)</label>
                    <div style={{ padding: '0.55rem', background: '#ffffff', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', fontWeight: 700, color: 'var(--text-primary)', minHeight: '42px', display: 'flex', alignItems: 'center' }}>
                      ₹{itemTotal}
                    </div>
                  </div>
                  <div className="item-remove-cell">
                    <button type="button" className="btn btn-secondary" onClick={() => removeCommonItem(idx)} style={{ color: 'var(--danger)', padding: '0.55rem', minWidth: '42px' }}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Section: Daily Entry Financial Summary */}
        <div className="panel-card" style={{ padding: '1.5rem', background: '#0f172a', color: 'white' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem' }}>
            <div>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                DAILY ENTRY FINANCIAL & QUANTITY SUMMARY ({selectedDate})
              </span>
              <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.5rem', fontSize: '0.9rem', flexWrap: 'wrap' }}>
                <div>Total Quantity: <strong style={{ color: '#38bdf8' }}>{totalQuantity}</strong> <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>(Actual)</span></div>
                <div style={{ borderLeft: '1px solid #334155', paddingLeft: '1rem' }}>
                  Request Quantity: <strong style={{ color: '#a5b4fc' }}>{employeeRequestQuantity}</strong>
                </div>
                <div style={{ borderLeft: '1px solid #334155', paddingLeft: '1rem' }}>
                  Breakfast Cost: <strong style={{ color: '#38bdf8' }}>₹{grandTotal}</strong>
                </div>
                <div style={{ borderLeft: '1px solid #334155', paddingLeft: '1rem' }}>
                  Current Fund Balance: <strong style={{ color: '#facc15' }}>₹{currentFundBalance.toLocaleString('en-IN')}</strong>
                </div>
                <div style={{ borderLeft: '1px solid #334155', paddingLeft: '1rem' }}>
                  Balance After Entry: <strong style={{ color: balanceAfterEntry >= 0 ? '#4ade80' : '#f87171' }}>
                    ₹{balanceAfterEntry.toLocaleString('en-IN')}
                  </strong>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>TOTAL QUANTITY: <strong style={{ color: '#38bdf8' }}>{totalQuantity}</strong></span>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'block' }}>DAILY ENTRY TOTAL</span>
                <span style={{ fontSize: '1.8rem', fontWeight: 800, color: '#4ade80' }}>₹{grandTotal}</span>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ padding: '0.85rem 1.75rem', fontSize: '1rem', background: '#2563eb' }}
                disabled={saving}
              >
                <Save size={18} />
                {saving ? 'Saving Daily Entry...' : isExisting ? 'Save Updated Daily Entry' : 'Save Daily Entry'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default DailyEntryPage;
