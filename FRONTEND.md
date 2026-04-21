# Meridian — Frontend Guide

## Overview

The Meridian prototype is a **single HTML file** (`index.html`) — ~5,100 lines of vanilla HTML, CSS, and JavaScript. No build step, no dependencies, no framework.

Design system: **Material Design 3 (Material You)**  
Typography: **Roboto + Roboto Mono** (Google Fonts)

---

## Navigation

The app uses a **Navigation Rail** (MD3 pattern) on the left with 6 destinations:

| Icon | Label | Page ID | Description |
|---|---|---|---|
| ⬡ | Home | `pg-dashboard` | Data Readiness Dashboard |
| ◫ | Catalog | `pg-catalog` | Report catalog with domain tree |
| ◈ | Tasks | `pg-tasks` | AI-generated governance task board |
| ◌ | Chat | `pg-chat` | AI assistant chat |
| ⚙ | Settings | `pg-settings` | Connectors, schedule, mart management |
| ◉ | Executive | `pg-executive` | Fullscreen executive view (overlay) |

Navigation is handled by `nav(pageId, navElement)`:

```javascript
function nav(pg, el) {
  // 1. Remove .active from all .page elements
  // 2. Add .active to #pg-{pg}
  // 3. Update breadcrumb
  // 4. Call page-specific render function
}
```

**Executive View** is a special case — it's a `position:fixed` fullscreen overlay, opened via `openExecutive()` and closed via `closeExecutive()`.

---

## Pages

### Dashboard (`pg-dashboard`)

Components:
- **Context bar** — Steward name, date, last scan time, next scan countdown
- **SLA Status strip** — 3 counters (Breach / Warning / Healthy) at DM layer
- **Active Incidents** — 2 incident cards (critical + warning)

Each incident card structure:
```
[colored top stripe]
[status row: badge + affected count + occurrence chip]
[description block: AI name + AI description text]
[location row: mart › Layer ✕ › Layer ✕ + View RCA button]
[footer: Est. recovery time]
```

---

### Catalog (`pg-catalog`)

Two-panel layout:
- **Left tree** (240px) — domain hierarchy with health dots, favourites section at top
- **Main area** — filter strip + report card list

**Catalog views:**
- `favourites` — sorted by `openCount DESC`
- `all` — grouped by domain
- Single report ID — shows just that report

**Filter strip** — All / ❌ Failed / ⚠ At Risk / ✓ Healthy

**Report card (`rc2`)** structure:
```
[colored left stripe: go/warn/stop]
[header: icon + name | status badge]
[meta: owner · refresh · last run]
[SLA table: Source / Staging / ODS / DM columns
  each showing: rows · SLA actual/target · DQ pass/fail]
```

---

### Report Detail (`pg-detail`)

7 tabs:
1. **Overview** — Readiness hero, AI narrative, resolution, impact map
2. **Data Dictionary** — Field cards with glossary
3. **Lineage & RCA** — Interactive node graph with SLA detail
4. **DQ Rules** — All rules across all layers
5. **Affected Rows** — KPI strip, AI assignment suggestions
6. **History** — Incident timeline
7. **Ownership** — People and regulatory refs

Side panel (296px): usage trend, DQ trend, pattern alert, time to resolution.

Tab switching: `dtab(id, element)` — shows/hides `#dt-{id}` divs.

---

### Data Dictionary Tab

Field cards use a **two-level expandable design**:

**Compact row (always visible)** — CSS Grid with 4 fixed columns:
```
[Business Name — 1fr] [tech_name pill — 180px] [TYPE — 120px] [Details › CTA — auto]
```

**Expanded body** (on click) — sections:
- **Definition** — plain text
- **Calculation** — monospace code block with `↕ Expand/Collapse`
- **Data Quality** — alert if DQ issue exists
- **Footer** — Edit/Publish buttons + "Last edited by" meta

Key functions:
```javascript
toggleDdField(id)          // toggle .open class on .dd-field
toggleCalc(id, btn)        // expand/collapse .dd-calc max-height
setDdFilter(filter, btn)   // filter by data-glossary attribute
```

Filter uses `data-glossary` attribute on each `.dd-field`:
```html
<div class="dd-field" data-glossary="published" ...>
<div class="dd-field" data-glossary="draft" ...>
<div class="dd-field" data-glossary="none" ...>
```

---

### Executive View (`pg-executive`)

Fullscreen overlay (`position:fixed; inset:0; z-index:50`).

Three views rendered by JavaScript:
- `exvCDO()` — Governance maturity by domain, glossary progress, actions needed
- `exvCRO()` — Report reliability table, regulatory DQ, active incidents
- `exvCFO()` — Financial exposure KPIs, incident business impact, recurrence history

All views return HTML strings injected into `#exv-body`.

Switching: `exvSwitch(view, btn)` → sets `exvView` → calls `renderExecutive()`.

Date navigation: `exvNav(dir)` steps through `exvDates[]` array (mock historical data).

---

## Data Model (Frontend)

### `REPORTS` array
```javascript
{
  id: 'credit',
  ico: '📊',
  name: 'Monthly Credit Portfolio Report',
  domain: 'Credit Risk',
  owner: 'Risk Analytics',
  refresh: 'Daily 06:00',
  dq: 71,              // DQ pass rate %
  failRules: 3,
  status: 'warn',      // 'go' | 'warn' | 'stop'
  run: 'today 06:14',
  incident: '3 DQ rules failed...',
  sla: [               // per-layer SLA data
    {layer:'Source', status:'go', actual:'01:30', target:'02:00',
     rows:148420, dq:100, dqPass:12, dqTotal:12},
    // ...
  ]
}
```

### `USAGE_DATA` object
```javascript
// Per-report array of 14 daily run counts
{ credit: [3,5,4,6,4,0,5,3,4,5,3,0,4,14], ... }
```

### `favourites` object
```javascript
// {reportId: {addedAt: timestamp, openCount: number}}
{ 'capital': {addedAt: 1234567890, openCount: 12} }
```

---

## CSS Architecture

All CSS is inline in `<style>` blocks co-located with their HTML sections.

**CSS variable system (MD3):**
```css
:root {
  --md-primary: #1565C0;
  --md-error:   #B3261E;
  --md-warning: #E65100;
  --md-success: #1B5E20;
  /* ... full MD3 color system */

  /* Aliases for convenience */
  --fog:  var(--md-on-surface);       /* primary text */
  --fog3: var(--md-outline);          /* secondary text */
  --fog4: var(--md-outline-var);      /* tertiary text */
  --go:   var(--md-success);
  --warn: var(--md-warning);
  --stop: var(--md-error);
  --signal: var(--md-primary);
}
```

**CSS class prefixes by section:**
| Prefix | Section |
|---|---|
| `.db-` | Dashboard |
| `.inc-` | Incident cards |
| `.rc2-` | Report cards in catalog |
| `.dd-` | Data Dictionary |
| `.dt-` | Report Detail |
| `.tc-` | Task cards |
| `.exv-` | Executive View |
| `.wsec-`, `.slac-` | Register Mart wizard |

---

## Key JavaScript Functions

```javascript
// Navigation
nav(pg, el)                // switch page
openExecutive()            // show fullscreen executive overlay
closeExecutive()           // hide executive overlay

// Catalog
renderCatalog()            // render tree + main list
renderCatalogMain()        // render report cards
setCatalogFilter(status)   // filter by go/warn/stop
selectReport(id)           // highlight in tree + open
openReport(id)             // navigate to detail page

// Report Detail
dtab(id, el)               // switch detail tab
selNode(nodeId)            // lineage graph node selection

// Data Dictionary
toggleDdField(id)          // expand/collapse field card
toggleCalc(id, btn)        // expand/collapse code block
setDdFilter(filter, btn)   // filter by glossary status

// Glossary
openGlossaryAdd(tech, biz) // open modal for new entry
openGlossaryEdit(...)      // open modal for editing
publishGlossary(field, btn) // publish draft entry

// Favourites
toggleFavourite(id)        // add/remove favourite
refreshFavBtn(id)          // update button state

// Executive
renderExecutive()          // render current view (CDO/CRO/CFO)
exvSwitch(view, btn)       // switch view
exvNav(dir)                // navigate dates

// Tasks
renderTasks()              // render task board
approveTask(id)            // remove task with animation
```
