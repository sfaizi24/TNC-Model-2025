from datetime import UTC, datetime, timedelta

import pytest
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
