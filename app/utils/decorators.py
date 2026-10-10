"""Role-based authorization decorators."""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.models.user import Role


def role_required(*roles):
    """Decorator to require any of the specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles and current_user.role != Role.ADMIN:
                flash("Access denied: You do not have permission to view this resource.", "danger")
                return abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return role_required(Role.ADMIN)(f)


def manager_required(f):
    return role_required(Role.ADMIN, Role.MANAGER)(f)


def receptionist_required(f):
    return role_required(Role.ADMIN, Role.MANAGER, Role.RECEPTIONIST)(f)


def restaurant_required(f):
    return role_required(Role.ADMIN, Role.MANAGER, Role.RESTAURANT_STAFF, Role.RECEPTIONIST)(f)
