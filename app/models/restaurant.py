"""Restaurant, Table, Reservation, Menu, and Order models."""
from datetime import datetime, date, time
from decimal import Decimal
from app.extensions import db


class TableStatus:
    AVAILABLE = 'Available'
    RESERVED = 'Reserved'
    OCCUPIED = 'Occupied'
    CLEANING = 'Cleaning'
    OUT_OF_SERVICE = 'Out of Service'

    CHOICES = [
        (AVAILABLE, 'Available'),
        (RESERVED, 'Reserved'),
        (OCCUPIED, 'Occupied'),
        (CLEANING, 'Cleaning'),
        (OUT_OF_SERVICE, 'Out of Service')
    ]

    COLORS = {
        AVAILABLE: 'success',
        RESERVED: 'warning',
        OCCUPIED: 'danger',
        CLEANING: 'info',
        OUT_OF_SERVICE: 'dark'
    }


class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'

    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    section = db.Column(db.String(50), nullable=False, default='Indoor')  # Indoor, Outdoor, Family, Rooftop, Bar
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(32), nullable=False, default=TableStatus.AVAILABLE, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    floor = db.relationship('Floor')
    reservations = db.relationship('TableReservation', back_populates='table', lazy='dynamic')
    orders = db.relationship('RestaurantOrder', back_populates='table', lazy='dynamic')

    @property
    def current_active_order(self):
        return self.orders.filter(RestaurantOrder.status.in_(['Pending', 'In Progress', 'Served'])).first()

    def __repr__(self):
        return f'<Table {self.table_number} ({self.status}, cap:{self.capacity})>'


class TableReservation(db.Model):
    __tablename__ = 'table_reservations'

    id = db.Column(db.Integer, primary_key=True)
    reservation_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id', ondelete='CASCADE'), nullable=False, index=True)
    
    customer_name = db.Column(db.String(120), nullable=False, index=True)
    contact_number = db.Column(db.String(30), nullable=False)
    reservation_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM
    end_time = db.Column(db.String(10), nullable=False)    # HH:MM
    guest_count = db.Column(db.Integer, nullable=False, default=2)
    
    special_requests = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default='Confirmed', index=True)  # Confirmed, Seated, Completed, Cancelled, No-Show
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    table = db.relationship('RestaurantTable', back_populates='reservations')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<TableReservation {self.reservation_number} T:{self.table_id} ({self.status})>'


class MenuCategory(db.Model):
    __tablename__ = 'menu_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    items = db.relationship('MenuItem', back_populates='category', cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<MenuCategory {self.name}>'


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00'))
    is_veg = db.Column(db.Boolean, default=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)

    category = db.relationship('MenuCategory', back_populates='items')

    def __repr__(self):
        return f'<MenuItem {self.name} (₹{self.price})>'


class RestaurantOrder(db.Model):
    __tablename__ = 'restaurant_orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    order_type = db.Column(db.String(32), nullable=False, default='Dine-In')  # Dine-In, Takeaway, Room-Service
    
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id', ondelete='SET NULL'), nullable=True, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='SET NULL'), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='SET NULL'), nullable=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='SET NULL'), nullable=True)
    
    customer_name = db.Column(db.String(100), nullable=True)
    customer_phone = db.Column(db.String(30), nullable=True)
    waiter_name = db.Column(db.String(100), nullable=True)
    
    status = db.Column(db.String(32), nullable=False, default='Pending', index=True)  # Pending, In Progress, Served, Paid, Cancelled
    payment_status = db.Column(db.String(32), nullable=False, default='Pending', index=True)  # Pending, Paid, Posted to Room
    payment_method = db.Column(db.String(50), nullable=True, default='Cash')
    
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('5.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    grand_total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    table = db.relationship('RestaurantTable', back_populates='orders')
    room = db.relationship('Room')
    booking = db.relationship('Booking')
    guest = db.relationship('Guest')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    items = db.relationship('RestaurantOrderItem', back_populates='order', cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<RestaurantOrder {self.order_number} ({self.status}) ₹{self.grand_total}>'


class RestaurantOrderItem(db.Model):
    __tablename__ = 'restaurant_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('restaurant_orders.id', ondelete='CASCADE'), nullable=False, index=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id', ondelete='SET NULL'), nullable=True)
    
    item_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    special_notes = db.Column(db.String(255), nullable=True)

    order = db.relationship('RestaurantOrder', back_populates='items')
    menu_item = db.relationship('MenuItem')

    def __repr__(self):
        return f'<OrderItem {self.item_name} x{self.quantity}>'
