import API from './api';

export const crmService = {
  // =========================================================================
  // 1. DASHBOARD METRICS
  // =========================================================================
  getDashboardMetrics: async () => {
    return API.get('/crm/dashboard/metrics');
  },

  // =========================================================================
  // 2. LEADS
  // =========================================================================
  getLeads: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.view) query.append('view', params.view);
    if (params.search) query.append('search', params.search);
    if (params.businessArea && params.businessArea !== 'ALL') query.append('businessArea', params.businessArea);
    if (params.requirementType && params.requirementType !== 'ALL') query.append('requirementType', params.requirementType);
    if (params.lifecycleStatus && params.lifecycleStatus !== 'ALL') query.append('lifecycleStatus', params.lifecycleStatus);
    if (params.assignedToUserId) query.append('assignedToUserId', params.assignedToUserId);
    if (params.accountId) query.append('accountId', params.accountId);
    if (params.sortBy) query.append('sortBy', params.sortBy);
    if (params.sortOrder) query.append('sortOrder', params.sortOrder);
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('pageSize', params.pageSize);

    return API.get(`/crm/leads?${query.toString()}`);
  },

  getLeadById: async (id) => {
    return API.get(`/crm/leads/${id}`);
  },

  createLead: async (data) => {
    return API.post('/crm/leads', data);
  },

  updateLead: async (id, data) => {
    return API.put(`/crm/leads/${id}`, data);
  },

  transitionLeadStatus: async (id, data) => {
    return API.post(`/crm/leads/${id}/status`, data);
  },

  getLeadQualificationMatches: async (leadId) => {
    return API.get(`/crm/leads/${leadId}/qualification-matches`);
  },

  qualifyLead: async (leadId, data) => {
    return API.post(`/crm/leads/${leadId}/qualify`, data);
  },

  // =========================================================================
  // OPPORTUNITIES & PIPELINE (PHASE 4A)
  // =========================================================================
  getOpportunities: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.accountId) query.append('accountId', params.accountId);
    if (params.status) query.append('status', params.status);
    if (params.stage) query.append('stage', params.stage);
    if (params.businessArea) query.append('businessArea', params.businessArea);
    if (params.assignedToUserId) query.append('assignedToUserId', params.assignedToUserId);
    if (params.view) query.append('view', params.view);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);
    return API.get(`/crm/opportunities?${query.toString()}`);
  },

  getPipelineSummary: async () => {
    return API.get('/crm/opportunities/pipeline-summary');
  },

  getOpportunityById: async (id) => {
    return API.get(`/crm/opportunities/${id}`);
  },

  updateOpportunity: async (id, data) => {
    return API.put(`/crm/opportunities/${id}`, data);
  },

  transitionOpportunityStage: async (id, data) => {
    return API.post(`/crm/opportunities/${id}/stage`, data);
  },

  // =========================================================================
  // REQUIREMENT ROUTING (PHASE 4B)
  // =========================================================================
  getOpportunityWorkstreams: async (id) => {
    return API.get(`/crm/opportunities/${id}/workstreams`);
  },

  routeOpportunityRequirements: async (id, data = {}) => {
    return API.post(`/crm/opportunities/${id}/route-requirements`, data);
  },

  updateOpportunityRequirements: async (id, data) => {
    return API.put(`/crm/opportunities/${id}/requirements`, data);
  },

  // =========================================================================
  // MILESTONE INTEGRATION (PHASE 4C)
  // =========================================================================
  getOpportunityMilestones: async (id, params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.assignedToUserId) query.append('assignedToUserId', params.assignedToUserId);
    return API.get(`/crm/opportunities/${id}/milestones?${query.toString()}`);
  },

  createOpportunityMilestone: async (id, data) => {
    return API.post(`/crm/opportunities/${id}/milestones`, data);
  },

  getUpcomingMilestones: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.days) query.append('days', params.days);
    if (params.assignedToUserId) query.append('assignedToUserId', params.assignedToUserId);
    return API.get(`/crm/milestones/upcoming?${query.toString()}`);
  },

  getMilestoneById: async (id) => {
    return API.get(`/crm/milestones/${id}`);
  },

  updateMilestone: async (id, data) => {
    return API.put(`/crm/milestones/${id}`, data);
  },

  transitionMilestoneStatus: async (id, data) => {
    return API.post(`/crm/milestones/${id}/status`, data);
  },

  deleteMilestone: async (id) => {
    return API.delete(`/crm/milestones/${id}`);
  },

  // =========================================================================
  // 3. COMMUNICATIONS
  // =========================================================================
  getLeadCommunications: async (leadId) => {
    return API.get(`/crm/leads/${leadId}/communications`);
  },

  addLeadCommunication: async (leadId, data) => {
    return API.post(`/crm/leads/${leadId}/communications`, data);
  },

  // =========================================================================
  // 4. ACCOUNTS & CONTACTS LOOKUP / QUICK-CREATE
  // =========================================================================
  getAccounts: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);
    return API.get(`/crm/accounts?${query.toString()}`);
  },

  getAccountById: async (id) => {
    return API.get(`/crm/accounts/${id}`);
  },

  createAccount: async (data) => {
    return API.post('/crm/accounts', data);
  },

  updateAccount: async (id, data) => {
    return API.put(`/crm/accounts/${id}`, data);
  },

  getContacts: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.accountId) query.append('accountId', params.accountId);
    if (params.includeUnassigned !== undefined && params.includeUnassigned !== null) {
      query.append('includeUnassigned', params.includeUnassigned);
    }
    if (params.limit) query.append('limit', params.limit);
    if (params.offset) query.append('offset', params.offset);
    return API.get(`/crm/contacts?${query.toString()}`);
  },

  getContactById: async (id) => {
    return API.get(`/crm/contacts/${id}`);
  },

  createContact: async (data) => {
    return API.post('/crm/contacts', data);
  },

  updateContact: async (id, data) => {
    return API.put(`/crm/contacts/${id}`, data);
  },

  getAccountMatches: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.name) query.append('name', params.name);
    if (params.website) query.append('website', params.website);
    if (params.email) query.append('email', params.email);
    if (params.phone) query.append('phone', params.phone);
    if (params.excludeId) query.append('excludeId', params.excludeId);
    if (params.limit) query.append('limit', params.limit);
    return API.get(`/crm/accounts/matches?${query.toString()}`);
  },

  getContactMatches: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.name) query.append('name', params.name);
    if (params.email) query.append('email', params.email);
    if (params.mobileNumber) query.append('mobileNumber', params.mobileNumber);
    if (params.accountId) query.append('accountId', params.accountId);
    if (params.excludeId) query.append('excludeId', params.excludeId);
    if (params.limit) query.append('limit', params.limit);
    return API.get(`/crm/contacts/matches?${query.toString()}`);
  },

  getEligibleAssignees: async () => {
    return API.get('/crm/assignees');
  },

  // =========================================================================
  // 5. CRM USER HUB (ADMIN ONLY)
  // =========================================================================
  getCrmUsers: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.crmAccess !== undefined && params.crmAccess !== null) query.append('crmAccess', params.crmAccess);
    if (params.roleCode) query.append('roleCode', params.roleCode);
    return API.get(`/crm/users?${query.toString()}`);
  },

  getCrmRoles: async () => {
    return API.get('/crm/roles');
  },

  setUserCrmAccess: async (userId, data) => {
    return API.post(`/crm/users/${userId}/access`, data);
  },

  setUserCrmRole: async (userId, data) => {
    return API.put(`/crm/users/${userId}/role`, data);
  },

  getAvailableCentralUsers: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    return API.get(`/crm/available-users?${query.toString()}`);
  },

  assignUserToCrm: async (data) => {
    return API.post('/crm/users/assign', data);
  },

  getCrmUserDetails: async (userId) => {
    return API.get(`/crm/users/${userId}`);
  },

  removeCrmMembership: async (userId) => {
    return API.delete(`/crm/users/${userId}/membership`);
  }
};

export default crmService;
