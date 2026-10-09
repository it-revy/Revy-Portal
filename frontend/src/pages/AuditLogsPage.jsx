import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { ShieldAlert, Search, Eye, X, UserCheck } from 'lucide-react';

const AuditLogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('ALL');

  const [selectedLog, setSelectedLog] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const formatIstDateTime = (val) => {
    if (!val) return '—';
    const str = typeof val === 'string' && !val.endsWith('Z') && !val.includes('+') && !val.includes('-')
      ? `${val}Z`
      : val;
    const d = new Date(str);
    if (isNaN(d.getTime())) return String(val);
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    }).format(d) + ' IST';
  };

  useEffect(() => {
    fetchLogs();
  }, [actionFilter]);

  const fetchLogs = async () => {
    try {
      const res = await API.get(`/audit-logs?search=${search}&action=${actionFilter}`);
      if (res.data.success) {
        setLogs(res.data.logs);
      }
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchLogs();
  };

  const openLogDetails = (log) => {
    setSelectedLog(log);
    setShowModal(true);
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: 0 }}>
            <ShieldAlert color="var(--accent-primary)" /> Platform Audit Trail & History
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', fontSize: '0.875rem' }}>
            Accountability records identifying actual user name, role used, and state changes
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <form onSubmit={handleSearchSubmit} style={{ flex: '1 1 240px', display: 'flex', gap: '0.5rem', minWidth: '200px' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search by Employee ID, Name, Action, or Audit ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary" style={{ whiteSpace: 'nowrap' }}>
            <Search size={16} /> Search
          </button>
        </form>

        <select
          className="form-select"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          style={{ flex: '1 1 200px', minWidth: '160px' }}
        >
          <option value="ALL">All Actions</option>
          <option value="EMPLOYEE_CREATED">EMPLOYEE_CREATED</option>
          <option value="EMPLOYEE_UPDATED">EMPLOYEE_UPDATED</option>
          <option value="EMPLOYEE_DEACTIVATED">EMPLOYEE_DEACTIVATED</option>
          <option value="PARTICIPATION_TYPE_CHANGED">PARTICIPATION_TYPE_CHANGED</option>
          <option value="EMPLOYEE_ROLES_UPDATED">EMPLOYEE_ROLES_UPDATED</option>
          <option value="BREAKFAST_RESPONSE_SUBMITTED">BREAKFAST_RESPONSE_SUBMITTED</option>
          <option value="BREAKFAST_RESPONSE_UPDATED">BREAKFAST_RESPONSE_UPDATED</option>
          <option value="BREAKFAST_SETTINGS_UPDATED">BREAKFAST_SETTINGS_UPDATED</option>
        </select>
      </div>

      {/* Audit Log Table */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Performed By (Name & ID)</th>
                <th>Role Used</th>
                <th>Action</th>
                <th>Target</th>
                <th>Timestamp</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>Loading audit logs...</td></tr>
              ) : logs.length === 0 ? (
                <tr><td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>No audit records found.</td></tr>
              ) : (
                logs.map(log => (
                  <tr key={log.auditId}>
                    <td><span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{log.auditId}</span></td>
                    <td>
                      <div><strong style={{ color: 'white' }}>{log.performedBy?.employeeName}</strong></div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{log.performedBy?.employeeId}</span>
                    </td>
                    <td>
                      <span className="badge badge-role">
                        {log.performedBy?.roleUsed?.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-info" style={{ textTransform: 'none' }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>
                      {log.target?.targetEmployeeName ? `${log.target.targetEmployeeName} (${log.target.targetEmployeeId})` : log.target?.details || '—'}
                    </td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      {log.timestampDisplay || formatIstDateTime(log.timestamp)}
                    </td>
                    <td>
                      <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem' }} onClick={() => openLogDetails(log)}>
                        <Eye size={15} /> View State
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Diff / State Viewer Modal */}
      {showModal && selectedLog && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '650px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2>Audit Log Details ({selectedLog.auditId})</h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div style={{ marginBottom: '1rem', background: '#f8fafc', border: '1px solid var(--border-color)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
              <div><strong>Action:</strong> {selectedLog.action}</div>
              <div><strong>Performed By:</strong> {selectedLog.performedBy?.employeeName} ({selectedLog.performedBy?.employeeId})</div>
              <div><strong>Role Used:</strong> {selectedLog.performedBy?.roleUsed}</div>
              <div><strong>Timestamp (IST):</strong> {selectedLog.timestampDisplay || formatIstDateTime(selectedLog.timestamp)}</div>
            </div>

            <div className="form-grid-2" style={{ marginTop: '1rem' }}>
              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--danger)' }}>Before State</h4>
                <pre style={{
                  background: '#0f172a',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                  color: '#f87171',
                  maxHeight: '250px'
                }}>
                  {selectedLog.beforeState ? JSON.stringify(selectedLog.beforeState, null, 2) : 'None / Initial Creation'}
                </pre>
              </div>

              <div>
                <h4 style={{ marginBottom: '0.5rem', color: 'var(--success)' }}>After State</h4>
                <pre style={{
                  background: '#0f172a',
                  padding: '0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.75rem',
                  overflowX: 'auto',
                  color: '#4ade80',
                  maxHeight: '250px'
                }}>
                  {selectedLog.afterState ? JSON.stringify(selectedLog.afterState, null, 2) : 'None / Deletion'}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogsPage;
