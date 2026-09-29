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

  getCEOReport: async () => {
    const res = await API.get('/reports/ceo');
    return res.data;
  }
};

export default reportService;
