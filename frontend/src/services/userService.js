import API from './api';

export const userService = {
  getUsers: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status && params.status !== 'ALL') query.append('status', params.status);
    if (params.module && params.module !== 'ALL') query.append('module', params.module);
    if (params.managerId) query.append('managerId', params.managerId);
    return API.get(`/users?${query.toString()}`);
  },

  getUserById: async (id) => {
    return API.get(`/users/${id}`);
  },

  createUser: async (data) => {
    return API.post('/users', data);
  },

  updateUser: async (id, data) => {
    return API.put(`/users/${id}`, data);
  },

  deactivateUser: async (id) => {
    return API.delete(`/users/${id}`);
  },

  resetUserPassword: async (id, data) => {
    return API.post(`/users/${id}/reset-password`, data);
  },

  getPotentialManagers: async (excludeUserId = null) => {
    const query = excludeUserId ? `?excludeUserId=${excludeUserId}` : '';
    return API.get(`/users/managers/list${query}`);
  },

  getAllModules: async () => {
    return API.get('/modules');
  },

  getModuleRoles: async (moduleId) => {
    return API.get(`/modules/${moduleId}/roles`);
  },

  getUserModules: async (userId) => {
    return API.get(`/users/${userId}/modules`);
  },

  updateUserModules: async (userId, modules) => {
    return API.put(`/users/${userId}/modules`, { modules });
  }
};

export default userService;
