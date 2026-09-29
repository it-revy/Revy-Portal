import API from './api';

export const authService = {
  login: async (username, password) => {
    const res = await API.post('/auth/login', { username, password });
    return res.data;
  },

  getMe: async () => {
    const res = await API.get('/auth/me');
    return res.data;
  },

  changePassword: async (currentPassword, newPassword, confirmPassword) => {
    const res = await API.post('/auth/change-password', {
      currentPassword,
      newPassword,
      confirmPassword
    });
    return res.data;
  }
};

export default authService;
