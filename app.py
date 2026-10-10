import os
import sys
from flask import Flask, render_template, make_response
from config.flask_config import app_config
from db.database import init_db, close_db, seed_sample_data

# Import blueprints
from modules.routes.core_routes import core_bp
from modules.routes.auth_routes import auth_bp
from modules.routes.inventory_routes import inventory_bp
from modules.routes.billing_routes import billing_bp


def create_app():
    """Application factory for CoreNestEngine."""
    application = Flask(__name__)
    cfg = app_config()
    application.config.update(cfg)
    application.secret_key = cfg.get("SECRET_KEY")

    # Register all blueprints
    application.register_blueprint(core_bp)
    application.register_blueprint(auth_bp)
    application.register_blueprint(inventory_bp)
    application.register_blueprint(billing_bp)

    # Database connection cleanup
    application.teardown_appcontext(close_db)

    # Automatically initialize SQLite database schema
    with application.app_context():
        init_db(application)

    # HTTP Error handlers
    @application.errorhandler(404)
    def not_found(error):
        return make_response(render_template('404.html'), 404)

    @application.errorhandler(500)
    def internal_error(error):
        return make_response(render_template('500.html'), 500)

    return application


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        # Seed default admin user and sample products if DB is newly created
        seed_sample_data()

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    debug = app.config.get("DEBUG", True)

    print("=" * 60)
    print(f"🚀 CoreNestEngine running at http://{host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)