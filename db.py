from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy 

def expected_result(team_rating, opponent_rating):
    return 1 / (1 + 10 ** ((opponent_rating - team_rating) / 400))

def update_elo(team_rating, opponent_rating, actual_score, k=20):
    expected = expected_result(team_rating, opponent_rating)
    return team_rating + k * (actual_score - expected)

class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    
    # Optional reverse relationships
    home_matches = db.relationship('Match', backref='home_team', foreign_keys='Match.home_team_id', lazy=True)
    away_matches = db.relationship('Match', backref='away_team', foreign_keys='Match.away_team_id', lazy=True)
    elo_ratings = db.relationship('EloRating', backref='team', lazy=True)

    def __init__(self, **kwargs):
        """Initialize a new team object"""
        self.name = kwargs.get("name")
        self.country = kwargs.get("country")


    def simple_serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country
        }
    

    def serialize(self):
        """Serialize the team object"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "home_matches": [match.serialize() for match in self.home_matches],
            "away_matches": [match.serialize() for match in self.away_matches],
            "elo_ratings": [rating.serialize() for rating in self.elo_ratings]
        }

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    home_score = db.Column(db.Integer, nullable=False)
    away_score = db.Column(db.Integer, nullable=False)

    def __init__(self, **kwargs):
        """Initialize a new match object"""
        self.date = kwargs.get("date")
        self.home_team_id = kwargs.get("home_team_id")
        self.away_team_id = kwargs.get("away_team_id")
        self.home_score = kwargs.get("home_score", 0)
        self.away_score = kwargs.get("away_score", 0)


    def simple_serialize(self):
        """Simple serialize the match object"""
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_score": self.home_score,
            "away_score": self.away_score
        }

    def serialize(self):
        """Serialize the match object"""
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "home_score": self.home_score,
            "away_score": self.away_score
        }

class EloRating(db.Model):
    __tablename__ = 'elo_ratings'
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    rating = db.Column(db.Float, nullable=False)

    def __init__(self, **kwargs):
        """Initialize a new Elo rating object"""
        self.team_id = kwargs.get("team_id")
        self.date = kwargs.get("date")
        self.rating = kwargs.get("rating")

    def simple_serialize(self):
        """Simple serialize the Elo rating object"""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "rating": self.rating
        }

    def serialize(self):
        """Serialize the Elo rating object"""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "date": self.date.isoformat(),
            "rating": self.rating
        }