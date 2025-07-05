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
        try:
            latest_elo = db.session.query(EloRating).filter_by(team_id=self.id)\
                         .order_by(EloRating.date.desc()).first()
            rating = latest_elo.rating if latest_elo else 1000
        except Exception as e:
            print(f"[serialize error for team {self.id}] {e}")
            rating = 1000

        return {
            "id": self.id,
            "name": self.name,
            "league": self.league,
            "elo": round(rating, 1)
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


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    subscription_status = db.Column(db.String(50), default="inactive")  # inactive, active, canceled, past_due
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def __init__(self, **kwargs):
        self.email = kwargs.get("email")
        self.stripe_customer_id = kwargs.get("stripe_customer_id")
        self.stripe_subscription_id = kwargs.get("stripe_subscription_id")
        self.subscription_status = kwargs.get("subscription_status", "inactive")
        self.subscription_start_date = kwargs.get("subscription_start_date")
        self.subscription_end_date = kwargs.get("subscription_end_date")

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            "subscription_status": self.subscription_status,
            "subscription_start_date": self.subscription_start_date.isoformat() if self.subscription_start_date else None,
            "subscription_end_date": self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def is_premium_active(self):
        """Check if user has an active premium subscription"""
        return self.subscription_status in ["active", "trialing"]


class Fixture(db.Model):
    __tablename__ = "fixtures"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    api_football_id = db.Column(db.Integer, nullable=False, unique=True)  # ID from API-Football
    date = db.Column(db.DateTime, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)  # Nullable if team not in our DB
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)  # Nullable if team not in our DB
    home_team_name = db.Column(db.String(100), nullable=False)  # Store original name from API
    away_team_name = db.Column(db.String(100), nullable=False)  # Store original name from API
    league_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # NS (Not Started), LIVE, FT (Finished), etc.
    venue = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    home_team = db.relationship("Team", foreign_keys=[home_team_id])
    away_team = db.relationship("Team", foreign_keys=[away_team_id])

    def __init__(self, **kwargs):
        self.api_football_id = kwargs.get("api_football_id")
        self.date = kwargs.get("date")
        self.home_team_id = kwargs.get("home_team_id")
        self.away_team_id = kwargs.get("away_team_id")
        self.home_team_name = kwargs.get("home_team_name")
        self.away_team_name = kwargs.get("away_team_name")
        self.league_name = kwargs.get("league_name")
        self.status = kwargs.get("status")
        self.venue = kwargs.get("venue")

    def serialize(self):
        return {
            "id": self.id,
            "api_football_id": self.api_football_id,
            "date": self.date.isoformat() if self.date else None,
            "home_team": self.home_team.simple_serialize() if self.home_team else {"name": self.home_team_name},
            "away_team": self.away_team.simple_serialize() if self.away_team else {"name": self.away_team_name},
            "league_name": self.league_name,
            "status": self.status,
            "venue": self.venue
        }

    def has_elo_teams(self):
        """Check if both teams have Elo ratings in our database"""
        return self.home_team_id is not None and self.away_team_id is not None
