"""Local dev entry point: `python -m app` runs Flask on 0.0.0.0:5000."""

import os

from app import app

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
