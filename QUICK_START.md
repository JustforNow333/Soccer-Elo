# ⚽ Soccer ELO System - Quick Start Guide

## 🚀 One-Command Setup

Get your complete soccer ELO system running with automatic match updates in just one command!

### Step 1: Set Your API Key

```bash
export API_FOOTBALL_KEY="your_api_key_here"
```

Get your API key from: https://api-football.com/

### Step 2: Choose Your Setup Method

#### For Interactive Setup (Local Development)
```bash
python3 start_system.py
```

#### For Background Worker (Render/Cloud Deployment)
```bash
python3 background_worker.py
```

#### For Initialization Only (No Daily Operations)
```bash
python3 initialize_only.py
```

That's it! This single command will:

1. ✅ **Import 250+ teams** using league-based discovery
2. ✅ **Import match history** from 2010-2025 (comprehensive coverage)
3. ✅ **Calculate ELO ratings** with adaptive K-factors
4. ✅ **Fetch upcoming fixtures** for next 7 days
5. ✅ **Start daily operations**:
   - Match updates every 3 hours ⚽
   - Weekly fixture refresh 📅  
   - Daily ELO maintenance 🏆
   - System health monitoring 🔍

## ⏱️ What to Expect

- **Initial setup**: 45-90 minutes
- **API usage**: ~6,000 requests (within 7,500 daily limit)
- **Ongoing**: System runs continuously with automatic updates

## 📊 Check System Status

```bash
python3 system_status.py
```

Shows complete system health, data counts, API usage, and scheduler status.

## ☁️ Render.com Deployment

### For Background Worker Setup:

1. **Create Background Worker Service** in Render
2. **Set Start Command**: `python3 background_worker.py`
3. **Environment Variables**:
   - `API_FOOTBALL_KEY` = your_api_key
   - `DATABASE_URL` = your_database_url
4. **Deploy** - The system will auto-initialize and run continuously

### For Web Service + Worker Setup:

1. **Web Service**:
   - Start Command: `gunicorn app:app`
   - For your Flask API

2. **Background Worker**:
   - Start Command: `python3 background_worker.py`
   - For data operations

**Note**: The `background_worker.py` script automatically detects non-interactive mode and starts without user prompts - perfect for Render deployment!

## 🔧 Advanced Options

### Skip Initialization (if already done)

```bash
python3 initialize_and_run.py --skip-init
```

### Run Only Initialization (don't start daily cycle)

```bash
python3 initialize_and_run.py --init-only
```

### Manual Operations

```bash
# Update matches right now
python3 match_results_updater.py

# Update fixtures right now  
python3 daily_fixtures_update.py

# Run ELO maintenance
python3 daily_elo_maintenance.py

# Check scheduler status
python3 scheduler_manager.py --status
```

## 🛑 Stop the System

Press `Ctrl+C` to gracefully stop all operations.

## 🔍 Troubleshooting

### API Key Issues
```bash
# Make sure your API key is set
echo $API_FOOTBALL_KEY

# If empty, set it:
export API_FOOTBALL_KEY="your_key_here"
```

### Check System Health
```bash
python3 system_status.py
```

### Database Issues
Make sure your `DATABASE_URL` environment variable is set correctly.

### Manual Recovery
If something goes wrong, you can run individual components:

```bash
# Just import teams and matches
python3 run_complete_import.py

# Just start daily operations
python3 scheduler_manager.py --daemon

# Just update matches once
python3 match_results_updater.py
```

## 📈 What Happens Daily

Once initialized, your system automatically:

- **Every 3 hours**: Updates match results, recalculates ELO ratings
- **Daily at 6 AM**: Refreshes upcoming fixtures for next 7 days
- **Daily at 2 AM**: Runs ELO maintenance and consistency checks
- **Every 6 hours**: Performs system health checks
- **Weekly**: Cleans up old data

## 🎯 Perfect for Production

The system is designed to run continuously in production environments:

- ✅ Stays within API limits (uses ~2,000 requests/day ongoing)
- ✅ Handles errors gracefully with automatic recovery
- ✅ Maintains data consistency with regular checks
- ✅ Provides comprehensive logging and monitoring
- ✅ Supports cloud deployment (Render, Heroku, AWS, etc.)

## 🚀 Ready to Go!

Your soccer ELO system will be fully operational with:
- Real-time ELO ratings for 250+ top teams
- Automatic match result updates
- Weekly fixture scheduling  
- Historical match data back to 2010
- Adaptive K-factor calculations
- Progressive rating storage with checkpoints

Perfect for building soccer prediction models, team analysis, or betting systems! ⚽🏆