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
        from api_import import APIFootballImporter
        from top_250_teams import get_team_mapper
        from migrate_db import migrate_database
        
        with app.app_context():
            # Step 1: Ensure database is migrated
            print("\n📊 Step 1: Database migration...")
            migrate_database()
            print("✅ Database migration complete")
            
            # Step 2: Initialize importer
            print("\n🔧 Step 2: Initializing API importer...")
            importer = APIFootballImporter(
                api_key=api_key,
                current_season=datetime.now().year,
                request_delay=0.6,  # Conservative delay
                max_requests_per_day=9000  # Conservative limit
            )
            print("✅ API importer initialized")
            
            # Step 3: Map teams to API IDs
            print("\n🗺️  Step 3: Mapping 250 teams to API IDs...")
            importer.map_top_250_teams()
            
            # Check mapping progress
            team_mapper = get_team_mapper()
            progress = team_mapper.get_mapping_progress()
            print(f"📊 Mapping progress: {progress['mapped']}/{progress['total']} teams ({progress['progress_percent']}%)")
            
            if progress['mapped'] < 150:  # Need at least 150 teams mapped
                print(f"❌ Only {progress['mapped']} teams mapped. Need at least 150 to proceed.")
                return False
            
            print("✅ Team mapping complete")
            
            # Step 4: Import historical data
            print(f"\n📚 Step 4: Importing historical data for {progress['mapped']} teams...")
            importer.import_top_250_teams_historical_enhanced(start_year=2000)
            print("✅ Historical data import complete")
            
            # Step 5: Calculate ELO ratings
            print("\n🏆 Step 5: Calculating ELO ratings...")
            # Import the ELO calculation logic directly
            from db import db, EloRating, Match
            from elo_utils import get_match_result, update_elo
            
            # Clear existing ELO ratings
            EloRating.query.delete()
            db.session.commit()
            print("✅ Cleared existing ELO ratings")
            
            # Get all matches ordered by date
            matches = Match.query.order_by(Match.date.asc()).all()
            print(f"📊 Found {len(matches)} matches to process")
            
            if matches:
                # Track ELO ratings for each team
                team_elos = {}
                ratings_to_add = []
                
                processed = 0
                for match in matches:
                    try:
                        # Get current ELO for both teams (default to 1000)
                        home_elo = team_elos.get(match.home_team_id, 1000)
                        away_elo = team_elos.get(match.away_team_id, 1000)
                        
                        # Calculate match result
                        home_score, away_score = get_match_result(match.home_score, match.away_score)
                        
                        # Calculate new ELO ratings
                        new_home_elo = update_elo(home_elo, away_elo, home_score)
                        new_away_elo = update_elo(away_elo, home_elo, away_score)
                        
                        # Update tracking
                        team_elos[match.home_team_id] = new_home_elo
                        team_elos[match.away_team_id] = new_away_elo
                        
                        # Add to batch
                        ratings_to_add.append(EloRating(
                            team_id=match.home_team_id, 
                            date=match.date, 
                            rating=new_home_elo
                        ))
                        ratings_to_add.append(EloRating(
                            team_id=match.away_team_id, 
                            date=match.date, 
                            rating=new_away_elo
                        ))
                        
                        processed += 1
                        
                        # Batch commit every 100 matches
                        if processed % 100 == 0:
                            db.session.add_all(ratings_to_add)
                            db.session.commit()
                            ratings_to_add = []
                            print(f"📈 Processed {processed}/{len(matches)} matches")
                            
                    except Exception as e:
                        print(f"❌ Error processing match {match.id}: {e}")
                        continue
                
                # Final commit
                if ratings_to_add:
                    db.session.add_all(ratings_to_add)
                    db.session.commit()
                
                print(f"✅ ELO calculation complete: {processed} matches processed")
            else:
                print("⚠️  No matches found for ELO calculation")
            
            print("\n🎉 Complete import process finished!")
            print("="*60)
            print(f"📊 Final stats:")
            print(f"   🗺️  Teams mapped: {progress['mapped']}/{progress['total']}")
            print(f"   📅 Historical data: Imported from 2000")
            print(f"   🏆 ELO ratings: Calculated")
            print(f"   📍 League assignments: Current leagues detected")
            
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