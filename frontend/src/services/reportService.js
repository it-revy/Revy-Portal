import API from './api';

export const reportService = {
  getYears: async () => {
    const res = await API.get('/reports/years');
    return res.data;
  },

  getMonthlyReport: async ({ year, month, department = '' }) => {
    const params = new URLSearchParams({ year, month });
    if (department) params.append('department', department);
    const res = await API.get(`/reports/monthly?${params.toString()}`);
    return res.data;
  },

  exportExcel: async ({ year, month, department = '' }) => {
    const params = new URLSearchParams({ year, month });
    if (department) params.append('department', department);
    const res = await API.get(`/reports/export-excel?${params.toString()}`, {
      responseType: 'blob'
    });
    return res.data;
  },

  getDirectorAnalyticsReport: async (date = '') => {
    const url = date ? `/reports/director-analytics?date=${date}` : '/reports/director-analytics';
    const res = await API.get(url);
    return res.data;
  },

  getCEOReport: async (date = '') => {
    const url = date ? `/reports/ceo?date=${date}` : '/reports/ceo';
    const res = await API.get(url);
    return res.data;
  }
};

export default reportService;
