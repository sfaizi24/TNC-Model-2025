from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session, flash, jsonify
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import sys
import sqlite3
import json
from datetime import datetime, timezone

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
def run_schema_migrations():
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        
        # Migrate datetime columns to timezone-aware (TIMESTAMPTZ)
        logging.info("Checking and migrating datetime columns to timezone-aware")
        with db.engine.connect() as conn:
            # Convert all TIMESTAMP WITHOUT TIME ZONE to TIMESTAMP WITH TIME ZONE
            # These columns assume existing values are in UTC
            datetime_migrations = [
                ('users', 'created_at'),
                ('users', 'updated_at'),
                ('bets', 'created_at'),
                ('bets', 'settled_at'),
                ('weekly_stats', 'created_at'),
                ('betting_periods', 'lock_time'),
                ('betting_periods', 'created_at'),
                ('betting_periods', 'updated_at'),
            ]
            
            for table, column in datetime_migrations:
                if table in inspector.get_table_names():
                    # Check if column is already TIMESTAMPTZ
                    result = conn.execute(text(f'''
                        SELECT data_type 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        AND column_name = '{column}'
                    ''')).first()
                    
                    if result and result[0] == 'timestamp without time zone':
                        try:
                            # Convert column to timezone-aware, treating existing values as UTC
                            conn.execute(text(f'''
                                ALTER TABLE {table} 
                                ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE 
                                USING {column} AT TIME ZONE 'UTC'
                            '''))
                            conn.commit()
                            logging.info(f"Converted {table}.{column} to TIMESTAMPTZ")
                        except Exception as col_error:
                            conn.rollback()
                            logging.error(f"Error converting {table}.{column}: {col_error}")
                    elif result and result[0] == 'timestamp with time zone':
                        logging.debug(f"{table}.{column} already TIMESTAMPTZ, skipping")
                    else:
                        logging.debug(f"{table}.{column} not found or unexpected type")
        
        if 'users' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            if 'is_admin' not in columns:
                logging.info("Adding is_admin column to users")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                logging.info("is_admin column added")
        
        if 'weekly_stats' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('weekly_stats')]
            
            if 'active_bets_amount' not in columns:
                logging.info("Adding active_bets_amount column to weekly_stats")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN active_bets_amount DOUBLE PRECISION DEFAULT 0.0'))
                    conn.execute(text('''
                        UPDATE weekly_stats ws
                        SET active_bets_amount = COALESCE((
                            SELECT SUM(b.amount)
                            FROM bets b
                            WHERE b.user_id = ws.user_id
                              AND b.week = ws.week
                              AND b.status = 'pending'
                        ), 0.0)
                    '''))
                    conn.commit()
                logging.info("active_bets_amount column added and backfilled")
            
            if 'settled_pnl' not in columns:
                logging.info("Adding settled_pnl column to weekly_stats")
                with db.engine.connect() as conn:
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN settled_pnl DOUBLE PRECISION DEFAULT 0.0'))
                    conn.execute(text('''
                        UPDATE weekly_stats ws
                        SET settled_pnl = COALESCE((
                            SELECT SUM(b.result)
                            FROM bets b
                            WHERE b.user_id = ws.user_id
                              AND b.week = ws.week
                              AND b.status IN ('won', 'lost')
                        ), 0.0)
                    '''))
                    conn.commit()
                logging.info("settled_pnl column added and backfilled")
    except Exception as e:
        logging.error(f"Migration error: {e}")
        import traceback
        traceback.print_exc()

with app.app_context():
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    run_schema_migrations()
    logging.info("Schema migrations completed")

# Import Replit Auth
from replit_auth import login_manager, make_replit_blueprint, require_login
from flask_login import current_user, login_required
from functools import wraps

# Initialize login manager
login_manager.init_app(app)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        if not getattr(current_user, 'is_admin', False):
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('betting'))
        return f(*args, **kwargs)
    return decorated_function

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
        
        week = get_current_week()
        cursor.execute("""
            SELECT * FROM betting_odds_matchup_ml
            WHERE week = ?
            ORDER BY matchup
        """, (week,))
        
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

@app.route('/api/team_performance')
@require_login
def get_team_performance():
    try:
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        week = get_current_week()
        cursor.execute("""
            SELECT * FROM betting_odds_team_ou
            WHERE week = ?
            ORDER BY owner
        """, (week,))
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'team_id': row['team_id'],
                'owner': row['owner'],
                'line': row['line'],
                'over_prob': row['over_prob'],
                'under_prob': row['under_prob']
            })
        
        conn.close()
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting team performance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/highest_scorer')
@require_login
def get_highest_scorer():
    try:
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        week = get_current_week()
        cursor.execute("""
            SELECT owner, probability, odds
            FROM betting_odds_highest_scorer
            WHERE week = ?
            ORDER BY probability DESC
        """, (week,))
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'owner': row['owner'],
                'win_prob': round(row['probability'] * 100, 1),
                'odds': row['odds']
            })
        
        conn.close()
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting highest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/lowest_scorer')
@require_login
def get_lowest_scorer():
    try:
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        week = get_current_week()
        cursor.execute("""
            SELECT owner, probability, odds
            FROM betting_odds_lowest_scorer
            WHERE week = ?
            ORDER BY probability DESC
        """, (week,))
        
        teams = []
        for row in cursor.fetchall():
            teams.append({
                'owner': row['owner'],
                'win_prob': round(row['probability'] * 100, 1),
                'odds': row['odds']
            })
        
        conn.close()
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting lowest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/lineup/<owner>')
@require_login
def get_lineup(owner):
    try:
        conn = sqlite3.connect(PROJECTIONS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Fetch lineup for the owner with proper slot ordering
        week = get_current_week()
        cursor.execute("""
            SELECT slot, player_name, position, mu
            FROM team_lineups
            WHERE owner = ? AND week = ? 
                AND slot IN ('QB', 'RB1', 'RB2', 'WR1', 'WR2', 'TE', 'FLEX', 'K', 'DEF')
            ORDER BY 
                CASE slot
                    WHEN 'QB' THEN 1
                    WHEN 'RB1' THEN 2
                    WHEN 'RB2' THEN 3
                    WHEN 'WR1' THEN 4
                    WHEN 'WR2' THEN 5
                    WHEN 'TE' THEN 6
                    WHEN 'FLEX' THEN 7
                    WHEN 'K' THEN 8
                    WHEN 'DEF' THEN 9
                    ELSE 10
                END
        """, (owner, week))
        
        lineup = []
        for row in cursor.fetchall():
            lineup.append({
                'slot': row['slot'],
                'player_name': row['player_name'],
                'position': row['position'],
                'projected_points': round(row['mu'], 1)
            })
        
        conn.close()
        return jsonify(lineup)
    except Exception as e:
        print(f"Error getting lineup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

def get_current_week():
    from models import BettingPeriod
    from datetime import datetime
    
    period = db.session.query(BettingPeriod).filter_by(is_settled=False).order_by(BettingPeriod.week.desc()).first()
    
    if period:
        return period.week
    
    return 10

def check_betting_period_lock(week):
    from models import BettingPeriod
    from datetime import datetime
    
    period = db.session.query(BettingPeriod).filter_by(week=week).first()
    
    if not period:
        return None
    
    if period.is_locked or datetime.now(timezone.utc) >= period.lock_time:
        if not period.is_locked:
            period.is_locked = True
            db.session.commit()
        return period.lock_time
    
    return None

@app.route('/api/place_bet', methods=['POST'])
@require_login
def place_bet():
    from models import Bet, WeeklyStats
    from datetime import datetime
    
    data = request.get_json()
    bet_type = data.get('bet_type', 'moneyline')
    amount = float(data.get('amount', 0))
    week = get_current_week()
    
    lock_time = check_betting_period_lock(week)
    if lock_time:
        return jsonify({
            'success': False,
            'error': f'Bets are locked as of {lock_time.strftime("%Y-%m-%d %I:%M %p UTC")}'
        })
    
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid bet amount'})
    
    if current_user.account_balance < amount:
        return jsonify({'success': False, 'error': 'Insufficient balance'})
    
    try:
        # Handle highest scorer bets
        if bet_type == 'highest_scorer':
            owner = data.get('owner')
            odds = data.get('odds')
            
            if not owner or not odds:
                return jsonify({'success': False, 'error': 'Missing required data'})
            
            # Calculate potential win
            odds_num = int(odds.replace('+', ''))
            if odds.startswith('+'):
                potential_win = amount * (odds_num / 100)
            else:
                potential_win = amount * (100 / abs(odds_num))
            
            weekly_stat = db.session.query(WeeklyStats).filter_by(
                user_id=current_user.id,
                week=week
            ).first()
            
            if not weekly_stat:
                weekly_stat = WeeklyStats(
                    user_id=current_user.id,
                    week=week,
                    starting_balance=current_user.account_balance,
                    ending_balance=current_user.account_balance,
                    pnl=0.0,
                    active_bets_amount=0.0,
                    settled_pnl=0.0,
                    bets_placed=0,
                    bets_won=0
                )
                db.session.add(weekly_stat)
            
            current_user.account_balance -= amount
            
            description = f"{owner}: Highest Scorer {odds}"
            
            bet = Bet(
                user_id=current_user.id,
                bet_type='highest_scorer',
                description=description,
                week=week,
                amount=amount,
                odds=odds,
                potential_win=potential_win,
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(bet)
            
            weekly_stat.bets_placed += 1
            weekly_stat.active_bets_amount += amount
            weekly_stat.ending_balance = current_user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
            
            db.session.commit()
            
            return jsonify({'success': True, 'new_balance': current_user.account_balance})
        
        # Handle lowest scorer bets
        if bet_type == 'lowest_scorer':
            owner = data.get('owner')
            odds = data.get('odds')
            
            if not owner or not odds:
                return jsonify({'success': False, 'error': 'Missing required data'})
            
            # Calculate potential win
            odds_num = int(odds.replace('+', ''))
            if odds.startswith('+'):
                potential_win = amount * (odds_num / 100)
            else:
                potential_win = amount * (100 / abs(odds_num))
            
            weekly_stat = db.session.query(WeeklyStats).filter_by(
                user_id=current_user.id,
                week=week
            ).first()
            
            if not weekly_stat:
                weekly_stat = WeeklyStats(
                    user_id=current_user.id,
                    week=week,
                    starting_balance=current_user.account_balance,
                    ending_balance=current_user.account_balance,
                    pnl=0.0,
                    active_bets_amount=0.0,
                    settled_pnl=0.0,
                    bets_placed=0,
                    bets_won=0
                )
                db.session.add(weekly_stat)
            
            current_user.account_balance -= amount
            
            description = f"{owner}: Lowest Scorer {odds}"
            
            bet = Bet(
                user_id=current_user.id,
                bet_type='lowest_scorer',
                description=description,
                week=week,
                amount=amount,
                odds=odds,
                potential_win=potential_win,
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(bet)
            
            weekly_stat.bets_placed += 1
            weekly_stat.active_bets_amount += amount
            weekly_stat.ending_balance = current_user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
            
            db.session.commit()
            
            return jsonify({'success': True, 'new_balance': current_user.account_balance})
        
        # Handle team over/under bets
        if bet_type == 'team_ou':
            team_idx = data.get('team_idx')
            choice = data.get('choice')  # 'over' or 'under'
            
            conn = sqlite3.connect(ODDS_DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM betting_odds_team_ou WHERE week = ? ORDER BY owner", (week,))
            teams = cursor.fetchall()
            conn.close()
            
            if team_idx >= len(teams):
                return jsonify({'success': False, 'error': 'Invalid team'})
            
            team_data = teams[team_idx]
            owner = team_data['owner']
            line = team_data['line']
            
            # Even money bet - win equals bet amount
            potential_win = amount
            
            weekly_stat = db.session.query(WeeklyStats).filter_by(
                user_id=current_user.id,
                week=week
            ).first()
            
            if not weekly_stat:
                weekly_stat = WeeklyStats(
                    user_id=current_user.id,
                    week=week,
                    starting_balance=current_user.account_balance,
                    ending_balance=current_user.account_balance,
                    pnl=0.0,
                    active_bets_amount=0.0,
                    settled_pnl=0.0,
                    bets_placed=0,
                    bets_won=0
                )
                db.session.add(weekly_stat)
            
            current_user.account_balance -= amount
            
            description = f"{owner} O/U {line:.1f}: {choice.capitalize()}"
            
            bet = Bet(
                user_id=current_user.id,
                bet_type='team_ou',
                description=description,
                week=week,
                amount=amount,
                odds='EVEN',
                potential_win=potential_win,
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(bet)
            
            weekly_stat.bets_placed += 1
            weekly_stat.active_bets_amount += amount
            weekly_stat.ending_balance = current_user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
            
            db.session.commit()
            
            return jsonify({'success': True, 'new_balance': current_user.account_balance})
        
        # Handle moneyline bets (original logic)
        matchup_idx = data.get('matchup_idx')
        team = data.get('team')
        
        # Get team owner mapping
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
        
        # Get matchups
        conn = sqlite3.connect(ODDS_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM betting_odds_matchup_ml WHERE week = ? ORDER BY matchup", (week,))
        matchups = cursor.fetchall()
        conn.close()
        
        if matchup_idx >= len(matchups):
            return jsonify({'success': False, 'error': 'Invalid matchup'})
        
        matchup = matchups[matchup_idx]
        
        team1_owner = team_mapping.get(matchup['team1_id'], f"Team {matchup['team1_id']}")
        team2_owner = team_mapping.get(matchup['team2_id'], f"Team {matchup['team2_id']}")
        matchup_display = f"{team1_owner} vs {team2_owner}"
        
        if team == 'team1':
            team_name = team1_owner
            odds = matchup['team1_ml']
        elif team == 'team2':
            team_name = team2_owner
            odds = matchup['team2_ml']
        else:
            return jsonify({'success': False, 'error': 'Invalid team'})
        
        odds_num = int(odds)
        if odds_num > 0:
            potential_win = amount * (odds_num / 100)
        else:
            potential_win = amount * (100 / abs(odds_num))
        
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
                active_bets_amount=0.0,
                settled_pnl=0.0,
                bets_placed=0,
                bets_won=0
            )
            db.session.add(weekly_stat)
        
        current_user.account_balance -= amount
        
        description = f"{matchup_display}: {team_name} {odds}"
        
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
        weekly_stat.active_bets_amount += amount
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
        
        lock_time = check_betting_period_lock(bet.week)
        if lock_time:
            return jsonify({
                'success': False,
                'error': f'Bets are locked as of {lock_time.strftime("%Y-%m-%d %I:%M %p UTC")}'
            })
        
        current_user.account_balance += bet.amount
        
        weekly_stat = db.session.query(WeeklyStats).filter_by(
            user_id=current_user.id,
            week=bet.week
        ).first()
        
        if weekly_stat:
            weekly_stat.bets_placed -= 1
            weekly_stat.active_bets_amount -= bet.amount
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
        
        week = get_current_week()
        placeholders = ','.join('?' * len(player_ids))
        proj_cursor.execute(f"""
            SELECT player_name, position, mu, sleeper_player_id
            FROM player_week_stats
            WHERE sleeper_player_id IN ({placeholders})
            AND week = ?
            ORDER BY mu DESC
        """, player_ids + [week])
        
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

@app.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', user=current_user)

@app.route('/api/admin/betting_periods', methods=['GET'])
@admin_required
def get_betting_periods():
    from models import BettingPeriod
    
    try:
        periods = db.session.query(BettingPeriod).order_by(BettingPeriod.week.desc()).all()
        
        periods_data = []
        for period in periods:
            periods_data.append({
                'id': period.id,
                'week': period.week,
                'lock_time': period.lock_time.strftime('%Y-%m-%d %I:%M %p UTC'),
                'is_locked': period.is_locked,
                'is_settled': period.is_settled
            })
        
        return jsonify(periods_data)
    except Exception as e:
        print(f"Error getting betting periods: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/admin/set_betting_period', methods=['POST'])
@admin_required
def set_betting_period():
    from models import BettingPeriod
    from datetime import datetime
    
    data = request.get_json()
    week = data.get('week')
    lock_time_str = data.get('lock_time')
    
    if not week or not lock_time_str:
        return jsonify({'success': False, 'error': 'Week and lock time required'})
    
    try:
        # Parse as naive datetime and convert to UTC
        lock_time = datetime.strptime(lock_time_str, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
        
        period = db.session.query(BettingPeriod).filter_by(week=week).first()
        
        if period:
            period.lock_time = lock_time
            period.is_locked = False
        else:
            period = BettingPeriod(week=week, lock_time=lock_time, is_locked=False, is_settled=False)
            db.session.add(period)
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error setting betting period: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/pending_bets', methods=['GET'])
@admin_required
def get_pending_bets():
    from models import Bet
    
    week = request.args.get('week', 10, type=int)
    
    try:
        bets = db.session.query(Bet).filter_by(week=week, status='pending').all()
        
        bets_data = []
        for bet in bets:
            bets_data.append({
                'id': bet.id,
                'user_id': bet.user_id,
                'description': bet.description,
                'amount': bet.amount,
                'odds': bet.odds,
                'potential_win': bet.potential_win,
                'bet_type': bet.bet_type
            })
        
        return jsonify(bets_data)
    except Exception as e:
        print(f"Error getting pending bets: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/admin/settle_bet', methods=['POST'])
@admin_required
def settle_bet():
    from models import Bet, WeeklyStats, User
    from datetime import datetime
    
    data = request.get_json()
    bet_id = data.get('bet_id')
    won = data.get('won', False)
    
    if not bet_id:
        return jsonify({'success': False, 'error': 'Bet ID required'})
    
    try:
        bet = db.session.query(Bet).filter_by(id=bet_id).first()
        
        if not bet:
            return jsonify({'success': False, 'error': 'Bet not found'})
        
        if bet.status != 'pending':
            return jsonify({'success': False, 'error': 'Bet already settled'})
        
        user = db.session.query(User).filter_by(id=bet.user_id).first()
        
        if won:
            payout = bet.amount + bet.potential_win
            bet.result = bet.potential_win
            bet.status = 'won'
        else:
            payout = 0
            bet.result = -bet.amount
            bet.status = 'lost'
        
        user.account_balance += payout
        user.total_pnl += bet.result
        
        bet.settled_at = datetime.now(timezone.utc)
        
        weekly_stat = db.session.query(WeeklyStats).filter_by(
            user_id=bet.user_id,
            week=bet.week
        ).first()
        
        if weekly_stat:
            weekly_stat.active_bets_amount -= bet.amount
            weekly_stat.settled_pnl += bet.result
            weekly_stat.ending_balance = user.account_balance
            weekly_stat.pnl = weekly_stat.ending_balance - weekly_stat.starting_balance
            if won:
                weekly_stat.bets_won += 1
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error settling bet: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/settle_week', methods=['POST'])
@admin_required
def settle_week():
    from models import BettingPeriod
    
    data = request.get_json()
    week = data.get('week')
    
    if not week:
        return jsonify({'success': False, 'error': 'Week required'})
    
    try:
        period = db.session.query(BettingPeriod).filter_by(week=week).first()
        
        if not period:
            return jsonify({'success': False, 'error': 'Betting period not found'})
        
        period.is_settled = True
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error settling week: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/unlock_period', methods=['POST'])
@admin_required
def unlock_period():
    from models import BettingPeriod
    
    data = request.get_json()
    week = data.get('week')
    
    if not week:
        return jsonify({'success': False, 'error': 'Week required'})
    
    try:
        period = db.session.query(BettingPeriod).filter_by(week=week).first()
        
        if not period:
            return jsonify({'success': False, 'error': 'Betting period not found'})
        
        period.is_locked = False
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error unlocking period: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
