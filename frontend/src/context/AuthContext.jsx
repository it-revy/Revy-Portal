import React, { createContext, useContext, useState, useEffect } from 'react';
import API from '../services/api';

const AuthContext = createContext();

const ROLE_PRIORITY = ['IT_ADMIN', 'DIRECTOR_ANALYTICS', 'CEO', 'FINANCE_MANAGER', 'BREAKFAST_ADMIN', 'EMPLOYEE'];
const pickPrimaryRole = (roles = []) => {
  return ROLE_PRIORITY.find(r => roles.includes(r)) || roles[0] || 'EMPLOYEE';
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

  const hasPermission = (permission) => {
    if (!user) return false;
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
    if (user.roles.includes(role)) return true;
    const normTarget = String(role).toLowerCase().replace(/[\s_-]+/g, '');
    return user.roles.some(r => String(r).toLowerCase().replace(/[\s_-]+/g, '') === normTarget);
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
        hasRole
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
