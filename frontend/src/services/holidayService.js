import API from './api';

export const holidayService = {
  getHolidays: async (year = '') => {
    const url = year ? `/holidays?year=${year}` : '/holidays';
    const res = await API.get(url);
    return res.data;
  },

  createHoliday: async (payload) => {
    const res = await API.post('/holidays', payload);
    return res.data;
  },

  deleteHoliday: async (holidayId) => {
    const res = await API.delete(`/holidays/${holidayId}`);
    return res.data;
  }
};

export default holidayService;
