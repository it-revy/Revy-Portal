import API from './api';

export const auditService = {
  getAuditLogs: async ({ search = '', action = '', skip = 0, limit = 100 } = {}) => {
    const params = new URLSearchParams({ skip, limit });
    if (search) params.append('search', search);
    if (action) params.append('action', action);
    const res = await API.get(`/audit-logs?${params.toString()}`);
    return res.data;
  }
};

export default auditService;
