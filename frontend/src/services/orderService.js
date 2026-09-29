import API from './api';

export const orderService = {
  getOrders: async ({ date = '', startDate = '', endDate = '', vendor = '' } = {}) => {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    if (startDate) params.append('startDate', startDate);
    if (endDate) params.append('endDate', endDate);
    if (vendor) params.append('vendor', vendor);
    const res = await API.get(`/orders?${params.toString()}`);
    return res.data;
  },

  createOrder: async (payload) => {
    const res = await API.post('/orders', payload);
    return res.data;
  },

  updateOrder: async (orderId, payload) => {
    const res = await API.put(`/orders/${orderId}`, payload);
    return res.data;
  },

  deleteOrder: async (orderId) => {
    const res = await API.delete(`/orders/${orderId}`);
    return res.data;
  }
};

export default orderService;
