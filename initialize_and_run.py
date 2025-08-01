#!/usr/bin/env python3
"""
Initialize and Run Complete System
1. First: Complete data import (teams, matches, ELO calculation)
2. Then: Start daily cycle (weekly fixtures + 3-hour match updates)
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SoccerEloSystemManager:
    """Manages complete system initialization and daily operations"""
    
    def __init__(self):
        self.api_key = os.environ.get('API_FOOTBALL_KEY')
        self.initialization_complete = False
        self.daily_cycle_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
    def validate_environment(self) -> bool:
        """Validate required environment variables"""
        if not self.api_key:
            print("❌ API_FOOTBALL_KEY environment variable not found")
            print("💡 Set your API Football key:")
            print("   export API_FOOTBALL_KEY='your_api_key_here'")
            return False
        
        # Check database connection
        try:
            from app import app
            with app.app_context():
                from db import db
                from sqlalchemy import text
                db.session.execute(text("SELECT 1"))
                print("✅ Database connection verified")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
        
        return True
    
    def run_complete_initialization(self) -> bool:
        """Run complete system initialization"""
        print("🚀 PHASE 1: COMPLETE SYSTEM INITIALIZATION")
        print("=" * 60)
        print("This will:")
        print("• Import top 250 teams via league-based discovery")
        print("• Import comprehensive match history (2010-2025)")
        print("• Calculate enhanced ELO ratings with adaptive K-factors")
        print("• Fetch upcoming fixtures for next 7 days")
        print("• Estimated time: 45-90 minutes")
        print("• API requests used: ~6,000-7,000 (within daily limit)")
        print()
        
        # Check if running in non-interactive mode
        import sys
        if not sys.stdin.isatty():
            print("🤖 Running in non-interactive mode (background worker)")
            print("🚀 Auto-proceeding with complete initialization...")
            user_confirm = 'y'
        else:
            try:
                user_confirm = input("Continue with complete initialization? (y/N): ").lower()
                if user_confirm != 'y':
                    print("🛑 Initialization cancelled by user")
                    return False
            except (KeyboardInterrupt, EOFError):
                print("\n🛑 Initialization cancelled or no input available")
                return False
        
        start_time = datetime.now()
        print(f"\n🕐 Starting complete initialization at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Step 1: Run complete import
            print("\n" + "="*60)
            print("🔄 STEP 1: Running complete team and match import...")
            print("="*60)
            
            from run_complete_import import run_complete_import
            success = run_complete_import()
            
            if not success:
                print("❌ Complete import failed - cannot proceed")
                return False
            
            print("✅ Complete import successful!")
            
            # Step 2: Verify data integrity
            print("\n" + "="*60)
            print("🔍 STEP 2: Verifying data integrity...")
            print("="*60)
            
            from app import app
            with app.app_context():
                from db import db, Team, Match, EloRating, Fixture
                
                team_count = Team.query.count()
                match_count = Match.query.count()
                elo_count = EloRating.query.count()
                fixture_count = Fixture.query.count()
                
                print(f"📊 Data Summary:")
                print(f"   Teams imported: {team_count}")
                print(f"   Matches imported: {match_count}")
                print(f"   ELO ratings calculated: {elo_count}")
                print(f"   Upcoming fixtures: {fixture_count}")
                
                # Minimum thresholds for success
                if team_count < 100:
                    print(f"❌ Insufficient teams imported: {team_count} < 100")
                    return False
                
                if match_count < 1000:
                    print(f"❌ Insufficient matches imported: {match_count} < 1000")
                    return False
                
                if elo_count == 0:
                    print("❌ No ELO ratings calculated")
                    return False
            
            print("✅ Data integrity verification passed!")
            
            # Step 3: Run consistency checks
            print("\n" + "="*60)
            print("🔧 STEP 3: Running system consistency checks...")
            print("="*60)
            
            from elo_triggers import verify_elo_consistency, cleanup_elo_issues
            
            issues = verify_elo_consistency()
            total_issues = sum(len(v) for v in issues.values())
            
            if total_issues > 0:
                print(f"⚠️  Found {total_issues} consistency issues, fixing...")
                cleanup_success = cleanup_elo_issues(issues)
                if cleanup_success:
                    print("✅ Consistency issues resolved")
                else:
                    print("⚠️  Some consistency issues remain")
            else:
                print("✅ No consistency issues found")
            
            elapsed_time = datetime.now() - start_time
            
            print("\n" + "="*60)
            print("🎉 INITIALIZATION COMPLETE!")
            print("="*60)
            print(f"✅ Total time: {elapsed_time}")
            print(f"📊 System ready with {team_count} teams and {match_count} matches")
            print(f"🏆 ELO ratings calculated for all teams")
            print("🚀 Ready to start daily operations cycle")
            
            self.initialization_complete = True
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_daily_operations_cycle(self) -> bool:
        """Start the daily operations cycle"""
        if not self.initialization_complete:
            print("⚠️  System not initialized. Run initialization first.")
            return False
        
        print("\n🔄 PHASE 2: STARTING DAILY OPERATIONS CYCLE")
        print("=" * 60)
        print("Daily operations include:")
        print("• 📅 Weekly fixture updates (get fixtures 7 days in advance)")
        print("• ⚽ Match result updates every 3 hours")
        print("• 🏆 Daily ELO maintenance and consistency checks")
        print("• 🧹 Weekly data cleanup")
        print("• 🔍 System health monitoring")
        print("• 📊 API usage: ~2,000 requests/day (well within 7,500 limit)")
        print()
        
        try:
            # Import scheduler manager
            from scheduler_manager import SoccerEloScheduler
            
            # Create and start scheduler
            self.scheduler = SoccerEloScheduler()
            self.scheduler.start()
            
            # Run initial tasks immediately
            print("🚀 Running initial daily tasks...")
            
            # Get today's fixtures immediately
            print("\n📅 Fetching today's fixtures...")
            self.scheduler.update_upcoming_fixtures()
            
            # Check for any match updates from today
            print("\n⚽ Checking for recent match updates...")
            self.scheduler.update_match_results()
            
            # Run health check
            print("\n🔍 Running initial health check...")
            self.scheduler.health_check()
            
            self.daily_cycle_running = True
            
            print("\n" + "="*60)
            print("✅ DAILY OPERATIONS CYCLE STARTED!")
            print("="*60)
            print("🔄 The system is now running continuously with:")
            print("   • Match updates every 3 hours")
            print("   • Daily fixture refresh at 6:00 AM")
            print("   • Daily ELO maintenance at 2:00 AM")
            print("   • System health checks every 6 hours")
            print()
            print("📊 To monitor status: python3 scheduler_manager.py --status")
            print("🛑 To stop: Press Ctrl+C")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start daily operations: {e}")
            return False
    
    def run_continuous_mode(self):
        """Run in continuous mode (keeps running until stopped)"""
        print("\n🔄 Running in continuous mode...")
        print("Press Ctrl+C to stop the system")
        
        try:
            while self.daily_cycle_running:
                time.sleep(60)  # Check every minute
                
                # Verify scheduler is still running
                if hasattr(self, 'scheduler') and not self.scheduler.running:
                    print("⚠️  Scheduler stopped unexpectedly, restarting...")
                    self.scheduler.start()
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested by user...")
            self.shutdown()
        except Exception as e:
            print(f"❌ Error in continuous mode: {e}")
            self.shutdown()
    
    def shutdown(self):
        """Graceful shutdown"""
        print("🛑 Shutting down Soccer ELO System...")
        
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.stop()
        
        self.daily_cycle_running = False
        print("✅ System shutdown complete")
    
    def run_full_cycle(self, skip_initialization: bool = False):
        """Run complete initialization + daily cycle"""
        print("⚽ SOCCER ELO SYSTEM - COMPLETE SETUP AND OPERATIONS")
        print("=" * 70)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Validate environment
        if not self.validate_environment():
            return False
        
        # Phase 1: Initialization (unless skipped)
        if not skip_initialization:
            if not self.run_complete_initialization():
                print("❌ Initialization failed - cannot proceed to daily operations")
                return False
        else:
            print("⏭️  Skipping initialization (--skip-init specified)")
            self.initialization_complete = True
        
        # Small pause between phases
        print("\n⏸️  Pausing 10 seconds before starting daily operations...")
        time.sleep(10)
        
        # Phase 2: Daily Operations
        if not self.start_daily_operations_cycle():
            print("❌ Failed to start daily operations")
            return False
        
        # Phase 3: Continuous Operation
        self.run_continuous_mode()
        
        return True

def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Soccer ELO System - Complete Initialization and Daily Operations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Complete setup (initialization + daily operations)
  python3 initialize_and_run.py
  
  # Skip initialization, just start daily operations
  python3 initialize_and_run.py --skip-init
  
  # Run initialization only, don't start daily cycle
  python3 initialize_and_run.py --init-only
  
  # Quick status check
  python3 initialize_and_run.py --status
        """
    )
    
    parser.add_argument('--skip-init', action='store_true',
                       help='Skip initialization, start daily operations immediately')
    parser.add_argument('--init-only', action='store_true',
                       help='Run initialization only, don\'t start daily operations')
    parser.add_argument('--status', action='store_true',
                       help='Show current system status')
    
    args = parser.parse_args()
    
    manager = SoccerEloSystemManager()
    
    try:
        if args.status:
            # Show status using scheduler manager
            from scheduler_manager import SoccerEloScheduler
            scheduler = SoccerEloScheduler()
            scheduler.status()
            return True
        
        if args.init_only:
            # Run initialization only
            if not manager.validate_environment():
                return False
            return manager.run_complete_initialization()
        
        # Run full cycle (with or without initialization)
        return manager.run_full_cycle(skip_initialization=args.skip_init)
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        manager.shutdown()
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)