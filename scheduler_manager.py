#!/usr/bin/env python3
"""
Scheduler Manager
Manages all periodic tasks for the soccer ELO system
"""

import os
import sys
import time
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SoccerEloScheduler:
    """Manages all periodic tasks for the soccer ELO system"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_run_times: Dict[str, datetime] = {}
        self.task_stats: Dict[str, Dict[str, Any]] = {}
        
    def log_task_execution(self, task_name: str, success: bool, details: str = ""):
        """Log task execution results"""
        now = datetime.now()
        self.last_run_times[task_name] = now
        
        if task_name not in self.task_stats:
            self.task_stats[task_name] = {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0,
                'last_success': None,
                'last_failure': None
            }
        
        stats = self.task_stats[task_name]
        stats['total_runs'] += 1
        
        if success:
            stats['successful_runs'] += 1
            stats['last_success'] = now
            status = "✅"
        else:
            stats['failed_runs'] += 1
            stats['last_failure'] = now
            status = "❌"
        
        print(f"{status} [{now.strftime('%Y-%m-%d %H:%M:%S')}] {task_name}: {details}")
    
    def update_match_results(self):
        """Update match results every 3 hours"""
        try:
            print("\n🔄 Starting 3-hour match results update...")
            
            # Import and run the match results updater
            from match_results_updater import main as update_matches
            success = update_matches()
            
            if success:
                self.log_task_execution("match_results_update", True, "Match results updated successfully")
            else:
                self.log_task_execution("match_results_update", False, "No matches processed")
                
        except Exception as e:
            self.log_task_execution("match_results_update", False, f"Error: {e}")
    
    def update_upcoming_fixtures(self):
        """Update upcoming fixtures daily"""
        try:
            print("\n📅 Starting daily upcoming fixtures update...")
            
            # Import and run the fixtures updater
            from daily_fixtures_update import main as update_fixtures
            success = update_fixtures()
            
            if success:
                self.log_task_execution("upcoming_fixtures_update", True, "Upcoming fixtures updated successfully")
            else:
                self.log_task_execution("upcoming_fixtures_update", False, "Fixtures update failed")
                
        except Exception as e:
            self.log_task_execution("upcoming_fixtures_update", False, f"Error: {e}")
    
    def run_elo_maintenance(self):
        """Run ELO maintenance daily"""
        try:
            print("\n🏆 Starting daily ELO maintenance...")
            
            # Import and run ELO maintenance
            from daily_elo_maintenance import main as elo_maintenance
            success = elo_maintenance()
            
            if success:
                self.log_task_execution("elo_maintenance", True, "ELO maintenance completed successfully")
            else:
                self.log_task_execution("elo_maintenance", False, "ELO maintenance failed")
                
        except Exception as e:
            self.log_task_execution("elo_maintenance", False, f"Error: {e}")
    
    def cleanup_old_data(self):
        """Clean up old data weekly"""
        try:
            print("\n🧹 Starting weekly data cleanup...")
            
            # Initialize Flask app context
            from app import app
            with app.app_context():
                from db import db, Fixture, EloRating
                
                # Remove very old upcoming fixtures (older than 1 week)
                cutoff_date = datetime.now() - timedelta(days=7)
                old_fixtures = Fixture.query.filter(
                    Fixture.date < cutoff_date,
                    Fixture.status.in_(["NS", "TBD", "POST"])
                ).all()
                
                if old_fixtures:
                    for fixture in old_fixtures:
                        db.session.delete(fixture)
                    db.session.commit()
                    
                    self.log_task_execution("data_cleanup", True, 
                                          f"Cleaned up {len(old_fixtures)} old fixtures")
                else:
                    self.log_task_execution("data_cleanup", True, "No old data to clean up")
                
        except Exception as e:
            self.log_task_execution("data_cleanup", False, f"Error: {e}")
    
    def health_check(self):
        """Perform system health check"""
        try:
            print("\n🔍 Running system health check...")
            
            from app import app
            with app.app_context():
                from db import db, Team, Match, EloRating, Fixture
                
                # Count records
                team_count = Team.query.count()
                match_count = Match.query.count()
                elo_count = EloRating.query.count()
                fixture_count = Fixture.query.count()
                
                # Check for recent activity
                recent_matches = Match.query.filter(
                    Match.date >= (datetime.now() - timedelta(days=7)).date()
                ).count()
                
                recent_fixtures = Fixture.query.filter(
                    Fixture.date >= datetime.now() - timedelta(days=1)
                ).count()
                
                health_info = (
                    f"Teams: {team_count}, Matches: {match_count}, "
                    f"ELO ratings: {elo_count}, Fixtures: {fixture_count}, "
                    f"Recent matches: {recent_matches}, Recent fixtures: {recent_fixtures}"
                )
                
                self.log_task_execution("health_check", True, health_info)
                
        except Exception as e:
            self.log_task_execution("health_check", False, f"Error: {e}")
    
    def setup_schedule(self):
        """Set up the schedule for all tasks"""
        print("📅 Setting up task schedule...")
        
        # Match results update every 3 hours
        schedule.every(3).hours.do(self.update_match_results)
        
        # Upcoming fixtures update daily at 6 AM
        schedule.every().day.at("06:00").do(self.update_upcoming_fixtures)
        
        # ELO maintenance daily at 2 AM
        schedule.every().day.at("02:00").do(self.run_elo_maintenance)
        
        # Data cleanup weekly on Sunday at 1 AM
        schedule.every().sunday.at("01:00").do(self.cleanup_old_data)
        
        # Health check every 6 hours
        schedule.every(6).hours.do(self.health_check)
        
        print("✅ Schedule configured:")
        print("   🔄 Match results: Every 3 hours")
        print("   📅 Upcoming fixtures: Daily at 6:00 AM")
        print("   🏆 ELO maintenance: Daily at 2:00 AM")
        print("   🧹 Data cleanup: Weekly on Sunday at 1:00 AM")
        print("   🔍 Health check: Every 6 hours")
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        print("🚀 Starting scheduler thread...")
        self.running = True
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            print("⚠️  Scheduler is already running")
            return
        
        self.setup_schedule()
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()
        
        print("✅ Scheduler started successfully")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            print("⚠️  Scheduler is not running")
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        
        print("🛑 Scheduler stopped")
    
    def status(self):
        """Show scheduler status"""
        print(f"📊 Scheduler Status: {'🟢 Running' if self.running else '🔴 Stopped'}")
        print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.task_stats:
            print("\n📈 Task Statistics:")
            for task_name, stats in self.task_stats.items():
                success_rate = (stats['successful_runs'] / stats['total_runs']) * 100 if stats['total_runs'] > 0 else 0
                print(f"   {task_name}:")
                print(f"     Total runs: {stats['total_runs']}")
                print(f"     Success rate: {success_rate:.1f}%")
                if stats['last_success']:
                    print(f"     Last success: {stats['last_success'].strftime('%Y-%m-%d %H:%M:%S')}")
                if stats['last_failure']:
                    print(f"     Last failure: {stats['last_failure'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n⏰ Next scheduled runs:")
        for job in schedule.jobs:
            print(f"   {job.job_func.__name__}: {job.next_run}")
    
    def run_task_now(self, task_name: str):
        """Run a specific task immediately"""
        tasks = {
            'match_results': self.update_match_results,
            'fixtures': self.update_upcoming_fixtures,
            'elo_maintenance': self.run_elo_maintenance,
            'cleanup': self.cleanup_old_data,
            'health_check': self.health_check
        }
        
        if task_name not in tasks:
            print(f"❌ Unknown task: {task_name}")
            print(f"Available tasks: {', '.join(tasks.keys())}")
            return False
        
        print(f"🚀 Running task immediately: {task_name}")
        tasks[task_name]()
        return True

def main():
    """Main function for scheduler management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Soccer ELO Scheduler Manager')
    parser.add_argument('--start', action='store_true', help='Start the scheduler')
    parser.add_argument('--status', action='store_true', help='Show scheduler status')
    parser.add_argument('--run-task', type=str, help='Run specific task now')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (keeps running)')
    
    args = parser.parse_args()
    
    scheduler = SoccerEloScheduler()
    
    if args.status:
        scheduler.status()
        return True
    
    if args.run_task:
        return scheduler.run_task_now(args.run_task)
    
    if args.start or args.daemon:
        try:
            scheduler.start()
            
            if args.daemon:
                print("🔄 Running as daemon. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(60)
                        if not scheduler.running:
                            break
                except KeyboardInterrupt:
                    print("\n🛑 Stopping scheduler...")
                    scheduler.stop()
            else:
                print("✅ Scheduler started in background")
                time.sleep(2)
                scheduler.status()
            
            return True
        except Exception as e:
            print(f"❌ Error starting scheduler: {e}")
            return False
    
    # Default: show help
    parser.print_help()
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)