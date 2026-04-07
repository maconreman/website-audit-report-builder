# PROJECT HANDOFF — Website Audit Report Builder

## Overview
A Flask + React web application that automates website audit reports. Originally a Google Colab notebook with ipywidgets, now a full-stack app deployable on Vercel.

## Architecture
- **Backend**: Flask (Python 3.12+), pandas for data processing, lightweight NLP (no external ML libs)
- **Frontend**: React 18 + Vite, no UI framework (custom CSS), no external chart libraries (SVG/CSS-only data viz)
- **Deployment**: Vercel (serverless Python + static React), also runs locally with two-terminal setup
- **Data**: CSV files stored in per-domain folders. Vercel uses /tmp (ephemeral). No database.

## Key Decisions Made

### Data Pipeline (Steps 2-6)
1. **All 3 CSV files required**: Screaming Frog, GA4 Organic, External Links
2. **Custom column extraction**: Uses "first valid value" from numbered columns (e.g., Author 1, Author 2 → picks first non-empty). Date Published is NOT treated as custom data.
3. **Page Highlight**: NLP extracts 2-6 word topic from Title + Meta Description using TF-weighted keywords with contiguous phrase extraction
4. **Estimated Reading Time**: Word Count / 200, rounded up → "X min read"
5. **Category approval**: Approve/Manual Check workflow. Manual Check sets Next Action for Nexus. Blog pages without author get Nexus Note.
6. **Action rules order**: (a) All zeros → Remove/Redirect, (b) /tag or /category → Discuss Further, (c) Has leads → Keep, (d) Thresholds → Keep with appending notes, (e) Recent content check, (f) Old content check LAST
7. **Nexus Notes**: Formatted as (a), (b), (c) lettered list. Never overwritten, always appended.
8. **Final action rename**: Unmarked pages → "Discuss Further" with Next Action for Nexus = "Nexus to check before finalization"
9. **Column order**: Address → metrics → CTR → Linking Sites → Page Category → Page Highlight → Estimated Reading Time → Date Modified → custom → Action → Nexus Notes → Next Action for Nexus
10. **Page categories**: Always capitalized (Blog, Product, etc.)

### Frontend
- **Font**: Arial (system font)
- **Theme**: Dark mode default, light/dark toggle. Nexus Marketing red (#DC2626) accent.
- **Layout**: Arcadia.io-inspired — dark top header, horizontal step bar, centered 960px content
- **Log panel**: Collapsed by default, shows last message, expandable
- **No icons/emojis**: Professional, text-only UI
- **Data viz**: Scorecards, horizontal bar charts, progress bars (all CSS/SVG, no libraries)
- **Step 6**: Three tabs — Audit Preview (10 rows + charts + download button), Documentation (text preview), Download (CSV + docs + Google Sheets option)

### Deployment
- `vercel.json` routes /api/* to Flask serverless, /* to React static
- `api/index.py` wraps Flask for Vercel's Python runtime
- Config detects VERCEL=1 env var → uses /tmp for data
- `requirements.txt` at project root for Vercel Python deps

## File Structure
```
backend/
  config.py          — All constants, column orders, NLP stop words
  session_state.py   — In-memory session keyed by domain
  services/
    cleaning.py      — Step 2: SF filter, custom extraction, Page Highlight, Reading Time
    merging.py       — Step 3: GA4 + External Links left-joins
    categorization.py — Step 4: URL pattern detection, category approval, Manual Check handling
    actions.py       — Step 5: Auto rules, thresholds, recent/old content, column ordering
    documentation.py — Step 6: Text doc generation, file downloads, preview API
  utils/
    url_helpers.py   — URL normalization, trailing slash, tag/category detection
    data_helpers.py  — Column detection, date formatting, metric filling
    file_helpers.py  — Path resolution, CSV I/O
    nlp_helpers.py   — Page Highlight extraction, reading time calculation
  routes/            — Flask blueprints for each step

frontend/src/
  App.jsx            — Main app with step wizard, all handler functions
  App.css            — Full layout styles, scorecards, tables, forms
  styles/theme.css   — CSS variables, dark/light mode, typography
  api/client.js      — Fetch wrapper for all backend endpoints
  components/        — 15 React components (StepWizard, ThresholdPanel, DocumentationPanel, etc.)
```

## Testing
- `test_phase1.py` — 29 unit tests (imports, helpers, Flask routes)
- `test_phase3.py` — Full pipeline integration test with synthetic CSV data
