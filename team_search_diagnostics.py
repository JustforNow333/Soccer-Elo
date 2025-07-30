#!/usr/bin/env python3
"""
Diagnostic tool to understand Football API team search behavior
"""

import os
import requests
import time
from collections import defaultdict

def analyze_search_patterns(api_key):
    """Analyze how the API search works with different patterns"""
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    # Test different search patterns
    test_cases = [
        # Exact matches
        ("Real Madrid", "Should find Real Madrid CF"),
        ("Barcelona", "Should find FC Barcelona"),
        ("Manchester United", "Should find Manchester United FC"),
        
        # Partial matches
        ("Madrid", "Should return multiple Madrid teams"),
        ("United", "Should return multiple United teams"),
        ("Milan", "Should return AC Milan and Inter Milan"),
        
        # With suffixes
        ("Valencia CF", "Valencia with suffix"),
        ("Valencia", "Valencia without suffix"),
        ("Athletic Club", "Athletic with Club"),
        ("Athletic Bilbao", "Athletic with city"),
        
        # Special characters
        ("São Paulo", "With Portuguese characters"),
        ("Sao Paulo", "Without special characters"),
        ("Fenerbahçe", "With Turkish characters"),
        ("Fenerbahce", "Without Turkish characters"),
        
        # Different formats
        ("Al Nassr", "With space"),
        ("Al-Nassr", "With hyphen"),
        ("Al Nassr FC", "With FC suffix"),
    ]
    
    print("🔍 Analyzing Football API search patterns...")
    results = {}
    
    for search_term, description in test_cases:
        print(f"\n📊 Testing: '{search_term}' - {description}")
        
        try:
            response = requests.get(
                "https://v3.football.api-sports.io/teams",
                headers=headers,
                params={"search": search_term}
            )
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get('response', [])
                
                print(f"   Results: {len(teams)} teams found")
                
                if teams:
                    # Show top 3 results
                    for i, team_data in enumerate(teams[:3]):
                        team = team_data.get('team', {})
                        print(f"   {i+1}. {team.get('name')} (ID: {team.get('id')}) - {team.get('country')}")
                    
                    if len(teams) > 3:
                        print(f"   ... and {len(teams) - 3} more")
                
                results[search_term] = {
                    'count': len(teams),
                    'teams': teams[:5]  # Store top 5
                }
            else:
                print(f"   ❌ API Error: {response.status_code}")
                results[search_term] = {'error': response.status_code}
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[search_term] = {'error': str(e)}
    
    return results

def find_common_patterns(results):
    """Analyze the results to find common patterns"""
    print("\n📈 Pattern Analysis:")
    
    # Analyze suffix patterns
    suffix_comparison = [
        ("Valencia CF", "Valencia"),
        ("São Paulo", "Sao Paulo"),
        ("Fenerbahçe", "Fenerbahce"),
        ("Al Nassr", "Al-Nassr"),
    ]
    
    for original, variation in suffix_comparison:
        if original in results and variation in results:
            orig_count = results[original].get('count', 0)
            var_count = results[variation].get('count', 0)
            print(f"   '{original}': {orig_count} results vs '{variation}': {var_count} results")
    
    # Find teams that appear in multiple searches
    team_appearances = defaultdict(list)
    for search_term, result in results.items():
        if 'teams' in result:
            for team_data in result['teams']:
                team = team_data.get('team', {})
                team_name = team.get('name')
                if team_name:
                    team_appearances[team_name].append(search_term)
    
    print("\n🔄 Teams appearing in multiple searches:")
    for team_name, searches in team_appearances.items():
        if len(searches) > 1:
            print(f"   '{team_name}' found in: {', '.join(searches)}")

def test_problematic_teams(api_key):
    """Test the teams that are currently failing"""
    headers = {
        "x-apisports-key": api_key,
        "x-apisports-host": "v3.football.api-sports.io"
    }
    
    failing_teams = [
        "Valencia CF", "Cádiz CF", "Al-Ittihad Club", "Everton FC",
        "CR Vasco da Gama", "Al-Ahli", "Grêmio", "Simba SC"
    ]
    
    print("\n🧪 Testing problematic teams with variations...")
    
    for team_name in failing_teams:
        print(f"\n🔍 Testing: {team_name}")
        
        # Try exact search first
        try:
            response = requests.get(
                "https://v3.football.api-sports.io/teams",
                headers=headers,
                params={"search": team_name}
            )
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get('response', [])
                
                if teams:
                    print(f"   ✅ Exact search found {len(teams)} results")
                    for i, team_data in enumerate(teams[:2]):
                        team = team_data.get('team', {})
                        print(f"      {i+1}. {team.get('name')} - {team.get('country')}")
                else:
                    print(f"   ❌ Exact search: No results")
                    
                    # Try partial search (first word only)
                    first_word = team_name.split()[0]
                    print(f"   🔄 Trying partial search: '{first_word}'")
                    
                    partial_response = requests.get(
                        "https://v3.football.api-sports.io/teams",
                        headers=headers,
                        params={"search": first_word}
                    )
                    
                    if partial_response.status_code == 200:
                        partial_data = partial_response.json()
                        partial_teams = partial_data.get('response', [])
                        
                        print(f"      Partial search found {len(partial_teams)} results")
                        for i, team_data in enumerate(partial_teams[:3]):
                            team = team_data.get('team', {})
                            print(f"         {i+1}. {team.get('name')} - {team.get('country')}")
            
            time.sleep(0.7)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found")
        return
    
    print("🚀 Starting Football API team search diagnostics...")
    
    # Run pattern analysis
    results = analyze_search_patterns(api_key)
    find_common_patterns(results)
    
    # Test problematic teams
    test_problematic_teams(api_key)
    
    print("\n✅ Diagnostics complete!")

if __name__ == "__main__":
    main()