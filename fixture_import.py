import os
import requests
from datetime import datetime, timedelta
from sqlalchemy import and_
from db import db, Team, Fixture
from import_data import normalize_team_name

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
    Uses the same normalization as import_data.py for consistent matching.
    """
    # Normalize the API team name the same way as when teams were created
    normalized_api_name = normalize_team_name(team_name)
    
    print(f"🔍 Matching team: '{team_name}' -> normalized: '{normalized_api_name}'")
    
    # Direct match with normalized name
    team = Team.query.filter_by(name=normalized_api_name).first()
    if team:
        print(f"✅ Direct match found: {team.name} (ID: {team.id})")
        return team
    
    # Try case-insensitive match (backup for any edge cases)
    team = Team.query.filter(Team.name.ilike(f"%{normalized_api_name}%")).first()
    if team:
        print(f"✅ Case-insensitive match found: {team.name} (ID: {team.id})")
        return team
    
    # Try partial matches (handle common variations)
    # Remove common suffixes/prefixes that might differ
    clean_name = normalized_api_name.replace(" fc", "").replace(" cf", "").replace("fc ", "").replace("cf ", "")
    team = Team.query.filter(Team.name.ilike(f"%{clean_name}%")).first()
    if team:
        print(f"✅ Partial match found: {team.name} (ID: {team.id}) using clean_name: '{clean_name}'")
        return team
    
    # If league is provided, try to match within that league
    if league_name:
        normalized_league = normalize_team_name(league_name)
        team = Team.query.filter(
            and_(Team.name.ilike(f"%{clean_name}%"), Team.league.ilike(f"%{normalized_league}%"))
        ).first()
        if team:
            print(f"✅ League-specific match found: {team.name} (ID: {team.id}) in league: '{normalized_league}'")
            return team
    
    print(f"❌ No match found for: '{team_name}' (normalized: '{normalized_api_name}')")
    return None

def process_and_store_fixtures(api_fixtures):
    """
    Process fixtures from API-Football and store in database.
    Only store fixtures involving teams we have in our database.
    """
    stored_count = 0
    relevant_count = 0
    no_match_count = 0
    
    print(f"🔄 Processing {len(api_fixtures)} fixtures from API Football...")
    
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
            
            print(f"\n📅 Processing fixture: {home_team_name} vs {away_team_name} ({league_name})")
            
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
                    print(f"🔄 Updated existing fixture (ID: {existing_fixture.id})")
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
                    print(f"✅ Added new fixture")
                    
                match_status = []
                if home_team:
                    match_status.append(f"Home: {home_team.name}")
                if away_team:
                    match_status.append(f"Away: {away_team.name}")
                print(f"   Teams matched: {', '.join(match_status)}")
                
            else:
                no_match_count += 1
                print(f"❌ No team matches found - skipping fixture")
                
        except Exception as e:
            print(f"❌ Error processing fixture: {str(e)}")
            continue
    
    try:
        db.session.commit()
        print(f"\n✅ Fixture import completed:")
        print(f"   📊 Total fixtures from API: {len(api_fixtures)}")
        print(f"   🎯 Relevant fixtures (with our teams): {relevant_count}")
        print(f"   ➕ New fixtures stored: {stored_count}")
        print(f"   ❌ No team matches: {no_match_count}")
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