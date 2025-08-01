#!/usr/bin/env python3
"""
System Status - Check Soccer ELO System Status
Shows comprehensive status of all system components
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_environment():
    """Check environment configuration"""
    print("🔧 ENVIRONMENT CONFIGURATION")
    print("-" * 40)
    
    required_vars = {
        "API_FOOTBALL_KEY": "API Football API key",
        "DATABASE_URL": "Database connection string"
    }
    
    all_good = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            if var == "API_FOOTBALL_KEY":
                masked = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing ({description})")
            all_good = False
    
    return all_good

def check_database_status():
    """Check database connection and data status"""
    print("\n💾 DATABASE STATUS")
    print("-" * 40)
    
    try:
        from app import app
        with app.app_context():
            from db import db, Team, Match, EloRating, Fixture
            
            # Test connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("✅ Database connection: OK")
            
            # Count records
            team_count = Team.query.count()
            match_count = Match.query.count()
            elo_count = EloRating.query.count()
            fixture_count = Fixture.query.count()
            
            print(f"📊 Data Summary:")
            print(f"   Teams: {team_count:,}")
            print(f"   Matches: {match_count:,}")
            print(f"   ELO Ratings: {elo_count:,}")
            print(f"   Upcoming Fixtures: {fixture_count:,}")
            
            # Check data quality
            teams_with_api_ids = Team.query.filter(Team.api_football_id.isnot(None)).count()
            api_mapping_percent = (teams_with_api_ids / team_count * 100) if team_count > 0 else 0
            
            print(f"🔗 API Integration:")
            print(f"   Teams with API IDs: {teams_with_api_ids:,} ({api_mapping_percent:.1f}%)")
            
            # Recent activity
            recent_cutoff = datetime.now() - timedelta(days=7)
            recent_matches = Match.query.filter(Match.date >= recent_cutoff.date()).count()
            recent_fixtures = Fixture.query.filter(Fixture.date >= recent_cutoff).count()
            
            print(f"📅 Recent Activity (last 7 days):")
            print(f"   New matches: {recent_matches:,}")
            print(f"   Upcoming fixtures: {recent_fixtures:,}")
            
            # System health indicators
            print(f"🏥 Health Indicators:")
            if team_count >= 100:
                print("   ✅ Sufficient teams imported")
            else:
                print(f"   ⚠️  Low team count: {team_count} (expected: 100+)")
            
            if match_count >= 1000:
                print("   ✅ Sufficient match history")
            else:
                print(f"   ⚠️  Low match count: {match_count} (expected: 1000+)")
            
            if elo_count > 0:
                print("   ✅ ELO ratings calculated")
            else:
                print("   ❌ No ELO ratings found")
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def check_scheduler_status():
    """Check scheduler and daily operations status"""
    print("\n⏰ SCHEDULER STATUS")
    print("-" * 40)
    
    try:
        from scheduler_manager import SoccerEloScheduler
        
        # Try to get scheduler status
        scheduler = SoccerEloScheduler()
        scheduler.status()
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduler status error: {e}")
        print("💡 Scheduler may not be running")
        return False

def check_api_usage():
    """Check API usage and limits"""
    print("\n📡 API USAGE")
    print("-" * 40)
    
    # Check for request log files
    today = datetime.now()
    log_file = f"api_requests_{today.strftime('%Y%m%d')}.log"
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                request_count = len(lines)
            
            print(f"📊 Today's API usage: {request_count:,} requests")
            print(f"📈 Daily limit: 7,500 requests")
            print(f"💹 Remaining: {7500 - request_count:,} requests ({((7500 - request_count) / 7500 * 100):.1f}%)")
            
            if request_count > 6000:
                print("⚠️  High API usage - approaching daily limit")
            elif request_count > 7500:
                print("❌ Daily API limit exceeded!")
            else:
                print("✅ API usage within normal limits")
                
        except Exception as e:
            print(f"⚠️  Could not read API log: {e}")
    else:
        print("📊 No API usage data for today")
        print("💡 Log file will be created when API requests are made")

def check_system_files():
    """Check if all required system files exist"""
    print("\n📁 SYSTEM FILES")
    print("-" * 40)
    
    required_files = [
        ("run_complete_import.py", "Complete import script"),
        ("enhanced_elo_engine.py", "Enhanced ELO calculation engine"),
        ("match_results_updater.py", "3-hour match updates"),
        ("scheduler_manager.py", "Daily operations scheduler"),
        ("daily_elo_maintenance.py", "Daily ELO maintenance"),
        ("upcoming_fixtures.py", "Fixture management"),
        ("league_based_import.py", "League-based team import"),
        ("elo_triggers.py", "ELO recalculation triggers")
    ]
    
    all_files_exist = True
    for filename, description in required_files:
        if os.path.exists(filename):
            print(f"✅ {filename}")
        else:
            print(f"❌ {filename} - {description}")
            all_files_exist = False
    
    return all_files_exist

def show_quick_commands():
    """Show useful commands for system management"""
    print("\n🔧 QUICK COMMANDS")
    print("-" * 40)
    
    commands = [
        ("Start complete system", "python3 start_system.py"),
        ("Start just daily operations", "python3 initialize_and_run.py --skip-init"),
        ("Run initialization only", "python3 initialize_and_run.py --init-only"),
        ("Update matches now", "python3 match_results_updater.py"),
        ("Update fixtures now", "python3 daily_fixtures_update.py"),
        ("Run ELO maintenance", "python3 daily_elo_maintenance.py"),
        ("Check scheduler status", "python3 scheduler_manager.py --status"),
        ("Run specific task", "python3 scheduler_manager.py --run-task <task_name>")
    ]
    
    for description, command in commands:
        print(f"📋 {description}:")
        print(f"   {command}")
        print()

def main():
    """Main status check function"""
    print("⚽ SOCCER ELO SYSTEM STATUS")
    print("=" * 50)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all status checks
    env_ok = check_environment()
    db_ok = check_database_status()
    scheduler_ok = check_scheduler_status()
    check_api_usage()
    files_ok = check_system_files()
    
    # Overall system health
    print("\n🏥 OVERALL SYSTEM HEALTH")
    print("=" * 50)
    
    health_checks = [
        ("Environment", env_ok),
        ("Database", db_ok),
        ("Scheduler", scheduler_ok),
        ("System Files", files_ok)
    ]
    
    healthy_components = sum(1 for _, status in health_checks if status)
    total_components = len(health_checks)
    
    for component, status in health_checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {component}")
    
    health_percentage = (healthy_components / total_components) * 100
    
    print(f"\n📊 System Health: {healthy_components}/{total_components} components OK ({health_percentage:.0f}%)")
    
    if health_percentage == 100:
        print("🎉 System is fully operational!")
    elif health_percentage >= 75:
        print("⚠️  System is mostly operational with minor issues")
    else:
        print("❌ System has significant issues that need attention")
    
    show_quick_commands()
    
    return health_percentage >= 75

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)