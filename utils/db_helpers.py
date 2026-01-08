from typing import Dict, List, Optional
from sqlalchemy import func
from db import db, Team, EloRating, Fixture


class EloQueryHelper:
    @staticmethod
    def get_latest_elo_map(team_ids: Optional[List[int]] = None) -> Dict[int, float]:
        subquery = db.session.query(
            EloRating.team_id,
            func.max(EloRating.date).label("latest_date")
        )
        if team_ids:
            subquery = subquery.filter(EloRating.team_id.in_(team_ids))
        subquery = subquery.group_by(EloRating.team_id).subquery()

        elo_map = {
            row.team_id: row.rating
            for row in db.session.query(EloRating).join(
                subquery,
                (EloRating.team_id == subquery.c.team_id) &
                (EloRating.date == subquery.c.latest_date)
            )
        }
        return elo_map

    @staticmethod
    def get_team_latest_elo(team_id: int, default: float = 1000.0) -> float:
        latest_elo = EloRating.query.filter_by(team_id=team_id)\
            .order_by(EloRating.date.desc()).first()
        return latest_elo.rating if latest_elo else default


class FixtureQueryHelper:
    @staticmethod
    def get_upcoming_fixtures(team_id: Optional[int] = None, limit: int = 10) -> List[Fixture]:
        from datetime import datetime
        from sqlalchemy import or_

        query = Fixture.query.filter(
            Fixture.date >= datetime.now(),
            Fixture.status.in_(["NS", "TBD", "POST"])
        )
        if team_id:
            query = query.filter(
                or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id)
            )
        return query.order_by(Fixture.date.asc()).limit(limit).all()

    @staticmethod
    def get_fixtures_with_elo_teams() -> List[Fixture]:
        from datetime import datetime
        upcoming_fixtures = Fixture.query.filter(
            Fixture.date >= datetime.now().date(),
            Fixture.status == "NS"
        ).order_by(Fixture.date.asc()).all()
        return [f for f in upcoming_fixtures if f.has_elo_teams()]


class TeamQueryHelper:
    @staticmethod
    def get_teams_with_api_ids() -> List[Team]:
        return Team.query.filter(Team.api_football_id.isnot(None)).all()

    @staticmethod
    def get_team_count() -> int:
        return Team.query.count()
