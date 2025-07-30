#!/usr/bin/env python3
"""
Comprehensive team search diagnostics for all 250 teams
Creates CSV output with detailed analysis and auto-generates manual mappings
"""

import os
import time
import requests
import csv
import json
from typing import List, Dict, Optional, Tuple
from top_250_teams import TOP_250_TEAMS

class TeamSearchDiagnostics:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key,
            "x-apisports-host": "v3.football.api-sports.io"
        }
        self.base_url = "https://v3.football.api-sports.io/teams"
        self.results = []
        self.manual_mappings = {}
        
    def normalize_team_name(self, name: str) -> List[str]:
        """Generate search variations based on API documentation patterns"""
        variations = [name]  # Start with original
        
        # Apply normalization rules from documentation
        normalized = name
        
        # Remove common suffixes
        suffixes_to_remove = ["FC", "CF", "SC", "Football Club", "Club de Fútbol", "S.p.A."]
        for suffix in suffixes_to_remove:
            if normalized.endswith(f" {suffix}"):
                variations.append(normalized.replace(f" {suffix}", ""))
        
        # Remove prefixes like "Club", "Club Atlético"
        prefixes_to_remove = ["Club ", "Club Atlético ", "Club de ", "CR "]
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                variations.append(normalized.replace(prefix, ""))
        
        # Simplify diacritics (common patterns)
        diacritic_map = {
            "ã": "a", "á": "a", "à": "a", "â": "a",
            "é": "e", "ê": "e",
            "í": "i", "î": "i", 
            "ó": "o", "ô": "o", "õ": "o",
            "ú": "u", "û": "u", "ü": "u",
            "ç": "c",
            "ñ": "n"
        }
        
        simplified = normalized
        for accented, simple in diacritic_map.items():
            simplified = simplified.replace(accented, simple)
        if simplified != normalized:
            variations.append(simplified)
        
        # Add known specific variations
        specific_variations = {
            # Spanish teams
            "Valencia CF": ["Valencia"],
            "Cádiz CF": ["Cadiz", "CF Cadiz"],
            "Athletic Club": ["Athletic Bilbao", "Athletic Club Bilbao"],
            "Real Betis": ["Real Betis Balompie"],
            
            # English teams  
            "Everton FC": ["Everton"],
            "Manchester United": ["Man United"],
            "Leicester City": ["Leicester"],
            "West Ham United": ["West Ham"],
            "Newcastle United": ["Newcastle"],
            "Tottenham Hotspur": ["Tottenham", "Spurs"],
            
            # Italian teams
            "AC Milan": ["Milan", "AC Milano"],
            "Inter Milan": ["Inter", "Internazionale", "FC Internazionale Milano"],
            "Juventus": ["Juve"],
            "AS Roma": ["Roma"],
            "SS Lazio": ["Lazio"],
            "Atalanta": ["Atalanta BC"],
            "Fiorentina": ["ACF Fiorentina"],
            
            # German teams
            "Bayern Munich": ["Bayern München", "FC Bayern Munich", "FC Bayern"],
            "Borussia Dortmund": ["BVB", "Dortmund"],
            "Bayer Leverkusen": ["Leverkusen"],
            "Eintracht Frankfurt": ["Frankfurt"],
            
            # French teams
            "Paris Saint-Germain": ["PSG", "Paris SG"],
            "Olympique Marseille": ["Marseille", "OM"],
            "AS Monaco": ["Monaco"],
            
            # Brazilian teams
            "CR Vasco da Gama": ["Vasco da Gama", "Vasco"],
            "Grêmio": ["Gremio", "Gremio Porto Alegre"],
            "SE Palmeiras": ["Palmeiras"],
            "São Paulo FC": ["São Paulo", "Sao Paulo"],
            "Santos FC": ["Santos"],
            "Corinthians": ["Sport Club Corinthians Paulista"],
            "Flamengo": ["CR Flamengo"],
            
            # Argentine teams
            "Boca Juniors": ["Boca", "CA Boca Juniors"],
            "River Plate": ["River", "CA River Plate"],
            "Independiente": ["CA Independiente"],
            "Racing Club": ["Racing"],
            "San Lorenzo": ["CA San Lorenzo"],
            
            # Mexican teams
            "Club América": ["América", "Club America"],
            "Chivas Guadalajara": ["Guadalajara", "CD Guadalajara"],
            "Cruz Azul": ["Cruz Azul FC"],
            "Pumas UNAM": ["Pumas", "UNAM"],
            "Tigres UANL": ["Tigres"],
            "Monterrey": ["CF Monterrey"],
            
            # MLS teams
            "Inter Miami": ["Inter Miami CF"],
            "LAFC": ["Los Angeles FC"],
            "LA Galaxy": ["Los Angeles Galaxy"],
            "D.C. United": ["DC United"],
            "Seattle Sounders FC": ["Seattle Sounders"],
            "New York City FC": ["New York City", "NYCFC"],
            "CF Montréal": ["Montreal", "CF Montreal"],
            
            # Middle Eastern teams
            "Al-Nassr": ["Al Nassr", "Al-Nassr FC"],
            "Al-Hilal": ["Al Hilal", "Al-Hilal FC"],
            "Al-Ittihad Club": ["Al Ittihad", "Al-Ittihad", "Al Ittihad Saudi"],
            "Al-Ahli": ["Al Ahli", "Al-Ahli Saudi", "Al Ahli Jeddah"],
            
            # Turkish teams
            "Fenerbahçe": ["Fenerbahce", "Fenerbahçe SK"],
            "Beşiktaş": ["Besiktas", "Beşiktaş JK"],
            "Galatasaray": ["Galatasaray SK"],
            
            # Portuguese teams
            "Sporting CP": ["Sporting", "Sporting Lisbon"],
            "SL Benfica": ["Benfica"],
            "FC Porto": ["Porto"],
            "SC Braga": ["Braga"],
            
            # Dutch teams
            "Ajax": ["AFC Ajax", "Ajax Amsterdam"],
            "PSV Eindhoven": ["PSV"],
            "Feyenoord": ["Feyenoord Rotterdam"],
            
            # Asian teams
            "Kashima Antlers": ["Kashima"],
            "Jeonbuk Hyundai Motors": ["Jeonbuk Motors", "Jeonbuk FC"],
            "Ulsan HD FC": ["Ulsan Hyundai", "Ulsan HD"],
            "FC Seoul": ["Seoul FC"],
            "Guangzhou FC": ["Guangzhou"],
            "Shanghai Port": ["Shanghai SIPG"],
            "Beijing Guoan": ["Beijing FC"],
            
            # African teams
            "Al-Ahly": ["Al Ahly", "Al-Ahly SC"],
            "Zamalek SC": ["Zamalek"],
            "Simba SC": ["Simba"],
            "Mamelodi Sundowns": ["Sundowns"],
            "Kaizer Chiefs": ["Chiefs"],
            "Orlando Pirates": ["Pirates"],
        }
        
        if name in specific_variations:
            variations.extend(specific_variations[name])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            if var not in seen:
                seen.add(var)
                unique_variations.append(var)
        
        return unique_variations[:6]  # Limit to prevent too many API calls
    
    def search_team(self, search_term: str) -> List[Dict]:
        """Search for a team and return all results"""
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params={"search": search_term}
            )
            
            if response.status_code == 200:
                data = response.json()
                teams = data.get('response', [])
                return [team_data.get('team', {}) for team_data in teams]
            else:
                print(f"❌ API error for '{search_term}': {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error searching '{search_term}': {e}")
            return []
    
    def analyze_team(self, team_name: str) -> Dict:
        """Analyze all search variations for a single team"""
        print(f"🔍 Analyzing: {team_name}")
        
        variations = self.normalize_team_name(team_name)
        analysis = {
            'original_name': team_name,
            'variations_tried': variations,
            'results': {},
            'best_match': None,
            'match_confidence': 0
        }
        
        for i, variation in enumerate(variations):
            if i > 0:
                print(f"   Trying: {variation}")
            
            results = self.search_team(variation)
            analysis['results'][variation] = results
            
            # Record results for CSV
            if results:
                for rank, team in enumerate(results[:5], 1):  # Top 5 results
                    self.results.append({
                        'original_name': team_name,
                        'search_term': variation,
                        'result_rank': rank,
                        'team_id': team.get('id'),
                        'team_name': team.get('name'),
                        'country': team.get('country'),
                        'founded': team.get('founded'),
                        'national': team.get('national', False)
                    })
                
                # Check if this is a good match
                first_result = results[0]
                confidence = self.calculate_match_confidence(team_name, variation, first_result)
                
                if confidence > analysis['match_confidence']:
                    analysis['best_match'] = {
                        'search_term': variation,
                        'team_id': first_result.get('id'),
                        'team_name': first_result.get('name'),
                        'country': first_result.get('country'),
                        'confidence': confidence
                    }
                    analysis['match_confidence'] = confidence
            else:
                # Record no results
                self.results.append({
                    'original_name': team_name,
                    'search_term': variation,
                    'result_rank': 0,
                    'team_id': None,
                    'team_name': 'NO RESULTS',
                    'country': None,
                    'founded': None,
                    'national': None
                })
            
            time.sleep(0.4)  # Rate limiting
        
        # If we found a good match, add to manual mappings
        if analysis['best_match'] and analysis['match_confidence'] > 0.7:
            self.manual_mappings[team_name] = {
                'api_id': analysis['best_match']['team_id'],
                'api_name': analysis['best_match']['team_name'],
                'search_term': analysis['best_match']['search_term'],
                'country': analysis['best_match']['country'],
                'confidence': analysis['match_confidence']
            }
            print(f"✅ Best match: {analysis['best_match']['team_name']} (ID: {analysis['best_match']['team_id']}) - {analysis['match_confidence']:.2f}")
        else:
            print(f"❌ No good match found (best: {analysis['match_confidence']:.2f})")
        
        return analysis
    
    def calculate_match_confidence(self, original_name: str, search_term: str, api_result: Dict) -> float:
        """Calculate confidence score for a match"""
        api_name = api_result.get('name', '').lower()
        original_lower = original_name.lower()
        search_lower = search_term.lower()
        
        # Exact match
        if search_lower == api_name:
            return 1.0
        
        # Very close match
        if original_lower in api_name or api_name in original_lower:
            return 0.9
        
        # Good partial match
        original_words = set(original_lower.split())
        api_words = set(api_name.split())
        
        if original_words and api_words:
            overlap = len(original_words.intersection(api_words))
            total = len(original_words.union(api_words))
            jaccard = overlap / total if total > 0 else 0
            return jaccard * 0.8
        
        return 0.1  # Default low confidence
    
    def run_full_analysis(self):
        """Run analysis on all 250 teams"""
        print(f"🚀 Starting comprehensive analysis of {len(TOP_250_TEAMS)} teams...")
        print("=" * 70)
        
        successful_matches = 0
        failed_matches = []
        
        for i, team_name in enumerate(TOP_250_TEAMS, 1):
            print(f"\n[{i}/{len(TOP_250_TEAMS)}] ", end="")
            
            analysis = self.analyze_team(team_name)
            
            if analysis['best_match']:
                successful_matches += 1
            else:
                failed_matches.append(team_name)
        
        print(f"\n" + "=" * 70)
        print(f"📊 Analysis Complete!")
        print(f"✅ Successful matches: {successful_matches}/{len(TOP_250_TEAMS)} ({successful_matches/len(TOP_250_TEAMS)*100:.1f}%)")
        print(f"❌ Failed matches: {len(failed_matches)}")
        
        if failed_matches:
            print(f"\n🔍 Teams that need manual research:")
            for team in failed_matches[:10]:  # Show first 10
                print(f"   - {team}")
            if len(failed_matches) > 10:
                print(f"   ... and {len(failed_matches) - 10} more")
    
    def save_results(self):
        """Save results to CSV and JSON files"""
        # Save detailed CSV
        csv_filename = "team_search_diagnostics.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['original_name', 'search_term', 'result_rank', 'team_id', 'team_name', 'country', 'founded', 'national']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"💾 Detailed results saved to: {csv_filename}")
        
        # Save manual mappings JSON
        mappings_filename = "auto_generated_team_mappings.json"
        with open(mappings_filename, 'w', encoding='utf-8') as f:
            json.dump(self.manual_mappings, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Auto-generated mappings saved to: {mappings_filename}")
        
        # Save summary CSV
        summary_filename = "team_mapping_summary.csv"
        summary_data = []
        
        for team_name in TOP_250_TEAMS:
            if team_name in self.manual_mappings:
                mapping = self.manual_mappings[team_name]
                summary_data.append({
                    'original_name': team_name,
                    'status': 'FOUND',
                    'api_id': mapping['api_id'],
                    'api_name': mapping['api_name'],
                    'search_term': mapping['search_term'],
                    'confidence': f"{mapping['confidence']:.2f}",
                    'country': mapping['country']
                })
            else:
                summary_data.append({
                    'original_name': team_name,
                    'status': 'NOT_FOUND',
                    'api_id': '',
                    'api_name': '',
                    'search_term': '',
                    'confidence': '0.00',
                    'country': ''
                })
        
        with open(summary_filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['original_name', 'status', 'api_id', 'api_name', 'search_term', 'confidence', 'country']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_data)
        
        print(f"💾 Summary saved to: {summary_filename}")

def main():
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        print("❌ API_FOOTBALL_KEY environment variable not found")
        print("Set it with: export API_FOOTBALL_KEY=your_key_here")
        return
    
    print("🔬 Comprehensive Team Search Diagnostics")
    print("This will analyze all 250 teams with multiple search variations")
    print("Estimated time: 15-20 minutes")
    print("=" * 70)
    
    diagnostics = TeamSearchDiagnostics(api_key)
    
    try:
        diagnostics.run_full_analysis()
        diagnostics.save_results()
        
        print(f"\n🎉 Diagnostics complete!")
        print(f"📁 Files generated:")
        print(f"   • team_search_diagnostics.csv - Detailed search results")
        print(f"   • auto_generated_team_mappings.json - Ready-to-use mappings")
        print(f"   • team_mapping_summary.csv - Quick overview")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Analysis interrupted by user")
        print(f"💾 Saving partial results...")
        diagnostics.save_results()
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        print(f"💾 Saving partial results...")
        diagnostics.save_results()

if __name__ == "__main__":
    main()