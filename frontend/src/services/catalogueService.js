import API from './api';

/**
 * Normalizes any API response or payload to guarantee a safe JavaScript Array.
 * Handles Axios responses, enveloped objects, and entity-specific array keys.
 */
export const normalizeArrayResponse = (response, fallbackKey = null) => {
  if (!response) return [];
  const payload = response?.data ?? response;

  if (Array.isArray(payload)) {
    return payload;
  }
  if (fallbackKey && Array.isArray(payload?.[fallbackKey])) {
    return payload[fallbackKey];
  }
  if (Array.isArray(payload?.subcategories)) {
    return payload.subcategories;
  }
  if (Array.isArray(payload?.categories)) {
    return payload.categories;
  }
  if (Array.isArray(payload?.services)) {
    return payload.services;
  }
  if (Array.isArray(payload?.packages)) {
    return payload.packages;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.data)) {
    return payload.data;
  }
  if (Array.isArray(payload?.billingUnits)) {
    return payload.billingUnits;
  }
  if (Array.isArray(payload?.reportingUnits)) {
    return payload.reportingUnits;
  }
  if (Array.isArray(payload?.sampleTypes)) {
    return payload.sampleTypes;
  }
  if (Array.isArray(payload?.testingMethods)) {
    return payload.testingMethods;
  }
  if (Array.isArray(payload?.currencies)) {
    return payload.currencies;
  }
  if (Array.isArray(payload?.taxConfigurations)) {
    return payload.taxConfigurations;
  }

  return [];
};

/**
 * Wraps list endpoint Axios responses to guarantee that res.data is an Array
 * while preserving envelope metadata (success, total, page, specific keys) for backwards compatibility.
 */
const wrapListResponse = (res, entityKey) => {
  const items = normalizeArrayResponse(res, entityKey);
  const dataArray = [...items];
  dataArray.success = res.data?.success ?? true;
  dataArray.total = res.data?.total ?? items.length;
  dataArray.page = res.data?.page ?? 1;
  dataArray.pageSize = res.data?.pageSize ?? items.length;
  if (entityKey) {
    dataArray[entityKey] = items;
  }
  dataArray.items = items;
  dataArray.data = items;

  return {
    ...res,
    data: dataArray,
    [entityKey]: items,
    items: items,
    total: res.data?.total ?? items.length,
    page: res.data?.page ?? 1,
    pageSize: res.data?.pageSize ?? items.length,
    success: res.data?.success ?? true,
    raw: res.data
  };
};

export const catalogueService = {
  // Normalization helper
  normalizeArray: normalizeArrayResponse,

  // =========================================================================
  // 1. CATEGORIES & SUBCATEGORIES
  // =========================================================================
  getCategories: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/categories?${query.toString()}`);
    return wrapListResponse(res, 'categories');
  },

  getCategoryById: async (id) => {
    const res = await API.get(`/crm/catalogue/categories/${id}`);
    const entity = res.data?.category || res.data?.data || res.data;
    return { ...res, data: entity, category: entity };
  },

  createCategory: async (data) => {
    const res = await API.post('/crm/catalogue/categories', data);
    const entity = res.data?.category || res.data?.data || res.data;
    return { ...res, data: entity, category: entity };
  },

  updateCategory: async (id, data) => {
    const res = await API.put(`/crm/catalogue/categories/${id}`, data);
    const entity = res.data?.category || res.data?.data || res.data;
    return { ...res, data: entity, category: entity };
  },

  deleteCategory: async (id) => {
    return API.delete(`/crm/catalogue/categories/${id}`);
  },

  getSubcategories: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.categoryId && params.categoryId !== 'ALL') query.append('category_id', params.categoryId);
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/subcategories?${query.toString()}`);
    return wrapListResponse(res, 'subcategories');
  },

  createSubcategory: async (data) => {
    const res = await API.post('/crm/catalogue/subcategories', data);
    const entity = res.data?.subcategory || res.data?.data || res.data;
    return { ...res, data: entity, subcategory: entity };
  },

  updateSubcategory: async (id, data) => {
    const res = await API.put(`/crm/catalogue/subcategories/${id}`, data);
    const entity = res.data?.subcategory || res.data?.data || res.data;
    return { ...res, data: entity, subcategory: entity };
  },

  deleteSubcategory: async (id) => {
    return API.delete(`/crm/catalogue/subcategories/${id}`);
  },

  // =========================================================================
  // 2. MASTER DATA (BILLING, REPORTING, SAMPLES, METHODS, CURRENCIES, TAX)
  // =========================================================================
  getBillingUnits: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/billing-units?${query.toString()}`);
    return wrapListResponse(res, 'billingUnits');
  },

  createBillingUnit: async (data) => {
    const res = await API.post('/crm/catalogue/billing-units', data);
    const entity = res.data?.billingUnit || res.data?.data || res.data;
    return { ...res, data: entity, billingUnit: entity };
  },

  updateBillingUnit: async (id, data) => {
    const res = await API.put(`/crm/catalogue/billing-units/${id}`, data);
    const entity = res.data?.billingUnit || res.data?.data || res.data;
    return { ...res, data: entity, billingUnit: entity };
  },

  getReportingUnits: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/reporting-units?${query.toString()}`);
    return wrapListResponse(res, 'reportingUnits');
  },

  createReportingUnit: async (data) => {
    const res = await API.post('/crm/catalogue/reporting-units', data);
    const entity = res.data?.reportingUnit || res.data?.data || res.data;
    return { ...res, data: entity, reportingUnit: entity };
  },

  updateReportingUnit: async (id, data) => {
    const res = await API.put(`/crm/catalogue/reporting-units/${id}`, data);
    const entity = res.data?.reportingUnit || res.data?.data || res.data;
    return { ...res, data: entity, reportingUnit: entity };
  },

  getSampleTypes: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/sample-types?${query.toString()}`);
    return wrapListResponse(res, 'sampleTypes');
  },

  createSampleType: async (data) => {
    const res = await API.post('/crm/catalogue/sample-types', data);
    const entity = res.data?.sampleType || res.data?.data || res.data;
    return { ...res, data: entity, sampleType: entity };
  },

  updateSampleType: async (id, data) => {
    const res = await API.put(`/crm/catalogue/sample-types/${id}`, data);
    const entity = res.data?.sampleType || res.data?.data || res.data;
    return { ...res, data: entity, sampleType: entity };
  },

  getTestingMethods: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/testing-methods?${query.toString()}`);
    return wrapListResponse(res, 'testingMethods');
  },

  createTestingMethod: async (data) => {
    const res = await API.post('/crm/catalogue/testing-methods', data);
    const entity = res.data?.testingMethod || res.data?.data || res.data;
    return { ...res, data: entity, testingMethod: entity };
  },

  updateTestingMethod: async (id, data) => {
    const res = await API.put(`/crm/catalogue/testing-methods/${id}`, data);
    const entity = res.data?.testingMethod || res.data?.data || res.data;
    return { ...res, data: entity, testingMethod: entity };
  },

  getCurrencies: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/currencies?${query.toString()}`);
    return wrapListResponse(res, 'currencies');
  },

  createCurrency: async (data) => {
    const res = await API.post('/crm/catalogue/currencies', data);
    const entity = res.data?.currency || res.data?.data || res.data;
    return { ...res, data: entity, currency: entity };
  },

  updateCurrency: async (id, data) => {
    const res = await API.put(`/crm/catalogue/currencies/${id}`, data);
    const entity = res.data?.currency || res.data?.data || res.data;
    return { ...res, data: entity, currency: entity };
  },

  getTaxConfigurations: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.includeInactive) query.append('include_inactive', 'true');
    const res = await API.get(`/crm/catalogue/tax-configurations?${query.toString()}`);
    return wrapListResponse(res, 'taxConfigurations');
  },

  createTaxConfiguration: async (data) => {
    const res = await API.post('/crm/catalogue/tax-configurations', data);
    const entity = res.data?.taxConfiguration || res.data?.data || res.data;
    return { ...res, data: entity, taxConfiguration: entity };
  },

  updateTaxConfiguration: async (id, data) => {
    const res = await API.put(`/crm/catalogue/tax-configurations/${id}`, data);
    const entity = res.data?.taxConfiguration || res.data?.data || res.data;
    return { ...res, data: entity, taxConfiguration: entity };
  },

  // =========================================================================
  // 3. SERVICES
  // =========================================================================
  getServices: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.categoryId && params.categoryId !== 'ALL') query.append('categoryId', params.categoryId);
    if (params.subcategoryId && params.subcategoryId !== 'ALL') query.append('subcategoryId', params.subcategoryId);
    if (params.search) query.append('search', params.search);
    if (params.isActive !== undefined && params.isActive !== 'ALL') query.append('isActive', params.isActive);
    if (params.isAddonEligible !== undefined) query.append('isAddonEligible', params.isAddonEligible);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('pageSize', params.pageSize);
    const res = await API.get(`/crm/catalogue/services?${query.toString()}`);
    return wrapListResponse(res, 'services');
  },

  getServiceById: async (id, params = {}) => {
    const query = new URLSearchParams();
    if (params.asOfDate) query.append('as_of_date', params.asOfDate);
    const res = await API.get(`/crm/catalogue/services/${id}?${query.toString()}`);
    const entity = res.data?.service || res.data?.data || res.data;
    return { ...res, data: entity, service: entity };
  },

  createService: async (data) => {
    const res = await API.post('/crm/catalogue/services', data);
    const entity = res.data?.service || res.data?.data || res.data;
    return { ...res, data: entity, service: entity };
  },

  updateService: async (id, data) => {
    const res = await API.put(`/crm/catalogue/services/${id}`, data);
    const entity = res.data?.service || res.data?.data || res.data;
    return { ...res, data: entity, service: entity };
  },

  deleteService: async (id) => {
    return API.delete(`/crm/catalogue/services/${id}`);
  },

  // =========================================================================
  // 4. PACKAGES & VERSIONS
  // =========================================================================
  getPackages: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.categoryId && params.categoryId !== 'ALL') query.append('categoryId', params.categoryId);
    if (params.search) query.append('search', params.search);
    if (params.isActive !== undefined && params.isActive !== 'ALL') query.append('isActive', params.isActive);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('pageSize', params.pageSize);
    const res = await API.get(`/crm/catalogue/packages?${query.toString()}`);
    return wrapListResponse(res, 'packages');
  },

  getPackageById: async (id) => {
    const res = await API.get(`/crm/catalogue/packages/${id}`);
    const entity = res.data?.package || res.data?.data || res.data;
    return { ...res, data: entity, package: entity };
  },

  createPackage: async (data) => {
    const res = await API.post('/crm/catalogue/packages', data);
    const entity = res.data?.package || res.data?.data || res.data;
    return { ...res, data: entity, package: entity };
  },

  updatePackage: async (id, data) => {
    const res = await API.put(`/crm/catalogue/packages/${id}`, data);
    const entity = res.data?.package || res.data?.data || res.data;
    return { ...res, data: entity, package: entity };
  },

  createPackageVersion: async (packageId, data) => {
    const res = await API.post(`/crm/catalogue/packages/${packageId}/versions`, data);
    const entity = res.data?.version || res.data?.data || res.data;
    return { ...res, data: entity, version: entity };
  },

  // =========================================================================
  // 5. QUOTATION ITEMS
  // =========================================================================
  getQuotationItems: async (quotationId) => {
    const res = await API.get(`/crm/catalogue/quotations/${quotationId}/items`);
    return wrapListResponse(res, 'items');
  },

  addQuotationItem: async (quotationId, data) => {
    const res = await API.post(`/crm/catalogue/quotations/${quotationId}/items`, data);
    const entity = res.data?.item || res.data?.data || res.data;
    return { ...res, data: entity, item: entity };
  },

  removeQuotationItem: async (quotationId, itemId) => {
    return API.delete(`/crm/catalogue/quotations/${quotationId}/items/${itemId}`);
  },

  deleteQuotationItem: async (quotationId, itemId) => {
    return API.delete(`/crm/catalogue/quotations/${quotationId}/items/${itemId}`);
  }
};

export default catalogueService;
