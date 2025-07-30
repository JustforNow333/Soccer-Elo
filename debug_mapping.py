#!/usr/bin/env python3
"""
Debug script to test team mapping and understand the 88 teams issue
"""

import os
import requests
import time
import json
from top_250_teams import get_team_mapper, get_top_250_team_names

def test_api_connection():
    """Test if API is working"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ No API key found")
        return False
    
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    try:
        response = requests.get(
            "https://v3.football.api-sports.io/status",
            headers=headers
        )
        print(f"🔌 API Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 API Response: {data}")
            return True
        else:
            print(f"❌ API Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def search_team_in_league(team_name, league_id, api_key):
    """Search for a team in a specific league"""
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    try:
        response = requests.get(
            f"https://v3.football.api-sports.io/teams?league={league_id}&season=2024",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            teams = data.get('response', [])
            
            for team_data in teams:
                team = team_data.get('team', {})
                team_api_name = team.get('name', '').lower()
                search_name = team_name.lower()
                
                # Simple match check
                if search_name in team_api_name or team_api_name in search_name:
                    return {
                        'id': team.get('id'),
                        'name': team.get('name'),
                        'league': league_id,
                        'country': team.get('country', 'Unknown')
                    }
        
        time.sleep(0.5)  # Rate limiting
        return None
        
    except Exception as e:
        print(f"❌ Error searching {team_name} in league {league_id}: {e}")
        return None

def manual_mapping_test():
    """Try to manually map some key teams"""
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    # Major leagues to test
    test_leagues = [
        (39, "Premier League"),
        (140, "La Liga"), 
        (78, "Bundesliga"),
        (135, "Serie A"),
        (61, "Ligue 1")
    ]
    
    # Test with some key teams
    test_teams = [
        "Real Madrid",
        "FC Barcelona", 
        "Manchester United",
        "Paris Saint-Germain",
        "Manchester City"
    ]
    
    print("🔍 Testing manual team mapping...")
    mapped_teams = {}
    
    for team_name in test_teams:
        print(f"\n🔎 Searching for: {team_name}")
        found = False
        
        for league_id, league_name in test_leagues:
            result = search_team_in_league(team_name, league_id, api_key)
            if result:
                print(f"✅ Found in {league_name}: {result['name']} (ID: {result['id']})")
                mapped_teams[team_name] = result
                found = True
                break
        
        if not found:
            print(f"❌ Could not find: {team_name}")
    
    print(f"\n📊 Mapped {len(mapped_teams)} out of {len(test_teams)} test teams")
    
    # Save test mapping
    if mapped_teams:
        with open('test_mapping.json', 'w') as f:
            json.dump(mapped_teams, f, indent=2)
        print("💾 Saved test mapping to test_mapping.json")

if __name__ == "__main__":
    print("🚀 Starting debug mapping process...")
    
    # Test API connection
    if test_api_connection():
        print("✅ API connection successful")
        manual_mapping_test()
    else:
        print("❌ API connection failed")