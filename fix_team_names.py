#!/usr/bin/env python3
"""
Fix team names that aren't being found by the API
Create alternative search terms for teams that fail to match
"""

import os
import requests
import time
from datetime import datetime

# Teams that are failing to be found with their likely API names
TEAM_NAME_FIXES = {
    # Spanish teams
    "Valencia CF": ["Valencia", "Valencia FC"],
    "Cádiz CF": ["Cadiz", "Cádiz", "CF Cadiz"],
    "Athletic Club": ["Athletic Bilbao", "Athletic Club Bilbao"],
    
    # Saudi/Middle East teams  
    "Al-Ittihad Club": ["Al Ittihad", "Al-Ittihad", "Ittihad FC"],
    "Al-Ahli": ["Al Ahli", "Al-Ahli Saudi", "Al Ahli Jeddah"],
    
    # English teams
    "Everton FC": ["Everton"],
    
    # Brazilian teams
    "CR Vasco da Gama": ["Vasco da Gama", "Vasco", "CR Vasco"],
    "Grêmio": ["Gremio", "Grêmio FBPA", "Gremio Porto Alegre"],
    
    # African teams
    "Simba SC": ["Simba", "Simba Sports Club"],
    
    # Portuguese teams  
    "Sporting CP": ["Sporting", "Sporting Lisbon", "Sporting Portugal"],
    
    # Add more problematic teams
    "SE Palmeiras": ["Palmeiras"],
    "São Paulo FC": ["São Paulo", "Sao Paulo", "São Paulo FC"],
    "Santos FC": ["Santos"],
    "Club América": ["América", "Club America"],
    "Chivas Guadalajara": ["Guadalajara", "CD Guadalajara"],
    "Inter Miami": ["Inter Miami CF"],
    "LAFC": ["Los Angeles FC"],
    "LA Galaxy": ["Los Angeles Galaxy"],
    "D.C. United": ["DC United"],
    "CF Montréal": ["Montreal", "CF Montreal"],
    
    # More international teams
    "Fenerbahçe": ["Fenerbahce", "Fenerbahçe SK"],
    "Beşiktaş": ["Besiktas", "Beşiktaş JK"],
    "Al-Nassr": ["Al Nassr", "Al-Nassr FC"],
    "Al-Hilal": ["Al Hilal", "Al-Hilal FC"],
    "Persib Bandung": ["Persib"],
    "Kashima Antlers": ["Kashima"],
    "Jeonbuk Hyundai Motors": ["Jeonbuk Motors", "Jeonbuk FC"],
    "Ulsan HD FC": ["Ulsan Hyundai", "Ulsan HD"],
    "FC Seoul": ["Seoul FC"],
    "Suwon Samsung Bluewings": ["Suwon Bluewings", "Suwon Samsung"],
    "Pohang Steelers": ["Pohang"],
    "Guangzhou FC": ["Guangzhou", "Guangzhou City"],
    "Shanghai Port": ["Shanghai SIPG", "Shanghai Harbour"],
    "Beijing Guoan": ["Beijing FC"],
    "Shandong Taishan": ["Shandong Luneng"],
}

def test_team_search(team_name, api_key):
    """Test searching for a team with various name variations"""
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    # Try original name first
    variations = [team_name]
    
    # Add variations if available
    if team_name in TEAM_NAME_FIXES:
        variations.extend(TEAM_NAME_FIXES[team_name])
    
    print(f"\n🔍 Testing search for: {team_name}")
    
    for i, variation in enumerate(variations):
        print(f"  {i+1}. Trying: '{variation}'")
        
        try:
            response = requests.get(
                "https://v3.football.api-sports.io/teams",
                headers=headers,
                params={"search": variation}
            )
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get('response', [])
                
                if teams:
                    print(f"     ✅ Found {len(teams)} results:")
                    for j, team_data in enumerate(teams[:3]):  # Show first 3
                        team = team_data.get('team', {})
                        print(f"        {j+1}. {team.get('name')} (ID: {team.get('id')}) - {team.get('country')}")
                    
                    # Return the best match
                    best_match = teams[0].get('team', {})
                    return {
                        'original_name': team_name,
                        'search_term': variation,
                        'api_name': best_match.get('name'),
                        'api_id': best_match.get('id'),
                        'country': best_match.get('country')
                    }
                else:
                    print(f"     ❌ No results for '{variation}'")
            else:
                print(f"     ❌ API error: {response.status_code}")
                
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    print(f"  ❌ No matches found for {team_name}")
    return None

def main():
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found")
        return
    
    # Test the problematic teams
    failing_teams = [
        "Valencia CF", "Cádiz CF", "Al-Ittihad Club", "Everton FC", 
        "CR Vasco da Gama", "Al-Ahli", "Grêmio", "Simba SC",
        "SE Palmeiras", "São Paulo FC", "Santos FC", "Club América",
        "Chivas Guadalajara", "Inter Miami", "LAFC", "LA Galaxy",
        "D.C. United", "CF Montréal", "Al-Nassr", "Al-Hilal"
    ]
    
    print("🧪 Testing team name variations...")
    successful_mappings = []
    
    for team_name in failing_teams:
        result = test_team_search(team_name, api_key)
        if result:
            successful_mappings.append(result)
        time.sleep(1)  # Be nice to the API
    
    print(f"\n📊 Results: {len(successful_mappings)}/{len(failing_teams)} teams found")
    
    if successful_mappings:
        print("\n✅ Successful mappings:")
        for mapping in successful_mappings:
            print(f"  '{mapping['original_name']}' -> '{mapping['api_name']}' (ID: {mapping['api_id']})")
    
    return successful_mappings

if __name__ == "__main__":
    main()