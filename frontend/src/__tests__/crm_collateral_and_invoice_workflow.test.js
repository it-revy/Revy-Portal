import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

describe('CRM Collateral, Quotation & Proforma Invoice Workflow Tests', () => {

  it('Verifies CrmSidebar renders Collateral navigation with Quotations and Invoices links', () => {
    const sidebar = fs.readFileSync('frontend/src/components/CrmSidebar.jsx', 'utf8');
    assert.match(sidebar, /Collateral/, 'Sidebar must contain Collateral navigation section header');
    assert.match(sidebar, /to="\/crm\/collateral\/quotations"/, 'Sidebar must link to /crm/collateral/quotations');
    assert.match(sidebar, /to="\/crm\/collateral\/invoices"/, 'Sidebar must link to /crm/collateral/invoices');
    assert.match(sidebar, /<span>Quotations<\/span>/, 'Sidebar must display Quotations text');
    assert.match(sidebar, /<span>Invoices<\/span>/, 'Sidebar must display Invoices text');
  });

  it('Verifies CrmSidebar renders Company & Invoice Configuration link under CRM Administration', () => {
    const sidebar = fs.readFileSync('frontend/src/components/CrmSidebar.jsx', 'utf8');
    assert.match(sidebar, /to="\/crm\/settings\/company-invoice"/, 'Sidebar must link to /crm/settings/company-invoice');
    assert.match(sidebar, /<span>Company & Invoice<\/span>/, 'Sidebar must show Company & Invoice text');
  });

  it('Verifies App.jsx registers all Collateral and Invoice routes', () => {
    const appRoutes = fs.readFileSync('frontend/src/App.jsx', 'utf8');
    assert.match(appRoutes, /path="\/crm\/collateral"/, 'App.jsx must route /crm/collateral');
    assert.match(appRoutes, /path="\/crm\/collateral\/quotations"/, 'App.jsx must route /crm/collateral/quotations');
    assert.match(appRoutes, /path="\/crm\/collateral\/invoices"/, 'App.jsx must route /crm/collateral/invoices');
    assert.match(appRoutes, /path="\/crm\/proforma-invoices\/:id"/, 'App.jsx must route /crm/proforma-invoices/:id');
    assert.match(appRoutes, /path="\/crm\/settings\/company-invoice"/, 'App.jsx must route /crm/settings/company-invoice');
  });

  it('Verifies invoiceService.js exports complete API suite for collateral and invoices', () => {
    const invoiceService = fs.readFileSync('frontend/src/services/invoiceService.js', 'utf8');
    assert.match(invoiceService, /getCollateral:/, 'invoiceService must have getCollateral');
    assert.match(invoiceService, /getCurrentQuotation:/, 'invoiceService must have getCurrentQuotation');
    assert.match(invoiceService, /saveCurrentQuotation:/, 'invoiceService must have saveCurrentQuotation');
    assert.match(invoiceService, /getQuotationEmailText:/, 'invoiceService must have getQuotationEmailText');
    assert.match(invoiceService, /previewProformaInvoice:/, 'invoiceService must have previewProformaInvoice');
    assert.match(invoiceService, /createProformaInvoice:/, 'invoiceService must have createProformaInvoice');
    assert.match(invoiceService, /createInvoiceRevision:/, 'invoiceService must have createInvoiceRevision');
    assert.match(invoiceService, /getInvoiceHtmlUrl:/, 'invoiceService must have getInvoiceHtmlUrl');
    assert.match(invoiceService, /getCompanySettings:/, 'invoiceService must have getCompanySettings');
    assert.match(invoiceService, /updateCompanySettings:/, 'invoiceService must have updateCompanySettings');
  });

  it('Verifies QuotationManagerModal supports custom items, email text copy, and approve action', () => {
    const modal = fs.readFileSync('frontend/src/components/crm/QuotationManagerModal.jsx', 'utf8');
    assert.match(modal, /Approve Quotation and Create Invoice/, 'Modal must have action Approve Quotation and Create Invoice');
    assert.match(modal, /Copy Quotation/, 'Modal must have Copy Quotation action');
    assert.match(modal, /Save as a one-time item|one-time item/i, 'Modal must support one-time custom item');
    assert.match(modal, /Save permanently to catalogue|savePermanently/i, 'Modal must support saving custom item permanently to catalogue');
    assert.match(modal, /saveCurrentQuotation/, 'Modal must call saveCurrentQuotation');
  });

  it('Verifies InvoicePreparationModal implements live preview tab and permanent creation', () => {
    const modal = fs.readFileSync('frontend/src/components/crm/InvoicePreparationModal.jsx', 'utf8');
    assert.match(modal, /previewProformaInvoice/, 'Modal must call previewProformaInvoice');
    assert.match(modal, /createProformaInvoice/, 'Modal must call createProformaInvoice');
    assert.match(modal, /openPreviewInNewTab/, 'Modal must open preview in new browser tab');
    assert.match(modal, /taxType/, 'Modal must support tax types (INTRA_STATE, INTER_STATE, EXEMPT)');
  });

  it('Verifies CollateralPage filters only opportunities with quotation or PI', () => {
    const page = fs.readFileSync('frontend/src/pages/crm/collateral/CollateralPage.jsx', 'utf8');
    assert.match(page, /getCollateral/, 'CollateralPage must fetch using getCollateral');
    assert.match(page, /activeTab === 'quotations'/, 'CollateralPage must support Quotations view');
    assert.match(page, /activeTab === 'invoices'/, 'CollateralPage must support Invoices view');
    assert.match(page, /handleOpenQuotation/, 'CollateralPage must allow opening Quotation manager');
    assert.match(page, /handleCreateInvoiceFromRow/, 'CollateralPage must allow approving and creating PI');
  });

  it('Verifies InvoiceDetailPage supports immutable revisions and print view', () => {
    const page = fs.readFileSync('frontend/src/pages/crm/collateral/InvoiceDetailPage.jsx', 'utf8');
    assert.match(page, /REVISION HISTORY/, 'DetailPage must show revision history');
    assert.match(page, /createInvoiceRevision/, 'DetailPage must support creating Revision N+1');
    assert.match(page, /handlePrint/, 'DetailPage must provide print action');
    assert.match(page, /getInvoiceHtmlUrl/, 'DetailPage must use getInvoiceHtmlUrl');
  });

  it('Verifies CrmOpportunityEditPage embeds commercial collateral section', () => {
    const page = fs.readFileSync('frontend/src/pages/CrmOpportunityEditPage.jsx', 'utf8');
    assert.match(page, /Commercial Collateral \(Quotation & Proforma Invoicing\)/, 'Edit page must feature Commercial Collateral section');
    assert.match(page, /QuotationManagerModal/, 'Edit page must import QuotationManagerModal');
    assert.match(page, /InvoicePreparationModal/, 'Edit page must import InvoicePreparationModal');
    assert.match(page, /handleCopyQuoteText/, 'Edit page must have Copy Quote action');
    assert.match(page, /Approve & Create Invoice/, 'Edit page must have Approve & Create Invoice action');
  });

});
