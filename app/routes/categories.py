"""Room Category and Floor management routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.hotel import RoomCategory, Floor, Room
from app.forms.hotel import RoomCategoryForm, FloorForm
from app.utils.decorators import manager_required
from app.services.audit_service import log_activity

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/')
@login_required
def index():
    categories = RoomCategory.query.order_by(RoomCategory.name).all()
    floors = Floor.query.order_by(Floor.sort_order).all()
    return render_template('rooms/category_list.html', categories=categories, floors=floors)


@categories_bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add():
    form = RoomCategoryForm()
    if form.validate_on_submit():
        existing = RoomCategory.query.filter_by(name=form.name.data.strip()).first()
        if existing:
            flash(f"Category '{form.name.data}' already exists!", 'danger')
            return render_template('rooms/category_form.html', form=form, title='Add Room Category')

        cat = RoomCategory(
            name=form.name.data.strip(),
            description=form.description.data,
            base_price=form.base_price.data,
            max_guests=form.max_guests.data,
            is_ac=form.is_ac.data,
            bed_type=form.bed_type.data,
            bed_count=form.bed_count.data,
            tax_rate=form.tax_rate.data,
            extra_adult_price=form.extra_adult_price.data,
            extra_child_price=form.extra_child_price.data,
            amenities=form.amenities.data,
            is_active=form.is_active.data
        )
        db.session.add(cat)
        db.session.commit()
        log_activity('CREATE_CATEGORY', 'RoomCategory', cat.id, f"Created category {cat.name} with rate ₹{cat.base_price}")
        flash(f"Room category '{cat.name}' created successfully.", 'success')
        return redirect(url_for('categories.index'))

    return render_template('rooms/category_form.html', form=form, title='Add Room Category')


@categories_bp.route('/<int:cat_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit(cat_id):
    cat = RoomCategory.query.get_or_404(cat_id)
    form = RoomCategoryForm(obj=cat)

    if form.validate_on_submit():
        conflict = RoomCategory.query.filter(RoomCategory.name == form.name.data.strip(), RoomCategory.id != cat.id).first()
        if conflict:
            flash(f"Category name '{form.name.data}' is already used by another category.", 'danger')
            return render_template('rooms/category_form.html', form=form, title=f'Edit {cat.name}')

        old_rate = cat.base_price
        cat.name = form.name.data.strip()
        cat.description = form.description.data
        cat.base_price = form.base_price.data
        cat.max_guests = form.max_guests.data
        cat.is_ac = form.is_ac.data
        cat.bed_type = form.bed_type.data
        cat.bed_count = form.bed_count.data
        cat.tax_rate = form.tax_rate.data
        cat.extra_adult_price = form.extra_adult_price.data
        cat.extra_child_price = form.extra_child_price.data
        cat.amenities = form.amenities.data
        cat.is_active = form.is_active.data
        db.session.commit()

        log_activity('UPDATE_CATEGORY', 'RoomCategory', cat.id, f"Updated {cat.name} (rate: ₹{old_rate} -> ₹{cat.base_price})")
        flash(f"Room category '{cat.name}' updated successfully.", 'success')
        return redirect(url_for('categories.index'))

    return render_template('rooms/category_form.html', form=form, title=f'Edit {cat.name}')


@categories_bp.route('/floors/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_floor():
    form = FloorForm()
    if form.validate_on_submit():
        existing = Floor.query.filter_by(floor_number=form.floor_number.data).first()
        if existing:
            flash(f"Floor number {form.floor_number.data} already exists.", 'danger')
            return render_template('rooms/floor_form.html', form=form, title='Add New Floor')

        floor = Floor(
            floor_number=form.floor_number.data,
            name=form.name.data.strip(),
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=form.is_active.data
        )
        db.session.add(floor)
        db.session.commit()
        log_activity('CREATE_FLOOR', 'Floor', floor.id, f"Created floor {floor.name}")
        flash(f"Floor '{floor.name}' added successfully.", 'success')
        return redirect(url_for('categories.index'))

    return render_template('rooms/floor_form.html', form=form, title='Add New Floor')
