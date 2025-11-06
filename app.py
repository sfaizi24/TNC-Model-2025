from flask import Flask, render_template, send_from_directory, redirect, url_for
import os

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

@app.route('/')
def index():
    """Redirect to login page."""
    return redirect(url_for('login'))

@app.route('/login')
def login():
    """Render the login page."""
    return render_template('login.html')

@app.route('/analytics')
def analytics():
    """Render the analytics dashboard."""
    return render_template('analytics.html')

@app.route('/account')
def account():
    """Render the account page."""
    return render_template('account.html')

@app.route('/betting')
def betting():
    """Render the betting page."""
    return render_template('betting.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (images)."""
    return send_from_directory('frontend/static', filename)

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit environment
    # Use environment variable for debug mode (only enable in development)
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
