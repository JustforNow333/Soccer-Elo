# Enhanced Import System Documentation

## Overview

The enhanced import system provides multiple ways to import soccer data into your ELO rating system:

1. **API-Football Integration**: Comprehensive, real-time data from API-Football
2. **CSV Import**: Historical data from football-data.co.uk (fallback)
3. **Fixture Fetching**: Live upcoming matches

## Components

### 1. `api_import.py` - Comprehensive API-Football Importer

**Features:**
- Fetches top 100 leagues with coverage filters
- Imports teams and fixtures for each league
- Batched database operations for efficiency
- Request throttling (0.5s delay) to stay under 7500 requests/day
- Local caching to avoid duplicate requests
- Comprehensive logging and statistics

**Usage:**
```bash
# Full production import (100 leagues)
python3 api_import.py --max-leagues 100 --delay 0.5

# Test import (5 leagues, 3 teams each)
python3 api_import.py --max-leagues 5 --max-teams 3 --delay 0.2

# Dry run (show what would be imported)
python3 api_import.py --max-leagues 20 --dry-run

# Custom import
python3 api_import.py --max-leagues 50 --max-teams 10 --season 2024 --delay 0.3
```

### 2. `import_and_fetch.py` - Integrated Scheduler

**Four Operation Modes:**

#### Enhanced Mode (Default)
Hybrid approach combining API and CSV imports:
- Full API import: Sundays at 2 AM UTC
- API updates: Every 3 days at 4 AM UTC  
- CSV import: Daily at 5 AM UTC
- Fixture fetch: Daily at 8 AM UTC

#### API-Only Mode
Pure API-Football approach:
- Full API import: Sundays at 2 AM UTC
- API updates: Daily at 6 AM UTC
- Fixture fetch: Daily at 8 AM UTC

#### CSV-Only Mode
Traditional CSV-based approach:
- CSV import: Every 5 minutes
- Fixture fetch: Daily at 8 AM UTC

#### Live Mode ⚡ (NEW)
Real-time updates for current season:
- Frequent season updates: Every 5 minutes (2024-2025 season)
- Weekly fixture fetch: Daily at 8 AM UTC (7 days ahead)
- Full API import: Sundays at 2 AM UTC

**Key Features:**
- Focuses on major European leagues + Champions/Europa League
- Updates recent fixtures (last 2 days) for live scores
- Optimized for API request efficiency (9 leagues per update)
- Automatic request quota management
- Preserves daily API limits for comprehensive weekly imports

**Usage:**
```bash
# Enhanced mode (default)
python3 import_and_fetch.py

# API-only mode
python3 import_and_fetch.py --mode api-only

# CSV-only mode  
python3 import_and_fetch.py --mode csv-only

# Live mode (frequent updates)
python3 import_and_fetch.py --mode live

# With startup import
python3 import_and_fetch.py --startup-import

# Test modes
python3 import_and_fetch.py --test-api
python3 import_and_fetch.py --test-csv
python3 import_and_fetch.py --test-frequent

# Dry run
python3 import_and_fetch.py --dry-run --mode enhanced
```

### 3. `migrate_db.py` - Database Migration

Adds `api_football_id` column to teams table for API integration.

```bash
python3 migrate_db.py
```

### 4. `run_import.sh` - Interactive Runner

User-friendly shell script with guided options:

```bash
chmod +x run_import.sh
./run_import.sh
```

## Setup Instructions

### 1. Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export API_FOOTBALL_KEY="your_api_key_here"
```

### 2. Database Migration

```bash
# Add api_football_id column to teams table
python3 migrate_db.py
```

### 3. Test the System

```bash
# Test API import
python3 import_and_fetch.py --test-api

# Test CSV import
python3 import_and_fetch.py --test-csv

# Test frequent season updates
python3 import_and_fetch.py --test-frequent
```

### 4. Run Production

```bash
# Enhanced mode (recommended)
python3 import_and_fetch.py --startup-import

# Or use the interactive runner
./run_import.sh
```

## API Request Management

### Daily Limits
- API-Football limit: 7,500 requests/day
- Full import (100 leagues): ~2,000-3,000 requests
- Update import (10 leagues): ~200-500 requests
- Request throttling: 0.5-0.6 seconds between requests

### Scheduling Strategy
- **Weekly full imports**: Comprehensive data refresh
- **Daily/regular updates**: Recent changes and new fixtures
- **Request pacing**: Stays well within daily limits
- **Error handling**: Graceful fallbacks and retry logic

## Database Schema Updates

### Teams Table
```sql
ALTER TABLE teams ADD COLUMN api_football_id INTEGER UNIQUE;
```

### New Fields Used
- `teams.api_football_id`: Links to API-Football team ID
- `fixtures.api_football_id`: Links to API-Football fixture ID

## Monitoring and Logs

### Log Output
- 🔄 Processing indicators
- ✅ Success confirmations  
- ❌ Error messages with details
- 📊 Statistics and counts
- ⚠️ Warnings for fallbacks

### Key Metrics Tracked
- Leagues processed
- Teams fetched/created
- Fixtures fetched/created
- Matches created with Elo updates
- API requests made vs. daily limit
- Skipped duplicate items

## Troubleshooting

### Common Issues

1. **API Key Not Set**
   ```bash
   export API_FOOTBALL_KEY="your_key"
   ```

2. **Database Migration Needed**
   ```bash
   python3 migrate_db.py
   ```

3. **Request Limit Reached**
   - Wait for daily reset (UTC midnight)
   - Reduce --max-leagues parameter
   - Increase --delay parameter

4. **Import Fails**
   - Check logs for specific errors
   - Try test modes first
   - Fallback to CSV-only mode

### Performance Tuning

```bash
# Conservative (slower, safer)
python3 api_import.py --delay 1.0 --max-leagues 20

# Aggressive (faster, higher risk) 
python3 api_import.py --delay 0.3 --max-leagues 100
```

## Comparison: API vs CSV

| Feature | API-Football | CSV Import |
|---------|-------------|------------|
| **Data Freshness** | Real-time | Updated periodically |
| **Coverage** | Global, 100+ leagues | European leagues |
| **Fixtures** | Live upcoming matches | Historical only |
| **Rate Limits** | 7,500/day | None |
| **Reliability** | Network dependent | Always available |
| **Detail Level** | Comprehensive | Basic |
| **Setup** | Requires API key | No setup |

## Best Practices

1. **Start with test imports** before production
2. **Use enhanced mode** for best of both worlds
3. **Monitor request usage** regularly
4. **Set up proper error alerting** for production
5. **Run database migrations** before new deployments
6. **Use dry-run mode** to preview changes
7. **Keep API key secure** and rotate regularly

## Production Deployment

### On Render/Heroku
```bash
# Set environment variable
API_FOOTBALL_KEY=your_key_here

# Run migration
python3 migrate_db.py

# Start enhanced scheduler
python3 import_and_fetch.py --mode enhanced
```

### Docker
```dockerfile
ENV API_FOOTBALL_KEY=your_key_here
RUN python3 migrate_db.py
CMD python3 import_and_fetch.py --startup-import
```

This integrated system provides maximum flexibility while maintaining reliability and staying within API limits. 