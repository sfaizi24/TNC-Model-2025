from flask import Flask, render_template, send_from_directory, redirect, url_for, request, session, flash, jsonify
import os
from functools import wraps
import sys
sys.path.append('backend/scrapers')
from database_users import UsersDB
from database import ProjectionsDB

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
app.secret_key = os.environ.get('SECRET_KEY', 'tncasino-secret-key-change-in-production')

db = UsersDB()
proj_db = ProjectionsDB()

def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Redirect to betting page."""
    if 'user_id' in session:
        return redirect(url_for('betting'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if request.method == 'POST':
        data = request.get_json()
        user = db.authenticate_user(data['username'], data['password'])
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    """Handle user signup."""
    data = request.get_json()
    user_id = db.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password'],
        full_name=data.get('full_name', '')
    )
    if user_id:
        session['user_id'] = user_id
        session['username'] = data['username']
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Username or email already exists'})

@app.route('/logout')
def logout():
    """Logout user."""
    session.clear()
    return redirect(url_for('login'))

@app.route('/analytics')
@login_required
def analytics():
    """Render the analytics dashboard."""
    user = db.get_user(session['user_id'])
    return render_template('analytics.html', user=user)

@app.route('/account')
@login_required
def account():
    """Render the account page."""
    user = db.get_user(session['user_id'])
    bets = db.get_user_bets(session['user_id'], limit=20)
    weekly_stats = db.get_all_weekly_stats(session['user_id'])
    return render_template('account.html', user=user, bets=bets, weekly_stats=weekly_stats)

@app.route('/betting')
@login_required
def betting():
    """Render the betting page."""
    user = db.get_user(session['user_id'])
    return render_template('betting.html', user=user)

@app.route('/api/place_bet', methods=['POST'])
@login_required
def place_bet():
    """API endpoint to place a bet."""
    data = request.get_json()
    bet_id = db.place_bet(
        user_id=session['user_id'],
        bet_type=data['bet_type'],
        description=data['description'],
        amount=float(data['amount']),
        odds=data['odds'],
        potential_win=float(data['potential_win']),
        week=data.get('week', 10)
    )
    if bet_id:
        user = db.get_user(session['user_id'])
        return jsonify({'success': True, 'balance': user['account_balance']})
    return jsonify({'success': False, 'message': 'Insufficient balance'})

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (images)."""
    return send_from_directory('frontend/static', filename)

@app.route('/api/teams')
@login_required
def get_teams():
    """API endpoint to get list of teams."""
    try:
        teams = proj_db.get_all_team_owners(week="10")
        return jsonify({'teams': teams})
    except Exception as e:
        print(f"Error getting teams: {e}")
        return jsonify({'teams': []})

@app.route('/api/team_players')
@login_required
def get_team_players():
    """API endpoint to get players for a specific team."""
    team = request.args.get('team')
    if not team:
        return jsonify({'error': 'Team parameter required'}), 400
    
    try:
        players = proj_db.get_player_stats(week="10", team_owner=team)
        return jsonify({'players': players})
    except Exception as e:
        print(f"Error getting team players: {e}")
        return jsonify({'players': []})

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit environment
    # Use environment variable for debug mode (only enable in development)
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
