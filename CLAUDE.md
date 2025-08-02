# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a soccer ELO rating system with both Flask backend and Next.js frontend. The system imports match data from API-Football, calculates ELO ratings chronologically, and provides a web interface to view team rankings and match predictions. The project is designed for deployment on Render (backend) and Vercel (frontend).

## Key Commands

### Complete System Setup (One-Command Solution)

```bash
# Quick start - complete system with automation (RECOMMENDED)
python3 start_system.py              # Interactive setup for local development
python3 background_worker.py         # Background worker for cloud deployment (Render)
python3 initialize_and_run.py        # Full initialization + daily operations
python3 initialize_only.py           # Initialization only (no daily operations)

# Check complete system status
python3 system_status.py
```

### Backend Development & Deployment

```bash
# Legacy complete import (still supported)
python3 run_complete_import.py

# Individual data operations
python3 discover_teams.py            # League-based team discovery only
python3 upcoming_fixtures.py         # Daily upcoming fixtures update
python3 match_results_updater.py     # Update match results from API
python3 daily_fixtures_update.py     # Daily fixture refresh
python3 daily_elo_maintenance.py     # ELO rating maintenance

# Automation & Scheduling
python3 scheduler_manager.py --daemon    # Start all automated tasks
python3 scheduler_manager.py --status    # Check scheduler status
python3 scheduler_manager.py --stop      # Stop scheduler

# Development & Testing
python3 app.py                       # Start Flask development server
python3 migrate_db.py                # Database migration
python3 comprehensive_team_diagnostics.py  # Team diagnostics
python3 apply_team_mappings.py       # Apply manual team mappings
python3 test_fix.py                  # Test API connection

# Legacy production worker (being phased out)
./start_worker.sh start
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

**Automation & Scheduling System**:
- `scheduler_manager.py`: Central scheduler for all periodic tasks (match updates, fixtures, maintenance)
- `match_results_updater.py`: Updates match results every 3 hours from API-Football
- `daily_fixtures_update.py`: Daily refresh of upcoming fixtures (7 days ahead)
- `daily_elo_maintenance.py`: Daily ELO rating consistency checks and maintenance
- `background_worker.py`: Non-interactive background worker for cloud deployment (Render)
- `initialize_and_run.py`: Complete system initialization with daily operation startup
- `initialize_only.py`: System initialization only (no ongoing operations)
- `start_system.py`: Interactive system manager for local development
- `system_status.py`: Comprehensive system health and status checker

**ELO Calculation** (`elo_utils.py`):
- Mathematical ELO rating updates with validation
- Match result parsing (win/draw/loss conversion)
- Expected outcome calculations

### API-Football Integration Details

The system uses a sophisticated multi-phase import strategy with automated ongoing operations:

**Initial Setup (One-time)**:
1. **Team Mapping Phase** (~440 requests): Maps 250 teams to API IDs using search + manual mappings
2. **Historical Import Phase** (~6,000-7,000 requests): Imports match history from 2000+ with tiered coverage:
   - Recent years (2019+): Full coverage
   - Modern era (2010-2018): Dense coverage  
   - Historical (2000-2009): Selective coverage

**Ongoing Operations (Automated)**:
3. **Match Updates**: Every 3 hours, fetch completed fixtures and update match results (~50-200 requests/day)
4. **Fixture Updates**: Daily refresh of upcoming fixtures for next 7 days (~20-50 requests/day)
5. **System Maintenance**: Daily ELO rating consistency checks and data cleanup

**Critical Implementation Details**:
- Completed fixtures (status="FT") create both `Fixture` AND `Match` records
- Only `Match` records are used for ELO calculation (they have scores)
- Manual team mappings are loaded automatically by both import systems
- Request rate limiting with conservative buffers to avoid API limits
- Automated scheduling keeps daily usage under 2,000 requests (well within 7,500/day limit)
- Background worker mode supports cloud deployment without interactive input
- **Runtime Compatibility**: Includes timezone-aware datetime handling and modern SQLAlchemy support
- **Import Progress**: Teams import in waves (88+ teams after 10 minutes is normal progress)
- **Fixture Processing**: "Teams not found" warnings are normal for non-target teams

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

### Backend (Render)

**Option 1: Complete System with Background Worker (RECOMMENDED)**
- **Service Type**: Background Worker
- **Start Command**: `python3 background_worker.py` ⚠️ **CRITICAL: Do NOT use `start_system.py`**
- **Auto-deploys** from git pushes
- **Environment Variables**:
  - `API_FOOTBALL_KEY`: Your API-Football key
  - `DATABASE_URL`: PostgreSQL connection string
- **Features**: Full system initialization + automated daily operations
- **Perfect for**: Production deployment with zero maintenance
- **Runtime**: Includes critical timezone and SQLAlchemy compatibility fixes

**Option 2: Web Service + Separate Background Worker**
- **Web Service**:
  - Service Type: Web Service
  - Start Command: `gunicorn app:app`
  - For Flask API endpoints
- **Background Worker**:
  - Service Type: Background Worker
  - Start Command: `python3 background_worker.py`
  - For automated data operations

**Option 3: Legacy Setup (Being Phased Out)**
- Uses `gunicorn` with worker processes
- Background scheduler runs via `start_worker.sh`
- Manual setup required

### Frontend (Vercel)
- Deploys automatically from git pushes to Frontend/ directory
- Static site generation with API calls to backend
- Environment variables configured in Vercel dashboard

## Data Flow

1. **Import**: API-Football data → Database (Teams, Matches, Fixtures)
2. **Processing**: Matches processed chronologically → ELO ratings calculated
3. **API**: Flask serves ELO data via REST endpoints
4. **Frontend**: Next.js fetches and displays team rankings, charts, predictions

## Troubleshooting

### System Status & Health Checks

**Check Overall System Status**: Run `python3 system_status.py` for comprehensive system health report including:
- Environment configuration
- Database connection and data counts  
- API key validation
- Scheduler status and task history
- Recent task execution logs

**Check Scheduler Status**: Run `python3 scheduler_manager.py --status` to see:
- Running tasks and schedules
- Last execution times
- Success/failure rates
- Upcoming scheduled tasks

### Critical Runtime Fixes Applied

**DateTime Timezone Compatibility**: Fixed critical timezone comparison errors that caused fixture processing failures:
- Files updated: `upcoming_fixtures.py`, `scheduler_manager.py`
- Issue: `can't compare offset-naive and offset-aware datetimes`
- Fix: Implemented proper UTC timezone handling for API datetime comparisons

**SQLAlchemy Compatibility**: Updated deprecated database engine calls:
- Files updated: `background_worker.py`, `initialize_and_run.py`, `system_status.py`
- Issue: `db.engine.execute()` deprecated in SQLAlchemy 2.0+
- Fix: Replaced with `db.session.execute(text("SELECT 1"))`

### Common Issues

**System Not Starting**: 
1. Check environment variables: `python3 system_status.py`
2. Verify database connection
3. Ensure API key is valid
4. Try: `python3 initialize_only.py` for fresh start

**Low Team Mapping Success**: Run `python3 comprehensive_team_diagnostics.py` to analyze API search patterns and generate additional manual mappings.

**ELO Not Calculating**: 
1. Ensure `Match` records exist (not just `Fixture` records)
2. Check that completed matches create both record types
3. Run: `python3 daily_elo_maintenance.py` for consistency check

**API Rate Limits**: 
1. Check current usage: `python3 system_status.py`
2. System designed to stay under 2,000 requests/day ongoing
3. Initial import uses ~6,000-7,000 requests (within 7,500/day limit)

**Database Issues**: 
1. Run `python3 migrate_db.py` to ensure schema is current
2. For corrupt data, clear database and run `python3 initialize_only.py`

**Scheduler Not Running**:
1. Check process: `python3 scheduler_manager.py --status`  
2. Restart: `python3 scheduler_manager.py --restart`
3. For cloud deployment, ensure background worker is running

**DateTime/Timezone Errors**: If you see "can't compare offset-naive and offset-aware datetimes":
1. This indicates timezone compatibility issues with API data
2. Restart the background worker - fixes have been applied
3. Issue typically occurs during fixture processing

**Fixture Processing Failures**: If fixtures show 0 counts despite API responses:
1. Check for timezone comparison errors in logs
2. Verify teams exist in database (warnings about missing teams are normal for non-target teams)
3. Run: `python3 system_status.py` to check data integrity

**ELO Ratings Not Updating**: If teams show similar ratings after import:
1. Verify matches were imported: Check match count in system status
2. ELO ratings start at 1000 - variation depends on match history
3. Run: `python3 daily_elo_maintenance.py` for consistency check
4. Expected range: Top teams 1200-1400, bottom teams 600-800

**Background Worker Issues**:
1. Use `python3 background_worker.py` NOT `python3 start_system.py` for Render
2. `start_system.py` requires interactive input - only for local development
3. Check Render logs for specific error messages