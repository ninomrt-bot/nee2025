# app.py ──────────────────────────────────────────────────────────
import os
from flask import Flask
from dotenv import load_dotenv
from routes import api_routes            # <- blueprint REST

def create_app() -> Flask:
    load_dotenv()                        # charge .env si présent
    app = Flask(__name__)
    app.register_blueprint(api_routes, url_prefix="/api")
    return app

if __name__ == "__main__":
    app   = create_app()
    host  = os.getenv("FLASK_HOST",   "0.0.0.0")
    port  = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)