import React, { useState, useEffect } from 'react';
import API from '../services/api';
import Drawer from '../components/Drawer';
import { useAuth } from '../context/AuthContext';
import HistoricalRecordCard from '../components/HistoricalRecordCard';
import { Utensils, CheckCircle2, XCircle, Search, Eye, History, Shield, Edit2, AlertCircle } from 'lucide-react';

const TodayBreakfastListPage = () => {
  const { hasPermission } = useAuth();
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().substring(0, 10));
  const [department, setDepartment] = useState('ALL');
  const [search, setSearch] = useState('');
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);

  // Drawer state for inspecting employee details & history
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [empHistory, setEmpHistory] = useState([]);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Quick edit status state
  const [editingEmpId, setEditingEmpId] = useState(null);
  const [editingStatus, setEditingStatus] = useState('TAKEN');
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState(null);
  const [dayStatus, setDayStatus] = useState(null);
  const [historicalRecords, setHistoricalRecords] = useState([]);
  const [hasHistorical, setHasHistorical] = useState(false);

  useEffect(() => {
    fetchList();
  }, [selectedDate, department]);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await API.get(`/breakfast/admin/records?date=${selectedDate}&department=${department}&search=${search}`);
      if (res.data.success) {
        setList(res.data.allList || []);
        setDayStatus(res.data.dayStatus || null);
        setHistoricalRecords(res.data.historicalRecords || []);
        setHasHistorical(!!res.data.hasHistorical);
      }
    } catch (err) {
      console.error('Failed to fetch list:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkActualStatus = async (employeeId, actualStatus) => {
    setUpdating(true);
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
        fetchList();
      }
    } catch (err) {
      setMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to update actual status' });
    } finally {
      setUpdating(false);
    }
  };

  const handleOpenDrawer = async (emp) => {
    setSelectedEmp(emp);
    setDrawerOpen(true);
    try {
      const res = await API.get(`/employees/${emp.employeeId}`);
      if (res.data.success) {
        setEmpHistory(res.data.recentRecords || []);
      }
    } catch (err) {
      console.error('Failed to fetch employee history drawer data');
    }
  };

  const canEdit = hasPermission('breakfast.manage');

  return (
    <div className="page-body">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Utensils color="var(--accent-primary)" /> Today's Operational Breakfast List
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.2rem', fontSize: '0.85rem' }}>
            Verify employee requested requirements vs. actual consumption control
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Business Date:</span>
          <input
            type="date"
            className="form-input"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{ width: 'auto', minWidth: '140px', padding: '0.45rem 0.75rem' }}
          />
        </div>
      </div>

      {dayStatus && (dayStatus.isSunday || dayStatus.isPublicHoliday) && (
        <div style={{
          background: dayStatus.isPublicHoliday ? '#fef3c7' : '#f1f5f9',
          border: `1px solid ${dayStatus.isPublicHoliday ? '#f59e0b' : '#cbd5e1'}`,
          color: dayStatus.isPublicHoliday ? '#92400e' : '#475569',
          padding: '0.85rem 1.25rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          fontWeight: 600
        }}>
          <AlertCircle size={20} color={dayStatus.isPublicHoliday ? '#d97706' : '#64748b'} />
          <div>
            {dayStatus.isPublicHoliday ? (
              <span>PUBLIC HOLIDAY: {dayStatus.publicHolidayName} — Employees are not required to submit breakfast responses.</span>
            ) : (
              <span>NON-WORKING DAY (Sunday) — Automatically excluded from expected breakfast responses.</span>
            )}
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

      {hasHistorical && historicalRecords.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge badge-historical" style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}>
                HISTORICAL BREAKFAST RECORD
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                ({historicalRecords.length} historical record{historicalRecords.length > 1 ? 's' : ''} for {selectedDate})
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Employee Not Recorded • Stored expense & quantity data
            </span>
          </div>
          {historicalRecords.map((hr, idx) => (
            <HistoricalRecordCard
              key={hr.id || hr.recordId || idx}
              record={hr}
              onRecordUpdated={fetchList}
            />
          ))}
        </div>
      )}

      {/* Filter Bar */}
      <div className="panel-card" style={{ padding: '1rem', marginBottom: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <form onSubmit={(e) => { e.preventDefault(); fetchList(); }} style={{ flex: '1 1 240px', display: 'flex', gap: '0.5rem', minWidth: '200px' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search employee by Username, Name, Employee ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary">
            <Search size={15} /> Search
          </button>
        </form>

        <select
          className="form-select"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          style={{ width: 'auto', minWidth: '150px', flex: '1 1 auto' }}
        >
          <option value="ALL">All Departments</option>
          <option value="IT Infrastructure">IT Infrastructure</option>
          <option value="Administration">Administration</option>
          <option value="Engineering">Engineering</option>
          <option value="Research & Development">Research & Development</option>
          <option value="Executive Office">Executive Office</option>
        </select>
      </div>

      {/* Table */}
      <div className="panel-card" style={{ padding: '1.25rem' }}>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Employee ID</th>
                <th>Username</th>
                <th>Employee Name</th>
                <th>Department</th>
                <th>Employee Request</th>
                <th>Reason / Description</th>
                <th>Actual Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '2.5rem' }}>Loading list...</td></tr>
              ) : list.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>No employee records found.</td></tr>
              ) : (
                list.map(emp => (
                  <tr key={emp.employeeId}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{emp.employeeId}</strong></td>
                    <td><span className="badge badge-secondary" style={{ fontFamily: 'monospace' }}>{emp.username || '—'}</span></td>
                    <td><strong>{emp.name}</strong></td>
                    <td>
                      <div>{emp.department}</div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{emp.designation}</span>
                    </td>
                    <td>
                      <span className={`badge ${
                        emp.employeeResponse === 'TAKING' ? 'badge-success' :
                        emp.employeeResponse === 'NOT_TAKING' ? 'badge-danger' : 'badge-warning'
                      }`}>
                        {emp.employeeResponse === 'TAKING' ? '✓ TAKING' :
                         emp.employeeResponse === 'NOT_TAKING' ? '✕ NOT TAKING' : '⏳ NO RESPONSE'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{emp.reasonText || emp.reasonCode || '—'}</td>
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
                            className="btn btn-primary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            disabled={updating}
                            onClick={() => handleMarkActualStatus(emp.employeeId, editingStatus)}
                          >
                            Save
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.4rem', fontSize: '0.75rem' }}
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
                      <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'flex-end' }}>
                        {canEdit && editingEmpId !== emp.employeeId && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.3rem 0.55rem', fontSize: '0.75rem' }}
                            onClick={() => { setEditingEmpId(emp.employeeId); setEditingStatus(emp.actualStatus || 'TAKEN'); }}
                            title="Edit Actual Status"
                          >
                            <Edit2 size={13} /> Edit Actual
                          </button>
                        )}
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.3rem 0.55rem', fontSize: '0.75rem' }}
                          onClick={() => handleOpenDrawer(emp)}
                          title="Quick Details Drawer"
                        >
                          <Eye size={13} /> Details
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Side Drawer for Quick Inspection */}
      <Drawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={`Employee Profile & History (${selectedEmp?.employeeId})`}
      >
        {selectedEmp && (
          <div>
            <div className="glass-card" style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>{selectedEmp.name}</h3>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {selectedEmp.department} • {selectedEmp.designation}
              </div>
              <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <span className="badge badge-role">Request: {selectedEmp.employeeResponse}</span>
                <span className="badge badge-success">Actual: {selectedEmp.actualStatus}</span>
                {selectedEmp.actualStatusSource && (
                  <span className="badge badge-info">Source: {selectedEmp.actualStatusSource}</span>
                )}
              </div>
            </div>

            <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <History size={16} color="var(--accent-primary)" /> Recent 30-Day Breakfast History
            </h4>

            <div className="table-container">
              <table className="custom-table" style={{ fontSize: '0.8rem' }}>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Request</th>
                    <th>Actual</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {empHistory.length === 0 ? (
                    <tr><td colSpan="4" style={{ textAlign: 'center', padding: '1rem' }}>No history records.</td></tr>
                  ) : (
                    empHistory.map(h => (
                      <tr key={h._id}>
                        <td>{h.businessDate}</td>
                        <td>
                          <span className={`badge ${h.response === 'YES' || h.employeeResponse === 'TAKING' ? 'badge-success' : 'badge-danger'}`}>
                            {h.employeeResponse || h.response}
                          </span>
                        </td>
                        <td>{h.actualStatus || '—'}</td>
                        <td style={{ fontSize: '0.7rem' }}>{h.actualStatusSource || 'EMPLOYEE_RESPONSE'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default TodayBreakfastListPage;
