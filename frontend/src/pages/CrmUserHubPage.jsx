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
  UserX
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
        setRoles(rolesRes.data.roles || []);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load CRM User Hub data. Please retry.');
    } finally {
      setLoading(false);
    }
  }, [canManage, search, accessFilter, roleFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!confirmModal) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setConfirmModal(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [confirmModal]);

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
      title: willEnable ? `Enable CRM Access for ${targetUser.name || targetUser.username}?` : `Revoke CRM Access for ${targetUser.name || targetUser.username}?`,
      message: willEnable
        ? `This will grant the user access to the CRM workspace with the role "${targetUser.crmRoleName || 'CRM Sales Representative'}".`
        : `Revoking CRM access will prevent this user from logging into the CRM workspace. All historical leads, ownership assignments, and audit records will remain preserved and intact.`
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
            Manage CRM module membership, assign functional roles, and monitor sales representative coverage
          </p>
        </div>

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

          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>CRM Access:</label>
              <select
                className="form-control"
                style={{ width: 'auto', fontSize: '0.85rem' }}
                value={accessFilter}
                onChange={e => setAccessFilter(e.target.value)}
              >
                <option value="ALL">All Portal Users</option>
                <option value="ACTIVE">CRM Active Only</option>
                <option value="INACTIVE">CRM Inactive Only</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>Role:</label>
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
                <th>User Details</th>
                <th>Portal Status</th>
                <th>CRM Access Status</th>
                <th>Assigned CRM Role</th>
                <th style={{ textAlign: 'center' }}>Active Leads</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                    Loading CRM user memberships...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                    No portal users found matching current filters.
                  </td>
                </tr>
              ) : (
                users.map(u => {
                  const isUpdating = updatingUserId === u.userId;
                  return (
                    <tr key={u.userId} className="table-row-hover">
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {u.name || u.username}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          @{u.username} • {u.email}
                        </div>
                      </td>

                      <td>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: u.status === 'active' ? '#ecfdf5' : '#fef2f2',
                          color: u.status === 'active' ? '#065f46' : '#991b1b'
                        }}>
                          {u.status}
                        </span>
                      </td>

                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '4px',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            background: u.crmAccess ? '#eff6ff' : '#f1f5f9',
                            color: u.crmAccess ? '#1d4ed8' : '#64748b'
                          }}>
                            {u.crmAccess ? 'Active CRM Member' : 'No Access'}
                          </span>
                        </div>
                      </td>

                      <td>
                        {u.crmAccess ? (
                          <select
                            className="form-control"
                            style={{
                              padding: '0.3rem 0.6rem',
                              fontSize: '0.85rem',
                              fontWeight: 500,
                              minWidth: '180px'
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
                        ) : (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                            None assigned
                          </span>
                        )}
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
                        <button
                          type="button"
                          onClick={() => handleToggleAccess(u)}
                          className={u.crmAccess ? 'btn btn-secondary' : 'btn btn-primary'}
                          style={{
                            padding: '0.35rem 0.75rem',
                            fontSize: '0.8rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem'
                          }}
                          disabled={isUpdating}
                        >
                          {u.crmAccess ? (
                            <>
                              <UserX size={14} color="#dc2626" />
                              <span>Revoke</span>
                            </>
                          ) : (
                            <>
                              <UserCheck size={14} />
                              <span>Grant Access</span>
                            </>
                          )}
                        </button>
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
                className={confirmModal.willEnable === false ? 'btn btn-danger' : 'btn btn-primary'}
                onClick={handleConfirmAction}
                disabled={Boolean(updatingUserId)}
              >
                {updatingUserId ? 'Processing...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
