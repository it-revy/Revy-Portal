import API from './api';

export const transactionService = {
  getBalance: async () => {
    const res = await API.get('/breakfast/money/balance');
    return res.data;
  },

  getTransactions: async (params = {}) => {
    const query = new URLSearchParams(params).toString();
    const res = await API.get(`/breakfast/money/transactions?${query}`);
    return res.data;
  },

  getDailyStatement: async (date) => {
    const res = await API.get(`/breakfast/money/statement/daily?date=${date}`);
    return res.data;
  },

  getMonthlyStatement: async (month) => {
    const res = await API.get(`/breakfast/money/statement/monthly?month=${month}`);
    return res.data;
  },

  createFundRequest: async (payload) => {
    const res = await API.post('/breakfast/money/requests', payload);
    return res.data;
  },

  getFundRequests: async (status = '') => {
    const res = await API.get(`/breakfast/money/requests?status=${status}`);
    return res.data;
  },

  approveFundRequest: async (requestId, payload) => {
    const res = await API.put(`/breakfast/money/requests/${requestId}/approve`, payload);
    return res.data;
  },

  rejectFundRequest: async (requestId, payload) => {
    const res = await API.put(`/breakfast/money/requests/${requestId}/reject`, payload);
    return res.data;
  },

  provideFundMoney: async (requestId, payload) => {
    const res = await API.put(`/breakfast/money/requests/${requestId}/provide`, payload);
    return res.data;
  },

  verifyFundReceipt: async (requestId, payload) => {
    const res = await API.put(`/breakfast/money/requests/${requestId}/verify`, payload);
    return res.data;
  },

  recordExpense: async (payload) => {
    const res = await API.post('/breakfast/money/expense', payload);
    return res.data;
  },

  receiveMoney: async (payload) => {
    const res = await API.post('/breakfast/money/receive', payload);
    return res.data;
  }
};

export default transactionService;
