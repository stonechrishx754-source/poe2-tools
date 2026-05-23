# POE2 Analytics — Frontend Optimization Design

Date: 2026-05-23 | Approach: Incremental Refinement | Status: Approved

## Overview

Incrementally optimize the POE2 Analytics frontend across 5 dimensions while keeping Bootstrap 5 as the base framework. Each section is self-contained and can be implemented independently.

## Section 1: CSS Architecture & Typography

### Typography Scale
Define a consistent font-size system replacing scattered inline values:

| Utility Class | Size | Use |
|---|---|---|
| `.page-title` | 1.5rem | h1 page heading |
| `.section-title` | 1.125rem | h2 section heading |
| `.card-title` | 1rem | h3 card heading |
| `.stat-value` | 2rem | Large stat number |
| `.stat-value-sm` | 1.25rem | Detail page stat number |
| `.stat-value-xs` | 1rem | Small stat number |
| `.text-meta` | 0.85rem | Description / metadata |
| `.text-label` | 0.75rem | Table headers, badges, labels |

### New CSS Utility Classes
- `.icon-sm` — width: 24px; height: 24px (replaces inline style on img)
- `.icon-col` — width: 36px (replaces inline style on td)
- `.nav-card` — cursor: pointer; transition: border-color .2s (replaces inline style)
- `.section-title` — font-weight: 600 (replaces scattered inline font-weight)

### Chart Color Variables (new CSS custom properties)
- `--chart-line`: var(--accent) — unified line color
- `--chart-fill`: rgba(88,166,255,.08) — unified fill color
- `--chart-grid`: #21262d — unified grid line
- `--chart-tick`: var(--muted) — unified tick/label color

### Chart.js Global Defaults
Add a `<script>` block in `base.html` after Chart.js CDN to set global defaults for borderColor, color, grid colors, and tick colors. Both `currency_detail.html` and `price_chart.html` will use these defaults instead of inline chart config colors.

## Section 2: Semantic HTML & Accessibility

### Heading Hierarchy
- All page titles: `<h3>` → `<h1 class="page-title">`
- Section headings: `<h3>` → `<h2 class="section-title">`
- Card headings: remain `<h3 class="card-title">`

### ARIA Additions
- `<nav>`: `aria-label="Main navigation"`
- Search `<input>`: `aria-label="Search items"` / `aria-label="Search gems"`
- `<table>` elements: `aria-label` describing content
- Chart `<canvas>`: `aria-label="Price history chart" role="img"`
- Language switcher: `role="button" aria-label="Switch to Chinese/English"`
- Dashboard refresh: change from `<a>` to `<button>` with `aria-label="Refresh data"`

### Skip Link
Add `.skip-link` as first element in `<body>` (base.html): hidden off-screen, visible on focus, links to `#main-content`. Wrap main content in `<main id="main-content">`.

## Section 3: Visual Consistency & States

### Skeleton Loading
Add `.skeleton` CSS class with gradient pulse animation. Replace dashboard "---" placeholders with skeleton divs. Dashboard JS fetch keeps the same API endpoint, just swaps skeleton → real values on load.

### Empty State Component
Standardized empty state markup: centered container with muted description text. Used when tables/charts have no data.

### Error Toast
`.toast-error` class: red-tinted banner with `role="alert"` and a Retry button. Used for failed HTMX requests.

### HTMX Loading Bar
Top-of-page loading bar (2px, accent color, fixed position) that animates during HTMX requests. Automatically shown/hidden via `.htmx-request` parent class.

## Section 4: Interaction Polish

### Replace Alpine.js Search (39KB → ~200B)
Items page search currently uses Alpine.js `x-data` + `@input`. Replace with a vanilla JS `debounceFilter()` function using `oninput` + `setTimeout`. Alpine.js CDN removed from items.html (gems.html doesn't use it).

### Dashboard Refresh → HTMX
Replace `<a onclick="location.reload()">` with `<button hx-get="/api/v1/dashboard/summary" hx-target="#dashboard-stats" hx-swap="innerHTML">`. Requires wrapping the stat cards in `<div id="dashboard-stats">`.

### HTMX Indicator Usage
Add `htmx-indicator` class to applicable elements in fragments so the CSS-defined opacity transition actually works. The loading bar (Section 3) provides the primary feedback.

### Page Transitions (optional/nice-to-have)
If time permits, add a subtle fade transition on page navigation using HTMX's `hx-swap` with `transition: true` on main content area. Skip if complex.

## Section 5: Template Cleanup & Feature Parity

### Inline Style Removal Map
| Inline Style | Replace With | Files Affected |
|---|---|---|
| `style="font-weight:600;"` | class `.section-title` | index, items, gems, currency_detail, item_detail |
| `style="font-size:.85rem;"` | class `.text-meta` | index, items, gems, currency_detail |
| `style="font-size:1.25rem;"` | class `.stat-value-sm` | currency_detail, item_detail |
| `style="font-size:1rem;"` | class `.stat-value-xs` | currency_detail, item_detail |
| `style="width:36px;"` | class `.icon-col` | currency, items, gems |
| `style="width:24px;height:24px;"` | class `.icon-sm` | currency, items, item_table_rows |
| `style="cursor:pointer;..."` | class `.nav-card` | index |

### Item Detail Chart
Add a price history chart to `item_detail.html` matching the pattern in `currency_detail.html`. Requires a backend endpoint (out of scope for frontend) or can reuse existing price data API. Include 7d/14d/30d range switcher using HTMX.

### Currency Filter Logic
Move the hardcoded exclusion list from `currency.html` template to the backend service layer. The template should receive pre-filtered data. (Minor backend change.)

## Files Changed

| File | Changes |
|---|---|
| `app/static/css/app.css` | Rewrite: add utility classes, skeleton, empty state, error toast, loading bar, chart variables |
| `app/templates/base.html` | Skip link, loading bar markup, `<main>` wrapper, Chart.js global defaults, remove Alpine.js CDN |
| `app/templates/index.html` | h1 hierarchy, skeleton loading, htmx refresh button, inline cleanup |
| `app/templates/currency.html` | h1 hierarchy, ARIA labels, inline cleanup, remove filter logic to backend |
| `app/templates/items.html` | h1 hierarchy, ARIA labels, JS search replacement, remove Alpine.js CDN |
| `app/templates/gems.html` | h1 hierarchy, ARIA labels, inline cleanup |
| `app/templates/item_detail.html` | h1 hierarchy, ARIA labels, inline cleanup, price chart (new) |
| `app/templates/currency_detail.html` | h1 hierarchy, ARIA labels, chart color variables |
| `app/templates/fragments/item_table_rows.html` | icon class, ARIA |
| `app/templates/fragments/price_table.html` | ARIA |
| `app/templates/fragments/price_chart.html` | chart color variables |

## Implementation Order

1. **app.css** — foundational utility classes and variables (everything depends on this)
2. **base.html** — skip link, loading bar, Chart.js config, main wrapper
3. **index.html** — dashboard (simplest page, good test case)
4. **items.html** — search debounce + inline cleanup
5. **gems.html** — inline cleanup
6. **currency.html** — inline cleanup + filter logic
7. **currency_detail.html** — chart color unification
8. **item_detail.html** — inline cleanup + chart addition
9. **fragments** — variable alignment + ARIA

## Non-Goals
- No CSS framework migration (staying on Bootstrap 5)
- No build toolchain (no webpack/vite — keep CDN)
- No redesign of the dark theme (keeping GitHub-dark aesthetic)
- No backend API changes beyond moving currency filter logic
