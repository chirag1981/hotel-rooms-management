"""Hotel settings, Floor, RoomCategory, and Room models."""
from datetime import datetime
from decimal import Decimal
from app.extensions import db


class RoomStatus:
    AVAILABLE = 'Available'
    RESERVED = 'Reserved'
    OCCUPIED = 'Occupied'
    CLEANING = 'Cleaning'
    MAINTENANCE = 'Maintenance'
    OUT_OF_SERVICE = 'Out of Service'

    CHOICES = [
        (AVAILABLE, 'Available'),
        (RESERVED, 'Reserved'),
        (OCCUPIED, 'Occupied'),
        (CLEANING, 'Cleaning'),
        (MAINTENANCE, 'Maintenance'),
        (OUT_OF_SERVICE, 'Out of Service')
    ]

    COLORS = {
        AVAILABLE: 'success',
        RESERVED: 'warning',
        OCCUPIED: 'danger',
        CLEANING: 'info',
        MAINTENANCE: 'secondary',
        OUT_OF_SERVICE: 'dark'
    }


class HotelSettings(db.Model):
    __tablename__ = 'hotel_settings'

    id = db.Column(db.Integer, primary_key=True)
    hotel_name = db.Column(db.String(150), nullable=False, default='Hotel Rooms Management System')
    tagline = db.Column(db.String(255), nullable=True, default='Luxury, Comfort & Fine Cuisine')
    address_line = db.Column(db.String(255), nullable=True, default='108 Sea Breeze Boulevard, Marine Drive')
    city = db.Column(db.String(100), nullable=True, default='Mumbai')
    state = db.Column(db.String(100), nullable=True, default='Maharashtra')
    pincode = db.Column(db.String(20), nullable=True, default='400020')
    country = db.Column(db.String(100), nullable=True, default='India')
    phone = db.Column(db.String(50), nullable=True, default='+91 98765 43210')
    email = db.Column(db.String(120), nullable=True, default='reservations@grandhorizonhotel.com')
    gstin = db.Column(db.String(50), nullable=True, default='27AAACG0123M1Z5')
    currency_code = db.Column(db.String(10), nullable=False, default='INR')
    currency_symbol = db.Column(db.String(10), nullable=False, default='₹')
    timezone = db.Column(db.String(50), nullable=False, default='Asia/Kolkata')
    
    # Check-in/Check-out policies
    standard_checkin_time = db.Column(db.String(10), nullable=False, default='14:00')
    standard_checkout_time = db.Column(db.String(10), nullable=False, default='11:00')
    
    # Tax rates
    room_tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))  # 12% GST
    restaurant_tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00'))  # 5% GST
    
    # Additional fee policies
    early_checkin_fee = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('500.00'))
    late_checkout_hourly_fee = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('250.00'))
    extra_bed_charge = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('800.00'))
    extra_person_charge = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('500.00'))
    
    # Invoice numbering
    invoice_prefix = db.Column(db.String(20), nullable=False, default='INV-')
    booking_prefix = db.Column(db.String(20), nullable=False, default='BK-')
    restaurant_order_prefix = db.Column(db.String(20), nullable=False, default='ORD-')

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings


class Floor(db.Model):
    __tablename__ = 'floors'

    id = db.Column(db.Integer, primary_key=True)
    floor_number = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    rooms = db.relationship('Room', back_populates='floor', cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<Floor {self.name}>'


class RoomCategory(db.Model):
    __tablename__ = 'room_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('2500.00'))
    max_guests = db.Column(db.Integer, nullable=False, default=2)
    is_ac = db.Column(db.Boolean, nullable=False, default=True)
    bed_type = db.Column(db.String(50), nullable=False, default='King Bed')
    bed_count = db.Column(db.Integer, nullable=False, default=1)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))
    extra_adult_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('600.00'))
    extra_child_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('300.00'))
    amenities = db.Column(db.String(255), nullable=True, default='Wi-Fi, TV, Geyser, Room Service, Safe')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    rooms = db.relationship('Room', back_populates='category', lazy='selectin')

    def __repr__(self):
        return f'<RoomCategory {self.name} (₹{self.base_price})>'


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id', ondelete='RESTRICT'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('room_categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default=RoomStatus.AVAILABLE, index=True)
    max_occupancy = db.Column(db.Integer, nullable=False, default=2)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    floor = db.relationship('Floor', back_populates='rooms')
    category = db.relationship('RoomCategory', back_populates='rooms')
    stays = db.relationship('Stay', back_populates='room', lazy='dynamic')
    booking_rooms = db.relationship('BookingRoom', back_populates='room', lazy='dynamic')

    @property
    def current_active_stay(self):
        from app.models.booking import Stay
        return Stay.query.filter_by(room_id=self.id, status='Active').first()

    def __repr__(self):
        return f'<Room {self.room_number} ({self.status})>'
