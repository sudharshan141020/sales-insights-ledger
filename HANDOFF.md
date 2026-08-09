# DataLens — Project Handoff Summary

## What it is
A universal, rule-based data analytics platform (originally "Sales Insights
Ledger," renamed to **DataLens**). Upload any CSV/Excel file → it detects
the domain (healthcare, sales, retail, education, HR, traffic, finance, or generic),
understands the data's structure, and produces a full analysis: dataset
profile, top-3 key analyses, a narrative "Story," findings, weak
points/recommendations, data quality report, and a correlation center.

**Critically: 100% rule-based, no LLM/AI API calls anywhere.** This was a
deliberate choice from the start — keeps it free to run and safe to deploy
publicly (no per-user API cost, no abuse risk). Do not suggest adding an LLM
call to "improve" insights — that would violate a core design constraint.

## Tech stack
- Backend: Python, FastAPI, pandas
- Frontend: React + Vite, Recharts for charts, lucide-react for icons
- Single process: FastAPI serves both the API and the built React app
  (no separate frontend/backend servers needed)
- Deployment: Render (free tier), auto-deploys from GitHub on push
- No database, no auth — everything processed in-memory per request

## Current visual design
**Black & white minimalist theme** (most recent state). Near-black
background (`#0A0A0B`), grayscale UI throughout. Color is used in exactly
ONE place: red, reserved for high-priority warnings. This was a deliberate
pivot away from an earlier colorful light theme — if asked to "make it
look better," don't reintroduce color without checking this is still wanted.

## Architecture (backend, all in `app/`)
Built in phases, each a separate tested module — this layering matters,
don't collapse it:

1. **`semantic_roles.py`** — classifies every column into a semantic role
   (FINANCIAL_METRIC, PROFIT, DISCOUNT, DATE, CONDITION, HOSPITAL, CATEGORY,
   IDENTIFIER, etc.) via keyword matching + dtype/cardinality fallback.
2. **`domains.py`** — scores which domain (healthcare/sales/education/hr/
   traffic/finance/generic) the dataset belongs to, based on which semantic
   roles are present. Only counts genuinely distinctive roles (learned the
   hard way: generic roles like CATEGORY caused false positives).
3. **`understanding.py`** — `understand_dataset(df)` produces a
   `DatasetProfile`: domain, confidence, primary entity, measures (each
   tagged sum/avg aggregation), dimensions (each tagged chartable/not).
   This is the single source of truth everything downstream consumes.
4. **`analyzers/`** — plugin architecture. `base_analyzer.py` defines the
   interface (`choose_dashboard`, `generate_findings`, `detect_weak_points`,
   `generate_story`, etc.); one file per domain
   (`healthcare_analyzer.py`, `sales_analyzer.py`, etc.) each just sets a
   few class attributes (`headline_dimension_roles`, `key_kpis`) — no
   domain-specific logic scattered elsewhere. `registry.py` maps domain
   name → analyzer class. Adding a new domain = one new small file +
   one registry line.
5. **`analysis_planner.py`** — decides WHICH analyses to run and picks
   chart types (line/donut/horizontal_bar/scatter/heatmap/boxplot/treemap)
   via explicit rules. Also ranks importance and picks the diverse top-3
   for the dashboard. Also generates "chart reasoning" text (why this
   chart was chosen).
6. **`executor_v2.py`** — actually computes the chart data for each
   planned analysis spec.
7. **`insight_engine.py`** — positive findings ("X is the most common Y").
8. **`weak_points.py`** — problems, each with Problem/Impact/Priority/
   Suggested Action, written in **plain English on purpose** (no jargon
   like "margin," "concentration," "IQR" — explicitly requested).
9. **`story_engine.py`** — chains findings/weak points into a narrative
   arc (Trend → Breakdown → Driver → Recommendation). Not a new detection
   engine — pure narrator over existing data.
10. **`data_quality.py`** — missing values, duplicates, constant columns,
    outliers, quality score.
11. **`correlation_center.py`** — strongest positive/negative relationships,
    each with a real p-value (Pearson r + two-sided t-test) and a caveat
    when the sample is too small or the result isn't significant — a
    strong r on 12 rows gets flagged, not presented as a confident
    finding. Also runs a VIF (variance inflation factor) check across all
    measures to catch multicollinearity — redundant metrics that only
    look independent pairwise. Both are additive to the original
    pairwise-correlation logic; nothing about the original ranking/
    pick-strongest behavior changed, these just attach more context to it.
12. **`kpi.py`, `insights.py`, `column_detector.py`, `planner.py`,
    `executor.py`** — the ORIGINAL sales-specific pipeline, kept running
    alongside the newer domain-aware one for zero regression risk. Both
    coexist in `main.py`'s response (legacy fields + a `v2` key with
    everything new). Don't be surprised two systems exist — that was
    intentional, additive-not-destructive engineering.

## Frontend (`frontend/src/`)
Key components: `ExecutiveSummary`, `IntelligentDashboard` (top-3),
`StoryMode`, `AnalysisExplorerV2` (sectioned: Trends/Distributions/
Relationships/Correlations/Outliers), `FindingsPanel`, `WeakPointsPanel`,
`DataQualityCenter`, `CorrelationCenter`, `Sidebar` (multi-file sessions,
pin, combine), `AnalysisChartV2` (renders all 7 chart types).

## Known regression-prone spots (fixed once, could break again if edited)
- **pandas 3.x changed string dtype** away from `object` — always check
  `pd.api.types.is_string_dtype()`, not `dtype == object`.
- **Identifier columns** (sequential IDs like PassengerId) must be excluded
  from becoming "the metric" — a numeric column with near-100% unique
  values isn't a real measure.
- **CSS token semantics**: `--ink` means "page background," not literally
  ink-black — its actual color has flipped between themes (dark→light→
  dark again). Any hardcoded `color: var(--ink)` assuming a specific
  literal color is fragile — check contrast whenever the theme changes.
- **top-3 diversity logic** in `analysis_planner.py`'s `top_n()`: only
  enforces unique *subject* (column), not unique *type* — an earlier
  stricter version blocked legitimate second entity-distribution analyses.

## Deployment
- Live on Render, auto-deploys from GitHub on push to main
- Workflow: edit local files → test with `start.bat` → `git add . && git
  commit && git push` → Render redeploys automatically (check the Render
  dashboard's "Events" tab to confirm a deploy actually triggered)
- **`venv` breaks if the project folder is moved/renamed** — Windows bakes
  absolute paths into it. Delete and recreate `venv` after any move.

## What's NOT built yet (from the roadmap discussions)
- More domains beyond the current 7 (Manufacturing, Agriculture,
  Sports, Marketing, Customer Support)
- Global search across charts/insights/findings
- Interactive filtering (date/region/category filters live-updating charts)
- Auth + persistence + saved workspace — **flagged multiple times as a
  real product-direction decision**, not just a feature: current app is
  pitched as "nothing is stored," adding accounts/persisted uploads
  reverses that and brings real responsibilities (password hashing,
  per-user data isolation). Needs a deliberate yes/no, not a default.
- PDF export (Excel export via SheetJS is done — client-side, no backend
  involvement, see `frontend/src/exportReport.js`)
- Performance/caching for very large datasets (100K+ rows)
- Trend forecasting on time-series measures
- Sunburst charts, map visualizations (mentioned as "future" in specs)

## Recently added (worth knowing about if picking this back up)
- **Retail domain** (`analyzers/retail_analyzer.py`): 7th domain, added purely
  additively per the plugin architecture -- new semantic roles
  (INVENTORY_LEVEL, REORDER_POINT, SUPPLIER, STORE, WAREHOUSE, UNIT_COST) in
  `semantic_roles.py`, one new entry in `domains.py`'s DOMAIN_SIGNALS, one
  new analyzer file, one registry line. Deliberately kept distinct from
  "sales" (inventory/supply-chain signals vs. transaction/discount signals)
  so datasets with both sets of columns resolve to whichever has the
  stronger weighted signal rather than colliding. Verified: a synthetic
  retail dataset (stock level, reorder point, supplier, store columns)
  detects as "retail" at full confidence; the existing sales demo dataset
  still detects as "sales" -- no regression.
- **Correlation significance + multicollinearity** (`correlation_center.py`):
  every correlation now carries `n`, `p_value`, `significant`, `strength`,
  and a plain-English `caveat`. New `analyze_multicollinearity()` function
  computes VIF per measure via plain least-squares (no sklearn needed).
  Added `scipy` and explicit `numpy` to `requirements.txt`.
- **Excel export** (`frontend/src/exportReport.js`): entirely client-side
  via SheetJS (`xlsx` npm package) — multi-sheet workbook (Overview,
  Story, Findings, Weak Points, Data Quality, Correlations,
  Multicollinearity), triggered from a button in `App.jsx`. No backend
  endpoint involved, consistent with the no-persistence design. Note:
  `npm audit` flags `xlsx` with a known prototype-pollution/ReDoS
  advisory with no patch available — low risk here since it's only used
  to *write* files from our own data, never to parse untrusted uploads,
  but worth knowing if `npm audit` output looks alarming later.

## Working style established in this project (worth carrying forward)
- Big feature requests get built in explicit phases, tested end-to-end
  after each one, with real datasets (not just the happy path) — several
  real bugs were only caught this way (pandas dtype bug, PassengerId
  picked as "revenue," top-3 diversity bug, contrast bugs after theme
  changes). Keep testing thoroughly before declaring something done.
- Changes are additive when possible — old working pipelines aren't torn
  out until a replacement is proven solid.
- This sandbox's filesystem does NOT persist between conversation
  sessions — if starting a new chat, you'll need to **re-upload your
  current project zip** (exclude `venv/` and `frontend/node_modules/`,
  those are huge and regenerate automatically) before any further backend
  or frontend edits can be made, same as had to happen this session.
