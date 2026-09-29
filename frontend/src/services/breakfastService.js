import API from './api';

export const breakfastService = {
  getTodayStatus: async () => {
    const res = await API.get('/breakfast/today');
    return res.data;
  },

  submitDailyStatus: async (payload) => {
    const res = await API.post('/breakfast/submit', payload);
    return res.data;
  },

  getHistory: async () => {
    const res = await API.get('/breakfast/history');
    return res.data;
  },

  submitMultiDayAbsence: async (payload) => {
    const res = await API.post('/breakfast/multi-day-absence', payload);
    return res.data;
  },

  getAdminSummary: async (date) => {
    const res = await API.get(`/breakfast/admin/summary?date=${date}`);
    return res.data;
  },

  getAdminRecords: async ({ date, department = '', search = '' } = {}) => {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    if (department) params.append('department', department);
    if (search) params.append('search', search);
    const res = await API.get(`/breakfast/admin/records?${params.toString()}`);
    return res.data;
  },

  overrideActualStatus: async (payload) => {
    const res = await API.put('/breakfast/actual-status', payload);
    return res.data;
  },

  getDailyEntry: async (date) => {
    const res = await API.get(`/breakfast/daily-entry?date=${date}`);
    return res.data;
  },

  saveDailyEntry: async (payload) => {
    const res = await API.post('/breakfast/daily-entry', payload);
    return res.data;
  },

  getAdditionalOrders: async (date) => {
    const res = await API.get(`/breakfast/additional-orders?date=${date}`);
    return res.data;
  },

  createAdditionalOrder: async (payload) => {
    const res = await API.post('/breakfast/additional-orders', payload);
    return res.data;
  },

  updateAdditionalOrder: async (orderId, payload) => {
    const res = await API.put(`/breakfast/additional-orders/${orderId}`, payload);
    return res.data;
  },

  deleteAdditionalOrder: async (orderId) => {
    const res = await API.delete(`/breakfast/additional-orders/${orderId}`);
    return res.data;
  },

  getAllOrders: async (queryParams = '') => {
    const query = typeof queryParams === 'string' ? queryParams : new URLSearchParams(queryParams).toString();
    const res = await API.get(`/breakfast/orders?${query}`);
    return res.data;
  }
};

export default breakfastService;
