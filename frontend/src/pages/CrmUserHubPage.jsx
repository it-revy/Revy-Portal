import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Users,
  Search,
  Shield,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  Layers,
  CheckCircle,
  XCircle,
  UserCheck,
  UserX,
  UserMinus,
  Plus,
  Eye,
  Info,
  Lock,
  Phone,
  Mail,
  Briefcase
} from 'lucide-react';
import crmService from '../services/crmService';

export default function CrmUserHubPage() {
  const navigate = useNavigate();
  const { user, isGlobalAdmin, hasRole, hasPermission } = useAuth();

  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  const [search, setSearch] = useState('');
  const [accessFilter, setAccessFilter] = useState('ALL');
  const [roleFilter, setRoleFilter] = useState('ALL');

  // Confirmation Modal state
  const [confirmModal, setConfirmModal] = useState(null);
  const [updatingUserId, setUpdatingUserId] = useState(null);

  // Add User from Central User Management state
  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [loadingAvailable, setLoadingAvailable] = useState(false);
  const [availableSearch, setAvailableSearch] = useState('');
  const [selectedCentralUser, setSelectedCentralUser] = useState(null);
  const [selectedRoleCode, setSelectedRoleCode] = useState('');
  const [selectedActiveStatus, setSelectedActiveStatus] = useState(true);
  const [addError, setAddError] = useState(null);
  const [submittingAdd, setSubmittingAdd] = useState(false);

  // View User (Read-only identity) state
  const [viewUserModal, setViewUserModal] = useState(null);

  // Security Guard: Only CRM Admins and Global Admins are permitted
  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManage = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.user.manage');

  const fetchData = useCallback(async () => {
    if (!canManage) return;

    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (accessFilter === 'ACTIVE') params.crmAccess = true;
      if (accessFilter === 'INACTIVE') params.crmAccess = false;
      if (roleFilter !== 'ALL') params.roleCode = roleFilter;

      const [usersRes, rolesRes] = await Promise.all([
        crmService.getCrmUsers(params),
        crmService.getCrmRoles()
      ]);

      if (usersRes.data.success) {
        setUsers(usersRes.data.users || []);
      }
      if (rolesRes.data.success) {
        const loadedRoles = rolesRes.data.roles || [];
        setRoles(loadedRoles);
        if (loadedRoles.length > 0 && !selectedRoleCode) {
          setSelectedRoleCode(loadedRoles[0].code);
        }
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load CRM User Hub data. Please retry.');
    } finally {
      setLoading(false);
    }
  }, [canManage, search, accessFilter, roleFilter, selectedRoleCode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Handle ESC key for modals
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setConfirmModal(null);
        setIsAddUserOpen(false);
        setViewUserModal(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchAvailableUsers = async (searchTerm = '') => {
    setLoadingAvailable(true);
    setAddError(null);
    try {
      const res = await crmService.getAvailableCentralUsers({ search: searchTerm });
      if (res.data?.success) {
        setAvailableUsers(res.data.users || []);
      }
    } catch (err) {
      setAddError(err.response?.data?.message || 'Failed to fetch available central users.');
    } finally {
      setLoadingAvailable(false);
    }
  };

  const handleOpenAddUser = () => {
    setSelectedCentralUser(null);
    setSelectedActiveStatus(true);
    if (roles.length > 0) setSelectedRoleCode(roles[0].code);
    setAvailableSearch('');
    setAddError(null);
    setIsAddUserOpen(true);
    fetchAvailableUsers('');
  };

  const handleSelectCentralUser = (u) => {
    setSelectedCentralUser(u);
    setAddError(null);
  };

  const handleAssignUserSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCentralUser) {
      setAddError('Please select a central user to add to the CRM module.');
      return;
    }
    if (!selectedRoleCode) {
      setAddError('Please select a CRM-specific role.');
      return;
    }

    setSubmittingAdd(true);
    setAddError(null);

    try {
      const res = await crmService.assignUserToCrm({
        userId: selectedCentralUser.id,
        roleCode: selectedRoleCode,
        isActive: selectedActiveStatus
      });

      if (res.data?.success) {
        setActionSuccess(res.data.message || `User ${selectedCentralUser.name || selectedCentralUser.username} added to CRM.`);
        setIsAddUserOpen(false);
        fetchData();
      }
    } catch (err) {
      setAddError(err.response?.data?.message || 'Failed to assign user to CRM. Please verify data.');
    } finally {
      setSubmittingAdd(false);
    }
  };

  if (!canManage) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', maxWidth: '540px', margin: '3rem auto' }}>
          <ShieldAlert size={44} color="var(--danger)" style={{ margin: '0 auto 1rem', display: 'block' }} />
          <h2 style={{ color: 'var(--danger)', marginBottom: '0.75rem' }}>403 — Unauthorized</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
            Access to CRM User Hub is strictly restricted to CRM Administrators and Global Platform Administrators.
          </p>
          <button onClick={() => navigate('/crm/dashboard')} className="btn btn-primary">
            ← Return to CRM Dashboard
          </button>
        </div>
      </div>
    );
  }

  const handleToggleAccess = (targetUser) => {
    const willEnable = !targetUser.crmAccess;
    setConfirmModal({
      type: 'ACCESS_TOGGLE',
      targetUser,
      willEnable,
      title: willEnable ? `Activate CRM Membership for ${targetUser.name || targetUser.username}?` : `Deactivate CRM Membership for ${targetUser.name || targetUser.username}?`,
      message: willEnable
        ? `This will activate the user's CRM membership with the assigned role "${targetUser.crmRoleName || 'CRM Sales Representative'}".`
        : `Deactivating CRM membership will pause this user's active CRM access. Their central user account, historical leads, and ownership assignments remain preserved.`
    });
  };

  const handleRemoveMembership = (targetUser) => {
    setConfirmModal({
      type: 'MEMBERSHIP_REMOVE',
      targetUser,
      title: `Remove ${targetUser.name || targetUser.username} from CRM?`,
      message: `Are you sure you want to remove this user from the CRM module? This only revokes CRM module membership. It will NEVER delete their Central User account or central identity credentials.`
    });
  };

  const handleRoleChangeSelect = (targetUser, newRoleCode) => {
    if (!newRoleCode || newRoleCode === targetUser.crmRoleCode) return;

    const selectedRole = roles.find(r => r.code === newRoleCode);
    setConfirmModal({
      type: 'ROLE_CHANGE',
      targetUser,
      newRoleCode,
      selectedRole,
      title: `Change CRM Role for ${targetUser.name || targetUser.username}?`,
      message: `Are you sure you want to change this user's role from "${targetUser.crmRoleName || targetUser.crmRoleCode || 'None'}" to "${selectedRole?.name || newRoleCode}"? This will immediately adjust their CRM permissions.`
    });
  };

  const handleConfirmAction = async () => {
    if (!confirmModal) return;

    setUpdatingUserId(confirmModal.targetUser.userId);
    setError(null);
    setActionSuccess(null);

    try {
      if (confirmModal.type === 'ACCESS_TOGGLE') {
        const res = await crmService.setUserCrmAccess(confirmModal.targetUser.userId, {
          enabled: confirmModal.willEnable,
          roleCode: confirmModal.targetUser.crmRoleCode || (roles[0]?.code || 'CRM_SALES_REP')
        });
        if (res.data.success) {
          setActionSuccess(res.data.message);
          fetchData();
        }
      } else if (confirmModal.type === 'ROLE_CHANGE') {
        const res = await crmService.setUserCrmRole(confirmModal.targetUser.userId, {
          roleCode: confirmModal.newRoleCode
        });
        if (res.data.success) {
          setActionSuccess(res.data.message);
          fetchData();
        }
      } else if (confirmModal.type === 'MEMBERSHIP_REMOVE') {
        const res = await crmService.removeCrmMembership(confirmModal.targetUser.userId);
        if (res.data.success) {
          setActionSuccess(res.data.message || `User removed from CRM module.`);
          fetchData();
        }
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Operation failed. Please verify permissions.');
    } finally {
      setUpdatingUserId(null);
      setConfirmModal(null);
    }
  };

  return (
    <div className="page-body">
      {/* Top Banner */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.25rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.45rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Users size={22} color="var(--accent-primary)" />
            <span>CRM User Hub</span>
          </h1>
          <p style={{ margin: '0.2rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Authoritative module membership for CRM users. Identity is managed centrally; access and roles are managed here.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <button
            onClick={handleOpenAddUser}
            className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', padding: '0.55rem 1rem' }}
          >
            <Plus size={16} />
            <span>Add User</span>
          </button>

          <button
            onClick={fetchData}
            className="btn btn-secondary"
            title="Refresh Users"
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Success Notification */}
      {actionSuccess && (
        <div style={{
          padding: '0.85rem 1rem',
          background: 'var(--success-bg)',
          border: '1px solid var(--success-border)',
          borderRadius: '8px',
          color: 'var(--success-text)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle size={18} />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Error Notification */}
      {error && (
        <div style={{
          padding: '0.85rem 1rem',
          background: 'var(--danger-bg)',
          border: '1px solid var(--danger-border)',
          borderRadius: '8px',
          color: 'var(--danger-text)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: '400px' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search by user name, username, email..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: '2.25rem' }}
            />
            <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Status:</label>
              <select
                className="form-control"
                style={{ width: 'auto', fontSize: '0.85rem' }}
                value={accessFilter}
                onChange={e => setAccessFilter(e.target.value)}
              >
                <option value="ALL">All CRM Members</option>
                <option value="ACTIVE">Active CRM Members</option>
                <option value="INACTIVE">Inactive CRM Members</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>CRM Role:</label>
              <select
                className="form-control"
                style={{ width: 'auto', fontSize: '0.85rem' }}
                value={roleFilter}
                onChange={e => setRoleFilter(e.target.value)}
              >
                <option value="ALL">All Roles</option>
                {roles.map(r => (
                  <option key={r.code} value={r.code}>{r.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <div className="table-responsive">
          <table className="modern-table">
            <thead>
              <tr>
                <th>User Identity (Central)</th>
                <th>CRM Role</th>
                <th>Membership Status</th>
                <th style={{ textAlign: 'center' }}>Active Leads</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    Loading CRM user memberships...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    <Users size={32} color="#cbd5e1" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    <p style={{ margin: 0, fontWeight: 600, color: '#475569' }}>No CRM Members Found</p>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem' }}>
                      Click <strong>Add User</strong> to select an existing Central User and assign them to the CRM module.
                    </p>
                  </td>
                </tr>
              ) : (
                users.map(u => {
                  const isUpdating = updatingUserId === u.userId;
                  return (
                    <tr key={u.userId} className="table-row-hover">
                      <td>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.45rem' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                            {u.name || u.username}
                          </span>
                          {u.designation && (
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                              • {u.designation}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', gap: '0.75rem', marginTop: '0.15rem' }}>
                          <span>@{u.username}</span>
                          <span>{u.email}</span>
                          {u.phone && <span>{u.phone}</span>}
                        </div>
                      </td>

                      <td>
                        <select
                          className="form-control"
                          style={{
                            padding: '0.3rem 0.6rem',
                            fontSize: '0.85rem',
                            fontWeight: 500,
                            minWidth: '170px'
                          }}
                          value={u.crmRoleCode || ''}
                          onChange={e => handleRoleChangeSelect(u, e.target.value)}
                          disabled={isUpdating}
                        >
                          {roles.map(r => (
                            <option key={r.code} value={r.code}>
                              {r.name}
                            </option>
                          ))}
                        </select>
                      </td>

                      <td>
                        <span style={{
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          background: u.crmAccess ? '#eff6ff' : '#fef2f2',
                          color: u.crmAccess ? '#1d4ed8' : '#991b1b',
                          border: u.crmAccess ? '1px solid #bfdbfe' : '1px solid #fecaca'
                        }}>
                          {u.crmAccess ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td style={{ textAlign: 'center' }}>
                        <span style={{
                          padding: '2px 10px',
                          borderRadius: '12px',
                          background: u.assignedLeadCount > 0 ? '#eff6ff' : '#f8fafc',
                          color: u.assignedLeadCount > 0 ? '#1d4ed8' : '#64748b',
                          fontWeight: 700,
                          fontSize: '0.85rem'
                        }}>
                          {u.assignedLeadCount || 0}
                        </span>
                      </td>

                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.4rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                          {/* View User Action */}
                          <button
                            type="button"
                            onClick={() => setViewUserModal(u)}
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                            title="View Central User Details (Read-only)"
                          >
                            <Eye size={13} />
                            <span>View</span>
                          </button>

                          {/* Toggle Active / Inactive Status */}
                          <button
                            type="button"
                            onClick={() => handleToggleAccess(u)}
                            className={u.crmAccess ? 'btn btn-secondary' : 'btn btn-primary'}
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                            disabled={isUpdating}
                            title={u.crmAccess ? 'Deactivate CRM membership' : 'Activate CRM membership'}
                          >
                            {u.crmAccess ? (
                              <>
                                <UserX size={13} color="#d97706" />
                                <span>Deactivate</span>
                              </>
                            ) : (
                              <>
                                <UserCheck size={13} />
                                <span>Activate</span>
                              </>
                            )}
                          </button>

                          {/* Remove from CRM Module Action */}
                          <button
                            type="button"
                            onClick={() => handleRemoveMembership(u)}
                            className="btn btn-secondary"
                            style={{
                              padding: '0.35rem 0.65rem',
                              fontSize: '0.78rem',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              color: '#dc2626',
                              borderColor: '#fca5a5'
                            }}
                            disabled={isUpdating}
                            title="Remove user from CRM module (preserves central account)"
                          >
                            <UserMinus size={13} />
                            <span>Remove</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setConfirmModal(null)}>
          <div className="modal-content" style={{ maxWidth: '480px' }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={20} color="var(--warning)" />
                <h3 style={{ margin: 0, fontSize: '1.15rem' }}>{confirmModal.title}</h3>
              </div>
            </div>

            <div className="modal-body">
              <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {confirmModal.message}
              </p>
            </div>

            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setConfirmModal(null)}
                disabled={Boolean(updatingUserId)}
              >
                Cancel
              </button>
              <button
                type="button"
                className={confirmModal.type === 'MEMBERSHIP_REMOVE' || confirmModal.willEnable === false ? 'btn btn-danger' : 'btn btn-primary'}
                onClick={handleConfirmAction}
                disabled={Boolean(updatingUserId)}
              >
                {updatingUserId ? 'Processing...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User From Central User Management Modal */}
      {isAddUserOpen && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setIsAddUserOpen(false)}>
          <div
            className="modal-content"
            style={{ maxWidth: '640px', width: '95%', maxHeight: '90vh', overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}
          >
            <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: '#eff6ff',
                  color: '#2563eb',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Plus size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Add User to CRM</h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    Select an existing Central User and assign a CRM-specific role
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAddUserOpen(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', color: '#94a3b8', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAssignUserSubmit}>
              <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {addError && (
                  <div style={{
                    padding: '0.75rem 1rem',
                    background: 'var(--danger-bg)',
                    border: '1px solid var(--danger-border)',
                    borderRadius: '8px',
                    color: 'var(--danger-text)',
                    fontSize: '0.85rem'
                  }}>
                    {addError}
                  </div>
                )}

                {/* Step 1: Search & Select Central User */}
                <div>
                  <label className="form-label" style={{ fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
                    <span>1. Search & Select Central User <span style={{ color: 'var(--danger)' }}>*</span></span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      Users without CRM membership
                    </span>
                  </label>

                  <div style={{ position: 'relative', marginBottom: '0.5rem' }}>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Search eligible central users by name, email, designation..."
                      value={availableSearch}
                      onChange={e => {
                        setAvailableSearch(e.target.value);
                        fetchAvailableUsers(e.target.value);
                      }}
                      style={{ paddingLeft: '2.25rem' }}
                    />
                    <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
                  </div>

                  <div style={{
                    maxHeight: '180px',
                    overflowY: 'auto',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    background: '#f8fafc'
                  }}>
                    {loadingAvailable ? (
                      <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        Loading eligible central users...
                      </div>
                    ) : availableUsers.length === 0 ? (
                      <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        No eligible unassigned central users found.
                      </div>
                    ) : (
                      availableUsers.map(u => {
                        const isSelected = selectedCentralUser?.id === u.id;
                        return (
                          <div
                            key={u.id}
                            onClick={() => handleSelectCentralUser(u)}
                            style={{
                              padding: '0.65rem 0.9rem',
                              borderBottom: '1px solid #e2e8f0',
                              background: isSelected ? '#eff6ff' : '#ffffff',
                              borderLeft: isSelected ? '3px solid #2563eb' : '3px solid transparent',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div>
                              <div style={{ fontWeight: isSelected ? 700 : 600, color: '#0f172a', fontSize: '0.9rem' }}>
                                {u.name || u.username}
                                {u.designation && (
                                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 400, marginLeft: '0.4rem' }}>
                                    ({u.designation})
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                @{u.username} • {u.email}
                              </div>
                            </div>
                            {isSelected && (
                              <CheckCircle size={16} color="#2563eb" />
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Selected User Read-Only Preview */}
                {selectedCentralUser && (
                  <div style={{
                    padding: '0.85rem 1rem',
                    background: '#f0fdf4',
                    border: '1px solid #bbf7d0',
                    borderRadius: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#166534', fontWeight: 600, fontSize: '0.85rem' }}>
                      <CheckCircle size={15} />
                      <span>Selected User Profile (Central Identity)</span>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#1e293b' }}>
                      <strong>{selectedCentralUser.name || selectedCentralUser.username}</strong> (@{selectedCentralUser.username})
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#475569', display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                      <span>Email: {selectedCentralUser.email}</span>
                      {selectedCentralUser.phone && <span>Mobile: {selectedCentralUser.phone}</span>}
                      {selectedCentralUser.department && <span>Dept: {selectedCentralUser.department}</span>}
                    </div>
                  </div>
                )}

                {/* Step 2: Role Selection & Status */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>
                      2. CRM Role <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <select
                      className="form-control"
                      value={selectedRoleCode}
                      onChange={e => setSelectedRoleCode(e.target.value)}
                      required
                    >
                      {roles.map(r => (
                        <option key={r.code} value={r.code}>{r.name}</option>
                      ))}
                    </select>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.2rem' }}>
                      Only CRM-scoped roles are eligible
                    </span>
                  </div>

                  <div className="form-group">
                    <label className="form-label" style={{ fontWeight: 600 }}>
                      3. Membership Status
                    </label>
                    <select
                      className="form-control"
                      value={selectedActiveStatus ? 'ACTIVE' : 'INACTIVE'}
                      onChange={e => setSelectedActiveStatus(e.target.value === 'ACTIVE')}
                    >
                      <option value="ACTIVE">Active Membership</option>
                      <option value="INACTIVE">Inactive Membership</option>
                    </select>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'block', marginTop: '0.2rem' }}>
                      Active members can access CRM
                    </span>
                  </div>
                </div>
              </div>

              <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', padding: '1rem 1.5rem', background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsAddUserOpen(false)}
                  disabled={submittingAdd}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={submittingAdd || !selectedCentralUser}
                >
                  {submittingAdd ? 'Saving...' : 'Add to CRM Module'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View User Modal (Read-Only Identity) */}
      {viewUserModal && (
        <div className="modal-backdrop" style={{ zIndex: 1200 }} onClick={() => setViewUserModal(null)}>
          <div
            className="modal-content"
            style={{ maxWidth: '500px', width: '92%', borderRadius: '12px', padding: '1.5rem', background: '#ffffff' }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <div style={{
                  width: '38px',
                  height: '38px',
                  borderRadius: '10px',
                  background: '#f1f5f9',
                  color: '#475569',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Shield size={20} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#0f172a' }}>
                    {viewUserModal.name || viewUserModal.username}
                  </h3>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    @{viewUserModal.username} • CRM Member
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewUserModal(null)}
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', color: '#94a3b8', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{
              padding: '0.75rem 0.9rem',
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.8rem',
              color: '#64748b'
            }}>
              <Lock size={15} style={{ flexShrink: 0 }} />
              <span>Identity information is authoritative from Central User Management and is read-only in the CRM workspace.</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Full Name</span>
                <span style={{ fontWeight: 600, color: '#1e293b' }}>{viewUserModal.name || '—'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Email</span>
                <span style={{ color: '#1e293b' }}>{viewUserModal.email || '—'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Mobile Number</span>
                <span style={{ color: '#1e293b' }}>{viewUserModal.phone || '—'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Designation</span>
                <span style={{ color: '#1e293b' }}>{viewUserModal.designation || '—'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Department</span>
                <span style={{ color: '#1e293b' }}>{viewUserModal.department || '—'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline', paddingTop: '0.5rem', borderTop: '1px solid #f1f5f9' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>CRM Role</span>
                <span style={{ fontWeight: 600, color: '#2563eb' }}>{viewUserModal.crmRoleName || viewUserModal.crmRoleCode || 'None'}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '0.5rem', alignItems: 'baseline' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>CRM Status</span>
                <span style={{ fontWeight: 600, color: viewUserModal.crmAccess ? '#166534' : '#991b1b' }}>
                  {viewUserModal.crmAccess ? 'Active Member' : 'Inactive Member'}
                </span>
              </div>
            </div>

            <div style={{ marginTop: '1.5rem', paddingTop: '0.75rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setViewUserModal(null)}
                style={{ padding: '0.45rem 1.1rem', fontSize: '0.85rem' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
