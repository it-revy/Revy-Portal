import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

describe('CRM Timezone Standardization & Navigation Label Update Tests', () => {

  it('Verifies CrmSidebar renders "Sales Funnel" navigation item for /crm/opportunities', () => {
    const sidebarContent = fs.readFileSync('frontend/src/components/CrmSidebar.jsx', 'utf8');
    assert.match(sidebarContent, /to="\/crm\/opportunities"/, 'Sidebar must link to /crm/opportunities');
    assert.match(sidebarContent, /title="Sales Funnel"/, 'Sidebar NavLink title must be "Sales Funnel"');
    assert.match(sidebarContent, /<span>Sales Funnel<\/span>/, 'Sidebar span text must be "Sales Funnel"');
    assert.doesNotMatch(sidebarContent, /<span>Opportunities<\/span>/, 'Sidebar must not show "Opportunities"');
  });

  it('Verifies Breadcrumb maps /crm/opportunities to "Sales Funnel"', () => {
    const breadcrumbContent = fs.readFileSync('frontend/src/components/Breadcrumb.jsx', 'utf8');
    assert.match(breadcrumbContent, /second === 'opportunities'/, 'Breadcrumb must have explicit mapping for opportunities');
    assert.match(breadcrumbContent, /crumbs\.push\(\{\s*label:\s*"Sales Funnel"/, 'Breadcrumb must render "Sales Funnel"');
  });

  it('Verifies CrmOpportunitiesPage header displays "Sales Funnel Workspace"', () => {
    const oppPageContent = fs.readFileSync('frontend/src/pages/CrmOpportunitiesPage.jsx', 'utf8');
    assert.match(oppPageContent, /title="Sales Funnel Workspace"/, 'Page header must be Sales Funnel Workspace');
  });

  it('Verifies CrmLeadDetailPage error state contains "Try Again" retry action', () => {
    const detailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');
    assert.match(detailContent, /Try Again/, 'Error screen must contain a Try Again button');
    assert.match(detailContent, /onClick=\{[^}]*fetchLeadDetails/, 'Try Again button must call fetchLeadDetails');
    assert.match(detailContent, /const cleanId = \(id \|\| ''\)\.trim\(\)/, 'fetchLeadDetails must sanitize/trim the ID');
  });

  it('Verifies dateUtils exports formatDateOnly and formatISTTimestamp with Asia/Kolkata timezone', () => {
    const dateUtilsContent = fs.readFileSync('frontend/src/utils/dateUtils.js', 'utf8');
    assert.match(dateUtilsContent, /export function formatDateOnly/, 'dateUtils must export formatDateOnly');
    assert.match(dateUtilsContent, /export function formatISTTimestamp/, 'dateUtils must export formatISTTimestamp');
    assert.match(dateUtilsContent, /timeZone:\s*['"]Asia\/Kolkata['"]/, 'dateUtils must use Asia/Kolkata timezone');
  });

  it('Verifies CrmLeadDetailPage, UnifiedTimeline, and NextActivityPanel import centralized dateUtils', () => {
    const detailContent = fs.readFileSync('frontend/src/pages/CrmLeadDetailPage.jsx', 'utf8');
    const timelineContent = fs.readFileSync('frontend/src/modules/crm/components/UnifiedTimeline.jsx', 'utf8');
    const panelContent = fs.readFileSync('frontend/src/modules/crm/components/NextActivityPanel.jsx', 'utf8');

    assert.match(detailContent, /from '\.\.\/utils\/dateUtils'/, 'CrmLeadDetailPage must import dateUtils');
    assert.match(timelineContent, /from '\.\.\/\.\.\/\.\.\/utils\/dateUtils'/, 'UnifiedTimeline must import dateUtils');
    assert.match(panelContent, /from '\.\.\/\.\.\/\.\.\/utils\/dateUtils'/, 'NextActivityPanel must import dateUtils');
  });

});

