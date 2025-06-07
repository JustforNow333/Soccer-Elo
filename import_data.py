import requests
import pandas as pd
from io import StringIO
from datetime import datetime, date
from db import db, Team, Match, EloRating
from app import app, update_elo_after_match
import numpy as np
import re

LEAGUE_CODE_TO_NAME = {
    "E0": "Premier League",
    "E1": "Championship",
    "E2": "League One",
    "E3": "League Two",
    "EC": "Conference",
    "SC0": "Scottish Premiership",
    "SC1": "Scottish Championship",
    "SC2": "Scottish League One",
    "SC3": "Scottish League Two",
    "D1": "Bundesliga",
    "D2": "2. Bundesliga",
    "I1": "Serie A",
    "I2": "Serie B",
    "SP1": "La Liga",
    "SP2": "Segunda Division",
    "F1": "Ligue 1",
    "F2": "Ligue 2",
    "N1": "Eredivisie",
    "B1": "Belgian First Division A",
    "P1": "Primeira Liga",
    "T1": "Süper Lig",
    "G1": "Super League Greece",
    "A1": "Austrian Bundesliga",
    "CH1": "Swiss Super League",
    "RU1": "Russian Premier League",
    # Add more as needed
}


def fetch_csv(url):
    print(f"Fetching: {url}")
    try:
        res = requests.get(url)
        if res.ok:
            # Add error handling for malformed CSV files
            try:
                return pd.read_csv(StringIO(res.text), on_bad_lines='skip')
            except pd.errors.ParserError as e:
                print(f"Parser error for {url}: {e}")
                return None
        else:
            print(f"Failed to fetch: {url}")
            return None
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_or_create_team(name, league="Unknown"):
    if not name or str(name).lower() == 'nan':
        print(f"Skipping team with invalid name: {name}")
        return None
    team = Team.query.filter_by(name=name).first()
    if not team:
        team = Team(name=name, league=league)
        db.session.add(team)
        db.session.commit()
    else:
        # Optionally update league to the latest encountered
        team.league = league
        db.session.commit()
    return team


def is_valid_team_name(val):
    try:
        return val is not None and str(val).strip() and str(
            val).lower() != "nan"
    except Exception:
        return False


def import_matches_from_csv(url):
    with app.app_context():
        df = fetch_csv(url)
        if df is None:
            return

        required_cols = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
        if not required_cols.issubset(df.columns):
            print(f"Missing required columns in {url}")
            return

        # Cache latest ELO ratings to avoid N+1 queries
        elo_cache = {}
        
        def get_latest_elo(team_id):
            if team_id not in elo_cache:
                latest_elo = EloRating.query.filter_by(team_id=team_id).order_by(
                    EloRating.date.desc()).first()
                elo_cache[team_id] = latest_elo.rating if latest_elo else 1000
            return elo_cache[team_id]

        matches_to_add = []
        elos_to_add = []

        # Extract league code from URL
        def extract_league_from_url(url):
            match = re.search(r'/([A-Z0-9]+)\.csv$', url)
            if match:
                return match.group(1)
            return "Unknown"
        league_code = extract_league_from_url(url)
        league = LEAGUE_CODE_TO_NAME.get(league_code, league_code)

        for _, row in df.iterrows():
            try:
                home_team = row["HomeTeam"]
                away_team = row["AwayTeam"]

                # Convert to string if not null, else set to empty string
                home_team_str = str(home_team).strip() if is_valid_team_name(
                    home_team) else ""
                away_team_str = str(away_team).strip() if is_valid_team_name(
                    away_team) else ""

                if not home_team_str or not away_team_str:
                    print(
                        f"Skipping row with missing or invalid team name: {row}"
                    )
                    continue

                date_val = row["Date"]

                # If it's already a datetime.date (but not a datetime.datetime), use as is
                if isinstance(date_val,
                              datetime) and not isinstance(date_val, date):
                    match_date = date_val.date()
                elif isinstance(date_val, date):
                    match_date = date_val
                else:
                    # Try to parse with pandas
                    parsed = pd.to_datetime(date_val,
                                            dayfirst=True,
                                            errors="coerce")
                    if isinstance(parsed, pd.Series):
                        if parsed.isnull().any():
                            print(f"Skipping row with invalid date: {row}")
                            continue
                        match_date = parsed.iloc[0].date()
                    else:
                        if pd.isnull(parsed):
                            print(f"Skipping row with invalid date: {row}")
                            continue
                        match_date = parsed.date()

                home = get_or_create_team(home_team, league)
                away = get_or_create_team(away_team, league)
                if home is None or away is None:
                    print(f"Skipping match due to invalid team: {row}")
                    continue
                # Only access .id after confirming home and away are not None
                assert home is not None and away is not None, "Team creation failed unexpectedly"
                existing_match = Match.query.filter_by(
                    date=match_date,
                    home_team_id=home.id,
                    away_team_id=away.id).first()
                if existing_match:
                    continue

                match = Match(date=match_date,
                              home_team_id=home.id,
                              away_team_id=away.id,
                              home_score=int(row["FTHG"]),
                              away_score=int(row["FTAG"]))
                matches_to_add.append(match)

                # Get current ELO ratings from cache
                home_rating_val = get_latest_elo(home.id)
                away_rating_val = get_latest_elo(away.id)

                # Calculate new Elo ratings
                from app import get_match_result, update_elo
                home_score, away_score = get_match_result(
                    match.home_score, match.away_score)

                new_home_rating = update_elo(home_rating_val, away_rating_val,
                                             home_score)
                new_away_rating = update_elo(away_rating_val, home_rating_val,
                                             away_score)

                # Update cache with new ratings
                elo_cache[home.id] = new_home_rating
                elo_cache[away.id] = new_away_rating

                # Prepare ELO ratings for batch insert
                home_elo = EloRating(team_id=home.id,
                                     date=match_date,
                                     rating=new_home_rating)
                away_elo = EloRating(team_id=away.id,
                                     date=match_date,
                                     rating=new_away_rating)

                elos_to_add.extend([home_elo, away_elo])

            except Exception as e:
                print(f"Error processing row: {e}")

        # Batch insert all matches and ELO ratings
        if matches_to_add:
            db.session.add_all(matches_to_add)
            db.session.add_all(elos_to_add)
            db.session.commit()
            print(f"Added {len(matches_to_add)} matches with ELO ratings")
        
        print("Finished importing.")


def generate_football_data_urls(start_season=1993,
                                end_season=2004,
                                league_codes=None):
    """
    Generate all football-data.co.uk CSV URLs for given seasons and leagues.
    """
    if league_codes is None:
        # Most common European leagues (add more as needed)
        league_codes = [
            "E0",
            "E1",
            "E2",
            "E3",
            "EC",  # England
            "SC0",
            "SC1",
            "SC2",
            "SC3",  # Scotland
            "D1",
            "D2",  # Germany
            "I1",
            "I2",  # Italy
            "SP1",
            "SP2",  # Spain
            "F1",
            "F2",  # France
            "N1",  # Netherlands
            "B1",  # Belgium
            "P1",  # Portugal
            "T1",  # Turkey
            "G1",  # Greece
            "A1",  # Austria
            "CH1",  # Switzerland
            "RU1",  # Russia
        ]
    urls = []
    for year in range(start_season, end_season):
        # e.g., 2000-01 season is 0001, 2022-23 is 2223
        season = f"{str(year)[-2:]}{str(year+1)[-2:]}"
        for code in league_codes:
            url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
            urls.append(url)
    return urls


if __name__ == "__main__":
    # Generate all URLs for all leagues/seasons
    # Ensure database tables are created before importing
    with app.app_context():
        db.create_all()

    urls = generate_football_data_urls(start_season=1993, end_season=2004
    )
    for url in urls:
        import_matches_from_csv(url)
    print("All matches and Elo ratings imported successfully!")
