#!/usr/bin/env python3
"""
Comprehensive API-Football Import Script

Features:
- Fetches top 100 leagues based on coverage and popularity
- Imports teams and fixtures for each league
- Batched database operations
- Request throttling and caching
- Comprehensive logging
- Command line controls
"""

import os
import sys
import time
import argparse
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Set, Dict, List, Optional, Tuple
import json

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db, Team, Match, EloRating, Fixture
from elo_utils import update_elo, get_match_result
import unicodedata


class APIFootballImporter:
    """Comprehensive API-Football data importer with optimization and caching"""
    
    def __init__(self, api_key: str, current_season: int = None, request_delay: float = 0.5):
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.current_season = current_season or datetime.now().year
        self.request_delay = request_delay
        
        # Request tracking
        self.requests_made = 0
        self.max_requests_per_day = 7500
        
        # Caching to avoid redundant requests
        self.cached_teams: Set[int] = set()  # API team IDs
        self.cached_fixtures: Set[int] = set()  # API fixture IDs
        self.league_cache: Dict[int, dict] = {}
        self.team_cache: Dict[int, dict] = {}
        
        # Batch storage for efficient database operations
        self.teams_batch: List[Team] = []
        self.fixtures_batch: List[Fixture] = []
        self.matches_batch: List[Match] = []
        self.elo_batch: List[EloRating] = []
        
        # Statistics
        self.stats = {
            "leagues_processed": 0,
            "teams_fetched": 0,
            "teams_created": 0,
            "fixtures_fetched": 0,
            "fixtures_created": 0,
            "matches_created": 0,
            "requests_made": 0,
            "skipped_items": 0
        }
        
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing teams and fixtures from database to avoid duplicates"""
        print("🔄 Loading existing data from database...")
        
        # Load existing teams by their API IDs (if column exists)
        try:
            from sqlalchemy import text
            existing_teams = db.session.execute(
                text("SELECT api_football_id FROM teams WHERE api_football_id IS NOT NULL")
            ).fetchall()
            self.cached_teams.update(row[0] for row in existing_teams if row[0])
            print(f"✅ Loaded {len(self.cached_teams)} existing teams")
        except Exception as e:
            print(f"⚠️  Could not load existing teams (table may need migration): {e}")
        
        # Load existing fixtures
        try:
            from sqlalchemy import text
            existing_fixtures = db.session.execute(
                text("SELECT api_football_id FROM fixtures")
            ).fetchall()
            self.cached_fixtures.update(row[0] for row in existing_fixtures)
            print(f"✅ Loaded {len(self.cached_fixtures)} existing fixtures")
        except Exception as e:
            print(f"⚠️  Could not load existing fixtures: {e}")
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make throttled API request with error handling"""
        if self.requests_made >= self.max_requests_per_day:
            print(f"❌ Daily request limit ({self.max_requests_per_day}) reached!")
            return None
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            time.sleep(self.request_delay)  # Throttle requests
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.requests_made += 1
            self.stats["requests_made"] = self.requests_made
            
            if response.status_code == 200:
                data = response.json()
                if data.get("errors"):
                    print(f"❌ API Error: {data['errors']}")
                    return None
                return data
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            return None
    
    def get_top_leagues(self, limit: int = 100) -> List[dict]:
        """Fetch top leagues with coverage filters"""
        print(f"🔄 Fetching top {limit} leagues...")
        
        params = {
            "season": str(self.current_season)
        }
        
        data = self._make_request("leagues", params)
        if not data:
            return []
        
        leagues = data.get("response", [])
        
        # Filter leagues based on requirements
        filtered_leagues = []
        for league_data in leagues:
            league = league_data.get("league", {})
            country = league_data.get("country", {})
            seasons = league_data.get("seasons", [])
            
            # Find current season data
            current_season_data = None
            for season in seasons:
                if season.get("year") == self.current_season:
                    current_season_data = season
                    break
            
            if not current_season_data:
                continue
            
            coverage = current_season_data.get("coverage", {})
            
            # Apply filters
            if (coverage.get("odds", False) and 
                league.get("type") in ["league", "cup"] and
                country.get("name") != "World"):  # Focus on national leagues
                
                filtered_leagues.append({
                    "id": league.get("id"),
                    "name": league.get("name"),
                    "country": country.get("name"),
                    "type": league.get("type"),
                    "logo": league.get("logo"),
                    "coverage": coverage
                })
        
        # Sort by type (leagues first) and then by country importance
        def league_priority(league):
            # Major leagues get higher priority
            major_countries = ["England", "Spain", "Germany", "Italy", "France", "Netherlands", "Portugal"]
            country_score = 100 if league["country"] in major_countries else 50
            type_score = 100 if league["type"] == "league" else 50
            return country_score + type_score
        
        filtered_leagues.sort(key=league_priority, reverse=True)
        
        top_leagues = filtered_leagues[:limit]
        print(f"✅ Found {len(top_leagues)} qualifying leagues")
        
        return top_leagues
    
    def get_league_teams(self, league_id: int, season: int) -> List[dict]:
        """Fetch all teams for a specific league and season"""
        print(f"🔄 Fetching teams for league {league_id}, season {season}")
        
        params = {
            "league": str(league_id),
            "season": str(season)
        }
        
        data = self._make_request("teams", params)
        if not data:
            return []
        
        teams = []
        for team_data in data.get("response", []):
            team = team_data.get("team", {})
            venue = team_data.get("venue", {})
            
            teams.append({
                "id": team.get("id"),
                "name": team.get("name"),
                "code": team.get("code"),
                "country": team.get("country"),
                "founded": team.get("founded"),
                "logo": team.get("logo"),
                "venue": venue.get("name"),
                "league_id": league_id
            })
        
        print(f"✅ Found {len(teams)} teams for league {league_id}")
        self.stats["teams_fetched"] += len(teams)
        
        return teams
    
    def get_team_fixtures(self, team_id: int, season: int, league_id: int = None) -> List[dict]:
        """Fetch fixtures for a specific team and season"""
        params = {
            "team": str(team_id),
            "season": str(season)
        }
        
        if league_id:
            params["league"] = str(league_id)
        
        data = self._make_request("fixtures", params)
        if not data:
            return []
        
        fixtures = []
        for fixture_data in data.get("response", []):
            fixture = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            league = fixture_data.get("league", {})
            goals = fixture_data.get("goals", {})
            
            fixture_id = fixture.get("id")
            if fixture_id in self.cached_fixtures:
                self.stats["skipped_items"] += 1
                continue
            
            fixtures.append({
                "api_fixture_id": fixture_id,
                "date": fixture.get("date"),
                "status": fixture.get("status", {}).get("short"),
                "venue": fixture.get("venue", {}).get("name"),
                "home_team": teams.get("home", {}),
                "away_team": teams.get("away", {}),
                "league": league,
                "goals": goals,
                "referee": fixture.get("referee")
            })
            
            self.cached_fixtures.add(fixture_id)
        
        self.stats["fixtures_fetched"] += len(fixtures)
        return fixtures
    
    def normalize_team_name(self, name: str) -> str:
        """Normalize team name for consistency"""
        if not name:
            return ""
        # Remove accents, lowercase, strip whitespace
        name = unicodedata.normalize('NFKD', name)
        name = "".join([c for c in name if not unicodedata.combining(c)])
        return name.strip().lower()
    
    def create_or_update_team(self, team_data: dict, league_name: str) -> Optional[Team]:
        """Create or update team in database"""
        api_team_id = team_data.get("id")
        if api_team_id in self.cached_teams:
            return None
        
        normalized_name = self.normalize_team_name(team_data.get("name", ""))
        if not normalized_name:
            return None
        
        # Check if team already exists
        existing_team = Team.query.filter_by(name=normalized_name).first()
        
        if existing_team:
            # Update league if different
            if existing_team.league != league_name:
                existing_team.league = league_name
                db.session.commit()
            return existing_team
        
        # Create new team
        team = Team(
            name=normalized_name,
            league=league_name,
            api_football_id=api_team_id
        )
        
        self.teams_batch.append(team)
        self.cached_teams.add(api_team_id)
        self.stats["teams_created"] += 1
        
        return team
    
    def process_fixture(self, fixture_data: dict, league_name: str) -> bool:
        """Process a single fixture and create database records"""
        try:
            # Parse fixture data
            api_fixture_id = fixture_data.get("api_fixture_id")
            date_str = fixture_data.get("date")
            status = fixture_data.get("status", "NS")
            
            if not date_str:
                return False
            
            fixture_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            
            # Get team data
            home_team_data = fixture_data.get("home_team", {})
            away_team_data = fixture_data.get("away_team", {})
            
            home_team_name = self.normalize_team_name(home_team_data.get("name", ""))
            away_team_name = self.normalize_team_name(away_team_data.get("name", ""))
            
            if not home_team_name or not away_team_name:
                return False
            
            # Find or create teams
            home_team = Team.query.filter_by(name=home_team_name).first()
            away_team = Team.query.filter_by(name=away_team_name).first()
            
            # Create fixture record
            fixture = Fixture(
                api_football_id=api_fixture_id,
                date=fixture_date,
                home_team_id=home_team.id if home_team else None,
                away_team_id=away_team.id if away_team else None,
                home_team_name=home_team_data.get("name", ""),
                away_team_name=away_team_data.get("name", ""),
                league_name=league_name,
                status=status,
                venue=fixture_data.get("venue", "")
            )
            
            self.fixtures_batch.append(fixture)
            self.stats["fixtures_created"] += 1
            
            # If fixture is finished and both teams exist, create match and update Elo
            if (status == "FT" and 
                home_team and away_team and 
                fixture_data.get("goals")):
                
                goals = fixture_data.get("goals", {})
                home_score = goals.get("home", 0) or 0
                away_score = goals.get("away", 0) or 0
                
                match = Match(
                    date=fixture_date.date(),
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    home_score=home_score,
                    away_score=away_score
                )
                
                self.matches_batch.append(match)
                self.stats["matches_created"] += 1
                
                # Calculate Elo updates
                self._add_elo_updates(home_team, away_team, home_score, away_score, fixture_date.date())
            
            return True
            
        except Exception as e:
            print(f"❌ Error processing fixture {api_fixture_id}: {str(e)}")
            return False
    
    def _add_elo_updates(self, home_team: Team, away_team: Team, 
                        home_score: int, away_score: int, match_date):
        """Calculate and queue Elo rating updates"""
        # Get latest ratings
        home_rating = EloRating.query.filter_by(team_id=home_team.id)\
                                   .order_by(EloRating.date.desc()).first()
        away_rating = EloRating.query.filter_by(team_id=away_team.id)\
                                   .order_by(EloRating.date.desc()).first()
        
        home_rating_val = home_rating.rating if home_rating else 1000
        away_rating_val = away_rating.rating if away_rating else 1000
        
        # Calculate match result
        home_result, away_result = get_match_result(home_score, away_score)
        
        # Update ratings
        new_home_rating = update_elo(home_rating_val, away_rating_val, home_result)
        new_away_rating = update_elo(away_rating_val, home_rating_val, away_result)
        
        # Queue Elo updates
        self.elo_batch.append(EloRating(
            team_id=home_team.id,
            date=match_date,
            rating=new_home_rating
        ))
        
        self.elo_batch.append(EloRating(
            team_id=away_team.id,
            date=match_date,
            rating=new_away_rating
        ))
    
    def commit_batched_data(self):
        """Commit all batched data to database"""
        try:
            if self.teams_batch:
                db.session.add_all(self.teams_batch)
                print(f"💾 Committing {len(self.teams_batch)} teams...")
                
            if self.fixtures_batch:
                db.session.add_all(self.fixtures_batch)
                print(f"💾 Committing {len(self.fixtures_batch)} fixtures...")
                
            if self.matches_batch:
                db.session.add_all(self.matches_batch)
                print(f"💾 Committing {len(self.matches_batch)} matches...")
                
            if self.elo_batch:
                db.session.add_all(self.elo_batch)
                print(f"💾 Committing {len(self.elo_batch)} Elo ratings...")
            
            db.session.commit()
            
            # Clear batches
            self.teams_batch.clear()
            self.fixtures_batch.clear()
            self.matches_batch.clear()
            self.elo_batch.clear()
            
            print("✅ Batch commit successful")
            
        except Exception as e:
            print(f"❌ Batch commit failed: {str(e)}")
            db.session.rollback()
    
    def import_league_data(self, league: dict, max_teams: int = None):
        """Import all data for a specific league"""
        league_id = league["id"]
        league_name = league["name"]
        
        print(f"\n🏆 Processing league: {league_name} (ID: {league_id})")
        
        # Get teams for this league
        teams = self.get_league_teams(league_id, self.current_season)
        if max_teams:
            teams = teams[:max_teams]
        
        # Process teams
        for team_data in teams:
            team = self.create_or_update_team(team_data, league_name)
            
            # Get fixtures for this team
            print(f"  🔄 Getting fixtures for {team_data['name']}...")
            fixtures = self.get_team_fixtures(
                team_data["id"], 
                self.current_season, 
                league_id
            )
            
            # Process fixtures
            for fixture_data in fixtures:
                self.process_fixture(fixture_data, league_name)
            
            # Commit in batches to avoid memory issues
            if len(self.fixtures_batch) >= 100:
                self.commit_batched_data()
        
        # Final commit for this league
        self.commit_batched_data()
        self.stats["leagues_processed"] += 1
    
    def run_frequent_season_update(self, season: int = None):
        """
        Frequent season update - optimized for 5-minute intervals
        Focuses on recent fixtures and live matches for current season
        """
        target_season = season or self.current_season
        print(f"🔄 Starting frequent season update for {target_season}")
        print(f"⏱️  Request delay: {self.request_delay}s")
        
        start_time = datetime.now()
        
        # Check if we have enough API requests remaining
        if self.requests_made >= self.max_requests_per_day - 50:  # Need buffer for frequent updates
            print(f"❌ Insufficient API requests remaining ({self.max_requests_per_day - self.requests_made})")
            print("⚠️  Skipping frequent update to preserve daily quota")
            return
        
        # Get major leagues only for frequent updates
        major_leagues = [
            {"id": 39, "name": "Premier League", "country": "England"},
            {"id": 140, "name": "La Liga", "country": "Spain"},
            {"id": 78, "name": "Bundesliga", "country": "Germany"},
            {"id": 135, "name": "Serie A", "country": "Italy"},
            {"id": 61, "name": "Ligue 1", "country": "France"},
            {"id": 94, "name": "Primeira Liga", "country": "Portugal"},
            {"id": 88, "name": "Eredivisie", "country": "Netherlands"},
            {"id": 2, "name": "UEFA Champions League", "country": "World"},
            {"id": 3, "name": "UEFA Europa League", "country": "World"},
        ]
        
        # Get recent fixtures (last 2 days to today) for live updates
        from_date = datetime.now() - timedelta(days=2)
        to_date = datetime.now()
        
        total_fixtures_processed = 0
        leagues_processed = 0
        
        for league in major_leagues:
            if self.requests_made >= self.max_requests_per_day - 20:  # Safety buffer
                print(f"❌ Approaching request limit, stopping early")
                break
            
            print(f"🔄 Updating {league['name']}...")
            
            # Get recent fixtures for this league
            recent_fixtures = self.get_recent_fixtures(
                league["id"], 
                from_date, 
                to_date, 
                target_season
            )
            
            # Process fixtures
            for fixture_data in recent_fixtures:
                if self.process_fixture(fixture_data, league["name"]):
                    total_fixtures_processed += 1
            
            # Commit after each league to avoid losing data
            if len(self.fixtures_batch) > 0 or len(self.matches_batch) > 0:
                self.commit_batched_data()
                
            leagues_processed += 1
        
        # Final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n⚡ Frequent update completed in {duration}")
        print(f"📊 Processed {leagues_processed} leagues")
        print(f"📊 Processed {total_fixtures_processed} fixtures")
        print(f"📊 Requests used: {self.requests_made}")
        print(f"📊 Remaining requests: {self.max_requests_per_day - self.requests_made}")
    
    def get_recent_fixtures(self, league_id: int, from_date: datetime, to_date: datetime, season: int) -> List[dict]:
        """Get recent fixtures for a league (optimized for frequent updates)"""
        params = {
            "league": str(league_id),
            "season": str(season),
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d"),
            "timezone": "UTC"
        }
        
        data = self._make_request("fixtures", params)
        if not data:
            return []
        
        fixtures = []
        for fixture_data in data.get("response", []):
            fixture = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            league = fixture_data.get("league", {})
            goals = fixture_data.get("goals", {})
            
            fixture_id = fixture.get("id")
            # Always process recent fixtures to get live score updates
            
            fixtures.append({
                "api_fixture_id": fixture_id,
                "date": fixture.get("date"),
                "status": fixture.get("status", {}).get("short"),
                "venue": fixture.get("venue", {}).get("name"),
                "home_team": teams.get("home", {}),
                "away_team": teams.get("away", {}),
                "league": league,
                "goals": goals,
                "referee": fixture.get("referee")
            })
        
        print(f"✅ Found {len(fixtures)} recent fixtures for league {league_id}")
        self.stats["fixtures_fetched"] += len(fixtures)
        return fixtures
    
    def run_import(self, max_leagues: int = 100, max_teams_per_league: int = None):
        """Main import process"""
        print(f"🚀 Starting API-Football import (max {max_leagues} leagues)")
        print(f"📊 Current season: {self.current_season}")
        print(f"⏱️  Request delay: {self.request_delay}s")
        print(f"📈 Request limit: {self.max_requests_per_day}/day")
        
        start_time = datetime.now()
        
        # Get top leagues
        leagues = self.get_top_leagues(max_leagues)
        
        # Process each league
        for i, league in enumerate(leagues, 1):
            if self.requests_made >= self.max_requests_per_day:
                print(f"❌ Stopping: Daily request limit reached")
                break
            
            print(f"\n📍 Progress: {i}/{len(leagues)} leagues")
            self.import_league_data(league, max_teams_per_league)
            
            remaining_requests = self.max_requests_per_day - self.requests_made
            print(f"📊 Requests remaining: {remaining_requests}")
            
            if remaining_requests < 50:  # Safety buffer
                print(f"⚠️  Approaching request limit, stopping early")
                break
        
        # Final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Import completed in {duration}")
        print(f"📊 Final Statistics:")
        for key, value in self.stats.items():
            print(f"   {key}: {value}")
        
        estimated_remaining = self.max_requests_per_day - self.requests_made
        print(f"   estimated_remaining_requests: {estimated_remaining}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="API-Football Data Importer")
    parser.add_argument("--max-leagues", type=int, default=100, 
                       help="Maximum number of leagues to process")
    parser.add_argument("--max-teams", type=int, default=None,
                       help="Maximum teams per league (for testing)")
    parser.add_argument("--season", type=int, default=None,
                       help="Season year (default: current year)")
    parser.add_argument("--delay", type=float, default=0.5,
                       help="Delay between requests in seconds")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be imported without actually importing")
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable is required!")
        sys.exit(1)
    
    # Initialize Flask app context for database operations
    from app import app
    with app.app_context():
        db.create_all()
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No data will be imported")
        
        # Initialize importer
        importer = APIFootballImporter(
            api_key=api_key,
            current_season=args.season,
            request_delay=args.delay
        )
        
        if args.dry_run:
            # Just show what leagues would be processed
            leagues = importer.get_top_leagues(args.max_leagues)
            print(f"\n📋 Would process {len(leagues)} leagues:")
            for i, league in enumerate(leagues, 1):
                print(f"  {i:2d}. {league['name']} ({league['country']}) - {league['type']}")
        else:
            # Run actual import
            importer.run_import(
                max_leagues=args.max_leagues,
                max_teams_per_league=args.max_teams
            )


if __name__ == "__main__":
    main() 