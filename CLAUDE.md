# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a soccer ELO rating system with both Flask backend and Next.js frontend. The system imports match data from API-Football, calculates ELO ratings chronologically, and provides a web interface to view team rankings and match predictions. The project is designed for deployment on Render (backend) and Vercel (frontend).

## Key Commands

### Backend Development & Deployment

```bash
# Complete team import and setup (primary command)
python3 run_complete_import.py

# League-based team discovery only (testing)
python3 discover_teams.py

# Daily upcoming fixtures update
python3 upcoming_fixtures.py

# Start Flask development server
python3 app.py

# Database migration
python3 migrate_db.py

# Start production worker with monitoring
./start_worker.sh start

# Run comprehensive team diagnostics (troubleshooting)
python3 comprehensive_team_diagnostics.py

# Apply manual team mappings
python3 apply_team_mappings.py

# Test API connection and configuration
python3 test_fix.py
```

### Frontend Development

```bash
cd Frontend
npm install
npm run dev        # Development server at localhost:3000
npm run build      # Production build
npm run start      # Production server
```

## Architecture Overview

### Backend Core Components

**Database Models** (`db.py`):
- `Team`: Stores team info with ELO ratings and API-Football IDs
- `Match`: Historical completed matches with scores (used for ELO calculation)
- `Fixture`: Upcoming/live fixtures from API-Football 
- `EloRating`: Time-series ELO ratings for each team
- `User`: Subscription management with Stripe integration

**Data Import System**:
- `league_based_import.py`: NEW league-based team discovery (API documentation compliant)
- `api_import.py`: Legacy API-Football integration (being phased out)
- `top_250_teams.py`: Hardcoded list of 250 top teams with mapping utilities
- `manual_team_mappings.json`: Manual overrides for teams that can't be found via API search
- `upcoming_fixtures.py`: Daily upcoming fixtures fetcher (7 days ahead)
- `import_data.py`: CSV import fallback and team name normalization

**ELO Calculation** (`elo_utils.py`):
- Mathematical ELO rating updates with validation
- Match result parsing (win/draw/loss conversion)
- Expected outcome calculations

### API-Football Integration Details

The system uses a sophisticated multi-phase import strategy:

1. **Team Mapping Phase** (~440 requests): Maps 250 teams to API IDs using search + manual mappings
2. **Historical Import Phase** (~6,000-7,000 requests): Imports match history from 2000+ with tiered coverage:
   - Recent years (2019+): Full coverage
   - Modern era (2010-2018): Dense coverage  
   - Historical (2000-2009): Selective coverage
3. **Live Updates**: Daily fixture updates and periodic match result updates

**Critical Implementation Details**:
- Completed fixtures (status="FT") create both `Fixture` AND `Match` records
- Only `Match` records are used for ELO calculation (they have scores)
- Manual team mappings are loaded automatically by both import systems
- Request rate limiting with conservative buffers to avoid API limits

### Frontend Architecture

**Next.js App** (`Frontend/`):
- App Router structure with TypeScript
- Tailwind CSS + shadcn/ui components
- Team detail pages with ELO charts and match history
- Real-time data fetching from Flask backend API

**Key Components**:
- `TeamTable.tsx`: Main ELO rankings display
- `TeamEloChart.tsx`: Historical ELO visualization
- `TeamMatchesTable.tsx`: Match history with predictions
- Backend API endpoints: `/api/teams/{id}/upcoming`, `/api/upcoming-fixtures/today`

## Environment Variables

**Backend** (Flask):
```bash
DATABASE_URL=postgresql://...     # PostgreSQL connection
API_FOOTBALL_KEY=your_key_here   # API-Football API key (7,500 requests/day)
STRIPE_SECRET_KEY=sk_...         # Stripe payments
STRIPE_WEBHOOK_SECRET=whsec_...  # Stripe webhook verification
```

**Frontend** (Next.js):
```bash
NEXT_PUBLIC_API_URL=https://your-backend.render.com
```

## Development Workflow

### Adding New Teams
1. Add team name to `TOP_250_TEAMS` list in `top_250_teams.py`
2. If API search fails, add manual mapping to `manual_team_mappings.json`
3. Run `python3 run_complete_import.py` to import data

### Database Schema Changes
1. Modify models in `db.py`
2. Run `python3 migrate_db.py` to apply changes
3. Clear existing data if schema is incompatible

### API Request Management
- The system tracks daily API usage in log files
- Conservative limits prevent exceeding 7,500 requests/day
- Historical import prioritizes recent years first
- Manual mappings reduce API requests for difficult-to-find teams

## Deployment

**Backend** (Render):
- Deploys automatically from git pushes
- Uses `gunicorn` with worker processes
- Environment variables configured in Render dashboard
- Background scheduler runs via `start_worker.sh`

**Frontend** (Vercel):
- Deploys automatically from git pushes to Frontend/ directory
- Static site generation with API calls to backend
- Environment variables configured in Vercel dashboard

## Data Flow

1. **Import**: API-Football data → Database (Teams, Matches, Fixtures)
2. **Processing**: Matches processed chronologically → ELO ratings calculated
3. **API**: Flask serves ELO data via REST endpoints
4. **Frontend**: Next.js fetches and displays team rankings, charts, predictions

## Troubleshooting

**Low Team Mapping Success**: Run `python3 comprehensive_team_diagnostics.py` to analyze API search patterns and generate additional manual mappings.

**ELO Not Calculating**: Ensure `Match` records exist (not just `Fixture` records). Completed matches should create both record types.

**API Rate Limits**: Check daily request logs. System is designed to stay under 7,500/day but may need adjustment for large imports.

**Database Issues**: Run `python3 migrate_db.py` to ensure schema is current. For corrupt data, clear database and run fresh import.