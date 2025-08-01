#!/usr/bin/env python3
"""
Background Worker for Render
Specifically designed for Render's background worker service
Runs complete system setup and daily operations without interactive input
"""

import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Background worker main function - no interactive input required"""
    print("🚀 SOCCER ELO BACKGROUND WORKER")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🤖 Running in background worker mode")
    print()
    
    # Check API key
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found!")
        print("💡 Make sure to set your API key in Render environment variables")
        return False
    
    print("✅ API key configured")
    print(f"🔑 Key: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Check database
    try:
        from app import app
        with app.app_context():
            from db import db, Team, Match
            
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            team_count = Team.query.count()
            match_count = Match.query.count()
            
            print("✅ Database connection successful")
            print(f"📊 Current data: {team_count} teams, {match_count} matches")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    print()
    print("🎯 BACKGROUND WORKER OPERATIONS:")
    print("   1️⃣  Complete system initialization (if needed)")
    print("   2️⃣  Import teams and match history")
    print("   3️⃣  Calculate ELO ratings")
    print("   4️⃣  Start continuous daily operations")
    print("   5️⃣  Match updates every 3 hours")
    print("   6️⃣  Daily fixture and ELO maintenance")
    print()
    
    try:
        # Determine if we need initialization
        needs_initialization = team_count < 100 or match_count < 1000
        
        if needs_initialization:
            print("🔄 PHASE 1: SYSTEM INITIALIZATION REQUIRED")
            print("=" * 50)
            print(f"📊 Current state: {team_count} teams, {match_count} matches")
            print("🚀 Starting complete system initialization...")
            
            # Run complete initialization
            from initialize_and_run import SoccerEloSystemManager
            
            manager = SoccerEloSystemManager()
            success = manager.run_complete_initialization()
            
            if not success:
                print("❌ System initialization failed")
                return False
            
            print("✅ System initialization complete!")
            
            # Small pause before daily operations
            time.sleep(10)
        else:
            print("✅ SYSTEM ALREADY INITIALIZED")
            print("=" * 50)
            print(f"📊 Found sufficient data: {team_count} teams, {match_count} matches")
            print("⏭️  Skipping initialization, proceeding to daily operations...")
        
        print("\n🔄 PHASE 2: STARTING DAILY OPERATIONS")
        print("=" * 50)
        
        # Start daily operations cycle
        from scheduler_manager import SoccerEloScheduler
        
        scheduler = SoccerEloScheduler()
        scheduler.start()
        
        # Run initial tasks
        print("🚀 Running initial daily tasks...")
        
        # Update upcoming fixtures
        print("\n📅 Fetching upcoming fixtures...")
        scheduler.update_upcoming_fixtures()
        
        # Check for match updates
        print("\n⚽ Checking for recent match updates...")
        scheduler.update_match_results()
        
        # Run health check
        print("\n🔍 Running system health check...")
        scheduler.health_check()
        
        print("\n" + "="*50)
        print("✅ BACKGROUND WORKER FULLY OPERATIONAL!")
        print("="*50)
        print("🔄 Now running continuous operations:")
        print("   • Match updates every 3 hours")
        print("   • Daily fixture refresh at 6:00 AM")
        print("   • Daily ELO maintenance at 2:00 AM")
        print("   • System health checks every 6 hours")
        print()
        print("🎯 Worker will run indefinitely until stopped")
        print("📊 Check logs for ongoing operation status")
        
        # Run continuously
        print("\n🔄 Entering continuous operation mode...")
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                # Verify scheduler is still running
                if not scheduler.running:
                    print("⚠️  Scheduler stopped unexpectedly, restarting...")
                    scheduler.start()
                
                # Log status periodically (every hour)
                current_time = datetime.now()
                if current_time.minute == 0:  # Top of the hour
                    print(f"💓 Heartbeat - {current_time.strftime('%Y-%m-%d %H:%M:%S')} - System running normally")
                    
            except Exception as e:
                print(f"❌ Error in continuous operation: {e}")
                print("🔄 Attempting to continue...")
                time.sleep(60)  # Wait a minute before retrying
                
    except KeyboardInterrupt:
        print("\n🛑 Background worker shutdown requested")
        return True
    except Exception as e:
        print(f"❌ Background worker error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)