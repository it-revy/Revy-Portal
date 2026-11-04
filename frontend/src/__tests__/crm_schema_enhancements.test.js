import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

describe('CRM Schema Enhancements & Workflow Verification Tests', () => {

  it('Verifies crmService.js exports unqualifyLead endpoint', () => {
    const serviceContent = fs.readFileSync('frontend/src/services/crmService.js', 'utf8');
    assert.match(serviceContent, /unqualifyLead:\s*async\s*\([^)]*\)\s*=>/);
    assert.match(serviceContent, /\/crm\/leads\/\$\{leadId\}\/unqualify/);
  });

  it('Verifies CrmLeadDetailPage has removed Add Opportunity button and modal', () => {
    const detailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');

    // "Add Opportunity" button in PageHeader actions must NOT be present
    assert.doesNotMatch(detailContent, new RegExp('<' + 'Button[^>]*>\\s*Add Opportunity\\s*<\\/Button>'));

    // "Add Opportunity" button above table must NOT be present
    assert.doesNotMatch(detailContent, /<span>Add Opportunity<\/span>/);

    // Add Opportunity modal state must NOT be present
    assert.doesNotMatch(detailContent, /isAddOppModalOpen/);
    assert.doesNotMatch(detailContent, /handleCreateOpportunity/);
  });

  it('Verifies CrmLeadDetailPage implements Unqualify Lead workflow', () => {
    const detailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');

    // Unqualify button
    assert.match(detailContent, /Unqualify/);
    assert.match(detailContent, /setIsUnqualifyModalOpen\(true\)/);

    // Unqualify state and handler
    assert.match(detailContent, /isUnqualifyModalOpen/);
    assert.match(detailContent, /disqualificationReason/);
    assert.match(detailContent, /handleUnqualifyLead/);
    assert.match(detailContent, /crmService\.unqualifyLead/);

    // Disqualification reason banner
    assert.match(detailContent, /lead\.disqualificationReason/);
    assert.match(detailContent, /Lead Disqualified/);
  });

  it('Verifies CrmAccountsPage supports enhanced account schema fields', () => {
    const accContent = fs.readFileSync('frontend/src/pages/CrmAccountsPage.jsx', 'utf8');

    // Form state & payload
    assert.match(accContent, /businessArea:\s*modalFormData\.businessArea/);
    assert.match(accContent, /parentAccountId:\s*modalFormData\.parentAccountId/);
    assert.match(accContent, /gstNumber:\s*modalFormData\.gstNumber/);
    assert.match(accContent, /panNumber:\s*modalFormData\.panNumber/);
    assert.match(accContent, /billingAddress:\s*modalFormData\.billingAddress/);
    assert.match(accContent, /shippingAddress:\s*modalFormData\.shippingAddress/);
    assert.match(accContent, /city:\s*modalFormData\.city/);
    assert.match(accContent, /state:\s*modalFormData\.state/);
    assert.match(accContent, /country:\s*modalFormData\.country/);

    // Business Area dropdown options
    assert.match(accContent, /<option value="Biogas">Biogas<\/option>/);
    assert.match(accContent, /<option value="WWT">WWT \(Wastewater Treatment\)<\/option>/);

    // Detail drawer metadata display
    assert.match(accContent, /selectedAccountDetail\.businessArea/);
    assert.match(accContent, /selectedAccountDetail\.parentAccount/);
    assert.match(accContent, /selectedAccountDetail\.gstNumber/);
  });

  it('Verifies CrmContactsPage supports auto-generated full name and primary contact fields', () => {
    const conContent = fs.readFileSync('frontend/src/pages/CrmContactsPage.jsx', 'utf8');

    // Form state contains firstName, lastName, whatsappNumber, isPrimary
    assert.match(conContent, /firstName:\s*''/);
    assert.match(conContent, /lastName:\s*''/);
    assert.match(conContent, /whatsappNumber:\s*''/);
    assert.match(conContent, /isPrimary:\s*false/);

    // Auto-computed full name calculation
    assert.match(conContent, /\$\{fn\}\s*\$\{ln\}/);
    assert.match(conContent, /Auto-computed from First \+ Last Name/);

    // Primary Contact indicator in table and drawer
    assert.match(conContent, /Primary/);
    assert.match(conContent, /c\.isPrimary/);
    assert.match(conContent, /selectedContactDetail\.isPrimary/);
    assert.match(conContent, /selectedContactDetail\.whatsappNumber/);
  });

  it('Verifies OpportunityStageModal enforces mandatory wonReason and displays it in details', () => {
    const stageContent = fs.readFileSync('frontend/src/modules/crm/components/OpportunityStageModal.jsx', 'utf8');
    const detailContent = fs.readFileSync('frontend/src/modules/crm/components/OpportunityDetailModal.jsx', 'utf8');

    // Stage modal wonReason state and quick pills
    assert.match(stageContent, /wonReason/);
    assert.match(stageContent, /QUICK_WON_REASONS/);
    assert.match(stageContent, /Please provide a won reason when marking an opportunity as Won/);
    assert.match(stageContent, /payload\.wonReason = wonReason\.trim\(\)/);

    // Detail modal displays wonReason when Won
    assert.match(detailContent, /opportunity\.status === 'Won' && opportunity\.wonReason/);
    assert.match(detailContent, /Won Reason & Commercial Rationale/);
    assert.match(detailContent, /opportunity\.wonReason/);
  });

});
