from flask import Flask, render_template, make_response
from config.flask_config import app_key, app_config

# Import blueprints
from modules.routes.core_routes import core_bp
from modules.routes.auth_routes import auth_bp
from modules.routes.inventory_routes import inventory_bp
from modules.routes.billing_routes import billing_bp

app = Flask(__name__)
app.secret_key = app_key()
app.config.update = app_config()

# Register all the blueprints with the app
app.register_blueprint(core_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(billing_bp)


@app.errorhandler(404)
def not_found(error):
    return make_response(render_template('404.html'), 404)

@app.errorhandler(500)
def internal_error(error):
    return make_response(render_template('505.html'), 505)


if __name__ == "__main__":
    app.run(debug=True)