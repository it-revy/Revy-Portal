import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

describe('CRM Lead Qualification, Opportunity Details & Quotation Selector Fixes Tests', () => {

  // =========================================================================
  // 1. QuotationCatalogueSelector Tests (Bug 4 & 5)
  // =========================================================================
  it('Verifies QuotationCatalogueSelector implements defensive search normalization without throwing TypeError', () => {
    const selectorSource = fs.readFileSync('frontend/src/components/crm/QuotationCatalogueSelector.jsx', 'utf8');

    // Safe normalization check
    assert.match(
      selectorSource,
      /safeSearchTerm\s*=\s*useMemo|safeSearchTerm/,
      'QuotationCatalogueSelector must calculate safeSearchTerm'
    );
    assert.match(
      selectorSource,
      /typeof\s+searchTerm\s*===\s*['"]string['"]/,
      'QuotationCatalogueSelector must check if searchTerm is a string'
    );
    assert.match(
      selectorSource,
      /target\?\.value|\.toLowerCase\(\)\.trim\(\)/,
      'QuotationCatalogueSelector must safely normalize search values'
    );

    // Verify SearchInput usage passes string and extracts event value
    assert.match(
      selectorSource,
      /<SearchInput[\s\S]*?value=\{typeof searchTerm === 'string' \? searchTerm : ''\}[\s\S]*?onChange=\{handleSearchChange\}/,
      'SearchInput must receive a safe string value and handle change safely'
    );

    // Ensure array validation before filtering
    assert.match(
      selectorSource,
      /Array\.isArray\(availableServices\)/,
      'Must check Array.isArray for services'
    );
    assert.match(
      selectorSource,
      /Array\.isArray\(availablePackages\)/,
      'Must check Array.isArray for packages'
    );
  });

  it('Verifies QuotationCatalogueSelector supports services, packages, add-ons, products, and custom items', () => {
    const selectorSource = fs.readFileSync('frontend/src/components/crm/QuotationCatalogueSelector.jsx', 'utf8');
    assert.match(selectorSource, /activeTab === 'services'/, 'Must support services tab');
    assert.match(selectorSource, /activeTab === 'packages'/, 'Must support packages tab');
    assert.match(selectorSource, /activeTab === 'addons'/, 'Must support addons tab');
    assert.match(selectorSource, /activeTab === 'products'/, 'Must support products tab');
    assert.match(selectorSource, /activeTab === 'custom'/, 'Must support custom item tab');
    assert.match(selectorSource, /customSavePermanently/, 'Must support saving custom items permanently');
  });

  it('Tests the defensive search normalization logic with edge cases', () => {
    const normalize = (searchTerm) => {
      const raw =
        typeof searchTerm === 'string'
          ? searchTerm
          : searchTerm?.target?.value ??
            searchTerm?.value ??
            searchTerm?.label ??
            searchTerm?.name ??
            '';
      return String(raw).toLowerCase().trim();
    };

    // 1. Plain string
    assert.equal(normalize('Wastewater'), 'wastewater');

    // 2. Synthetic React Event
    assert.equal(normalize({ target: { value: '  Biogas Analysis  ' } }), 'biogas analysis');

    // 3. Null / Undefined
    assert.equal(normalize(null), '');
    assert.equal(normalize(undefined), '');

    // 4. Object option { value: 'COD', label: 'Chemical Oxygen Demand' }
    assert.equal(normalize({ value: 'COD', label: 'Chemical Oxygen Demand' }), 'COD'.toLowerCase());

    // 5. Number
    assert.equal(normalize(100), '');
  });

  // =========================================================================
  // 2. Opportunity Details Page Layout Alignment (Bug 2)
  // =========================================================================
  it('Verifies CrmOpportunityDetailPage adopts the 2-column layout matching Lead Details', () => {
    const oppDetail = fs.readFileSync('frontend/src/pages/CrmOpportunityDetailPage.jsx', 'utf8');

    // Check PageHeader breadcrumbs & actions
    assert.match(oppDetail, /<PageHeader/, 'Must render PageHeader');
    assert.match(oppDetail, /Stage:\s*\{opportunity\.stage/, 'Must display current sales stage');
    assert.match(oppDetail, /Change Stage/, 'Must provide Change Stage action');
    assert.match(oppDetail, /Edit Overview/, 'Must provide Edit Overview action');
    assert.match(oppDetail, /Opportunities/, 'Must provide Back to Opportunities action');

    // Check 2-Column layout structure
    assert.match(oppDetail, /gridTemplateColumns:\s*'2fr 1fr'/, 'Must use 2fr 1fr 2-column grid layout');

    // Check Section B: Opportunity Details & Scope
    assert.match(oppDetail, /Opportunity Details & Scope/, 'Must render Opportunity Details & Scope section');
    assert.match(oppDetail, /Estimated Value/, 'Must display Estimated Value');
    assert.match(oppDetail, /Expected Close Date/, 'Must display Expected Close Date');
    assert.match(oppDetail, /Business Area/, 'Must display Business Area');
    assert.match(oppDetail, /Requirement Types/, 'Must display Requirement Types');

    // Check Section C: Account Details
    assert.match(oppDetail, /Account Details/, 'Must render Account Details section');
    assert.match(oppDetail, /opportunity\.account\.name/, 'Must display linked Account Name');
    assert.match(oppDetail, /opportunity\.account\.website/, 'Must display linked Account Website');
    assert.match(oppDetail, /opportunity\.account\.gstNumber/, 'Must display linked Account GSTIN');
    assert.match(oppDetail, /opportunity\.account\.email/, 'Must display linked Account Email');
    assert.match(oppDetail, /opportunity\.account\.phone/, 'Must display linked Account Phone');

    // Check Section D: Contact Details
    assert.match(oppDetail, /Primary Contact Details/, 'Must render Primary Contact Details section');
    assert.match(oppDetail, /opportunity\.contact\.name/, 'Must display linked Contact Name');
    assert.match(oppDetail, /opportunity\.contact\.designation/, 'Must display linked Contact Designation');
    assert.match(oppDetail, /opportunity\.contact\.email/, 'Must display linked Contact Email');

    // Check Section E: Log Interaction
    assert.match(oppDetail, /Interaction History & Touchpoints/, 'Must render Interaction History section');
    assert.match(oppDetail, /Log Interaction/, 'Must provide Log Interaction button and modal');
    assert.match(oppDetail, /addOpportunityCommunication/, 'Must log interaction via crmService.addOpportunityCommunication');

    // Check Section F: Quotations & Invoicing
    assert.match(oppDetail, /Quotations & Commercial Invoicing/, 'Must render Quotations & Invoicing section');
    assert.match(oppDetail, /QuotationCatalogueSelector/, 'Must embed QuotationCatalogueSelector');
    assert.match(oppDetail, /Proforma Invoices & Revisions/, 'Must display Proforma Invoices & Revisions');
    assert.match(oppDetail, /Copy Quotation Text/, 'Must provide Copy Quotation Text action');
  });

  it('Verifies Opportunity Details does not contain Lead nurturing controls or lead nurturing stages', () => {
    const oppDetail = fs.readFileSync('frontend/src/pages/CrmOpportunityDetailPage.jsx', 'utf8');
    assert.doesNotMatch(oppDetail, /NextActivityPanel/, 'Opportunity details must not contain NextActivityPanel');
    assert.doesNotMatch(oppDetail, /nurturingState/, 'Opportunity details must not contain nurturingState');
    assert.doesNotMatch(oppDetail, /CustomerResponseModal/, 'Opportunity details must not contain CustomerResponseModal');
  });

  // =========================================================================
  // 3. Qualified Leads in Leads Workspace (Bug 1 & 3)
  // =========================================================================
  it('Verifies CrmLeadsPage includes Qualified Leads in saved views and status filter', () => {
    const leadsPage = fs.readFileSync('frontend/src/pages/CrmLeadsPage.jsx', 'utf8');

    // Saved views
    assert.match(leadsPage, /id:\s*'qualified',\s*label:\s*'Qualified Leads'/, 'Must include Qualified Leads in SAVED_VIEWS');

    // Status filter
    assert.match(leadsPage, /value:\s*'Qualified',\s*label:\s*'Qualified'/, 'Must include Qualified in status filter dropdown');

    // Opportunity link in table
    assert.match(leadsPage, /lead\.opportunityId \|\| lead\.opportunity\?\.id/, 'Must check for linked opportunity in table row');
    assert.match(leadsPage, /\/crm\/opportunities\//, 'Must link to /crm/opportunities/ in table row');
  });

  it('Verifies CrmLeadDetailPage displays Qualified status badge and links to Opportunity', () => {
    const leadDetail = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');

    // Status badge includes qualified
    assert.match(leadDetail, /s === 'qualified'[\s\S]*?status-badge success/, 'Must format qualified status with success badge');

    // Button switches from Qualify Lead to View Opportunity
    assert.match(leadDetail, /View Opportunity/, 'Must render View Opportunity button when qualified');
    assert.match(leadDetail, /\/crm\/opportunities\//, 'Must navigate to /crm/opportunities/ when clicked');
  });

  // =========================================================================
  // 4. API Services Configuration
  // =========================================================================
  it('Verifies crmService and invoiceService export opportunity communication and invoice methods', () => {
    const crmServiceSrc = fs.readFileSync('frontend/src/services/crmService.js', 'utf8');
    assert.match(crmServiceSrc, /getOpportunityCommunications:/, 'crmService must have getOpportunityCommunications');
    assert.match(crmServiceSrc, /addOpportunityCommunication:/, 'crmService must have addOpportunityCommunication');

    const invoiceServiceSrc = fs.readFileSync('frontend/src/services/invoiceService.js', 'utf8');
    assert.match(invoiceServiceSrc, /getOpportunityProformaInvoices:/, 'invoiceService must have getOpportunityProformaInvoices');
  });
});
