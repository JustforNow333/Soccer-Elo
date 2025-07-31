#!/usr/bin/env python3
"""
Match Results Updater
Updates match results every 3 hours by fetching completed fixtures from API Football
"""

import os
import sys
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db, Team, Match, Fixture
from elo_triggers import trigger_elo_after_match_update, get_trigger_manager

class MatchResultsUpdater:
    """Updates match results from API Football every 3 hours"""
    
    def __init__(self, api_key: str, max_requests_per_update: int = 200):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.base_url = "https://v3.football.api-sports.io"
        self.max_requests_per_update = max_requests_per_update
        self.requests_made = 0
        self.updated_matches: List[Match] = []
        
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting"""
        if self.requests_made >= self.max_requests_per_update:
            print(f"⚠️  Request limit reached ({self.requests_made}/{self.max_requests_per_update})")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            self.requests_made += 1
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"⏰ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)
                
            response.raise_for_status()
            data = response.json()
            
            if data.get('errors'):
                print(f"❌ API Error: {data['errors']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
        finally:
            time.sleep(1.0)  # Rate limiting
    
    def get_recent_fixtures_results(self, days_back: int = 3) -> List[Dict]:
        """Get completed fixtures from the last few days"""
        fixtures = []
        
        # Get fixtures from the last few days
        for days_ago in range(days_back):
            date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            params = {
                "date": date,
                "status": "FT"  # Full Time only
            }
            
            print(f"🔍 Fetching completed fixtures for {date}...")
            data = self._make_request("fixtures", params)
            
            if data and data.get("response"):
                day_fixtures = data["response"]
                fixtures.extend(day_fixtures)
                print(f"   Found {len(day_fixtures)} completed fixtures")
            
            if self.requests_made >= self.max_requests_per_update:
                break
        
        return fixtures
    
    def update_fixture_to_match(self, fixture_data: Dict) -> Optional[Match]:
        """Convert a completed fixture to a match with results"""
        try:
            fixture_info = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            
            api_fixture_id = fixture_info.get("id")
            fixture_date_str = fixture_info.get("date")
            status = fixture_info.get("status", {}).get("short", "")
            
            if not api_fixture_id or status != "FT":
                return None
            
            # Parse date
            fixture_date = datetime.fromisoformat(fixture_date_str.replace('Z', '+00:00'))
            
            # Get team data
            home_team_data = teams.get("home", {})
            away_team_data = teams.get("away", {})
            
            home_team_api_id = home_team_data.get("id")
            away_team_api_id = away_team_data.get("id")
            
            # Get scores
            home_score = goals.get("home")
            away_score = goals.get("away")
            
            if home_score is None or away_score is None:
                print(f"⚠️  Missing scores for fixture {api_fixture_id}")
                return None
            
            # Find teams in our database
            home_team = Team.query.filter_by(api_football_id=home_team_api_id).first()
            away_team = Team.query.filter_by(api_football_id=away_team_api_id).first()
            
            if not home_team or not away_team:
                print(f"⚠️  Teams not found in database for fixture {api_fixture_id}")
                return None
            
            # Check if match already exists
            existing_match = Match.query.filter_by(
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                date=fixture_date.date()
            ).first()
            
            if existing_match:
                # Update existing match if scores changed
                if (existing_match.home_score != home_score or 
                    existing_match.away_score != away_score):
                    
                    print(f"🔄 Updating match: {home_team.name} vs {away_team.name}")
                    print(f"   Old score: {existing_match.home_score}-{existing_match.away_score}")
                    print(f"   New score: {home_score}-{away_score}")
                    
                    existing_match.home_score = home_score
                    existing_match.away_score = away_score
                    
                    return existing_match
                else:
                    # No update needed
                    return None
            else:
                # Create new match
                new_match = Match(
                    date=fixture_date.date(),
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_score=home_score,
                    away_score=away_score
                )
                
                db.session.add(new_match)
                print(f"✅ Created match: {home_team.name} {home_score}-{away_score} {away_team.name}")
                
                return new_match
            
        except Exception as e:
            print(f"❌ Error processing fixture {fixture_data.get('fixture', {}).get('id', 'unknown')}: {e}")
            return None
    
    def update_matches_from_fixtures(self) -> int:
        """Update matches from recent completed fixtures"""
        print("🔄 Starting match results update...")
        print(f"📊 Budget: {self.max_requests_per_update} API requests")
        
        # Get recent completed fixtures
        fixtures = self.get_recent_fixtures_results(days_back=3)
        
        if not fixtures:
            print("❌ No fixtures found to process")
            return 0
        
        print(f"📊 Processing {len(fixtures)} completed fixtures...")
        
        updated_count = 0
        created_count = 0
        
        for fixture_data in fixtures:
            match = self.update_fixture_to_match(fixture_data)
            
            if match:
                if match.id:  # Existing match (updated)
                    updated_count += 1
                else:  # New match (created)
                    created_count += 1
                
                self.updated_matches.append(match)
                
                # Commit every 20 matches
                if (updated_count + created_count) % 20 == 0:
                    try:
                        db.session.commit()
                        print(f"💾 Committed batch ({updated_count + created_count} matches processed)")
                    except Exception as e:
                        print(f"❌ Commit error: {e}")
                        db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            print(f"💾 Final commit completed")
        except Exception as e:
            print(f"❌ Final commit error: {e}")
            db.session.rollback()
            return 0
        
        # Trigger ELO recalculation for updated matches
        if self.updated_matches:
            print(f"🏆 Triggering ELO recalculation for {len(self.updated_matches)} matches...")
            try:
                # Get unique team IDs from updated matches
                affected_teams = set()
                for match in self.updated_matches:
                    affected_teams.add(match.home_team_id)
                    affected_teams.add(match.away_team_id)
                
                # Get trigger manager and register changes
                trigger_manager = get_trigger_manager()
                trigger_manager.register_matches_batch(self.updated_matches, "results_update")
                trigger_manager.execute_recalculation()
                
            except Exception as e:
                print(f"⚠️  ELO recalculation failed: {e}")
        
        total_processed = updated_count + created_count
        
        print(f"\n✅ Match results update complete!")
        print(f"📊 Statistics:")
        print(f"   Fixtures processed: {len(fixtures)}")
        print(f"   Matches updated: {updated_count}")
        print(f"   Matches created: {created_count}")
        print(f"   Total processed: {total_processed}")
        print(f"   API requests used: {self.requests_made}")
        
        return total_processed
    
    def cleanup_old_upcoming_fixtures(self):
        """Remove fixtures that are now completed"""
        try:
            # Find fixtures that should now be matches
            completed_fixture_ids = []
            
            for match in self.updated_matches:
                # Find corresponding fixture
                fixture = Fixture.query.filter_by(
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    date=datetime.combine(match.date, datetime.min.time())
                ).first()
                
                if fixture:
                    completed_fixture_ids.append(fixture.id)
            
            if completed_fixture_ids:
                # Remove completed fixtures
                Fixture.query.filter(Fixture.id.in_(completed_fixture_ids)).delete()
                db.session.commit()
                print(f"🧹 Cleaned up {len(completed_fixture_ids)} completed fixtures")
                
        except Exception as e:
            print(f"⚠️  Error cleaning up fixtures: {e}")
            db.session.rollback()

def main():
    """Main function for 3-hour match updates"""
    print(f"⚽ Match Results Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
                updater = MatchResultsUpdater(api_key, max_requests_per_update=200)
                
                # Update matches from recent fixtures
                matches_processed = updater.update_matches_from_fixtures()
                
                # Cleanup old upcoming fixtures that are now completed
                updater.cleanup_old_upcoming_fixtures()
                
                print(f"\n🎉 3-hour update cycle complete!")
                print(f"📊 Total matches processed: {matches_processed}")
                print(f"🔢 API requests used: {updater.requests_made}")
                
                return matches_processed > 0 or updater.requests_made > 0
                
        except ImportError:
            # Fallback without Flask context
            print("⚠️  Running without Flask context")
            updater = MatchResultsUpdater(api_key, max_requests_per_update=200)
            matches_processed = updater.update_matches_from_fixtures()
            
            print(f"✅ Update complete! Processed {matches_processed} matches")
            return matches_processed > 0
            
    except Exception as e:
        print(f"❌ Error during match update: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_scheduling_info():
    """Show how to schedule this script to run every 3 hours"""
    print("\n📅 Scheduling Match Updates Every 3 Hours")
    print("=" * 50)
    
    print("🕐 Cron Job Configuration:")
    print("   Add this line to your crontab (crontab -e):")
    print("   0 */3 * * * cd /path/to/project && python3 match_results_updater.py")
    print()
    print("🕐 Alternative Cron Schedule (specific times):")
    print("   0 0,3,6,9,12,15,18,21 * * * cd /path/to/project && python3 match_results_updater.py")
    print()
    print("🐳 Docker/Container Scheduling:")
    print("   Use a cron container or scheduler service to run every 3 hours")
    print()
    print("☁️  Render/Heroku Scheduling:")
    print("   Configure a scheduled job to run this script every 3 hours")
    print()
    print("📋 What this script does every 3 hours:")
    print("   • Fetches completed fixtures from last 3 days")
    print("   • Updates existing matches with new scores")
    print("   • Creates new matches from completed fixtures")
    print("   • Triggers ELO recalculation for affected teams")
    print("   • Cleans up old upcoming fixtures")
    print("   • Uses ~200 API requests per run (well within daily limit)")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Match Results Updater (3-hour cycle)')
    parser.add_argument('--schedule-info', action='store_true',
                       help='Show scheduling information')
    
    args = parser.parse_args()
    
    if args.schedule_info:
        show_scheduling_info()
        sys.exit(0)
    
    success = main()
    sys.exit(0 if success else 1)