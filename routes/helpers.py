import sqlite3
from datetime import UTC
from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required

from database import db

LEAGUE_DB_PATH = "backend/data/databases/league.db"
PROJECTIONS_DB_PATH = "backend/data/databases/projections.db"
ODDS_DB_PATH = "backend/data/databases/odds.db"


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


def get_team_mapping(week):
    """Get roster_id to owner name mapping from league database for the given week."""
    team_mapping = {}
    with sqlite3.connect(LEAGUE_DB_PATH) as league_conn:
        league_conn.row_factory = sqlite3.Row
        league_cursor = league_conn.cursor()

        league_cursor.execute(
            """
            SELECT DISTINCT league_id FROM matchups WHERE week = ?
        """,
            (week,),
        )
        league_row = league_cursor.fetchone()
        current_league_id = league_row["league_id"] if league_row else None

        league_cursor.execute(
            """
            SELECT r.roster_id, u.display_name, u.username
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE r.league_id = ?
        """,
            (current_league_id,),
        )

        for row in league_cursor.fetchall():
            owner_name = row["display_name"] or row["username"] or f"Team {row['roster_id']}"
            team_mapping[row["roster_id"]] = owner_name

    return team_mapping
