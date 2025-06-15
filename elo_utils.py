# elo_utils.py
def expected_result(team_rating, opponent_rating):
    return 1 / (1 + 10**((opponent_rating - team_rating) / 400))

def update_elo(team_rating, opponent_rating, actual_score, k=20):
    expected = expected_result(team_rating, opponent_rating)
    return team_rating + k * (actual_score - expected)

def get_match_result(home_score, away_score):
    if home_score > away_score:
        return 1, 0
    elif home_score < away_score:
        return 0, 1
    else:
        return 0.5, 0.5
