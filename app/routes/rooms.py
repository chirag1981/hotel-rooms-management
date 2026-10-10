"""Room management routes: Floor-wise grid, Room CRUD, Status Transitions."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.hotel import Room, RoomCategory, Floor, RoomStatus
from app.models.booking import Stay, BookingStatus
from app.forms.hotel import RoomForm, FloorForm
from app.utils.decorators import receptionist_required, manager_required
from app.services.audit_service import log_activity

rooms_bp = Blueprint('rooms', __name__)


@rooms_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    floor_filter = request.args.get('floor', '')
    category_filter = request.args.get('category', '')

    query = Room.query.filter_by(is_active=True)

    if status_filter:
        query = query.filter_by(status=status_filter)
    if floor_filter and floor_filter.isdigit():
        query = query.filter_by(floor_id=int(floor_filter))
    if category_filter and category_filter.isdigit():
        query = query.filter_by(category_id=int(category_filter))

    rooms = query.order_by(Room.room_number).all()
    floors = Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()
    categories = RoomCategory.query.filter_by(is_active=True).order_by(RoomCategory.name).all()

    # Group rooms by floor
    floors_with_rooms = []
    for floor in floors:
        floor_rooms = [r for r in rooms if r.floor_id == floor.id]
        floors_with_rooms.append({
            'floor': floor,
            'rooms': floor_rooms
        })

    # Summary badges count
    status_counts = {
        'all': Room.query.filter_by(is_active=True).count(),
        'available': Room.query.filter_by(is_active=True, status=RoomStatus.AVAILABLE).count(),
        'occupied': Room.query.filter_by(is_active=True, status=RoomStatus.OCCUPIED).count(),
        'reserved': Room.query.filter_by(is_active=True, status=RoomStatus.RESERVED).count(),
        'cleaning': Room.query.filter_by(is_active=True, status=RoomStatus.CLEANING).count(),
        'maintenance': Room.query.filter_by(is_active=True, status=RoomStatus.MAINTENANCE).count(),
    }

    return render_template(
        'rooms/index.html',
        floors_with_rooms=floors_with_rooms,
        floors=floors,
        categories=categories,
        status_filter=status_filter,
        floor_filter=floor_filter,
        category_filter=category_filter,
        status_counts=status_counts,
        RoomStatus=RoomStatus
    )


@rooms_bp.route('/<int:room_id>')
@login_required
def detail(room_id):
    room = Room.query.get_or_404(room_id)
    active_stay = Stay.query.filter_by(room_id=room.id, status='Active').first()
    recent_stays = Stay.query.filter_by(room_id=room.id).order_by(Stay.created_at.desc()).limit(10).all()
    return render_template('rooms/detail.html', room=room, active_stay=active_stay, recent_stays=recent_stays)


@rooms_bp.route('/add', methods=['GET', 'POST'])
@login_required
@receptionist_required
def add():
    form = RoomForm()
    form.floor_id.choices = [(f.id, f.name) for f in Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()]
    form.category_id.choices = [(c.id, f"{c.name} (₹{c.base_price})") for c in RoomCategory.query.filter_by(is_active=True).order_by(RoomCategory.name).all()]

    if form.validate_on_submit():
        existing = Room.query.filter_by(room_number=form.room_number.data.strip()).first()
        if existing:
            flash(f"Room number '{form.room_number.data}' already exists!", 'danger')
            return render_template('rooms/form.html', form=form, title='Add New Room')

        room = Room(
            room_number=form.room_number.data.strip(),
            floor_id=form.floor_id.data,
            category_id=form.category_id.data,
            status=form.status.data,
            max_occupancy=form.max_occupancy.data,
            notes=form.notes.data,
            is_active=form.is_active.data
        )
        db.session.add(room)
        db.session.commit()
        log_activity('CREATE_ROOM', 'Room', room.id, f"Created room {room.room_number}")
        flash(f"Room {room.room_number} added successfully!", 'success')
        return redirect(url_for('rooms.index'))

    return render_template('rooms/form.html', form=form, title='Add New Room')


@rooms_bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit(room_id):
    room = Room.query.get_or_404(room_id)
    form = RoomForm(obj=room)
    form.floor_id.choices = [(f.id, f.name) for f in Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()]
    form.category_id.choices = [(c.id, f"{c.name} (₹{c.base_price})") for c in RoomCategory.query.filter_by(is_active=True).order_by(RoomCategory.name).all()]

    if form.validate_on_submit():
        conflict = Room.query.filter(Room.room_number == form.room_number.data.strip(), Room.id != room.id).first()
        if conflict:
            flash(f"Room number '{form.room_number.data}' already exists for another room!", 'danger')
            return render_template('rooms/form.html', form=form, title=f'Edit Room {room.room_number}')

        room.room_number = form.room_number.data.strip()
        room.floor_id = form.floor_id.data
        room.category_id = form.category_id.data
        room.status = form.status.data
        room.max_occupancy = form.max_occupancy.data
        room.notes = form.notes.data
        room.is_active = form.is_active.data
        db.session.commit()

        log_activity('UPDATE_ROOM', 'Room', room.id, f"Updated room {room.room_number}")
        flash(f"Room {room.room_number} updated successfully.", 'success')
        return redirect(url_for('rooms.index'))

    return render_template('rooms/form.html', form=form, title=f'Edit Room {room.room_number}')


@rooms_bp.route('/<int:room_id>/update-status', methods=['POST'])
@login_required
@receptionist_required
def update_status(room_id):
    room = Room.query.get_or_404(room_id)
    new_status = request.form.get('status')
    notes = request.form.get('notes', '')

    if new_status not in [c[0] for c in RoomStatus.CHOICES]:
        flash('Invalid status provided.', 'danger')
        return redirect(request.referrer or url_for('rooms.index'))

    # If occupied, cannot manually change to available without check-out
    if room.status == RoomStatus.OCCUPIED and new_status == RoomStatus.AVAILABLE:
        active_stay = Stay.query.filter_by(room_id=room.id, status='Active').first()
        if active_stay:
            flash(f"Cannot mark Room {room.room_number} Available directly while an active guest stay exists! Please complete check-out first.", 'warning')
            return redirect(request.referrer or url_for('rooms.index'))

    old_status = room.status
    room.status = new_status
    if notes:
        room.notes = notes
    db.session.commit()

    log_activity('UPDATE_ROOM_STATUS', 'Room', room.id, f"Changed status from {old_status} to {new_status}")
    flash(f"Room {room.room_number} status changed to {new_status}.", 'success')
    return redirect(request.referrer or url_for('rooms.index'))


@rooms_bp.route('/<int:room_id>/mark-cleaned', methods=['POST'])
@login_required
@receptionist_required
def mark_cleaned(room_id):
    room = Room.query.get_or_404(room_id)
    room.status = RoomStatus.AVAILABLE
    db.session.commit()
    log_activity('ROOM_CLEANED', 'Room', room.id, f"Room {room.room_number} marked clean and available")
    flash(f"Room {room.room_number} is now Cleaned and Available for guests.", 'success')
    return redirect(request.referrer or url_for('rooms.index'))



