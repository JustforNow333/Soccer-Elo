from db import db
from app import app
from import_data import import_matches_from_csv, generate_football_data_urls
from fixture_import import fetch_next_48_hours_fixtures
from apscheduler.schedulers.blocking import BlockingScheduler

def import_all_once():
    print("Importing all matches ONCE at startup, including Club World Cup...")
    urls = generate_football_data_urls(
        start_season=1993,
        end_season=2025,
        include_club_world_cup=True
    )
    for url in urls:
        try:
            import_matches_from_csv(url)
        except Exception as e:
            print(f"Error importing {url}: {e}")
    print("Initial import complete.")

def scheduled_fetch():
    print("Running scheduled match import (fetch)...")
    urls = generate_football_data_urls(
        start_season=2024,
        end_season=2025,
        include_club_world_cup=True
    )
    for url in urls:
        try:
            import_matches_from_csv(url)
        except Exception as e:
            print(f"Error in scheduled import {url}: {e}")
    print("Scheduled fetch complete.")

def scheduled_fixture_fetch():
    """Scheduled function to fetch fixtures from API-Football"""
    print("Running scheduled fixture fetch...")
    with app.app_context():
        fetch_next_48_hours_fixtures()
    print("Finished scheduled fixture fetch.")

if __name__ == "__main__":
    # Make sure all tables are created
    with app.app_context():
        db.create_all()
        print("All tables created (if not exist).")
        # Import all data ONCE at startup
        import_all_once()
    
    # Start scheduled jobs
    scheduler = BlockingScheduler()
    
    # Historical match data import (every 5 minutes)
    scheduler.add_job(scheduled_fetch, 'interval', minutes=5)
    
    # Fixture fetch (once per day at 8 AM UTC to stay within API limits)
    scheduler.add_job(scheduled_fixture_fetch, 'cron', hour=8, minute=0)
    
    print("Starting scheduled jobs: 5-minute fetch + daily fixture fetch...")
    scheduler.start()