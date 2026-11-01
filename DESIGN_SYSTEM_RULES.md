# DESIGN_SYSTEM_RULES.md — Mandatory REVY Portal Frontend Standards

> **MANDATORY POLICY FOR ALL FUTURE REVY PORTAL DEVELOPMENT**  
> Applies to all developers, frontend architects, and AI coding agents.

---

## 1. Absolute Foundation Rule

**ALL CURRENT AND FUTURE REVY PORTAL MODULES MUST USE THE CENTRALIZED REVY ENTERPRISE DESIGN SYSTEM.**

A new module (e.g., LMS, IMS, DWR, Leave Management, MIS, or additional CRM/BMS sub-features) **MUST NOT** introduce:
- Another visual style or theme.
- Another primary color system or custom shades of blue.
- Another font family (Inter is the mandatory portal-wide typography).
- Custom, ad-hoc button designs.
- Another filter toolbar design or custom dropdown arrows.
- Another table styling or pagination layout.
- Module-specific global CSS files that override common classes.

---

## 2. Standard Shared Component Suite

All UI interfaces must be constructed using the centralized components located at:
`frontend/src/components/ui/`

Available exports:
- `PageHeader` — Standardized title, description, breadcrumbs, and command actions.
- `FilterBar` — Standardized container for filters and search toolbars.
- `FilterField` — Standardized label + control wrapper for faceted filtering.
- `SearchInput` — Standardized search input with integrated search icon and clear button.
- `Select` — Standardized dropdown control with uniform height (38px standard) and focus ring.
- `DatePicker` — Standardized date input with calendar trigger.
- `Button` — Variants: `primary`, `secondary`, `danger`, `success`, `ghost`. Sizes: `sm`, `md`, `lg`.
- `Input` — Standardized text, number, and password input fields.
- `Card` — Standardized panel surface with subtle border, shadow elevation, and padding tokens.
- `DataTable` — Standardized data table with hover states, sorting indicators, and empty states.
- `Pagination` — Standardized pagination footer with page size selection.
- `StatusBadge` — Accessible status badge pills (`success`, `warning`, `danger`, `info`, `neutral`).
- `FormField` — Form wrapper with label, validation errors, and helper text.
- `LoadingState` — Unified loading spinner and card skeletons.
- `ConfirmationDialog` — Accessible modal confirmation dialog.

---

## 3. Strict Filter Standardization Mandate

> **RULE: CHANGE THE LOOK OF FILTERS, NOT THEIR FUNCTIONALITY.**

When working on or adding filters:
1. Every filter input, select, and search box must have identical height (`38px` / `size="md"`).
2. Every filter must have the same border color (`var(--color-border)`), focus ring (`var(--color-focus-ring)`), and corner radius (`var(--radius-md)`).
3. Do not add or remove filters without explicit architectural authorization.
4. Do not alter filter names, query parameters, API contracts, or default values.
5. Mode-dependent filters (such as Table view vs Kanban view) must preserve their respective filter options.

---

## 4. Code Example for New Modules

```jsx
import React, { useState } from 'react';
import { 
  PageHeader, 
  FilterBar, 
  FilterField, 
  SearchInput, 
  Select, 
  Button, 
  Card, 
  DataTable, 
  Pagination 
} from '../components/ui';
import { Plus, RefreshCw, Layers } from 'lucide-react';

export default function NewModulePage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('ALL');
  const [page, setPage] = useState(1);

  return (
    <div className="page-body">
      {/* 1. Page Header */}
      <PageHeader
        title="Module Title"
        subtitle="Operational overview and management workspace"
        icon={Layers}
        breadcrumbs={[
          { label: 'Portal', to: '/portal' },
          { label: 'Module Title' }
        ]}
        actions={
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <Button variant="secondary" icon={RefreshCw}>Refresh</Button>
            <Button variant="primary" icon={Plus}>Create Record</Button>
          </div>
        }
      />

      {/* 2. Filter Toolbar */}
      <FilterBar>
        <div style={{ flex: 1, minWidth: '260px', maxWidth: '480px' }}>
          <SearchInput
            placeholder="Search records..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onClear={() => setSearch('')}
          />
        </div>

        <FilterField label="Status">
          <Select
            size="md"
            value={status}
            onChange={e => setStatus(e.target.value)}
            options={[
              { value: 'ALL', label: 'All Statuses' },
              { value: 'ACTIVE', label: 'Active' },
              { value: 'INACTIVE', label: 'Inactive' }
            ]}
          />
        </FilterField>
      </FilterBar>

      {/* 3. Data Presentation */}
      <Card noPadding>
        {/* Table content */}
        <Pagination
          currentPage={page}
          totalPages={10}
          totalItems={100}
          onPageChange={setPage}
        />
      </Card>
    </div>
  );
}
```

---

## 5. Verification Checklist for Pull Requests & AI Agents

Before submitting code:
- [ ] Are design tokens used for colors, padding, and borders (`var(--color-...)`, `var(--space-...)`)?
- [ ] Are shared UI components from `frontend/src/components/ui` used instead of ad-hoc HTML elements?
- [ ] Does `npm run build` succeed in `frontend/` with zero errors?
- [ ] Do all filters look identical across all pages?
- [ ] Has all existing business functionality, query parameters, and endpoints been preserved?
