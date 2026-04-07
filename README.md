# Website Audit Report Builder

A web application for building comprehensive website audit reports. Flask + React stack deployable to Vercel or locally.

## Quick Start (Local)

```bash
cd website-audit-builder

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Run both
./start.sh              # macOS/Linux
# OR two terminals:
python run.py           # Terminal 1 -> http://localhost:5000
cd frontend && npm run dev  # Terminal 2 -> http://localhost:5173
```

Open **http://localhost:5173**.

## Deploy to Vercel

```bash
# 1. Push to GitHub
git init && git add . && git commit -m "Website Audit Report Builder"
git remote add origin <your-repo-url>
git push -u origin main

# 2. In Vercel Dashboard:
#    - Import your GitHub repo
#    - Vercel auto-detects vercel.json
#    - No additional config needed
#    - Deploy
```

The `vercel.json` routes `/api/*` to the Flask serverless function and serves the React frontend as static files.

**Note:** Vercel serverless uses ephemeral `/tmp` storage. Files persist within a warm function instance but not across cold starts. For production persistence, add cloud storage (S3, GCS).

## Workflow

1. **Upload** — Set domain, upload 3 CSV files (all required: SF, GA4 Organic, External Links)
2. **Clean** — Filter HTML 200, detect custom columns (Author, Date, Tags, etc.), generate Page Highlights via NLP, calculate Estimated Reading Time
3. **Merge** — Left-join GA4 Organic + External Links
4. **Categorize** — Detect URL patterns, approve/reject. "Manual Check" pages get flagged in "Next Action for Nexus" column
5. **Actions** — Auto rules (zero metrics, tags, leads) → Metric thresholds with live preview → Recent content check → Old content check (LAST)
6. **Documentation** — Preview with scorecards, charts, data table; download CSV + docs

## Output Columns (in order)

Address, Landing Page Traffic, Landing Page Leads, Organic Traffic, Organic Leads, Clicks, Impressions, CTR, Linking Sites, Page Category, Page Highlight, Estimated Reading Time, Date Modified, [Custom Columns], Action, Nexus Notes, Next Action for Nexus

## Tests

```bash
python test_phase1.py    # Unit tests
python test_phase3.py    # Full pipeline integration
```
