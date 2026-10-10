"""Routes package initialization."""
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

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'rooms_bp',
    'categories_bp',
    'bookings_bp',
    'checkin_out_bp',
    'billing_bp',
    'restaurant_bp',
    'reports_bp',
    'settings_bp'
]
