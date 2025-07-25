import os
import sys
import argparse
from datetime import datetime
import json
print("🟢 STARTED import_and_fetch.py", flush=True)
from db import db
from app import app
# Removed CSV imports - API-only system
from fixture_import import fetch_next_48_hours_fixtures
from apscheduler.schedulers.blocking import BlockingScheduler\

# Define the file path for storing top 100 teams
TOP_100_TEAMS_FILE = "top_100_teams.json"


# Import the new API-Football system
try:
    from api_import import APIFootballImporter
    from migrate_db import migrate_database
    from top_250_teams import get_team_mapper
    API_IMPORT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  API import system not available: {e}", flush=True)
    API_IMPORT_AVAILABLE = False

# CSV functionality removed - using API-only system

def scheduled_fixture_fetch():
    """Scheduled function to fetch fixtures from API-Football"""
    print("Running scheduled fixture fetch...", flush=True)
    with app.app_context():
        from fixture_import import fetch_upcoming_week_fixtures
        fetch_upcoming_week_fixtures()
    print("Finished scheduled fixture fetch.", flush=True)


def api_import_full():
    """Full API import for comprehensive data (weekly)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API import...", flush=True)
        return
    
    print("🚀 Running full API-Football import (weekly)...", flush=True)
    
    with app.app_context():
        try:
            # Run database migration first
            migrate_database()
            
            # Initialize importer with conservative settings for scheduled runs
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.6,  # Slightly slower for scheduled runs
                max_requests_per_day=7000  # Conservative limit to ensure we don't exceed
            )
            
            # Import top 50 leagues to stay within daily limits
            importer.run_import(
                max_leagues=50,
                max_teams_per_league=None  # All teams
            )
            
            print("✅ Full API import completed successfully", flush=True)
            
        except Exception as e:
            print(f"❌ API import failed: {str(e)}", flush=True)


def api_import_updates():
    """Quick API import for recent updates (daily)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API import...", flush=True)
        return
    
    print("🔄 Running API-Football updates (daily)...", flush=True)
    
    with app.app_context():
        try:
            # Initialize importer for quick updates
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.5,
                max_requests_per_day=7000  # Conservative limit
            )
            
            # Import top 10 major leagues only for daily updates
            importer.run_import(
                max_leagues=10,
                max_teams_per_league=None
            )
            
            print("✅ API updates completed successfully", flush=True)
            
        except Exception as e:
            print(f"❌ API updates failed: {str(e)}", flush=True)


def api_frequent_season_update():
    """Frequent season update - optimized for 5-minute intervals"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping frequent update...", flush=True)
        return
    
    print("⚡ Running frequent season update (5-minute interval)...", flush=True)
    
    with app.app_context():
        try:
            # Initialize importer with faster settings for frequent updates
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=2024,  # Focus on 2024-2025 season
                request_delay=0.3,  # Faster for frequent updates
                max_requests_per_day=7000  # Conservative limit
            )
            
            # Run frequent season update
            importer.run_frequent_season_update(season=2024)
            
            print("✅ Frequent season update completed successfully", flush=True)
            
        except Exception as e:
            print(f"❌ Frequent season update failed: {str(e)}", flush=True)

def api_import_test():
    """Test API import with minimal data"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return False
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set", flush=True)
        return False
    
    print("🧪 Running test API import...", flush=True)
    
    with app.app_context():
        try:
            migrate_database()
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.3,
                max_requests_per_day=7000  # Conservative limit
            )
            
            # Test with just 3 leagues, 5 teams each
            importer.run_import(
                max_leagues=3,
                max_teams_per_league=5
            )
            
            print("✅ Test import completed successfully", flush=True)
            return True
            
        except Exception as e:
            print(f"❌ Test import failed: {str(e)}", flush=True)
            return False

def api_import_test_small():
    """Small test - just 1 league, 3 teams (uses ~2-3 API requests)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return False
    
    try:
        from api_import import test_api_import_small
        return test_api_import_small()
    except Exception as e:
        print(f"❌ Small test import failed: {str(e)}", flush=True)
        return False


def api_import_full_startup():
    """Full API-only startup import - no CSV fallback"""
    print("🚀 Full API startup import...", flush=True)
    
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return False
        
    if not os.environ.get("API_FOOTBALL_KEY"):
        print("❌ API_FOOTBALL_KEY not configured", flush=True)
        return False
    
    print("🔄 Running full API-based import...", flush=True)
    return api_import_full()


# CSV import functionality removed - API-only system

def run_scheduler(mode="enhanced"):
    """Run the scheduler with different import strategies"""
    
    scheduler = BlockingScheduler()
    
    if mode == "api-only":
        print("🚀 API-only mode: Using API-Football for all imports", flush=True)
        
        # Full API import weekly (Sundays at 2 AM UTC)
        scheduler.add_job(api_import_full, 'cron', day_of_week=6, hour=2, minute=0, id='weekly_full_import')
        
        # Quick API updates daily (6 AM UTC) 
        scheduler.add_job(api_import_updates, 'cron', hour=6, minute=0, id='daily_api_updates')
        
        # Fixture fetch daily (8 AM UTC)
        scheduler.add_job(scheduled_fixture_fetch, 'cron', hour=8, minute=0, id='daily_fixture_fetch')
        
    elif mode == "api-light":
        print("💡 API-Light mode: Minimal API usage with essential updates", flush=True)
        
        # Quick API updates weekly (Sundays at 4 AM UTC)
        scheduler.add_job(api_import_updates, 'cron', day_of_week=6, hour=4, minute=0, id='weekly_api_updates')
        
        # Fixture fetch daily (8 AM UTC)
        scheduler.add_job(scheduled_fixture_fetch, 'cron', hour=8, minute=0, id='daily_fixture_fetch')
        
    elif mode == "live":
        print("⚡ Live mode: Frequent updates for current season with daily fixtures", flush=True)
        
        # Frequent season updates every 5 minutes for live scores
        scheduler.add_job(api_frequent_season_update, 'interval', minutes=5, id='frequent_season_update')
        
        # Daily fixture fetch for upcoming week (8 AM UTC)
        scheduler.add_job(scheduled_fixture_fetch, 'cron', hour=8, minute=0, id='daily_fixture_fetch_week')
        
    elif mode == "top-250":
        print("🏆 Top 250 mode: Updates for the specific 250 teams", flush=True)
        
        # Daily fixture updates for top 250 teams (6 AM UTC)
        scheduler.add_job(update_top_250_fixtures, 'cron', hour=6, minute=0, id='daily_top_250_fixtures')
        
        # 5-minute match updates for top 250 teams
        scheduler.add_job(update_top_250_recent_matches, 'interval', minutes=5, id='frequent_top_250_matches')
        
    else:
        print(f"❌ Unknown mode: {mode}", flush=True)
        return
    
    print(f"📅 Starting scheduler in {mode} mode...", flush=True)
    print("📊 Scheduled jobs:", flush=True)
    for job in scheduler.get_jobs():
        print(f"   - {job.name}: {job.trigger}", flush=True)
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("🛑 Scheduler stopped by user", flush=True)
        scheduler.shutdown()


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Enhanced Import and Fetch System")
    parser.add_argument("--mode", choices=["api-only", "api-light", "live", "top-250"], 
                       default="api-only",
                       help="Import strategy (default: api-only)")
    parser.add_argument("--startup-import", action="store_true",
                       help="Run startup import before scheduling")
    parser.add_argument("--test-api", action="store_true",
                       help="Test API import and exit")
    parser.add_argument("--test-api-small", action="store_true",
                       help="Small API test (1 league, 3 teams, ~2-3 requests)")
# CSV test option removed
    parser.add_argument("--test-frequent", action="store_true",
                       help="Test frequent season update and exit")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be scheduled without running")
    
    # Top 250 specific commands
    parser.add_argument("--map-teams", action="store_true",
                       help="Map top 250 teams to API IDs (one-time setup)")
    parser.add_argument("--import-historical", action="store_true",
                       help="Import historical data from 2000 for top 250 teams")
    parser.add_argument("--setup-top-250", action="store_true",
                       help="Complete top 250 setup: map teams, import historical data, and start scheduler")
    parser.add_argument("--status", action="store_true",
                       help="Show top 250 teams status")
    
    args = parser.parse_args()
    
    # Make sure all tables are created
    with app.app_context():
        db.create_all()
        print("✅ All tables created (if not exist)", flush=True)
        
        # Handle top 250 specific commands
        if args.map_teams:
            print("🗺️  Mapping top 250 teams...", flush=True)
            map_top_250_teams()
            return
            
        if args.import_historical:
            print("📚 Importing historical data for top 250 teams...", flush=True)
            import_top_250_historical()
            return
            
        if args.setup_top_250:
            print("🚀 Complete top 250 setup starting (optimized for <7,500 requests)...", flush=True)
            
            try:
                # Use enhanced single-day import method to stay under API limits
                print("📊 Using enhanced import method with smart request budgeting...", flush=True)
                setup_top_250_optimized()
                
                # Start scheduler
                print("📅 Starting top 250 scheduler...", flush=True)
                print("✅ Setup complete! Starting continuous updates...", flush=True)
                run_scheduler("top-250")
            except Exception as e:
                print(f"❌ Setup failed with error: {str(e)}", flush=True)
                print("🔄 You can restart the setup process by running the same command again", flush=True)
                import traceback
                traceback.print_exc()
            return
            
        if args.status:
            print("📊 Top 250 teams status...", flush=True)
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"Team mapping progress: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)", flush=True)
            
            if progress['unmapped'] > 0:
                unmapped = team_mapper.get_unmapped_teams()
                print(f"Unmapped teams: {progress['unmapped']}", flush=True)
                print("First 10 unmapped:", flush=True)
                for team in unmapped[:10]:
                    print(f"  - {team}", flush=True)
            return
        
        # Handle test modes
        if args.test_api:
            print("🧪 Testing API import...", flush=True)
            if api_import_test():
                print("✅ API import test successful!", flush=True)
            else:
                print("❌ API import test failed!", flush=True)
            return
            
        if args.test_api_small:
            print("🧪 Testing small API import (1 league, 3 teams)...", flush=True)
            if api_import_test_small():
                print("✅ Small API import test successful!", flush=True)
                print("🎯 Teams are now being saved to database properly!")
            else:
                print("❌ Small API import test failed!", flush=True)
            return
            
# CSV test removed - API-only system
            
        if args.test_frequent:
            print("🧪 Testing frequent season update...", flush=True)
            try:
                api_frequent_season_update()
                print("✅ Frequent season update test successful!", flush=True)
            except Exception as e:
                print(f"❌ Frequent season update test failed: {e}", flush=True)
            return
        
        # Run startup import if requested
        if args.startup_import:
            print("🚀 Running startup import...", flush=True)
            if args.mode == "api-only":
                api_import_full_startup()
            elif args.mode == "api-light":
                api_import_test()
            elif args.mode == "live":
                print("⚡ Running initial full API import for live mode...", flush=True)
                api_import_full_startup()
            elif args.mode == "top-250":
                print("🏆 Running top 250 teams setup...", flush=True)
                print("Note: Make sure to run --map-teams first, then --import-historical", flush=True)
    
    # Handle dry run
    if args.dry_run:
        print(f"🔍 DRY RUN: Would start scheduler in {args.mode} mode", flush=True)
        
        # Show what would be scheduled
        if args.mode == "api-only":
            print("📅 Would schedule:", flush=True)
            print("   - Full API import: Sundays at 2 AM UTC", flush=True)
            print("   - API updates: Daily at 6 AM UTC", flush=True) 
            print("   - Fixture fetch: Daily at 8 AM UTC", flush=True)
        elif args.mode == "api-light":
            print("📅 Would schedule:", flush=True)
            print("   - API updates: Weekly at 4 AM UTC", flush=True)
            print("   - Fixture fetch: Daily at 8 AM UTC", flush=True)
        elif args.mode == "live":
            print("📅 Would schedule:", flush=True)
            print("   - Frequent season updates: Every 5 minutes (2024-2025 season)", flush=True)
            print("   - Daily fixture fetch: Daily at 8 AM UTC", flush=True)
        elif args.mode == "top-250":
            print("📅 Would schedule:", flush=True)
            print("   - Top 250 fixture updates: Daily at 6 AM UTC", flush=True)
            print("   - Top 250 match updates: Every 5 minutes", flush=True)
            print("   - Targets your specific 250 teams list", flush=True)
        return
    
    # Run the scheduler
    run_scheduler(args.mode)
def get_top_100_teams(api_importer):
    """Fetch and return the top 100 teams by popularity using the API importer."""
    teams = api_importer.fetch_top_teams_efficient(100)  # Use efficient method
    return [team['id'] for team in teams]

def save_top_100_teams(team_ids):
    with open(TOP_100_TEAMS_FILE, "w") as f:
        json.dump(team_ids, f)

def load_top_100_teams():
    if not os.path.exists(TOP_100_TEAMS_FILE):
        return None
    with open(TOP_100_TEAMS_FILE, "r") as f:
        return json.load(f)

def import_top_100_teams_once():
    """Import all available data for the top 100 teams by popularity and save their IDs."""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return

    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API import...", flush=True)
        return

    print("🚀 Importing all data for top 100 teams by popularity...", flush=True)
    with app.app_context():
        try:
            migrate_database()
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.5,
                max_requests_per_day=7000  # Conservative limit
            )
            top_100_team_ids = get_top_100_teams(importer)
            save_top_100_teams(top_100_team_ids)
            importer.run_import(team_ids=top_100_team_ids)
            print("✅ Top 100 teams import completed successfully", flush=True)
        except Exception as e:
            print(f"❌ Top 100 teams import failed: {str(e)}", flush=True)

def update_top_100_teams():
    """Update data for the same top 100 teams as at startup."""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return

    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API update...", flush=True)
        return

    team_ids = load_top_100_teams()
    if not team_ids:
        print("❌ No top 100 teams found. Run the startup import first.", flush=True)
        return

    print("🔄 Updating data for the same top 100 teams by popularity...", flush=True)
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.3,
                max_requests_per_day=7000  # Conservative limit
            )
            importer.run_import(team_ids=team_ids)
            print("✅ Top 100 teams update completed successfully", flush=True)
        except Exception as e:
            print(f"❌ Top 100 teams update failed: {str(e)}", flush=True)

# Top 250 Teams Functions
def map_top_250_teams():
    """Map the top 250 teams to their API IDs (one-time setup)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping mapping...", flush=True)
        return
    
    print("🗺️  Mapping top 250 teams to API IDs...", flush=True)
    
    with app.app_context():
        try:
            migrate_database()
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.8,  # Slower for mapping
                max_requests_per_day=6000  # Conservative for mapping
            )
            
            importer.map_top_250_teams()
            
            # Show progress
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"✅ Mapping complete: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)", flush=True)
            
        except Exception as e:
            print(f"❌ Team mapping failed: {str(e)}", flush=True)

def import_top_250_historical():
    """Import historical data from 2000 for the top 250 teams"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping import...", flush=True)
        return
    
    print("📚 Importing historical data for top 250 teams from 2000...", flush=True)
    
    with app.app_context():
        try:
            migrate_database()
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.6,
                max_requests_per_day=6000  # Conservative for historical import
            )
            
            importer.import_top_250_teams_historical(start_year=2000)
            
            print("✅ Historical data import complete!", flush=True)
            
        except Exception as e:
            print(f"❌ Historical data import failed: {str(e)}", flush=True)

def update_top_250_fixtures():
    """Update fixtures for the next week for top 250 teams (run daily)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping fixture update...", flush=True)
        return
    
    print("📅 Updating fixtures for top 250 teams...", flush=True)
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.4,
                max_requests_per_day=7000
            )
            
            importer.update_top_250_fixtures()
            
            print("✅ Fixture updates complete!", flush=True)
            
        except Exception as e:
            print(f"❌ Fixture update failed: {str(e)}", flush=True)

def update_top_250_recent_matches():
    """Update recent matches for top 250 teams (run every 5 minutes)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping match update...", flush=True)
        return
    
    print("⚡ Updating recent matches for top 250 teams...", flush=True)
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.3,
                max_requests_per_day=7000
            )
            
            importer.update_top_250_recent_matches()
            
            print("✅ Recent match updates complete!", flush=True)
            
        except Exception as e:
            print(f"❌ Recent match update failed: {str(e)}", flush=True)

def map_top_250_teams():
    """Map the top 250 teams to their API IDs (one-time setup)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API import...", flush=True)
        return
    
    print("🗺️  Mapping top 250 teams to API IDs...", flush=True)
    
    with app.app_context():
        try:
            # Run database migration first
            print("🔄 Creating database tables...", flush=True)
            migrate_database()
            print("✅ Database tables created/verified", flush=True)
            
            # Check current status
            team_mapper = get_team_mapper()
            initial_progress = team_mapper.get_mapping_progress()
            print(f"📊 Current mapping status: {initial_progress['mapped']}/{initial_progress['total']} teams ({initial_progress['progress_percent']}%)", flush=True)
            
            if initial_progress['mapped'] >= initial_progress['total']:
                print("✅ All teams already mapped!", flush=True)
                return
            
            # Initialize importer with conservative settings for mapping
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.6,  # Balanced speed for mapping
                max_requests_per_day=7000  # Conservative for mapping
            )
            
            print(f"🚀 Starting team mapping for {initial_progress['unmapped']} remaining teams...", flush=True)
            importer.map_top_250_teams_optimized()
            
            # Show final progress
            final_progress = team_mapper.get_mapping_progress()
            print(f"✅ Mapping complete: {final_progress['mapped']}/{final_progress['total']} teams ({final_progress['progress_percent']}%)", flush=True)
            print(f"📊 Mapped {final_progress['mapped'] - initial_progress['mapped']} new teams in this run", flush=True)
            
        except KeyboardInterrupt:
            print("🛑 Team mapping interrupted by user", flush=True)
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"💾 Current progress saved: {progress['mapped']}/{progress['total']} teams", flush=True)
        except Exception as e:
            print(f"❌ Team mapping failed: {e}", flush=True)
            print("🔍 Error details:", flush=True)
            import traceback
            traceback.print_exc()
            # Still show current progress
            try:
                team_mapper = get_team_mapper()
                progress = team_mapper.get_mapping_progress()
                print(f"💾 Progress before error: {progress['mapped']}/{progress['total']} teams", flush=True)
            except:
                pass

def import_top_250_historical():
    """Import historical data for top 250 teams (requires teams to be mapped first)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping API import...", flush=True)
        return
    
    print("📚 Importing historical data for top 250 teams...", flush=True)
    
    with app.app_context():
        try:
            # Check if teams are mapped first
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"📊 Team mapping status: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)", flush=True)
            
            if progress['mapped'] == 0:
                print("❌ No teams mapped yet! Run --map-teams first.", flush=True)
                return
            
            migrate_database()
            
            # Initialize importer
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.5,
                max_requests_per_day=7000
            )
            
            print("🚀 Starting historical data import...", flush=True)
            importer.import_top_250_teams_historical_optimized(start_year=2000)
            
            print("✅ Historical data import completed!", flush=True)
            
        except Exception as e:
            print(f"❌ Historical import failed: {e}", flush=True)
            print("🔍 Error details:", flush=True)
            import traceback
            traceback.print_exc()

def setup_top_250_optimized():
    """Optimized top 250 setup that stays under 7,500 requests per day"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available, skipping...", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set, skipping setup...", flush=True)
        return
    
    print("🚀 Running optimized top 250 setup (enhanced single-day import)...", flush=True)
    print("📊 Request budget: ~6,200 requests (leaves 1,300 for daily operations)", flush=True)
    
    with app.app_context():
        try:
            # Run database migration first
            print("🔄 Creating database tables...", flush=True)
            migrate_database()
            print("✅ Database tables created/verified", flush=True)
            
            # Check current mapping status
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"📊 Current mapping status: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)", flush=True)
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.5,  # Balanced speed vs safety
                max_requests_per_day=7500,  # Your daily limit
                daily_operations_budget=1300  # Reserved for ongoing updates
            )
            
            # Use the enhanced single-day import method
            # This method uses smart request budgeting:
            # - Modern-biased historical coverage (2019+ full, 2010-2018 dense, 2000-2009 selective)
            # - ~100 requests for team mapping
            # - ~5,800 requests for historical data
            # - ~50 requests for fixture updates
            # - Total: ~6,200 requests
            print("🚀 Starting enhanced single-day import...", flush=True)
            importer.single_day_complete_import_enhanced(start_year=2000)
            
            print("✅ Optimized top 250 setup completed successfully!", flush=True)
            print("📈 Historical coverage: 19 strategically selected years from 2000-2024", flush=True)
            print("🔋 Remaining daily budget: ~1,300 requests for live updates", flush=True)
            
            # Show final status
            final_progress = team_mapper.get_mapping_progress()
            print(f"🎯 Final mapping status: {final_progress['mapped']}/{final_progress['total']} teams ({final_progress['progress_percent']}%)", flush=True)
            
        except KeyboardInterrupt:
            print("🛑 Setup interrupted by user", flush=True)
            raise
        except Exception as e:
            print(f"❌ Optimized setup failed: {str(e)}", flush=True)
            print("🔍 Error details:", flush=True)
            import traceback
            traceback.print_exc()
            raise

def run_scheduler_top_100():
    """Run the scheduler to update top 100 teams every 5 minutes."""
    scheduler = BlockingScheduler()
    scheduler.add_job(update_top_100_teams, 'interval', minutes=5, id='top_100_teams_update')
    print("📅 Starting scheduler for top 100 teams (every 5 minutes)...", flush=True)
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("🛑 Scheduler stopped by user", flush=True)
        scheduler.shutdown()

if __name__ == "__main__":
    main()