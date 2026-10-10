"""Comprehensive operational and financial reporting with CSV export."""
import csv
import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, make_response, Response
from flask_login import login_required
from sqlalchemy import func, and_, or_
from app.extensions import db
from app.models.hotel import Room, RoomCategory, Floor, RoomStatus, HotelSettings
from app.models.booking import Booking, Stay, Guest, BookingStatus
from app.models.billing import Invoice, Payment
from app.models.restaurant import RestaurantTable, TableReservation, RestaurantOrder
from app.utils.decorators import manager_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
@manager_required
def index():
    report_type = request.args.get('report_type', 'occupancy')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    today = date.today()
    if not start_date_str:
        start_date = today - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)

    if not end_date_str:
        end_date = today
    else:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today

    settings = HotelSettings.get_settings()
    data = {}

    if report_type == 'occupancy':
        # Room occupancy by floor and category
        floors = Floor.query.filter_by(is_active=True).all()
        categories = RoomCategory.query.filter_by(is_active=True).all()
        rooms = Room.query.filter_by(is_active=True).all()

        total_rooms = len(rooms)
        occupied_count = sum(1 for r in rooms if r.status == RoomStatus.OCCUPIED)
        occupancy_rate = (occupied_count / total_rooms * 100) if total_rooms > 0 else 0

        data = {
            'total_rooms': total_rooms,
            'occupied_count': occupied_count,
            'occupancy_rate': round(occupancy_rate, 1),
            'floors': floors,
            'categories': categories,
            'rooms': rooms
        }

    elif report_type == 'checkins_outs':
        # Check-in and check-out logs in date range
        checkins = Booking.query.filter(
            Booking.checkin_date >= start_date,
            Booking.checkin_date <= end_date,
            Booking.status.in_([BookingStatus.CHECKED_IN, BookingStatus.CONFIRMED, BookingStatus.CHECKED_OUT])
        ).order_by(Booking.checkin_date.desc()).all()

        checkouts = Booking.query.filter(
            Booking.checkout_date >= start_date,
            Booking.checkout_date <= end_date,
            Booking.status == BookingStatus.CHECKED_OUT
        ).order_by(Booking.checkout_date.desc()).all()

        data = {'checkins': checkins, 'checkouts': checkouts}

    elif report_type == 'in_house':
        # In-house guests currently staying
        active_stays = Stay.query.filter_by(status='Active').all()
        data = {'stays': active_stays}

    elif report_type == 'revenue':
        # Revenue collected from rooms
        room_payments = Payment.query.filter(
            func.date(Payment.payment_date) >= start_date,
            func.date(Payment.payment_date) <= end_date
        ).order_by(Payment.payment_date.desc()).all()

        total_room_rev = sum(p.amount for p in room_payments)

        data = {
            'room_payments': room_payments,
            'total_room_rev': total_room_rev
        }

    elif report_type == 'outstanding':
        # Outstanding balances
        unpaid_invoices = Invoice.query.filter(
            Invoice.balance_amount > 0,
            Invoice.status != 'Cancelled'
        ).order_by(Invoice.balance_amount.desc()).all()
        total_unpaid = sum(i.balance_amount for i in unpaid_invoices)
        data = {'invoices': unpaid_invoices, 'total_unpaid': total_unpaid}

    elif report_type == 'cancellations':
        # Cancelled bookings and no-shows
        cancelled = Booking.query.filter(
            func.date(Booking.created_at) >= start_date,
            func.date(Booking.created_at) <= end_date,
            Booking.status.in_([BookingStatus.CANCELLED, BookingStatus.NO_SHOW])
        ).order_by(Booking.created_at.desc()).all()
        data = {'cancelled': cancelled}

    return render_template(
        'reports/index.html',
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        data=data,
        settings=settings
    )


@reports_bp.route('/export-csv')
@login_required
@manager_required
def export_csv():
    report_type = request.args.get('report_type', 'revenue')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')

    today = date.today()
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today - timedelta(days=30)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'revenue':
        writer.writerow(['Receipt Number', 'Date', 'Type', 'Guest Name', 'Method', 'Amount (INR)'])
        payments = Payment.query.filter(
            func.date(Payment.payment_date) >= start_date,
            func.date(Payment.payment_date) <= end_date
        ).all()
        for p in payments:
            writer.writerow([p.receipt_number, p.payment_date.strftime('%Y-%m-%d %H:%M'), 'Hotel Room Payment', p.guest.full_name if p.guest else 'N/A', p.payment_method, p.amount])

    elif report_type == 'checkins_outs':
        writer.writerow(['Booking Ref', 'Guest Name', 'Mobile', 'Check-in Date', 'Check-out Date', 'Status', 'Total Amount (INR)'])
        bookings = Booking.query.filter(
            Booking.checkin_date >= start_date,
            Booking.checkin_date <= end_date
        ).all()
        for b in bookings:
            writer.writerow([b.booking_number, b.guest.full_name, b.guest.mobile, b.checkin_date, b.checkout_date, b.status, b.total_amount])

    else:
        writer.writerow(['Record ID', 'Created Date', 'Status', 'Amount'])
        invoices = Invoice.query.filter(Invoice.balance_amount > 0).all()
        for i in invoices:
            writer.writerow([i.invoice_number, i.finalized_at.strftime('%Y-%m-%d'), i.status, i.balance_amount])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=Report_{report_type}_{start_date}_to_{end_date}.csv"
    response.headers["Content-Type"] = "text/csv"
    return response
