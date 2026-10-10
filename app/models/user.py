"""User, Role, and Audit models."""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class Role:
    ADMIN = 'admin'
    MANAGER = 'manager'
    RECEPTIONIST = 'receptionist'
    RESTAURANT_STAFF = 'restaurant_staff'

    CHOICES = [
        (ADMIN, 'Administrator'),
        (MANAGER, 'Hotel Manager'),
        (RECEPTIONIST, 'Front Desk Receptionist'),
        (RESTAURANT_STAFF, 'Restaurant Staff')
    ]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(32), nullable=False, default=Role.RECEPTIONIST)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role in (Role.ADMIN, Role.MANAGER)

    @property
    def is_receptionist(self) -> bool:
        return self.role in (Role.ADMIN, Role.MANAGER, Role.RECEPTIONIST)

    @property
    def is_restaurant_staff(self) -> bool:
        return self.role in (Role.ADMIN, Role.MANAGER, Role.RESTAURANT_STAFF)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    entity_type = db.Column(db.String(64), nullable=False, index=True)
    entity_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>'
