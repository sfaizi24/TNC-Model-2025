import logging
import os

from dotenv import load_dotenv
from flask import Flask, session
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__,
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.environ["SECRET_KEY"]

if os.environ.get("FLASK_ENV") == "production":
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}
app.config["WTF_CSRF_CHECK_DEFAULT"] = False

# Extensions
from extensions import csrf

csrf.init_app(app)

from database import db

db.init_app(app)

# Database setup
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    from migrations import run_schema_migrations
    run_schema_migrations()
    logging.info("Schema migrations completed")

# Auth
from auth import auth_bp, google_bp, login_manager

login_manager.init_app(app)
app.register_blueprint(google_bp, url_prefix="/auth")
app.register_blueprint(auth_bp)

# Route blueprints
from routes.account import account_bp
from routes.admin import admin_bp
from routes.betting import betting_bp
from routes.odds import odds_bp
from routes.pages import pages_bp

app.register_blueprint(pages_bp)
app.register_blueprint(account_bp)
app.register_blueprint(odds_bp)
app.register_blueprint(betting_bp)
app.register_blueprint(admin_bp)


@app.before_request
def make_session_permanent():
    session.permanent = True


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
