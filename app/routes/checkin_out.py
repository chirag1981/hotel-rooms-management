"""Check-in, Check-out, and Operational Monitoring routes."""
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models.hotel import Room, RoomCategory, Floor, RoomStatus, HotelSettings
from app.models.booking import Guest, Booking, BookingRoom, Stay, BookingStatus
from app.models.billing import Invoice, Payment, GuestFolioCharge, InvoiceStatus
from app.forms.billing import CheckoutFinalizeForm, PaymentForm
from app.services.availability import is_room_available, get_available_rooms
from app.services.billing_service import calculate_stay_billing, finalize_invoice, record_payment, quantize_amount
from app.services.audit_service import log_activity
from app.utils.decorators import receptionist_required

checkin_out_bp = Blueprint('checkin_out', __name__)


@checkin_out_bp.route('/check-in/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@receptionist_required
def process_checkin(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.status == BookingStatus.CHECKED_IN:
        flash(f"Booking {booking.booking_number} is already checked in!", "info")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    if booking.status in [BookingStatus.CANCELLED, BookingStatus.CHECKED_OUT]:
        flash(f"Cannot check in a {booking.status} booking.", "danger")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    if request.method == 'POST':
        # Optional room re-assignment before check-in
        new_room_id = request.form.get('assigned_room_id', type=int)
        if new_room_id:
            curr_room = booking.primary_room
            if not curr_room or curr_room.id != new_room_id:
                avail, reason = is_room_available(new_room_id, booking.checkin_date, booking.checkout_date, exclude_booking_id=booking.id)
                if not avail:
                    flash(f"Cannot switch to selected room: {reason}", "danger")
                    return redirect(url_for('checkin_out.process_checkin', booking_id=booking.id))

                # Update booking room allocation
                BookingRoom.query.filter_by(booking_id=booking.id).delete()
                new_br = BookingRoom(
                    booking_id=booking.id,
                    room_id=new_room_id,
                    rate_per_night=booking.agreed_rate_per_night,
                    has_extra_bed=booking.extra_bed_charge > 0,
                    extra_bed_charge=booking.extra_bed_charge
                )
                db.session.add(new_br)
                log_activity('REASSIGN_ROOM', 'Booking', booking.id, f"Reassigned room to {new_room_id}")

        # Record advance deposit if entered during check-in
        deposit_amount = request.form.get('deposit_amount', type=float, default=0.0)
        pay_method = request.form.get('payment_method', 'Cash')
        if deposit_amount > 0:
            record_payment(
                booking_id=booking.id,
                amount=Decimal(str(deposit_amount)),
                payment_method=pay_method,
                user_id=current_user.id,
                transaction_ref='Check-in Advance Deposit',
                notes='Deposit received at check-in counter',
                is_advance=True
            )

        # Mark Booking Checked In
        booking.status = BookingStatus.CHECKED_IN

        # Create active Stay record for each allocated room
        for br in booking.booking_rooms:
            room = br.room
            if room:
                room.status = RoomStatus.OCCUPIED

            planned_in = datetime.combine(booking.checkin_date, datetime.strptime(booking.expected_checkin_time, '%H:%M').time() if ':' in booking.expected_checkin_time else datetime.min.time())
            planned_out = datetime.combine(booking.checkout_date, datetime.strptime(booking.expected_checkout_time, '%H:%M').time() if ':' in booking.expected_checkout_time else datetime.min.time())

            stay = Stay(
                booking_id=booking.id,
                guest_id=booking.guest_id,
                room_id=br.room_id,
                planned_checkin=planned_in,
                planned_checkout=planned_out,
                actual_checkin=datetime.utcnow(),
                status='Active',
                checked_in_by_id=current_user.id
            )
            db.session.add(stay)

        db.session.commit()

        log_activity('CHECKIN', 'Booking', booking.id, f"Guest {booking.guest.full_name} checked into room(s) {booking.assigned_room_numbers}")
        flash(f"Check-in completed for {booking.guest.full_name} (Room: {', '.join(booking.assigned_room_numbers)})", "success")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    # GET: show verification screen with option to reassign available rooms
    available_rooms = get_available_rooms(booking.checkin_date, booking.checkout_date, category_id=booking.room_category_id, exclude_booking_id=booking.id)
    return render_template('checkin_out/checkin_process.html', booking=booking, available_rooms=available_rooms)


@checkin_out_bp.route('/check-out/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@receptionist_required
def process_checkout(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    stay = booking.active_stay

    if booking.status == BookingStatus.CHECKED_OUT:
        flash(f"Booking {booking.booking_number} is already checked out.", "info")
        return redirect(url_for('bookings.detail', booking_id=booking.id))

    form = CheckoutFinalizeForm()

    # Calculate live billing summary
    late_hours = 0.0
    if stay and stay.is_overdue:
        late_hours = round(stay.overdue_duration_hours, 1)
        form.late_hours.data = Decimal(str(late_hours))

    calc = calculate_stay_billing(
        booking,
        stay=stay,
        late_hours=float(form.late_hours.data or 0.0),
        apply_early_fee=bool(form.apply_early_fee.data),
        discount=Decimal(str(form.discount_amount.data or 0.0))
    )

    if form.validate_on_submit():
        # 1. Finalize the invoice
        invoice = finalize_invoice(
            booking=booking,
            user_id=current_user.id,
            stay=stay,
            late_hours=float(form.late_hours.data or 0.0),
            apply_early_fee=form.apply_early_fee.data,
            discount=quantize_amount(form.discount_amount.data),
            notes=form.notes.data
        )

        # 2. Record checkout payment if collected
        pay_amt = quantize_amount(form.payment_amount.data)
        if pay_amt > Decimal('0.00'):
            record_payment(
                booking_id=booking.id,
                amount=pay_amt,
                payment_method=form.payment_method.data,
                user_id=current_user.id,
                invoice_id=invoice.id,
                transaction_ref=form.transaction_ref.data or 'Checkout Settlement',
                notes='Payment collected at check-out counter'
            )

        # 3. Mark Stay as Completed
        if stay:
            stay.status = 'Completed'
            stay.actual_checkout = datetime.utcnow()
            stay.checked_out_by_id = current_user.id

        # 4. Mark Booking Checked Out
        booking.status = BookingStatus.CHECKED_OUT

        # 5. Move physical rooms to CLEANING status (per specification: never directly to Available!)
        for br in booking.booking_rooms:
            if br.room:
                br.room.status = RoomStatus.CLEANING

        db.session.commit()

        log_activity('CHECKOUT', 'Booking', booking.id, f"Completed checkout for {booking.guest.full_name}. Room moved to Cleaning.")
        flash(f"Check-out complete! Invoice {invoice.invoice_number} finalized. Room(s) moved to Cleaning.", "success")
        return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))

    return render_template(
        'checkin_out/checkout_view.html',
        booking=booking,
        stay=stay,
        calc=calc,
        form=form,
        late_hours=late_hours
    )


@checkin_out_bp.route('/today-checkins')
@login_required
def today_checkins():
    today = date.today()
    checkins = Booking.query.filter(
        Booking.checkin_date == today,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN])
    ).order_by(Booking.expected_checkin_time).all()
    return render_template('checkin_out/today_checkins.html', checkins=checkins, today=today)


@checkin_out_bp.route('/today-checkouts')
@login_required
def today_checkouts():
    today = date.today()
    checkouts = Booking.query.filter(
        Booking.checkout_date == today,
        Booking.status.in_([BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT])
    ).order_by(Booking.expected_checkout_time).all()
    return render_template('checkin_out/today_checkouts.html', checkouts=checkouts, today=today)


@checkin_out_bp.route('/overdue')
@login_required
def overdue():
    now = datetime.utcnow()
    active_stays = Stay.query.filter(Stay.status == 'Active').all()
    overdue_list = [s for s in active_stays if s.planned_checkout and s.planned_checkout < now]
    return render_template('checkin_out/overdue.html', overdue_list=overdue_list, now=now)
