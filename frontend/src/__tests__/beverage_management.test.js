import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

describe('REVY BMS Beverage Management Feature Tests', () => {

  it('Verifies routes.jsx registers /bms/beverage-log with bms.beverages.submit permission', () => {
    const routesContent = fs.readFileSync('frontend/src/modules/bms/routes.jsx', 'utf8');
    assert.match(routesContent, /import BeverageLogPage from '\.\.\/\.\.\/pages\/BeverageLogPage'/, 'Must import BeverageLogPage');
    assert.match(routesContent, /path="\/bms\/beverage-log"/, 'Must define /bms/beverage-log route');
    assert.match(routesContent, /requiredPermission="bms\.beverages\.submit"/, 'Must guard with bms.beverages.submit');
  });

  it('Verifies routes.jsx registers /bms/beverage-management with bms.beverages.manage permission', () => {
    const routesContent = fs.readFileSync('frontend/src/modules/bms/routes.jsx', 'utf8');
    assert.match(routesContent, /import BeverageManagementPage from '\.\.\/\.\.\/pages\/BeverageManagementPage'/, 'Must import BeverageManagementPage');
    assert.match(routesContent, /path="\/bms\/beverage-management"/, 'Must define /bms/beverage-management route');
    assert.match(routesContent, /requiredPermission="bms\.beverages\.manage"/, 'Must guard with bms.beverages.manage');
  });

  it('Verifies BMSSidebar.jsx renders Beverage Log and Beverage Management navigation links', () => {
    const sidebarContent = fs.readFileSync('frontend/src/components/BMSSidebar.jsx', 'utf8');
    assert.match(sidebarContent, /to="\/bms\/beverage-log"/, 'Sidebar must link to /bms/beverage-log');
    assert.match(sidebarContent, /to="\/bms\/beverage-management"/, 'Sidebar must link to /bms/beverage-management');
    assert.match(sidebarContent, /bms\.beverages\.submit/, 'Sidebar must check bms.beverages.submit');
    assert.match(sidebarContent, /bms\.beverages\.manage/, 'Sidebar must check bms.beverages.manage');
  });

  it('Verifies navigation.js registers Beverage Log and Beverage Management items', () => {
    const navContent = fs.readFileSync('frontend/src/modules/bms/navigation.js', 'utf8');
    assert.match(navContent, /path:\s*'\/bms\/beverage-log'/, 'Navigation must include /bms/beverage-log');
    assert.match(navContent, /label:\s*'Beverage Log'/, 'Navigation must label Beverage Log');
    assert.match(navContent, /path:\s*'\/bms\/beverage-management'/, 'Navigation must include /bms/beverage-management');
    assert.match(navContent, /permission:\s*'bms\.beverages\.manage'/, 'Navigation must enforce bms.beverages.manage');
  });

  it('Verifies BeverageLogPage renders Morning and Evening sessions and enforces Cups unit', () => {
    const pageContent = fs.readFileSync('frontend/src/pages/BeverageLogPage.jsx', 'utf8');
    assert.match(pageContent, /Morning Session/, 'Must render Morning Session');
    assert.match(pageContent, /Evening Session/, 'Must render Evening Session');
    assert.match(pageContent, /Cups/, 'Must use Cups measurement unit');
    assert.match(pageContent, /\/breakfast\/beverages\/entries/, 'Must post to /breakfast/beverages/entries');
    assert.match(pageContent, /\/breakfast\/beverages\/my-entries/, 'Must fetch from /breakfast/beverages/my-entries');
    assert.match(pageContent, /Submitted records cannot be modified or deleted by employees/, 'Must inform employees of immutable entries');
  });

  it('Verifies BeverageManagementPage provides Consumption Records and Catalogue Master tabs', () => {
    const pageContent = fs.readFileSync('frontend/src/pages/BeverageManagementPage.jsx', 'utf8');
    assert.match(pageContent, /Consumption Records/, 'Must include Consumption Records tab');
    assert.match(pageContent, /Beverage Catalogue Master/, 'Must include Beverage Catalogue Master tab');
    assert.match(pageContent, /\/breakfast\/beverages\/admin\/entries/, 'Must query admin entries endpoint');
    assert.match(pageContent, /\/breakfast\/beverages\/catalogue/, 'Must query catalogue endpoint');
    assert.match(pageContent, /Show Deleted/, 'Must provide filter to show soft-deleted records');
    assert.match(pageContent, /Log Beverage on Behalf of Employee/, 'Must provide create-on-behalf capability');
  });

  it('Verifies CEOViewPage integrates Beverage Operations Overview into the Existing Director Dashboard', () => {
    const ceoPageContent = fs.readFileSync('frontend/src/pages/CEOViewPage.jsx', 'utf8');
    assert.match(ceoPageContent, /Beverage Operations &amp; Consumption Overview/, 'Must include Beverage Overview title');
    assert.match(ceoPageContent, /TODAY'S BEVERAGE CUPS/, 'Must render Today Beverage Cups KPI card');
    assert.match(ceoPageContent, /MORNING SESSION/, 'Must render Morning Session KPI card');
    assert.match(ceoPageContent, /EVENING SESSION/, 'Must render Evening Session KPI card');
    assert.match(ceoPageContent, /EMPLOYEE PARTICIPATION/, 'Must render Employee Participation KPI card');
    assert.match(ceoPageContent, /Employee Beverage Consumption Ranking/, 'Must include Employee Beverage Consumption Ranking table');
    assert.match(ceoPageContent, /Maintained strictly distinct from breakfast meals/, 'Must preserve strict metric distinction');
  });

});
