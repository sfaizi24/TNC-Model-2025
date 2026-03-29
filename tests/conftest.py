from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.pool import StaticPool

from app import create_app
from database import db as _db
from models import BettingPeriod, User

TEST_CONFIG = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite://",
    "SQLALCHEMY_ENGINE_OPTIONS": {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    },
    "WTF_CSRF_ENABLED": False,
    "SECRET_KEY": "test-secret",
    "GOOGLE_OAUTH_CLIENT_ID": "",
    "GOOGLE_OAUTH_CLIENT_SECRET": "",
}


@pytest.fixture(scope="session")
def app():
    app = create_app(TEST_CONFIG)
    yield app


@pytest.fixture(autouse=True)
def db_session(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(db_session):
    u = User(
        id="test-user-1",
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        account_balance=1000.0,
        total_pnl=0.0,
        is_admin=False,
    )
    db_session.session.add(u)
    db_session.session.commit()
    return u


@pytest.fixture
def admin_user(db_session):
    u = User(
        id="admin-user-1",
        username="adminuser",
        email="admin@example.com",
        first_name="Admin",
        last_name="User",
        account_balance=1000.0,
        total_pnl=0.0,
        is_admin=True,
    )
    db_session.session.add(u)
    db_session.session.commit()
    return u


@pytest.fixture
def logged_in_client(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = user.id
    return client


@pytest.fixture
def admin_client(client, admin_user):
    with client.session_transaction() as sess:
        sess["_user_id"] = admin_user.id
    return client


@pytest.fixture
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    from flask import template_rendered

    template_rendered.connect(record, app)
    yield recorded
    template_rendered.disconnect(record, app)


@pytest.fixture
def betting_period(db_session):
    period = BettingPeriod(
        week=10,
        lock_time=datetime.now(UTC) + timedelta(days=7),
        is_locked=False,
        is_settled=False,
    )
    db_session.session.add(period)
    db_session.session.commit()
    return period


ANALYTICS_TABLES = [
    "betting_odds_matchup_ml",
    "betting_odds_team_ou",
    "betting_odds_highest_scorer",
    "betting_odds_lowest_scorer",
    "betting_odds_first_place",
    "betting_odds_make_playoffs",
    "team_lineups",
    "sleeper_rosters",
    "sleeper_users",
    "sleeper_matchups",
    "projections_rosters",
]


@pytest.fixture
def analytics_tables(db_session):
    """Create analytics tables that mirror what publish.py pushes to PostgreSQL."""
    for table in ANALYTICS_TABLES:
        db_session.session.execute(text(f"DROP TABLE IF EXISTS {table}"))

    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_matchup_ml (
            run_id TEXT, week INTEGER, matchup TEXT,
            team1_id INTEGER, team1_name TEXT, team1_win_prob REAL, team1_ml TEXT,
            team2_id INTEGER, team2_name TEXT, team2_win_prob REAL, team2_ml TEXT,
            ties INTEGER, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_team_ou (
            run_id TEXT, week INTEGER, team_id INTEGER, team_name TEXT, owner TEXT,
            line REAL, over_prob REAL, over_odds TEXT, under_prob REAL, under_odds TEXT,
            push_count INTEGER, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_highest_scorer (
            run_id TEXT, week INTEGER, team_id INTEGER, team_name TEXT, owner TEXT,
            count INTEGER, probability REAL, odds TEXT, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_lowest_scorer (
            run_id TEXT, week INTEGER, team_id INTEGER, team_name TEXT, owner TEXT,
            count INTEGER, probability REAL, odds TEXT, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_first_place (
            id INTEGER PRIMARY KEY, run_id TEXT, week INTEGER,
            team_id INTEGER, team_name TEXT, owner TEXT,
            probability REAL, american_odds TEXT, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE betting_odds_make_playoffs (
            id INTEGER PRIMARY KEY, run_id TEXT, week INTEGER,
            team_id INTEGER, team_name TEXT, owner TEXT,
            probability REAL, american_odds TEXT, created_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE team_lineups (
            roster_id INTEGER, team_name TEXT, owner TEXT, record TEXT,
            slot TEXT, player_name TEXT, position TEXT,
            mu REAL, sigma REAL, var REAL, n_sources INTEGER,
            is_replacement INTEGER, week INTEGER, season TEXT, timestamp TEXT
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE sleeper_rosters (
            roster_id INTEGER, league_id TEXT, owner_id TEXT,
            co_owners TEXT, team_name TEXT, starters TEXT, players TEXT,
            reserve TEXT, taxi TEXT, settings TEXT, metadata TEXT,
            wins INTEGER, losses INTEGER, ties INTEGER,
            fpts REAL, fpts_against REAL, fpts_decimal REAL, fpts_against_decimal REAL,
            total_moves INTEGER, waiver_position INTEGER, waiver_budget_used INTEGER,
            created_at TIMESTAMP, updated_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE sleeper_users (
            user_id TEXT, username TEXT, display_name TEXT,
            avatar TEXT, metadata TEXT, created_at TIMESTAMP, updated_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE sleeper_matchups (
            matchup_id TEXT, league_id TEXT, week INTEGER, roster_id INTEGER,
            matchup_id_number INTEGER, starters TEXT, players TEXT,
            points REAL, custom_points REAL, players_points TEXT,
            created_at TIMESTAMP, updated_at TIMESTAMP
        )
    """)
    )
    db_session.session.execute(
        text("""
        CREATE TABLE projections_rosters (
            roster_id INTEGER, team_name TEXT, sleeper_player_id TEXT,
            first_name TEXT, last_name TEXT, position TEXT, nfl_team TEXT,
            week INTEGER, season TEXT, mu REAL, var REAL,
            starting_status INTEGER, timestamp TEXT
        )
    """)
    )
    db_session.session.commit()


@pytest.fixture
def seeded_analytics(analytics_tables, db_session):
    """Seed analytics tables with test data for week 10."""
    db_session.session.execute(
        text("""
        INSERT INTO sleeper_users (user_id, username, display_name)
        VALUES ('u1', 'alice', 'Alice A'), ('u2', 'bob', 'Bob B')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO sleeper_rosters (roster_id, league_id, owner_id)
        VALUES (1, 'league1', 'u1'), (2, 'league1', 'u2')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO sleeper_matchups (league_id, week, roster_id, matchup_id_number)
        VALUES ('league1', 10, 1, 1), ('league1', 10, 2, 1)
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_matchup_ml
            (week, matchup, team1_id, team1_name, team1_win_prob, team1_ml,
             team2_id, team2_name, team2_win_prob, team2_ml, ties)
        VALUES (10, 'Matchup 1', 1, 'Team1', 0.6, '-150', 2, 'Team2', 0.4, '+130', 0)
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_team_ou (week, team_id, team_name, owner, line, over_prob, over_odds, under_prob, under_odds)
        VALUES (10, 1, 'Team1', 'Alice A', 110.5, 0.55, '-120', 0.45, '+100'),
               (10, 2, 'Team2', 'Bob B', 95.0, 0.48, '+105', 0.52, '-125')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_highest_scorer (week, team_id, owner, probability, odds)
        VALUES (10, 1, 'Alice A', 0.35, '+185'), (10, 2, 'Bob B', 0.25, '+300')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_lowest_scorer (week, team_id, owner, probability, odds)
        VALUES (10, 1, 'Alice A', 0.20, '+400'), (10, 2, 'Bob B', 0.30, '+230')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_first_place (week, team_id, owner, probability, american_odds)
        VALUES (10, 1, 'Alice A', 0.45, '-120'), (10, 2, 'Bob B', 0.30, '+150')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO betting_odds_make_playoffs (week, team_id, owner, probability, american_odds)
        VALUES (10, 1, 'Alice A', 0.80, '-400'), (10, 2, 'Bob B', 0.60, '-150')
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO team_lineups (owner, week, slot, player_name, position, mu)
        VALUES ('Alice A', 10, 'QB', 'Patrick Mahomes', 'QB', 22.5),
               ('Alice A', 10, 'RB1', 'Derrick Henry', 'RB', 15.0),
               ('Alice A', 10, 'WR1', 'Tyreek Hill', 'WR', 18.0)
    """)
    )
    db_session.session.execute(
        text("""
        INSERT INTO projections_rosters (roster_id, first_name, last_name, position, mu, var, starting_status)
        VALUES (1, 'Patrick', 'Mahomes', 'QB', 22.5, 7.0, 1),
               (1, 'Bench', 'Player', 'WR', 5.0, 3.0, 0)
    """)
    )
    db_session.session.commit()
