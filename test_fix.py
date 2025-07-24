#!/usr/bin/env python3
"""
Test script to verify the team creation bug fix
"""

import os
from app import app
from db import db, Team
from api_import import APIFootballImporter
from top_250_teams import get_team_mapper

def test_team_creation_fix():
    """Test that teams are actually created in database after mapping"""
    
    print("🧪 Testing team creation fix...")
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    if not api_key:
        print("❌ API_FOOTBALL_KEY not found")
        return False
    
    with app.app_context():
        # Clear existing teams for clean test
        print("🧹 Clearing existing teams...")
        Team.query.delete()
        db.session.commit()
        
        # Initialize importer
        importer = APIFootballImporter(
            api_key=api_key,
            current_season=2025,
            request_delay=0.5,
            max_requests_per_day=7000
        )
        
        print("📊 Before fix test:")
        teams_before = Team.query.count()
        print(f"   Teams in database: {teams_before}")
        
        # Test the team creation from mappings
        print("\n🔧 Testing create_teams_from_mappings()...")
        created_count = importer.create_teams_from_mappings()
        
        print("📊 After fix test:")
        teams_after = Team.query.count()
        print(f"   Teams in database: {teams_after}")
        print(f"   Teams created: {created_count}")
        
        # Verify teams are visible via API
        if teams_after > 0:
            sample_teams = Team.query.limit(5).all()
            print(f"\n✅ Sample teams created:")
            for team in sample_teams:
                print(f"   - {team.name} ({team.league}) - API ID: {team.api_football_id}")
            
            print(f"🎉 FIX VERIFIED: {teams_after} teams now exist in database!")
            return True
        else:
            print("❌ No teams were created - fix failed or no mappings exist")
            return False

if __name__ == "__main__":
    success = test_team_creation_fix()
    if success:
        print("\n✅ Test passed! The fix should work.")
    else:
        print("\n❌ Test failed! Check team mappings or API connection.")