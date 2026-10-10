"""Application factory for Hotel and Restaurant Management System."""
import os
from datetime import datetime
from flask import Flask, render_template
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
from app.extensions import db, migrate, login_manager, csrf
from app.models.user import User
from app.models.hotel import HotelSettings
from app.utils.helpers import format_currency, format_date, format_datetime, calculate_overdue_text


def create_app(config_class=None):
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Select configuration
    if config_class is None:
        env = os.environ.get('FLASK_ENV', 'development')
        if env == 'production':
            config_class = ProductionConfig
        elif env == 'testing':
            config_class = TestingConfig
        else:
            config_class = DevelopmentConfig

    app.config.from_object(config_class)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register custom Jinja template filters
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['date'] = format_date
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['overdue_text'] = calculate_overdue_text

    # Inject global context processor for templates
    @app.context_processor
    def inject_globals():
        try:
            settings = HotelSettings.get_settings()
        except Exception:
            settings = None
        return {
            'hotel_settings': settings,
            'settings': settings,
            'current_datetime': datetime.utcnow()
        }


    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.rooms import rooms_bp
    from app.routes.categories import categories_bp
    from app.routes.bookings import bookings_bp
    from app.routes.checkin_out import checkin_out_bp
    from app.routes.billing import billing_bp
    from app.routes.restaurant import restaurant_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rooms_bp, url_prefix='/rooms')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    app.register_blueprint(bookings_bp, url_prefix='/bookings')
    app.register_blueprint(checkin_out_bp, url_prefix='/operations')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(restaurant_bp, url_prefix='/restaurant')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
