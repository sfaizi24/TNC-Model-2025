from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from ..database import db
from .helpers import admin_required, friendly_description

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", user=current_user)


@admin_bp.route("/api/admin/betting_periods", methods=["GET"])
@admin_required
def get_betting_periods():
    from ..models import BettingPeriod

    try:
        periods = db.session.query(BettingPeriod).order_by(BettingPeriod.week.desc()).all()

        periods_data = []
        for period in periods:
            periods_data.append(
                {
                    "id": period.id,
                    "week": period.week,
                    "lock_time": period.lock_time.strftime("%Y-%m-%d %I:%M %p UTC"),
                    "is_locked": period.is_locked,
                    "is_settled": period.is_settled,
                }
            )

        return jsonify(periods_data)
    except Exception as e:
        print(f"Error getting betting periods: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@admin_bp.route("/api/admin/set_betting_period", methods=["POST"])
@admin_required
def set_betting_period():
    from ..models import BettingPeriod

    data = request.get_json()
    week = data.get("week")
    lock_time_str = data.get("lock_time")

    if not week or not lock_time_str:
        return jsonify({"success": False, "error": "Week and lock time required"})

    try:
        lock_time = datetime.strptime(lock_time_str, "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)

        period = db.session.query(BettingPeriod).filter_by(week=week).first()

        if period:
            period.lock_time = lock_time
            period.is_locked = False
        else:
            period = BettingPeriod(week=week, lock_time=lock_time, is_locked=False, is_settled=False)
            db.session.add(period)

        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        print(f"Error setting betting period: {e}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/api/admin/pending_bets", methods=["GET"])
@admin_required
def get_pending_bets():
    from ..models import Bet

    week = request.args.get("week", 10, type=int)

    try:
        bets = db.session.query(Bet).filter_by(week=week, status="pending").all()

        bets_data = []
        for bet in bets:
            bets_data.append(
                {
                    "id": bet.id,
                    "user_id": bet.user_id,
                    "description": friendly_description(bet.description),
                    "amount": bet.amount,
                    "odds": bet.odds,
                    "potential_win": bet.potential_win,
                    "bet_type": bet.bet_type,
                }
            )

        return jsonify(bets_data)
    except Exception as e:
        print(f"Error getting pending bets: {e}")
        import traceback

        traceback.print_exc()
        return jsonify([])


@admin_bp.route("/api/admin/settle_bet", methods=["POST"])
@admin_required
def settle_bet():
    from ..models import Bet, User, WeeklyStats

    data = request.get_json()
    bet_id = data.get("bet_id")
    won = data.get("won", False)

    if not bet_id:
        return jsonify({"success": False, "error": "Bet ID required"})

    try:
        bet = db.session.query(Bet).filter_by(id=bet_id).first()

        if not bet:
            return jsonify({"success": False, "error": "Bet not found"})

        if bet.status != "pending":
            return jsonify({"success": False, "error": "Bet already settled"})

        user = db.session.query(User).filter_by(id=bet.user_id).first()

        if not user:
            return jsonify({"success": False, "error": "User not found"})

        if won:
            payout = bet.amount + bet.potential_win
            bet.result = bet.potential_win
            bet.status = "won"
        else:
            payout = 0
            bet.result = -bet.amount
            bet.status = "lost"

        user.account_balance += payout
        user.total_pnl += bet.result

        bet.settled_at = datetime.now(UTC)

        weekly_stat = db.session.query(WeeklyStats).filter_by(user_id=bet.user_id, week=bet.week).first()

        if weekly_stat:
            weekly_stat.active_bets_amount -= bet.amount
            weekly_stat.settled_pnl += bet.result
            weekly_stat.ending_balance = user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
            if won:
                weekly_stat.bets_won += 1

        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        print(f"Error settling bet: {e}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/api/admin/settle_week", methods=["POST"])
@admin_required
def settle_week():
    from ..models import BettingPeriod

    data = request.get_json()
    week = data.get("week")

    if not week:
        return jsonify({"success": False, "error": "Week required"})

    try:
        period = db.session.query(BettingPeriod).filter_by(week=week).first()

        if not period:
            return jsonify({"success": False, "error": "Betting period not found"})

        period.is_settled = True

        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        print(f"Error settling week: {e}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


@admin_bp.route("/api/admin/unlock_period", methods=["POST"])
@admin_required
def unlock_period():
    from ..models import BettingPeriod

    data = request.get_json()
    week = data.get("week")

    print(f"[UNLOCK] Request received for week: {week}")
    print(f"[UNLOCK] Request data: {data}")
    print(f"[UNLOCK] Current user: {current_user.email if current_user.is_authenticated else 'Not authenticated'}")
    print(f"[UNLOCK] Is admin: {getattr(current_user, 'is_admin', False)}")

    if not week:
        print("[UNLOCK] Error: Week not provided")
        return jsonify({"success": False, "error": "Week required"})

    try:
        period = db.session.query(BettingPeriod).filter_by(week=week).first()

        if not period:
            print(f"[UNLOCK] Error: Betting period not found for week {week}")
            return jsonify({"success": False, "error": "Betting period not found"})

        print(
            f"[UNLOCK] Found period: week={period.week}, is_locked={period.is_locked}, is_settled={period.is_settled}, lock_time={period.lock_time}"
        )

        period.is_locked = False
        new_lock_time = datetime.now(UTC) + timedelta(days=7)
        period.lock_time = new_lock_time

        db.session.commit()

        print(f"[UNLOCK] Successfully unlocked week {week}, new lock_time set to {new_lock_time}")

        return jsonify({"success": True})
    except Exception as e:
        print(f"[UNLOCK] Error unlocking period: {e}")
        import traceback

        traceback.print_exc()
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})
