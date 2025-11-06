from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files (images)."""
    return send_from_directory('frontend/static', filename)

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit environment
    app.run(host='0.0.0.0', port=5000, debug=True)
