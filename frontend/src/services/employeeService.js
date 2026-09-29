import API from './api';

export const employeeService = {
  getEmployees: async ({ search = '', department = '', status = '', participationType = '' } = {}) => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (department) params.append('department', department);
    if (status) params.append('status', status);
    if (participationType) params.append('participationType', participationType);
    const res = await API.get(`/employees?${params.toString()}`);
    return res.data;
  },

  getEmployeeById: async (empId) => {
    const res = await API.get(`/employees/${empId}`);
    return res.data;
  },

  createEmployee: async (payload) => {
    const res = await API.post('/employees', payload);
    return res.data;
  },

  updateEmployee: async (empId, payload) => {
    const res = await API.put(`/employees/${empId}`, payload);
    return res.data;
  },

  deactivateEmployee: async (empId) => {
    const res = await API.delete(`/employees/${empId}`);
    return res.data;
  },

  resetPassword: async (empId, payload) => {
    const res = await API.post(`/employees/${empId}/reset-password`, payload);
    return res.data;
  },

  hardDeleteEmployee: async (empId, confirmCode) => {
    const res = await API.post(`/employees/${empId}/hard-delete`, { confirmCode });
    return res.data;
  }
};

export default employeeService;
