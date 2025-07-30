#!/usr/bin/env python3
"""
Apply auto-generated team mappings to improve import success rate
"""

import json
import os
from typing import Dict, Optional
from top_250_teams import get_team_mapper

def load_auto_mappings() -> Dict:
    """Load auto-generated team mappings"""
    mappings_file = "auto_generated_team_mappings.json"
    
    if not os.path.exists(mappings_file):
        print(f"❌ {mappings_file} not found")
        print("💡 Run 'python3 comprehensive_team_diagnostics.py' first")
        return {}
    
    try:
        with open(mappings_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        print(f"✅ Loaded {len(mappings)} auto-generated mappings")
        return mappings
    except Exception as e:
        print(f"❌ Error loading mappings: {e}")
        return {}

def apply_mappings_to_team_mapper():
    """Apply auto-generated mappings to the team mapper"""
    auto_mappings = load_auto_mappings()
    
    if not auto_mappings:
        return False
    
    team_mapper = get_team_mapper()
    applied_count = 0
    
    print("🔄 Applying auto-generated mappings...")
    
    for team_name, mapping_data in auto_mappings.items():
        api_id = mapping_data.get('api_id')
        api_name = mapping_data.get('api_name')
        country = mapping_data.get('country')
        confidence = mapping_data.get('confidence', 0)
        
        if api_id and confidence > 0.7:  # Only apply high-confidence mappings
            # Check if team is already mapped
            existing_id = team_mapper.get_team_id(team_name)
            
            if not existing_id:
                team_mapper.add_team_mapping(
                    name=team_name,
                    api_id=api_id,
                    league="TBD",  # Will be updated during import
                    country=country or "Unknown"
                )
                applied_count += 1
                print(f"✅ Mapped: {team_name} → {api_name} (ID: {api_id})")
            else:
                print(f"⚠️  Skipped: {team_name} already mapped (ID: {existing_id})")
    
    if applied_count > 0:
        team_mapper.save_mapping()
        print(f"💾 Saved {applied_count} new team mappings")
    
    # Show updated progress
    progress = team_mapper.get_mapping_progress()
    print(f"📊 Updated mapping progress: {progress['mapped']}/{progress['total']} ({progress['progress_percent']}%)")
    
    return True

def show_mapping_stats():
    """Show statistics about the mappings"""
    auto_mappings = load_auto_mappings()
    
    if not auto_mappings:
        return
    
    print(f"\n📊 Auto-Generated Mapping Statistics:")
    print(f"=" * 50)
    
    # Count by confidence level
    high_confidence = sum(1 for m in auto_mappings.values() if m.get('confidence', 0) > 0.9)
    medium_confidence = sum(1 for m in auto_mappings.values() if 0.7 <= m.get('confidence', 0) <= 0.9)
    low_confidence = sum(1 for m in auto_mappings.values() if m.get('confidence', 0) < 0.7)
    
    print(f"🟢 High confidence (>0.9): {high_confidence}")
    print(f"🟡 Medium confidence (0.7-0.9): {medium_confidence}")
    print(f"🔴 Low confidence (<0.7): {low_confidence}")
    
    # Count by country
    countries = {}
    for mapping in auto_mappings.values():
        country = mapping.get('country', 'Unknown')
        countries[country] = countries.get(country, 0) + 1
    
    print(f"\n🌍 Teams by country (top 10):")
    for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {country}: {count}")
    
    # Show teams that might need manual review
    manual_review = []
    for team_name, mapping in auto_mappings.items():
        if mapping.get('confidence', 0) < 0.8:
            manual_review.append((team_name, mapping))
    
    if manual_review:
        print(f"\n⚠️  Teams needing manual review ({len(manual_review)}):")
        for team_name, mapping in manual_review[:5]:
            confidence = mapping.get('confidence', 0)
            api_name = mapping.get('api_name', 'Unknown')
            print(f"   {team_name} → {api_name} (confidence: {confidence:.2f})")
        if len(manual_review) > 5:
            print(f"   ... and {len(manual_review) - 5} more")

def main():
    print("🔧 Team Mapping Application Tool")
    print("=" * 40)
    
    # Show current stats
    team_mapper = get_team_mapper()
    current_progress = team_mapper.get_mapping_progress()
    print(f"📊 Current mapping: {current_progress['mapped']}/{current_progress['total']} ({current_progress['progress_percent']}%)")
    
    # Show auto-mapping stats
    show_mapping_stats()
    
    # Apply mappings
    print(f"\n🚀 Applying auto-generated mappings...")
    success = apply_mappings_to_team_mapper()
    
    if success:
        print(f"\n✅ Mapping application complete!")
        
        # Show final stats
        final_progress = team_mapper.get_mapping_progress()
        improvement = final_progress['mapped'] - current_progress['mapped']
        
        if improvement > 0:
            print(f"📈 Improvement: +{improvement} teams mapped")
            print(f"📊 Final mapping: {final_progress['mapped']}/{final_progress['total']} ({final_progress['progress_percent']}%)")
        else:
            print(f"📊 No new mappings applied (all high-confidence teams already mapped)")
    else:
        print(f"❌ Failed to apply mappings")

if __name__ == "__main__":
    main()