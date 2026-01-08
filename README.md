# Soccer ELO Rating System

A full-stack soccer ELO rating system with Flask backend and Next.js frontend. Imports match data from API-Football, calculates ELO ratings chronologically, and provides team rankings, match predictions, and premium betting insights.

## Tech Stack

**Backend:**
- Flask (Python 3.9+)
- PostgreSQL with SQLAlchemy ORM
- API-Football integration
- Stripe for subscriptions
- APScheduler for automated tasks

**Frontend:**
- Next.js 15.3.3 with App Router
- TypeScript + React
- Tailwind CSS + shadcn/ui components
- Recharts for ELO visualizations

## Quick Start

### Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://..."
export API_FOOTBALL_KEY="your_key"
export STRIPE_SECRET_KEY="sk_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."

# Complete system setup (one command)
python3 start_system.py              # Local development (interactive)
python3 background_worker.py         # Cloud deployment (non-interactive)

# Check system status
python3 system_status.py
```

### Frontend Setup
```bash
cd Frontend
npm install

# Set environment variable
export NEXT_PUBLIC_API_URL="http://localhost:5000"

npm run dev    # Development at localhost:3000
npm run build  # Production build
```

## Key Commands

### Data Operations
```bash
python3 run_complete_import.py        # Legacy full import
python3 discover_teams.py             # Team discovery only
python3 upcoming_fixtures.py          # Fetch upcoming fixtures
python3 match_results_updater.py      # Update match results
python3 daily_elo_maintenance.py      # ELO maintenance
```

### Automation
```bash
python3 scheduler_manager.py --daemon    # Start scheduler
python3 scheduler_manager.py --status    # Check status
python3 scheduler_manager.py --stop      # Stop scheduler
```

### Database
```bash
python3 migrate_db.py                 # Run migrations
python3 app.py                        # Start Flask dev server
```

## Architecture

### Database Models (`db.py`)
- **Team**: Team info with ELO ratings and API-Football IDs
- **Match**: Historical completed matches with scores (for ELO calculation)
- **Fixture**: Upcoming/live fixtures from API-Football
- **EloRating**: Time-series ELO ratings per team
- **User**: Subscription management via Stripe

### Data Import System
- `league_based_import.py`: League-based team discovery (API compliant)
- `api_import.py`: Legacy API-Football integration
- `top_250_teams.py`: Hardcoded top 250 teams list
- `manual_team_mappings.json`: Manual team ID overrides
- `upcoming_fixtures.py`: Daily fixture fetcher (7 days ahead)
- `import_data.py`: CSV import fallback

### Automation System
- `scheduler_manager.py`: Central scheduler for periodic tasks
- `match_results_updater.py`: Updates results every 3 hours
- `daily_fixtures_update.py`: Daily fixture refresh
- `daily_elo_maintenance.py`: Daily ELO consistency checks
- `background_worker.py`: Non-interactive worker for cloud deployment
- `initialize_and_run.py`: Full initialization + daily operations
- `start_system.py`: Interactive system manager for local dev
- `system_status.py`: System health checker

### ELO Calculation (`elo_utils.py`)
- Mathematical ELO rating updates
- Match result parsing (win/draw/loss)
- Expected outcome calculations

### Premium Features
- **Strategic Betting Endpoint**: Premium betting insights
- **Confidence Levels**:
  - Good Chance: 150-249 ELO difference
  - Great Chance: 250-399 ELO difference
  - Almost Certain: 400+ ELO difference
- Subscription validation via Stripe
- Premium-only win probability calculations

### Frontend Structure
**Pages:**
- `/`: Team rankings with search and filtering
- `/team/[id]`: Team details with ELO history and match tables
- `/subscription`: Stripe subscription management
- `/strategic-betting`: Premium betting insights
- `/terms`: Terms of Service
- `/admin`: Admin functionality
- `/success`, `/cancel`: Subscription flow pages

**Key Components:**
- `TeamTable.tsx`: Main ELO rankings
- `TeamEloChart.tsx`: Historical ELO visualization
- `TeamMatchesTable.tsx`: Match history with predictions
- `TeamsByLeague.tsx`: League-organized teams

## API-Football Integration

### Initial Setup (One-time)
1. **Team Mapping** (~440 requests): Maps 250 teams to API IDs
2. **Historical Import** (~6,000-7,000 requests): Match history from 2000+
   - Recent years (2019+): Full coverage
   - Modern era (2010-2018): Dense coverage
   - Historical (2000-2009): Selective coverage

### Ongoing Operations (Automated)
- **Match Updates**: Every 3 hours (~50-200 requests/day)
- **Fixture Updates**: Daily (~20-50 requests/day)
- **System Maintenance**: Daily ELO checks

**Critical Details:**
- Completed fixtures (status="FT") create both `Fixture` AND `Match` records
- Only `Match` records used for ELO calculation (they have scores)
- Manual team mappings loaded automatically
- Request rate limiting with conservative buffers
- Daily usage stays under 2,000 requests (7,500/day limit)

## Deployment

### Backend (Render)
**Recommended: Background Worker**
- Service Type: Background Worker
- Start Command: `python3 background_worker.py`
- Environment Variables: `API_FOOTBALL_KEY`, `DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- Auto-deploys from git pushes

**Alternative: Web Service + Background Worker**
- Web Service: `gunicorn app:app`
- Background Worker: `python3 background_worker.py`

### Frontend (Vercel)
- Auto-deploys from git pushes to `Frontend/` directory
- Environment Variable: `NEXT_PUBLIC_API_URL`
- Static site generation with API calls to backend

## Development Workflow

### Adding New Teams
1. Add team name to `TOP_250_TEAMS` in `top_250_teams.py`
2. If API search fails, add manual mapping to `manual_team_mappings.json`
3. Run `python3 run_complete_import.py`

### Database Schema Changes
1. Modify models in `db.py`
2. Run `python3 migrate_db.py`
3. Clear data if schema is incompatible

## Troubleshooting

### System Health
```bash
python3 system_status.py              # Full system report
python3 scheduler_manager.py --status # Scheduler status
```

### Common Issues

**System Not Starting:**
- Check environment variables: `python3 system_status.py`
- Verify database connection
- Ensure API key is valid

**ELO Not Calculating:**
- Ensure `Match` records exist (not just `Fixture` records)
- Run: `python3 daily_elo_maintenance.py`

**API Rate Limits:**
- Check usage: `python3 system_status.py`
- System designed to stay under 2,000 requests/day ongoing
- Initial import uses ~6,000-7,000 requests (within limit)

**DateTime/Timezone Errors:**
- Restart background worker (fixes applied for timezone handling)
- Issue occurs during fixture processing

**Background Worker Issues:**
- Use `python3 background_worker.py` NOT `start_system.py` for Render
- `start_system.py` requires interactive input (local dev only)

## Data Flow

1. **Import**: API-Football data → Database (Teams, Matches, Fixtures)
2. **Processing**: Matches processed chronologically → ELO ratings calculated
3. **API**: Flask serves ELO data via REST endpoints
4. **Frontend**: Next.js fetches and displays team rankings, charts, predictions

## Environment Variables

**Backend:**
```bash
DATABASE_URL=postgresql://...
API_FOOTBALL_KEY=your_key_here
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Frontend:**
```bash
NEXT_PUBLIC_API_URL=https://your-backend.render.com
```

## Project Status

**Production-Ready:**
- ✅ Deployed on Render (backend) and Vercel (frontend)
- ✅ Automated daily operations within API limits
- ✅ Comprehensive health monitoring
- ✅ Database integrity checks
- ✅ Timezone and SQLAlchemy compatibility fixes applied

**Current Features:**
- ✅ Team rankings with search/filtering
- ✅ Historical ELO visualizations
- ✅ Match predictions
- ✅ Stripe subscription integration
- ✅ Premium betting insights
- ✅ Terms of Service page

**Planned Features:**
- User authentication with email + password
- JWT-based session management
- Email-based 2FA for premium subscribers
- Anti-account sharing measures
- Security dashboard

## License

Proprietary - All rights reserved
