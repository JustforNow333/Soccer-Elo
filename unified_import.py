#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from typing import Optional
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.config import config
class UnifiedImporter:
    def __init__(self):
        self.api_key = config.get_api_key()
        if not self.api_key:
            raise ValueError("API_FOOTBALL_KEY not configured")
        self.app = None
        self.league_importer = None
        self.fixtures_manager = None
    def _init_app_context(self):
        if self.app is None:
            from app import app
            self.app = app
    def _init_league_importer(self):
        if self.league_importer is None:
            from league_based_import import LeagueBasedImporter
            self.league_importer = LeagueBasedImporter(
                api_key=self.api_key,
                max_requests_per_day=7500
            )
    def _init_fixtures_manager(self):
        if self.fixtures_manager is None:
            from upcoming_fixtures import UpcomingFixturesManager
            self.fixtures_manager = UpcomingFixturesManager(
                api_key=self.api_key,
                max_requests_per_day=7500
            )
    def migrate_database(self):
        print("\n📊 Running database migration...")
        from migrate_db import migrate_database
        migrate_database()
        print("✅ Database migration complete")
    def discover_teams(self, seasons: Optional[list] = None) -> dict:
        self._init_app_context()
        self._init_league_importer()
        if seasons is None:
            seasons = [2024, 2023]
        print(f"\n🗺️  Discovering teams through major leagues (seasons: {seasons})...")
        with self.app.app_context():
            discovered = self.league_importer.discover_teams_by_leagues(seasons)
            applied = self.league_importer.apply_discovered_teams()
            print(f"✅ Team discovery complete:")
            print(f"   Discovered: {len(discovered)} teams")
            print(f"   Applied: {applied} teams")
            return discovered
    def import_matches(self, seasons: Optional[list] = None) -> int:
        self._init_app_context()
        self._init_league_importer()
        print(f"\n📚 Importing historical match data...")
        with self.app.app_context():
            matches_imported = self.league_importer.import_team_matches(seasons)
            print(f"✅ Match import complete: {matches_imported} matches")
            return matches_imported
    def calculate_elo_ratings(self, force_recalculate: bool = False) -> dict:
        self._init_app_context()
        print(f"\n🏆 Calculating ELO ratings...")
        with self.app.app_context():
            from enhanced_elo_engine import EnhancedEloEngine
            elo_engine = EnhancedEloEngine()
            stats = elo_engine.recalculate_all_elos(force_recalculate=force_recalculate)
            print(f"✅ ELO calculation complete:")
            print(f"   Matches processed: {stats.get('total_matches_processed', 0)}")
            print(f"   Teams processed: {stats.get('teams_processed', 0)}")
            return stats
    def fetch_upcoming_fixtures(self, days_ahead: int = 7) -> int:
        self._init_app_context()
        self._init_fixtures_manager()
        print(f"\n📅 Fetching upcoming fixtures ({days_ahead} days ahead)...")
        with self.app.app_context():
            if self.league_importer:
                self.fixtures_manager.requests_made = self.league_importer.requests_made
            fixtures_count = self.fixtures_manager.fetch_all_upcoming_fixtures(days_ahead)
            print(f"✅ Fixture fetch complete: {fixtures_count} fixtures")
            return fixtures_count
    def run_complete_setup(self, skip_fixtures: bool = False) -> bool:
        print("🚀 Starting Complete System Setup")
        print("=" * 60)
        try:
            self._init_app_context()
            with self.app.app_context():
                self.migrate_database()
                discovered = self.discover_teams()
                if len(discovered) < 50:
                    print(f"⚠️  Only {len(discovered)} teams discovered. Expected at least 50.")
                    print("💡 This may indicate an API issue or mapping problem.")
                    return False
                self._init_league_importer()
                if self.league_importer.requests_made < 6000:
                    matches = self.import_matches()
                    if matches < 100:
                        print(f"⚠️  Only {matches} matches imported. Expected more.")
                else:
                    print("⚠️  Insufficient API budget for match import")
                    print("💡 Run match import separately when API limit resets")
                    return False
                stats = self.calculate_elo_ratings(force_recalculate=True)
                if not skip_fixtures:
                    if self.league_importer.requests_made < 7200:
                        fixtures = self.fetch_upcoming_fixtures()
                    else:
                        print("⚠️  Skipping fixtures - insufficient API budget")
                        fixtures = 0
                else:
                    fixtures = 0
                    print("⏭️  Skipping fixtures as requested")
                total_requests = self.league_importer.requests_made
                if self.fixtures_manager:
                    total_requests = max(total_requests, self.fixtures_manager.requests_made)
                print("\n🎉 Complete setup finished!")
                print("=" * 60)
                print(f"📊 Final Stats:")
                print(f"   Teams discovered: {len(discovered)}")
                print(f"   Matches imported: {matches if 'matches' in locals() else 0}")
                print(f"   ELO matches processed: {stats.get('total_matches_processed', 0)}")
                print(f"   Upcoming fixtures: {fixtures if 'fixtures' in locals() else 0}")
                print(f"   API requests used: {total_requests}/7500")
                return True
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Unified Import System")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    setup_parser = subparsers.add_parser('setup', help='Run complete system setup')
    setup_parser.add_argument('--skip-fixtures', action='store_true',
                             help='Skip fixture fetching to save API requests')
    discover_parser = subparsers.add_parser('discover', help='Discover teams only')
    discover_parser.add_argument('--seasons', nargs='+', type=int,
                                help='Seasons to check (default: 2024 2023)')
    import_parser = subparsers.add_parser('import-matches', help='Import historical matches')
    elo_parser = subparsers.add_parser('calculate-elo', help='Calculate ELO ratings')
    elo_parser.add_argument('--force', action='store_true',
                           help='Force full recalculation')
    fixtures_parser = subparsers.add_parser('fetch-fixtures', help='Fetch upcoming fixtures')
    fixtures_parser.add_argument('--days', type=int, default=7,
                                help='Days ahead to fetch (default: 7)')
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    try:
        importer = UnifiedImporter()
        if args.command == 'setup':
            success = importer.run_complete_setup(skip_fixtures=args.skip_fixtures)
            sys.exit(0 if success else 1)
        elif args.command == 'discover':
            seasons = args.seasons if args.seasons else None
            importer.discover_teams(seasons)
        elif args.command == 'import-matches':
            importer.import_matches()
        elif args.command == 'calculate-elo':
            importer.calculate_elo_ratings(force_recalculate=args.force)
        elif args.command == 'fetch-fixtures':
            importer.fetch_upcoming_fixtures(days_ahead=args.days)
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to set API_FOOTBALL_KEY environment variable")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
if __name__ == "__main__":
    main()