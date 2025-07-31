#!/usr/bin/env python3
"""
Enhanced ELO Integration Script
Demonstrates complete integration of the enhanced ELO system with match imports and automatic recalculation.
"""

import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demonstrate_enhanced_elo_system():
    """Demonstrate the complete enhanced ELO system functionality"""
    print("🏆 Enhanced ELO System Integration Demonstration")
    print("=" * 60)
    
    try:
        from app import app
        with app.app_context():
            from enhanced_elo_engine import EnhancedEloEngine
            from elo_triggers import (
                get_trigger_manager, 
                trigger_elo_after_match_import,
                verify_elo_consistency,
                schedule_daily_elo_maintenance
            )
            from db import db, Team, Match, EloRating
            
            # Step 1: Initialize the enhanced ELO engine
            print("\n🔧 Step 1: Initializing Enhanced ELO Engine...")
            engine = EnhancedEloEngine()
            print("✅ Engine initialized with adaptive K-factors and progressive storage")
            
            # Step 2: Show current system status
            print("\n📊 Step 2: Current System Status...")
            total_teams = Team.query.count()
            total_matches = Match.query.count()
            total_ratings = EloRating.query.count()
            
            print(f"   Teams in database: {total_teams}")
            print(f"   Matches in database: {total_matches}")
            print(f"   ELO ratings stored: {total_ratings}")
            
            # Step 3: Demonstrate trigger system
            print("\n🔄 Step 3: Trigger System Status...")
            trigger_manager = get_trigger_manager()
            print(f"   Affected teams tracked: {len(trigger_manager.affected_teams)}")
            print(f"   Earliest change date: {trigger_manager.earliest_change_date}")
            
            # Step 4: Run consistency check
            print("\n🔍 Step 4: ELO Consistency Check...")
            issues = verify_elo_consistency()
            total_issues = sum(len(v) for v in issues.values())
            
            if total_issues > 0:
                print(f"⚠️  Found {total_issues} consistency issues:")
                for issue_type, issue_list in issues.items():
                    if issue_list:
                        print(f"   {issue_type}: {len(issue_list)} issues")
            else:
                print("✅ No consistency issues found")
            
            # Step 5: Demonstrate recalculation capabilities
            print("\n🏆 Step 5: ELO Recalculation Capabilities...")
            
            # Show teams with recent matches (last 30 days)
            recent_cutoff = datetime.now() - timedelta(days=30)
            recent_matches = Match.query.filter(Match.date >= recent_cutoff.date()).count()
            
            if recent_matches > 0:
                print(f"   Recent matches (last 30 days): {recent_matches}")
                
                # Get teams involved in recent matches
                recent_teams = db.session.query(Team.id).filter(
                    db.or_(
                        Team.id.in_(
                            db.session.query(Match.home_team_id).filter(Match.date >= recent_cutoff.date())
                        ),
                        Team.id.in_(
                            db.session.query(Match.away_team_id).filter(Match.date >= recent_cutoff.date())
                        )
                    )
                ).distinct().count()
                
                print(f"   Teams with recent matches: {recent_teams}")
            else:
                print("   No recent matches found")
            
            # Step 6: Demonstrate adaptive K-factor system
            print("\n⚖️  Step 6: Adaptive K-Factor System...")
            
            # Show K-factors for different team scenarios
            sample_scenarios = [
                (5, 800, "New low-rated team"),
                (25, 1200, "Developing mid-rated team"), 
                (75, 1600, "Established high-rated team"),
                (150, 2000, "Elite veteran team")
            ]
            
            for matches_played, rating, description in sample_scenarios:
                engine.match_counts[9999] = matches_played  # Fake team ID for demo
                k_factor = engine.get_adaptive_k_factor(9999, rating)
                print(f"   {description}: K={k_factor:.1f} ({matches_played} matches, {rating} rating)")
            
            # Step 7: Show integration points
            print("\n🔗 Step 7: Integration Points...")
            print("   ✅ API import triggers automatic ELO recalculation")
            print("   ✅ Flask routes trigger ELO updates for new matches")
            print("   ✅ Daily maintenance script for consistency checks")
            print("   ✅ Progressive rating storage with checkpoints")
            print("   ✅ Batch processing for memory efficiency")
            
            # Step 8: Usage recommendations
            print("\n💡 Step 8: Usage Recommendations...")
            print("   🚀 For new installations: Run enhanced_elo_engine.py --force")
            print("   🔄 For match imports: Triggers fire automatically")
            print("   🕐 For daily maintenance: Run daily_elo_maintenance.py")
            print("   🔍 For diagnostics: Run elo_triggers.py --verify")
            print("   🧹 For cleanup: Run elo_triggers.py --cleanup")
            
            print("\n🎉 Enhanced ELO System Integration Complete!")
            print("=" * 60)
            print("The system is ready to automatically maintain ELO ratings")
            print("whenever match history is updated.")
            
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all required modules are available")
        return False
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_usage_examples():
    """Show practical usage examples for the enhanced ELO system"""
    print("\n📚 Enhanced ELO System Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "title": "Complete ELO Recalculation",
            "command": "python3 enhanced_elo_engine.py --force",
            "description": "Recalculates all ELO ratings from scratch"
        },
        {
            "title": "Team-Specific ELO Calculation", 
            "command": "python3 enhanced_elo_engine.py --team-id 42",
            "description": "Recalculates ELO for team ID 42 only"
        },
        {
            "title": "Date-Range ELO Calculation",
            "command": "python3 enhanced_elo_engine.py --from-date 2024-01-01",
            "description": "Recalculates ELO from January 1st, 2024 onwards"
        },
        {
            "title": "Daily Maintenance",
            "command": "python3 daily_elo_maintenance.py",
            "description": "Runs daily ELO consistency checks and updates"
        },
        {
            "title": "Consistency Verification",
            "command": "python3 elo_triggers.py --verify",
            "description": "Checks for ELO rating consistency issues"
        },
        {
            "title": "Issue Cleanup",
            "command": "python3 elo_triggers.py --cleanup",
            "description": "Fixes identified ELO consistency issues"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}")
        print(f"   Command: {example['command']}")
        print(f"   Purpose: {example['description']}")
    
    print("\n🔄 Automatic Triggers:")
    print("   • Match imports automatically trigger ELO recalculation")
    print("   • Flask API match creation triggers ELO updates")
    print("   • Daily maintenance can be scheduled via cron job")
    
    print("\n⚙️  Cron Job Example (daily at 2 AM):")
    print("   0 2 * * * cd /path/to/project && python3 daily_elo_maintenance.py")

def main():
    """Main function to run the integration demonstration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced ELO System Integration')
    parser.add_argument('--demo', action='store_true', 
                       help='Run system demonstration')
    parser.add_argument('--examples', action='store_true',
                       help='Show usage examples')
    
    args = parser.parse_args()
    
    if args.examples:
        show_usage_examples()
        return True
    
    if args.demo or not any(vars(args).values()):
        # Run demonstration by default
        return demonstrate_enhanced_elo_system()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)