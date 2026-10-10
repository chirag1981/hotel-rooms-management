"""Test Room Categories, Floors, and Rooms status management."""
from decimal import Decimal
from app.extensions import db
from app.models.hotel import Room, RoomCategory, Floor, RoomStatus


def test_create_category_and_room(app, admin_client):
    with app.app_context():
        cat = RoomCategory(
            name="Executive Suite",
            base_price=Decimal("3500.00"),
            max_guests=3,
            is_ac=True,
            tax_rate=Decimal("12.00")
        )
        db.session.add(cat)
        db.session.commit()

        floor = Floor.query.first()
        room = Room(
            room_number="205",
            floor_id=floor.id,
            category_id=cat.id,
            status=RoomStatus.AVAILABLE,
            max_occupancy=3
        )
        db.session.add(room)
        db.session.commit()

        saved_room = Room.query.filter_by(room_number="205").first()
        assert saved_room is not None
        assert saved_room.category.name == "Executive Suite"
        assert saved_room.status == RoomStatus.AVAILABLE


def test_room_status_transitions_and_cleaning(app, auth_client):
    with app.app_context():
        room = Room.query.filter_by(room_number="101").first()
        room_id = room.id

    # 1. Update status to Cleaning via endpoint
    resp1 = auth_client.post(f'/rooms/{room_id}/update-status', data={'status': RoomStatus.CLEANING}, follow_redirects=True)
    assert resp1.status_code == 200

    # Verify status is Cleaning
    with app.app_context():
        db.session.expire_all()
        r1 = Room.query.get(room_id)
        assert r1.status == RoomStatus.CLEANING

    # 2. Mark room cleaned via mark-cleaned endpoint
    resp2 = auth_client.post(f'/rooms/{room_id}/mark-cleaned', follow_redirects=True)
    assert resp2.status_code == 200

    # Verify status is back to Available
    with app.app_context():
        db.session.expire_all()
        r2 = Room.query.get(room_id)
        assert r2.status == RoomStatus.AVAILABLE




