#!/usr/bin/env python3
"""
Daily Upcoming Fixtures Update
Simple script that can be run via cron job to update upcoming fixtures daily
"""

import os
import sys
from datetime import datetime

def main():
    """Run daily upcoming fixtures update"""
    print(f"🕐 Daily Fixtures Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        return False
    
    try:
        # Initialize Flask app context if needed
        try:
            from app import app
            with app.app_context():
                from upcoming_fixtures import UpcomingFixturesManager
                
                manager = UpcomingFixturesManager(api_key, max_requests_per_day=7500)
                upcoming_count = manager.fetch_all_upcoming_fixtures(days_ahead=7)
                
                print(f"✅ Daily fixtures update complete!")
                print(f"📅 Fixtures updated: {upcoming_count}")
                print(f"🔢 API requests used: {manager.requests_made}")
                
                return True
                
        except ImportError:
            # Fallback without Flask context
            print("⚠️  Running without Flask context")
            from upcoming_fixtures import UpcomingFixturesManager
            
            manager = UpcomingFixturesManager(api_key, max_requests_per_day=7500)
            upcoming_count = manager.fetch_all_upcoming_fixtures(days_ahead=7)
            
            print(f"✅ Daily fixtures update complete!")
            print(f"📅 Fixtures updated: {upcoming_count}")
            print(f"🔢 API requests used: {manager.requests_made}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during daily update: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)