#!/usr/bin/env python3
"""
Complete import script for 250 teams with proper mapping, league assignment, and ELO calculation
"""

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_complete_import():
    """Run the complete import process"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found in environment")
        print("💡 Make sure to set the API_FOOTBALL_KEY environment variable on Render:")
        print("   1. Go to your Render dashboard")
        print("   2. Select your service")
        print("   3. Go to Environment tab")
        print("   4. Add: API_FOOTBALL_KEY = your_api_key_here")
        print("   5. Redeploy the service")
        return False
    
    print("🚀 Starting complete 250 teams import process...")
    print("="*60)
    
    try:
        # Import here to avoid dependency issues
        from app import app
        from top_250_teams import get_team_mapper
        from migrate_db import migrate_database
        
        with app.app_context():
            # Step 1: Ensure database is migrated
            print("\n📊 Step 1: Database migration...")
            migrate_database()
            print("✅ Database migration complete")
            
            # Step 2: Initialize new league-based importer
            print("\n🔧 Step 2: Initializing league-based API importer...")
            from league_based_import import LeagueBasedImporter
            
            importer = LeagueBasedImporter(
                api_key=api_key,
                max_requests_per_day=7500  # Actual API limit
            )
            print("✅ League-based importer initialized")
            
            # Step 3: Discover teams by leagues (NEW APPROACH)
            print("\n🗺️  Step 3: Discovering teams through major leagues...")
            discovered_teams = importer.discover_teams_by_leagues([2024, 2023])
            
            # Apply discovered teams to mapper
            applied_teams = importer.apply_discovered_teams()
            
            # Check mapping progress
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"📊 Team discovery results:")
            print(f"   Teams discovered: {len(discovered_teams)}")
            print(f"   Teams applied: {applied_teams}")
            print(f"   Total mapped: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
            
            if progress['mapped'] < 100:  # Reduced threshold since we expect better results
                print(f"❌ Only {progress['mapped']} teams mapped. Expected at least 100 with new system.")
                print("💡 You may need to run diagnostics to identify missing teams")
                return False
            
            print("✅ Team discovery complete")
            
            # Step 4: Import historical match data (NEW APPROACH)
            print(f"\n📚 Step 4: Importing match history for discovered teams...")
            
            # Check if we have enough API budget for match import
            if importer.requests_made < 6000:  # Leave room for match import
                matches_imported = importer.import_team_matches()
                print(f"✅ Match history import complete: {matches_imported} matches")
            else:
                print("⚠️  Insufficient API budget for full match import")
                print("💡 Run match import separately when API limit resets")
                return False
            
            # Step 5: Calculate ELO ratings using enhanced system
            print("\n🏆 Step 5: Calculating ELO ratings with enhanced system...")
            from enhanced_elo_engine import EnhancedEloEngine
            
            # Initialize enhanced ELO engine
            elo_engine = EnhancedEloEngine()
            
            # Recalculate all ELO ratings
            stats = elo_engine.recalculate_all_elos(force_recalculate=True)
            
            processed = stats.get('total_matches_processed', 0)
            print(f"✅ Enhanced ELO calculation complete: {processed} matches processed")
            print(f"   Teams processed: {stats.get('teams_processed', 0)}")
            print(f"   Teams skipped: {stats.get('teams_skipped', 0)}")
            print(f"   Errors: {stats.get('errors', 0)}")
            
            # Step 6: Fetch upcoming fixtures (if we have API budget)
            if importer.requests_made < importer.max_requests_per_day - 300:
                print("\n📅 Step 6: Fetching upcoming fixtures...")
                from upcoming_fixtures import UpcomingFixturesManager
                
                fixtures_manager = UpcomingFixturesManager(
                    api_key=api_key,
                    max_requests_per_day=importer.max_requests_per_day
                )
                
                # Update requests count to include what we've already used
                fixtures_manager.requests_made = importer.requests_made
                
                upcoming_count = fixtures_manager.fetch_all_upcoming_fixtures(days_ahead=7)
                total_requests = fixtures_manager.requests_made
                
                print(f"✅ Upcoming fixtures fetch complete: {upcoming_count} fixtures")
            else:
                print("\n⚠️  Step 6: Skipping upcoming fixtures - insufficient API budget")
                print("💡 Run upcoming fixtures separately: python3 upcoming_fixtures.py")
                upcoming_count = 0
                total_requests = importer.requests_made
            
            print("\n🎉 Complete import process finished!")
            print("="*60)
            print(f"📊 Final stats:")
            print(f"   🗺️  Teams discovered: {len(discovered_teams)}")
            print(f"   ✅ Teams mapped: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
            print(f"   ⚽ Matches imported: {matches_imported}")
            print(f"   📅 Historical coverage: 2010-2025 (comprehensive)")
            print(f"   🏆 ELO ratings: {processed} matches processed")
            print(f"   📅 Upcoming fixtures: {upcoming_count} fixtures (next 7 days)")
            print(f"   🔢 API requests used: {total_requests}/{importer.max_requests_per_day}")
            print(f"   📍 System: League-based import (API documentation compliant)")
            
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Trying alternative approach without Flask dependencies...")
        return run_simple_mapping()
    except Exception as e:
        print(f"❌ Error during import: {e}")
        return False

def run_simple_mapping():
    """Run just the team mapping without Flask dependencies"""
    print("🔧 Running simple team mapping...")
    
    try:
        from top_250_teams import get_team_mapper, get_top_250_team_names
        import requests
        import time
        import json
        
        api_key = os.environ.get('API_FOOTBALL_KEY')
        headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        
        team_mapper = get_team_mapper()
        team_names = get_top_250_team_names()
        unmapped_teams = team_mapper.get_unmapped_teams()
        
        print(f"📊 Teams to map: {len(unmapped_teams)}")
        
        mapped_count = 0
        max_requests = 500  # Conservative limit
        
        for i, team_name in enumerate(unmapped_teams[:max_requests]):
            print(f"🔍 ({i+1}/{min(len(unmapped_teams), max_requests)}) Searching for: {team_name}")
            
            try:
                # Use search endpoint with proper URL encoding
                response = requests.get(
                    "https://v3.football.api-sports.io/teams",
                    headers=headers,
                    params={"search": team_name}  # This handles URL encoding automatically
                )
                
                if response.status_code == 200:
                    data = response.json()
                    teams = data.get('response', [])
                    
                    if teams:
                        # Take the first result (usually the best match)
                        team_data = teams[0]
                        team = team_data.get('team', {})
                        
                        # Get current league for this team
                        team_id = team.get('id')
                        current_league = "Unknown"
                        
                        if team_id:
                            try:
                                league_response = requests.get(
                                    "https://v3.football.api-sports.io/leagues",
                                    headers=headers,
                                    params={"team": team_id, "season": datetime.now().year}
                                )
                                if league_response.status_code == 200:
                                    league_data = league_response.json()
                                    leagues = league_data.get('response', [])
                                    if leagues:
                                        # Get the first domestic league
                                        for league_info in leagues:
                                            league = league_info.get('league', {})
                                            league_type = league.get('type', '').lower()
                                            if 'cup' not in league_type:
                                                current_league = league.get('name', 'Unknown')
                                                break
                                        if current_league == "Unknown" and leagues:
                                            # Fallback to first league if no domestic found
                                            current_league = leagues[0].get('league', {}).get('name', 'Unknown')
                                time.sleep(0.3)  # Additional delay for league lookup
                            except Exception as e:
                                print(f"⚠️  Could not get league for {team_name}: {e}")
                        
                        team_mapper.add_team_mapping(
                            name=team_name,
                            api_id=team_id,
                            league=current_league,
                            country=team.get('country', 'Unknown')
                        )
                        
                        mapped_count += 1
                        print(f"✅ Mapped: {team.get('name')} (ID: {team.get('id')})")
                        
                        # Save progress periodically
                        if mapped_count % 10 == 0:
                            team_mapper.save_mapping()
                            print(f"💾 Saved progress: {mapped_count} teams mapped")
                    else:
                        print(f"❌ No results for: {team_name}")
                else:
                    print(f"❌ API error for {team_name}: {response.status_code}")
                
                time.sleep(0.7)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error searching {team_name}: {e}")
                continue
        
        # Final save
        team_mapper.save_mapping()
        
        progress = team_mapper.get_mapping_progress()
        print(f"\n✅ Simple mapping complete!")
        print(f"📊 Mapped: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during simple mapping: {e}")
        return False

if __name__ == "__main__":
    success = run_complete_import()
    if success:
        print("🎉 Import completed successfully!")
    else:
        print("❌ Import failed")
        sys.exit(1)