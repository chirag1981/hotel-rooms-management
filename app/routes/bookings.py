"""Guest Registration and Booking routes."""
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models.hotel import Room, RoomCategory, RoomStatus, HotelSettings, Floor

from app.models.booking import Guest, Booking, BookingRoom, Stay, BookingStatus
from app.models.billing import Payment
from app.forms.booking import BookingForm, GuestForm
from app.services.availability import is_room_available, get_available_rooms
from app.services.billing_service import quantize_amount, record_payment
from app.services.audit_service import log_activity
from app.utils.decorators import receptionist_required

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '').strip()
    date_filter = request.args.get('date', '')

    query = Booking.query.join(Guest)

    if status_filter:
        query = query.filter(Booking.status == status_filter)
    if search_query:
        query = query.filter(
            or_(
                Booking.booking_number.ilike(f"%{search_query}%"),
                Guest.full_name.ilike(f"%{search_query}%"),
                Guest.mobile.ilike(f"%{search_query}%")
            )
        )
    if date_filter:
        try:
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(or_(Booking.checkin_date == d, Booking.checkout_date == d))
        except ValueError:
            pass

    bookings = query.order_by(Booking.created_at.desc()).all()

    return render_template(
        'bookings/index.html',
        bookings=bookings,
        status_filter=status_filter,
        search_query=search_query,
        date_filter=date_filter,
        BookingStatus=BookingStatus
    )


@bookings_bp.route('/new', methods=['GET', 'POST'])
@login_required
@receptionist_required
def new():
    settings = HotelSettings.get_settings()
    form = BookingForm()

    # Populate dropdown choices
    guests = Guest.query.order_by(Guest.full_name).all()
    form.guest_id.choices = [(0, '-- Create / Enter New Guest --')] + [(g.id, f"{g.full_name} ({g.mobile})") for g in guests]
    
    categories = RoomCategory.query.filter_by(is_active=True).order_by(RoomCategory.name).all()
    form.room_category_id.choices = [(c.id, f"{c.name} - ₹{c.base_price}/night") for c in categories]
    
    all_rooms = Room.query.filter_by(is_active=True).order_by(Room.floor_id, Room.room_number).all()
    floors = Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()
    form.allocated_rooms.choices = [(r.id, f"Room {r.room_number} ({r.category.name} - {r.status})") for r in all_rooms]

    # Preselect category if passed in query string
    pre_cat = request.args.get('category_id', type=int)
    if request.method == 'GET' and pre_cat:
        form.room_category_id.data = pre_cat
        cat_obj = RoomCategory.query.get(pre_cat)
        if cat_obj:
            form.agreed_rate_per_night.data = cat_obj.base_price

    if form.validate_on_submit():
        checkin_d = form.checkin_date.data
        checkout_d = form.checkout_date.data

        if checkout_d <= checkin_d:
            flash("Check-out date must be strictly after check-in date.", "danger")
            return render_template('bookings/new.html', form=form, categories=categories, settings=settings, all_rooms=all_rooms, floors=floors)

        nights = (checkout_d - checkin_d).days

        # 1. Resolve or Create Guest
        guest_id = form.guest_id.data
        if not guest_id or guest_id == 0:
            if not form.new_guest_name.data or not form.new_guest_mobile.data:
                flash("Please provide Guest Name and Mobile Number for new guest.", "danger")
                return render_template('bookings/new.html', form=form, categories=categories, settings=settings, all_rooms=all_rooms, floors=floors)

            # Check if guest with same mobile exists
            existing_guest = Guest.query.filter_by(mobile=form.new_guest_mobile.data.strip()).first()
            if existing_guest:
                guest = existing_guest
                if form.new_guest_name.data:
                    guest.full_name = form.new_guest_name.data.strip()
            else:
                guest = Guest(
                    full_name=form.new_guest_name.data.strip(),
                    mobile=form.new_guest_mobile.data.strip(),
                    email=form.new_guest_email.data.strip() if form.new_guest_email.data else None,
                    id_type=form.new_guest_id_type.data,
                    id_number=form.new_guest_id_number.data.strip() if form.new_guest_id_number.data else None,
                    city=form.new_guest_city.data.strip() if form.new_guest_city.data else None
                )
                db.session.add(guest)
                db.session.flush()
        else:
            guest = Guest.query.get_or_404(guest_id)

        # 2. Check room availability for all selected rooms
        allocated_room_ids = form.allocated_rooms.data
        if not allocated_room_ids:
            flash("Please allocate at least one physical room.", "danger")
            return render_template('bookings/new.html', form=form, categories=categories, settings=settings, all_rooms=all_rooms, floors=floors)

        for rid in allocated_room_ids:
            avail, reason = is_room_available(rid, checkin_d, checkout_d)
            if not avail:
                flash(f"Room allocation failed: {reason}", "danger")
                return render_template('bookings/new.html', form=form, categories=categories, settings=settings, all_rooms=all_rooms, floors=floors)


        # 3. Create Booking
        timestamp_str = datetime.utcnow().strftime('%Y%m%d')
        count = Booking.query.filter(Booking.created_at >= datetime.utcnow().date()).count() + 1
        booking_number = f"{settings.booking_prefix}{timestamp_str}-{count:04d}"

        rate_per_night = quantize_amount(form.agreed_rate_per_night.data)
        extra_bed_rate = quantize_amount(form.extra_bed_charge.data) if form.has_extra_bed.data else Decimal('0.00')
        room_count = len(allocated_room_ids)

        subtotal_estimate = quantize_amount((rate_per_night * room_count + extra_bed_rate) * nights)
        tax_rate = quantize_amount(settings.room_tax_rate)
        tax_amount = quantize_amount(subtotal_estimate * (tax_rate / Decimal('100.00')))
        discount = quantize_amount(form.discount_amount.data)
        total_estimate = quantize_amount(subtotal_estimate + tax_amount - discount)
        advance_paid = quantize_amount(form.advance_payment.data)

        # Status determined by Walk-in Immediate check-in or standard confirmation
        is_immediate_checkin = form.checkin_now.data and checkin_d == date.today()
        initial_status = BookingStatus.CHECKED_IN if is_immediate_checkin else BookingStatus.CONFIRMED

        booking = Booking(
            booking_number=booking_number,
            guest_id=guest.id,
            room_category_id=form.room_category_id.data,
            booking_source=form.booking_source.data,
            status=initial_status,
            checkin_date=checkin_d,
            checkout_date=checkout_d,
            expected_checkin_time=form.expected_checkin_time.data,
            expected_checkout_time=form.expected_checkout_time.data,
            adults_count=form.adults_count.data,
            children_count=form.children_count.data,
            total_nights=nights,
            agreed_rate_per_night=rate_per_night,
            extra_bed_charge=extra_bed_rate,
            discount_amount=discount,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_estimate,
            advance_payment=advance_paid,
            payment_method=form.payment_method.data,
            special_requests=form.special_requests.data,
            created_by_id=current_user.id
        )
        db.session.add(booking)
        db.session.flush()

        # 4. Attach Allocated Rooms
        for rid in allocated_room_ids:
            br = BookingRoom(
                booking_id=booking.id,
                room_id=rid,
                rate_per_night=rate_per_night,
                has_extra_bed=form.has_extra_bed.data,
                extra_bed_charge=extra_bed_rate
            )
            db.session.add(br)

            # If advance booking (future), set status to Reserved; if immediate walk-in, set to Occupied
            room_obj = Room.query.get(rid)
            if is_immediate_checkin:
                room_obj.status = RoomStatus.OCCUPIED
            elif checkin_d == date.today():
                room_obj.status = RoomStatus.RESERVED

        # 5. If immediate walk-in check-in, create active Stay record
        if is_immediate_checkin:
            for rid in allocated_room_ids:
                planned_in = datetime.combine(checkin_d, datetime.strptime(form.expected_checkin_time.data, '%H:%M').time() if ':' in form.expected_checkin_time.data else datetime.min.time())
                planned_out = datetime.combine(checkout_d, datetime.strptime(form.expected_checkout_time.data, '%H:%M').time() if ':' in form.expected_checkout_time.data else datetime.min.time())
                stay = Stay(
                    booking_id=booking.id,
                    guest_id=guest.id,
                    room_id=rid,
                    planned_checkin=planned_in,
                    planned_checkout=planned_out,
                    actual_checkin=datetime.utcnow(),
                    status='Active',
                    checked_in_by_id=current_user.id
                )
                db.session.add(stay)

        # 6. Record Advance Deposit Payment if paid
        if advance_paid > Decimal('0.00'):
            record_payment(
                booking_id=booking.id,
                amount=advance_paid,
                payment_method=form.payment_method.data,
                user_id=current_user.id,
                transaction_ref='Advance Deposit at Booking',
                notes=f'Advance deposit for Booking {booking.booking_number}',
                is_advance=True
            )

        db.session.commit()

        action_name = "CHECKIN_WALKIN" if is_immediate_checkin else "CREATE_BOOKING"
        log_activity(action_name, 'Booking', booking.id, f"Booking {booking.booking_number} created for {guest.full_name} ({booking.status})")
        
        flash(f"Booking {booking.booking_number} created successfully ({booking.status})!", "success")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    return render_template('bookings/new.html', form=form, categories=categories, settings=settings, all_rooms=all_rooms, floors=floors)



@bookings_bp.route('/<int:booking_id>')
@login_required
def detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    settings = HotelSettings.get_settings()
    payments = Payment.query.filter_by(booking_id=booking.id).order_by(Payment.payment_date.desc()).all()
    invoices = booking.invoices.all()
    folio_charges = booking.folio_charges.all()
    
    total_paid = sum(p.amount for p in payments)
    balance = booking.total_amount - total_paid

    return render_template(
        'bookings/detail.html',
        booking=booking,
        payments=payments,
        invoices=invoices,
        folio_charges=folio_charges,
        total_paid=total_paid,
        balance=balance,
        settings=settings,
        BookingStatus=BookingStatus
    )


@bookings_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
@receptionist_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
        flash("Cannot cancel a booking that has already checked in or checked out.", "warning")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    booking.status = BookingStatus.CANCELLED
    # Free up room reserved status
    for br in booking.booking_rooms:
        if br.room and br.room.status == RoomStatus.RESERVED:
            br.room.status = RoomStatus.AVAILABLE

    db.session.commit()
    log_activity('CANCEL_BOOKING', 'Booking', booking.id, f"Cancelled booking {booking.booking_number}")
    flash(f"Booking {booking.booking_number} has been cancelled.", "info")
    return redirect(url_for('bookings.detail', booking_id=booking.id))


@bookings_bp.route('/api/available-rooms')
@login_required
def api_available_rooms():
    """AJAX endpoint to get available rooms for date picker in real time."""
    checkin_str = request.args.get('checkin')
    checkout_str = request.args.get('checkout')
    cat_id = request.args.get('category_id', type=int)

    if not checkin_str or not checkout_str:
        return jsonify([])

    try:
        checkin_d = datetime.strptime(checkin_str, '%Y-%m-%d').date()
        checkout_d = datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    rooms = get_available_rooms(checkin_d, checkout_d, category_id=cat_id)
    return jsonify([{
        'id': r.id,
        'room_number': r.room_number,
        'category': r.category.name,
        'price': str(r.category.base_price),
        'floor': r.floor.name
    } for r in rooms])
