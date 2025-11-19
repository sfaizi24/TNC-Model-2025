from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session, flash, jsonify
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import sys
import sqlite3
import json
import ast
from datetime import datetime, timezone, timedelta
from flask_wtf.csrf import CSRFProtect

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
app.config["WTF_CSRF_CHECK_DEFAULT"] = False

csrf = CSRFProtect(app)

LEAGUE_DB_PATH = 'backend/data/databases/league.db'
PROJECTIONS_DB_PATH = 'backend/data/databases/projections.db'

# Initialize database
from database import db
db.init_app(app)

# Create tables
def run_schema_migrations():
    try:
        from sqlalchemy import inspect, text
        
        # Helper to check if column exists
        def column_exists(inspector, table_name, column_name):
            if table_name not in inspector.get_table_names():
                return False
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
        
        # Detect database dialect
        dialect = db.engine.dialect.name
        logging.info(f"Running schema migrations for dialect: {dialect}")
        
        with db.engine.begin() as conn:
            inspector = inspect(db.engine)
            
            # Migrate datetime columns to timezone-aware (PostgreSQL only)
            # SQLite doesn't need this as it stores datetimes as TEXT/REAL
            if dialect == 'postgresql':
                logging.info("PostgreSQL detected: migrating datetime columns to timezone-aware")
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
                    if column_exists(inspector, table, column):
                        try:
                            result = conn.execute(text(f'''
                                SELECT data_type 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}' 
                                AND column_name = '{column}'
                            ''')).first()
                            
                            if result and result[0] == 'timestamp without time zone':
                                conn.execute(text(f'''
                                    ALTER TABLE {table} 
                                    ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE 
                                    USING {column} AT TIME ZONE 'UTC'
                                '''))
                                logging.info(f"Converted {table}.{column} to TIMESTAMPTZ")
                        except Exception as col_error:
                            logging.error(f"Error converting {table}.{column}: {col_error}")
            else:
                logging.info(f"{dialect} detected: skipping timezone migration (not needed)")
            
            # Add missing columns (all dialects)
            inspector = inspect(db.engine)
            
            if not column_exists(inspector, 'users', 'is_admin'):
                logging.info("Adding is_admin column to users")
                if dialect == 'postgresql':
                    conn.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE'))
                else:
                    conn.execute(text('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0'))
                logging.info("is_admin column added")
            
            if not column_exists(inspector, 'weekly_stats', 'active_bets_amount'):
                logging.info("Adding active_bets_amount column to weekly_stats")
                if dialect == 'postgresql':
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN active_bets_amount DOUBLE PRECISION DEFAULT 0.0'))
                else:
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN active_bets_amount REAL DEFAULT 0.0'))
                
                # Backfill values
                conn.execute(text('''
                    UPDATE weekly_stats
                    SET active_bets_amount = COALESCE((
                        SELECT SUM(b.amount)
                        FROM bets b
                        WHERE b.user_id = weekly_stats.user_id
                          AND b.week = weekly_stats.week
                          AND b.status = 'pending'
                    ), 0.0)
                '''))
                logging.info("active_bets_amount column added and backfilled")
            
            if not column_exists(inspector, 'weekly_stats', 'settled_pnl'):
                logging.info("Adding settled_pnl column to weekly_stats")
                if dialect == 'postgresql':
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN settled_pnl DOUBLE PRECISION DEFAULT 0.0'))
                else:
                    conn.execute(text('ALTER TABLE weekly_stats ADD COLUMN settled_pnl REAL DEFAULT 0.0'))
                
                # Backfill values
                conn.execute(text('''
                    UPDATE weekly_stats
                    SET settled_pnl = COALESCE((
                        SELECT SUM(b.result)
                        FROM bets b
                        WHERE b.user_id = weekly_stats.user_id
                          AND b.week = weekly_stats.week
                          AND b.status IN ('won', 'lost')
                    ), 0.0)
                '''))
                logging.info("settled_pnl column added and backfilled")
            
            logging.info("Schema migrations completed successfully")
            
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
    return redirect(url_for('betting'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/analytics')
def analytics():
    week = get_current_week()
    return render_template('analytics.html', user=current_user if current_user.is_authenticated else None, current_week=week)

@app.route('/account')
@require_login
def account():
    from models import Bet, WeeklyStats
    from sqlalchemy.orm import joinedload
    
    # Optimize queries by limiting and ordering properly
    bets = db.session.query(Bet).filter_by(user_id=current_user.id).order_by(Bet.created_at.desc()).limit(20).all()
    weekly_stats = db.session.query(WeeklyStats).filter_by(user_id=current_user.id).order_by(WeeklyStats.week.desc()).all()
    
    return render_template('account.html', user=current_user, bets=bets, weekly_stats=weekly_stats)

@app.route('/account/update-profile', methods=['POST'])
@require_login
def update_profile():
    csrf.protect()
    try:
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        if len(first_name) > 100:
            flash('First name must be 100 characters or less.', 'error')
            return redirect(url_for('account'))
        
        if len(last_name) > 100:
            flash('Last name must be 100 characters or less.', 'error')
            return redirect(url_for('account'))
        
        current_user.first_name = first_name if first_name else None
        current_user.last_name = last_name if last_name else None
        
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile: {e}")
        flash('An error occurred while updating your profile. Please try again.', 'error')
    
    return redirect(url_for('account'))

@app.route('/betting')
def betting():
    return render_template('betting.html', user=current_user if current_user.is_authenticated else None)

@app.route('/leaderboard')
def leaderboard():
    from models import Bet, WeeklyStats, User
    from sqlalchemy import func, desc, case, distinct
    
    current_week = get_current_week()
    selected_week = request.args.get('week', current_week, type=int)
    
    # Get available weeks for dropdown
    available_weeks = db.session.query(distinct(WeeklyStats.week))\
        .order_by(desc(WeeklyStats.week)).all()
    available_weeks = [w[0] for w in available_weeks]
    
    # All-Time Top 3 and Bottom 2 (only users with at least 1 bet)
    users_with_bets = db.session.query(Bet.user_id).group_by(Bet.user_id).subquery()
    
    alltime_top = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.total_pnl
    ).join(users_with_bets, User.id == users_with_bets.c.user_id)\
     .order_by(desc(User.total_pnl)).limit(3).all()
    
    alltime_bottom = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.total_pnl
    ).join(users_with_bets, User.id == users_with_bets.c.user_id)\
     .order_by(User.total_pnl.asc()).limit(2).all()
    
    # Weekly Top 3 and Bottom 2 (only users who placed a bet that week)
    weekly_top = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        WeeklyStats.settled_pnl
    ).join(WeeklyStats, User.id == WeeklyStats.user_id)\
     .filter(WeeklyStats.week == selected_week, WeeklyStats.bets_placed > 0)\
     .order_by(desc(WeeklyStats.settled_pnl))\
     .limit(3).all()
    
    weekly_bottom = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        WeeklyStats.settled_pnl
    ).join(WeeklyStats, User.id == WeeklyStats.user_id)\
     .filter(WeeklyStats.week == selected_week, WeeklyStats.bets_placed > 0)\
     .order_by(WeeklyStats.settled_pnl.asc())\
     .limit(2).all()
    
    # Best Bets - Highest odds that won (best odds = highest number like +637)
    # Convert odds to numeric for proper sorting: +637 > +200 > EVEN > -110
    # Aggregate bets with same user_id, description, odds, week
    from sqlalchemy import cast, Integer
    best_odds_bet = db.session.query(
        Bet.description,
        Bet.odds,
        func.sum(Bet.amount).label('amount'),
        func.sum(Bet.result).label('result'),
        User.first_name,
        User.last_name
    ).join(User, Bet.user_id == User.id)\
     .filter(Bet.status == 'won')\
     .group_by(Bet.user_id, Bet.description, Bet.odds, Bet.week, User.first_name, User.last_name)\
     .order_by(desc(cast(func.replace(func.replace(Bet.odds, '+', ''), 'EVEN', '0'), Integer))).first()
    
    # Most Money Won (biggest win result)
    # Aggregate bets with same user_id, description, odds, week
    most_money_won = db.session.query(
        Bet.description,
        Bet.odds,
        func.sum(Bet.amount).label('amount'),
        func.sum(Bet.result).label('result'),
        User.first_name,
        User.last_name
    ).join(User, Bet.user_id == User.id)\
     .filter(Bet.status == 'won')\
     .group_by(Bet.user_id, Bet.description, Bet.odds, Bet.week, User.first_name, User.last_name)\
     .order_by(desc(func.sum(Bet.result))).first()
    
    # Worst Bets - Worst odds that lost (worst odds = lowest number like -200)
    # Convert odds to numeric for proper sorting: -200 < -110 < EVEN < +200
    # Aggregate bets with same user_id, description, odds, week
    worst_odds_bet = db.session.query(
        Bet.description,
        Bet.odds,
        func.sum(Bet.amount).label('amount'),
        Bet.result,
        User.first_name,
        User.last_name
    ).join(User, Bet.user_id == User.id)\
     .filter(Bet.status == 'lost')\
     .group_by(Bet.user_id, Bet.description, Bet.odds, Bet.week, Bet.result, User.first_name, User.last_name)\
     .order_by(cast(func.replace(func.replace(Bet.odds, '+', ''), 'EVEN', '0'), Integer).asc()).first()
    
    # Most Money Lost on a single bet
    # Aggregate bets with same user_id, description, odds, week
    biggest_loss = db.session.query(
        Bet.description,
        Bet.odds,
        func.sum(Bet.amount).label('amount'),
        Bet.result,
        User.first_name,
        User.last_name
    ).join(User, Bet.user_id == User.id)\
     .filter(Bet.status == 'lost')\
     .group_by(Bet.user_id, Bet.description, Bet.odds, Bet.week, Bet.result, User.first_name, User.last_name)\
     .order_by(desc(func.sum(Bet.amount))).first()
    
    # Most Popular Bets with win/loss status and total money placed
    def get_popular_bet_with_stats(bet_type):
        result = db.session.query(
            Bet.description,
            func.count(Bet.id).label('count'),
            func.sum(case((Bet.status == 'won', 1), else_=0)).label('wins'),
            func.sum(case((Bet.status == 'lost', 1), else_=0)).label('losses'),
            func.sum(case((Bet.status == 'pending', 1), else_=0)).label('pending'),
            func.sum(Bet.amount).label('total_wagered')
        ).filter(Bet.bet_type == bet_type)\
         .group_by(Bet.description)\
         .order_by(desc('count'))\
         .first()
        return result
    
    popular_moneyline = get_popular_bet_with_stats('moneyline')
    popular_over_under = get_popular_bet_with_stats('team_ou')
    popular_highest = get_popular_bet_with_stats('highest_scorer')
    popular_lowest = get_popular_bet_with_stats('lowest_scorer')
    
    return render_template('leaderboard.html',
                         user=current_user if current_user.is_authenticated else None,
                         current_week=current_week,
                         selected_week=selected_week,
                         available_weeks=available_weeks,
                         weekly_top=weekly_top,
                         weekly_bottom=weekly_bottom,
                         alltime_top=alltime_top,
                         alltime_bottom=alltime_bottom,
                         best_odds_bet=best_odds_bet,
                         most_money_won=most_money_won,
                         worst_odds_bet=worst_odds_bet,
                         biggest_loss=biggest_loss,
                         popular_moneyline=popular_moneyline,
                         popular_over_under=popular_over_under,
                         popular_highest=popular_highest,
                         popular_lowest=popular_lowest)

ODDS_DB_PATH = 'backend/data/databases/odds.db'

@app.route('/api/matchups')
def get_matchups():
    try:
        team_mapping = {}
        week = get_current_week()
        
        # Get team ID to owner name mapping from league database
        with sqlite3.connect(LEAGUE_DB_PATH) as league_conn:
            league_conn.row_factory = sqlite3.Row
            league_cursor = league_conn.cursor()
            
            league_cursor.execute("""
                SELECT r.roster_id, u.display_name, u.username
                FROM rosters r
                LEFT JOIN users u ON r.owner_id = u.user_id
            """)
            
            for row in league_cursor.fetchall():
                owner_name = row['display_name'] or row['username'] or f"Team {row['roster_id']}"
                team_mapping[row['roster_id']] = owner_name
        
        # Get matchup odds
        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
        
        return jsonify(matchups)
    except Exception as e:
        print(f"Error getting matchups: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/team_performance')
def get_team_performance():
    try:
        week = get_current_week()
        
        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
        
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting team performance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/highest_scorer')
def get_highest_scorer():
    try:
        week = get_current_week()
        
        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
        
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting highest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/lowest_scorer')
def get_lowest_scorer():
    try:
        week = get_current_week()
        
        with sqlite3.connect(ODDS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
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
        
        return jsonify(teams)
    except Exception as e:
        print(f"Error getting lowest scorer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@app.route('/api/lineup/<owner>')
def get_lineup(owner):
    """Public endpoint - anyone can view team lineups for research/preview"""
    try:
        week = get_current_week()
        
        with sqlite3.connect(PROJECTIONS_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch lineup for the owner with proper slot ordering
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
        # Get or create WeeklyStats once for all bet types (optimization)
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
        
        # Handle highest scorer bets
        if bet_type == 'highest_scorer':
            owner = data.get('owner')
            odds = data.get('odds')
            
            if not owner or not odds:
                return jsonify({'success': False, 'error': 'Missing required data'})
            
            odds_num = int(odds.replace('+', ''))
            if odds.startswith('+'):
                potential_win = amount * (odds_num / 100)
            else:
                potential_win = amount * (100 / abs(odds_num))
            
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
            
            odds_num = int(odds.replace('+', ''))
            if odds.startswith('+'):
                potential_win = amount * (odds_num / 100)
            else:
                potential_win = amount * (100 / abs(odds_num))
            
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
            choice = data.get('choice')
            
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
            
            potential_win = amount
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
        
        # Handle moneyline bets
        matchup_idx = data.get('matchup_idx')
        team = data.get('team')
        
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
            created_at=datetime.now(timezone.utc)
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

@app.route('/analytics-images/<path:filename>')
def serve_analytics_image(filename):
    from werkzeug.security import safe_join
    import os
    
    images_dir = 'backend/data/images'
    safe_path = safe_join(images_dir, filename)
    
    if not safe_path or not os.path.exists(safe_path):
        return "Image not found", 404
    
    # Cache images for 24 hours since they change infrequently
    return send_from_directory(images_dir, filename, max_age=86400)

@app.route('/api/session-check')
def check_session():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.username})
    return jsonify({'authenticated': False}), 401

@app.route('/api/teams')
@require_login
def get_teams():
    try:
        conn = sqlite3.connect(LEAGUE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.roster_id, u.username, u.display_name
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            ORDER BY r.roster_id
        """)
        
        teams = []
        for row in cursor.fetchall():
            username = row['username']
            display_name = row['display_name']
            roster_id = row['roster_id']
            
            label = display_name or username or f"Team {roster_id}"
            slug = username or display_name
            
            if slug:
                teams.append({
                    'label': label,
                    'slug': slug,
                    'roster_id': roster_id
                })
        
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
            SELECT r.roster_id, r.starters, r.players
            FROM rosters r
            LEFT JOIN users u ON r.owner_id = u.user_id
            WHERE u.username = ? OR u.display_name = ?
        """, (team_owner, team_owner))
        
        roster = league_cursor.fetchone()
        if not roster:
            league_conn.close()
            return jsonify({'error': 'Team not found'}), 404
        
        roster_id = roster['roster_id']
        team_name = f"Team {roster_id}"
        
        league_cursor.execute("""
            SELECT sleeper_player_id, first_name, last_name, position, mu, var, starting_status
            FROM projections_rosters
            WHERE roster_id = ?
            ORDER BY 
                CASE position
                    WHEN 'QB' THEN 1
                    WHEN 'RB' THEN 2
                    WHEN 'WR' THEN 3
                    WHEN 'TE' THEN 4
                    WHEN 'K' THEN 5
                    WHEN 'DEF' THEN 6
                    ELSE 7
                END,
                mu DESC
        """, (roster_id,))
        
        starters = []
        bench = []
        
        for row in league_cursor.fetchall():
            player_data = {
                'player_first_name': row['first_name'] or '',
                'player_last_name': row['last_name'] or '',
                'position': row['position'],
                'mu': float(row['mu']) if row['mu'] is not None else None,
                'var': float(row['var']) if row['var'] is not None else None
            }
            
            if row['starting_status'] and str(row['starting_status']).strip():
                starters.append(player_data)
            else:
                bench.append(player_data)
        
        league_conn.close()
        
        bench.sort(key=lambda x: (
            {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'K': 5, 'DEF': 6}.get(x['position'], 7),
            -(x['mu'] if x['mu'] is not None else 0)
        ))
        
        return jsonify({'starters': starters, 'bench': bench})
        
    except Exception as e:
        print(f"Error getting team players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'starters': [], 'bench': []})

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
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
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
    
    print(f"[UNLOCK] Request received for week: {week}")
    print(f"[UNLOCK] Request data: {data}")
    print(f"[UNLOCK] Current user: {current_user.email if current_user.is_authenticated else 'Not authenticated'}")
    print(f"[UNLOCK] Is admin: {getattr(current_user, 'is_admin', False)}")
    
    if not week:
        print("[UNLOCK] Error: Week not provided")
        return jsonify({'success': False, 'error': 'Week required'})
    
    try:
        period = db.session.query(BettingPeriod).filter_by(week=week).first()
        
        if not period:
            print(f"[UNLOCK] Error: Betting period not found for week {week}")
            return jsonify({'success': False, 'error': 'Betting period not found'})
        
        print(f"[UNLOCK] Found period: week={period.week}, is_locked={period.is_locked}, is_settled={period.is_settled}, lock_time={period.lock_time}")
        
        period.is_locked = False
        new_lock_time = datetime.now(timezone.utc) + timedelta(days=7)
        period.lock_time = new_lock_time
        
        db.session.commit()
        
        print(f"[UNLOCK] Successfully unlocked week {week}, new lock_time set to {new_lock_time}")
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"[UNLOCK] Error unlocking period: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
