from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    league = db.Column(db.String(100), nullable=False)
    home_matches = db.relationship("Match",
                                   back_populates="home_team",
                                   foreign_keys="Match.home_team_id",
                                   lazy=True)
    away_matches = db.relationship("Match",
                                   back_populates="away_team",
                                   foreign_keys="Match.away_team_id",
                                   lazy=True)
    elo_ratings = db.relationship("EloRating",
                                  back_populates="team",
                                  lazy=True)

    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.league = kwargs.get("league")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "league": self.league,
            "elo_ratings":
            [e.simple_serialize() for e in list(self.elo_ratings)]
        }

    def simple_serialize(self):
        return {"id": self.id, "name": self.name, "league": self.league}


class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer,
                             db.ForeignKey("teams.id"),
                             nullable=False)
    away_team_id = db.Column(db.Integer,
                             db.ForeignKey("teams.id"),
                             nullable=False)
    home_score = db.Column(db.Integer, nullable=False)
    away_score = db.Column(db.Integer, nullable=False)
    home_team = db.relationship("Team",
                                foreign_keys=[home_team_id],
                                back_populates="home_matches")
    away_team = db.relationship("Team",
                                foreign_keys=[away_team_id],
                                back_populates="away_matches")

    def __init__(self, **kwargs):
        self.date = kwargs.get("date")
        self.home_team_id = kwargs.get("home_team_id")
        self.away_team_id = kwargs.get("away_team_id")
        self.home_score = kwargs.get("home_score")
        self.away_score = kwargs.get("away_score")

    def serialize(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "home_team":
            self.home_team.simple_serialize() if self.home_team else None,
            "away_team":
            self.away_team.simple_serialize() if self.away_team else None,
            "home_score": self.home_score,
            "away_score": self.away_score
        }

    def simple_serialize(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_score": self.home_score,
            "away_score": self.away_score
        }


class EloRating(db.Model):
    __tablename__ = "elo_ratings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    team = db.relationship("Team", back_populates="elo_ratings")

    def __init__(self, **kwargs):
        self.team_id = kwargs.get("team_id")
        self.date = kwargs.get("date")
        self.rating = kwargs.get("rating")

    def serialize(self):
        return {
            "id": self.id,
            "team": self.team.simple_serialize() if self.team else None,
            "date": self.date.isoformat() if self.date else None,
            "rating": self.rating
        }

    def simple_serialize(self):
        return {"id": self.id, "team_id": self.team_id, "rating": self.rating}
