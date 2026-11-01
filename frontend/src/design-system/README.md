# REVY Enterprise Design System (REVY-EDS)
**Version:** 1.0.0 (Authoritative)  
**Standardized for:** Microsoft Dynamics 365 / Salesforce Lightning Enterprise Grade Quality

---

## 1. Overview & Purpose

The **REVY Enterprise Design System (REVY-EDS)** is the mandatory visual, architectural, and component standard across all modules in the REVY Portal.

### Permanent Rule for Developers and AI Coding Agents:
> **SAME DESIGN SYSTEM. SAME COMPONENT STANDARDS. SAME FILTER APPEARANCE. SAME ENTERPRISE EXPERIENCE ACROSS ALL MODULES.**
>
> When a new module (e.g., LMS, IMS, DWR, Leave Management, MIS) is developed, developers and AI coding agents MUST use this design system. 
> **Never create module-specific themes, separate button styles, independent dropdown styles, or custom filter bars.**

---

## 2. Directory Structure

```
frontend/src/
├── design-system/
│   ├── index.css          # Master design system entry point (imported in main.jsx)
│   ├── tokens.css         # Central CSS variables (palette, spacing, radius, shadows, z-index)
│   ├── typography.css     # Typography scale, fonts, headings, and data labels
│   ├── theme.css          # Global resets, scrollbars, focus rings, and legacy aliases
│   ├── components.css     # Universal class standards (.revy-btn, .revy-input, .revy-table, etc.)
│   └── README.md          # This documentation
└── components/
    └── ui/
        ├── index.js             # Central export for all UI components
        ├── Button.jsx           # Enterprise button (primary, secondary, danger, success, ghost)
        ├── Input.jsx            # Text, number, email, and password inputs
        ├── Select.jsx           # Standardized dropdowns with consistent height and chevron
        ├── SearchInput.jsx      # Search input with integrated search icon and clear button
        ├── DatePicker.jsx       # Universal enterprise date input control
        ├── FilterBar.jsx        # Enterprise filter container with auto-wrapping
        ├── FilterField.jsx      # Uniform label + control filter wrapper
        ├── Card.jsx             # Surface panel container with header, body, and footer
        ├── DataTable.jsx        # Enterprise data table with sortable headers and empty states
        ├── Pagination.jsx       # Standardized pagination controls with page size selector
        ├── StatusBadge.jsx      # High-contrast, accessible status indicator pills
        ├── PageHeader.jsx       # Unified page title, breadcrumb navigation, and command actions
        ├── FormField.jsx        # Form input wrapper with labels, errors, and helper text
        ├── LoadingState.jsx     # Consistent spinner and skeleton loading states
        └── ConfirmationDialog.jsx # Accessible modal confirmation dialog
```

---

## 3. Design Tokens & Standards

### A. Color Palette
- **Primary / Brand:** `#2563EB` (Hover: `#1D4ED8`, Light Background: `#EFF6FF`)
- **Neutral Dark / Sidebar:** `#0F172A`
- **Application Canvas:** `#F8FAFC`
- **Surface / Card Background:** `#FFFFFF`
- **Borders & Dividers:** `#E2E8F0` (Subtle: `#F1F5F9`, Strong: `#CBD5E1`)
- **Typography:** Primary `#0F172A`, Secondary `#475569`, Muted `#94A3B8`
- **Semantic Feedback:**
  - Success: `#16A34A` (Bg: `#F0FDF4`, Border: `#BBF7D0`)
  - Warning: `#D97706` (Bg: `#FFFBEB`, Border: `#FDE68A`)
  - Danger / Error: `#DC2626` (Bg: `#FEF2F2`, Border: `#FECACA`)
  - Info: `#0284C7` (Bg: `#F0F9FF`, Border: `#BAE6FD`)

### B. Typography
- **Font Family:** `Inter`, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- **Heading Scales:**
  - Page Title (`<h1>`): 1.5rem (24px), font-weight 700, line-height 1.25
  - Section Heading (`<h2>`): 1.25rem (20px), font-weight 600, line-height 1.3
  - Card Heading (`<h3>`): 1.05rem (17px), font-weight 600, line-height 1.4
  - Form Label / Table Header: 0.75rem – 0.8125rem, font-weight 600, letter-spacing 0.025em
  - Body Text: 0.875rem (14px), font-weight 400, line-height 1.5

### C. Dimensions & Sizing Scale
- **Control Heights:**
  - Compact (`sm`): 34px (tables, inline actions)
  - Standard (`md`): 38px (filter bars, standard forms, toolbars)
  - Large (`lg`): 42px (prominent logins, hero controls)
- **Border Radii:**
  - Small (`--radius-sm`): 4px
  - Medium (`--radius-md`): 6px (Standard controls, buttons, dropdowns)
  - Card / Panel (`--radius-lg`): 8px – 10px

---

## 4. Filter Standardization Rules (STRICT MANDATE)

> **"CHANGE THE LOOK OF FILTERS, NOT THEIR FUNCTIONALITY."**

Every filter across every module MUST follow these requirements:
1. Always wrap filters inside `<FilterBar>` from `../components/ui`.
2. Each filter must use `<FilterField label="Name">` wrapping `<Select>` or `<DatePicker>`.
3. Search inputs must use `<SearchInput>` with clear buttons and integrated search icons.
4. Filter controls must have uniform height (`38px` / `size="md"`).
5. Never alter query parameters, backend API contracts, default options, or conditional visibility rules.
6. Mode-dependent filters (e.g. Table vs Kanban view) must strictly preserve their conditional rendering.

### Example Filter Implementation:
```jsx
import { FilterBar, FilterField, SearchInput, Select, Button } from '../components/ui';

<FilterBar>
  {/* Search control */}
  <div style={{ flex: 1, minWidth: '260px', maxWidth: '480px' }}>
    <SearchInput
      placeholder="Search records..."
      value={search}
      onChange={e => setSearch(e.target.value)}
      onClear={() => setSearch('')}
    />
  </div>

  {/* Faceted filters */}
  <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
    <FilterField label="Status">
      <Select
        size="md"
        value={statusFilter}
        onChange={e => setStatusFilter(e.target.value)}
        options={[
          { value: 'ALL', label: 'All Statuses' },
          { value: 'Active', label: 'Active' },
          { value: 'Pending', label: 'Pending' }
        ]}
      />
    </FilterField>

    <Button variant="secondary" onClick={handleReset}>
      Reset
    </Button>
  </div>
</FilterBar>
```

---

## 5. Standard Page Architecture

Every page must conform to the following top-to-bottom layout:
1. **Page Header:** `<PageHeader title="..." subtitle="..." breadcrumbs={...} actions={...} />`
2. **Filter / Command Bar:** `<FilterBar>...</FilterBar>` (where records are listable/filterable)
3. **Primary Data View:** `<Card>` containing `<DataTable>` or Kanban board
4. **Pagination:** `<Pagination currentPage={...} totalPages={...} totalItems={...} onPageChange={...} />`

---

## 6. Prohibited Practices for Future Modules

❌ **Do NOT:**
- Create module-specific CSS files that redefine `.btn`, `.form-control`, or headings.
- Hardcode background colors or border colors (e.g. `border: 1px solid #ccc`). Always use `var(--color-border)`.
- Use custom dropdown chevrons or disparate border radii.
- Introduce arbitrary heading sizes or non-Inter fonts.
- Remove or modify existing filter keys or business logic.
