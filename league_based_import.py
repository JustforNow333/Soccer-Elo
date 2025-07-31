#!/usr/bin/env python3
"""
League-Based Team Import System
Uses API Football documentation-compliant approach: GET /teams?league={id}&season={year}
"""

import os
import time
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from top_250_teams import TOP_250_TEAMS, get_team_mapper

# Major football leagues and competitions
MAJOR_LEAGUES = {
    # European Top 5 Leagues
    39: "Premier League",           # England
    140: "La Liga",                # Spain  
    135: "Serie A",                # Italy
    78: "Bundesliga",              # Germany
    61: "Ligue 1",                 # France
    
    # European Competitions
    2: "Champions League",
    3: "Europa League",
    848: "Conference League",
    
    # Other Major European Leagues
    94: "Primeira Liga",           # Portugal
    88: "Eredivisie",              # Netherlands
    203: "Super Lig",              # Turkey
    235: "Russian Premier League",
    218: "Belgian Pro League",
    119: "Superliga",              # Denmark
    103: "Eliteserien",            # Norway
    113: "Allsvenskan",            # Sweden
    
    # South American
    71: "Serie A",                 # Brazil
    128: "Primera División",       # Argentina
    11: "CONMEBOL Libertadores",
    13: "CONMEBOL Sudamericana",
    
    # North American
    253: "Major League Soccer",    # MLS USA/Canada
    262: "Liga MX",               # Mexico
    
    # Middle East & Asia
    307: "Saudi Pro League",       # Saudi Arabia
    301: "UAE Pro League",
    188: "J1 League",              # Japan
    292: "K League 1",             # South Korea
    169: "Chinese Super League",
    
    # African
    233: "Egyptian Premier League",
    288: "Premier Soccer League",  # South Africa
    
    # Additional European
    179: "Jupiler Pro League",     # Belgium
    203: "Super Lig",              # Turkey
    218: "First Division A",       # Belgium
    
    # International
    1: "World Cup",
    4: "European Championship",
    9: "Copa America",
    17: "African Cup of Nations",
}

class LeagueBasedImporter:
    """Import teams using league-based discovery as per API Football documentation"""
    
    def __init__(self, api_key: str, max_requests_per_day: int = 7500):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.base_url = "https://v3.football.api-sports.io"
        self.max_requests_per_day = max_requests_per_day
        self.requests_made = 0
        self.discovered_teams = {}
        self.team_mapper = get_team_mapper()
        
    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """Make API request with rate limiting and error handling"""
        if self.requests_made >= self.max_requests_per_day - 10:
            print(f"⚠️  Approaching request limit ({self.requests_made}/{self.max_requests_per_day})")
            return None
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            self.requests_made += 1
            
            # Check rate limit headers
            remaining = response.headers.get('x-ratelimit-requests-remaining')
            if remaining:
                print(f"📊 Requests remaining today: {remaining}")
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"⏰ Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)  # Retry once
                
            response.raise_for_status()
            data = response.json()
            
            if data.get('errors'):
                print(f"❌ API Error: {data['errors']}")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
        finally:
            time.sleep(1.2)  # Conservative rate limiting
    
    def get_teams_in_league(self, league_id: int, season: int) -> List[Dict]:
        """Get all teams in a specific league and season"""
        print(f"🔍 Getting teams for {MAJOR_LEAGUES.get(league_id, f'League {league_id}')} {season}...")
        
        params = {
            "league": str(league_id),
            "season": str(season)
        }
        
        data = self._make_request("teams", params)
        if not data:
            return []
            
        teams = data.get("response", [])
        print(f"   📊 Found {len(teams)} teams in league")
        return teams
    
    def fuzzy_match_team(self, api_team_name: str, threshold: float = 0.6) -> Optional[str]:
        """Match API team name against TOP_250_TEAMS using fuzzy matching"""
        api_name_clean = self._normalize_team_name(api_team_name)
        
        best_match = None
        best_score = 0
        
        for top_250_name in TOP_250_TEAMS:
            top_250_clean = self._normalize_team_name(top_250_name)
            
            # Calculate similarity
            similarity = SequenceMatcher(None, api_name_clean, top_250_clean).ratio()
            
            # Check for partial matches (important words)
            words_api = set(api_name_clean.split())
            words_250 = set(top_250_clean.split())
            
            # Boost score if key words match
            if words_api.intersection(words_250):
                word_overlap = len(words_api.intersection(words_250)) / max(len(words_api), len(words_250))
                similarity = max(similarity, word_overlap * 0.9)
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = top_250_name
        
        if best_match:
            print(f"   ✅ Matched: {api_team_name} → {best_match} (score: {best_score:.2f})")
            return best_match
        
        return None
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching"""
        # Remove common prefixes/suffixes
        name = name.lower()
        prefixes = ["fc ", "ac ", "as ", "sc ", "cf ", "cd ", "club ", "real ", "atletico "]
        suffixes = [" fc", " ac", " as", " sc", " cf", " cd", " united", " city"]
        
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
                
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        
        # Remove special characters
        name = "".join(c for c in name if c.isalnum() or c.isspace())
        return name.strip()
    
    def discover_teams_by_leagues(self, seasons: List[int] = None) -> Dict[str, Dict]:
        """Main method: discover teams by querying leagues"""
        if seasons is None:
            current_year = datetime.now().year
            seasons = [current_year, current_year - 1]  # Current and previous season
        
        print(f"🚀 Starting league-based team discovery for seasons: {seasons}")
        print(f"📊 Checking {len(MAJOR_LEAGUES)} major leagues")
        print("=" * 60)
        
        discovered_teams = {}
        processed_leagues = 0
        
        for league_id, league_name in MAJOR_LEAGUES.items():
            if self.requests_made >= self.max_requests_per_day - 50:
                print(f"⚠️  Approaching request limit, stopping discovery")
                break
                
            print(f"\n🏆 Processing {league_name} (ID: {league_id})")
            
            for season in seasons:
                teams_data = self.get_teams_in_league(league_id, season)
                
                for team_data in teams_data:
                    team_info = team_data.get("team", {})
                    venue_info = team_data.get("venue", {})
                    
                    api_team_name = team_info.get("name", "")
                    team_id = team_info.get("id")
                    
                    if not api_team_name or not team_id:
                        continue
                    
                    # Try to match against TOP_250_TEAMS
                    matched_name = self.fuzzy_match_team(api_team_name)
                    
                    if matched_name:
                        # Store the best info we have for this team
                        if matched_name not in discovered_teams:
                            discovered_teams[matched_name] = {
                                "api_id": team_id,
                                "api_name": api_team_name,
                                "country": team_info.get("country", "Unknown"),
                                "league": league_name,
                                "season": season,
                                "venue_name": venue_info.get("name"),
                                "venue_city": venue_info.get("city"),
                                "venue_capacity": venue_info.get("capacity"),
                                "founded": team_info.get("founded"),
                                "match_score": 1.0  # Perfect league-based match
                            }
                        else:
                            # Update with more recent season info if needed
                            if season > discovered_teams[matched_name]["season"]:
                                discovered_teams[matched_name].update({
                                    "league": league_name,
                                    "season": season
                                })
            
            processed_leagues += 1
            if processed_leagues % 5 == 0:
                print(f"📊 Progress: {processed_leagues}/{len(MAJOR_LEAGUES)} leagues processed")
                print(f"🎯 Teams discovered so far: {len(discovered_teams)}")
        
        self.discovered_teams = discovered_teams
        
        print("\n" + "=" * 60)
        print(f"🎉 Discovery Complete!")
        print(f"📊 Leagues processed: {processed_leagues}")
        print(f"🎯 Teams discovered: {len(discovered_teams)}/{len(TOP_250_TEAMS)}")
        print(f"📈 Success rate: {len(discovered_teams)/len(TOP_250_TEAMS)*100:.1f}%")
        print(f"🔢 API requests used: {self.requests_made}")
        
        return discovered_teams
    
    def apply_discovered_teams(self) -> int:
        """Apply discovered teams to the team mapper"""
        if not self.discovered_teams:
            print("❌ No teams discovered yet. Run discover_teams_by_leagues() first.")
            return 0
        
        print(f"\n🔧 Applying {len(self.discovered_teams)} discovered teams to mapper...")
        applied_count = 0
        
        for team_name, team_info in self.discovered_teams.items():
            # Check if already mapped
            existing_id = self.team_mapper.get_team_id(team_name)
            
            if not existing_id:
                self.team_mapper.add_team_mapping(
                    name=team_name,
                    api_id=team_info["api_id"],
                    league=team_info["league"],
                    country=team_info["country"]
                )
                applied_count += 1
                print(f"✅ Added: {team_name} → {team_info['api_name']} (ID: {team_info['api_id']})")
            else:
                print(f"⚠️  Skipped: {team_name} already mapped (ID: {existing_id})")
        
        if applied_count > 0:
            self.team_mapper.save_mapping()
            print(f"💾 Saved {applied_count} new team mappings")
            
        # Show final progress
        progress = self.team_mapper.get_mapping_progress()
        print(f"📊 Final mapping: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
        
        return applied_count
    
    def save_discovery_results(self, filename: str = "league_discovery_results.json"):
        """Save discovery results to JSON file"""
        if not self.discovered_teams:
            print("❌ No discovery results to save")
            return
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.discovered_teams, f, indent=2, ensure_ascii=False)
            print(f"💾 Discovery results saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
    
    def get_team_leagues(self, team_id: int, season: int) -> List[Dict]:
        """Get leagues that a team participates in for a given season"""
        params = {
            "team": str(team_id),
            "season": str(season)
        }
        
        data = self._make_request("leagues", params)
        if not data:
            return []
            
        return data.get("response", [])
    
    def get_team_fixtures(self, team_id: int, season: int, status: str = "FT") -> List[Dict]:
        """Get fixtures for a team in a specific season"""
        params = {
            "team": str(team_id),
            "season": str(season),
            "status": status
        }
        
        data = self._make_request("fixtures", params)
        if not data:
            return []
            
        return data.get("response", [])
    
    def import_team_matches(self, seasons: List[int] = None) -> int:
        """Import match history for all discovered teams"""
        if not self.discovered_teams:
            print("❌ No teams discovered yet. Run discover_teams_by_leagues() first.")
            return 0
        
        if seasons is None:
            # Import comprehensive historical data
            current_year = datetime.now().year
            seasons = []
            # Recent years (full coverage)
            seasons.extend(range(2019, current_year + 1))
            # Modern era (selective coverage)
            seasons.extend([2015, 2016, 2017, 2018])
            # Historical (selective coverage)
            seasons.extend([2010, 2012, 2014])
            seasons = sorted(set(seasons))
        
        print(f"\n🏆 Importing match history for {len(self.discovered_teams)} teams")
        print(f"📅 Seasons: {seasons}")
        print(f"📊 Estimated requests: {len(self.discovered_teams) * len(seasons)}")
        print("=" * 60)
        
        from db import db, Team, Match
        
        total_matches_imported = 0
        teams_processed = 0
        
        for team_name, team_info in self.discovered_teams.items():
            if self.requests_made >= self.max_requests_per_day - 50:
                print(f"⚠️  Approaching request limit, stopping match import")
                break
            
            team_id = team_info["api_id"]
            api_name = team_info["api_name"]
            
            print(f"\n⚽ Processing {api_name} (ID: {team_id})")
            
            team_matches = 0
            for season in seasons:
                if self.requests_made >= self.max_requests_per_day - 20:
                    print(f"   ⚠️  Stopping at season {season} - approaching request limit")
                    break
                
                print(f"   📅 Season {season}...", end=" ")
                fixtures = self.get_team_fixtures(team_id, season, "FT")
                
                season_matches = 0
                for fixture_data in fixtures:
                    match_created = self._process_fixture_to_match(fixture_data, team_name)
                    if match_created:
                        season_matches += 1
                        total_matches_imported += 1
                
                print(f"{season_matches} matches")
                team_matches += season_matches
            
            teams_processed += 1
            print(f"   ✅ Total for {api_name}: {team_matches} matches")
            
            # Commit periodically
            if teams_processed % 10 == 0:
                try:
                    db.session.commit()
                    print(f"💾 Committed batch ({teams_processed} teams processed)")
                except Exception as e:
                    print(f"❌ Commit error: {e}")
                    db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            print(f"💾 Final commit completed")
        except Exception as e:
            print(f"❌ Final commit error: {e}")
            db.session.rollback()
        
        print("\n" + "=" * 60)
        print(f"🎉 Match Import Complete!")
        print(f"⚽ Teams processed: {teams_processed}")
        print(f"📊 Matches imported: {total_matches_imported}")
        print(f"🔢 API requests used: {self.requests_made}")
        
        return total_matches_imported
    
    def _process_fixture_to_match(self, fixture_data: Dict, team_name: str) -> bool:
        """Process a single fixture and create Match record"""
        try:
            from db import db, Team, Match
            from datetime import datetime
            
            fixture = fixture_data.get("fixture", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            
            # Extract data
            fixture_date = fixture.get("date")
            if not fixture_date:
                return False
                
            # Parse date
            match_date = datetime.fromisoformat(fixture_date.replace('Z', '+00:00')).date()
            
            # Get teams
            home_team_data = teams.get("home", {})
            away_team_data = teams.get("away", {})
            
            home_team_id = home_team_data.get("id")
            away_team_id = away_team_data.get("id")
            
            # Get scores
            home_score = goals.get("home")
            away_score = goals.get("away")
            
            if home_score is None or away_score is None:
                return False
            
            # Find teams in our database
            home_team = Team.query.filter_by(api_football_id=home_team_id).first()
            away_team = Team.query.filter_by(api_football_id=away_team_id).first()
            
            # Create teams if they don't exist (from discovered teams)
            if not home_team and home_team_id in [t["api_id"] for t in self.discovered_teams.values()]:
                home_team_info = next((t for t in self.discovered_teams.values() if t["api_id"] == home_team_id), None)
                if home_team_info:
                    home_team = Team(
                        name=self._normalize_team_name(home_team_info["api_name"]),
                        league=home_team_info["league"],
                        api_football_id=home_team_id
                    )
                    db.session.add(home_team)
                    db.session.flush()  # Get ID
            
            if not away_team and away_team_id in [t["api_id"] for t in self.discovered_teams.values()]:
                away_team_info = next((t for t in self.discovered_teams.values() if t["api_id"] == away_team_id), None)
                if away_team_info:
                    away_team = Team(
                        name=self._normalize_team_name(away_team_info["api_name"]),
                        league=away_team_info["league"],
                        api_football_id=away_team_id
                    )
                    db.session.add(away_team)
                    db.session.flush()  # Get ID
            
            if not home_team or not away_team:
                return False
            
            # Check if match already exists
            existing_match = Match.query.filter_by(
                date=match_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id
            ).first()
            
            if existing_match:
                return False  # Already exists
            
            # Create match record
            match = Match(
                date=match_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=int(home_score),
                away_score=int(away_score)
            )
            
            db.session.add(match)
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing fixture: {e}")
            return False

def main():
    """Test the league-based import system"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        return
    
    print("🚀 League-Based Team Import System")
    print("=" * 50)
    
    importer = LeagueBasedImporter(api_key)
    
    try:
        # Phase 1: Discover teams from major leagues
        print("📍 PHASE 1: Team Discovery")
        discovered = importer.discover_teams_by_leagues([2024, 2023])
        
        # Save discovery results
        importer.save_discovery_results()
        
        # Apply to team mapper
        applied = importer.apply_discovered_teams()
        
        print(f"\n📊 Phase 1 Results:")
        print(f"   Teams discovered: {len(discovered)}")
        print(f"   Teams applied: {applied}")
        print(f"   API requests used: {importer.requests_made}")
        
        # Phase 2: Import match history (if we have budget)
        if importer.requests_made < importer.max_requests_per_day - 1000:
            print(f"\n📍 PHASE 2: Match History Import")
            matches_imported = importer.import_team_matches()
            
            print(f"\n📊 Phase 2 Results:")
            print(f"   Matches imported: {matches_imported}")
        else:
            print(f"\n⚠️  Skipping match import - insufficient API budget")
            print(f"   Requests used: {importer.requests_made}/{importer.max_requests_per_day}")
            print(f"   Run match import separately when API resets")
        
        print(f"\n🎉 Import Complete!")
        print(f"🔢 Total API requests used: {importer.requests_made}")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Import interrupted by user")
        print(f"💾 Saving partial results...")
        importer.save_discovery_results("partial_discovery_results.json")
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        importer.save_discovery_results("error_discovery_results.json")

if __name__ == "__main__":
    main()