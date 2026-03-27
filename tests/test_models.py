from datetime import UTC

import pytest
from sqlalchemy.exc import IntegrityError

from models import Bet, BettingPeriod, User, WeeklyStats


def test_user_defaults(db_session):
    user = User(id="u1")
    db_session.session.add(user)
    db_session.session.commit()

    assert user.account_balance == 1000.0
    assert user.total_pnl == 0.0
    assert user.is_admin is False
    assert user.created_at is not None


def test_bet_defaults(db_session, user):
    bet = Bet(
        user_id=user.id,
        bet_type="moneyline",
        description="Test bet",
        amount=50.0,
        odds="+100",
        potential_win=50.0,
    )
    db_session.session.add(bet)
    db_session.session.commit()

    assert bet.status == "pending"
    assert bet.result == 0.0


def test_betting_period_defaults(db_session):
    from datetime import datetime

    period = BettingPeriod(week=1, lock_time=datetime.now(UTC))
    db_session.session.add(period)
    db_session.session.commit()

    assert period.is_locked is False
    assert period.is_settled is False


def test_weekly_stats_unique_constraint(db_session, user):
    stat1 = WeeklyStats(
        user_id=user.id,
        week=10,
        starting_balance=1000.0,
        ending_balance=900.0,
        pnl=-100.0,
    )
    db_session.session.add(stat1)
    db_session.session.commit()

    stat2 = WeeklyStats(
        user_id=user.id,
        week=10,
        starting_balance=1000.0,
        ending_balance=800.0,
        pnl=-200.0,
    )
    db_session.session.add(stat2)

    with pytest.raises(IntegrityError):
        db_session.session.commit()


def test_user_bets_relationship(db_session, user):
    bet = Bet(
        user_id=user.id,
        bet_type="moneyline",
        description="Test bet",
        amount=50.0,
        odds="+100",
        potential_win=50.0,
    )
    db_session.session.add(bet)
    db_session.session.commit()

    db_session.session.refresh(user)
    assert len(user.bets) == 1
    assert user.bets[0].description == "Test bet"
