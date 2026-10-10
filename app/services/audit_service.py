"""Audit service for logging operational activities."""
import json
from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.user import AuditLog


def log_activity(action: str, entity_type: str, entity_id: str = None, details: str = None) -> AuditLog:
    """Record an audit trail entry."""
    try:
        user_id = current_user.id if current_user and current_user.is_authenticated else None
        user_name = current_user.full_name if current_user and current_user.is_authenticated else 'System'
        ip_address = request.remote_addr if request else None

        log_entry = AuditLog(
            user_id=user_id,
            user_name=user_name,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
    except Exception as e:
        # Prevent audit failures from crashing the main transaction
        db.session.rollback()
        print(f"Warning: Audit log failed: {e}")
        return None


