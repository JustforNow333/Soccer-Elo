#!/usr/bin/env python3
"""
ELO Recalculation Triggers
Automatic triggers that ensure ELO ratings are recalculated whenever match history is updated
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Set, Optional, Dict, Any
from functools import wraps

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db, Team, Match, EloRating
from enhanced_elo_engine import EnhancedEloEngine

class EloTriggerManager:
    """
    Manages automatic ELO recalculation triggers
    Tracks when matches are added/updated and triggers appropriate recalculations
    """
    
    def __init__(self):
        self.affected_teams: Set[int] = set()
        self.earliest_change_date: Optional[datetime] = None
        self.engine = EnhancedEloEngine()
    
    def register_match_change(self, match: Match, change_type: str = "update"):
        """
        Register that a match has been added/updated/deleted
        """
        # Add affected teams
        if match.home_team_id:
            self.affected_teams.add(match.home_team_id)
        if match.away_team_id:
            self.affected_teams.add(match.away_team_id)
        
        # Track earliest change date for optimization
        if self.earliest_change_date is None or match.date < self.earliest_change_date:
            self.earliest_change_date = match.date
        
        print(f"📝 Registered {change_type} for match {match.id} on {match.date}")
        print(f"   Affected teams: {match.home_team_id}, {match.away_team_id}")
    
    def register_matches_batch(self, matches: List[Match], change_type: str = "batch_update"):
        """
        Register multiple match changes efficiently
        """
        if not matches:
            return
        
        print(f"📝 Registering batch {change_type} for {len(matches)} matches...")
        
        for match in matches:
            if match.home_team_id:
                self.affected_teams.add(match.home_team_id)
            if match.away_team_id:
                self.affected_teams.add(match.away_team_id)
            
            if self.earliest_change_date is None or match.date < self.earliest_change_date:
                self.earliest_change_date = match.date
        
        print(f"   Total affected teams: {len(self.affected_teams)}")
        print(f"   Earliest change: {self.earliest_change_date}")
    
    def execute_recalculation(self, force: bool = False) -> bool:
        """
        Execute ELO recalculation for all affected teams
        """
        if not self.affected_teams and not force:
            print("✅ No teams need ELO recalculation")
            return True
        
        try:
            print(f"🔄 Executing ELO recalculation...")
            print(f"   Affected teams: {len(self.affected_teams)}")
            print(f"   From date: {self.earliest_change_date}")
            
            # Convert set to list for the engine
            team_ids = list(self.affected_teams)
            
            # Execute recalculation
            stats = self.engine.recalculate_elo_for_teams(
                team_ids, 
                from_date=self.earliest_change_date
            )
            
            print(f"✅ ELO recalculation complete!")
            print(f"   Teams processed: {stats['teams_processed']}")
            print(f"   Matches processed: {stats['total_matches_processed']}")
            
            # Clear tracking after successful recalculation
            self.affected_teams.clear()
            self.earliest_change_date = None
            
            return True
            
        except Exception as e:
            print(f"❌ Error during ELO recalculation: {e}")
            return False
    
    def auto_recalculate_if_needed(self, threshold_teams: int = 5) -> bool:
        """
        Automatically trigger recalculation if enough teams are affected
        """
        if len(self.affected_teams) >= threshold_teams:
            print(f"🚨 Auto-triggering ELO recalculation ({len(self.affected_teams)} teams affected)")
            return self.execute_recalculation()
        
        return True

# Global trigger manager instance
_trigger_manager = EloTriggerManager()

def get_trigger_manager() -> EloTriggerManager:
    """Get the global trigger manager instance"""
    return _trigger_manager

def elo_recalculation_decorator(func):
    """
    Decorator that automatically triggers ELO recalculation after functions
    that modify match data
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Execute the original function
        result = func(*args, **kwargs)
        
        # Check if we need to trigger recalculation
        trigger_manager = get_trigger_manager()
        if trigger_manager.affected_teams:
            print(f"🔄 Auto-triggering ELO recalculation after {func.__name__}")
            trigger_manager.execute_recalculation()
        
        return result
    
    return wrapper

def trigger_elo_after_match_import(imported_matches: List[Match]):
    """
    Trigger ELO recalculation after a batch of matches has been imported
    """
    if not imported_matches:
        return
    
    trigger_manager = get_trigger_manager()
    trigger_manager.register_matches_batch(imported_matches, "import")
    
    # Execute recalculation immediately for imports
    trigger_manager.execute_recalculation()

def trigger_elo_after_match_update(match: Match):
    """
    Trigger ELO recalculation after a single match has been updated
    """
    trigger_manager = get_trigger_manager()
    trigger_manager.register_match_change(match, "update")
    
    # Auto-recalculate if we have enough affected teams
    trigger_manager.auto_recalculate_if_needed(threshold_teams=1)

def trigger_elo_after_match_deletion(match: Match):
    """
    Trigger ELO recalculation after a match has been deleted
    """
    trigger_manager = get_trigger_manager()
    trigger_manager.register_match_change(match, "delete")
    
    # Execute recalculation immediately for deletions (they affect historical calculations)
    trigger_manager.execute_recalculation()

def schedule_daily_elo_maintenance():
    """
    Schedule daily ELO maintenance tasks
    - Recalculate for any teams with recent match updates
    - Clean up orphaned ELO ratings
    - Verify ELO consistency
    """
    print("🔧 Running daily ELO maintenance...")
    
    try:
        # Check for teams that may need recalculation
        # (teams with matches but no recent ELO ratings)
        cutoff_date = datetime.now() - timedelta(days=7)
        
        teams_needing_update = db.session.query(Team.id).filter(
            Team.id.in_(
                db.session.query(Match.home_team_id).filter(Match.date >= cutoff_date).union(
                    db.session.query(Match.away_team_id).filter(Match.date >= cutoff_date)
                )
            )
        ).outerjoin(EloRating, Team.id == EloRating.team_id).filter(
            db.or_(
                EloRating.date < cutoff_date,
                EloRating.date.is_(None)
            )
        ).distinct().all()
        
        if teams_needing_update:
            team_ids = [team[0] for team in teams_needing_update]
            print(f"🔄 Found {len(team_ids)} teams needing ELO updates")
            
            engine = EnhancedEloEngine()
            stats = engine.recalculate_elo_for_teams(team_ids, from_date=cutoff_date)
            
            print(f"✅ Daily maintenance complete: {stats}")
        else:
            print("✅ All teams have up-to-date ELO ratings")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during daily ELO maintenance: {e}")
        return False

def verify_elo_consistency() -> Dict[str, Any]:
    """
    Verify ELO rating consistency and identify any issues
    """
    print("🔍 Verifying ELO consistency...")
    
    issues = {
        'orphaned_ratings': [],
        'missing_ratings': [],
        'duplicate_ratings': [],
        'inconsistent_progression': []
    }
    
    try:
        # Check for orphaned ELO ratings (ratings without corresponding teams)
        orphaned = db.session.query(EloRating).outerjoin(Team).filter(Team.id.is_(None)).all()
        issues['orphaned_ratings'] = [r.id for r in orphaned]
        
        # Check for teams with matches but no ELO ratings
        teams_with_matches = db.session.query(Team.id).filter(
            db.or_(
                Team.id.in_(db.session.query(Match.home_team_id.distinct())),
                Team.id.in_(db.session.query(Match.away_team_id.distinct()))
            )
        ).all()
        
        for team_id, in teams_with_matches:
            rating_count = EloRating.query.filter_by(team_id=team_id).count()
            if rating_count == 0:
                issues['missing_ratings'].append(team_id)
        
        # Check for duplicate ratings on same date
        duplicates = db.session.query(
            EloRating.team_id, 
            EloRating.date, 
            db.func.count().label('count')
        ).group_by(
            EloRating.team_id, 
            EloRating.date
        ).having(db.func.count() > 1).all()
        
        issues['duplicate_ratings'] = [(d.team_id, d.date, d.count) for d in duplicates]
        
        print(f"🔍 ELO consistency check complete:")
        print(f"   Orphaned ratings: {len(issues['orphaned_ratings'])}")
        print(f"   Missing ratings: {len(issues['missing_ratings'])}")
        print(f"   Duplicate ratings: {len(issues['duplicate_ratings'])}")
        
        return issues
        
    except Exception as e:
        print(f"❌ Error during consistency check: {e}")
        return issues

def cleanup_elo_issues(issues: Dict[str, Any]) -> bool:
    """
    Clean up identified ELO consistency issues
    """
    print("🧹 Cleaning up ELO issues...")
    
    try:
        # Remove orphaned ratings
        if issues['orphaned_ratings']:
            EloRating.query.filter(EloRating.id.in_(issues['orphaned_ratings'])).delete()
            print(f"🗑️  Removed {len(issues['orphaned_ratings'])} orphaned ratings")
        
        # Remove duplicate ratings (keep the latest)
        for team_id, date, count in issues['duplicate_ratings']:
            duplicates = EloRating.query.filter_by(
                team_id=team_id, 
                date=date
            ).order_by(EloRating.id.desc()).all()
            
            # Keep the first (most recent ID), delete the rest
            for duplicate in duplicates[1:]:
                db.session.delete(duplicate)
            
            print(f"🗑️  Removed {count-1} duplicate ratings for team {team_id} on {date}")
        
        # Recalculate missing ratings
        if issues['missing_ratings']:
            engine = EnhancedEloEngine()
            stats = engine.recalculate_elo_for_teams(issues['missing_ratings'])
            print(f"🔄 Recalculated ratings for {len(issues['missing_ratings'])} teams")
        
        db.session.commit()
        print("✅ ELO cleanup complete")
        return True
        
    except Exception as e:
        print(f"❌ Error during ELO cleanup: {e}")
        db.session.rollback()
        return False

def main():
    """Standalone script for ELO triggers and maintenance"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ELO Triggers and Maintenance')
    parser.add_argument('--maintenance', action='store_true',
                       help='Run daily maintenance')
    parser.add_argument('--verify', action='store_true',
                       help='Verify ELO consistency')
    parser.add_argument('--cleanup', action='store_true',
                       help='Clean up ELO issues')
    
    args = parser.parse_args()
    
    try:
        from app import app
        with app.app_context():
            
            if args.maintenance:
                success = schedule_daily_elo_maintenance()
                return success
            
            if args.verify:
                issues = verify_elo_consistency()
                if any(len(v) > 0 for v in issues.values()):
                    print("⚠️  Issues found. Run with --cleanup to fix them.")
                    return False
                else:
                    print("✅ No issues found")
                    return True
            
            if args.cleanup:
                issues = verify_elo_consistency()
                success = cleanup_elo_issues(issues)
                return success
            
            # Default: show current trigger status
            trigger_manager = get_trigger_manager()
            print(f"📊 ELO Trigger Manager Status:")
            print(f"   Affected teams: {len(trigger_manager.affected_teams)}")
            print(f"   Earliest change: {trigger_manager.earliest_change_date}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)