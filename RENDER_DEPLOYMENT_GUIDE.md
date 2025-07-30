# 🚀 Render Deployment Guide for 250 Teams Import

## Issues Fixed ✅

1. **Team Mapping**: Updated to use `/teams?search=` endpoint for accurate results
2. **League Assignment**: Added current league detection using `/leagues` endpoint  
3. **250 Teams**: Extended list from 230 to 250 teams
4. **ELO Calculations**: Fixed to process all imported matches chronologically
5. **API Integration**: Improved error handling and rate limiting

## 🔧 Setup on Render

### 1. Environment Variables
In your Render dashboard, set these environment variables:

```
API_FOOTBALL_KEY = your_football_api_key_here
DATABASE_URL = your_postgres_database_url
```

### 2. Deploy the Updated Code
Push these changes to your repository and redeploy on Render.

### 3. Run the Complete Import Process

Once deployed, you can run the import in several ways:

#### Option A: Using the New Import Script
```bash
python3 run_complete_import.py
```

#### Option B: Using the Top 250 Manager
```bash  
python3 top_250_manager.py setup
```

#### Option C: Manual Step-by-Step
```bash
# Step 1: Map teams
python3 top_250_manager.py map

# Step 2: Import historical data  
python3 top_250_manager.py import-historical

# Step 3: Start scheduler for ongoing updates
python3 top_250_manager.py scheduler
```

## 📊 What the Import Process Does

### Phase 1: Team Mapping (1-2 hours)
- Maps all 250 teams to their API IDs using `/teams?search=`
- Detects current league for each team using `/leagues` endpoint
- Uses ~500 API requests (250 search + 250 league lookups)
- Creates `team_id_mapping.json` with all mappings

### Phase 2: Historical Data Import (4-6 hours)
- Imports **completed matches only** (FT, AET, PEN status) from 2000 onwards
- Enhanced coverage: Full recent years + selective historical sampling
- Uses ~4,750 API requests (optimized with status filtering)
- Creates teams, matches, and fixtures in database

### Phase 3: ELO Calculation (30 minutes)
- Processes all imported matches chronologically
- Calculates ELO ratings for each team after every match
- Creates ELO history for all teams
- No API requests needed (uses existing data)

## 🎯 Expected Results

After successful import:

- **250 teams** mapped with current league assignments
- **~100,000+ matches** imported from 2000 onwards  
- **Complete ELO history** for all teams
- **Current ELO ratings** for rankings
- **League assignments** showing where each team currently plays

## 🔍 Monitoring Progress

Check status anytime with:
```bash
python3 top_250_manager.py status
```

This shows:
- Teams mapping progress (X/250 mapped)
- API request usage
- System status

## ⚠️ Important Notes

1. **API Limits**: Process respects your daily API limits
2. **Render Timeout**: Long imports may timeout - use background workers if needed
3. **Database**: Ensure sufficient storage for historical data
4. **Rate Limiting**: Built-in delays prevent API overuse

## 🚨 Troubleshooting

### If Import Stops Early
- Check API request limits: `python3 top_250_manager.py status` 
- Resume next day when API resets
- Progress is saved automatically

### If Some Teams Not Found
- Check team name variations in `top_250_teams.py`
- API search is fuzzy but some names may need adjustment
- 90%+ success rate is normal

### If ELO Calculation Fails
- Ensure matches were imported successfully
- Check database for Match records
- ELO calculation runs independently after import

## 📈 Performance Optimization

The import is optimized for:
- **Render's environment** with proper error handling
- **API rate limits** with conservative request spacing  
- **Memory usage** with batched database operations
- **Resume capability** if interrupted

Run the import during off-peak hours for best performance!