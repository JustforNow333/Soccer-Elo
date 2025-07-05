import os
import requests
from datetime import datetime, timedelta
from sqlalchemy import and_
from db import db, Team, Fixture

def get_api_football_client():
    """Get API-Football client configuration"""
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY is missing!")
        return None
    
    return {
        "base_url": "https://v3.football.api-sports.io",
        "headers": {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
    }

def fetch_fixtures_by_date_range(from_date, to_date):
    """
    Fetch fixtures from API-Football for a specific date range.
    This is the efficient approach - one request can return many matches.
    """
    client = get_api_football_client()
    if not client:
        return []

    url = f"{client['base_url']}/fixtures"
    params = {
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "timezone": "UTC"
    }

    try:
        print(f"🔄 Fetching fixtures from {from_date} to {to_date}")
        response = requests.get(url, headers=client["headers"], params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("response", [])
            print(f"✅ Fetched {len(fixtures)} fixtures")
            return fixtures
        else:
            print(f"❌ API-Football error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching fixtures: {str(e)}")
        return []

def match_team_to_database(team_name, league_name=None):
    """
    Match API-Football team name to our database team.
    Uses fuzzy matching to handle name variations.
    """
    # Direct match first
    team = Team.query.filter_by(name=team_name).first()
    if team:
        return team
    
    # Try case-insensitive match
    team = Team.query.filter(Team.name.ilike(f"%{team_name}%")).first()
    if team:
        return team
    
    # Try partial matches (handle common variations)
    # Remove common suffixes/prefixes that might differ
    clean_name = team_name.replace(" FC", "").replace(" CF", "").replace("FC ", "").replace("CF ", "")
    team = Team.query.filter(Team.name.ilike(f"%{clean_name}%")).first()
    if team:
        return team
    
    # If league is provided, try to match within that league
    if league_name:
        team = Team.query.filter(
            and_(Team.name.ilike(f"%{clean_name}%"), Team.league.ilike(f"%{league_name}%"))
        ).first()
        if team:
            return team
    
    return None

def process_and_store_fixtures(api_fixtures):
    """
    Process fixtures from API-Football and store in database.
    Only store fixtures involving teams we have in our database.
    """
    stored_count = 0
    relevant_count = 0
    
    for fixture_data in api_fixtures:
        try:
            # Extract fixture information
            fixture_info = fixture_data.get("fixture", {})
            teams_info = fixture_data.get("teams", {})
            league_info = fixture_data.get("league", {})
            
            api_fixture_id = fixture_info.get("id")
            fixture_date = datetime.fromisoformat(fixture_info.get("date").replace("Z", "+00:00"))
            status = fixture_info.get("status", {}).get("short", "NS")
            venue = fixture_info.get("venue", {}).get("name", "")
            
            home_team_name = teams_info.get("home", {}).get("name", "")
            away_team_name = teams_info.get("away", {}).get("name", "")
            league_name = league_info.get("name", "")
            
            # Try to match teams to our database
            home_team = match_team_to_database(home_team_name, league_name)
            away_team = match_team_to_database(away_team_name, league_name)
            
            # Only store if at least one team is in our database
            if home_team or away_team:
                relevant_count += 1
                
                # Check if fixture already exists
                existing_fixture = Fixture.query.filter_by(api_football_id=api_fixture_id).first()
                
                if existing_fixture:
                    # Update existing fixture
                    existing_fixture.date = fixture_date
                    existing_fixture.status = status
                    existing_fixture.venue = venue
                    existing_fixture.home_team_id = home_team.id if home_team else None
                    existing_fixture.away_team_id = away_team.id if away_team else None
                    existing_fixture.updated_at = datetime.utcnow()
                else:
                    # Create new fixture
                    new_fixture = Fixture(
                        api_football_id=api_fixture_id,
                        date=fixture_date,
                        home_team_id=home_team.id if home_team else None,
                        away_team_id=away_team.id if away_team else None,
                        home_team_name=home_team_name,
                        away_team_name=away_team_name,
                        league_name=league_name,
                        status=status,
                        venue=venue
                    )
                    db.session.add(new_fixture)
                    stored_count += 1
                
        except Exception as e:
            print(f"❌ Error processing fixture: {str(e)}")
            continue
    
    try:
        db.session.commit()
        print(f"✅ Stored {stored_count} new fixtures, {relevant_count} relevant fixtures total")
    except Exception as e:
        print(f"❌ Error committing fixtures: {str(e)}")
        db.session.rollback()

def fetch_next_48_hours_fixtures():
    """
    Main function to fetch fixtures for the next 48 hours.
    This uses only 1-2 API requests and covers all teams.
    """
    print("🔄 Starting fixture fetch for next 48 hours...")
    
    # Get date range (today to +48 hours)
    today = datetime.now().date()
    end_date = today + timedelta(days=2)
    
    # Fetch fixtures for the date range
    fixtures = fetch_fixtures_by_date_range(today, end_date)
    
    if fixtures:
        process_and_store_fixtures(fixtures)
        print(f"✅ Fixture fetch completed")
    else:
        print("❌ No fixtures fetched") 