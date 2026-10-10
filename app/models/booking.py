"""Guest, Booking, BookingRoom, and Stay models."""
from datetime import datetime, date
from decimal import Decimal
from app.extensions import db


class BookingStatus:
    PENDING = 'Pending'
    CONFIRMED = 'Confirmed'
    CHECKED_IN = 'Checked In'
    CHECKED_OUT = 'Checked Out'
    CANCELLED = 'Cancelled'
    NO_SHOW = 'No-Show'

    CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (CHECKED_IN, 'Checked In'),
        (CHECKED_OUT, 'Checked Out'),
        (CANCELLED, 'Cancelled'),
        (NO_SHOW, 'No-Show')
    ]

    COLORS = {
        PENDING: 'warning',
        CONFIRMED: 'primary',
        CHECKED_IN: 'success',
        CHECKED_OUT: 'secondary',
        CANCELLED: 'danger',
        NO_SHOW: 'dark'
    }


class Guest(db.Model):
    __tablename__ = 'guests'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False, index=True)
    mobile = db.Column(db.String(30), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True, default='India')
    id_type = db.Column(db.String(50), nullable=False, default='Aadhaar Card')
    id_number = db.Column(db.String(100), nullable=True)
    emergency_contact = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = db.relationship('Booking', back_populates='guest', cascade='all, delete-orphan', lazy='dynamic')
    stays = db.relationship('Stay', back_populates='guest', lazy='dynamic')
    invoices = db.relationship('Invoice', back_populates='guest', lazy='dynamic')

    def __repr__(self):
        return f'<Guest {self.full_name} ({self.mobile})>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False, index=True)
    room_category_id = db.Column(db.Integer, db.ForeignKey('room_categories.id', ondelete='SET NULL'), nullable=True)
    
    booking_source = db.Column(db.String(32), nullable=False, default='Walk-in')  # Walk-in, Phone, Online, Corporate
    status = db.Column(db.String(32), nullable=False, default=BookingStatus.CONFIRMED, index=True)
    
    checkin_date = db.Column(db.Date, nullable=False, index=True)
    checkout_date = db.Column(db.Date, nullable=False, index=True)
    expected_checkin_time = db.Column(db.String(10), nullable=False, default='14:00')
    expected_checkout_time = db.Column(db.String(10), nullable=False, default='11:00')
    
    adults_count = db.Column(db.Integer, nullable=False, default=1)
    children_count = db.Column(db.Integer, nullable=False, default=0)
    total_nights = db.Column(db.Integer, nullable=False, default=1)
    
    # Financial snapshot per booking (preserves historical rates)
    agreed_rate_per_night = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    extra_bed_charge = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    extra_person_charge = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    additional_charges = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    advance_payment = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    payment_method = db.Column(db.String(50), nullable=True, default='Cash')
    
    special_requests = db.Column(db.Text, nullable=True)
    internal_notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    guest = db.relationship('Guest', back_populates='bookings')
    room_category = db.relationship('RoomCategory')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    booking_rooms = db.relationship('BookingRoom', back_populates='booking', cascade='all, delete-orphan', lazy='selectin')
    stays = db.relationship('Stay', back_populates='booking', cascade='all, delete-orphan', lazy='selectin')
    invoices = db.relationship('Invoice', back_populates='booking', lazy='dynamic')
    folio_charges = db.relationship('GuestFolioCharge', back_populates='booking', lazy='dynamic')

    @property
    def assigned_room_numbers(self):
        return [br.room.room_number for br in self.booking_rooms if br.room]

    @property
    def primary_room(self):
        if self.booking_rooms:
            return self.booking_rooms[0].room
        return None

    @property
    def active_stay(self):
        for stay in self.stays:
            if stay.status == 'Active':
                return stay
        return None

    def __repr__(self):
        return f'<Booking {self.booking_number} ({self.status})>'


class BookingRoom(db.Model):
    __tablename__ = 'booking_rooms'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='RESTRICT'), nullable=False, index=True)
    rate_per_night = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    has_extra_bed = db.Column(db.Boolean, default=False, nullable=False)
    extra_bed_charge = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))

    booking = db.relationship('Booking', back_populates='booking_rooms')
    room = db.relationship('Room', back_populates='booking_rooms')

    def __repr__(self):
        return f'<BookingRoom B:{self.booking_id} R:{self.room_id}>'


class Stay(db.Model):
    """Represents the physical occupancy / stay period for a guest in a room."""
    __tablename__ = 'stays'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    planned_checkin = db.Column(db.DateTime, nullable=False)
    planned_checkout = db.Column(db.DateTime, nullable=False)
    actual_checkin = db.Column(db.DateTime, nullable=True)
    actual_checkout = db.Column(db.DateTime, nullable=True)
    
    status = db.Column(db.String(32), nullable=False, default='Active', index=True)  # Active, Completed, Cancelled
    
    checked_in_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    checked_out_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    early_checkin_applied = db.Column(db.Boolean, default=False, nullable=False)
    late_checkout_applied = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    booking = db.relationship('Booking', back_populates='stays')
    guest = db.relationship('Guest', back_populates='stays')
    room = db.relationship('Room', back_populates='stays')
    checked_in_by = db.relationship('User', foreign_keys=[checked_in_by_id])
    checked_out_by = db.relationship('User', foreign_keys=[checked_out_by_id])

    @property
    def is_overdue(self) -> bool:
        if self.status != 'Active':
            return False
        return datetime.utcnow() > self.planned_checkout

    @property
    def overdue_duration_hours(self) -> float:
        if not self.is_overdue:
            return 0.0
        delta = datetime.utcnow() - self.planned_checkout
        return max(0.0, delta.total_seconds() / 3600.0)

    def __repr__(self):
        return f'<Stay {self.id} Room:{self.room_id} Status:{self.status}>'
