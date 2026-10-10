"""Billing, Invoice, InvoiceLineItem, Payment, and GuestFolioCharge models."""
from datetime import datetime
from decimal import Decimal
from app.extensions import db


class InvoiceStatus:
    DRAFT = 'Draft'
    FINALIZED = 'Finalized'
    PAID = 'Paid'
    CANCELLED = 'Cancelled'

    CHOICES = [
        (DRAFT, 'Draft'),
        (FINALIZED, 'Finalized'),
        (PAID, 'Paid'),
        (CANCELLED, 'Cancelled')
    ]

    COLORS = {
        DRAFT: 'secondary',
        FINALIZED: 'primary',
        PAID: 'success',
        CANCELLED: 'danger'
    }


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False, index=True)
    stay_id = db.Column(db.Integer, db.ForeignKey('stays.id', ondelete='SET NULL'), nullable=True)
    
    status = db.Column(db.String(32), nullable=False, default=InvoiceStatus.FINALIZED, index=True)
    
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('12.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    grand_total = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    paid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    balance_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finalized_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finalized_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    snapshot_json = db.Column(db.Text, nullable=True)  # Full JSON snapshot of billing data

    booking = db.relationship('Booking', back_populates='invoices')
    guest = db.relationship('Guest', back_populates='invoices')
    stay = db.relationship('Stay')
    finalized_by = db.relationship('User', foreign_keys=[finalized_by_id])
    
    items = db.relationship('InvoiceLineItem', back_populates='invoice', cascade='all, delete-orphan', lazy='selectin')
    payments = db.relationship('Payment', back_populates='invoice', cascade='all, delete-orphan', lazy='selectin')

    @property
    def is_paid_in_full(self) -> bool:
        return self.balance_amount <= Decimal('0.00')

    def __repr__(self):
        return f'<Invoice {self.invoice_number} (₹{self.grand_total})>'


class InvoiceLineItem(db.Model):
    __tablename__ = 'invoice_line_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False, index=True)
    
    item_type = db.Column(db.String(32), nullable=False, default='room')  # room, restaurant, extra_bed, early_late, service, other
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(6, 2), nullable=False, default=Decimal('1.00'))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    total_price = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('0.00'))
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))

    invoice = db.relationship('Invoice', back_populates='items')

    def __repr__(self):
        return f'<InvoiceLineItem {self.description} ({self.total_price})>'


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=True, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    payment_method = db.Column(db.String(50), nullable=False, default='Cash')  # Cash, Card, UPI, Bank Transfer, Online
    transaction_ref = db.Column(db.String(100), nullable=True)
    is_advance = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    
    received_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    invoice = db.relationship('Invoice', back_populates='payments')
    booking = db.relationship('Booking')
    guest = db.relationship('Guest')
    received_by = db.relationship('User', foreign_keys=[received_by_id])

    def __repr__(self):
        return f'<Payment {self.receipt_number} ₹{self.amount} ({self.payment_method})>'


class GuestFolioCharge(db.Model):
    """Auxiliary charges such as restaurant orders, minibar, or laundry posted to room stay."""
    __tablename__ = 'guest_folio_charges'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False, index=True)
    stay_id = db.Column(db.Integer, db.ForeignKey('stays.id', ondelete='SET NULL'), nullable=True)
    
    charge_type = db.Column(db.String(32), nullable=False, default='restaurant')  # restaurant, laundry, room_service, other
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))
    reference_order_id = db.Column(db.Integer, nullable=True)  # RestaurantOrder id if applicable
    
    posted_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    posted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_billed = db.Column(db.Boolean, default=False, nullable=False)  # True once added to finalized invoice

    booking = db.relationship('Booking', back_populates='folio_charges')
    guest = db.relationship('Guest')
    stay = db.relationship('Stay')
    posted_by = db.relationship('User', foreign_keys=[posted_by_id])

    def __repr__(self):
        return f'<GuestFolioCharge {self.charge_type}: ₹{self.amount} (Billed:{self.is_billed})>'
