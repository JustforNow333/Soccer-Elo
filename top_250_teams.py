#!/usr/bin/env python3
"""
Top 250 Teams Configuration
Contains the hardcoded list of 250 teams and utilities for mapping them to API-Football IDs
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class TeamInfo:
    name: str
    api_id: Optional[int] = None
    league: Optional[str] = None
    country: Optional[str] = None

# The exact 250 teams from your list
TOP_250_TEAMS = [
    "Real Madrid",
    "FC Barcelona", 
    "Manchester United",
    "Paris Saint-Germain",
    "Manchester City",
    "Juventus",
    "Liverpool",
    "Chelsea",
    "Bayern Munich",
    "Arsenal",
    "Tottenham Hotspur",
    "Atlético Madrid",
    "AC Milan",
    "Inter Milan",
    "Flamengo",
    "Al-Nassr",
    "Borussia Dortmund",
    "Al-Ahly",
    "Galatasaray",
    "AS Roma",
    "Corinthians",
    "Fenerbahçe",
    "Inter Miami",
    "Al-Hilal",
    "Persib Bandung",
    "Club América",
    "Boca Juniors",
    "River Plate",
    "Ajax",
    "Leicester City",
    "Santos FC",
    "Sevilla FC",
    "SE Palmeiras",
    "São Paulo FC",
    "Real Betis",
    "Beşiktaş",
    "Olympique Marseille",
    "AS Monaco",
    "Real Sociedad",
    "Chivas Guadalajara",
    "SSC Napoli",
    "West Ham United",
    "Aston Villa",
    "Newcastle United",
    "Zamalek SC",
    "Valencia CF",
    "Bayer Leverkusen",
    "Cádiz CF",
    "Al-Ittihad Club",
    "Athletic Club",
    "Celta Vigo",
    "Everton FC",
    "CR Vasco da Gama",
    "Raja Casablanca",
    "Persija Jakarta",
    "Al-Ahli",
    "SL Benfica",
    "FC Porto",
    "Grêmio",
    "Simba SC",
    "Sporting CP",
    "Kaizer Chiefs",
    "Cruz Azul",
    "Pumas UNAM",
    "Orlando Pirates",
    "Johor Darul Ta'zim",
    "Independiente",
    "Racing Club",
    "Atlético Nacional",
    "Millonarios",
    "Persepolis",
    "Esteghlal",
    "Tigres UANL",
    "Monterrey",
    "Celtic",
    "Rangers",
    "Mamelodi Sundowns",
    "Pyramids FC",
    "Wydad Casablanca",
    "San Lorenzo",
    "SS Lazio",
    "Eintracht Frankfurt",
    "Crystal Palace",
    "Wolverhampton Wanderers",
    "Brighton & Hove Albion",
    "Fulham",
    "Leeds United",
    "Southampton",
    "Burnley",
    "Watford",
    "Norwich City",
    "Sheffield United",
    "Stoke City",
    "Sunderland",
    "West Bromwich Albion",
    "Middlesbrough",
    "Nottingham Forest",
    "PSV Eindhoven",
    "Feyenoord",
    "Olympiacos",
    "Colo-Colo",
    "Universidad de Chile",
    "Peñarol",
    "Nacional",
    "Olimpia",
    "Cerro Porteño",
    "América de Cali",
    "Deportivo Cali",
    "Independiente Santa Fe",
    "LDU Quito",
    "Barcelona SC",
    "Emelec",
    "Alianza Lima",
    "Universitario",
    "Sporting Cristal",
    "Bolívar",
    "The Strongest",
    "Zenit St. Petersburg",
    "Spartak Moscow",
    "CSKA Moscow",
    "Lokomotiv Moscow",
    "Dynamo Moscow",
    "Panathinaikos",
    "AEK Athens",
    "PAOK",
    "Shakhtar Donetsk",
    "Dynamo Kyiv",
    "Legia Warsaw",
    "Lech Poznań",
    "Wisła Kraków",
    "Dinamo Zagreb",
    "Hajduk Split",
    "Red Star Belgrade",
    "Partizan Belgrade",
    "Red Bull Salzburg",
    "Rapid Wien",
    "Austria Wien",
    "BSC Young Boys",
    "FC Basel",
    "FC Copenhagen",
    "Brøndby IF",
    "Rosenborg",
    "Molde",
    "Bodø/Glimt",
    "Malmö FF",
    "AIK",
    "IFK Göteborg",
    "Club Brugge",
    "Anderlecht",
    "Standard Liège",
    "KRC Genk",
    "Urawa Red Diamonds",
    "Kashima Antlers",
    "Vissel Kobe",
    "Yokohama F. Marinos",
    "Gamba Osaka",
    "Jeonbuk Hyundai Motors",
    "Ulsan HD FC",
    "FC Seoul",
    "Suwon Samsung Bluewings",
    "Pohang Steelers",
    "Guangzhou FC",
    "Shanghai Port",
    "Beijing Guoan",
    "Shandong Taishan",
    "Buriram United",
    "Muangthong United",
    "Kerala Blasters",
    "Mohun Bagan SG",
    "East Bengal",
    "Al-Sadd",
    "Al-Duhail",
    "Al-Ain",
    "Shabab Al-Ahli",
    "Al-Jazira",
    "Espérance de Tunis",
    "Club Africain",
    "Étoile du Sahel",
    "CS Sfaxien",
    "AS FAR",
    "USM Alger",
    "MC Alger",
    "JS Kabylie",
    "Enyimba",
    "Kano Pillars",
    "Enugu Rangers",
    "Asante Kotoko",
    "Hearts of Oak",
    "TP Mazembe",
    "AS Vita Club",
    "Horoya AC",
    "Coton Sport",
    "ASEC Mimosas",
    "Gor Mahia",
    "Young Africans",
    "Azam FC",
    "LAFC",
    "LA Galaxy",
    "Atlanta United FC",
    "Seattle Sounders FC",
    "New York City FC",
    "Austin FC",
    "D.C. United",
    "Toronto FC",
    "Vancouver Whitecaps FC",
    "CF Montréal",
    "Pachuca",
    "Toluca",
    "Santos Laguna",
    "León",
    "Atlas",
    "Saprissa",
    "Alajuelense",
    "Olimpia",
    "Motagua",
    "Sydney FC",
    "Melbourne Victory",
    "Western Sydney Wanderers",
    "Melbourne City",
    "Brisbane Roar",
    "Adelaide United",
    "Perth Glory",
    "Auckland FC",
    "SC Braga",
    "Atalanta",
    "Fiorentina",
    "Torino",
    "Bologna",
    "Sampdoria",
    "Genoa",
    "VfB Stuttgart",
    "Werder Bremen",
    "Hamburger SV",
    "Schalke 04",
    "Hertha BSC",
    "1. FC Köln",
    "Borussia Mönchengladbach",
    "RB Leipzig",
    "Villarreal",
    "Real Valladolid",
    "Espanyol",
    "Deportivo La Coruña",
    "Real Zaragoza",
    "LOSC Lille",
    "RC Lens",
    "Stade Rennais",
    "FC Nantes",
    "Girondins de Bordeaux",
    "AS Saint-Étienne",
    "Trabzonspor"
]

class TeamMapper:
    """Utility class for mapping team names to API-Football IDs"""
    
    def __init__(self):
        self.mapping_file = "team_id_mapping.json"
        self.team_mapping: Dict[str, TeamInfo] = {}
        self._load_existing_mapping()
    
    def _load_existing_mapping(self):
        """Load existing team mappings from file"""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, info in data.items():
                        self.team_mapping[name] = TeamInfo(
                            name=info['name'],
                            api_id=info.get('api_id'),
                            league=info.get('league'),
                            country=info.get('country')
                        )
                print(f"✅ Loaded {len(self.team_mapping)} team mappings from file")
            except Exception as e:
                print(f"⚠️  Could not load team mappings: {e}")
    
    def save_mapping(self):
        """Save current team mappings to file"""
        try:
            data = {}
            for name, info in self.team_mapping.items():
                data[name] = {
                    'name': info.name,
                    'api_id': info.api_id,
                    'league': info.league,
                    'country': info.country
                }
            
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved {len(self.team_mapping)} team mappings to file")
        except Exception as e:
            print(f"❌ Could not save team mappings: {e}")
    
    def add_team_mapping(self, name: str, api_id: int, league: str = None, country: str = None):
        """Add a team mapping"""
        self.team_mapping[name] = TeamInfo(
            name=name,
            api_id=api_id,
            league=league,
            country=country
        )
    
    def get_team_id(self, name: str) -> Optional[int]:
        """Get API ID for a team name"""
        team_info = self.team_mapping.get(name)
        return team_info.api_id if team_info else None
    
    def get_unmapped_teams(self) -> List[str]:
        """Get list of teams that don't have API IDs yet"""
        unmapped = []
        for team_name in TOP_250_TEAMS:
            if team_name not in self.team_mapping or self.team_mapping[team_name].api_id is None:
                unmapped.append(team_name)
        return unmapped
    
    def get_mapped_team_ids(self) -> List[int]:
        """Get list of API IDs for all mapped teams"""
        ids = []
        for team_name in TOP_250_TEAMS:
            if team_name in self.team_mapping and self.team_mapping[team_name].api_id:
                ids.append(self.team_mapping[team_name].api_id)
        return ids
    
    def get_mapping_progress(self) -> Dict[str, int]:
        """Get mapping progress statistics"""
        total = len(TOP_250_TEAMS)
        mapped = len([name for name in TOP_250_TEAMS 
                     if name in self.team_mapping and self.team_mapping[name].api_id])
        return {
            'total': total,
            'mapped': mapped,
            'unmapped': total - mapped,
            'progress_percent': round((mapped / total) * 100, 1)
        }

def get_team_mapper() -> TeamMapper:
    """Get a team mapper instance"""
    return TeamMapper()

def get_top_250_team_names() -> List[str]:
    """Get the list of top 250 team names"""
    return TOP_250_TEAMS.copy()

if __name__ == "__main__":
    # Quick test
    mapper = get_team_mapper()
    progress = mapper.get_mapping_progress()
    print(f"Team mapping progress: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
    
    unmapped = mapper.get_unmapped_teams()
    if unmapped:
        print(f"Unmapped teams: {len(unmapped)}")
        for team in unmapped[:5]:  # Show first 5
            print(f"  - {team}")
        if len(unmapped) > 5:
            print(f"  ... and {len(unmapped) - 5} more")