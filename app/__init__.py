from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

# Optional CORS import for mobile API
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Enable CORS for mobile API endpoints
    if HAS_CORS:
        CORS(app, resources={r"/api/v1/*": {"origins": "*"}})

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.delegates import delegates_bp
    from app.routes.payments import payments_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.events import events_bp
    from app.routes.settings import settings_bp
    from app.routes.analytics import analytics_bp
    from app.routes.communications import communications_bp
    from app.routes.badges import badges_bp
    from app.routes.checkin import checkin_bp
    from app.routes.mobile_api import mobile_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(delegates_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(communications_bp)
    app.register_blueprint(badges_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(mobile_api_bp)

    return app
