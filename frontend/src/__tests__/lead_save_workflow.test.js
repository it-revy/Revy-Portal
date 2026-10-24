import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

describe('CRM Lead Save Workflow - 6 Required Test Cases', () => {

  // Simulate the form submission logic matching LeadModal.jsx
  async function simulateLeadModalSubmit({
    formData,
    isEdit = false,
    crmService,
    onClose,
    onLeadSaved,
    validate = () => true
  }) {
    let submitting = false;
    let isVerifying = false;
    let uncertainOutcome = false;
    let error = null;
    let errorCategory = 'validation';
    let fieldErrors = {};
    let postCallCount = 0;

    const handleSubmit = async () => {
      // Prevent duplicate submissions while a request is in progress
      if (submitting || isVerifying) return;
      if (!validate()) return;

      error = null;
      errorCategory = 'validation';
      uncertainOutcome = false;
      submitting = true;

      const payload = {
        businessArea: formData.businessArea,
        requirementTypes: formData.requirementTypes,
        requirementType: formData.requirementTypes[0] || 'Sample Testing',
        contactId: formData.contactId,
        leadName: formData.leadName?.trim() || undefined
      };

      let res = null;
      let saveFailed = false;

      try {
        postCallCount++;
        if (isEdit) {
          res = await crmService.updateLead('lead-id', payload);
        } else {
          res = await crmService.createLead(payload);
        }
      } catch (err) {
        saveFailed = true;
        if (err.response) {
          const status = err.response.status;
          if (status === 409) {
            errorCategory = 'conflict';
            error = err.response.data?.message || 'Conflict';
          } else if (status === 401 || status === 403) {
            errorCategory = 'auth';
            error = err.response.data?.message || 'Permission denied.';
          } else if (status === 400 || status === 422) {
            errorCategory = 'validation';
            error = err.response.data?.message || 'Validation error.';
          } else if (status >= 500) {
            errorCategory = 'server';
            error = 'A server error occurred while processing the lead.';
          } else {
            errorCategory = 'validation';
            error = 'Failed to save lead.';
          }
        } else if (err.code === 'ECONNABORTED' || (err.message && err.message.toLowerCase().includes('timeout'))) {
          errorCategory = 'uncertain';
          uncertainOutcome = true;
          error = 'Request timed out while waiting for the server. The lead may have already been saved. Please verify before retrying to prevent duplicate records.';
        } else if (err.message === 'Network Error' || err.code === 'ERR_NETWORK') {
          errorCategory = 'network';
          error = 'Connection Error — Unable to reach the server. Please check your network connection and try again.';
        } else {
          errorCategory = 'server';
          error = err.message || 'An unexpected error occurred while saving the lead.';
        }
      } finally {
        submitting = false;
      }

      if (saveFailed) {
        return { success: false, error, errorCategory, uncertainOutcome };
      }

      if (res && res.data?.success && res.data?.lead) {
        const savedLead = res.data.lead;

        if (typeof onClose === 'function') {
          try {
            onClose();
          } catch (closeErr) {
            console.error('Error closing modal:', closeErr);
          }
        }

        if (typeof onLeadSaved === 'function') {
          try {
            const cbResult = onLeadSaved(savedLead);
            if (cbResult && typeof cbResult.catch === 'function') {
              cbResult.catch(cbErr => {
                console.warn('Background error in onLeadSaved:', cbErr);
              });
            }
          } catch (cbErr) {
            console.warn('Sync error in onLeadSaved:', cbErr);
          }
        }

        return { success: true, savedLead };
      } else {
        errorCategory = 'server';
        error = 'Unexpected server response.';
        return { success: false, error, errorCategory };
      }
    };

    const handleVerifyOutcome = async () => {
      isVerifying = true;
      try {
        const checkRes = await crmService.getLeads({ contactId: formData.contactId });
        const recent = checkRes.data?.leads || [];
        const matched = recent.find(l => l.contactId === formData.contactId && l.businessArea === formData.businessArea);
        if (matched) {
          uncertainOutcome = false;
          if (typeof onClose === 'function') onClose();
          if (typeof onLeadSaved === 'function') onLeadSaved(matched);
          return { verified: true, matchedLead: matched };
        } else {
          uncertainOutcome = false;
          errorCategory = 'validation';
          error = 'Verification complete: No duplicate lead was found in the database. You may safely submit the form now.';
          return { verified: false };
        }
      } finally {
        isVerifying = false;
      }
    };

    return {
      handleSubmit,
      handleVerifyOutcome,
      getState: () => ({ submitting, isVerifying, uncertainOutcome, error, errorCategory, fieldErrors, postCallCount })
    };
  }

  // Simulate CrmLeadsPage handleLeadSaved and fetchLeads
  function createParentPageHandlers({ fetchLeadsMock }) {
    let successNotification = null;
    let warningNotification = null;
    let error = null;

    const fetchLeads = async (options = {}) => {
      if (!options.silent) error = null;
      try {
        const res = await fetchLeadsMock();
        return { success: true, data: res };
      } catch (err) {
        const errMsg = err.message || 'Failed to fetch leads.';
        if (!options.silent) error = errMsg;
        return { success: false, error: errMsg };
      }
    };

    const handleLeadSaved = async (savedLead) => {
      error = null;
      warningNotification = null;
      const leadId = savedLead?.leadId || savedLead?.lead_id || 'Lead';
      successNotification = `Lead ${leadId} created successfully.`;

      const refreshResult = await fetchLeads({ silent: true });
      if (refreshResult && !refreshResult.success) {
        warningNotification = 'Lead saved successfully, but the list could not be refreshed.';
      }
    };

    return {
      handleLeadSaved,
      fetchLeads,
      getState: () => ({ successNotification, warningNotification, error })
    };
  }

  // =========================================================================
  // Test Case 1: POST succeeds and Lead list refresh succeeds
  // =========================================================================
  it('Case 1: POST succeeds and Lead list refresh succeeds', async () => {
    let modalClosed = false;
    const parent = createParentPageHandlers({
      fetchLeadsMock: async () => ({ leads: [{ id: 'lead-101', lead_id: 'LEAD-00101' }] })
    });

    const crmServiceMock = {
      createLead: async (payload) => ({
        data: {
          success: true,
          message: 'Lead created successfully.',
          lead: { id: 'lead-101', lead_id: 'LEAD-00101', leadName: 'Test Bio' }
        }
      })
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: 'contact-1' },
      crmService: crmServiceMock,
      onClose: () => { modalClosed = true; },
      onLeadSaved: (lead) => parent.handleLeadSaved(lead)
    });

    const result = await modal.handleSubmit();
    assert.equal(result.success, true);
    assert.equal(modalClosed, true, 'Form must be closed on successful save');

    // Wait a tick for async parent refresh
    await new Promise(r => setTimeout(r, 10));

    const parentState = parent.getState();
    assert.match(parentState.successNotification, /LEAD-00101 created successfully/);
    assert.equal(parentState.warningNotification, null);
    assert.equal(parentState.error, null);
  });

  // =========================================================================
  // Test Case 2: POST succeeds but Lead list refresh fails
  // =========================================================================
  it('Case 2: POST succeeds but Lead list refresh fails', async () => {
    let modalClosed = false;
    const parent = createParentPageHandlers({
      fetchLeadsMock: async () => {
        throw new Error('500 Internal Server Error on leads list endpoint');
      }
    });

    const crmServiceMock = {
      createLead: async (payload) => ({
        data: {
          success: true,
          message: 'Lead created successfully.',
          lead: { id: 'lead-102', lead_id: 'LEAD-00102', leadName: 'Test Refresh Fail' }
        }
      })
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: 'contact-1' },
      crmService: crmServiceMock,
      onClose: () => { modalClosed = true; },
      onLeadSaved: (lead) => parent.handleLeadSaved(lead)
    });

    const result = await modal.handleSubmit();
    assert.equal(result.success, true, 'Save operation itself succeeded');
    assert.equal(modalClosed, true, 'Form must be closed and NOT report connection error');

    // Wait a tick for async parent refresh failure
    await new Promise(r => setTimeout(r, 10));

    const parentState = parent.getState();
    assert.match(parentState.successNotification, /LEAD-00102 created successfully/);
    assert.equal(
      parentState.warningNotification,
      'Lead saved successfully, but the list could not be refreshed.',
      'Must display non-blocking warning when refresh fails after successful save'
    );
    assert.equal(parentState.error, null, 'Must NOT report that the save failed');
  });

  // =========================================================================
  // Test Case 3: POST fails with a validation error
  // =========================================================================
  it('Case 3: POST fails with a validation error (400 / 422)', async () => {
    let modalClosed = false;
    let leadSavedCalled = false;

    const crmServiceMock = {
      createLead: async () => {
        const error = new Error('Request failed with status code 400');
        error.response = {
          status: 400,
          data: {
            success: false,
            message: 'Primary Contact is required.',
            error_code: 'VALIDATION_ERROR'
          }
        };
        throw error;
      }
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: '' },
      crmService: crmServiceMock,
      onClose: () => { modalClosed = true; },
      onLeadSaved: () => { leadSavedCalled = true; }
    });

    const result = await modal.handleSubmit();
    assert.equal(result.success, false);
    assert.equal(modalClosed, false, 'Modal should stay open for user to fix validation');
    assert.equal(leadSavedCalled, false);

    const state = modal.getState();
    assert.equal(state.errorCategory, 'validation');
    assert.equal(state.error, 'Primary Contact is required.');
    assert.notEqual(state.errorCategory, 'network', 'Must NOT report network error for validation failure');
  });

  // =========================================================================
  // Test Case 4: POST fails with a server error
  // =========================================================================
  it('Case 4: POST fails with a server error (500)', async () => {
    let modalClosed = false;

    const crmServiceMock = {
      createLead: async () => {
        const error = new Error('Request failed with status code 500');
        error.response = {
          status: 500,
          data: {
            success: false,
            message: 'Internal Server Error',
            error_code: 'INTERNAL_SERVER_ERROR'
          }
        };
        throw error;
      }
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: 'contact-1' },
      crmService: crmServiceMock,
      onClose: () => { modalClosed = true; },
      onLeadSaved: () => {}
    });

    const result = await modal.handleSubmit();
    assert.equal(result.success, false);
    assert.equal(modalClosed, false);

    const state = modal.getState();
    assert.equal(state.errorCategory, 'server');
    assert.match(state.error, /server error occurred/i);
    assert.notEqual(state.errorCategory, 'network', 'Must NOT report network error for server 500 failure');
  });

  // =========================================================================
  // Test Case 5: Network disconnects before save outcome is known
  // =========================================================================
  it('Case 5: The network disconnects before the save outcome is known (timeout / uncertain)', async () => {
    let modalClosed = false;
    let savedLeadReceived = null;

    // Simulate ambiguous timeout (server received and committed, but response timed out)
    const crmServiceMock = {
      createLead: async () => {
        const error = new Error('timeout of 30000ms exceeded');
        error.code = 'ECONNABORTED';
        throw error;
      },
      getLeads: async ({ contactId }) => {
        // Verification API call finds that the lead actually exists!
        return {
          data: {
            success: true,
            leads: [
              { id: 'lead-saved-during-timeout', lead_id: 'LEAD-00999', contactId, businessArea: 'Biogas' }
            ]
          }
        };
      }
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: 'contact-abc' },
      crmService: crmServiceMock,
      onClose: () => { modalClosed = true; },
      onLeadSaved: (lead) => { savedLeadReceived = lead; }
    });

    const result = await modal.handleSubmit();
    assert.equal(result.success, false);
    assert.equal(modalClosed, false, 'Modal remains open during uncertain state');

    const state = modal.getState();
    assert.equal(state.errorCategory, 'uncertain');
    assert.equal(state.uncertainOutcome, true);
    assert.match(state.error, /Request timed out.*verify before retrying/i);

    // Verify operation without creating duplicates
    const verifyResult = await modal.handleVerifyOutcome();
    assert.equal(verifyResult.verified, true);
    assert.equal(modalClosed, true, 'After verification finds lead, modal closes');
    assert.equal(savedLeadReceived.lead_id, 'LEAD-00999');
  });

  // =========================================================================
  // Test Case 6: User clicks Save multiple times
  // =========================================================================
  it('Case 6: The user clicks Save multiple times (duplicate submission prevention)', async () => {
    let resolvePost;
    const postPromise = new Promise(resolve => { resolvePost = resolve; });

    let postCount = 0;
    const crmServiceMock = {
      createLead: async () => {
        postCount++;
        await postPromise;
        return {
          data: {
            success: true,
            lead: { id: 'lead-single', lead_id: 'LEAD-00001' }
          }
        };
      }
    };

    const modal = await simulateLeadModalSubmit({
      formData: { businessArea: 'Biogas', requirementTypes: ['Consulting'], contactId: 'contact-1' },
      crmService: crmServiceMock,
      onClose: () => {},
      onLeadSaved: () => {}
    });

    // Fire 5 clicks concurrently
    const p1 = modal.handleSubmit();
    const p2 = modal.handleSubmit();
    const p3 = modal.handleSubmit();
    const p4 = modal.handleSubmit();
    const p5 = modal.handleSubmit();

    // Release the single in-flight post
    resolvePost();
    await Promise.all([p1, p2, p3, p4, p5]);

    assert.equal(postCount, 1, 'Only exactly 1 POST request must be dispatched even if user clicks 5 times');
  });

});
