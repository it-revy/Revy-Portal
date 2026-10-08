import React, { useState, useEffect } from 'react';
import API from '../services/api';
import employeeService from '../services/employeeService';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  UserPlus,
  Edit,
  UserX,
  Trash2,
  Search,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  X,
  History,
  Shield,
  UserCheck,
  Check,
  Building,
  Briefcase,
  Utensils
} from 'lucide-react';

const EmployeeManagementPage = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [participationFilter, setParticipationFilter] = useState('ALL');

  // Add User to BMS Modal State
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [availableLoading, setAvailableLoading] = useState(false);
  const [userSearchTerm, setUserSearchTerm] = useState('');
  const [selectedCentralUser, setSelectedCentralUser] = useState(null);
  const [addFormData, setAddFormData] = useState({
    department: 'General',
    designation: 'Employee',
    roleCode: 'BMS_EMPLOYEE',
    breakfastParticipationType: 'NORMAL'
  });
  const [addSubmitting, setAddSubmitting] = useState(false);

  // Edit BMS Profile Modal State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editFormData, setEditFormData] = useState({
    employeeId: '',
    name: '',
    username: '',
    email: '',
    department: '',
    designation: '',
    roleCode: 'BMS_EMPLOYEE',
    breakfastParticipationType: 'NORMAL',
    status: 'active'
  });
  const [editSubmitting, setEditSubmitting] = useState(false);

  // IT_ADMIN Hard Delete Modal state
  const [showHardDeleteModal, setShowHardDeleteModal] = useState(false);
  const [hardDeleteEmpId, setHardDeleteEmpId] = useState(null);
  const [confirmCodeInput, setConfirmCodeInput] = useState('');

  // History Modal state
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [selectedEmp, setSelectedEmp] = useState(null);
  const [empHistory, setEmpHistory] = useState([]);

  const { hasRole, hasPermission } = useAuth();

  useEffect(() => {
    fetchEmployees();
  }, [search, departmentFilter, statusFilter, participationFilter]);

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await employeeService.getEmployees({
        search,
        department: departmentFilter,
        status: statusFilter,
        participationType: participationFilter
      });
      if (res && res.success) {
        setEmployees(res.employees || []);
      } else {
        setError(res?.message || 'Unable to load employees. Please try again.');
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

  const showNotification = (msg) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 4000);
  };

  // Open "Add User to BMS" modal
  const handleOpenAddUserModal = async () => {
    setUserSearchTerm('');
    setSelectedCentralUser(null);
    setAddFormData({
      department: 'Engineering',
      designation: 'Software Engineer',
      roleCode: 'BMS_EMPLOYEE',
      breakfastParticipationType: 'NORMAL'
    });
    setShowAddUserModal(true);
    setAvailableLoading(true);

    try {
      const res = await employeeService.getAvailableUsers();
      setAvailableUsers(res || []);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to fetch available users.');
    } finally {
      setAvailableLoading(false);
    }
  };

  // Submit adding user to BMS
  const handleAddUserSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCentralUser) {
      setError('Please select a Central User to add to BMS.');
      return;
    }

    setAddSubmitting(true);
    try {
      const res = await employeeService.assignUserToBms({
        userId: selectedCentralUser.id,
        roleCode: addFormData.roleCode,
        department: addFormData.department,
        designation: addFormData.designation,
        breakfastParticipationType: addFormData.breakfastParticipationType
      });

      if (res && res.success) {
        setShowAddUserModal(false);
        showNotification(res.message || `User ${selectedCentralUser.name || selectedCentralUser.username} successfully added to BMS.`);
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to add user to BMS.');
    } finally {
      setAddSubmitting(false);
    }
  };

  // Open Edit BMS Profile Modal
  const handleOpenEditModal = (emp) => {
    setEditFormData({
      employeeId: emp.employeeId,
      name: emp.name,
      username: emp.username,
      email: emp.email,
      department: emp.department || '',
      designation: emp.designation || '',
      roleCode: emp.bmsRoleCode || (emp.roles && emp.roles[0]) || 'BMS_EMPLOYEE',
      breakfastParticipationType: emp.breakfastParticipationType || 'NORMAL',
      status: emp.status || 'active'
    });
    setShowEditModal(true);
  };

  // Submit Edit BMS Profile
  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setEditSubmitting(true);
    try {
      const res = await employeeService.updateEmployee(editFormData.employeeId, {
        department: editFormData.department,
        designation: editFormData.designation,
        roleCode: editFormData.roleCode,
        breakfastParticipationType: editFormData.breakfastParticipationType,
        status: editFormData.status
      });

      if (res && res.success) {
        setShowEditModal(false);
        showNotification(`BMS Profile for ${editFormData.name} updated successfully.`);
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to update BMS employee profile.');
    } finally {
      setEditSubmitting(false);
    }
  };

  // Remove User from BMS
  const handleRemoveFromBms = async (emp) => {
    const confirmed = window.confirm(
      `Remove ${emp.name} (${emp.employeeId}) from BMS?\n\n` +
      `• The Central User account will remain Active.\n` +
      `• All historical breakfast transactions and orders are preserved.\n` +
      `• The user will no longer participate in BMS meals.`
    );
    if (!confirmed) return;

    try {
      const res = await employeeService.deactivateEmployee(emp.employeeId);
      if (res && res.success) {
        showNotification(res.message || `User ${emp.name} removed from BMS.`);
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to remove user from BMS.');
    }
  };

  const handleExecuteHardDelete = async () => {
    try {
      const res = await employeeService.hardDeleteEmployee(hardDeleteEmpId, confirmCodeInput);
      if (res && res.success) {
        setShowHardDeleteModal(false);
        setConfirmCodeInput('');
        showNotification('BMS participation record permanently deleted.');
        fetchEmployees();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Hard delete failed');
    }
  };

  const handleViewHistory = async (empId) => {
    try {
      const res = await employeeService.getEmployeeById(empId);
      if (res && res.success) {
        setEmpHistory(res.recentRecords || []);
        setSelectedEmp(res.employee);
        setShowHistoryModal(true);
      }
    } catch (err) {
      setError('Failed to fetch history');
    }
  };

  // Filter available users based on search
  const filteredAvailableUsers = availableUsers.filter(u => {
    if (!userSearchTerm) return true;
    const term = userSearchTerm.toLowerCase();
    return (
      (u.name && u.name.toLowerCase().includes(term)) ||
      (u.username && u.username.toLowerCase().includes(term)) ||
      (u.email && u.email.toLowerCase().includes(term)) ||
      (u.department && u.department.toLowerCase().includes(term))
    );
  });

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Users color="var(--accent-primary)" /> BMS Employees
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            Users participating in the Breakfast Management System. (Central credentials and passwords are strictly managed in Central User Management).
          </p>
        </div>

        {hasPermission('breakfast.employee.create') && (
          <button className="btn btn-primary" onClick={handleOpenAddUserModal}>
            <UserPlus size={18} />
            Add User to BMS
          </button>
        )}
      </div>

      {/* Success Notification Banner */}
      {successMessage && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#34d399',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem'
        }}>
          <CheckCircle2 size={18} color="#10b981" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
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

      {/* Employees Table */}
      <div className="glass-panel table-card-panel">
        <div className="table-container">
          <table className="custom-table" style={{ minWidth: '1100px' }}>
            <thead>
              <tr>
                <th style={{ minWidth: '110px' }}>Employee ID</th>
                <th style={{ minWidth: '130px' }}>Central User</th>
                <th style={{ minWidth: '160px' }}>Name & Email</th>
                <th style={{ minWidth: '130px' }}>Department</th>
                <th style={{ minWidth: '130px' }}>Designation</th>
                <th style={{ minWidth: '140px' }}>BMS Role</th>
                <th style={{ minWidth: '130px' }}>Participation</th>
                <th style={{ minWidth: '90px' }}>BMS Status</th>
                <th className="actions-column" style={{ textAlign: 'right', minWidth: '160px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text-secondary)' }}>
                      <div className="spinner" style={{ width: '18px', height: '18px', border: '2px solid rgba(255,255,255,0.2)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                      <span>Loading BMS employees...</span>
                    </div>
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr><td colSpan="9" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No BMS employees found.</td></tr>
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
                    <td>{emp.department || '—'}</td>
                    <td>
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{emp.designation || '—'}</span>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: emp.bmsRoleCode === 'BMS_ADMIN' ? 'rgba(239, 68, 68, 0.15)' :
                                      emp.bmsRoleCode === 'BMS_FINANCE_MANAGER' ? 'rgba(16, 185, 129, 0.15)' :
                                      emp.bmsRoleCode === 'BMS_DIRECTOR_ANALYTICS' ? 'rgba(139, 92, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)',
                          color: emp.bmsRoleCode === 'BMS_ADMIN' ? '#f87171' :
                                 emp.bmsRoleCode === 'BMS_FINANCE_MANAGER' ? '#34d399' :
                                 emp.bmsRoleCode === 'BMS_DIRECTOR_ANALYTICS' ? '#a78bfa' : '#93c5fd',
                          border: '1px solid rgba(255, 255, 255, 0.15)',
                          fontWeight: 600
                        }}
                      >
                        {emp.bmsRoleName || emp.bmsRoleCode || 'BMS Employee'}
                      </span>
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
                    <td className="actions-column" style={{ textAlign: 'right', minWidth: '160px' }}>
                      <div className="table-action-btn-group">
                        <button
                          type="button"
                          className="action-btn action-btn-history"
                          onClick={() => handleViewHistory(emp.employeeId)}
                          title="View Breakfast History"
                          aria-label={`View history for ${emp.name || emp.employeeId}`}
                        >
                          <History size={16} />
                        </button>
                        {hasPermission('breakfast.employee.update') && (
                          <button
                            type="button"
                            className="action-btn action-btn-edit"
                            onClick={() => handleOpenEditModal(emp)}
                            title="Edit BMS Profile"
                            aria-label={`Edit BMS Profile for ${emp.name || emp.employeeId}`}
                          >
                            <Edit size={16} />
                          </button>
                        )}
                        {emp.status === 'active' && hasPermission('breakfast.employee.deactivate') && (
                          <button
                            type="button"
                            className="action-btn action-btn-warning"
                            onClick={() => handleRemoveFromBms(emp)}
                            title="Remove from BMS"
                            aria-label={`Remove ${emp.name || emp.employeeId} from BMS`}
                          >
                            <UserX size={16} />
                          </button>
                        )}
                        {hasRole('IT_ADMIN') && (
                          <button
                            type="button"
                            className="action-btn action-btn-danger"
                            onClick={() => {
                              setHardDeleteEmpId(emp.employeeId);
                              setShowHardDeleteModal(true);
                            }}
                            title="Permanent Hard Delete"
                            aria-label={`Delete ${emp.name || emp.employeeId}`}
                          >
                            <Trash2 size={16} />
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

      {/* ========================================================================= */}
      {/* 1. ADD USER TO BMS MODAL (Search & Select Existing Central User)          */}
      {/* ========================================================================= */}
      {showAddUserModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '650px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <UserPlus color="var(--accent-primary)" size={22} /> Add User to BMS
              </h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowAddUserModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div style={{
              background: 'rgba(37, 99, 235, 0.1)',
              border: '1px solid rgba(37, 99, 235, 0.25)',
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '1.25rem',
              fontSize: '0.85rem',
              color: '#93c5fd',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <Shield size={18} color="#3b82f6" />
              <span>
                Select an existing Central User to grant BMS participation. Account creation and password management are handled centrally in <strong>User Management</strong>.
              </span>
            </div>

            <form onSubmit={handleAddUserSubmit}>
              {/* Central User Search and Select */}
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" style={{ fontWeight: 600 }}>
                  Select Central User *
                </label>
                <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search central users by Name, Username, or Email..."
                    value={userSearchTerm}
                    onChange={(e) => setUserSearchTerm(e.target.value)}
                  />
                </div>

                {availableLoading ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    Loading eligible central users...
                  </div>
                ) : filteredAvailableUsers.length === 0 ? (
                  <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', background: 'rgba(15, 23, 42, 0.4)', borderRadius: 'var(--radius-sm)' }}>
                    No eligible central users found. All active users may already be assigned to BMS.
                  </div>
                ) : (
                  <div style={{
                    maxHeight: '180px',
                    overflowY: 'auto',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(15, 23, 42, 0.6)'
                  }}>
                    {filteredAvailableUsers.map(u => {
                      const isSelected = selectedCentralUser && selectedCentralUser.id === u.id;
                      return (
                        <div
                          key={u.id}
                          onClick={() => {
                            setSelectedCentralUser(u);
                            if (u.department) setAddFormData(prev => ({ ...prev, department: u.department }));
                            if (u.designation) setAddFormData(prev => ({ ...prev, designation: u.designation }));
                          }}
                          style={{
                            padding: '0.65rem 0.85rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                            cursor: 'pointer',
                            background: isSelected ? 'rgba(37, 99, 235, 0.25)' : 'transparent',
                            transition: 'background 0.15s ease'
                          }}
                        >
                          <div>
                            <strong style={{ color: isSelected ? '#93c5fd' : 'var(--text-primary)', fontSize: '0.9rem' }}>
                              {u.name || u.username}
                            </strong>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                              (@{u.username})
                            </span>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                              {u.email} {u.department ? `• ${u.department}` : ''}
                            </div>
                          </div>
                          {isSelected && <Check size={18} color="#60a5fa" />}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Selected User Summary Card */}
              {selectedCentralUser && (
                <div style={{
                  padding: '0.75rem 1rem',
                  background: 'rgba(37, 99, 235, 0.15)',
                  border: '1px solid rgba(37, 99, 235, 0.35)',
                  borderRadius: 'var(--radius-sm)',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#93c5fd' }}>
                      Selected Central User
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '1rem', color: 'white' }}>
                      {selectedCentralUser.name || selectedCentralUser.username}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Username: <strong>{selectedCentralUser.username}</strong> | Email: <strong>{selectedCentralUser.email}</strong>
                    </div>
                  </div>
                  <span className="badge badge-success">Active Central User</span>
                </div>
              )}

              {/* BMS Specific Fields */}
              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">BMS Module Role *</label>
                  <select
                    className="form-select"
                    value={addFormData.roleCode}
                    onChange={(e) => setAddFormData({ ...addFormData, roleCode: e.target.value })}
                  >
                    <option value="BMS_EMPLOYEE">BMS Employee (Standard Daily Meals)</option>
                    <option value="BMS_ADMIN">BMS Admin (Operational Breakfast Management)</option>
                    <option value="BMS_FINANCE_MANAGER">BMS Finance Manager (Fund Requests & Ledger)</option>
                    <option value="BMS_DIRECTOR_ANALYTICS">BMS Director Analytics (Analytics Dashboard)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Breakfast Participation Type *</label>
                  <select
                    className="form-select"
                    value={addFormData.breakfastParticipationType}
                    onChange={(e) => setAddFormData({ ...addFormData, breakfastParticipationType: e.target.value })}
                  >
                    <option value="NORMAL">Regular Taker (Normal)</option>
                    <option value="PERMANENT_NON_TAKER">Permanent Non-Taker (Opt-out)</option>
                  </select>
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Department *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Engineering, Operations"
                    value={addFormData.department}
                    onChange={(e) => setAddFormData({ ...addFormData, department: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Designation *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Software Engineer, Executive"
                    value={addFormData.designation}
                    onChange={(e) => setAddFormData({ ...addFormData, designation: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddUserModal(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={!selectedCentralUser || addSubmitting}
                >
                  {addSubmitting ? 'Adding to BMS...' : 'Add to BMS'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. EDIT BMS EMPLOYEE PROFILE MODAL (BMS Fields Only)                      */}
      {/* ========================================================================= */}
      {showEditModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2>Edit BMS Profile — {editFormData.name}</h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowEditModal(false)}>
                <X size={18} />
              </button>
            </div>

            {/* Read-only Central Identity Notice */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid var(--border-color)',
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '1.25rem',
              fontSize: '0.85rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <span>Central User: <strong style={{ color: 'white' }}>{editFormData.name}</strong> (@{editFormData.username})</span>
                <span className="badge badge-secondary">{editFormData.employeeId}</span>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Email: {editFormData.email} • <em>Central account credentials are managed in User Management.</em>
              </div>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">BMS Module Role *</label>
                  <select
                    className="form-select"
                    value={editFormData.roleCode}
                    onChange={(e) => setEditFormData({ ...editFormData, roleCode: e.target.value })}
                  >
                    <option value="BMS_EMPLOYEE">BMS Employee (Standard Meals)</option>
                    <option value="BMS_ADMIN">BMS Admin (Operational Breakfast Management)</option>
                    <option value="BMS_FINANCE_MANAGER">BMS Finance Manager (Fund Requests & Ledger)</option>
                    <option value="BMS_DIRECTOR_ANALYTICS">BMS Director Analytics (Analytics Dashboard)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Breakfast Participation Type *</label>
                  <select
                    className="form-select"
                    value={editFormData.breakfastParticipationType}
                    onChange={(e) => setEditFormData({ ...editFormData, breakfastParticipationType: e.target.value })}
                  >
                    <option value="NORMAL">Regular Taker (Normal)</option>
                    <option value="PERMANENT_NON_TAKER">Permanent Non-Taker (Opt-out)</option>
                  </select>
                </div>
              </div>

              <div className="form-grid-2">
                <div className="form-group">
                  <label className="form-label">Department *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={editFormData.department}
                    onChange={(e) => setEditFormData({ ...editFormData, department: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Designation *</label>
                  <input
                    type="text"
                    className="form-input"
                    value={editFormData.designation}
                    onChange={(e) => setEditFormData({ ...editFormData, designation: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">BMS Participation Status</label>
                <select
                  className="form-select"
                  value={editFormData.status}
                  onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value })}
                >
                  <option value="active">Active in BMS</option>
                  <option value="inactive">Inactive in BMS</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={editSubmitting}>
                  {editSubmitting ? 'Updating...' : 'Update BMS Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. IT_ADMIN Exceptional Hard Delete Modal                                 */}
      {/* ========================================================================= */}
      {showHardDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ borderColor: 'var(--danger)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--danger)', marginBottom: '1rem' }}>
              <AlertTriangle size={28} />
              <h2>IT_ADMIN Exceptional Hard Delete</h2>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
              You are about to execute a permanent HARD DELETE on BMS employee <strong style={{ color: 'var(--text-primary)' }}>{hardDeleteEmpId}</strong>.
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

      {/* ========================================================================= */}
      {/* 4. View Breakfast History Modal                                           */}
      {/* ========================================================================= */}
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
