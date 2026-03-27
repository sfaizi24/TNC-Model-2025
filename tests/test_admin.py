from datetime import UTC, datetime

from database import db
from models import BettingPeriod


def test_admin_page_requires_admin(logged_in_client, user):
    resp = logged_in_client.get("/admin", follow_redirects=False)
    assert resp.status_code == 302


def test_admin_page_accessible_to_admin(admin_client, admin_user):
    resp = admin_client.get("/admin")
    assert resp.status_code == 200


def test_admin_api_rejects_anonymous(client):
    resp = client.get("/api/admin/pending_bets")
    # Should redirect to login or return 401
    assert resp.status_code in (302, 401)


def test_set_betting_period(admin_client, admin_user, db_session):
    resp = admin_client.post(
        "/api/admin/set_betting_period",
        json={
            "week": 15,
            "lock_time": "2026-12-25T18:00",
        },
    )
    assert resp.get_json()["success"] is True

    period = db.session.query(BettingPeriod).filter_by(week=15).first()
    assert period is not None
    assert period.is_locked is False
    assert period.lock_time.year == 2026
    assert period.lock_time.month == 12


def test_unlock_period(admin_client, admin_user, betting_period, db_session):
    betting_period.is_locked = True
    db_session.session.commit()

    resp = admin_client.post(
        "/api/admin/unlock_period",
        json={
            "week": betting_period.week,
        },
    )
    assert resp.get_json()["success"] is True

    db_session.session.refresh(betting_period)
    assert betting_period.is_locked is False
    lock_time = betting_period.lock_time
    if lock_time.tzinfo is None:
        lock_time = lock_time.replace(tzinfo=UTC)
    assert lock_time > datetime.now(UTC)
