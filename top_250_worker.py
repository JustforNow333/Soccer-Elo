#!/usr/bin/env python3
"""
Top 250 Teams Background Worker
Single command that handles the entire workflow intelligently
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from db import db
from api_import import APIFootballImporter
from top_250_teams import get_team_mapper
from migrate_db import migrate_database

class Top250Worker:
    """Intelligent background worker for top 250 teams"""
    
    def __init__(self):
        self.api_key = os.environ.get("API_FOOTBALL_KEY")
        self.status_file = "worker_status.json"
        self.load_status()
    
    def load_status(self):
        """Load worker status from file"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r') as f:
                    self.status = json.load(f)
            except:
                self.status = {}
        else:
            self.status = {}
        
        # Default status
        self.status.setdefault('teams_mapped', False)
        self.status.setdefault('historical_imported', False)
        self.status.setdefault('last_mapping_date', None)
        self.status.setdefault('last_historical_date', None)
        self.status.setdefault('scheduler_running', False)
    
    def save_status(self):
        """Save worker status to file"""
        try:
            with open(self.status_file, 'w') as f:
                json.dump(self.status, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save status: {e}")
    
    def check_api_key(self):
        """Check if API key is available"""
        if not self.api_key:
            print("❌ API_FOOTBALL_KEY not set in environment variables")
            print("   Please set your API key: export API_FOOTBALL_KEY='your_key_here'")
            return False
        return True
    
    def get_mapping_progress(self):
        """Get team mapping progress"""
        try:
            team_mapper = get_team_mapper()
            return team_mapper.get_mapping_progress()
        except Exception as e:
            print(f"⚠️  Could not get mapping progress: {e}")
            return {'mapped': 0, 'total': 250, 'progress_percent': 0}
    
    def should_run_mapping(self):
        """Check if team mapping should be run"""
        progress = self.get_mapping_progress()
        
        # If less than 200 teams mapped, definitely need mapping
        if progress['mapped'] < 200:
            return True
        
        # If mapped recently (within 7 days), probably don't need to re-map
        if self.status.get('last_mapping_date'):
            try:
                last_date = datetime.fromisoformat(self.status['last_mapping_date'])
                if (datetime.now() - last_date).days < 7:
                    return False
            except:
                pass
        
        return not self.status.get('teams_mapped', False)
    
    def should_run_historical(self):
        """Check if historical import should be run"""
        # If historical import done recently (within 30 days), skip
        if self.status.get('last_historical_date'):
            try:
                last_date = datetime.fromisoformat(self.status['last_historical_date'])
                if (datetime.now() - last_date).days < 30:
                    return False
            except:
                pass
        
        # Need good mapping progress first
        progress = self.get_mapping_progress()
        if progress['mapped'] < 200:
            return False
        
        return not self.status.get('historical_imported', False)
    
    def run_single_day_complete_import(self):
        """Run complete optimized single-day import under 7500 requests"""
        print("🚀 Running complete single-day optimized import...")
        
        try:
            with app.app_context():
                migrate_database()
                
                importer = APIFootballImporter(
                    api_key=self.api_key,
                    current_season=datetime.now().year,
                    request_delay=0.5,  # Balanced speed
                    max_requests_per_day=7400,  # Use most of daily limit with buffer
                    daily_operations_budget=1300  # Reserve budget for ongoing operations
                )
                
                importer.single_day_complete_import_enhanced(start_year=2000)
                
                # Update status
                self.status['teams_mapped'] = True
                self.status['historical_imported'] = True
                self.status['last_mapping_date'] = datetime.now().isoformat()
                self.status['last_historical_date'] = datetime.now().isoformat()
                self.save_status()
                
                print("✅ Complete single-day import successful!")
                return True
                
        except Exception as e:
            print(f"❌ Single-day import failed: {e}")
            return False

    def run_mapping(self):
        """Run team mapping if needed"""
        if not self.should_run_mapping():
            progress = self.get_mapping_progress()
            print(f"✅ Team mapping up to date: {progress['mapped']}/{progress['total']} teams mapped")
            return True
        
        print("🗺️  Running optimized team mapping...")
        
        try:
            with app.app_context():
                migrate_database()
                
                importer = APIFootballImporter(
                    api_key=self.api_key,
                    current_season=datetime.now().year,
                    request_delay=0.8,
                    max_requests_per_day=7400  # Higher limit for single operations
                )
                
                importer.map_top_250_teams_optimized()
                
                # Update status
                self.status['teams_mapped'] = True
                self.status['last_mapping_date'] = datetime.now().isoformat()
                self.save_status()
                
                progress = self.get_mapping_progress()
                print(f"✅ Team mapping complete: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)")
                
                return True
                
        except Exception as e:
            print(f"❌ Team mapping failed: {e}")
            return False
    
    def run_historical_import(self):
        """Run optimized historical import if needed"""
        if not self.should_run_historical():
            print("✅ Historical import up to date or mapping insufficient")
            return True
        
        print("📚 Running optimized historical data import from 2000...")
        
        try:
            with app.app_context():
                migrate_database()
                
                importer = APIFootballImporter(
                    api_key=self.api_key,
                    current_season=datetime.now().year,
                    request_delay=0.6,
                    max_requests_per_day=7400  # Higher limit for single operations
                )
                
                importer.import_top_250_teams_historical_enhanced(start_year=2000)
                
                # Update status
                self.status['historical_imported'] = True
                self.status['last_historical_date'] = datetime.now().isoformat()
                self.save_status()
                
                print("✅ Optimized historical data import complete!")
                return True
                
        except Exception as e:
            print(f"❌ Historical import failed: {e}")
            return False
    
    def update_fixtures(self):
        """Update fixtures for top 250 teams"""
        print("📅 Updating fixtures for top 250 teams...")
        
        try:
            with app.app_context():
                importer = APIFootballImporter(
                    api_key=self.api_key,
                    current_season=datetime.now().year,
                    request_delay=0.4,
                    max_requests_per_day=7400,
                    daily_operations_budget=1300  # Conservative budget for daily operations
                )
                
                importer.update_top_250_fixtures()
                print("✅ Fixture updates complete!")
                return True
                
        except Exception as e:
            print(f"❌ Fixture update failed: {e}")
            return False
    
    def update_recent_matches(self):
        """Update recent matches for top 250 teams"""
        print("⚡ Updating recent matches for top 250 teams...")
        
        try:
            with app.app_context():
                importer = APIFootballImporter(
                    api_key=self.api_key,
                    current_season=datetime.now().year,
                    request_delay=0.3,
                    max_requests_per_day=7400,
                    daily_operations_budget=1300  # Conservative budget for daily operations  
                )
                
                importer.update_top_250_recent_matches()
                print("✅ Recent match updates complete!")
                return True
                
        except Exception as e:
            print(f"❌ Recent match update failed: {e}")
            return False
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🚀 Starting Top 250 Teams setup...")
        print("=" * 60)
        
        # Check API key
        if not self.check_api_key():
            return False
        
        # Initialize database
        with app.app_context():
            db.create_all()
            print("✅ Database initialized")
        
        # Show current status
        progress = self.get_mapping_progress()
        print(f"📊 Current status:")
        print(f"   - Teams mapped: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
        print(f"   - Historical imported: {self.status.get('historical_imported', False)}")
        print("")
        
        # Step 1: Team mapping
        if not self.run_mapping():
            print("❌ Setup failed at team mapping step")
            return False
        
        # Step 2: Historical import
        if not self.run_historical_import():
            print("❌ Setup failed at historical import step")
            return False
        
        print("🎉 Setup complete! Ready for live updates.")
        return True
    
    def run_scheduler(self):
        """Run the live update scheduler"""
        print("🔄 Starting live update scheduler...")
        
        # Check if setup is complete
        progress = self.get_mapping_progress()
        if progress['mapped'] < 200:
            print("❌ Need to complete setup first (insufficient team mapping)")
            print("   Run: python3 top_250_worker.py --setup")
            return False
        
        scheduler = BlockingScheduler()
        
        # Daily fixture updates at 6 AM UTC
        scheduler.add_job(
            self.update_fixtures,
            'cron',
            hour=6,
            minute=0,
            id='daily_fixtures'
        )
        
        # 5-minute match updates
        scheduler.add_job(
            self.update_recent_matches,
            'interval',
            minutes=5,
            id='recent_matches'
        )
        
        # Update status
        self.status['scheduler_running'] = True
        self.save_status()
        
        print("📅 Scheduled jobs:")
        print("   - Daily fixture updates: 6:00 AM UTC (~250 requests)")
        print("   - Recent match updates: Every 5 minutes (5-10 teams per cycle)")
        print("   - Total daily operations budget: 1300 requests/day")
        print("   - Smart budget management: Automatically scales based on usage")
        print("")
        print("🔄 Scheduler running... (Press Ctrl+C to stop)")
        
        try:
            scheduler.start()
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            self.status['scheduler_running'] = False
            self.save_status()
            scheduler.shutdown()
    
    def run_complete_workflow(self):
        """Run the complete workflow: setup + scheduler"""
        print("🚀 Starting complete Top 250 Teams workflow...")
        print("=" * 60)
        
        # Run setup
        if not self.run_setup():
            print("❌ Setup failed, cannot start scheduler")
            return False
        
        print("\n" + "=" * 60)
        print("🔄 Setup complete, starting live updates...")
        
        # Small delay before starting scheduler
        time.sleep(2)
        
        # Run scheduler
        self.run_scheduler()
        
        return True
    
    def show_status(self):
        """Show detailed status"""
        print("📊 Top 250 Teams Worker Status")
        print("=" * 50)
        
        # API Key
        print(f"🔑 API Key: {'✅ Set' if self.api_key else '❌ Missing'}")
        
        # Team Mapping
        progress = self.get_mapping_progress()
        print(f"🗺️  Team Mapping: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
        
        if self.status.get('last_mapping_date'):
            last_date = datetime.fromisoformat(self.status['last_mapping_date'])
            print(f"   Last mapped: {last_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Historical Import
        historical_status = "✅ Complete" if self.status.get('historical_imported') else "❌ Pending"
        print(f"📚 Historical Import: {historical_status}")
        
        if self.status.get('last_historical_date'):
            last_date = datetime.fromisoformat(self.status['last_historical_date'])
            print(f"   Last imported: {last_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Scheduler
        scheduler_status = "🔄 Running" if self.status.get('scheduler_running') else "⏸️  Stopped"
        print(f"🔄 Scheduler: {scheduler_status}")
        
        # API Usage
        print(f"\n📈 API Usage Today:")
        try:
            today = datetime.now().strftime('%Y%m%d')
            log_file = f"api_requests_{today}.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    requests_today = len(f.readlines())
                print(f"   Requests made: {requests_today}")
                print(f"   Requests remaining: {7500 - requests_today}")
            else:
                print("   No requests logged today")
        except Exception as e:
            print(f"   Could not read request log: {e}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if not self.api_key:
            print("   - Set API_FOOTBALL_KEY environment variable")
        
        if progress['mapped'] < 200:
            print("   - Run team mapping: --setup or --map-only")
        
        if progress['mapped'] >= 200 and not self.status.get('historical_imported'):
            print("   - Run historical import: --setup or --historical-only")
        
        if progress['mapped'] >= 200 and self.status.get('historical_imported'):
            print("   - Ready for live updates: --scheduler or --complete")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Top 250 Teams Background Worker")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--complete", action="store_true",
                      help="Run complete workflow (setup + scheduler)")
    group.add_argument("--single-day", action="store_true",
                      help="Run optimized single-day complete import under 7500 requests")
    group.add_argument("--setup", action="store_true",
                      help="Run setup only (mapping + historical import)")
    group.add_argument("--scheduler", action="store_true",
                      help="Run scheduler only (live updates)")
    group.add_argument("--status", action="store_true",
                      help="Show current status")
    group.add_argument("--map-only", action="store_true",
                      help="Run team mapping only")
    group.add_argument("--historical-only", action="store_true",
                      help="Run historical import only")
    
    args = parser.parse_args()
    
    worker = Top250Worker()
    
    if args.complete:
        worker.run_complete_workflow()
    elif args.single_day:
        if worker.run_single_day_complete_import():
            print("\n🔄 Starting live updates scheduler...")
            worker.run_scheduler()
    elif args.setup:
        worker.run_setup()
    elif args.scheduler:
        worker.run_scheduler()
    elif args.status:
        worker.show_status()
    elif args.map_only:
        worker.run_mapping()
    elif args.historical_only:
        worker.run_historical_import()

if __name__ == "__main__":
    main()