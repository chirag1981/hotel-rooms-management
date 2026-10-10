"""Test Bookings, Overlap prevention, Check-in, Check-out, and Cleaning workflows."""
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models.hotel import Room, RoomCategory, RoomStatus
from app.models.booking import Guest, Booking, BookingRoom, Stay, BookingStatus
from app.services.availability import is_room_available


def test_booking_and_overlap_prevention(app, auth_client):
    with app.app_context():
        room = Room.query.filter_by(room_number="101").first()
        room_id = room.id
        cat = RoomCategory.query.first()

        guest = Guest(full_name="Alice Smith", mobile="9876543210", id_type="Aadhaar Card")
        db.session.add(guest)
        db.session.flush()

        # Create Booking 1: Oct 10 to Oct 15
        d1 = date(2026, 10, 10)
        d2 = date(2026, 10, 15)
        b1 = Booking(
            booking_number="BK-TEST-001",
            guest_id=guest.id,
            room_category_id=cat.id,
            status=BookingStatus.CONFIRMED,
            checkin_date=d1,
            checkout_date=d2,
            agreed_rate_per_night=Decimal("2000.00")
        )
        db.session.add(b1)
        db.session.flush()

        br1 = BookingRoom(booking_id=b1.id, room_id=room_id, rate_per_night=Decimal("2000.00"))
        db.session.add(br1)
        db.session.commit()

        # Test overlap checking
        # Overlapping period (Oct 12 to Oct 14) -> Must be REJECTED (False)
        avail, reason = is_room_available(room_id, date(2026, 10, 12), date(2026, 10, 14))
        assert avail is False
        assert "already booked" in reason

        # Non-overlapping period (Oct 15 to Oct 20) -> Must be AVAILABLE (True)
        avail2, _ = is_room_available(room_id, date(2026, 10, 15), date(2026, 10, 20))
        assert avail2 is True


def test_checkin_checkout_and_cleaning_transition(app, auth_client):
    today = date.today()
    with app.app_context():
        room = Room.query.filter_by(room_number="102").first()
        room_id = room.id
        cat = RoomCategory.query.first()

        guest = Guest(full_name="Bob Wilson", mobile="9123456789")
        db.session.add(guest)
        db.session.flush()

        booking = Booking(
            booking_number="BK-TEST-CHECKIN",
            guest_id=guest.id,
            room_category_id=cat.id,
            status=BookingStatus.CONFIRMED,
            checkin_date=today,
            checkout_date=today + timedelta(days=2),
            agreed_rate_per_night=Decimal("2000.00")
        )
        db.session.add(booking)
        db.session.flush()

        br = BookingRoom(booking_id=booking.id, room_id=room_id, rate_per_night=Decimal("2000.00"))
        db.session.add(br)
        db.session.commit()
        booking_id = booking.id

    # 1. Process Check-in
    resp = auth_client.post(f'/operations/check-in/{booking_id}', data={'deposit_amount': '500.00', 'payment_method': 'Cash'}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        b = Booking.query.get(booking_id)
        r = Room.query.get(room_id)
        stay = b.active_stay
        assert b.status == BookingStatus.CHECKED_IN
        assert r.status == RoomStatus.OCCUPIED
        assert stay is not None
        assert stay.status == 'Active'
        assert stay.actual_checkin is not None

    # 2. Process Check-out
    resp_co = auth_client.post(f'/operations/check-out/{booking_id}', data={
        'payment_amount': '3980.00',
        'payment_method': 'Cash',
        'discount_amount': '0.00'
    }, follow_redirects=True)
    assert resp_co.status_code == 200

    with app.app_context():
        b = Booking.query.get(booking_id)
        r = Room.query.get(room_id)
        assert b.status == BookingStatus.CHECKED_OUT
        # Room MUST move to Cleaning (not directly to Available)
        assert r.status == RoomStatus.CLEANING
        assert b.invoices.count() == 1


def test_overdue_checkouts_detection(app):
    with app.app_context():
        now = datetime.utcnow()
        room = Room.query.filter_by(room_number="101").first()
        cat = RoomCategory.query.first()
        
        guest = Guest(full_name="Overdue Guest", mobile="9888877777")
        db.session.add(guest)
        db.session.flush()

        booking = Booking(
            booking_number="BK-OVERDUE-TEST",
            guest_id=guest.id,
            room_category_id=cat.id,
            checkin_date=date.today() - timedelta(days=2),
            checkout_date=date.today(),
            status="Checked In"
        )
        db.session.add(booking)
        db.session.flush()

        # Active stay with planned checkout in the past
        past_stay = Stay(
            booking_id=booking.id,
            guest_id=guest.id,
            room_id=room.id,
            planned_checkin=now - timedelta(days=2),
            planned_checkout=now - timedelta(hours=4),
            actual_checkin=now - timedelta(days=2),
            status='Active'
        )
        db.session.add(past_stay)
        db.session.commit()

        assert past_stay.is_overdue is True
        assert past_stay.overdue_duration_hours >= 3.9
