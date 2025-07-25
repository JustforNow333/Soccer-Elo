# elo_utils.py
def expected_result(team_rating, opponent_rating):
    """Calculate expected result based on team ratings"""
    # CRITICAL FIX: Add input validation
    if not isinstance(team_rating, (int, float)) or not isinstance(opponent_rating, (int, float)):
        raise TypeError(f"Ratings must be numeric: team={team_rating}, opponent={opponent_rating}")
    
    if not (0 <= team_rating <= 5000) or not (0 <= opponent_rating <= 5000):
        raise ValueError(f"Ratings must be between 0-5000: team={team_rating}, opponent={opponent_rating}")
    
    try:
        return 1 / (1 + 10**((opponent_rating - team_rating) / 400))
    except (OverflowError, ZeroDivisionError) as e:
        print(f"⚠️ Mathematical error in expected_result: {e}")
        return 0.5  # Return neutral expectation as fallback

def update_elo(team_rating, opponent_rating, actual_score, k=20):
    """Update Elo rating with comprehensive validation"""
    # CRITICAL FIX: Validate all inputs
    if not isinstance(team_rating, (int, float)) or not isinstance(opponent_rating, (int, float)):
        raise TypeError(f"Ratings must be numeric: team={team_rating}, opponent={opponent_rating}")
    
    if not isinstance(actual_score, (int, float)):
        raise TypeError(f"Actual score must be numeric: {actual_score}")
    
    if not (0 <= team_rating <= 5000) or not (0 <= opponent_rating <= 5000):
        raise ValueError(f"Ratings must be between 0-5000: team={team_rating}, opponent={opponent_rating}")
    
    if not (0 <= actual_score <= 1):
        raise ValueError(f"Actual score must be between 0-1: {actual_score}")
    
    if not (1 <= k <= 100):  # Reasonable K-factor bounds
        raise ValueError(f"K-factor must be between 1-100: {k}")
    
    try:
        expected = expected_result(team_rating, opponent_rating)
        new_rating = team_rating + k * (actual_score - expected)
        
        # CRITICAL FIX: Enforce rating bounds
        new_rating = max(0, min(5000, new_rating))
        
        return new_rating
    except Exception as e:
        print(f"❌ Error calculating Elo update: {e}")
        return team_rating  # Return original rating as fallback

def get_match_result(home_score, away_score):
    """Get match result scores with validation"""
    # CRITICAL FIX: Add input validation
    if not isinstance(home_score, (int, float)) or not isinstance(away_score, (int, float)):
        raise TypeError(f"Scores must be numeric: home={home_score}, away={away_score}")
    
    if home_score < 0 or away_score < 0:
        raise ValueError(f"Scores cannot be negative: home={home_score}, away={away_score}")
    
    if home_score > 50 or away_score > 50:  # Sanity check
        raise ValueError(f"Unrealistic scores: home={home_score}, away={away_score}")
    
    if home_score > away_score:
        return 1, 0
    elif home_score < away_score:
        return 0, 1
    else:
        return 0.5, 0.5
