import os
import re

from flask import Blueprint, redirect, render_template, send_from_directory, url_for
from flask_login import current_user

from routes.helpers import get_current_week

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return redirect(url_for("betting.betting"))


@pages_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("betting.betting"))
    return render_template("login.html")


@pages_bp.route("/about")
def about():
    return render_template("about.html")


@pages_bp.route("/analytics")
def analytics():
    images_dir = "backend/data/images"
    week = get_current_week()

    available_weeks = set()
    if os.path.exists(images_dir):
        for filename in os.listdir(images_dir):
            match = re.search(r"simulation_distributions_overlay_week_(\d+)\.png", filename)
            if match:
                available_weeks.add(int(match.group(1)))

    if available_weeks:
        if week not in available_weeks:
            week = max(available_weeks)

    return render_template(
        "analytics.html", user=current_user if current_user.is_authenticated else None, current_week=week
    )


@pages_bp.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("frontend/static", filename)


@pages_bp.route("/analytics-images/<path:filename>")
def serve_analytics_image(filename):
    from werkzeug.security import safe_join

    images_dir = "backend/data/images"
    safe_path = safe_join(images_dir, filename)

    if not safe_path or not os.path.exists(safe_path):
        return "Image not found", 404

    return send_from_directory(images_dir, filename, max_age=86400)
