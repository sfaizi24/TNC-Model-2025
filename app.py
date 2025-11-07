from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session, flash, jsonify
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import sys
import sqlite3
import json

logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.environ.get("SESSION_SECRET", os.environ.get('SECRET_KEY', 'tncasino-secret-key-change-in-production'))
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app, model_class=Base)

LEAGUE_DB_PATH = 'backend/data/databases/league.db'
PROJECTIONS_DB_PATH = 'backend/data/databases/projections.db'

with app.app_context():
    import models
    db.create_all()
    logging.info("Database tables created")

from flask_login import LoginManager, current_user, login_user, logout_user, login_required

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('betting'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('betting'))
    
    if request.method == 'POST':
        from models import User
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.session.query(User).filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('betting'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('betting'))
    
    if request.method == 'POST':
        from models import User
        email = request.form.get('email')
        password = request.form.get('password')
        
        if db.session.query(User).filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('login.html')
        
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('betting'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html', user=current_user)

@app.route('/account')
@login_required
def account():
    from models import Bet, WeeklyStats
    bets = db.session.query(Bet).filter_by(user_id=current_user.id).order_by(Bet.created_at.desc()).limit(20).all()
    weekly_stats = db.session.query(WeeklyStats).filter_by(user_id=current_user.id).all()
    return render_template('account.html', user=current_user, bets=bets, weekly_stats=weekly_stats)

@app.route('/betting')
@login_required
def betting():
    return render_template('betting.html', user=current_user)

@app.route('/api/place_bet', methods=['POST'])
@login_required
def place_bet():
    from models import Bet, WeeklyStats
    from datetime import datetime
    
    data = request.get_json()
    amount = float(data['amount'])
    
    if current_user.account_balance < amount:
        return jsonify({'success': False, 'message': 'Insufficient balance'})
    
    week = data.get('week', 10)
    
    weekly_stat = db.session.query(WeeklyStats).filter_by(
        user_id=current_user.id, week=week
    ).first()
    
    if not weekly_stat:
        weekly_stat = WeeklyStats(
            user_id=current_user.id,
            week=week,
            starting_balance=current_user.account_balance,
            ending_balance=current_user.account_balance,
            pnl=0.0,
            bets_placed=0,
            bets_won=0
        )
        db.session.add(weekly_stat)
    
    current_user.account_balance -= amount
    
    bet = Bet(
        user_id=current_user.id,
        bet_type=data['bet_type'],
        description=data['description'],
        week=week,
        amount=amount,
        odds=data['odds'],
        potential_win=float(data['potential_win']),
        status='pending',
        created_at=datetime.now()
    )
    
    db.session.add(bet)
    
    weekly_stat.bets_placed += 1
    weekly_stat.ending_balance = current_user.account_balance
    weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
    
    db.session.commit()
    
    return jsonify({'success': True, 'balance': current_user.account_balance})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('frontend/static', filename)

@app.route('/api/teams')
@login_required
def get_teams():
    try:
        conn = sqlite3.connect(LEAGUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.username, u.display_name
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            ORDER BY r.roster_id
        """)
        
        teams = []
        for row in cursor.fetchall():
            owner = row['username'] or row['display_name']
            if owner:
                teams.append(owner)
        
        conn.close()
        return jsonify({'teams': teams})
    except Exception as e:
        print(f"Error getting teams: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'teams': []})

@app.route('/api/team_players')
@login_required
def get_team_players():
    team_owner = request.args.get('team')
    if not team_owner:
        return jsonify({'error': 'Team parameter required'}), 400
    
    try:
        league_conn = sqlite3.connect(LEAGUE_DB_PATH)
        league_conn.row_factory = sqlite3.Row
        league_cursor = league_conn.cursor()
        
        league_cursor.execute("""
            SELECT r.starters, r.roster_id
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE u.username = ? OR u.display_name = ?
        """, (team_owner, team_owner))
        
        roster = league_cursor.fetchone()
        if not roster or not roster['starters']:
            league_conn.close()
            return jsonify({'players': []})
        
        starters_str = roster['starters']
        player_ids = json.loads(starters_str.replace("'", '"'))
        
        league_conn.close()
        
        proj_conn = sqlite3.connect(PROJECTIONS_DB_PATH)
        proj_conn.row_factory = sqlite3.Row
        proj_cursor = proj_conn.cursor()
        
        placeholders = ','.join('?' * len(player_ids))
        proj_cursor.execute(f"""
            SELECT player_name, position, mu, sleeper_player_id
            FROM player_week_stats
            WHERE sleeper_player_id IN ({placeholders})
            AND week = 10
            ORDER BY mu DESC
        """, player_ids)
        
        players = []
        for row in proj_cursor.fetchall():
            name_parts = row['player_name'].split(' ', 1)
            first_name = name_parts[0] if len(name_parts) > 0 else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            players.append({
                'player_first_name': first_name,
                'player_last_name': last_name,
                'position': row['position'],
                'mu': float(row['mu'])
            })
        
        proj_conn.close()
        return jsonify({'players': players})
        
    except Exception as e:
        print(f"Error getting team players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'players': []})

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
