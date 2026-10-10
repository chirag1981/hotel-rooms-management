"""Application configuration classes."""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-9988776655')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'hotel_management.db')}"
    )
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Hotel Defaults
    HOTEL_NAME = os.environ.get('HOTEL_NAME', 'Hotel Rooms Management')
    HOTEL_CURRENCY = os.environ.get('HOTEL_CURRENCY', 'INR')
    HOTEL_CURRENCY_SYMBOL = os.environ.get('HOTEL_CURRENCY_SYMBOL', '₹')
    HOTEL_TIMEZONE = os.environ.get('HOTEL_TIMEZONE', 'Asia/Kolkata')


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


from sqlalchemy.pool import StaticPool


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': StaticPool,
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
