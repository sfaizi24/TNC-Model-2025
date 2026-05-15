import logging
from itertools import groupby

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..database import db
from ..extensions import csrf

account_bp = Blueprint("account", __name__)


@account_bp.route("/account")
@login_required
def account():
    from ..models import Bet, WeeklyStats

    bets = (
        db.session.query(Bet)
        .filter(Bet.user_id == current_user.id)
        .order_by(Bet.week.desc(), Bet.created_at.desc())
        .all()
    )
    bets_by_week = [(week, list(group)) for week, group in groupby(bets, key=lambda b: b.week)]

    weekly_pnl = (
        db.session.query(WeeklyStats)
        .filter(WeeklyStats.user_id == current_user.id)
        .order_by(WeeklyStats.week.desc())
        .all()
    )

    return render_template(
        "account.html",
        user=current_user,
        bets_by_week=bets_by_week,
        weekly_pnl=weekly_pnl,
    )


@account_bp.route("/account/update-profile", methods=["POST"])
@login_required
def update_profile():
    csrf.protect()
    try:
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if len(first_name) > 100:
            flash("First name must be 100 characters or less.", "error")
            return redirect(url_for("account.account"))

        if len(last_name) > 100:
            flash("Last name must be 100 characters or less.", "error")
            return redirect(url_for("account.account"))

        current_user.first_name = first_name if first_name else None
        current_user.last_name = last_name if last_name else None

        db.session.commit()

        flash("Profile updated successfully!", "success")

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile: {e}")
        flash("An error occurred while updating your profile. Please try again.", "error")

    return redirect(url_for("account.account"))
