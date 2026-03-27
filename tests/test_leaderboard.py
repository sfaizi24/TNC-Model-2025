from models import Bet, BettingPeriod, User, WeeklyStats


def _seed_leaderboard_data(db_session):
    """Create 3 users with bets and weekly stats for leaderboard testing."""
    users = [
        User(
            id="lb-1", username="alice", email="alice@test.com", first_name="Alice", last_name="Smith", total_pnl=500.0
        ),
        User(id="lb-2", username="bob", email="bob@test.com", first_name="Bob", last_name="Jones", total_pnl=200.0),
        User(
            id="lb-3", username="carol", email="carol@test.com", first_name="Carol", last_name="Davis", total_pnl=-300.0
        ),
    ]
    db_session.session.add_all(users)

    period = BettingPeriod(
        week=10,
        lock_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        is_locked=True,
        is_settled=False,
    )
    db_session.session.add(period)

    bets = [
        # Won bets with different odds
        Bet(
            user_id="lb-1",
            bet_type="highest_scorer",
            description="Alice bet",
            amount=100.0,
            odds="+300",
            potential_win=300.0,
            status="won",
            result=300.0,
            week=10,
        ),
        Bet(
            user_id="lb-2",
            bet_type="moneyline",
            description="Bob bet",
            amount=200.0,
            odds="+150",
            potential_win=300.0,
            status="won",
            result=300.0,
            week=10,
        ),
        Bet(
            user_id="lb-1",
            bet_type="highest_scorer",
            description="Alice bet 2",
            amount=50.0,
            odds="-110",
            potential_win=45.45,
            status="won",
            result=45.45,
            week=10,
        ),
        # Lost bets
        Bet(
            user_id="lb-3",
            bet_type="moneyline",
            description="Carol loss 1",
            amount=400.0,
            odds="+100",
            potential_win=400.0,
            status="lost",
            result=-400.0,
            week=10,
        ),
        Bet(
            user_id="lb-2",
            bet_type="team_ou",
            description="Bob loss",
            amount=100.0,
            odds="EVEN",
            potential_win=100.0,
            status="lost",
            result=-100.0,
            week=10,
        ),
        # Pending bet (should not appear in settled stats)
        Bet(
            user_id="lb-1",
            bet_type="highest_scorer",
            description="Alice pending",
            amount=50.0,
            odds="+200",
            potential_win=100.0,
            status="pending",
            result=0.0,
            week=10,
        ),
    ]
    db_session.session.add_all(bets)

    stats = [
        WeeklyStats(
            user_id="lb-1",
            week=10,
            starting_balance=1000.0,
            ending_balance=1295.45,
            pnl=295.45,
            settled_pnl=345.45,
            bets_placed=3,
            bets_won=2,
        ),
        WeeklyStats(
            user_id="lb-2",
            week=10,
            starting_balance=1000.0,
            ending_balance=1200.0,
            pnl=200.0,
            settled_pnl=200.0,
            bets_placed=2,
            bets_won=1,
        ),
        WeeklyStats(
            user_id="lb-3",
            week=10,
            starting_balance=1000.0,
            ending_balance=600.0,
            pnl=-400.0,
            settled_pnl=-400.0,
            bets_placed=1,
            bets_won=0,
        ),
    ]
    db_session.session.add_all(stats)
    db_session.session.commit()


def test_alltime_top_ranking(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    top = context["alltime_top"]

    assert len(top) == 3
    assert top[0].total_pnl == 500.0  # Alice
    assert top[1].total_pnl == 200.0  # Bob
    assert top[2].total_pnl == -300.0  # Carol


def test_alltime_bottom_ranking(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    bottom = context["alltime_bottom"]

    assert len(bottom) == 2
    assert bottom[0].total_pnl == -300.0  # Carol (lowest)
    assert bottom[1].total_pnl == 200.0  # Bob


def test_weekly_top_bottom(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard?week=10")

    context = captured_templates[0][1]
    weekly_top = context["weekly_top"]
    weekly_bottom = context["weekly_bottom"]

    assert len(weekly_top) == 3
    assert weekly_top[0].settled_pnl == 345.45  # Alice
    assert weekly_top[1].settled_pnl == 200.0  # Bob

    assert len(weekly_bottom) == 2
    assert weekly_bottom[0].settled_pnl == -400.0  # Carol


def test_best_odds_bet(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    best = context["best_odds_bet"]

    assert best is not None
    # +300 has the highest numeric odds value among won bets
    assert best.odds == "+300"


def test_most_money_won(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    most = context["most_money_won"]

    assert most is not None
    # Alice's +300 bet: result=300, Bob's +150 bet: result=300
    # Both have result=300, either could be first — just verify it's 300
    assert most.result == 300.0


def test_worst_odds_bet(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    worst = context["worst_odds_bet"]

    assert worst is not None
    # EVEN maps to 0 via REPLACE, +100 maps to 100 — EVEN is lowest
    assert worst.odds == "EVEN"


def test_biggest_loss(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)
    client.get("/leaderboard")

    context = captured_templates[0][1]
    biggest = context["biggest_loss"]

    assert biggest is not None
    assert biggest.amount == 400.0  # Carol's $400 lost bet


def test_popular_bet_stats(client, db_session, captured_templates):
    _seed_leaderboard_data(db_session)

    # Add extra bets with the same description to test group-by aggregation
    from models import Bet

    extra_bets = [
        Bet(
            user_id="lb-2",
            bet_type="highest_scorer",
            description="Alice bet",
            amount=75.0,
            odds="+200",
            potential_win=150.0,
            status="lost",
            result=-75.0,
            week=10,
        ),
        Bet(
            user_id="lb-3",
            bet_type="highest_scorer",
            description="Alice bet",
            amount=50.0,
            odds="+200",
            potential_win=100.0,
            status="pending",
            result=0.0,
            week=10,
        ),
    ]
    db_session.session.add_all(extra_bets)
    db_session.session.commit()

    client.get("/leaderboard")

    context = captured_templates[0][1]
    popular = context["popular_highest"]

    assert popular is not None
    # "Alice bet" appears 3 times: 1 won + 1 lost + 1 pending
    assert popular.count == 3
    assert popular.wins == 1
    assert popular.losses == 1
    assert popular.pending == 1


def test_empty_leaderboard(client, db_session, captured_templates):
    # No data seeded — just a betting period so get_current_week works
    from datetime import UTC, datetime

    period = BettingPeriod(
        week=10,
        lock_time=datetime.now(UTC),
        is_settled=False,
    )
    db_session.session.add(period)
    db_session.session.commit()

    resp = client.get("/leaderboard")
    assert resp.status_code == 200
