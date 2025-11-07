from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session, flash, jsonify
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import sys
import sqlite3
import json

logging.basicConfig(level=logging.DEBUG)

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

LEAGUE_DB_PATH = 'backend/data/databases/league.db'
PROJECTIONS_DB_PATH = 'backend/data/databases/projections.db'

# Initialize database
from database import db
db.init_app(app)

# Create tables
with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")

# Import Replit Auth
from replit_auth import login_manager, make_replit_blueprint, require_login
from flask_login import current_user

# Initialize login manager
login_manager.init_app(app)

# Register Replit Auth blueprint
app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('betting'))
    return render_template('login.html')

@app.route('/analytics')
@require_login
def analytics():
    return render_template('analytics.html', user=current_user)

@app.route('/account')
@require_login
def account():
    from models import Bet, WeeklyStats
    bets = db.session.query(Bet).filter_by(user_id=current_user.id).order_by(Bet.created_at.desc()).limit(20).all()
    weekly_stats = db.session.query(WeeklyStats).filter_by(user_id=current_user.id).all()
    return render_template('account.html', user=current_user, bets=bets, weekly_stats=weekly_stats)

@app.route('/betting')
@require_login
def betting():
    return render_template('betting.html', user=current_user)

ODDS_DB_PATH = 'backend/data/databases/odds.db'

@app.route('/api/matchups')
@require_login
def get_matchups():
    try:
        # Get team ID to owner name mapping from league database
        league_conn = sqlite3.connect(LEAGUE_DB_PATH)
        league_conn.row_factory = sqlite3.Row
        league_cursor = league_conn.cursor()
        
        league_cursor.execute("""
            SELECT r.roster_id, u.display_name, u.username
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
        """)
        
        team_mapping = {}
        for row in league_cursor.fetchall():
            owner_name = row['display_name'] or row['username'] or f"Team {row['roster_id']}"
            team_mapping[row['roster_id']] = owner_name
        
        league_conn.close()
        
        # Get matchup odds
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM betting_odds_matchup_ml
            WHERE week = 10
            ORDER BY matchup
        """)
        
        matchups = []
        for row in cursor.fetchall():
            team1_owner = team_mapping.get(row['team1_id'], f"Team {row['team1_id']}")
            team2_owner = team_mapping.get(row['team2_id'], f"Team {row['team2_id']}")
            
            matchups.append({
                'matchup': f"{team1_owner} vs {team2_owner}",
                'original_matchup': row['matchup'],
                'team1_id': row['team1_id'],
                'team1_name': team1_owner,
                'team1_win_prob': row['team1_win_prob'],
                'team1_ml': row['team1_ml'],
                'team2_id': row['team2_id'],
                'team2_name': team2_owner,
                'team2_win_prob': row['team2_win_prob'],
                'team2_ml': row['team2_ml']
            })
        
        conn.close()
        return jsonify(matchups)
    except Exception as e:
        print(f"Error getting matchups: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/place_bet', methods=['POST'])
@require_login
def place_bet():
    from models import Bet, WeeklyStats
    from datetime import datetime
    
    data = request.get_json()
    matchup_idx = data.get('matchup_idx')
    team = data.get('team')
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid bet amount'})
    
    if current_user.account_balance < amount:
        return jsonify({'success': False, 'error': 'Insufficient balance'})
    
    try:
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM betting_odds_matchup_ml WHERE week = 10 ORDER BY matchup")
        matchups = cursor.fetchall()
        conn.close()
        
        if matchup_idx >= len(matchups):
            return jsonify({'success': False, 'error': 'Invalid matchup'})
        
        matchup = matchups[matchup_idx]
        
        if team == 'team1':
            team_name = matchup['team1_name']
            odds = matchup['team1_ml']
        elif team == 'team2':
            team_name = matchup['team2_name']
            odds = matchup['team2_ml']
        else:
            return jsonify({'success': False, 'error': 'Invalid team'})
        
        odds_num = int(odds)
        if odds_num > 0:
            potential_win = amount * (odds_num / 100)
        else:
            potential_win = amount * (100 / abs(odds_num))
        
        week = 10
        
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
        
        description = f"{matchup['matchup']}: {team_name} {odds}"
        
        bet = Bet(
            user_id=current_user.id,
            bet_type='moneyline',
            description=description,
            week=week,
            amount=amount,
            odds=odds,
            potential_win=potential_win,
            status='pending',
            created_at=datetime.now()
        )
        
        db.session.add(bet)
        
        weekly_stat.bets_placed += 1
        weekly_stat.ending_balance = current_user.account_balance
        weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
        
        db.session.commit()
        
        return jsonify({'success': True, 'new_balance': current_user.account_balance})
    
    except Exception as e:
        print(f"Error placing bet: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/my_bets')
@require_login
def get_my_bets():
    from models import Bet
    
    try:
        bets = db.session.query(Bet).filter_by(
            user_id=current_user.id,
            status='pending'
        ).order_by(Bet.created_at.desc()).all()
        
        bets_data = []
        for bet in bets:
            bets_data.append({
                'id': bet.id,
                'description': bet.description,
                'amount': bet.amount,
                'odds': bet.odds,
                'potential_win': bet.potential_win,
                'status': bet.status,
                'week': bet.week
            })
        
        return jsonify(bets_data)
    
    except Exception as e:
        print(f"Error getting bets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/remove_bet/<int:bet_id>', methods=['DELETE'])
@require_login
def remove_bet(bet_id):
    from models import Bet, WeeklyStats
    
    try:
        bet = db.session.query(Bet).filter_by(
            id=bet_id,
            user_id=current_user.id,
            status='pending'
        ).first()
        
        if not bet:
            return jsonify({'success': False, 'error': 'Bet not found'})
        
        current_user.account_balance += bet.amount
        
        weekly_stat = db.session.query(WeeklyStats).filter_by(
            user_id=current_user.id,
            week=bet.week
        ).first()
        
        if weekly_stat:
            weekly_stat.bets_placed -= 1
            weekly_stat.ending_balance = current_user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
        
        db.session.delete(bet)
        db.session.commit()
        
        return jsonify({'success': True, 'new_balance': current_user.account_balance})
    
    except Exception as e:
        print(f"Error removing bet: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('frontend/static', filename)

@app.route('/api/teams')
@require_login
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
@require_login
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
