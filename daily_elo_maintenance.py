#!/usr/bin/env python3
"""
Daily ELO Maintenance Script
Run this script daily to maintain ELO rating consistency and recalculate ratings for any teams with recent match updates.
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run daily ELO maintenance tasks"""
    print(f"🔧 Daily ELO Maintenance - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Initialize Flask app context
        from app import app
        with app.app_context():
            from elo_triggers import schedule_daily_elo_maintenance, verify_elo_consistency, cleanup_elo_issues
            
            print("🔍 Step 1: Verifying ELO consistency...")
            issues = verify_elo_consistency()
            
            # Fix any issues found
            if any(len(v) > 0 for v in issues.values()):
                print("🧹 Step 2: Cleaning up ELO issues...")
                cleanup_success = cleanup_elo_issues(issues)
                if not cleanup_success:
                    print("❌ ELO cleanup failed")
                    return False
            else:
                print("✅ Step 2: No ELO issues found")
            
            print("🔄 Step 3: Running daily ELO maintenance...")
            maintenance_success = schedule_daily_elo_maintenance()
            
            if maintenance_success:
                print("✅ Daily ELO maintenance completed successfully!")
                return True
            else:
                print("❌ Daily ELO maintenance failed")
                return False
                
    except Exception as e:
        print(f"❌ Error during daily maintenance: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)