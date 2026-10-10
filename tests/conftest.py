"""Test configuration and fixtures."""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.user import User, Role
from app.models.hotel import HotelSettings, Floor, RoomCategory, Room, RoomStatus
from app.models.restaurant import RestaurantTable, TableStatus, MenuCategory, MenuItem


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        # Create settings
        settings = HotelSettings(
            hotel_name="Test Grand Hotel",
            room_tax_rate=Decimal("12.00"),
            restaurant_tax_rate=Decimal("5.00"),
            early_checkin_fee=Decimal("500.00"),
            late_checkout_hourly_fee=Decimal("200.00")
        )
        db.session.add(settings)

        # Create test users
        admin = User(username="admin_test", email="admin@test.com", full_name="Admin User", role=Role.ADMIN)
        admin.set_password("password123")

        receptionist = User(username="rec_test", email="rec@test.com", full_name="Receptionist User", role=Role.RECEPTIONIST)
        receptionist.set_password("password123")

        staff = User(username="staff_test", email="staff@test.com", full_name="Restaurant Staff", role=Role.RESTAURANT_STAFF)
        staff.set_password("password123")

        db.session.add_all([admin, receptionist, staff])

        # Create floor & categories
        floor1 = Floor(floor_number=1, name="1st Floor", sort_order=1)
        db.session.add(floor1)
        db.session.flush()

        cat1 = RoomCategory(
            name="Deluxe Room",
            base_price=Decimal("2000.00"),
            max_guests=2,
            is_ac=True,
            tax_rate=Decimal("12.00")
        )
        db.session.add(cat1)
        db.session.flush()

        room101 = Room(room_number="101", floor_id=floor1.id, category_id=cat1.id, status=RoomStatus.AVAILABLE, max_occupancy=2)
        room102 = Room(room_number="102", floor_id=floor1.id, category_id=cat1.id, status=RoomStatus.AVAILABLE, max_occupancy=2)
        db.session.add_all([room101, room102])

        # Restaurant table
        t1 = RestaurantTable(table_number="T1", capacity=4, section="Indoor", status=TableStatus.AVAILABLE)
        db.session.add(t1)

        # Menu
        mcat = MenuCategory(name="Main Course")
        db.session.add(mcat)
        db.session.flush()
        mitem = MenuItem(category_id=mcat.id, name="Paneer Tikka", price=Decimal("250.00"), tax_rate=Decimal("5.00"))
        db.session.add(mitem)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Client authenticated as receptionist."""
    client.get('/auth/logout', follow_redirects=True)
    client.post('/auth/login', data={'username': 'rec_test', 'password': 'password123'}, follow_redirects=True)
    return client


@pytest.fixture
def admin_client(client):
    """Client authenticated as administrator."""
    client.get('/auth/logout', follow_redirects=True)
    client.post('/auth/login', data={'username': 'admin_test', 'password': 'password123'}, follow_redirects=True)
    return client
