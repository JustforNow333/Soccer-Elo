# ⚽ Match Update Scheduling Setup

This guide shows how to set up automatic match updates every 3 hours for your Soccer ELO system.

## 🚀 Quick Setup

### Option 1: Using the Scheduler Manager (Recommended)

The easiest way to run all periodic tasks:

```bash
# Start the scheduler as a daemon (runs continuously)
python3 scheduler_manager.py --daemon

# Or start in background
python3 scheduler_manager.py --start
```

This automatically handles:
- ✅ Match results updates every 3 hours
- ✅ Daily upcoming fixtures updates  
- ✅ Daily ELO maintenance
- ✅ Weekly data cleanup
- ✅ System health checks

### Option 2: Individual Scripts

Run specific tasks manually or via cron:

```bash
# Update match results (run every 3 hours)
python3 match_results_updater.py

# Update upcoming fixtures (run daily)
python3 daily_fixtures_update.py

# ELO maintenance (run daily)
python3 daily_elo_maintenance.py
```

## 📅 Cron Job Setup

### For Match Updates Every 3 Hours

Add to crontab (`crontab -e`):

```bash
# Match results every 3 hours
0 */3 * * * cd /path/to/your/project && python3 match_results_updater.py

# OR use specific times (every 3 hours starting at midnight)
0 0,3,6,9,12,15,18,21 * * * cd /path/to/your/project && python3 match_results_updater.py
```

### Complete Cron Schedule

```bash
# Match results every 3 hours
0 */3 * * * cd /path/to/project && python3 match_results_updater.py

# Upcoming fixtures daily at 6 AM
0 6 * * * cd /path/to/project && python3 daily_fixtures_update.py

# ELO maintenance daily at 2 AM  
0 2 * * * cd /path/to/project && python3 daily_elo_maintenance.py

# Health check every 6 hours
0 */6 * * * cd /path/to/project && python3 scheduler_manager.py --run-task health_check
```

## ☁️ Cloud Platform Setup

### Render.com

1. **Background Service**: Create a new "Background Worker" service
2. **Start Command**: `python3 scheduler_manager.py --daemon`
3. **Environment Variables**: Make sure `API_FOOTBALL_KEY` is set

### Heroku

1. **Add to Procfile**:
   ```
   scheduler: python3 scheduler_manager.py --daemon
   ```

2. **Scale the scheduler**:
   ```bash
   heroku ps:scale scheduler=1
   ```

3. **Alternative - Use Heroku Scheduler Add-on**:
   ```bash
   heroku addons:create scheduler:standard
   ```
   Then add jobs:
   - `python3 match_results_updater.py` (every 3 hours)
   - `python3 daily_fixtures_update.py` (daily)

### AWS/Docker

**Docker Compose Example**:
```yaml
version: '3.8'
services:
  app:
    build: .
    environment:
      - API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
      - DATABASE_URL=${DATABASE_URL}
  
  scheduler:
    build: .
    command: python3 scheduler_manager.py --daemon
    environment:
      - API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - app
```

## 🔧 Configuration

### API Request Limits

The system is designed to stay within API Football's 7,500 daily request limit:

- **Match results update**: ~200 requests every 3 hours (1,600/day)
- **Daily fixtures**: ~300 requests once per day
- **Total daily usage**: ~2,000 requests (well under 7,500 limit)

### Scheduling Intervals

| Task | Frequency | Purpose |
|------|-----------|---------|
| Match Results | Every 3 hours | Get latest scores for completed games |
| Upcoming Fixtures | Daily at 6 AM | Refresh next week's fixture list |
| ELO Maintenance | Daily at 2 AM | Recalculate ratings, fix inconsistencies |
| Data Cleanup | Weekly | Remove old fixtures, clean up data |
| Health Check | Every 6 hours | Monitor system status |

## 🔍 Monitoring

### Check Scheduler Status

```bash
# See what's running
python3 scheduler_manager.py --status

# Run a task immediately
python3 scheduler_manager.py --run-task match_results

# Available tasks: match_results, fixtures, elo_maintenance, cleanup, health_check
```

### View Logs

Tasks log their execution:
- ✅ Successful runs with details
- ❌ Failed runs with error messages  
- 📊 Statistics and success rates

### Manual Testing

Test individual components:

```bash
# Test match results update
python3 match_results_updater.py

# Test with scheduling info
python3 match_results_updater.py --schedule-info

# Test upcoming fixtures
python3 daily_fixtures_update.py

# Test ELO maintenance
python3 daily_elo_maintenance.py
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Not Found**
   ```bash
   export API_FOOTBALL_KEY="your_api_key_here"
   ```

2. **Database Connection Issues**
   - Make sure `DATABASE_URL` is set correctly
   - Check database permissions

3. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```

4. **Scheduler Not Running**
   ```bash
   # Check if scheduler is active
   python3 scheduler_manager.py --status
   
   # Restart if needed
   python3 scheduler_manager.py --start
   ```

### Debug Mode

Run tasks individually to debug issues:

```bash
# Test match results update
python3 match_results_updater.py

# Check what fixtures would be processed
python3 -c "
from match_results_updater import MatchResultsUpdater
import os
updater = MatchResultsUpdater(os.environ['API_FOOTBALL_KEY'])
fixtures = updater.get_recent_fixtures_results(days_back=1)
print(f'Found {len(fixtures)} fixtures to process')
"
```

## 📊 Expected Behavior

With proper setup, you should see:

- **Every 3 hours**: Match scores updated, ELO ratings recalculated
- **Daily**: New upcoming fixtures added, old fixtures cleaned up
- **Automatic**: ELO ratings stay current with latest match results
- **Efficient**: API usage stays well under daily limits

The system ensures your ELO ratings are always up-to-date with the latest match results! ⚽🏆