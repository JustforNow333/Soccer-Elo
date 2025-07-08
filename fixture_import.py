import os
import requests
from datetime import datetime, timedelta
from sqlalchemy import and_
from db import db, Team, Fixture

def get_api_football_client():
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY is missing!", flush=True)
        return None

    return {
        "base_url": "https://v3.football.api-sports.io",
        "headers": {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
    }

def fetch_fixtures_by_date_range(from_date, to_date):
    client = get_api_football_client()
    if not client:
        return []

    url = f"{client['base_url']}/fixtures"
    params = {
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "season": datetime.now().year,
        "timezone": "UTC"
    }

    try:
        print(f"🔄 Fetching fixtures from {from_date} to {to_date}", flush=True)
        response = requests.get(url, headers=client["headers"], params=params, timeout=30)

        print(f"🔍 Raw API response (first 1000 chars): {response.text[:1000]}", flush=True)

        if response.status_code == 200:
            data = response.json()
            fixtures = data.get("response", [])
            print(f"✅ Fetched {len(fixtures)} fixtures", flush=True)
            return fixtures
        else:
            print(f"❌ API-Football error: {response.status_code} - {response.text}", flush=True)
            return []

    except Exception as e:
        print(f"❌ Error fetching fixtures: {str(e)}", flush=True)
        return []

def match_team_to_database(team_name, league_name=None):
    team = Team.query.filter_by(name=team_name).first()
    if team:
        return team

    team = Team.query.filter(Team.name.ilike(f"%{team_name}%")).first()
    if team:
        return team

    clean_name = team_name.replace(" FC", "").replace(" CF", "").replace("FC ", "").replace("CF ", "")
    team = Team.query.filter(Team.name.ilike(f"%{clean_name}%")).first()
    if team:
        return team

    if league_name:
        team = Team.query.filter(
            and_(Team.name.ilike(f"%{clean_name}%"), Team.league.ilike(f"%{league_name}%"))
        ).first()
        if team:
            return team

    print(f"❌ No DB match for team: '{team_name}' (league: '{league_name}')", flush=True)
    return None

def process_and_store_fixtures(api_fixtures):
    stored_count = 0
    relevant_count = 0

    for fixture_data in api_fixtures:
        try:
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

            home_team = match_team_to_database(home_team_name, league_name)
            away_team = match_team_to_database(away_team_name, league_name)

            if home_team or away_team:
                relevant_count += 1

                existing_fixture = Fixture.query.filter_by(api_football_id=api_fixture_id).first()

                if existing_fixture:
                    existing_fixture.date = fixture_date
                    existing_fixture.status = status
                    existing_fixture.venue = venue
                    existing_fixture.home_team_id = home_team.id if home_team else None
                    existing_fixture.away_team_id = away_team.id if away_team else None
                    existing_fixture.updated_at = datetime.utcnow()
                else:
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
            else:
                print(f"⚠️ Fixture skipped: {home_team_name} vs {away_team_name}", flush=True)

        except Exception as e:
            print(f"❌ Error processing fixture: {str(e)}", flush=True)
            continue

    try:
        db.session.commit()
        print(f"✅ Stored {stored_count} new fixtures, {relevant_count} relevant fixtures total", flush=True)
    except Exception as e:
        print(f"❌ Error committing fixtures: {str(e)}", flush=True)
        db.session.rollback()

def fetch_next_48_hours_fixtures():
    print("🔄 Starting fixture fetch for next 7 days...", flush=True)

    today = datetime.now().date()
    end_date = today + timedelta(days=7)

    fixtures = fetch_fixtures_by_date_range(today, end_date)

    if fixtures:
        process_and_store_fixtures(fixtures)
        print(f"✅ Fixture fetch completed", flush=True)
    else:
        print("❌ No fixtures fetched", flush=True)