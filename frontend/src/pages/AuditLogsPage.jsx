import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { ShieldAlert, Search, Eye, X, UserCheck, RefreshCw } from 'lucide-react';
import { formatISTTimestamp } from '../utils/dateUtils';
import { PageHeader, Button, SearchInput, Select, FilterBar, FilterField } from '../components/ui';

const AuditLogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('ALL');

  const [selectedLog, setSelectedLog] = useState(null);
  const [showModal, setShowModal] = useState(false);

  const formatIstDateTime = (val) => {
    if (!val) return '—';
    const formatted = formatISTTimestamp(val);
    return formatted === '—' ? '—' : `${formatted} IST`;
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
      <PageHeader
        title="Platform Audit Trail & History"
        subtitle="Accountability records identifying actual user name, role used, and state changes"
        icon={ShieldAlert}
        iconBg="linear-gradient(135deg, #2563eb, #1d4ed8)"
        actions={
          <Button variant="secondary" icon={RefreshCw} onClick={fetchLogs}>
            Refresh Logs
          </Button>
        }
      />

      {/* Standard Enterprise Filter Bar */}
      <FilterBar
        onReset={search || actionFilter !== 'ALL' ? () => {
          setSearch('');
          setActionFilter('ALL');
        } : null}
      >
        <form onSubmit={handleSearchSubmit} style={{ flex: '1 1 280px', display: 'flex', gap: 'var(--space-2)' }}>
          <SearchInput
            placeholder="Search by Employee ID, Name, Action, or Audit ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onSearch={fetchLogs}
          />
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </form>

        <FilterField label="Action:">
          <Select
            size="md"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            style={{ width: 'auto', minWidth: '180px' }}
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
          </Select>
        </FilterField>
      </FilterBar>

      {/* Audit Log Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
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
                      <div><strong style={{ color: 'var(--color-text-primary)' }}>{log.performedBy?.employeeName}</strong></div>
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
