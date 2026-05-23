# Frontend Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Incrementally optimize POE2 Analytics frontend across 5 dimensions — CSS architecture, accessibility, visual consistency, interactions, and template cleanup.

**Architecture:** Foundation-first approach. Rewrite `app.css` with all new utility classes and variables, then update `base.html` for shared infrastructure (skip link, loading bar, Chart.js defaults), then page-by-page template cleanup following the same pattern: fix heading hierarchy → add ARIA labels → replace inline styles with classes.

**Tech Stack:** Flask + Jinja2 + Bootstrap 5.3.3 + HTMX 2.0.4 + Chart.js 4.4.7 (CDN, no build tools)

---

## Task 0: Read All Source Files

Before any changes, read every file that will be modified to ensure the plan uses current line numbers and exact content.

**Files to read:**
- `app/static/css/app.css`
- `app/templates/base.html`
- `app/templates/index.html`
- `app/templates/items.html`
- `app/templates/gems.html`
- `app/templates/currency.html`
- `app/templates/currency_detail.html`
- `app/templates/item_detail.html`
- `app/templates/fragments/item_table_rows.html`
- `app/templates/fragments/price_table.html`
- `app/templates/fragments/price_chart.html`

---

### Task 1: Rewrite app.css — Foundation

**Files:**
- Modify: `app/static/css/app.css`

**What:** Rewrite the 71-line CSS file to add typography utility classes, skeleton animation, empty/error states, loading bar, chart variables, and new component classes. Keep existing dark theme variables and Bootstrap overrides.

- [ ] **Step 1: Replace app.css with rewritten version**

```css
/* POE2 Analytics — Clean Theme */

:root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #21262d;
    --text: #c9d1d9;
    --muted: #8b949e;
    --accent: #58a6ff;
    --warning: #d29922;
    --success: #3fb950;
    --purple: #a371f7;
    --error: #f85149;
    --chart-line: var(--accent);
    --chart-fill: rgba(88,166,255,.08);
    --chart-grid: #21262d;
    --chart-tick: var(--muted);
}

body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: .875rem; }

/* Skip link */
.skip-link { position: absolute; top: -100%; left: 1rem; background: var(--accent); color: #fff; padding: .5rem 1rem; border-radius: 0 0 4px 4px; z-index: 9999; text-decoration: none; }
.skip-link:focus { top: 0; }

/* Nav */
.navbar { border-bottom: 1px solid var(--border); background: var(--surface) !important; }
.navbar-brand { font-size: 1rem; letter-spacing: .5px; }
.nav-link { font-size: .875rem; color: var(--muted); }
.nav-link:hover, .nav-link.active { color: var(--text); }

/* Typography */
.page-title { font-size: 1.5rem; font-weight: 600; }
.section-title { font-size: 1.125rem; font-weight: 600; }
.card-title { font-size: 1rem; font-weight: 600; }
.text-meta { font-size: .85rem; color: var(--muted); }
.text-label { font-size: .75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; }

/* Cards */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; }
.card-stat { text-align: center; padding: 1.25rem; }
.card-stat .value { font-size: 2rem; font-weight: 600; }
.card-stat .value-sm { font-size: 1.25rem; font-weight: 600; }
.card-stat .value-xs { font-size: 1rem; font-weight: 600; }
.card-stat .label { font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
.nav-card { cursor: pointer; transition: border-color .2s; }
.nav-card:hover { border-color: var(--accent); }

/* Tables */
.table-dark { --bs-table-bg: transparent; color: var(--text); }
.table-dark tbody tr:hover { background: rgba(255,255,255,.03); }
.table th { font-size: .75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .5px; border-color: var(--border); }
.table td { border-color: var(--border); vertical-align: middle; padding: .6rem .75rem; }

/* Tabs */
.nav-tabs { border-color: var(--border); }
.nav-tabs .nav-link { color: var(--muted); border: none; font-size: .8rem; padding: .5rem 1rem; }
.nav-tabs .nav-link.active { color: var(--accent); background: transparent; border-bottom: 2px solid var(--accent); }
.nav-tabs .nav-link:hover:not(.active) { color: var(--text); border-color: transparent; }

/* Badges */
.badge { font-weight: 500; font-size: .7rem; padding: .2em .6em; }

/* Buttons */
.btn-sm { font-size: .8rem; }

/* Forms */
.form-control-dark { background: var(--surface); color: var(--text); border-color: var(--border); }
.form-control-dark:focus { border-color: var(--accent); box-shadow: none; }

/* Links */
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Footer */
footer { font-size: .75rem; color: var(--muted); border-color: var(--border) !important; }

/* Icons */
.icon-sm { width: 24px; height: 24px; }
.icon-col { width: 36px; }

/* HTMX */
.htmx-indicator { opacity: 0; transition: opacity 200ms; }
.htmx-request .htmx-indicator { opacity: 1; }
.htmx-loading-bar { position: fixed; top: 0; left: 0; height: 2px; background: var(--accent); width: 0; z-index: 9999; transition: width .3s ease; }
.htmx-request .htmx-loading-bar { width: 80%; animation: loading-bar 2s ease; }
@keyframes loading-bar { 0% { width: 0; } 100% { width: 80%; } }

/* Skeleton */
.skeleton { background: linear-gradient(90deg, var(--surface) 25%, var(--border) 50%, var(--surface) 75%); background-size: 200% 100%; animation: skeleton-pulse 1.5s ease-in-out infinite; border-radius: 4px; }
.skeleton-text { height: 1rem; width: 60%; margin-bottom: .5rem; }
.skeleton-value { height: 2rem; width: 40%; }
@keyframes skeleton-pulse { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Empty state */
.empty-state { text-align: center; padding: 3rem 1rem; }
.empty-state-title { font-size: 1.125rem; font-weight: 600; color: var(--muted); margin: .75rem 0 .25rem; }
.empty-state-desc { font-size: .875rem; color: var(--muted); }

/* Error toast */
.toast-error { background: rgba(248,81,73,.12); border: 1px solid var(--error); color: var(--error); padding: .75rem 1rem; border-radius: 6px; display: flex; align-items: center; gap: .75rem; font-size: .875rem; }
.toast-error button { background: none; border: 1px solid var(--error); color: var(--error); padding: .25rem .75rem; border-radius: 4px; cursor: pointer; font-size: .8rem; }
.toast-error button:hover { background: rgba(248,81,73,.15); }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* Stat colors */
.text-divine { color: var(--purple); }
.text-chaos { color: var(--warning); }
.text-exalted { color: var(--accent); }

/* Chart controls */
.chart-controls { display: flex; gap: .25rem; margin-top: .75rem; }
.chart-controls button { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: .3rem .75rem; border-radius: 4px; font-size: .8rem; cursor: pointer; }
.chart-controls button:hover { color: var(--text); border-color: var(--muted); }
.chart-controls button.active { color: var(--accent); border-color: var(--accent); }
```

- [ ] **Step 2: Commit**

```bash
git add app/static/css/app.css
git commit -m "feat: rewrite CSS with typography scale, skeleton, states, and chart variables"
```

---

### Task 2: Update base.html — Shared Infrastructure

**Files:**
- Modify: `app/templates/base.html`

**What:** Add skip link, loading bar, `<main>` wrapper, Chart.js global defaults. Remove Alpine.js CDN.

- [ ] **Step 1: Read the current base.html**

Read `app/templates/base.html` to understand exact structure before editing.

- [ ] **Step 2: Apply changes**

After the opening `<body>` tag, add skip link and loading bar:

```html
<body>
    <a href="#main-content" class="skip-link">Skip to content</a>
    <div class="htmx-loading-bar"></div>
```

Remove the Alpine.js script line:
```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js"></script>
```

Wrap the content block in `<main>`:
```html
<main id="main-content">
    {% block content %}{% endblock %}
</main>
```

Add `aria-label` to `<nav>`:
```html
<nav class="navbar navbar-expand-lg" aria-label="Main navigation">
```

Change language switcher to use `role="button"` and `aria-label`:
```html
<a href="?lang=zh" class="nav-link" role="button" aria-label="Switch to Chinese">中文</a>
<a href="?lang=en" class="nav-link" role="button" aria-label="Switch to English">En</a>
```

Add Chart.js global defaults script after Chart.js CDN:
```html
<script>
Chart.defaults.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim();
Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--chart-tick').trim();
Chart.defaults.scale = Chart.defaults.scale || {};
Chart.overrides.line.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim();
</script>
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/base.html
git commit -m "feat: add skip link, loading bar, main wrapper, Chart.js defaults to base.html; remove Alpine.js"
```

---

### Task 3: Update index.html — Dashboard

**Files:**
- Modify: `app/templates/index.html`

**What:** Fix heading hierarchy (h3→h1), add skeleton loading placeholders, replace refresh link with HTMX button, replace inline styles with classes.

- [ ] **Step 1: Read the current index.html**

Read `app/templates/index.html`.

- [ ] **Step 2: Apply changes**

Change page title to h1:
```html
<h1 class="page-title mb-4">POE2 Analytics</h1>
```

Replace the "---" stat value placeholders with skeleton divs. Each stat card becomes:
```html
<div class="col-md-3 col-sm-6 mb-3">
    <div class="card card-stat">
        <div class="value text-chaos" id="stat-chaos">
            <div class="skeleton skeleton-value mx-auto"></div>
        </div>
        <div class="label">Chaos per Hour</div>
    </div>
</div>
```

Replace the refresh `<a>` link with:
```html
<button class="btn btn-sm btn-outline-secondary"
        hx-get="/api/v1/dashboard/summary"
        hx-target="#dashboard-stats"
        hx-swap="innerHTML"
        aria-label="Refresh data">Refresh</button>
```

Wrap all stat cards in `<div id="dashboard-stats">`.

Change stat cards on nav cards: replace `style="cursor: pointer; transition: border-color .2s;"` with `class="nav-card"`.

Replace `style="font-weight: 600;"` headings with `class="section-title"`.
Replace `style="font-size: .85rem;"` paragraphs with `class="text-meta"`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/index.html
git commit -m "feat: dashboard — h1 hierarchy, skeleton loading, htmx refresh, inline cleanup"
```

---

### Task 4: Update items.html — Search & Cleanup

**Files:**
- Modify: `app/templates/items.html`

**What:** Fix heading hierarchy, add ARIA labels, replace Alpine.js search with vanilla JS, replace inline styles with classes.

- [ ] **Step 1: Read the current items.html**

- [ ] **Step 2: Apply changes**

Change title to h1:
```html
<h1 class="page-title mb-3">Items</h1>
```

Replace the Alpine.js `@input` with vanilla JS:
```html
<input type="text"
       class="form-control form-control-dark"
       placeholder="Search items..."
       aria-label="Search items"
       oninput="if(window._ti)clearTimeout(window._ti);window._ti=setTimeout(()=>{const v=this.value.toLowerCase();document.querySelectorAll('#item-table-body tr').forEach(r=>{r.hidden=v&&!r.textContent.toLowerCase().includes(v)})},200)">
```

Add `aria-label` to table:
```html
<table class="table table-dark table-sm mb-0" aria-label="Items list">
```

Replace `style="font-weight: 600;"` with `class="section-title"`.
Replace `style="font-size: .85rem;"` with `class="text-meta"`.
Replace `style="width: 36px;"` with `class="icon-col"`.
Replace `style="width: 24px; height: 24px;"` with `class="icon-sm"`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/items.html
git commit -m "feat: items page — h1, aria, vanilla JS search replaces Alpine, inline cleanup"
```

---

### Task 5: Update gems.html — Cleanup

**Files:**
- Modify: `app/templates/gems.html`

**What:** Fix heading hierarchy, add ARIA labels, replace inline styles.

- [ ] **Step 1: Read the current gems.html**

- [ ] **Step 2: Apply changes**

Change title to h1:
```html
<h1 class="page-title mb-3">Skill Gems</h1>
```

Add aria-label to table:
```html
<table class="table table-dark table-sm mb-0" aria-label="Skill gems list">
```

Replace `style="font-weight: 600;"` with `class="section-title"`.
Replace `style="font-size: .85rem;"` with `class="text-meta"`.
Replace `style="width: 36px;"` with `class="icon-col"`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/gems.html
git commit -m "feat: gems page — h1, aria labels, inline cleanup"
```

---

### Task 6: Update currency.html — Cleanup & Filter Logic

**Files:**
- Modify: `app/templates/currency.html`
- Modify: `app/services/currency_service.py`
- Modify: `app/models/currency.py` (if needed)

**What:** Fix heading hierarchy, add ARIA labels, inline cleanup, move hardcoded filter list from template to backend.

- [ ] **Step 1: Read current currency.html and currency_service.py**

Read `app/templates/currency.html` and `app/services/currency_service.py`.

- [ ] **Step 2: Apply template changes**

Change title to h1:
```html
<h1 class="page-title mb-3">Currency Exchange</h1>
```

Add aria-label to tables:
```html
<table class="table table-dark table-sm mb-0" aria-label="Currency exchange rates">
```

Replace inline styles: `font-weight:600;` → `class="section-title"`, `font-size:.85rem;` → `class="text-meta"`, `width:36px;` → `class="icon-col"`, `width:24px;height:24px;` → `class="icon-sm"`.

Remove the `{% if not (...)` hardcoded filter block. Replace loop to iterate over pre-filtered `currencies` list.

- [ ] **Step 3: Move filter logic to backend**

In `currency_service.py`, add the exclusion list to the service method that returns currencies for the list page. The exclusion list: `["chance shard", "transmutation shard", "regal shard", "ancient shard", "mirror shard"]` and names containing "greater" or "perfect" (case insensitive).

- [ ] **Step 4: Commit**

```bash
git add app/templates/currency.html app/services/currency_service.py
git commit -m "feat: currency page — h1, aria, inline cleanup, filter logic moved to backend"
```

---

### Task 7: Update currency_detail.html — Chart Color Unification

**Files:**
- Modify: `app/templates/currency_detail.html`

**What:** Fix heading hierarchy, add ARIA labels, replace chart inline colors with CSS variable references.

- [ ] **Step 1: Read current currency_detail.html**

- [ ] **Step 2: Apply changes**

Change item name to h1:
```html
<h1 class="page-title">{{ item.name }}</h1>
```

Add aria-label to chart canvas:
```html
<canvas id="priceChart" aria-label="Price history chart" role="img"></canvas>
```

Replace inline chart colors:
- `borderColor: '#58a6ff'` → `borderColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim()`
- `backgroundColor: 'rgba(88,166,255,0.05)'` → remove (use CSS variable via JS)
- `color: '#484f58'` → remove (use Chart.js global defaults from base.html)

Replace `style="font-weight: 600;"` → `class="section-title"`.
Replace `style="font-size: 1.25rem;"` → `class="value-sm"`.
Replace `style="font-size: 1rem;"` → `class="value-xs"`.
Replace `style="font-size: .85rem;"` → `class="text-meta"`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/currency_detail.html
git commit -m "feat: currency detail — h1, aria, chart colors via CSS variables, inline cleanup"
```

---

### Task 8: Update item_detail.html — Cleanup & Add Chart

**Files:**
- Modify: `app/templates/item_detail.html`

**What:** Fix heading hierarchy, add ARIA labels, inline cleanup, add price history chart section matching currency_detail pattern.

- [ ] **Step 1: Read current item_detail.html**

- [ ] **Step 2: Apply changes**

Change item name to h1:
```html
<h1 class="page-title">{{ item.name }}</h1>
```

Replace inline stat sizes: `style="font-size: 1.25rem;"` → `class="value-sm"`, `style="font-size: 1rem;"` → `class="value-xs"`.
Replace `style="font-weight: 600;"` → `class="section-title"`.
Replace `style="font-size: .85rem;"` → `class="text-meta"`.

Add price history chart section before the closing `{% endblock %}`:
```html
<section aria-label="Price history" class="mt-4">
    <h2 class="section-title mb-3">Price History</h2>
    <div class="card p-3">
        <canvas id="priceChart" aria-label="Item price history chart" role="img"></canvas>
        <div class="chart-controls">
            <button class="active" onclick="loadChart('7d')">7d</button>
            <button onclick="loadChart('14d')">14d</button>
            <button onclick="loadChart('30d')">30d</button>
        </div>
    </div>
</section>
<script>
function loadChart(range) {
    document.querySelectorAll('.chart-controls button').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    fetch(`/api/v1/items/{{ item.id }}/chart?range=${range}`)
        .then(r => r.json())
        .then(data => {
            const ctx = document.getElementById('priceChart').getContext('2d');
            if (window._chart) window._chart.destroy();
            window._chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Price (Chaos)',
                        data: data.values,
                        borderColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim(),
                        backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--chart-fill').trim(),
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() } },
                        y: { grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim() } }
                    }
                }
            });
        });
}
loadChart('7d');
</script>
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/item_detail.html
git commit -m "feat: item detail — h1, aria, inline cleanup, price chart section"
```

---

### Task 9: Update Fragment Templates — ARIA & Variables

**Files:**
- Modify: `app/templates/fragments/item_table_rows.html`
- Modify: `app/templates/fragments/price_table.html`
- Modify: `app/templates/fragments/price_chart.html`

**What:** Align chart colors with CSS variables, add icon classes, ARIA labels.

- [ ] **Step 1: Read all three fragment files**

- [ ] **Step 2: Update item_table_rows.html**

Replace `style="width: 24px; height: 24px;"` with `class="icon-sm"`.
Replace `style="width: 36px;"` with `class="icon-col"`.

- [ ] **Step 3: Update price_table.html**

Add `aria-label` to the nested table if present.

- [ ] **Step 4: Update price_chart.html**

Replace inline chart colors:
- `borderColor: '#0dcaf0'` → use `getComputedStyle(document.documentElement).getPropertyValue('--chart-line').trim()`
- `backgroundColor: 'rgba(13,202,240,0.1)'` → use `getComputedStyle(document.documentElement).getPropertyValue('--chart-fill').trim()`
- `color: '#6c757d'` → remove (use Chart.js globals from base.html)

Add `aria-label="Price chart" role="img"` to canvas.

- [ ] **Step 5: Commit**

```bash
git add app/templates/fragments/item_table_rows.html app/templates/fragments/price_table.html app/templates/fragments/price_chart.html
git commit -m "feat: fragments — icon classes, chart CSS variables, aria labels"
```

---

### Task 10: Verification

**Files:** None (verification only)

- [ ] **Step 1: Start the Flask dev server**

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- [ ] **Step 2: Check each page visually**

Navigate to:
1. `http://127.0.0.1:8000/` — Dashboard: skeleton loads then fills, refresh button works via HTMX
2. `http://127.0.0.1:8000/items` — Items: search works with debounce, no Alpine.js reference in source
3. `http://127.0.0.1:8000/gems` — Gems: heading hierarchy correct, no inline styles
4. `http://127.0.0.1:8000/currency` — Currency: filter works, no inline styles
5. `http://127.0.0.1:8000/currency/1` — Currency detail: chart uses unified colors
6. `http://127.0.0.1:8000/items/1` — Item detail: chart visible with range switcher, no inline styles

- [ ] **Step 3: Run accessibility audit**

Check with browser DevTools:
- Heading hierarchy: h1 → h2 → h3 (no skipped levels)
- Tab through page: skip link appears first, all interactive elements reachable
- Check `<nav>`, `<table>`, `<canvas>`, search `<input>` all have `aria-label`

- [ ] **Step 4: Verify page source has no inline styles**

```bash
grep -rn 'style="font-' app/templates/ | grep -v '.css' | grep -v 'base.html'
grep -rn 'style="width:' app/templates/
```

Expected: no output (all inline styles migrated to classes).

- [ ] **Step 5: Commit any verification fixes**

```bash
git add .
git commit -m "fix: verification tweaks after full-page review"
```

---

## Summary

| Task | Files | Risk |
|---|---|---|
| 1. CSS rewrite | `app.css` | Low — additive, old selectors preserved |
| 2. Base template | `base.html` | Medium — affects all pages |
| 3. Dashboard | `index.html` | Low — isolated page |
| 4. Items | `items.html` | Medium — removes Alpine.js dependency |
| 5. Gems | `gems.html` | Low — cleanup only |
| 6. Currency | `currency.html` + service | Medium — moves logic to backend |
| 7. Currency detail | `currency_detail.html` | Low — chart color change |
| 8. Item detail | `item_detail.html` | Medium — adds new chart section |
| 9. Fragments | 3 fragment files | Low — variable alignment |
| 10. Verification | All pages | Verification only |

Total new CSS: ~130 lines (from 71). Total templates touched: 10. Estimated implementation time: ~45 minutes.
