import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import userService from '../services/userService';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Shield,
  Layers,
  Edit,
  Key,
  UserX,
  UserCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  X,
  Save,
  Building,
  Phone,
  Mail,
  User as UserIcon,
  ChevronRight,
  Briefcase
} from 'lucide-react';

const UserManagementPage = () => {
  const { hasRole, hasPermission, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [modules, setModules] = useState([]);
  const [managers, setManagers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [moduleFilter, setModuleFilter] = useState('ALL');

  // Modals state
  const [showUserModal, setShowUserModal] = useState(false);
  const [modalMode, setModalMode] = useState('CREATE'); // 'CREATE' | 'EDIT'
  const [selectedUser, setSelectedUser] = useState(null);

  const [showModulesModal, setShowModulesModal] = useState(false);
  const [userModuleAssignments, setUserModuleAssignments] = useState([]);
  const [modulesSaving, setModulesSaving] = useState(false);

  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);

  // User form data
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    email: '',
    phone: '',
    password: '',
    managerId: '',
    status: 'active',
    roles: ['EMPLOYEE']
  });
  const [formSaving, setFormSaving] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [search, statusFilter, moduleFilter]);

  const loadInitialData = async () => {
    try {
      const [modRes, mgrRes] = await Promise.all([
        userService.getAllModules(),
        userService.getPotentialManagers()
      ]);
      setModules(modRes.data || []);
      setManagers(mgrRes.data || []);
    } catch (err) {
      console.error('Failed to load metadata:', err);
    }
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await userService.getUsers({
        search,
        status: statusFilter,
        module: moduleFilter
      });
      setUsers(res.data || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch users:', err);
      setError('Unable to load users list. Please verify connection.');
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (msg) => {
    setSuccessMessage(msg);
    setTimeout(() => setSuccessMessage(null), 3500);
  };

  // Open Create Modal
  const handleOpenCreateModal = async () => {
    setModalMode('CREATE');
    setSelectedUser(null);
    setFormData({
      name: '',
      username: '',
      email: '',
      phone: '',
      password: '',
      managerId: '',
      status: 'active',
      roles: ['EMPLOYEE']
    });
    // Refresh manager list
    try {
      const mgrRes = await userService.getPotentialManagers();
      setManagers(mgrRes.data || []);
    } catch {}
    setShowUserModal(true);
  };

  // Open Edit Modal
  const handleOpenEditModal = async (u) => {
    setModalMode('EDIT');
    setSelectedUser(u);
    setFormData({
      name: u.name,
      username: u.username,
      email: u.email,
      phone: u.phone || '',
      password: '',
      managerId: u.managerId || '',
      status: u.status,
      roles: u.roles || ['EMPLOYEE']
    });
    // Refresh manager list excluding self to prevent self-assignment
    try {
      const mgrRes = await userService.getPotentialManagers(u.id);
      setManagers(mgrRes.data || []);
    } catch {}
    setShowUserModal(true);
  };

  // Save User Form (Create or Update)
  const handleSaveUser = async (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.email.trim()) {
      setError('Name and email are required.');
      return;
    }

    setFormSaving(true);
    setError(null);
    try {
      if (modalMode === 'CREATE') {
        const payload = { ...formData };
        if (!payload.password) delete payload.password;
        if (!payload.managerId) payload.managerId = null;
        await userService.createUser(payload);
        showNotification('User account created successfully.');
      } else {
        const payload = {
          name: formData.name,
          username: formData.username,
          email: formData.email,
          phone: formData.phone,
          managerId: formData.managerId || null,
          status: formData.status,
          roles: formData.roles
        };
        await userService.updateUser(selectedUser.id, payload);
        showNotification('User account updated successfully.');
      }
      setShowUserModal(false);
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save user.');
    } finally {
      setFormSaving(false);
    }
  };

  // Open Module Access Modal
  const handleOpenModulesModal = async (u) => {
    setSelectedUser(u);
    setModulesSaving(false);
    try {
      const res = await userService.getUserModules(u.id);
      setUserModuleAssignments(res.data || []);
      setShowModulesModal(true);
    } catch (err) {
      setError('Failed to fetch module memberships.');
    }
  };

  // Toggle Module in modal
  const handleToggleModule = (moduleCode) => {
    setUserModuleAssignments(prev => prev.map(m => {
      if (m.moduleCode === moduleCode) {
        if (m.isOpenToAll) return m; // Cannot disable universal modules
        const nextEnabled = !m.isEnabled;
        // If enabling and no role is set, pick default role
        let nextRoleCode = m.roleCode;
        let nextRoleId = m.roleId;
        if (nextEnabled && !nextRoleCode) {
          const modDef = modules.find(mod => mod.code === moduleCode);
          if (modDef && modDef.roles && modDef.roles.length > 0) {
            nextRoleCode = modDef.roles[0].code;
            nextRoleId = modDef.roles[0].id;
          }
        }
        return {
          ...m,
          isEnabled: nextEnabled,
          roleCode: nextEnabled ? nextRoleCode : null,
          roleId: nextEnabled ? nextRoleId : null
        };
      }
      return m;
    }));
  };

  // Change Module Role in modal
  const handleModuleRoleChange = (moduleCode, roleCode) => {
    const modDef = modules.find(m => m.code === moduleCode);
    const selectedRole = modDef?.roles?.find(r => r.code === roleCode);

    setUserModuleAssignments(prev => prev.map(m => {
      if (m.moduleCode === moduleCode) {
        return {
          ...m,
          roleCode: roleCode,
          roleId: selectedRole?.id || null,
          roleName: selectedRole?.name || null
        };
      }
      return m;
    }));
  };

  // Save Module Access
  const handleSaveModules = async () => {
    if (!selectedUser) return;
    setModulesSaving(true);
    try {
      const payload = userModuleAssignments.map(m => ({
        moduleCode: m.moduleCode,
        enabled: m.isEnabled,
        roleCode: m.roleCode
      }));
      await userService.updateUserModules(selectedUser.id, payload);
      showNotification(`Module access updated for ${selectedUser.name || selectedUser.username}.`);
      setShowModulesModal(false);
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save module assignments.');
    } finally {
      setModulesSaving(false);
    }
  };

  // Open Reset Password Modal
  const handleOpenPasswordModal = (u) => {
    setSelectedUser(u);
    setNewPassword('');
    setConfirmPassword('');
    setPasswordError('');
    setShowPasswordModal(true);
  };

  const handleSavePassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 6) {
      setPasswordError('Password must be at least 6 characters long.');
      return;
    }
    if (confirmPassword && newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.');
      return;
    }

    setPasswordSaving(true);
    setPasswordError('');
    try {
      await userService.resetUserPassword(selectedUser.id, {
        newPassword,
        confirmPassword
      });
      showNotification(`Password reset for ${selectedUser.username}.`);
      setShowPasswordModal(false);
    } catch (err) {
      setPasswordError(err.response?.data?.message || 'Failed to reset password.');
    } finally {
      setPasswordSaving(false);
    }
  };

  // Toggle user active / inactive status
  const handleToggleUserStatus = async (u) => {
    const isActivating = u.status === 'inactive';
    const actionText = isActivating ? 'activate' : 'deactivate';
    if (!window.confirm(`Are you sure you want to ${actionText} user account ${u.name || u.username}?`)) {
      return;
    }
    try {
      if (isActivating) {
        await userService.updateUser(u.id, { status: 'active' });
        showNotification(`User ${u.username} activated.`);
      } else {
        await userService.deactivateUser(u.id);
        showNotification(`User ${u.username} deactivated.`);
      }
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.message || `Failed to ${actionText} user.`);
    }
  };

  return (
    <div className="page-body">
      {/* Header Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: 0, fontSize: '1.6rem' }}>
            <Users color="var(--accent-primary)" size={28} />
            User & System Identity Management
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.35rem', fontSize: '0.9rem' }}>
            Manage central user identities, reporting managers, and independent business module memberships
          </p>
        </div>

        <button className="btn btn-primary" onClick={handleOpenCreateModal} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <UserPlus size={18} />
          Add New User
        </button>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.35)',
          color: '#34d399',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem'
        }}>
          <CheckCircle2 size={18} color="#10b981" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
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

      {/* Filters Bar */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 240px', minWidth: '220px', position: 'relative' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search by Name, Username, Email, Phone..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="form-select"
          style={{ flex: '0 1 180px', minWidth: '150px' }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All Statuses</option>
          <option value="active">Active Only</option>
          <option value="inactive">Inactive Only</option>
        </select>

        <select
          className="form-select"
          style={{ flex: '0 1 200px', minWidth: '160px' }}
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
        >
          <option value="ALL">All Modules</option>
          <option value="BMS">BMS (Breakfast)</option>
          <option value="CRM">CRM (Sales & Pipeline)</option>
          <option value="LMS">LMS (Laboratory)</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="glass-panel table-card-panel">
        <div className="table-container">
          <table className="custom-table" style={{ minWidth: '1150px' }}>
            <thead>
              <tr>
                <th style={{ minWidth: '180px' }}>User / Full Name</th>
                <th style={{ minWidth: '120px' }}>Username</th>
                <th style={{ minWidth: '180px' }}>Contact Details</th>
                <th style={{ minWidth: '150px' }}>Manager (Hierarchy)</th>
                <th style={{ minWidth: '140px' }}>System Roles</th>
                <th style={{ minWidth: '180px' }}>Module Memberships</th>
                <th style={{ minWidth: '90px' }}>Status</th>
                <th className="actions-column" style={{ textAlign: 'right', minWidth: '220px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '3rem' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.75rem', color: 'var(--text-secondary)' }}>
                      <div className="spinner" style={{ width: '20px', height: '20px', border: '2px solid rgba(255,255,255,0.2)', borderTopColor: 'var(--accent-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                      <span>Loading user identities...</span>
                    </div>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                    No users found matching current filters.
                  </td>
                </tr>
              ) : (
                users.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          background: 'rgba(59, 130, 246, 0.15)',
                          color: '#60a5fa',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: 700,
                          fontSize: '0.85rem',
                          flexShrink: 0
                        }}>
                          {u.name ? u.name.charAt(0).toUpperCase() : u.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>{u.name}</strong>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {u.hasBmsEmployee ? `BMS ID: ${u.employeeId}` : 'System User'}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-secondary" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {u.username}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontSize: '0.825rem' }}>
                        <div style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Mail size={13} color="var(--text-muted)" />
                          <span>{u.email}</span>
                        </div>
                        {u.phone && (
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                            <Phone size={12} color="var(--text-muted)" />
                            <span>{u.phone}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      {u.managerName ? (
                        <div style={{ fontSize: '0.825rem' }}>
                          <strong style={{ color: 'var(--text-primary)' }}>{u.managerName}</strong>
                          <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                            @{u.managerUsername}
                          </span>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                          — (Top-Level)
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
                        {u.roles?.map(r => (
                          <span
                            key={r}
                            className="badge"
                            style={{
                              background: r === 'IT_ADMIN' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(59, 130, 246, 0.12)',
                              color: r === 'IT_ADMIN' ? '#f87171' : '#93c5fd',
                              fontSize: '0.7rem',
                              border: r === 'IT_ADMIN' ? '1px solid rgba(239, 68, 68, 0.25)' : '1px solid rgba(59, 130, 246, 0.25)'
                            }}
                          >
                            {r.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                        {u.modules && u.modules.length > 0 ? (
                          u.modules.map(m => (
                            <span
                              key={m.moduleCode}
                              className="badge"
                              style={{
                                background: m.moduleCode === 'BMS' ? 'rgba(16, 185, 129, 0.12)' : m.moduleCode === 'CRM' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(139, 92, 246, 0.12)',
                                color: m.moduleCode === 'BMS' ? '#34d399' : m.moduleCode === 'CRM' ? '#fbbf24' : '#c084fc',
                                border: '1px solid rgba(255,255,255,0.1)',
                                fontSize: '0.75rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.3rem'
                              }}
                              title={m.roleName ? `${m.moduleName} — Role: ${m.roleName}` : m.moduleName}
                            >
                              <strong>{m.moduleCode}</strong>
                              {m.roleCode && <span style={{ opacity: 0.8, fontSize: '0.7rem' }}>({m.roleCode.replace(`${m.moduleCode}_`, '')})</span>}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            Universal Access Only
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${u.status === 'active' ? 'badge-success' : 'badge-danger'}`}>
                        {u.status}
                      </span>
                    </td>
                    <td className="actions-column" style={{ textAlign: 'right', minWidth: '220px' }}>
                      <div className="table-action-btn-group">
                        <button
                          type="button"
                          className="action-btn action-btn-history"
                          onClick={() => handleOpenModulesModal(u)}
                          title="Manage Module Access"
                          aria-label={`Manage modules for ${u.name || u.username}`}
                        >
                          <Layers size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn action-btn-edit"
                          onClick={() => handleOpenEditModal(u)}
                          title="Edit User Details"
                          aria-label={`Edit ${u.name || u.username}`}
                        >
                          <Edit size={16} />
                        </button>
                        <button
                          type="button"
                          className="action-btn action-btn-password"
                          onClick={() => handleOpenPasswordModal(u)}
                          title="Reset Password"
                          aria-label={`Reset password for ${u.name || u.username}`}
                        >
                          <Key size={16} />
                        </button>
                        <button
                          type="button"
                          className={u.status === 'active' ? 'action-btn action-btn-warning' : 'action-btn action-btn-edit'}
                          onClick={() => handleToggleUserStatus(u)}
                          title={u.status === 'active' ? 'Deactivate User' : 'Activate User'}
                          aria-label={`Toggle active state for ${u.name || u.username}`}
                        >
                          {u.status === 'active' ? <UserX size={16} /> : <UserCheck size={16} />}
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

      {/* Modal 1: Create / Edit User Modal */}
      {showUserModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '580px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserIcon color="var(--accent-primary)" size={20} />
                {modalMode === 'CREATE' ? 'Add New System User' : `Edit User (${formData.username || selectedUser?.username})`}
              </h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowUserModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveUser}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label className="form-label">Full Name *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. John Smith"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="form-label">Username</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. john.smith (optional)"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label className="form-label">Email Address *</label>
                  <input
                    type="email"
                    className="form-input"
                    placeholder="john@company.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="form-label">Phone Number</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="+91 9876543210"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label className="form-label">Reporting Manager</label>
                  <select
                    className="form-select"
                    value={formData.managerId || ''}
                    onChange={(e) => setFormData({ ...formData, managerId: e.target.value || null })}
                  >
                    <option value="">— No Manager (Top-Level) —</option>
                    {managers.map(m => (
                      <option key={m.id} value={m.id}>
                        {m.name} (@{m.username})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="form-label">Account Status</label>
                  <select
                    className="form-select"
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {modalMode === 'CREATE' && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <label className="form-label">Initial Password (Default: Password123!)</label>
                  <input
                    type="password"
                    className="form-input"
                    placeholder="Leave blank for default"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>
              )}

              <div style={{ marginBottom: '1.5rem' }}>
                <label className="form-label">System Platform Role</label>
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  {['EMPLOYEE', 'BREAKFAST_ADMIN', 'FINANCE_MANAGER', 'IT_ADMIN', 'CEO', 'DIRECTOR_ANALYTICS'].map(role => {
                    const isSelected = formData.roles.includes(role);
                    return (
                      <button
                        type="button"
                        key={role}
                        onClick={() => {
                          const curr = [...formData.roles];
                          if (curr.includes(role)) {
                            if (curr.length > 1) {
                              setFormData({ ...formData, roles: curr.filter(r => r !== role) });
                            }
                          } else {
                            setFormData({ ...formData, roles: [...curr, role] });
                          }
                        }}
                        style={{
                          padding: '0.4rem 0.75rem',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                          background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.05)',
                          color: isSelected ? '#60a5fa' : 'var(--text-secondary)'
                        }}
                      >
                        {role.replace('_', ' ')}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUserModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={formSaving}>
                  {formSaving ? 'Saving...' : modalMode === 'CREATE' ? 'Create User' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Module Access Management Modal */}
      {showModulesModal && selectedUser && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '640px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Layers color="var(--accent-primary)" size={22} />
                  Module Access & Roles
                </h2>
                <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Assign authorized business modules for <strong>{selectedUser.name || selectedUser.username}</strong>
                </p>
              </div>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowModulesModal(false)}>
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.5rem', maxHeight: '420px', overflowY: 'auto' }}>
              {userModuleAssignments.map(m => {
                const modDef = modules.find(def => def.code === m.moduleCode);
                const isUniversal = m.isOpenToAll;
                const isEnabled = m.isEnabled || isUniversal;

                return (
                  <div
                    key={m.moduleCode}
                    className="glass-card"
                    style={{
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '1rem',
                      borderLeft: isEnabled ? '3px solid var(--accent-primary)' : '3px solid transparent',
                      opacity: isEnabled ? 1 : 0.65
                    }}
                  >
                    <div style={{ flex: '1 1 200px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <strong style={{ color: 'var(--text-primary)', fontSize: '0.95rem' }}>{m.moduleName}</strong>
                        <span className="badge badge-secondary" style={{ fontSize: '0.7rem', fontWeight: 700 }}>
                          {m.moduleCode}
                        </span>
                        {isUniversal && (
                          <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.7rem' }}>
                            Universal Access
                          </span>
                        )}
                      </div>
                      <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {isUniversal
                          ? 'Accessible by all authenticated users in the company.'
                          : isEnabled
                          ? 'User has authorized access to this business module.'
                          : 'Not assigned to user. Access restricted.'}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      {/* Module-Scoped Role Dropdown */}
                      {isEnabled && !isUniversal && modDef?.roles && modDef.roles.length > 0 && (
                        <div>
                          <select
                            className="form-select"
                            style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem', minWidth: '160px' }}
                            value={m.roleCode || ''}
                            onChange={(e) => handleModuleRoleChange(m.moduleCode, e.target.value)}
                          >
                            {modDef.roles.map(r => (
                              <option key={r.code} value={r.code}>
                                {r.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      {/* Enable/Disable Toggle */}
                      {!isUniversal ? (
                        <button
                          type="button"
                          onClick={() => handleToggleModule(m.moduleCode)}
                          className={`btn ${isEnabled ? 'btn-primary' : 'btn-secondary'}`}
                          style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
                        >
                          {isEnabled ? 'Enabled ✓' : 'Disabled'}
                        </button>
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: '#10b981', fontWeight: 600, padding: '0.35rem 0.5rem' }}>
                          Open
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowModulesModal(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveModules}
                disabled={modulesSaving}
                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
              >
                <Save size={16} />
                {modulesSaving ? 'Saving...' : 'Save Module Access'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 3: Reset Password Modal */}
      {showPasswordModal && selectedUser && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '420px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Key color="var(--accent-primary)" size={20} />
                Reset User Password
              </h2>
              <button className="btn btn-secondary" style={{ padding: '0.3rem 0.5rem' }} onClick={() => setShowPasswordModal(false)}>
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Enter a new temporary password for <strong>{selectedUser.name || selectedUser.username}</strong>. They will be required to change it on their next login.
            </p>

            {passwordError && (
              <div style={{ color: 'var(--danger)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
                {passwordError}
              </div>
            )}

            <form onSubmit={handleSavePassword}>
              <div style={{ marginBottom: '1rem' }}>
                <label className="form-label">New Password *</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="At least 6 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label className="form-label">Confirm Password *</label>
                <input
                  type="password"
                  className="form-input"
                  placeholder="Repeat new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowPasswordModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={passwordSaving}>
                  {passwordSaving ? 'Updating...' : 'Set Password'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagementPage;
