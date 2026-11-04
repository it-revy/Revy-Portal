import os

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
service_path = os.path.join(root_dir, "frontend", "src", "services", "crmService.js")
with open(service_path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("\r\n", "\n")

target = """  removeCrmMembership: async (userId) => {
    return API.delete(`/crm/users/${userId}/membership`);
  }
};"""

replacement = """  removeCrmMembership: async (userId) => {
    return API.delete(`/crm/users/${userId}/membership`);
  },

  // =========================================================================
  // LEAD NURTURING & UNIFIED TIMELINE API METHODS
  // =========================================================================

  getLeadNurturing: async (leadId) => {
    return API.get(`/crm/leads/${leadId}/nurturing`);
  },

  getLeadTimeline: async (leadId, params = {}) => {
    const query = new URLSearchParams();
    if (params.sort) query.append('sort', params.sort);
    if (params.filter) query.append('filter', params.filter);
    return API.get(`/crm/leads/${leadId}/timeline?${query.toString()}`);
  },

  getLeadNextActivity: async (leadId) => {
    return API.get(`/crm/leads/${leadId}/next-activity`);
  },

  completeNurturingActivity: async (leadId, activityId, data) => {
    return API.post(`/crm/leads/${leadId}/nurturing/activities/${activityId}/complete`, data);
  },

  rescheduleNurturingActivity: async (leadId, activityId, data) => {
    return API.post(`/crm/leads/${leadId}/nurturing/activities/${activityId}/reschedule`, data);
  },

  skipNurturingActivity: async (leadId, activityId, data) => {
    return API.post(`/crm/leads/${leadId}/nurturing/activities/${activityId}/skip`, data);
  },

  recordCustomerResponse: async (leadId, data) => {
    return API.post(`/crm/leads/${leadId}/nurturing/customer-response`, data);
  },

  pauseNurturing: async (leadId, data = {}) => {
    return API.post(`/crm/leads/${leadId}/nurturing/pause`, data);
  },

  resumeNurturing: async (leadId, data = {}) => {
    return API.post(`/crm/leads/${leadId}/nurturing/resume`, data);
  },

  cancelNurturing: async (leadId, data) => {
    return API.post(`/crm/leads/${leadId}/nurturing/cancel`, data);
  }
};"""

assert target in c, "Target not found in crmService.js!"
c = c.replace(target, replacement)

with open(service_path, "w", encoding="utf-8") as f:
    f.write(c)

print("Updated frontend/src/services/crmService.js successfully")
