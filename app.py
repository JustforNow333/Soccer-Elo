from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from db import db, Team, Match, EloRating
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///elo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

db.init_app(app)


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


def update_elo_after_match(match_id, k=20):
    match = Match.query.get(match_id)
    if not match:
        return jsonify({"error": "Match not found"}), 404

    home_team = Team.query.get(match.home_team_id)
    away_team = Team.query.get(match.away_team_id)

    if home_team is None or away_team is None:
        return {"error": "Home or away team not found"}, 400

    home_rating = EloRating.query.filter_by(team_id=home_team.id).order_by(
        EloRating.date.desc()).first()
    away_rating = EloRating.query.filter_by(team_id=away_team.id).order_by(
        EloRating.date.desc()).first()

    home_score, away_score = get_match_result(match.home_score,
                                              match.away_score)
    home_rating_val = home_rating.rating if home_rating else 1000
    away_rating_val = away_rating.rating if away_rating else 1000

    db.session.add(
        EloRating(team_id=home_team.id,
                  date=match.date,
                  rating=update_elo(home_rating_val, away_rating_val,
                                    home_score, k)))
    db.session.add(
        EloRating(team_id=away_team.id,
                  date=match.date,
                  rating=update_elo(away_rating_val, home_rating_val,
                                    away_score, k)))
    db.session.commit()
    return {"message": "Elo updated"}, 200


@app.route("/api/teams/", methods=["GET"])
def get_teams():
    return jsonify({"teams": [team.serialize() for team in Team.query.all()]})


@app.route("/api/teams/", methods=["POST"])
def create_team():
    body = request.get_json()
    if not body.get("name") or not body.get("league"):
        return jsonify({"error": "Missing name or league"}), 400
    team = Team(name=body["name"], league=body["league"])
    db.session.add(team)
    db.session.commit()
    return jsonify(team.serialize()), 201


@app.route("/api/matches/", methods=["POST"])
def create_match():
    body = request.get_json()
    try:
        date = datetime.strptime(body["date"], "%Y-%m-%d").date()
        match = Match(
            date=date,
            home_team_id=body["home_team_id"],
            away_team_id=body["away_team_id"],
            home_score=body.get("home_score", 0),
            away_score=body.get("away_score", 0),
        )
        db.session.add(match)
        db.session.flush()
        update_elo_after_match(match.id)
        db.session.commit()
        return jsonify({"id": match.id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/elo-ratings/", methods=["GET"])
def get_elo_ratings():
    ratings = EloRating.query.all()
    return jsonify({
        "elo_ratings": [{
            "team_id": r.team_id,
            "rating": r.rating,
            "date": r.date.isoformat()
        } for r in ratings]
    })


@app.route("/")
def show_teams():
    teams = Team.query.all()
    team_elos = []
    for team in teams:
        latest = EloRating.query.filter_by(team_id=team.id).order_by(
            EloRating.date.desc()).first()
        team_elos.append({
            "name": team.name,
            "league": team.league,
            "elo": round(latest.rating, 1) if latest else "N/A"
        })
    team_elos.sort(key=lambda x: x["elo"] if isinstance(x["elo"], float) else 0, reverse=True)
    return render_template("team_elos.html", teams=team_elos)


@app.route("/top-teams")
def top_teams_by_league():
    teams = Team.query.all()
    team_elos = []
    for team in teams:
        latest = EloRating.query.filter_by(team_id=team.id).order_by(
            EloRating.date.desc()).first()
        team_elos.append({
            "name": team.name,
            "league": team.league,
            "elo": round(latest.rating, 1) if latest else None
        })
    # Group by league and find top team in each
    league_top = {}
    league_groups = defaultdict(list)
    for t in team_elos:
        if t["elo"] is not None:
            league_groups[t["league"]].append(t)
    for league, teams in league_groups.items():
        top_team = max(teams, key=lambda x: x["elo"])
        league_top[league] = top_team
    league_top = dict(sorted(league_top.items()))
    return render_template("team_elo2.html", league_top=league_top)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
