from datetime import UTC
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import text

from database import db


def get_current_week():
    from models import BettingPeriod

    period = db.session.query(BettingPeriod).filter_by(is_settled=False).order_by(BettingPeriod.week.desc()).first()

    if period:
        return period.week

    print(
        "[WARNING] No active (unsettled) betting period found in database. Defaulting to week 10. Please create a new betting period via /admin."
    )
    return 10


def check_betting_period_lock(week):
    from datetime import datetime

    from models import BettingPeriod

    period = db.session.query(BettingPeriod).filter_by(week=week).first()

    if not period:
        return None

    lock_time = period.lock_time
    if lock_time.tzinfo is None:
        lock_time = lock_time.replace(tzinfo=UTC)

    if period.is_locked or datetime.now(UTC) >= lock_time:
        if not period.is_locked:
            period.is_locked = True
            db.session.commit()
        return period.lock_time

    return None


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("pages.index"))
        if not getattr(current_user, "is_admin", False):
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for("betting.betting"))
        return f(*args, **kwargs)

    return decorated_function


def query_analytics(sql, params=None):
    """Execute a read-only SQL query and return results as a list of dicts."""
    result = db.session.execute(text(sql), params or {})
    return [dict(row._mapping) for row in result]


def get_league_id_for_week(week):
    league_rows = query_analytics(
        "SELECT DISTINCT league_id FROM sleeper_matchups WHERE week = :week",
        {"week": week},
    )
    return league_rows[0]["league_id"] if league_rows else None


def get_team_mapping(week):
    """Get roster_id to owner name mapping from league database for the given week."""
    current_league_id = get_league_id_for_week(week)

    roster_rows = query_analytics(
        """
        SELECT r.roster_id, u.display_name, u.username
        FROM sleeper_rosters r
        LEFT JOIN sleeper_users u ON r.owner_id = u.user_id
        WHERE r.league_id = :league_id
        """,
        {"league_id": current_league_id},
    )

    team_mapping = {}
    for row in roster_rows:
        owner_name = row["display_name"] or row["username"] or f"Team {row['roster_id']}"
        team_mapping[row["roster_id"]] = owner_name

    return team_mapping
