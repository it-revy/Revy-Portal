import React, { createContext, useContext, useState, useEffect } from 'react';
import API from '../services/api';

const AuthContext = createContext();

const ROLE_PRIORITY = [
  'IT_ADMIN', 'IT Admin',
  'DIRECTOR', 'Director',
  'BMS_ADMIN', 'BMS Admin', 'BREAKFAST_ADMIN',
  'BMS_BF_MANAGER', 'BMS BF Manager',
  'BMS_FINANCE_MANAGER', 'BMS Finance Manager', 'FINANCE_MANAGER',
  'USER_MANAGEMENT_ADMIN', 'User Management Admin',
  'CRM_ADMIN', 'CRM Admin',
  'LMS_ADMIN', 'LMS Admin',
  'IMS_ADMIN', 'IMS Admin',
  'LEAVE_ADMIN', 'Leave Management Admin',
  'MIS_ADMIN', 'MIS Admin',
  'DWR_ADMIN', 'DWR Admin',
  'REPORTS_ADMIN', 'Reports Admin',
  'BMS_EMPLOYEE', 'BMS Employee', 'EMPLOYEE'
];

const pickPrimaryRole = (roles = []) => {
  return ROLE_PRIORITY.find(r => roles.includes(r)) || roles[0] || 'BMS_EMPLOYEE';
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [activeRole, setActiveRole] = useState(localStorage.getItem('activeRole') || null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const res = await API.get('/auth/me');
      if (res.data.success) {
        const userData = res.data.user;
        setUser(userData);
        if (!activeRole || !userData.roles.includes(activeRole)) {
          const primaryRole = pickPrimaryRole(userData.roles);
          setActiveRole(primaryRole);
          localStorage.setItem('activeRole', primaryRole);
        }
      }
    } catch (err) {
      console.error('Failed to fetch user:', err);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (usernameInput, password) => {
    try {
      const res = await API.post('/auth/login', { username: usernameInput, password });
      if (res.data.success) {
        const { token: newToken, user: userData } = res.data;
        const primaryRole = pickPrimaryRole(userData.roles);
        localStorage.setItem('token', newToken);
        localStorage.setItem('activeRole', primaryRole);
        setToken(newToken);
        setUser(userData);
        setActiveRole(primaryRole);
        return { success: true };
      }
      return { success: false, message: res.data.message || 'Login failed' };
    } catch (err) {
      if (!err.response) {
        if (err.code === 'ECONNABORTED') {
          return { success: false, message: 'Connection timed out. The server might be starting up. Please retry in a few seconds.' };
        }
        return { success: false, message: 'Network Error: Unable to reach the backend service. Please check your internet connection or verify the backend is online.' };
      }

      if (err.response.status === 401) {
        return { success: false, message: err.response.data?.message || 'Invalid username or password.' };
      }

      if (err.response.status === 403) {
        return { success: false, message: err.response.data?.message || 'Account is deactivated. Contact IT Administrator.' };
      }

      if (err.response.status === 404) {
        return { success: false, message: 'Authentication endpoint not found (404). Please ensure backend is properly deployed.' };
      }

      if (err.response.status >= 500) {
        return { success: false, message: 'Backend server error (500). Please try again or contact IT Administrator.' };
      }

      return { success: false, message: err.response.data?.message || 'Authentication request failed.' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('activeRole');
    setToken(null);
    setUser(null);
    setActiveRole(null);
  };

  const changePassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      const res = await API.post('/auth/change-password', { currentPassword, newPassword, confirmPassword });
      if (res.data.success) {
        setUser(prev => prev ? { ...prev, forcePasswordChange: false } : null);
        return { success: true, message: res.data.message };
      }
      return { success: false, message: res.data.message };
    } catch (err) {
      return { success: false, message: err.response?.data?.message || 'Failed to update password' };
    }
  };

  const switchRole = (newRole) => {
    if (user && user.roles.includes(newRole)) {
      setActiveRole(newRole);
      localStorage.setItem('activeRole', newRole);
    }
  };

  const isGlobalAdmin = () => {
    if (!user || !user.roles) return false;
    const normRoles = user.roles.map(r => String(r).toUpperCase().replace(/[\s_-]+/g, ''));
    return normRoles.includes('ITADMIN') || normRoles.includes('DIRECTOR') || (user.permissions && user.permissions.includes('*'));
  };

  const hasPermission = (permission) => {
    if (!user) return false;
    if (isGlobalAdmin()) return true;

    // Authoritative permissions assigned to the authenticated user
    if (user.permissions && (user.permissions.includes('*') || user.permissions.includes(permission))) {
      return true;
    }
    // Check across all user's assigned roles in permissionsByRole
    if (user.permissionsByRole && Array.isArray(user.roles)) {
      for (const r of user.roles) {
        const rolePerms = user.permissionsByRole[r];
        if (rolePerms && (rolePerms.includes('*') || rolePerms.includes(permission))) {
          return true;
        }
      }
    }
    return false;
  };

  const hasRole = (role) => {
    if (!user || !user.roles) return false;
    const normTarget = String(role).toLowerCase().replace(/[\s_-]+/g, '');

    // Global administrators satisfy all module and admin role requirements
    if (isGlobalAdmin()) {
      return true;
    }

    // Direct match
    const normRoles = user.roles.map(r => String(r).toLowerCase().replace(/[\s_-]+/g, ''));
    if (normRoles.includes(normTarget)) return true;

    // Role alias mappings for module vs legacy roles
    if (normTarget === 'ceo' || normTarget === 'chiefexecutiveofficer') {
      return normRoles.includes('director');
    }
    if (normTarget === 'breakfastadmin') {
      return normRoles.includes('bmsadmin');
    }
    if (normTarget === 'financemanager') {
      return normRoles.includes('bmsfinancemanager');
    }
    if (normTarget === 'employee') {
      return normRoles.includes('bmsemployee') || normRoles.includes('bmsadmin');
    }

    return false;
  };

  const hasModuleAccess = (moduleCode) => {
    if (!user) return false;
    // Global IT Admin and Director bypass all module boundaries
    if (isGlobalAdmin()) return true;

    const target = String(moduleCode).toUpperCase();
    if (Array.isArray(user.modules)) {
      return user.modules.some(m => (m.moduleCode || '').toUpperCase() === target);
    }
    return false;
  };

  const getModuleRole = (moduleCode) => {
    if (!user || !Array.isArray(user.modules)) return null;
    const target = String(moduleCode).toUpperCase();
    const entry = user.modules.find(m => (m.moduleCode || '').toUpperCase() === target);
    return entry ? (entry.roleCode || entry.roleName || null) : null;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        activeRole,
        loading,
        login,
        logout,
        changePassword,
        switchRole,
        hasPermission,
        hasRole,
        hasModuleAccess,
        getModuleRole,
        isGlobalAdmin: isGlobalAdmin()
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
