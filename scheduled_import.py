from apscheduler.schedulers.blocking import BlockingScheduler
from import_data import import_matches_from_csv, generate_football_data_urls

def scheduled_fetch():
    print("Running scheduled match import...")
    urls = generate_football_data_urls(start_season=2024, end_season=2025, include_club_world_cup=True)
    for url in urls:
        import_matches_from_csv(url)
    print("Finished scheduled fetch.")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_fetch, 'interval', minutes=5)
    scheduler.start()

