
from db import db
from db import Team, Match, EloRating
from flask import Flask, request, json
from datetime import datetime
from flask import render_template


app = Flask(__name__)
db_filename = "elo.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

def success_response(data, code=200):
    return json.dumps(data), code

def failure_response(message, code=404):
    return json.dumps({"error": message}), code



def expected_result(team_rating = 1000, opponent_rating = 1000):
    return 1 / (1 + 10 ** ((opponent_rating - team_rating) / 400))

def update_elo(team_rating = 1000, opponent_rating = 1000, actual_score = 0, k = 20):
    expected = expected_result(team_rating, opponent_rating)
    return team_rating + k * (actual_score - expected)      


# Get the match result based on home and away scores
def get_match_result(home_score, away_score):
    if home_score > away_score:
        return (1, 0)     # home win
    elif home_score < away_score:
        return (0, 1)     # away win
    else:
        return (0.5, 0.5) # draw
    
def update_elo_after_match(match_id, k=20):
    match = Match.query.get(match_id)
    if not match:
        return failure_response("Match not found", 404)
    if match.home_score is None or match.away_score is None:
        return failure_response("Match scores not available", 400)

    home_team = Team.query.get(match.home_team_id)
    away_team = Team.query.get(match.away_team_id)

    # Get current or default ratings
    home_team_rating = EloRating.query.filter_by(team_id=home_team.id).order_by(EloRating.date.desc()).first()
    away_team_rating = EloRating.query.filter_by(team_id=away_team.id).order_by(EloRating.date.desc()).first()

    home_rating = home_team_rating.rating if home_team_rating else 1000
    away_rating = away_team_rating.rating if away_team_rating else 1000
    # Match result as scores (1/0/0.5)
    home_score, away_score = get_match_result(match.home_score, match.away_score)

    # Calculate new ratings
    new_home_rating = update_elo(home_rating, away_rating, home_score, k)
    new_away_rating = update_elo(away_rating, home_rating, away_score, k)

    # Save updated ratings
    db.session.add(EloRating(team_id=home_team.id, date=match.date, rating=new_home_rating))
    db.session.add(EloRating(team_id=away_team.id, date=match.date, rating=new_away_rating))
    db.session.commit()

@app.route("/update-match-elo/<int:match_id>", methods=["POST"])
def update_match_elo_route(match_id):
    result = update_elo_after_match(match_id)
    if isinstance(result, tuple):  
        return result
    return success_response(f"Elo updated for match {match_id}", 200)

@app.route("/api/teams/", methods=["GET"])
def get_teams():
    """Endpoint to get all teams"""
    teams = []
    for team in Team.query.all():
        teams.append(team.serialize())
    return success_response({"teams":teams})

@app.route("/api/teams/", methods=["POST"])
def create_team():
    """Endpoint to create a new team"""
    body = json.loads(request.data)
    if not body.get("name") or not body.get("country"):
        return failure_response("Missing name or country", 400)
    
    new_team = Team(name=body["name"], country=body["country"])
    db.session.add(new_team)
    db.session.commit()
    return success_response({"id": new_team.id, "name": new_team.name, "country": new_team.country}, 201)

@app.route("/api/matches/", methods=["GET"])
def get_matches():
    """Endpoint to get all matches"""
    matches = []
    for match in Match.query.all():
        matches.append({
            "id": match.id,
            "date": match.date.isoformat(),
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_score": match.home_score,
            "away_score": match.away_score
        })
    return success_response({"matches": matches})

@app.route("/api/matches/", methods=["POST"])
def create_match():
    """Endpoint to create a new match"""
    body = json.loads(request.data)
    if not body.get("date") or not body.get("home_team_id") or not body.get("away_team_id"):
        return failure_response("Missing date, home_team_id, or away_team_id", 400)
    
    date = datetime.strptime(body["date"], "%Y-%m-%d").date()
    new_match = Match(date=date, home_team_id=body["home_team_id"], away_team_id=body["away_team_id"],
                      home_score=body.get("home_score", 0), away_score=body.get("away_score", 0))
    db.session.add(new_match)
    db.session.commit()
    return success_response({"id": new_match.id, "date": new_match.date.isoformat(),
                             "home_team_id": new_match.home_team_id, "away_team_id": new_match.away_team_id}, 201)

@app.route("/api/elo-ratings/", methods=["GET"])
def get_elo_ratings():
    """Endpoint to get all Elo ratings"""
    elo_ratings = []
    for rating in EloRating.query.all():
        elo_ratings.append({
            "id": rating.id,
            "team_id": rating.team_id,
            "date": rating.date.isoformat(),
            "rating": rating.rating
        })
    return success_response({"elo_ratings": elo_ratings})


@app.route("/")
def show_team_elos():
    # Get all teams
    teams = Team.query.all()
    team_elos = []
    for team in teams:
        # Get latest Elo for this team
        latest_elo = (
            EloRating.query.filter_by(team_id=team.id)
            .order_by(EloRating.date.desc())
            .first()
        )
        team_elos.append({
            "name": team.name,
            "country": team.country,
            "elo": round(latest_elo.rating, 1) if latest_elo else "N/A"
        })
    # Sort by Elo descending (if available)
    team_elos = sorted(team_elos, key=lambda x: x["elo"] if x["elo"] != "N/A" else 0, reverse=True)
    return render_template("team_elos.html", teams=team_elos)


def batch_update_elo_for_all_matches(k=20):
    """
    Recalculate Elo for all matches in chronological order.
    This will clear all existing EloRatings and recalculate from scratch.
    """
    # Clear all existing Elo ratings
    EloRating.query.delete()
    db.session.commit()

    # Get all matches in chronological order
    matches = Match.query.order_by(Match.date.asc(), Match.id.asc()).all()
    for match in matches:
        update_elo_after_match(match.id, k)
    print(f"Processed {len(matches)} matches for Elo recalculation.")

    
if __name__ == "__main__":
    app.run(debug=True)