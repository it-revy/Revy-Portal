import API from './api';

export const invoiceService = {
  // Collateral summary (Quotations & Invoices views)
  getCollateral: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.view) query.append('view', params.view);
    if (params.search) query.append('search', params.search);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);
    return API.get(`/crm/collateral?${query.toString()}`);
  },

  // Company & Invoice Configuration
  getCompanySettings: async () => {
    return API.get('/crm/company-settings');
  },

  updateCompanySettings: async (data) => {
    return API.put('/crm/company-settings', data);
  },

  uploadSignatureImage: async (formData) => {
    return API.post('/crm/company-settings/signature', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  deleteSignatureImage: async () => {
    return API.delete('/crm/company-settings/signature');
  },

  // Single current quotation per opportunity
  getCurrentQuotation: async (oppId) => {
    return API.get(`/crm/opportunities/${oppId}/quotations/current`);
  },

  saveCurrentQuotation: async (oppId, data) => {
    return API.post(`/crm/opportunities/${oppId}/quotations/save-current`, data);
  },

  getQuotationEmailText: async (quotationId) => {
    return API.get(`/crm/quotations/${quotationId}/email-text`);
  },

  // Proforma Invoices
  previewProformaInvoice: async (data) => {
    return API.post('/crm/proforma-invoices/preview', data);
  },

  createProformaInvoice: async (data) => {
    return API.post('/crm/proforma-invoices', data);
  },

  updateProformaInvoice: async (piId, data) => {
    return API.put(`/crm/proforma-invoices/${piId}`, data);
  },

  createInvoiceRevision: async (piId, data) => {
    return API.post(`/crm/proforma-invoices/${piId}/revisions`, data);
  },

  getProformaInvoice: async (piId) => {
    return API.get(`/crm/proforma-invoices/${piId}`);
  },

  getOpportunityProformaInvoices: async (oppId) => {
    return API.get(`/crm/opportunities/${oppId}/proforma-invoices`);
  },

  getInvoiceHtmlUrl: (piId, revision = null) => {
    const base = API.defaults.baseURL || '/api/v1';
    const revParam = revision ? `?revision=${revision}` : '';
    return `${base}/crm/proforma-invoices/${piId}/html${revParam}`;
  },

  openPreviewInNewTab: (previewHtml) => {
    const previewWindow = window.open('', '_blank');
    if (previewWindow) {
      previewWindow.document.open();
      previewWindow.document.write(previewHtml);
      previewWindow.document.close();
    } else {
      alert('Please allow popups to open the preview in a new tab.');
    }
  }
};

export default invoiceService;
