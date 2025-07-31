#!/usr/bin/env python3
"""
Standalone Team Discovery Script
Uses the new league-based approach to discover teams only (no match import)
"""

import os
import sys
from league_based_import import LeagueBasedImporter

def main():
    """Discover teams using league-based approach"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        print("Set it with: export API_FOOTBALL_KEY=your_key_here")
        return False
    
    print("🔍 Team Discovery using League-Based Import")
    print("=" * 60)
    print("This script discovers teams from major leagues without importing match history")
    print("Useful for testing the new approach and seeing coverage results")
    print("=" * 60)
    
    try:
        # Initialize importer
        importer = LeagueBasedImporter(api_key, max_requests_per_day=7500)
        
        # Discover teams from current and previous season
        print("🚀 Starting team discovery...")
        discovered_teams = importer.discover_teams_by_leagues([2024, 2023])
        
        # Save results for analysis
        importer.save_discovery_results("team_discovery_results.json")
        
        # Apply to team mapper
        applied_teams = importer.apply_discovered_teams()
        
        # Show detailed results
        print("\n" + "=" * 60)
        print("📊 DISCOVERY RESULTS")
        print("=" * 60)
        
        from top_250_teams import get_team_mapper
        team_mapper = get_team_mapper()
        progress = team_mapper.get_mapping_progress()
        
        print(f"🎯 Teams in TOP_250_TEAMS: {len(importer.discovered_teams)}")
        print(f"✅ Teams discovered: {len(discovered_teams)}")
        print(f"💾 Teams applied to mapper: {applied_teams}")
        print(f"📈 Success rate: {len(discovered_teams)/250*100:.1f}%")
        print(f"🔢 API requests used: {importer.requests_made}/7500")
        print(f"📊 Final mapping: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
        
        # Show some examples of discovered teams
        print(f"\n🔍 Sample discovered teams:")
        for i, (team_name, info) in enumerate(list(discovered_teams.items())[:10]):
            print(f"   {i+1}. {team_name} → {info['api_name']} (ID: {info['api_id']}, {info['league']})")
        
        if len(discovered_teams) > 10:
            print(f"   ... and {len(discovered_teams) - 10} more teams")
        
        # Identify missing teams
        from top_250_teams import TOP_250_TEAMS
        missing_teams = [team for team in TOP_250_TEAMS if team not in discovered_teams]
        
        if missing_teams:
            print(f"\n⚠️  Teams not found ({len(missing_teams)}):")
            for i, team in enumerate(missing_teams[:15]):
                print(f"   {i+1}. {team}")
            if len(missing_teams) > 15:
                print(f"   ... and {len(missing_teams) - 15} more")
            
            print(f"\n💡 These teams might need:")
            print(f"   • Manual mappings in manual_team_mappings.json")
            print(f"   • Additional leagues in MAJOR_LEAGUES")
            print(f"   • Different team name variations")
        
        print(f"\n📁 Results saved to: team_discovery_results.json")
        
        if len(discovered_teams) >= 200:
            print(f"\n🎉 Excellent results! Ready for match import.")
            print(f"   Run: python3 run_complete_import.py")
        elif len(discovered_teams) >= 150:
            print(f"\n✅ Good results! You can proceed with import.")
            print(f"   Consider adding manual mappings for missing teams")
        else:
            print(f"\n⚠️  Results below expectations.")
            print(f"   Review missing teams and add manual mappings")
            print(f"   Or run comprehensive diagnostics")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Discovery interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)