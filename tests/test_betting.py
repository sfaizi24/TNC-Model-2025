from datetime import UTC, datetime, timedelta

from app.database import db
from app.models import Bet, BettingPeriod, WeeklyStats


def test_place_bet_positive_odds(logged_in_client, user, betting_period):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+200",
        },
    )
    data = resp.get_json()

    assert data["success"] is True
    assert data["new_balance"] == 900.0

    bet = db.session.query(Bet).first()
    assert bet.potential_win == 200.0
    assert bet.odds == "+200"
    assert bet.amount == 100.0
    assert bet.status == "pending"


def test_place_bet_negative_odds(logged_in_client, user, betting_period):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 150,
            "owner": "Player B",
            "odds": "-150",
        },
    )
    data = resp.get_json()

    assert data["success"] is True
    bet = db.session.query(Bet).first()
    assert bet.potential_win == 100.0


def test_place_bet_insufficient_balance(logged_in_client, user, betting_period):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 1500,
            "owner": "Player A",
            "odds": "+100",
        },
    )
    data = resp.get_json()

    assert data["success"] is False
    assert "Insufficient" in data["error"]

    db.session.refresh(user)
    assert user.account_balance == 1000.0


def test_place_bet_invalid_amount(logged_in_client, user, betting_period):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 0,
            "owner": "Player A",
            "odds": "+100",
        },
    )
    data = resp.get_json()

    assert data["success"] is False
    assert "Invalid" in data["error"]


def test_place_bet_creates_weekly_stats(logged_in_client, user, betting_period):
    logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+100",
        },
    )

    stat = db.session.query(WeeklyStats).filter_by(user_id=user.id).first()
    assert stat is not None
    assert stat.starting_balance == 1000.0
    assert stat.bets_placed == 1
    assert stat.active_bets_amount == 100.0


def test_place_bet_updates_existing_weekly_stats(logged_in_client, user, betting_period):
    logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+100",
        },
    )
    logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "lowest_scorer",
            "amount": 50,
            "owner": "Player B",
            "odds": "+200",
        },
    )

    stat = db.session.query(WeeklyStats).filter_by(user_id=user.id).first()
    assert stat.bets_placed == 2
    assert stat.active_bets_amount == 150.0


def test_place_bet_locked_period(logged_in_client, user, db_session):
    period = BettingPeriod(
        week=10,
        lock_time=datetime.now(UTC) - timedelta(hours=1),
        is_locked=True,
        is_settled=False,
    )
    db_session.session.add(period)
    db_session.session.commit()

    resp = logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+100",
        },
    )
    data = resp.get_json()

    assert data["success"] is False
    assert "locked" in data["error"].lower()
    assert db.session.query(Bet).count() == 0


def test_remove_bet_refunds_balance(logged_in_client, user, betting_period):
    logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+100",
        },
    )

    bet = db.session.query(Bet).first()
    resp = logged_in_client.delete(f"/api/remove_bet/{bet.id}")
    data = resp.get_json()

    assert data["success"] is True
    assert data["new_balance"] == 1000.0

    assert db.session.query(Bet).count() == 0

    stat = db.session.query(WeeklyStats).filter_by(user_id=user.id).first()
    assert stat.bets_placed == 0
    assert stat.active_bets_amount == 0.0


def test_remove_bet_locked_period(logged_in_client, user, db_session):
    period = BettingPeriod(
        week=10,
        lock_time=datetime.now(UTC) + timedelta(days=7),
        is_locked=False,
        is_settled=False,
    )
    db_session.session.add(period)
    db_session.session.commit()

    logged_in_client.post(
        "/api/place_bet",
        json={
            "bet_type": "highest_scorer",
            "amount": 100,
            "owner": "Player A",
            "odds": "+100",
        },
    )

    bet = db.session.query(Bet).first()

    # Lock the period
    period.is_locked = True
    period.lock_time = datetime.now(UTC) - timedelta(hours=1)
    db_session.session.commit()

    resp = logged_in_client.delete(f"/api/remove_bet/{bet.id}")
    data = resp.get_json()

    assert data["success"] is False
    assert db.session.query(Bet).count() == 1


def test_place_team_ou_bet(logged_in_client, user, betting_period, seeded_analytics):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={"bet_type": "team_ou", "amount": 50, "team_idx": 0, "choice": "over"},
    )
    data = resp.get_json()

    assert data["success"] is True
    assert data["new_balance"] == 950.0

    bet = db.session.query(Bet).first()
    assert bet.bet_type == "team_ou"
    assert "O/U" in bet.description
    assert bet.odds == "EVEN"


def test_place_moneyline_bet(logged_in_client, user, betting_period, seeded_analytics):
    resp = logged_in_client.post(
        "/api/place_bet",
        json={"bet_type": "moneyline", "amount": 100, "matchup_idx": 0, "team": "team1"},
    )
    data = resp.get_json()

    assert data["success"] is True

    bet = db.session.query(Bet).first()
    assert bet.bet_type == "moneyline"
    assert bet.odds == "-150"
