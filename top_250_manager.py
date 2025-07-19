#!/usr/bin/env python3
"""
Top 250 Teams Manager
Specialized script for managing the top 250 teams import and updates
"""

import os
import sys
import argparse
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from db import db
from api_import import APIFootballImporter
from top_250_teams import get_team_mapper
from migrate_db import migrate_database

def map_teams():
    """Map the top 250 teams to their API IDs (run once when API limit resets)"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set")
        return
    
    print("🗺️  Mapping top 250 teams to API IDs...")
    
    with app.app_context():
        try:
            migrate_database()
            
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.8,  # Slower for mapping to be safe
                max_requests_per_day=6000  # Conservative for mapping
            )
            
            importer.map_top_250_teams()
            
            # Show progress
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"✅ Mapping complete: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)")
            
        except Exception as e:
            print(f"❌ Team mapping failed: {e}")

def import_historical_data():
    """Import historical data from 2000 for the top 250 teams"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set")
        return
    
    print("📚 Importing historical data for top 250 teams from 2000...")
    
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
            
            print("✅ Historical data import complete!")
            
        except Exception as e:
            print(f"❌ Historical data import failed: {e}")

def update_fixtures():
    """Update fixtures for the next week for top 250 teams (run daily)"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set")
        return
    
    print("📅 Updating fixtures for top 250 teams...")
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.4,
                max_requests_per_day=7000
            )
            
            importer.update_top_250_fixtures()
            
            print("✅ Fixture updates complete!")
            
        except Exception as e:
            print(f"❌ Fixture update failed: {e}")

def update_recent_matches():
    """Update recent matches for top 250 teams (run every 5 minutes)"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not set")
        return
    
    print("⚡ Updating recent matches for top 250 teams...")
    
    with app.app_context():
        try:
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.3,
                max_requests_per_day=7000
            )
            
            importer.update_top_250_recent_matches()
            
            print("✅ Recent match updates complete!")
            
        except Exception as e:
            print(f"❌ Recent match update failed: {e}")

def run_scheduler():
    """Run the scheduler for top 250 teams updates"""
    print("🚀 Starting Top 250 Teams scheduler...")
    
    scheduler = BlockingScheduler()
    
    # Daily fixture updates at 6 AM UTC
    scheduler.add_job(
        update_fixtures, 
        'cron', 
        hour=6, 
        minute=0, 
        id='daily_fixture_update'
    )
    
    # 5-minute match updates
    scheduler.add_job(
        update_recent_matches, 
        'interval', 
        minutes=5, 
        id='frequent_match_update'
    )
    
    print("📅 Scheduled jobs:")
    print("   - Daily fixture updates: 6:00 AM UTC")
    print("   - Recent match updates: Every 5 minutes")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("🛑 Scheduler stopped by user")
        scheduler.shutdown()

def status():
    """Show status of team mappings and system"""
    print("📊 Top 250 Teams Status")
    print("=" * 50)
    
    team_mapper = get_team_mapper()
    progress = team_mapper.get_mapping_progress()
    
    print(f"Team Mapping Progress: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
    
    if progress['unmapped'] > 0:
        print(f"Unmapped teams: {progress['unmapped']}")
        unmapped = team_mapper.get_unmapped_teams()
        print("First 10 unmapped teams:")
        for team in unmapped[:10]:
            print(f"  - {team}")
        if len(unmapped) > 10:
            print(f"  ... and {len(unmapped) - 10} more")
    
    # Check if we can proceed with historical import
    if progress['mapped'] >= 130:  # Temporarily lowered from 200 teams mapped
        print("✅ Ready for historical data import")
    else:
        print("⚠️  Need more teams mapped before historical import")
    
    print("\nAPI Request Log Files:")
    import glob
    log_files = glob.glob("api_requests_*.log")
    for log_file in sorted(log_files):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
            date_str = log_file.split('_')[2].split('.')[0]
            print(f"  {date_str}: {len(lines)} requests")
        except:
            pass

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Top 250 Teams Manager")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Map teams command
    map_parser = subparsers.add_parser('map', help='Map team names to API IDs')
    
    # Import historical data command
    import_parser = subparsers.add_parser('import-historical', help='Import historical data from 2000')
    
    # Update fixtures command
    fixtures_parser = subparsers.add_parser('update-fixtures', help='Update upcoming fixtures')
    
    # Update recent matches command
    matches_parser = subparsers.add_parser('update-matches', help='Update recent matches')
    
    # Run scheduler command
    scheduler_parser = subparsers.add_parser('scheduler', help='Run the update scheduler')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize Flask app context
    with app.app_context():
        db.create_all()
        
        if args.command == 'map':
            map_teams()
        elif args.command == 'import-historical':
            import_historical_data()
        elif args.command == 'update-fixtures':
            update_fixtures()
        elif args.command == 'update-matches':
            update_recent_matches()
        elif args.command == 'scheduler':
            run_scheduler()
        elif args.command == 'status':
            status()

if __name__ == "__main__":
    main()