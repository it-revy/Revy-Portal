import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  Edit,
  UserX,
  Trash2,
  Search,
  Key,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  X,
  History
} from 'lucide-react';

const EmployeeManagementPage = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [participationFilter, setParticipationFilter] = useState('ALL');

  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('CREATE'); // CREATE or EDIT
  const [selectedEmp, setSelectedEmp] = useState(null);

  // Form states
  const [formData, setFormData] = useState({
    employeeId: '',
    username: '',
    name: '',
    email: '',
    password: '',
    phone: '',
    department: '',
    designation: '',
    breakfastParticipationType: 'NORMAL',
    status: 'active',
    roles: ['EMPLOYEE']
  });

  // Password Reset Modal state
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passTargetEmp, setPassTargetEmp] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passMessage, setPassMessage] = useState(null);
  const [passUpdating, setPassUpdating] = useState(false);

  // IT_ADMIN Hard Delete Modal state
  const [showHardDeleteModal, setShowHardDeleteModal] = useState(false);
  const [hardDeleteEmpId, setHardDeleteEmpId] = useState(null);
  const [confirmCodeInput, setConfirmCodeInput] = useState('');

  // History Modal state
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [empHistory, setEmpHistory] = useState([]);

  const { hasRole, hasPermission } = useAuth();

  useEffect(() => {
    fetchEmployees();
  }, [search, departmentFilter, statusFilter, participationFilter]);

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await API.get(
        `/employees?search=${encodeURIComponent(search)}&department=${encodeURIComponent(departmentFilter)}&status=${encodeURIComponent(statusFilter)}&participationType=${encodeURIComponent(participationFilter)}`
      );
      if (res.data && res.data.success) {
        setEmployees(res.data.employees || []);
      } else {
        setError(res.data?.message || 'Unable to load employees. Please try again.');
        setEmployees([]);
      }
    } catch (err) {
      console.error('Failed to fetch employees:', err);
      const msg = err.response?.data?.message || err.message || 'Unable to load employees. Please try again.';
      setError(msg);
      setEmployees([]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreateModal = () => {
    setModalMode('CREATE');
    setFormData({
      employeeId: '',
      username: '',
      name: '',
      email: '',
      password: '',
      phone: '',
      department: 'Engineering',
      designation: 'Software Engineer',
      breakfastParticipationType: 'NORMAL',
      status: 'active',
      roles: ['EMPLOYEE']
    });
    setShowModal(true);
  };

  const handleOpenEditModal = (emp) => {
    setModalMode('EDIT');
    setSelectedEmp(emp);
    const isPnt = ['PERMANENT_NOT_TAKING', 'PERMANENT_NON_TAKER', 'NON_TAKER'].includes((emp.breakfastParticipationType || '').toUpperCase());
    setFormData({
      employeeId: emp.employeeId,
      username: emp.username || '',
      name: emp.name,
      email: emp.email,
      password: '',
      phone: emp.phone || '',
      department: emp.department,
      designation: emp.designation,
      breakfastParticipationType: isPnt ? 'PERMANENT_NON_TAKER' : 'NORMAL',
      status: emp.status,
      roles: emp.roles || ['EMPLOYEE']
    });
    setShowModal(true);
  };

  const handleOpenPasswordModal = (emp) => {
    setPassTargetEmp(emp);
    setNewPassword('');
    setConfirmPassword('');
    setPassMessage(null);
    setShowPasswordModal(true);
  };

  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    setPassMessage(null);

    if (!newPassword || !confirmPassword) {
      setPassMessage({ type: 'danger', text: 'New password and confirm password are required' });
      return;
    }

    if (newPassword.length < 6) {
      setPassMessage({ type: 'danger', text: 'Password must be at least 6 characters long' });
      return;
    }

    if (newPassword !== confirmPassword) {
      setPassMessage({ type: 'danger', text: 'Passwords do not match' });
      return;
    }

    setPassUpdating(true);
    try {
      const res = await API.post(`/employees/${passTargetEmp.employeeId}/reset-password`, {
        newPassword,
        confirmPassword
      });

      if (res.data.success) {
        setPassMessage({ type: 'success', text: res.data.message });
        setTimeout(() => {
          setShowPasswordModal(false);
          setPassTargetEmp(null);
        }, 1500);
      }
    } catch (err) {
      setPassMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to reset password' });
    } finally {
      setPassUpdating(false);
    }
  };

  const handleRoleToggle = (roleCode) => {
    setFormData(prev => {
      const currentRoles = [...prev.roles];
      if (currentRoles.includes(roleCode)) {
        if (currentRoles.length === 1) return prev;
        return { ...prev, roles: currentRoles.filter(r => r !== roleCode) };
      } else {
        return { ...prev, roles: [...currentRoles, roleCode] };
      }
    });
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    try {
      if (modalMode === 'CREATE') {
        const res = await API.post('/employees', formData);
        if (res.data.success) {
          setShowModal(false);
          fetchEmployees();
        }
      } else {
        const res = await API.put(`/employees/${formData.employeeId}`, formData);
        if (res.data.success) {
          setShowModal(false);
          fetchEmployees();
        }
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Operation failed');
    }
  };

  const handleDeactivate = async (empId) => {
    if (!window.confirm(`Deactivate employee ${empId}? Account status will be set to inactive, preserving historical records.`)) {
      return;
    }
    try {
      const res = await API.delete(`/employees/${empId}`);
      if (res.data.success) {
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to deactivate employee');
    }
  };

  const handleExecuteHardDelete = async () => {
    try {
      const res = await API.post(`/employees/${hardDeleteEmpId}/hard-delete`, {
        confirmCode: confirmCodeInput
      });
      if (res.data.success) {
        setShowHardDeleteModal(false);
        setConfirmCodeInput('');
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Hard delete failed');
    }
  };

  const handleViewHistory = async (empId) => {
    try {
      const res = await API.get(`/employees/${empId}`);
      if (res.data.success) {
        setEmpHistory(res.data.recentRecords || []);
        setSelectedEmp(res.data.employee);
        setShowHistoryModal(true);
      }
    } catch (err) {
      setError('Failed to fetch history');
    }
  };

  return (
    <div className="page-body">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Users color="var(--accent-primary)" /> Employee & User Account Management
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Manage user credentials (Username + Password), roles, status, and participation types
          </p>
        </div>

        {hasPermission('breakfast.employee.create') && (
          <button className="btn btn-primary" onClick={handleOpenCreateModal}>
            <UserPlus size={18} />
            Add New Employee
          </button>
        )}
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 220px', minWidth: '200px' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search by Username, ID, Name, Department..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select className="form-select" style={{ flex: '1 1 160px', width: 'auto', minWidth: '140px' }} value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)}>
          <option value="ALL">All Departments</option>
          <option value="IT Infrastructure">IT Infrastructure</option>
          <option value="Administration">Administration</option>
          <option value="Engineering">Engineering</option>
          <option value="Research & Development">Research & Development</option>
          <option value="Executive Office">Executive Office</option>
          <option value="Finance & Accounts">Finance & Accounts</option>
          <option value="Quality Assurance">Quality Assurance</option>
          <option value="Human Resources">Human Resources</option>
          <option value="Operations">Operations</option>
        </select>

        <select className="form-select" style={{ flex: '1 1 140px', width: 'auto', minWidth: '130px' }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="ALL">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>

        <select className="form-select" style={{ flex: '1 1 160px', width: 'auto', minWidth: '140px' }} value={participationFilter} onChange={(e) => setParticipationFilter(e.target.value)}>
          <option value="ALL">All Participation</option>
          <option value="NORMAL">Regular Taker</option>
          <option value="PERMANENT_NON_TAKER">Permanent Non-Taker</option>
        </select>
      </div>

      {/* Error Banner when actions fail but employees exist */}
      {error && employees.length > 0 && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.875rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} color="#ef4444" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer' }}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Employees Table */}
      <div className="glass-panel" style={{ padding: '1.75rem' }}>
        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Employee ID</th>
                <th>Username</th>
                <th>Employee Name</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Assigned Roles</th>
                <th>Breakfast Type</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text-secondary)' }}>
                      <div className="spinner" style={{ width: '18px', height: '18px', border: '2px solid rgba(255,255,255,0.2)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                      <span>Loading employees...</span>
                    </div>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <div style={{ maxWidth: '440px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                      <AlertCircle size={32} color="var(--danger)" />
                      <strong style={{ color: 'var(--text-primary)', fontSize: '1rem' }}>Unable to load employees.</strong>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>{error}</p>
                      <button className="btn btn-secondary" style={{ marginTop: '0.5rem' }} onClick={fetchEmployees}>
                        Please try again
                      </button>
                    </div>
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr><td colSpan="9" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No employees found.</td></tr>
              ) : (
                employees.map(emp => (
                  <tr key={emp.employeeId}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{emp.employeeId}</strong></td>
                    <td>
                      <span className="badge badge-secondary" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {emp.username || '—'}
                      </span>
                    </td>
                    <td>
                      <div><strong>{emp.name}</strong></div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{emp.email}</span>
                    </td>
                    <td>
                      <div>{emp.department}</div>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{emp.designation}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                        {emp.roles?.map(r => {
                          const isFinance = (r === 'FINANCE_MANAGER' || r === 'Finance Manager');
                          return (
                            <span
                              key={r}
                              className="badge"
                              style={isFinance ? {
                                background: 'rgba(16, 185, 129, 0.15)',
                                color: '#34d399',
                                border: '1px solid rgba(16, 185, 129, 0.35)',
                                fontWeight: 600
                              } : {
                                background: 'rgba(59, 130, 246, 0.1)',
                                color: '#93c5fd',
                                border: '1px solid rgba(59, 130, 246, 0.25)'
                              }}
                            >
                              {r.replace('_', ' ')}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${['NORMAL', 'REGULAR', 'REGULAR_TAKER'].includes((emp.breakfastParticipationType || '').toUpperCase()) ? 'badge-success' : 'badge-warning'}`}>
                        {['NORMAL', 'REGULAR', 'REGULAR_TAKER'].includes((emp.breakfastParticipationType || '').toUpperCase()) ? 'Regular Taker' : 'Permanent Non-Taker'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${emp.status === 'active' ? 'badge-success' : 'badge-danger'}`}>
                        {emp.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                        <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem' }} onClick={() => handleViewHistory(emp.employeeId)} title="History">
                          <History size={15} />
                        </button>
                        {hasPermission('breakfast.employee.update') && (
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem' }} onClick={() => handleOpenEditModal(emp)} title="Edit Employee / Username">
                            <Edit size={15} />
                          </button>
                        )}
                        {hasPermission('user.password.reset') && (
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', color: '#2563eb' }} onClick={() => handleOpenPasswordModal(emp)} title="Reset User Password">
                            <Key size={15} />
                          </button>
                        )}
                        {emp.status === 'active' && hasPermission('breakfast.employee.deactivate') && (
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', color: 'var(--warning)' }} onClick={() => handleDeactivate(emp.employeeId)} title="Soft Deactivate">
                            <UserX size={15} />
                          </button>
                        )}
                        {hasRole('IT_ADMIN') && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.6rem', color: 'var(--danger)' }}
                            onClick={() => {
                              setHardDeleteEmpId(emp.employeeId);
                              setShowHardDeleteModal(true);
                            }}
                            title="IT_ADMIN Hard Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add / Edit Employee Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <h2>{modalMode === 'CREATE' ? 'Add New Employee' : `Edit Employee (${formData.employeeId})`}</h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Employee ID</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="EMP-0006 (auto)"
                    value={formData.employeeId}
                    onChange={(e) => setFormData({ ...formData, employeeId: e.target.value })}
                    disabled={modalMode === 'EDIT'}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Username (Login ID) *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. rahul, vasudev"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Full Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Email Address *</label>
                  <input
                    type="email"
                    className="form-input"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone Number</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Department *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Designation *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.designation}
                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Breakfast Participation Type *</label>
                  <select
                    className="form-select"
                    value={formData.breakfastParticipationType}
                    onChange={(e) => setFormData({ ...formData, breakfastParticipationType: e.target.value })}
                  >
                    <option value="NORMAL">Regular Taker (Normal)</option>
                    <option value="PERMANENT_NON_TAKER">Permanent Non-Taker (Opt-out)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Account Status</label>
                  <select
                    className="form-select"
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive (Soft Deactivated)</option>
                  </select>
                </div>
              </div>

              {/* Multi-Role Select Checkboxes */}
              <div className="form-group" style={{ marginTop: '0.5rem', background: 'rgba(15, 23, 42, 0.6)', padding: '1rem', borderRadius: 'var(--radius-sm)' }}>
                <label className="form-label" style={{ marginBottom: '0.75rem', display: 'block', color: 'var(--accent-primary)' }}>
                  Assign Roles (Multi-Select Support)
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  {['EMPLOYEE', 'BREAKFAST_ADMIN', 'FINANCE_MANAGER', 'IT_ADMIN', 'CEO'].map(role => (
                    <label key={role} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                      <input
                        type="checkbox"
                        checked={formData.roles.includes(role)}
                        onChange={() => handleRoleToggle(role)}
                        style={{ width: '16px', height: '16px', accentColor: 'var(--accent-primary)' }}
                      />
                      {role === 'FINANCE_MANAGER' ? 'Finance Manager' : role.replace('_', ' ')}
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {modalMode === 'CREATE' ? 'Create Employee' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* IT Admin Password Reset Modal */}
      {showPasswordModal && passTargetEmp && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '450px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Key color="#2563eb" size={20} /> Change User Password
              </h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowPasswordModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="glass-card" style={{ padding: '0.85rem 1rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <div><strong>User:</strong> {passTargetEmp.name}</div>
              <div><strong>Username:</strong> <code style={{ color: 'var(--accent-primary)' }}>{passTargetEmp.username}</code></div>
              <div><strong>Employee ID:</strong> {passTargetEmp.employeeId}</div>
            </div>

            {passMessage && (
              <div style={{
                background: passMessage.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
                border: `1px solid ${passMessage.type === 'success' ? '#a7f3d0' : '#fca5a5'}`,
                color: passMessage.type === 'success' ? 'var(--success-text)' : 'var(--danger-text)',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '1rem',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                {passMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                {passMessage.text}
              </div>
            )}

            <form onSubmit={handleResetPasswordSubmit}>
              <div className="form-group">
                <label className="form-label">New Password *</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Enter new password (min 6 chars)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Confirm New Password *</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Re-enter new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowPasswordModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={passUpdating}>
                  {passUpdating ? 'Updating Password...' : 'Update Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* IT_ADMIN Exceptional Hard Delete Modal */}
      {showHardDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ borderColor: 'var(--danger)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--danger)', marginBottom: '1rem' }}>
              <AlertTriangle size={28} />
              <h2>IT_ADMIN Exceptional Hard Delete</h2>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              You are about to execute a permanent HARD DELETE on employee <strong style={{ color: 'var(--text-primary)' }}>{hardDeleteEmpId}</strong>. Normal administrative deletion is soft deactivation.
            </p>

            <div className="form-group">
              <label className="form-label">Type "CONFIRM_PERMANENT_DELETE" to confirm:</label>
              <input
                type="text"
                className="form-input"
                placeholder="CONFIRM_PERMANENT_DELETE"
                value={confirmCodeInput}
                onChange={(e) => setConfirmCodeInput(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
              <button className="btn btn-secondary" onClick={() => setShowHardDeleteModal(false)}>
                Cancel
              </button>
              <button
                className="btn btn-danger"
                disabled={confirmCodeInput !== 'CONFIRM_PERMANENT_DELETE'}
                onClick={handleExecuteHardDelete}
              >
                Execute Hard Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View History Modal */}
      {showHistoryModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '700px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <h2>Breakfast History ({selectedEmp?.name} - {selectedEmp?.employeeId})</h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowHistoryModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Business Date</th>
                    <th>Response</th>
                    <th>Reason</th>
                    <th>Submitted Time</th>
                  </tr>
                </thead>
                <tbody>
                  {empHistory.length === 0 ? (
                    <tr><td colSpan="4" style={{ textAlign: 'center', padding: '2rem' }}>No history recorded.</td></tr>
                  ) : (
                    empHistory.map(r => (
                      <tr key={r._id}>
                        <td>{r.businessDate}</td>
                        <td>
                          <span className={`badge ${r.response === 'YES' ? 'badge-success' : 'badge-danger'}`}>
                            {r.response}
                          </span>
                        </td>
                        <td>{r.reasonText || r.reasonCode || '—'}</td>
                        <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          {new Date(r.submittedAt).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmployeeManagementPage;
