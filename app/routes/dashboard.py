"""Main Dashboard route computing hotel operational analytics."""
from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func, and_, or_
from app.extensions import db
from app.models.hotel import Room, RoomCategory, Floor, RoomStatus, HotelSettings
from app.models.booking import Booking, BookingRoom, Stay, BookingStatus
from app.models.billing import Invoice, Payment, GuestFolioCharge

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    now = datetime.utcnow()
    settings = HotelSettings.get_settings()

    # 1. HOTEL ROOM METRICS
    total_rooms = Room.query.filter_by(is_active=True).count()
    occupied_rooms = Room.query.filter_by(is_active=True, status=RoomStatus.OCCUPIED).count()
    reserved_rooms = Room.query.filter_by(is_active=True, status=RoomStatus.RESERVED).count()
    available_rooms = Room.query.filter_by(is_active=True, status=RoomStatus.AVAILABLE).count()
    cleaning_maintenance_rooms = Room.query.filter(
        Room.is_active == True,
        Room.status.in_([RoomStatus.CLEANING, RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE])
    ).count()

    # 2. TODAY'S CHECK-IN / CHECK-OUT COUNTS
    today_checkins = Booking.query.filter(
        Booking.checkin_date == today,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN])
    ).all()
    
    today_checkouts = Booking.query.filter(
        Booking.checkout_date == today,
        Booking.status.in_([BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT])
    ).all()

    # 3. OVERDUE CHECK-OUTS (Active stays where planned checkout < current time)
    active_stays = Stay.query.filter(Stay.status == 'Active').all()
    overdue_stays = [stay for stay in active_stays if stay.planned_checkout and stay.planned_checkout < now]
    overdue_checkouts_count = len(overdue_stays)

    # 4. FINANCIAL METRICS
    # Today's Room Payments received
    today_room_revenue = db.session.query(
        func.coalesce(func.sum(Payment.amount), 0)
    ).filter(
        func.date(Payment.payment_date) == today
    ).scalar() or Decimal('0.00')

    # Total Outstanding Guest Payments on all active stays / confirmed bookings
    outstanding_invoices = db.session.query(
        func.coalesce(func.sum(Invoice.balance_amount), 0)
    ).filter(
        Invoice.balance_amount > 0,
        Invoice.status != 'Cancelled'
    ).scalar() or Decimal('0.00')

    # Recent Bookings & Floor layout
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(6).all()
    floors = Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()

    return render_template(
        'dashboard/index.html',
        settings=settings,
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        reserved_rooms=reserved_rooms,
        available_rooms=available_rooms,
        cleaning_maintenance_rooms=cleaning_maintenance_rooms,
        today_checkins_count=len(today_checkins),
        today_checkouts_count=len(today_checkouts),
        overdue_checkouts_count=overdue_checkouts_count,
        today_room_revenue=today_room_revenue,
        outstanding_invoices=outstanding_invoices,
        today_checkins=today_checkins[:5],
        today_checkouts=today_checkouts[:5],
        overdue_stays=overdue_stays[:5],
        recent_bookings=recent_bookings,
        floors=floors
    )
