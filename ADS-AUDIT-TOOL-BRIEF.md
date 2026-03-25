# Ads Audit Tool — Claude Code Brief

## What This Is

Full-stack Google Ads audit platform. Users connect their Google Ads account via OAuth, run automated audits (23 checks across 6 weighted categories), and view scored results with fix recommendations. Built with FastAPI (async) + Next.js 14 + PostgreSQL.

---

## Tech Stack

| Layer | Tech | Version |
|-------|------|---------|
| Backend | FastAPI + Uvicorn | 0.115.6 |
| ORM | SQLAlchemy 2.0 (async) | 2.0.36 |
| DB | PostgreSQL 16 | alpine |
| Driver | asyncpg | 0.30.0 |
| Google Ads | google-ads Python client | 25.1.0 |
| Auth | OAuth 2.0 + JWT (python-jose) | 3.3.0 |
| Frontend | Next.js 14 (App Router) + React 18 | 14.2.0 |
| Styling | Tailwind CSS 4 | 4.0.0 |
| Icons | lucide-react | 0.460.0 |
| Deployment | Docker Compose / Railway | — |

---

## Project Structure

```
ads-audit-tool/
├── docker-compose.yml              # PostgreSQL + backend + frontend
├── railway.toml                    # Railway deployment config
│
├── backend/
│   ├── Dockerfile                  # Python 3.11-slim
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py                 # FastAPI app init, CORS, router mount
│       ├── config.py               # pydantic-settings (env vars)
│       ├── models/
│       │   ├── database.py         # 5 SQLAlchemy models (User, GoogleAdsAccount, Audit, CheckResult)
│       │   └── schemas.py          # Pydantic request/response schemas
│       ├── api/
│       │   ├── auth.py             # OAuth2 flow + JWT issuance
│       │   ├── accounts.py         # List Google Ads accounts
│       │   └── audits.py           # Audit CRUD + background task trigger
│       ├── services/
│       │   └── audit_runner.py     # Orchestrates: fetch data → run checks → save results
│       ├── auditors/
│       │   └── google_ads.py       # 23 audit checks, scoring algorithm (754 lines, core logic)
│       └── connectors/
│           └── google_ads.py       # Google Ads API client, 13 GAQL queries (424 lines)
│
└── frontend/
    ├── Dockerfile                  # Node 20-alpine, multi-stage
    ├── package.json
    └── src/
        ├── app/
        │   ├── layout.tsx          # Root layout (dark theme, Inter font)
        │   ├── page.tsx            # Landing page with CTA
        │   ├── auth/callback/page.tsx  # OAuth callback → stores JWT → redirects to dashboard
        │   └── dashboard/
        │       ├── page.tsx        # Account selector, run audit, audit list
        │       └── audit/[id]/page.tsx  # Audit report (polling, score gauge, check grid)
        ├── components/
        │   ├── score-gauge.tsx     # Circular SVG gauge (green/yellow/red)
        │   └── check-card.tsx      # Individual check result card
        └── lib/
            └── api.ts              # Typed API client (auth, accounts, audits)
```

---

## Running Locally

```bash
# 1. Copy env files
cp backend/.env.example backend/.env
# Edit backend/.env with your Google Ads API credentials

# 2. Start everything
docker-compose up

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Swagger:  http://localhost:8000/docs
```

### Required Environment Variables

```env
# Google Ads (from Google Cloud Console)
GOOGLE_ADS_DEVELOPER_TOKEN=xxx
GOOGLE_ADS_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=xxx
GOOGLE_ADS_REDIRECT_URI=http://localhost:8000/api/auth/callback
GOOGLE_ADS_LOGIN_CUSTOMER_ID=xxx          # optional, for MCC accounts

# Security
SECRET_KEY=<random-32+-chars>
JWT_SECRET=<random-32+-chars>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ads_audit

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
FRONTEND_ORIGIN=http://localhost:3000
```

---

## API Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/auth/login` | No | Returns Google OAuth URL |
| GET | `/api/auth/callback` | No | Exchanges auth code for JWT |
| GET | `/api/auth/refresh` | Yes | Refreshes Google access token |
| GET | `/api/accounts` | Yes | Lists user's Google Ads accounts |
| POST | `/api/audits` | Yes | Triggers audit (background task), body: `{ account_id }` |
| GET | `/api/audits` | Yes | Lists user's audits |
| GET | `/api/audits/{id}` | Yes | Gets audit detail + all check results |
| GET | `/api/health` | No | Health check |

---

## Database Schema (5 tables)

- **users** — id (UUID), email, name, encrypted Google tokens, timestamps
- **google_ads_accounts** — id (UUID), customer_id, account_name, industry, monthly_budget, primary_goal
- **audits** — id (UUID), account_id (FK), user_id (FK), status (PENDING/RUNNING/COMPLETED/FAILED), score (0-100), grade (A-F), summary, raw_data (JSON category_scores)
- **check_results** — id (UUID), audit_id (FK), check_id, check_name, category, severity, status (PASS/WARNING/FAIL/NA), score, detail, fix, fix_time_minutes, is_quick_win

Tables are created on startup via `metadata.create_all` (no Alembic migrations wired up yet).

---

## Audit Logic

### Execution Flow

1. User clicks "Run Audit" → `POST /api/audits`
2. Backend creates Audit (status=PENDING), kicks off `BackgroundTask`
3. `audit_runner.execute_audit()` sets status=RUNNING, fetches 13 GAQL queries from Google Ads API
4. Data passed to `auditors/google_ads.run_audit()` which runs all 23 checks
5. Each check returns: check_id, name, category, severity, status, score (0-100), detail, fix, fix_time
6. CheckResult records saved to DB, Audit updated with score/grade/summary
7. Frontend polls `GET /api/audits/{id}` every 3s until COMPLETED/FAILED

### 23 Checks Across 6 Categories

| Category | Weight | Checks | IDs |
|----------|--------|--------|-----|
| Conversion Tracking | 25% | 4 | G42, G43, G47, G48 |
| Wasted Spend | 20% | 4 | G14, G16, G17, G-WS1 |
| Account Structure | 15% | 5 | G03, G04, G08, G11, G12 |
| Keywords & Quality Score | 15% | 3 | G20, G21, G-KW1 |
| Ads & Assets | 15% | 3 | G26, G27, G29 |
| Settings & Targeting | 10% | 4 | G36, G50, G56, G57 |

### Scoring Algorithm

```
Per category: average of check scores within category
Overall:      weighted average of category scores (using weights above)
Grade:        A (90+), B (80-89), C (70-79), D (60-69), F (<60)
```

### Key Check Thresholds

- **G42** (CRITICAL): Must have ≥1 primary conversion action
- **G43** (CRITICAL): Enhanced conversions must be enabled
- **G17** (CRITICAL): Broad Match + Manual CPC = automatic fail
- **G14** (CRITICAL): Must have ≥1 negative keyword list (ideal: 3+ themed lists)
- **G16** (CRITICAL): Flags search terms with 0 conversions but >2 clicks as waste
- **G20** (HIGH): Impression-weighted Quality Score must be ≥7
- **G21** (CRITICAL): Any keyword with QS ≤3 flagged
- **G29** (HIGH): RSA ad strength must be Good or Excellent
- **G11** (HIGH): Location targeting must use "People in" not "People in or interested in"

### Quick Win Criteria

A check is a quick win if: severity is CRITICAL or HIGH, and fix_time_minutes ≤ 15.

---

## Google Ads API Integration

13 GAQL queries in `connectors/google_ads.py` fetch:
campaigns, ad_groups, search_terms, negative_keyword_lists, keywords, ads (RSA), asset_groups, asset_group_assets, conversion_actions, extensions, audience_segments, customer_match_lists, bidding_strategies

Data is fetched synchronously via the google-ads client library, wrapped in `run_in_executor()` for async compatibility. Failed queries return empty lists (checks mark as N/A).

---

## Auth Flow

1. `GET /api/auth/login` → returns Google OAuth consent URL
2. User grants Google Ads read permission
3. Google redirects to `/auth/callback?code=xxx`
4. Frontend captures code, calls `GET /api/auth/callback?code=xxx`
5. Backend exchanges code for tokens, creates/updates User, issues JWT (24h)
6. Frontend stores JWT in localStorage, sends as `Authorization: Bearer {jwt}` on all requests
7. `GET /api/auth/refresh` refreshes expired Google access tokens using stored refresh token

---

## Known Gaps & TODOs

### Not Yet Implemented
- **Alembic migrations**: Tables use `create_all` on startup — needs proper migration setup
- **Token encryption**: Schema fields say "encrypted" but no actual encryption applied
- **Rate limiting**: No rate limiting on API endpoints
- **Redis**: Referenced in .env.example but not used (future task queue)
- **Pagination**: Audit list not paginated
- **Multi-platform**: Only Google Ads — Meta, LinkedIn, TikTok, Microsoft checks not yet built
- **Export**: No PDF/CSV export of audit results
- **Trends**: No audit history comparison over time

### Partially Implemented
- `industry`, `monthly_budget`, `primary_goal` fields exist on GoogleAdsAccount but are never populated or used for benchmark adjustment
- Error handling UI exists but is minimal
- No tests exist

### Origin Context
This tool originated from the [claude-ads](https://github.com/hello-yellow-fornya/claude-ads) skill repo which defines the full audit framework: 190 checks across 5 platforms, severity-weighted scoring (Critical 5.0×, High 3.0×, Medium 1.5×, Low 0.5×), industry benchmarks, and compliance rules. The check IDs (G42, G14, etc.) map to the reference checklists in that repo. Expanding this tool to match the full framework's 74 Google checks (currently 23) and adding Meta/LinkedIn/TikTok/Microsoft platforms is the natural growth path.

---

## Development Guidelines

- **Backend**: All endpoints use async/await. New endpoints go in `api/`. New audit checks go in `auditors/`. New API integrations go in `connectors/`.
- **Frontend**: Uses Next.js App Router. New pages go in `src/app/`. Shared components go in `src/components/`. API calls go through `src/lib/api.ts`.
- **Adding a check**: Add the check function to `auditors/google_ads.py`, call it from `run_audit()`, and assign it a check_id matching the claude-ads reference system (e.g., G-XX).
- **Adding a platform**: Create new `auditors/<platform>.py` and `connectors/<platform>.py`. Add OAuth flow for that platform. Update `audit_runner.py` to include the new platform's checks.
- **Database changes**: Currently no migrations — when adding columns/tables, set up Alembic properly first.
- **Styling**: Dark theme, Tailwind CSS only, no component libraries. Color scheme: gray-950 background, blue-500 accents.
