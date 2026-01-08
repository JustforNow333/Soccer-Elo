#!/usr/bin/env python3
"""
Upcoming Fixtures Manager
Fetches next week's fixtures for all mapped teams - runs once daily
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from db import db, Team, Fixture

class UpcomingFixturesManager:
    """Manage upcoming fixtures for all teams"""
    
    def __init__(self, api_key: str, max_requests_per_day: int = 7500):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.base_url = "https://v3.football.api-sports.io"
        self.max_requests_per_day = max_requests_per_day
        self.requests_made = 0
        
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting"""
        if self.requests_made >= self.max_requests_per_day - 10:
            print(f"⚠️  Approaching request limit ({self.requests_made}/{self.max_requests_per_day})")
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
            time.sleep(1.2)  # Conservative rate limiting
    
    def get_team_upcoming_fixtures(self, team_id: int, limit: int = 5) -> List[Dict]:
        """Get upcoming fixtures for a specific team"""
        current_year = datetime.now().year
        
        params = {
            "team": str(team_id),
            "season": str(current_year),
            "next": str(limit)
        }
        
        data = self._make_request("fixtures", params)
        if not data:
            return []
            
        return data.get("response", [])
    
    def fetch_all_upcoming_fixtures(self, days_ahead: int = 7) -> int:
        """Fetch upcoming fixtures for all mapped teams"""
        print(f"📅 Fetching upcoming fixtures for next {days_ahead} days...")
        
        # Get all teams with API IDs
        teams = Team.query.filter(Team.api_football_id.isnot(None)).all()
        
        if not teams:
            print("❌ No teams with API IDs found")
            return 0
            
        print(f"📊 Processing {len(teams)} teams")
        
        # Clear old upcoming fixtures
        self._cleanup_old_fixtures()
        
        total_fixtures = 0
        teams_processed = 0
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        for team in teams:
            if self.requests_made >= self.max_requests_per_day - 50:
                print(f"⚠️  Stopping at team {teams_processed} - approaching request limit")
                break
                
            print(f"🔍 {team.name} (ID: {team.api_football_id})...", end=" ")
            
            fixtures_data = self.get_team_upcoming_fixtures(team.api_football_id, limit=5)
            team_fixtures = 0
            
            for fixture_data in fixtures_data:
                if self._process_upcoming_fixture(fixture_data, cutoff_date):
                    team_fixtures += 1
                    total_fixtures += 1
            
            print(f"{team_fixtures} fixtures")
            teams_processed += 1
            
            # Commit every 20 teams
            if teams_processed % 20 == 0:
                try:
                    db.session.commit()
                    print(f"💾 Committed batch ({teams_processed} teams processed)")
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
        
        print(f"\n✅ Upcoming fixtures fetch complete!")
        print(f"📊 Teams processed: {teams_processed}")
        print(f"📅 Fixtures added: {total_fixtures}")
        print(f"🔢 API requests used: {self.requests_made}")
        
        return total_fixtures
    
    def _process_upcoming_fixture(self, fixture_data: Dict, cutoff_date: datetime) -> bool:
        """Process a single upcoming fixture"""
        try:
            fixture = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            league = fixture_data.get("league", {})

            # Extract data
            api_fixture_id = fixture.get("id")
            fixture_date_str = fixture.get("date")
            status = fixture.get("status", {}).get("short", "NS")
            venue = fixture.get("venue", {})

            if not api_fixture_id or not fixture_date_str:
                return False

            # Parse date
            fixture_date = datetime.fromisoformat(fixture_date_str.replace('Z', '+00:00'))

            # Only include fixtures within our time window
            # Make cutoff_date timezone-aware for comparison (create new variable to avoid mutating parameter)
            cutoff_date_aware = cutoff_date
            if cutoff_date_aware.tzinfo is None:
                from zoneinfo import ZoneInfo
                cutoff_date_aware = cutoff_date_aware.replace(tzinfo=ZoneInfo("UTC"))

            if fixture_date > cutoff_date_aware:
                return False
            
            # Skip if not upcoming (should be NS, TBD, or POST)
            if status not in ["NS", "TBD", "POST"]:
                return False
            
            # Get team data
            home_team_data = teams.get("home", {})
            away_team_data = teams.get("away", {})
            
            home_team_api_id = home_team_data.get("id")
            away_team_api_id = away_team_data.get("id")
            
            # Find teams in our database
            home_team = Team.query.filter_by(api_football_id=home_team_api_id).first()
            away_team = Team.query.filter_by(api_football_id=away_team_api_id).first()
            
            # Check if fixture already exists
            existing_fixture = Fixture.query.filter_by(api_football_id=api_fixture_id).first()
            if existing_fixture:
                return False
            
            # Create fixture record
            new_fixture = Fixture(
                api_football_id=api_fixture_id,
                date=fixture_date,
                home_team_id=home_team.id if home_team else None,
                away_team_id=away_team.id if away_team else None,
                home_team_name=home_team_data.get("name", ""),
                away_team_name=away_team_data.get("name", ""),
                league_name=league.get("name", ""),
                status=status,
                venue=venue.get("name", "")
            )
            
            db.session.add(new_fixture)
            return True
            
        except Exception as e:
            print(f"❌ Error processing fixture: {e}")
            return False
    
    def _cleanup_old_fixtures(self):
        """Remove old upcoming fixtures that have passed"""
        try:
            from zoneinfo import ZoneInfo
            cutoff_date = datetime.now(ZoneInfo("UTC")) - timedelta(hours=2)  # 2 hour buffer
            
            old_fixtures = Fixture.query.filter(
                Fixture.date < cutoff_date,
                Fixture.status.in_(["NS", "TBD", "POST"])
            ).all()
            
            if old_fixtures:
                for fixture in old_fixtures:
                    db.session.delete(fixture)
                
                db.session.commit()
                print(f"🧹 Cleaned up {len(old_fixtures)} old upcoming fixtures")
            
        except Exception as e:
            print(f"❌ Error cleaning up fixtures: {e}")
            db.session.rollback()

def main():
    """Standalone script to fetch upcoming fixtures"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        return False
    
    print("📅 Upcoming Fixtures Daily Update")
    print("=" * 50)
    
    try:
        manager = UpcomingFixturesManager(api_key)
        fixtures_added = manager.fetch_all_upcoming_fixtures(days_ahead=7)
        
        print(f"\n🎉 Daily update complete!")
        print(f"📅 Fixtures added: {fixtures_added}")
        print(f"🔢 API requests used: {manager.requests_made}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during update: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)