import requests
import pandas as pd
from io import StringIO
from datetime import datetime
from db import db, Team, Match
from soccerelo import app, batch_update_elo_for_all_matches


def fetch_csv(url):
    print(f"Fetching: {url}")
    res = requests.get(url)
    if res.ok:
        return pd.read_csv(StringIO(res.text))
    else:
        print(f"Failed to fetch: {url}")
        return None

def get_or_create_team(name, country="Unknown"):
    team = Team.query.filter_by(name=name).first()
    if not team:
        team = Team(name=name, country=country)
        db.session.add(team)
        db.session.commit()
    return team

def import_matches_from_csv(url):
    with app.app_context():
        df = fetch_csv(url)
        if df is None:
            return

        required_cols = {"Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"}
        if not required_cols.issubset(df.columns):
            print(f"Missing required columns in {url}")
            return

        for _, row in df.iterrows():
            try:
                match_date = pd.to_datetime(row["Date"], dayfirst=True).date()
                home = get_or_create_team(row["HomeTeam"])
                away = get_or_create_team(row["AwayTeam"])
                existing_match = Match.query.filter_by(
                    date=match_date,
                    home_team_id=home.id,
                    away_team_id=away.id
                ).first()
                if existing_match:
                    continue

                match = Match(
                    date=match_date,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    home_score=int(row["FTHG"]),
                    away_score=int(row["FTAG"])
                )
                db.session.add(match)
            except Exception as e:
                print(f"Error processing row: {e}")
        
        db.session.commit()
        print("Finished importing.")

def generate_football_data_urls(
    start_season=1993, end_season=2023,
    league_codes=None
):
    """
    Generate all football-data.co.uk CSV URLs for given seasons and leagues.
    """
    if league_codes is None:
        # Most common European leagues (add more as needed)
        league_codes = [
            "E0", "E1", "E2", "E3", "EC",  # England
            "SC0", "SC1", "SC2", "SC3",    # Scotland
            "D1", "D2",                    # Germany
            "I1", "I2",                    # Italy
            "SP1", "SP2",                  # Spain
            "F1", "F2",                    # France
            "N1",                          # Netherlands
            "B1",                          # Belgium
            "P1",                          # Portugal
            "T1",                          # Turkey
            "G1",                          # Greece
            "A1",                          # Austria
            "CH1",                         # Switzerland
            "RU1",                         # Russia
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
    urls = generate_football_data_urls(start_season=1993, end_season=2024)
    for url in urls:
        import_matches_from_csv(url)
    print("All matches imported. Now updating Elo ratings...")
    with app.app_context():
        batch_update_elo_for_all_matches()
    print("Elo ratings updated for all matches.")
