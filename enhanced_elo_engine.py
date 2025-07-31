#!/usr/bin/env python3
"""
Enhanced ELO Calculation Engine
Comprehensive ELO rating system with progressive storage, adaptive K-factors, and automatic recalculation
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import db, Team, Match, EloRating

@dataclass
class EloCheckpoint:
    """Data class for ELO calculation checkpoints"""
    team_id: int
    date: datetime
    rating: float
    matches_processed: int
    last_match_id: int

class EnhancedEloEngine:
    """
    Comprehensive ELO calculation engine with:
    - Progressive rating storage with checkpoints
    - Adaptive K-factor calculations
    - Automatic recalculation triggers
    - Memory-efficient batch processing
    """
    
    def __init__(self, initial_rating: float = 1000.0, batch_size: int = 100):
        self.initial_rating = initial_rating
        self.batch_size = batch_size
        self.checkpoints: Dict[int, EloCheckpoint] = {}
        self.current_ratings: Dict[int, float] = {}
        self.match_counts: Dict[int, int] = defaultdict(int)
        
    def get_adaptive_k_factor(self, team_id: int, current_rating: float) -> float:
        """
        Calculate adaptive K-factor based on:
        - Number of matches played (experience)
        - Current rating level
        - Rating stability
        """
        matches_played = self.match_counts.get(team_id, 0)
        
        # Base K-factor decreases with experience
        if matches_played < 10:
            base_k = 40  # High K for new teams
        elif matches_played < 30:
            base_k = 30  # Medium K for developing teams
        elif matches_played < 100:
            base_k = 20  # Standard K for established teams
        else:
            base_k = 15  # Low K for veteran teams
        
        # Rating-based adjustment
        if current_rating < 800:
            rating_multiplier = 1.3  # Higher K for low-rated teams
        elif current_rating > 1800:
            rating_multiplier = 0.8  # Lower K for high-rated teams
        else:
            rating_multiplier = 1.0  # Standard K for mid-rated teams
        
        # Calculate final K-factor
        k_factor = base_k * rating_multiplier
        
        # Ensure reasonable bounds
        return max(10, min(50, k_factor))
    
    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for team A vs team B"""
        try:
            return 1 / (1 + 10**((rating_b - rating_a) / 400))
        except (OverflowError, ZeroDivisionError):
            return 0.5  # Neutral expectation as fallback
    
    def get_match_result_score(self, home_score: int, away_score: int, is_home: bool) -> float:
        """
        Get result score with home advantage consideration
        """
        if home_score > away_score:
            # Home team won
            if is_home:
                return 1.0  # Full win
            else:
                return 0.0  # Full loss
        elif home_score < away_score:
            # Away team won
            if is_home:
                return 0.0  # Full loss
            else:
                return 1.1  # Win with slight bonus for away victory
        else:
            # Draw
            if is_home:
                return 0.4  # Slight penalty for home draw
            else:
                return 0.6  # Slight bonus for away draw
    
    def update_elo_rating(self, team_id: int, opponent_id: int, match: Match, is_home: bool) -> float:
        """Update ELO rating for a single match"""
        # Get current ratings
        team_rating = self.current_ratings.get(team_id, self.initial_rating)
        opponent_rating = self.current_ratings.get(opponent_id, self.initial_rating)
        
        # Calculate expected score
        expected_score = self.calculate_expected_score(team_rating, opponent_rating)
        
        # Get actual score
        actual_score = self.get_match_result_score(
            match.home_score, match.away_score, is_home
        )
        
        # Get adaptive K-factor
        k_factor = self.get_adaptive_k_factor(team_id, team_rating)
        
        # Calculate new rating
        new_rating = team_rating + k_factor * (actual_score - expected_score)
        
        # Enforce bounds
        new_rating = max(0, min(5000, new_rating))
        
        # Update tracking
        self.current_ratings[team_id] = new_rating
        self.match_counts[team_id] += 1
        
        return new_rating
    
    def create_checkpoint(self, team_id: int, date: datetime, match_id: int) -> EloCheckpoint:
        """Create a checkpoint for ELO calculation state"""
        checkpoint = EloCheckpoint(
            team_id=team_id,
            date=date,
            rating=self.current_ratings.get(team_id, self.initial_rating),
            matches_processed=self.match_counts.get(team_id, 0),
            last_match_id=match_id
        )
        self.checkpoints[team_id] = checkpoint
        return checkpoint
    
    def load_checkpoint(self, team_id: int) -> Optional[EloCheckpoint]:
        """Load the most recent checkpoint for a team"""
        try:
            # Get the most recent ELO rating for this team
            latest_rating = EloRating.query.filter_by(team_id=team_id)\
                .order_by(EloRating.date.desc()).first()
            
            if latest_rating:
                # Count matches processed up to this point
                matches_count = Match.query.filter(
                    db.or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.date <= latest_rating.date
                ).count()
                
                # Get the last match processed
                last_match = Match.query.filter(
                    db.or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.date <= latest_rating.date
                ).order_by(Match.date.desc()).first()
                
                checkpoint = EloCheckpoint(
                    team_id=team_id,
                    date=latest_rating.date,
                    rating=latest_rating.rating,
                    matches_processed=matches_count,
                    last_match_id=last_match.id if last_match else 0
                )
                
                self.checkpoints[team_id] = checkpoint
                self.current_ratings[team_id] = latest_rating.rating
                self.match_counts[team_id] = matches_count
                
                return checkpoint
            
        except Exception as e:
            print(f"⚠️  Error loading checkpoint for team {team_id}: {e}")
        
        return None
    
    def calculate_elo_for_team(self, team_id: int, from_date: Optional[datetime] = None, 
                             force_recalculate: bool = False) -> int:
        """
        Calculate ELO ratings for a specific team from a given date
        Returns number of matches processed
        """
        print(f"🏆 Calculating ELO for team {team_id}...")
        
        # Load existing checkpoint unless forcing recalculation
        if not force_recalculate:
            checkpoint = self.load_checkpoint(team_id)
            if checkpoint and from_date:
                if checkpoint.date >= from_date:
                    print(f"✅ Team {team_id} ELO up to date (last: {checkpoint.date})")
                    return 0
                from_date = checkpoint.date
        
        # Initialize rating if no checkpoint
        if team_id not in self.current_ratings:
            self.current_ratings[team_id] = self.initial_rating
        
        # Get matches to process
        query = Match.query.filter(
            db.or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
        ).order_by(Match.date.asc())
        
        if from_date:
            query = query.filter(Match.date > from_date)
        
        matches = query.all()
        
        if not matches:
            print(f"✅ No new matches for team {team_id}")
            return 0
        
        print(f"📊 Processing {len(matches)} matches for team {team_id}")
        
        ratings_to_add = []
        matches_processed = 0
        
        for match in matches:
            try:
                # Determine if this team is home or away
                is_home = match.home_team_id == team_id
                opponent_id = match.away_team_id if is_home else match.home_team_id
                
                # Update ELO rating
                new_rating = self.update_elo_rating(team_id, opponent_id, match, is_home)
                
                # Add to batch
                ratings_to_add.append(EloRating(
                    team_id=team_id,
                    date=match.date,
                    rating=new_rating
                ))
                
                matches_processed += 1
                
                # Create checkpoint every 50 matches
                if matches_processed % 50 == 0:
                    self.create_checkpoint(team_id, match.date, match.id)
                    
                    # Batch commit
                    db.session.add_all(ratings_to_add)
                    db.session.commit()
                    ratings_to_add = []
                    
                    print(f"📈 Processed {matches_processed}/{len(matches)} matches for team {team_id}")
                
            except Exception as e:
                print(f"❌ Error processing match {match.id} for team {team_id}: {e}")
                continue
        
        # Final commit
        if ratings_to_add:
            db.session.add_all(ratings_to_add)
            db.session.commit()
        
        # Create final checkpoint
        if matches:
            self.create_checkpoint(team_id, matches[-1].date, matches[-1].id)
        
        print(f"✅ ELO calculation complete for team {team_id}: {matches_processed} matches")
        return matches_processed
    
    def recalculate_all_elos(self, from_date: Optional[datetime] = None, 
                           force_recalculate: bool = False) -> Dict[str, int]:
        """
        Recalculate ELO ratings for all teams
        Returns statistics about the calculation
        """
        print("🏆 Starting comprehensive ELO recalculation...")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Clear existing ratings if force recalculating
        if force_recalculate:
            print("🧹 Clearing existing ELO ratings...")
            EloRating.query.delete()
            db.session.commit()
            self.current_ratings.clear()
            self.match_counts.clear()
            self.checkpoints.clear()
        
        # Get all teams that have matches
        teams_with_matches = db.session.query(Team.id).filter(
            db.or_(
                Team.id.in_(db.session.query(Match.home_team_id.distinct())),
                Team.id.in_(db.session.query(Match.away_team_id.distinct()))
            )
        ).all()
        
        team_ids = [team[0] for team in teams_with_matches]
        
        print(f"📊 Found {len(team_ids)} teams with match history")
        
        stats = {
            'teams_processed': 0,
            'total_matches_processed': 0,
            'teams_skipped': 0,
            'errors': 0
        }
        
        for i, team_id in enumerate(team_ids):
            try:
                print(f"\n🔄 ({i+1}/{len(team_ids)}) Processing team {team_id}...")
                
                matches_processed = self.calculate_elo_for_team(
                    team_id, from_date, force_recalculate
                )
                
                if matches_processed > 0:
                    stats['teams_processed'] += 1
                    stats['total_matches_processed'] += matches_processed
                else:
                    stats['teams_skipped'] += 1
                
            except Exception as e:
                print(f"❌ Error processing team {team_id}: {e}")
                stats['errors'] += 1
                continue
        
        elapsed_time = datetime.now() - start_time
        
        print("\n🎉 ELO recalculation complete!")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   Teams processed: {stats['teams_processed']}")
        print(f"   Teams skipped (up to date): {stats['teams_skipped']}")
        print(f"   Total matches processed: {stats['total_matches_processed']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Time elapsed: {elapsed_time}")
        print(f"   Average per team: {elapsed_time.total_seconds() / len(team_ids):.1f}s")
        
        return stats
    
    def recalculate_elo_for_teams(self, team_ids: List[int], 
                                 from_date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Recalculate ELO ratings for specific teams (triggered by match updates)
        """
        print(f"🔄 Recalculating ELO for {len(team_ids)} teams...")
        
        stats = {
            'teams_processed': 0,
            'total_matches_processed': 0,
            'errors': 0
        }
        
        for team_id in team_ids:
            try:
                matches_processed = self.calculate_elo_for_team(team_id, from_date)
                
                if matches_processed > 0:
                    stats['teams_processed'] += 1
                    stats['total_matches_processed'] += matches_processed
                
            except Exception as e:
                print(f"❌ Error recalculating ELO for team {team_id}: {e}")
                stats['errors'] += 1
        
        print(f"✅ ELO recalculation complete for {len(team_ids)} teams")
        print(f"📊 Processed: {stats['teams_processed']} teams, {stats['total_matches_processed']} matches")
        
        return stats

def trigger_elo_recalculation(team_ids: List[int], from_date: Optional[datetime] = None):
    """
    Trigger ELO recalculation for specific teams
    This function should be called whenever match history is updated
    """
    try:
        engine = EnhancedEloEngine()
        stats = engine.recalculate_elo_for_teams(team_ids, from_date)
        
        print(f"🏆 ELO recalculation triggered successfully")
        return stats
        
    except Exception as e:
        print(f"❌ Error in ELO recalculation trigger: {e}")
        return None

def main():
    """Standalone script for comprehensive ELO calculation"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced ELO Calculation Engine')
    parser.add_argument('--force', action='store_true', 
                       help='Force complete recalculation (clears existing ratings)')
    parser.add_argument('--team-id', type=int, 
                       help='Calculate ELO for specific team only')
    parser.add_argument('--from-date', type=str, 
                       help='Calculate from specific date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    # Parse from_date if provided
    from_date = None
    if args.from_date:
        try:
            from_date = datetime.strptime(args.from_date, '%Y-%m-%d')
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return False
    
    try:
        # Initialize Flask app context
        from app import app
        with app.app_context():
            engine = EnhancedEloEngine()
            
            if args.team_id:
                # Calculate for specific team
                matches_processed = engine.calculate_elo_for_team(
                    args.team_id, from_date, args.force
                )
                print(f"✅ Processed {matches_processed} matches for team {args.team_id}")
            else:
                # Calculate for all teams
                stats = engine.recalculate_all_elos(from_date, args.force)
                print(f"✅ Full recalculation complete: {stats}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during ELO calculation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)