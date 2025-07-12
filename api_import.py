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
from top_250_teams import get_team_mapper, get_top_250_team_names


class APIFootballImporter:
    """Comprehensive API-Football data importer with optimization and caching"""
    
    def __init__(self, api_key: str, current_season: int = None, request_delay: float = 0.5, max_requests_per_day: int = 7500):
        self.api_key = api_key
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.current_season = current_season or datetime.now().year
        self.request_delay = request_delay
        
        # Request tracking with daily reset
        self.requests_made = 0
        self.max_requests_per_day = max_requests_per_day
        self.request_date = datetime.now().date()
        self.request_log_file = f"api_requests_{self.request_date.strftime('%Y%m%d')}.log"
        
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
        self._load_request_count()

    
    def fetch_all_teams(self) -> list:
        """
        Fetch all teams across all leagues for the current season.
        Returns a list of dicts: {"id": ..., "name": ..., "popularity": ...}
        Popularity is estimated by league priority and team name length (as a fallback).
        """
        print("🔄 Fetching all teams for popularity ranking...")
        
        # Only fetch top 20 most important leagues to conserve API requests
        leagues = self.get_top_leagues(20)
        teams = []
        league_priority = {l['id']: i for i, l in enumerate(leagues)}
        
        for league in leagues:
            # Check if we have enough requests remaining
            remaining = self.max_requests_per_day - self.requests_made
            if remaining <= 10:  # Keep some buffer
                print(f"⚠️  Stopping league fetch - only {remaining} requests remaining")
                break
                
            league_teams = self.get_league_teams(league['id'], self.current_season)
            for team in league_teams:
                # Estimate popularity: higher for teams in higher-priority leagues
                popularity = 1000 - league_priority[league['id']] * 10
                # Optionally, you can add more logic (e.g., based on team name, country, etc.)
                teams.append({
                    "id": team["id"],
                    "name": team["name"],
                    "popularity": popularity
                })
        
        print(f"✅ Fetched {len(teams)} teams with popularity scores")
        return teams
    
    def fetch_top_teams_efficient(self, target_count: int = 100) -> list:
        """
        Efficiently fetch top teams by focusing on major leagues first.
        This method optimizes for API request conservation.
        """
        print(f"🔄 Efficiently fetching top {target_count} teams...")
        
        # Major leagues in order of priority
        major_leagues = [
            {"id": 39, "name": "Premier League", "country": "England", "priority": 1},
            {"id": 140, "name": "La Liga", "country": "Spain", "priority": 2},
            {"id": 78, "name": "Bundesliga", "country": "Germany", "priority": 3},
            {"id": 135, "name": "Serie A", "country": "Italy", "priority": 4},
            {"id": 61, "name": "Ligue 1", "country": "France", "priority": 5},
            {"id": 2, "name": "UEFA Champions League", "country": "World", "priority": 6},
            {"id": 3, "name": "UEFA Europa League", "country": "World", "priority": 7},
            {"id": 94, "name": "Primeira Liga", "country": "Portugal", "priority": 8},
            {"id": 88, "name": "Eredivisie", "country": "Netherlands", "priority": 9},
            {"id": 203, "name": "Turkish Super Lig", "country": "Turkey", "priority": 10},
        ]
        
        teams = []
        
        for league in major_leagues:
            # Check if we have enough requests remaining
            remaining = self.max_requests_per_day - self.requests_made
            if remaining <= 5:  # Keep buffer
                print(f"⚠️  Stopping team fetch - only {remaining} requests remaining")
                break
                
            if len(teams) >= target_count:
                break
                
            print(f"🔄 Fetching teams from {league['name']}...")
            league_teams = self.get_league_teams(league['id'], self.current_season)
            
            for team in league_teams:
                # Higher priority leagues get higher popularity scores
                popularity = 1000 - (league['priority'] * 50)
                teams.append({
                    "id": team["id"],
                    "name": team["name"],
                    "popularity": popularity,
                    "league": league['name']
                })
        
        # Sort by popularity and return top teams
        teams.sort(key=lambda x: x['popularity'], reverse=True)
        top_teams = teams[:target_count]
        
        print(f"✅ Fetched {len(top_teams)} top teams efficiently")
        return top_teams


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
    
    def _load_request_count(self):
        """Load today's request count from log file"""
        try:
            if os.path.exists(self.request_log_file):
                with open(self.request_log_file, 'r') as f:
                    lines = f.readlines()
                    self.requests_made = len(lines)
                    print(f"📊 Loaded {self.requests_made} requests from today's log")
            else:
                print("📊 Starting fresh request count for today")
        except Exception as e:
            print(f"⚠️  Could not load request count: {e}")
    
    def _log_request(self, endpoint: str, status_code: int):
        """Log API request to file"""
        try:
            timestamp = datetime.now().isoformat()
            log_entry = f"{timestamp},{endpoint},{status_code}\n"
            with open(self.request_log_file, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"⚠️  Could not log request: {e}")
    
    def _check_daily_reset(self):
        """Check if we need to reset daily counter"""
        current_date = datetime.now().date()
        if current_date != self.request_date:
            print(f"🔄 New day detected, resetting request counter")
            self.request_date = current_date
            self.requests_made = 0
            self.request_log_file = f"api_requests_{self.request_date.strftime('%Y%m%d')}.log"
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make throttled API request with error handling"""
        self._check_daily_reset()
        
        if self.requests_made >= self.max_requests_per_day:
            print(f"❌ Daily request limit ({self.max_requests_per_day}) reached!")
            print(f"📊 Requests made today: {self.requests_made}")
            return None
        
        # Calculate remaining requests and warn if getting low
        remaining = self.max_requests_per_day - self.requests_made
        if remaining <= 100:
            print(f"⚠️  Only {remaining} requests remaining today!")
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            time.sleep(self.request_delay)  # Throttle requests
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.requests_made += 1
            self.stats["requests_made"] = self.requests_made
            
            # Log the request
            self._log_request(endpoint, response.status_code)
            
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
    
    def run_import(self, max_leagues: int = 100, max_teams_per_league: int = None, team_ids: list = None):
        """
        Main import process.
        If team_ids is provided, only import/update those teams.
        """
        print(f"🚀 Starting API-Football import")
        print(f"⏱️  Request delay: {self.request_delay}s")
        print(f"📈 Request limit: {self.max_requests_per_day}/day")
        print(f"📊 Current requests used: {self.requests_made}")
        start_time = datetime.now()

        if team_ids is not None:
            # Efficiently import/update the specified teams
            print(f"🔄 Importing/updating {len(team_ids)} specific teams...")
            self.import_specific_teams(team_ids)
            print("✅ Selected teams import/update complete.")
        else:
            # Default: import all teams in top leagues
            leagues = self.get_top_leagues(max_leagues)
            for i, league in enumerate(leagues, 1):
                if self.requests_made >= self.max_requests_per_day:
                    print(f"❌ Stopping: Daily request limit reached")
                    break
                print(f"\n📍 Progress: {i}/{len(leagues)} leagues")
                self.import_league_data(league, max_teams_per_league)
                remaining_requests = self.max_requests_per_day - self.requests_made
                print(f"📊 Requests remaining: {remaining_requests}")
                if remaining_requests < 50:
                    print(f"⚠️  Approaching request limit, stopping early")
                    break

        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n🎉 Import completed in {duration}")
        print(f"📊 Final Statistics:")
        for key, value in self.stats.items():
            print(f"   {key}: {value}")
        estimated_remaining = self.max_requests_per_day - self.requests_made
        print(f"   estimated_remaining_requests: {estimated_remaining}")
    
    def import_specific_teams(self, team_ids: list):
        """
        Import specific teams efficiently by batching league requests.
        This method reduces API calls by getting all teams per league at once.
        """
        print(f"🔄 Efficiently importing {len(team_ids)} specific teams...")
        
        # Get major leagues first (most likely to contain the teams we want)
        major_leagues = [
            {"id": 39, "name": "Premier League"},
            {"id": 140, "name": "La Liga"},
            {"id": 78, "name": "Bundesliga"},
            {"id": 135, "name": "Serie A"},
            {"id": 61, "name": "Ligue 1"},
            {"id": 2, "name": "UEFA Champions League"},
            {"id": 3, "name": "UEFA Europa League"},
            {"id": 94, "name": "Primeira Liga"},
            {"id": 88, "name": "Eredivisie"},
        ]
        
        teams_found = set()
        teams_to_find = set(team_ids)
        
        for league in major_leagues:
            if not teams_to_find:  # All teams found
                break
                
            remaining = self.max_requests_per_day - self.requests_made
            if remaining <= 10:  # Keep buffer
                print(f"⚠️  Stopping - only {remaining} requests remaining")
                break
                
            print(f"🔄 Checking {league['name']} for target teams...")
            league_teams = self.get_league_teams(league['id'], self.current_season)
            
            for team in league_teams:
                if team["id"] in teams_to_find:
                    print(f"✅ Found team: {team['name']}")
                    teams_found.add(team["id"])
                    teams_to_find.remove(team["id"])
                    
                    # Import this team
                    self.create_or_update_team(team, league["name"])
                    
                    # Get fixtures for this team with request limit check
                    if self.requests_made < self.max_requests_per_day - 5:
                        fixtures = self.get_team_fixtures(team["id"], self.current_season, league["id"])
                        for fixture_data in fixtures:
                            self.process_fixture(fixture_data, league["name"])
                    else:
                        print(f"⚠️  Skipping fixtures for {team['name']} - request limit approaching")
            
            # Commit after each league
            self.commit_batched_data()
        
        print(f"✅ Found and imported {len(teams_found)} out of {len(team_ids)} teams")
        if teams_to_find:
            print(f"⚠️  Could not find {len(teams_to_find)} teams: {list(teams_to_find)[:5]}...")  # Show first 5
    
    def find_team_by_name(self, team_name: str) -> Optional[dict]:
        """
        Find a team by name using fuzzy matching across all leagues.
        This method will search through major leagues to find the team.
        """
        print(f"🔍 Searching for team: {team_name}")
        
        # Major leagues to search through
        search_leagues = [
            39,   # Premier League
            140,  # La Liga
            78,   # Bundesliga
            135,  # Serie A
            61,   # Ligue 1
            94,   # Primeira Liga
            88,   # Eredivisie
            203,  # Turkish Super Lig
            71,   # Brasileiro Serie A
            253,  # MLS
            2,    # UEFA Champions League
            3,    # UEFA Europa League
            4,    # UEFA Europa Conference League
            128,  # Argentine Primera División
            13,   # CONMEBOL Copa Libertadores
            81,   # DFB Pokal
            137,  # Coppa Italia
            143,  # Copa del Rey
            144,  # Copa da Liga
            239,  # Egyptian Premier League
            274,  # Saudi Pro League
            307,  # UAE Pro League
            218,  # CAF Champions League
            219,  # CAF Confederation Cup
            292,  # J1 League
            299,  # K League 1
            169,  # Greek Super League
            583,  # Polish Ekstraklasa
            345,  # Russian Premier League
            564,  # Ukrainian Premier League
        ]
        
        for league_id in search_leagues:
            # Check if we have enough requests
            if self.requests_made >= self.max_requests_per_day - 10:
                print(f"⚠️  Stopping search - approaching request limit")
                break
            
            try:
                teams = self.get_league_teams(league_id, self.current_season)
                
                for team in teams:
                    team_api_name = team.get('name', '').lower()
                    search_name = team_name.lower()
                    
                    # Direct match
                    if search_name == team_api_name:
                        print(f"✅ Found exact match: {team['name']} (ID: {team['id']})")
                        return team
                    
                    # Fuzzy matching for common variations
                    if self._is_team_name_match(search_name, team_api_name):
                        print(f"✅ Found fuzzy match: {team['name']} (ID: {team['id']}) for search: {team_name}")
                        return team
                        
            except Exception as e:
                print(f"❌ Error searching league {league_id}: {e}")
                continue
        
        print(f"❌ Could not find team: {team_name}")
        return None
    
    def _is_team_name_match(self, search_name: str, api_name: str) -> bool:
        """Check if team names match using fuzzy logic"""
        # Remove common prefixes/suffixes
        search_clean = self._clean_team_name(search_name)
        api_clean = self._clean_team_name(api_name)
        
        # Direct match after cleaning
        if search_clean == api_clean:
            return True
        
        # Check if one contains the other (for cases like "AC Milan" vs "Milan")
        if search_clean in api_clean or api_clean in search_clean:
            return True
        
        # Check for common abbreviations
        abbreviations = {
            'fc': 'football club',
            'sc': 'sporting club',
            'ac': 'associazione calcio',
            'cf': 'club de fútbol',
            'united': 'utd',
            'athletic': 'ath',
            'real': 'r',
            'saint': 'st',
            'saint-étienne': 'st-étienne',
        }
        
        for abbr, full in abbreviations.items():
            search_expanded = search_clean.replace(abbr, full)
            api_expanded = api_clean.replace(abbr, full)
            
            if search_expanded == api_expanded:
                return True
        
        return False
    
    def _clean_team_name(self, name: str) -> str:
        """Clean team name for matching"""
        # Remove common words and normalize
        name = name.lower()
        
        # Remove common prefixes/suffixes
        removals = ['fc', 'sc', 'ac', 'cf', 'club', 'de', 'da', 'do', 'the', 'af', 'if', 'bk', 'fk', 'sk']
        words = name.split()
        words = [word for word in words if word not in removals]
        
        return ' '.join(words).strip()
    
    def map_top_250_teams(self) -> None:
        """
        Find and map the top 250 teams to their API IDs.
        This is a one-time operation that should be run when API limit resets.
        """
        print("🔍 Mapping top 250 teams to API IDs...")
        
        team_mapper = get_team_mapper()
        team_names = get_top_250_team_names()
        unmapped_teams = team_mapper.get_unmapped_teams()
        
        print(f"📊 Teams to map: {len(unmapped_teams)}")
        
        if not unmapped_teams:
            print("✅ All teams already mapped!")
            return
        
        mapped_count = 0
        
        for team_name in unmapped_teams:
            if self.requests_made >= self.max_requests_per_day - 20:  # Keep buffer
                print(f"⚠️  Stopping mapping - approaching request limit")
                break
            
            team_info = self.find_team_by_name(team_name)
            
            if team_info:
                team_mapper.add_team_mapping(
                    name=team_name,
                    api_id=team_info['id'],
                    league=team_info.get('league', 'Unknown'),
                    country=team_info.get('country', 'Unknown')
                )
                mapped_count += 1
                
                # Save progress periodically
                if mapped_count % 10 == 0:
                    team_mapper.save_mapping()
                    print(f"💾 Saved progress: {mapped_count} teams mapped")
        
        # Final save
        team_mapper.save_mapping()
        
        progress = team_mapper.get_mapping_progress()
        print(f"✅ Mapping complete! {progress['mapped']}/{progress['total']} teams mapped ({progress['progress_percent']}%)")
    
    def import_top_250_teams_historical(self, start_year: int = 2000) -> None:
        """
        Import historical data for the top 250 teams from the specified start year.
        """
        print(f"🏆 Importing historical data for top 250 teams from {start_year}...")
        
        team_mapper = get_team_mapper()
        team_ids = team_mapper.get_mapped_team_ids()
        
        if not team_ids:
            print("❌ No teams mapped! Run map_top_250_teams() first.")
            return
        
        print(f"📊 Importing data for {len(team_ids)} teams")
        
        # Import data for each season from start_year to current year
        current_year = datetime.now().year
        seasons = list(range(start_year, current_year + 1))
        
        for season in seasons:
            if self.requests_made >= self.max_requests_per_day - 50:  # Keep buffer
                print(f"⚠️  Stopping import - approaching request limit")
                break
            
            print(f"\n📅 Importing season {season}...")
            
            # Track teams processed this season
            teams_processed = 0
            
            for team_id in team_ids:
                if self.requests_made >= self.max_requests_per_day - 10:
                    print(f"⚠️  Stopping season {season} - approaching request limit")
                    break
                
                # Get fixtures for this team in this season
                fixtures = self.get_team_fixtures(team_id, season)
                
                # Process fixtures
                for fixture_data in fixtures:
                    self.process_fixture(fixture_data, f"Season {season}")
                
                teams_processed += 1
                
                # Commit periodically to avoid memory issues
                if teams_processed % 20 == 0:
                    self.commit_batched_data()
                    print(f"  💾 Processed {teams_processed} teams in season {season}")
            
            # Commit at end of season
            self.commit_batched_data()
            print(f"✅ Season {season} complete - processed {teams_processed} teams")
        
        print(f"🎉 Historical import complete!")
    
    def update_top_250_fixtures(self) -> None:
        """
        Update fixtures for the next week for all top 250 teams.
        This should be run daily.
        """
        print("📅 Updating fixtures for top 250 teams (next week)...")
        
        team_mapper = get_team_mapper()
        team_ids = team_mapper.get_mapped_team_ids()
        
        if not team_ids:
            print("❌ No teams mapped!")
            return
        
        # Get fixtures for next 7 days
        from_date = datetime.now()
        to_date = from_date + timedelta(days=7)
        
        fixtures_updated = 0
        
        for team_id in team_ids:
            if self.requests_made >= self.max_requests_per_day - 10:
                print(f"⚠️  Stopping fixture update - approaching request limit")
                break
            
            # Get upcoming fixtures for this team
            fixtures = self.get_team_fixtures_in_range(team_id, from_date, to_date)
            
            for fixture_data in fixtures:
                self.process_fixture(fixture_data, "Upcoming")
                fixtures_updated += 1
            
            # Commit periodically
            if fixtures_updated % 50 == 0:
                self.commit_batched_data()
        
        # Final commit
        self.commit_batched_data()
        print(f"✅ Updated {fixtures_updated} fixtures for upcoming week")
    
    def get_team_fixtures_in_range(self, team_id: int, from_date: datetime, to_date: datetime) -> List[dict]:
        """Get fixtures for a team within a specific date range"""
        params = {
            "team": str(team_id),
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
            
            fixtures.append({
                "api_fixture_id": fixture.get("id"),
                "date": fixture.get("date"),
                "status": fixture.get("status", {}).get("short"),
                "venue": fixture.get("venue", {}).get("name"),
                "home_team": teams.get("home", {}),
                "away_team": teams.get("away", {}),
                "league": league,
                "goals": goals,
                "referee": fixture.get("referee")
            })
        
        return fixtures
    
    def update_top_250_recent_matches(self) -> None:
        """
        Update recent matches for top 250 teams.
        This should be run every 5 minutes for live updates.
        """
        print("⚡ Updating recent matches for top 250 teams...")
        
        team_mapper = get_team_mapper()
        team_ids = team_mapper.get_mapped_team_ids()
        
        if not team_ids:
            print("❌ No teams mapped!")
            return
        
        # Get matches from last 2 days (for live score updates)
        from_date = datetime.now() - timedelta(days=2)
        to_date = datetime.now()
        
        matches_updated = 0
        
        # Process a subset of teams each run to conserve API requests
        # With 5-minute intervals, we can process ~50 teams per run
        import random
        selected_teams = random.sample(team_ids, min(50, len(team_ids)))
        
        for team_id in selected_teams:
            if self.requests_made >= self.max_requests_per_day - 5:
                print(f"⚠️  Stopping match update - approaching request limit")
                break
            
            # Get recent fixtures
            fixtures = self.get_team_fixtures_in_range(team_id, from_date, to_date)
            
            for fixture_data in fixtures:
                # Only process if match is finished or live
                status = fixture_data.get("status", "NS")
                if status in ["FT", "1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT"]:
                    self.process_fixture(fixture_data, "Recent")
                    matches_updated += 1
        
        # Commit updates
        self.commit_batched_data()
        print(f"✅ Updated {matches_updated} recent matches")

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