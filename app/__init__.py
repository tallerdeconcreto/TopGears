from flask import Flask
from config import config
from .extensions import db, migrate, login_manager
from .routes import bp as main_bp

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    app.register_blueprint(main_bp)

    return app
