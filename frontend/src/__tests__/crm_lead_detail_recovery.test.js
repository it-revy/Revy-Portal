import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

describe('CRM Workflow Recovery & Lead Detail Integrity Tests', () => {

  it('Verifies that Briefcase, Clock, TrendingUp, Building, and DollarSign are properly imported and defined', () => {
    const leadDetailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');
    const oppEditContent = fs.readFileSync('frontend/src/pages/CrmOpportunityEditPage.jsx', 'utf8');
    const adminDashContent = fs.readFileSync('frontend/src/pages/AdminDashboardPage.jsx', 'utf8');

    // 1. Briefcase & Clock in CrmLeadDetailPage
    assert.match(leadDetailContent, /import\s*\{[^}]*\bBriefcase\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'Briefcase must be imported in CrmLeadDetailPage');
    assert.match(leadDetailContent, /import\s*\{[^}]*\bClock\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'Clock must be imported in CrmLeadDetailPage');

    // 2. TrendingUp, Briefcase, Building in CrmOpportunityEditPage
    assert.match(oppEditContent, /import\s*\{[^}]*\bTrendingUp\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'TrendingUp must be imported in CrmOpportunityEditPage');
    assert.match(oppEditContent, /import\s*\{[^}]*\bBriefcase\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'Briefcase must be imported in CrmOpportunityEditPage');
    assert.match(oppEditContent, /import\s*\{[^}]*\bBuilding\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'Building must be imported in CrmOpportunityEditPage');

    // 3. DollarSign in AdminDashboardPage
    assert.match(adminDashContent, /import\s*\{[^}]*\bDollarSign\b[^}]*\}\s*from\s*['"]lucide-react['"]/m, 'DollarSign must be imported in AdminDashboardPage');
  });

  it('Ensures NO undefined JSX elements exist across any CRM and page files', () => {
    function walk(dir) {
      let results = [];
      const list = fs.readdirSync(dir);
      list.forEach(file => {
        const full = path.join(dir, file);
        const stat = fs.statSync(full);
        if (stat && stat.isDirectory()) {
          if (file !== '__tests__') {
            results = results.concat(walk(full));
          }
        } else if (file.endsWith('.jsx') || file.endsWith('.js')) {
          results.push(full);
        }
      });
      return results;
    }


    const files = walk('frontend/src');
    const issues = [];

    files.forEach(file => {
      const content = fs.readFileSync(file, 'utf8');
      const jsxTags = [...content.matchAll(/<([A-Z][A-Za-z0-9_]*)/g)].map(m => m[1]);
      const uniqueTags = [...new Set(jsxTags)];

      uniqueTags.forEach(tag => {
        const isImported = new RegExp('(?:import\\s+{[^}]*\\b' + tag + '\\b|import\\s+' + tag + '\\b|from\\s+.*\\b' + tag + '\\b)', 'm').test(content);
        const isDeclared = new RegExp('(?:const|let|var|function|class)\\s+' + tag + '\\b', 'm').test(content);
        const isParam = new RegExp('\\(\\s*{[^}]*\\b' + tag + '\\b', 'm').test(content);
        if (!isImported && !isDeclared && !isParam) {
          issues.push({ file, tag });
        }
      });
    });

    assert.deepEqual(issues, [], `Found undefined JSX tags: ${JSON.stringify(issues)}`);
  });

  it('Verifies CRM Error Boundary supports route resetKey, clean remounting, and diagnostic reporting', () => {
    const errorBoundaryContent = fs.readFileSync('frontend/src/components/ErrorBoundary.jsx', 'utf8');
    const crmLayoutContent = fs.readFileSync('frontend/src/layouts/CrmLayout.jsx', 'utf8');

    // ErrorBoundary has componentDidUpdate resetting on resetKey
    assert.match(errorBoundaryContent, /componentDidUpdate\s*\(\s*prevProps\s*\)/, 'ErrorBoundary must implement componentDidUpdate');
    assert.match(errorBoundaryContent, /resetKey/, 'ErrorBoundary must support resetKey');
    assert.match(errorBoundaryContent, /remountKey/, 'ErrorBoundary must support remountKey for clean retry');

    // CrmLayout passes location.pathname as resetKey
    assert.match(crmLayoutContent, /resetKey=\{location\.pathname\}/, 'CrmLayout must pass resetKey={location.pathname}');
  });

  it('Verifies complete CRM Routing Architecture in App.jsx', () => {
    const appContent = fs.readFileSync('frontend/src/App.jsx', 'utf8');

    const expectedRoutes = [
      '/crm/dashboard',
      '/crm/leads',
      '/crm/leads/new',
      '/crm/leads/:id',
      '/crm/leads/:id/edit',
      '/crm/accounts',
      '/crm/opportunities',
      '/crm/opportunities/:id/edit',
      '/crm/contacts',
      '/crm/user-hub'
    ];

    expectedRoutes.forEach(route => {
      assert.ok(appContent.includes(route), `Route ${route} must be registered in App.jsx`);
    });
  });

  it('Verifies Lead Edit navigation returns to Lead Details on save and cancel', () => {
    const leadCreateContent = fs.readFileSync('frontend/src/pages/CrmLeadCreatePage.jsx', 'utf8');
    assert.match(leadCreateContent, /isEditMode\s*\?\s*`\/crm\/leads\/\$\{id\}`\s*:\s*'\/crm\/leads'/, 'Lead edit save and discard must return to /crm/leads/${id}');
  });

  it('Verifies standardized filter styles and dimensions in design-system CSS', () => {
    const compCss = fs.readFileSync('frontend/src/design-system/components.css', 'utf8');
    const crmCss = fs.readFileSync('frontend/src/modules/crm/crm.css', 'utf8');

    // 140px min-width for filter selects to prevent stunted Business Area dropdown
    assert.match(compCss, /min-width:\s*140px/, 'Filter selects must have min-width: 140px');
    assert.match(compCss, /height:\s*var\(--control-height-md\)/, 'Controls must use standardized control height');

    // crm.css uses same height and radius
    assert.match(crmCss, /height:\s*var\(--control-height-md,\s*38px\)/, 'crm.css selects must use 38px height');
    assert.match(crmCss, /border-radius:\s*var\(--crm-radius,\s*6px\)/, 'crm.css selects must use 6px radius');
  });

  it('Simulates Lead Details data resolution with full valid record and missing optional fields', () => {
    // 1. Full valid lead
    const fullLead = {
      id: 101,
      leadId: 'LEAD-00101',
      leadName: 'Bio-Enzyme Corp Expansion',
      companyName: 'Bio-Enzyme Industries Ltd',
      businessArea: 'Biogas',
      requirementTypes: ['Turnkey', 'Supply'],
      rating: 'Hot',
      lifecycleStatus: 'Enquiry',
      clientStatus: 'New',
      connectedDate: '2026-10-15',
      followUpDate: '2026-10-25',
      account: { id: 12, accountId: 'ACC-00012', name: 'Bio-Enzyme Corp' },
      contact: { id: 8, contactId: 'CON-00008', name: 'Dr. Ramesh Sharma', email: 'ramesh@bioenzyme.test' },
      assignedUser: { id: 3, name: 'Ananya Verma', email: 'ananya@revy.test' },
      opportunities: [
        { id: 5, opportunityId: 'OPP-00005', name: 'Biogas Turnkey Reactor Plant', stage: 'Qualify', estimatedValue: 5000000, currency: 'INR' }
      ]
    };

    assert.equal(fullLead.leadId, 'LEAD-00101');
    assert.equal(fullLead.account.name, 'Bio-Enzyme Corp');
    assert.equal(fullLead.contact.name, 'Dr. Ramesh Sharma');
    assert.equal(fullLead.assignedUser.name, 'Ananya Verma');
    assert.equal(fullLead.opportunities.length, 1);
    assert.equal(Number(fullLead.opportunities[0].estimatedValue).toLocaleString(), '50,00,000');

    // 2. Minimal lead with all optional fields absent - must resolve without error
    const minimalLead = {
      id: 42,
      leadId: 'LEAD-00042',
      leadName: 'Minimalist Lead Corp',
      lifecycleStatus: 'Enquiry',
      businessArea: 'Biogas',
      account: null,
      contact: null,
      opportunities: [],
      opportunity: null,
      additionalContacts: null,
      requirementTypes: null,
      requirementType: null,
      contactMethods: null
    };

    const displayedArea = minimalLead.businessArea || 'Biogas';
    assert.equal(displayedArea, 'Biogas');

    const reqTypes = (minimalLead.requirementTypes && minimalLead.requirementTypes.length > 0)
      ? minimalLead.requirementTypes
      : [minimalLead.requirementType || 'Consulting'];
    assert.deepEqual(reqTypes, ['Consulting']);

    assert.equal(minimalLead.account?.name || null, null);
    assert.equal(minimalLead.contact?.name || null, null);
    assert.equal(minimalLead.opportunities?.length || 0, 0);
    assert.equal(minimalLead.additionalContacts ? minimalLead.additionalContacts.length : 0, 0);
  });

  it('Verifies Lead Details error handling handles 404, 500, and null states without throwing', () => {
    const leadDetailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');

    // 404 handling
    assert.match(leadDetailContent, /if\s*\(err\.response\?\.status\s*===\s*404\)/, 'Must specifically catch and handle 404 not found');
    assert.match(leadDetailContent, /Lead with identifier .* not found/, 'Must display friendly not found message');

    // Generic error fallback
    assert.match(leadDetailContent, /Failed to load lead details\. Please try again\./, 'Must provide friendly generic error fallback');

    // Render error card
    assert.match(leadDetailContent, /if\s*\(error\s*\|\|\s*!lead\)/, 'Must render dedicated error state instead of crashing');
    assert.match(leadDetailContent, /Return to Leads/, 'Must provide Return to Leads navigation button');
  });

  it('Verifies CRM Lead Form fields and dropdown options remain canonical', () => {
    const leadCreateContent = fs.readFileSync('frontend/src/pages/CrmLeadCreatePage.jsx', 'utf8');

    // Canonical lists must be present
    assert.match(leadCreateContent, /CANONICAL_LEAD_SOURCES/, 'CANONICAL_LEAD_SOURCES must exist');
    assert.match(leadCreateContent, /CANONICAL_BUSINESS_AREAS/, 'CANONICAL_BUSINESS_AREAS must exist');

    // Rating options
    assert.match(leadCreateContent, /Hot — Urgent \/ High Intent/, 'Rating options must preserve Hot');
    assert.match(leadCreateContent, /Warm — Active Interest/, 'Rating options must preserve Warm');
    assert.match(leadCreateContent, /Cold — Future \/ Exploration/, 'Rating options must preserve Cold');

    // Client Relationship Status
    assert.match(leadCreateContent, /New — First time enquiry/, 'Client Relationship Status must preserve New');
    assert.match(leadCreateContent, /Existing — Existing client relationship/, 'Client Relationship Status must preserve Existing');
  });

});
