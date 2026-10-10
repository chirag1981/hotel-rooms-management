"""Settings, User Accounts, and Audit Log routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.hotel import HotelSettings
from app.models.user import User, Role, AuditLog
from app.forms.settings import HotelSettingsForm, UserAccountForm
from app.services.audit_service import log_activity
from app.utils.decorators import admin_required, manager_required

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
@manager_required
def index():
    hotel_settings = HotelSettings.get_settings()
    form = HotelSettingsForm(obj=hotel_settings)

    if form.validate_on_submit():
        form.populate_obj(hotel_settings)
        db.session.commit()
        log_activity('UPDATE_SETTINGS', 'HotelSettings', hotel_settings.id, "Updated hotel configuration parameters")
        flash("Hotel and billing settings updated successfully.", "success")
        return redirect(url_for('settings.index'))

    return render_template('settings/index.html', form=form, settings=hotel_settings)


@settings_bp.route('/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('settings/users.html', users=all_users, Role=Role)


@settings_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    form = UserAccountForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required when creating a new user account.", "danger")
            return render_template('settings/user_form.html', form=form, title="Create Staff Account")

        existing_user = User.query.filter(
            (User.username == form.username.data.strip()) | (User.email == form.email.data.strip())
        ).first()
        if existing_user:
            flash("A user with this username or email already exists.", "danger")
            return render_template('settings/user_form.html', form=form, title="Create Staff Account")

        user = User(
            username=form.username.data.strip(),
            email=form.email.data.strip(),
            full_name=form.full_name.data.strip(),
            role=form.role.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        log_activity('CREATE_USER', 'User', user.id, f"Created staff user {user.username} with role {user.role}")
        flash(f"Staff user account for '{user.full_name}' created successfully.", "success")
        return redirect(url_for('settings.users'))

    return render_template('settings/user_form.html', form=form, title="Create Staff Account")


@settings_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserAccountForm(obj=user)

    if form.validate_on_submit():
        conflict = User.query.filter(
            ((User.username == form.username.data.strip()) | (User.email == form.email.data.strip())),
            User.id != user.id
        ).first()
        if conflict:
            flash("Another user is already using this username or email.", "danger")
            return render_template('settings/user_form.html', form=form, title=f"Edit {user.username}")

        user.username = form.username.data.strip()
        user.email = form.email.data.strip()
        user.full_name = form.full_name.data.strip()
        user.role = form.role.data
        user.is_active = form.is_active.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        log_activity('UPDATE_USER', 'User', user.id, f"Updated account {user.username}")
        flash(f"User '{user.username}' updated successfully.", "success")
        return redirect(url_for('settings.users'))

    return render_template('settings/user_form.html', form=form, title=f"Edit Staff Account: {user.username}")


@settings_bp.route('/audit-logs')
@login_required
@manager_required
def audit_logs():
    action_filter = request.args.get('action', '')
    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)

    logs = query.order_by(AuditLog.created_at.desc()).limit(150).all()
    actions = db.session.query(AuditLog.action).distinct().all()
    action_list = [a[0] for a in actions]

    return render_template('settings/audit_logs.html', logs=logs, actions=action_list, action_filter=action_filter)
