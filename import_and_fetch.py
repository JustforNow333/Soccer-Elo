import os
import sys
import argparse
from datetime import datetime
import json
print("🟢 STARTED import_and_fetch.py", flush=True)
from db import db
from app import app
# CSV imports removed - using API-Football only
from fixture_import import fetch_next_48_hours_fixtures
from apscheduler.schedulers.blocking import BlockingScheduler\


# Define the file path for storing top 250 teams
TOP_250_TEAMS_FILE = "top_250_teams.json"

# Import the new API-Football system
try:
    from api_import import APIFootballImporter
    from migrate_db import migrate_database
    API_IMPORT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  API import system not available: {e}", flush=True)
    API_IMPORT_AVAILABLE = False

# CSV scheduled fetch removed - using API-Football only

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
                request_delay=0.6  # Slightly slower for scheduled runs
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
                request_delay=0.5
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
                request_delay=0.3  # Faster for frequent updates
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
                request_delay=0.3
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


# CSV import functions removed - using API-Football only

def import_top_250_teams_initial():
    """One-time import of top 250 teams with full history from 2000 onwards"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return False
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set", flush=True)
        return False
    
    print("🚀 Starting one-time import of top 250 teams with full history...", flush=True)
    
    with app.app_context():
        try:
            migrate_database()
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=2024,
                request_delay=0.4  # Slightly conservative for large import
            )
            
            # Get top 250 teams by popularity
            print("🔄 Fetching top 250 teams by popularity...")
            all_teams = importer.fetch_all_teams()
            teams_sorted = sorted(all_teams, key=lambda t: t['popularity'], reverse=True)
            top_250_teams = teams_sorted[:250]
            
            # Save team IDs for future reference
            team_ids = [team['id'] for team in top_250_teams]
            save_top_250_teams(team_ids)
            
            print(f"✅ Selected top 250 teams")
            print(f"📊 Sample teams: {[t['name'] for t in top_250_teams[:5]]}")
            
            # Import historical data from 2000 onwards for these teams
            seasons_to_import = list(range(2000, 2025))  # 2000 to 2024
            
            for season in seasons_to_import:
                print(f"🔄 Importing season {season}-{season+1}...")
                importer.current_season = season
                
                # Import data for our top 250 teams for this season
                importer.import_teams_by_ids_for_season(team_ids, season)
                
                # Check if we're approaching API limits
                remaining = importer.max_requests_per_day - importer.requests_made
                if remaining < 200:  # Safety buffer
                    print(f"⚠️  Approaching API limit ({remaining} requests left). Stopping at season {season}")
                    break
            
            print("✅ Top 250 teams historical import completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Top 250 teams import failed: {str(e)}", flush=True)
            return False

def update_top_250_teams_current_season():
    """Update data for top 250 teams - current season only (2024-2025)"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set", flush=True)
        return
    
    # Load saved team IDs
    team_ids = load_top_250_teams()
    if not team_ids:
        print("❌ No top 250 teams found. Run initial import first.", flush=True)
        return
    
    print(f"🔄 Updating current season data for {len(team_ids)} teams...", flush=True)
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=2024,
                request_delay=0.3  # Faster for frequent updates
            )
            
            # Import only 2024-2025 season data
            importer.import_teams_by_ids_for_season(team_ids, 2024)
            
            print("✅ Top 250 teams current season update completed", flush=True)
            
        except Exception as e:
            print(f"❌ Top 250 teams update failed: {str(e)}", flush=True)

def fetch_upcoming_fixtures_for_top_250():
    """Fetch upcoming fixtures for the next week for all top 250 teams"""
    if not API_IMPORT_AVAILABLE:
        print("❌ API import system not available", flush=True)
        return
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set", flush=True)
        return
    
    # Load saved team IDs
    team_ids = load_top_250_teams()
    if not team_ids:
        print("❌ No top 250 teams found. Run initial import first.", flush=True)
        return
    
    print(f"🔄 Fetching upcoming fixtures for {len(team_ids)} teams...", flush=True)
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=2024,
                request_delay=0.3
            )
            
            # Fetch fixtures for next 7 days for our teams
            from datetime import datetime, timedelta
            today = datetime.now()
            end_date = today + timedelta(days=7)
            
            importer.fetch_fixtures_for_teams(team_ids, today, end_date)
            
            print("✅ Upcoming fixtures fetch completed", flush=True)
            
        except Exception as e:
            print(f"❌ Fixtures fetch failed: {str(e)}", flush=True)

def save_top_250_teams(team_ids):
    """Save top 250 team IDs to file"""
    with open(TOP_250_TEAMS_FILE, "w") as f:
        json.dump(team_ids, f)
    print(f"💾 Saved {len(team_ids)} team IDs")

def load_top_250_teams():
    """Load top 250 team IDs from file"""
    if not os.path.exists(TOP_250_TEAMS_FILE):
        return None
    with open(TOP_250_TEAMS_FILE, "r") as f:
        return json.load(f)

def run_top_250_scheduler():
    """Run the scheduler for top 250 teams system"""
    print("🚀 Starting Top 250 Teams Scheduler", flush=True)
    
    scheduler = BlockingScheduler()
    
    # Every 5 minutes: Update current season data for top 250 teams
    scheduler.add_job(
        update_top_250_teams_current_season, 
        'interval', 
        minutes=5, 
        id='top_250_current_updates'
    )
    
    # Daily at 6 AM UTC: Fetch upcoming fixtures for next week
    scheduler.add_job(
        fetch_upcoming_fixtures_for_top_250,
        'cron',
        hour=6,
        minute=0,
        id='daily_fixtures_fetch'
    )
    
    print("📅 Scheduled jobs:", flush=True)
    for job in scheduler.get_jobs():
        print(f"   - {job.name}: {job.trigger}", flush=True)
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("🛑 Scheduler stopped by user", flush=True)
        scheduler.shutdown()


def main():
    """Main function - automatically handles initial import and ongoing scheduling"""
    parser = argparse.ArgumentParser(description="Top 250 Football Teams Import System")
    parser.add_argument("--force-initial-import", action="store_true",
                       help="Force re-run of initial import even if teams already exist")
    parser.add_argument("--test-current-update", action="store_true",
                       help="Test current season update and exit")
    parser.add_argument("--test-fixtures", action="store_true",
                       help="Test fixture fetch and exit")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be scheduled without running")
    
    args = parser.parse_args()
    
    # Make sure all tables are created
    with app.app_context():
        db.create_all()
        print("✅ All tables created (if not exist)", flush=True)
        
        # Handle test modes
        if args.test_current_update:
            print("🧪 Testing current season update...", flush=True)
            update_top_250_teams_current_season()
            return
            
        if args.test_fixtures:
            print("🧪 Testing fixture fetch...", flush=True)
            fetch_upcoming_fixtures_for_top_250()
            return
        
        # Handle dry run
        if args.dry_run:
            print("🔍 DRY RUN: Top 250 Teams Scheduler", flush=True)
            print("📅 Would schedule:", flush=True)
            print("   - Current season updates: Every 5 minutes", flush=True)
            print("   - Fixture fetch: Daily at 6 AM UTC", flush=True)
            return
        
        # Check if we need to run initial import
        team_ids = load_top_250_teams()
        
        if not team_ids or args.force_initial_import:
            if args.force_initial_import:
                print("🔄 Force initial import requested...", flush=True)
            else:
                print("🔍 No existing team data found. Running initial import...", flush=True)
            
            if import_top_250_teams_initial():
                print("✅ Initial import completed successfully", flush=True)
                print("🔄 Now starting ongoing scheduler...", flush=True)
            else:
                print("❌ Initial import failed. Cannot start scheduler.", flush=True)
                return
        else:
            print(f"✅ Found existing data for {len(team_ids)} teams", flush=True)
            print("🔄 Starting ongoing scheduler...", flush=True)
    
    # Run the ongoing scheduler
    run_top_250_scheduler()
# Old functions removed - using new top 250 system

if __name__ == "__main__":
    main()