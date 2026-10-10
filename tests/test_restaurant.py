"""Test Restaurant Tables, Reservations, POS Orders, and Guest Folio Posting."""
import json
from datetime import date
from decimal import Decimal
from app.extensions import db
from app.models.hotel import Room, RoomCategory
from app.models.booking import Guest, Booking, BookingRoom, Stay
from app.models.billing import GuestFolioCharge
from app.models.restaurant import RestaurantTable, TableReservation, TableStatus, MenuItem, RestaurantOrder
from app.services.availability import is_table_available


def test_table_reservation_and_conflict_prevention(app):
    with app.app_context():
        table = RestaurantTable.query.first()
        t_id = table.id

        # Reserve for Oct 10 from 19:00 to 21:00
        res1 = TableReservation(
            reservation_number="RES-TEST-01",
            table_id=t_id,
            customer_name="John Doe",
            contact_number="9876543210",
            reservation_date=date(2026, 10, 10),
            start_time="19:00",
            end_time="21:00",
            guest_count=2,
            status="Confirmed"
        )
        db.session.add(res1)
        db.session.commit()

        # Conflicting time (19:30 to 20:30) -> Should be False
        avail, reason = is_table_available(t_id, date(2026, 10, 10), "19:30", "20:30")
        assert avail is False
        assert "has reservation" in reason

        # Non-conflicting time (21:30 to 23:00) -> Should be True
        avail2, _ = is_table_available(t_id, date(2026, 10, 10), "21:30", "23:00")
        assert avail2 is True


def test_restaurant_pos_order_and_post_to_room_folio(app, auth_client):
    with app.app_context():
        guest = Guest(full_name="Folio Diner", mobile="9800011122")
        db.session.add(guest)
        db.session.flush()

        room = Room.query.first()
        cat = RoomCategory.query.first()

        booking = Booking(
            booking_number="BK-FOLIO-TEST",
            guest_id=guest.id,
            room_category_id=cat.id,
            checkin_date=date.today(),
            checkout_date=date.today(),
            status="Checked In"
        )
        db.session.add(booking)
        db.session.flush()

        stay = Stay(
            booking_id=booking.id,
            guest_id=guest.id,
            room_id=room.id,
            planned_checkin=booking.created_at,
            planned_checkout=booking.created_at,
            status="Active"
        )
        db.session.add(stay)
        db.session.commit()

        stay_id = stay.id
        booking_id = booking.id
        menu_item = MenuItem.query.first()

    # Place POS order and post to room folio
    cart_json = json.dumps([
        {'id': menu_item.id, 'name': menu_item.name, 'price': float(menu_item.price), 'quantity': 2}
    ])
    resp = auth_client.post('/restaurant/pos', data={
        'order_type': 'Room-Service',
        'stay_id': str(stay_id),
        'cart_items_json': cart_json,
        'payment_action': 'PostToRoom'
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        # Verify folio charge was added
        folio_charges = GuestFolioCharge.query.filter_by(booking_id=booking_id).all()
        assert len(folio_charges) == 1
        assert folio_charges[0].amount == Decimal("525.00")  # (250 * 2) + 5% GST = 525.00
        assert folio_charges[0].is_billed is False
