"""Test Billing, Invoice finalization, Decimal calculations, and PDF generation."""
from datetime import date, datetime
from decimal import Decimal
from app.extensions import db
from app.models.hotel import Room, RoomCategory, HotelSettings
from app.models.booking import Guest, Booking, BookingRoom, Stay
from app.models.billing import Invoice, Payment
from app.services.billing_service import calculate_stay_billing, finalize_invoice, record_payment
from app.utils.pdf_generator import generate_invoice_pdf


def test_stay_billing_calculation_with_decimal(app):
    with app.app_context():
        settings = HotelSettings.get_settings()
        guest = Guest(full_name="Billing Test Guest", mobile="9811122233")
        db.session.add(guest)
        db.session.flush()

        cat = RoomCategory.query.first()
        room = Room.query.filter_by(room_number="101").first()

        booking = Booking(
            booking_number="BK-BILL-TEST",
            guest_id=guest.id,
            room_category_id=cat.id,
            checkin_date=date(2026, 10, 1),
            checkout_date=date(2026, 10, 4),  # 3 nights
            total_nights=3,
            agreed_rate_per_night=Decimal("2000.00"),
            extra_bed_charge=Decimal("500.00"),
            discount_amount=Decimal("200.00")
        )
        db.session.add(booking)
        db.session.flush()

        br = BookingRoom(
            booking_id=booking.id,
            room_id=room.id,
            rate_per_night=Decimal("2000.00"),
            has_extra_bed=True,
            extra_bed_charge=Decimal("500.00")
        )
        db.session.add(br)
        db.session.commit()

        # Calculation:
        # Room: 2000 * 3 = 6000
        # Extra bed: 500 * 3 = 1500
        # Subtotal = 7500.00
        # Tax: 12% of 7500 = 900.00
        # Discount = 200.00
        # Grand total = 7500 + 900 - 200 = 8200.00
        calc = calculate_stay_billing(booking)
        assert calc['subtotal'] == Decimal("7500.00")
        assert calc['tax_amount'] == Decimal("900.00")
        assert calc['discount_amount'] == Decimal("200.00")
        assert calc['grand_total'] == Decimal("8200.00")


def test_invoice_finalization_and_pdf_generation(app):
    with app.app_context():
        guest = Guest(full_name="PDF Test Guest", mobile="9988776655")
        db.session.add(guest)
        db.session.flush()

        cat = RoomCategory.query.first()
        room = Room.query.filter_by(room_number="101").first()

        booking = Booking(
            booking_number="BK-INV-PDF",
            guest_id=guest.id,
            room_category_id=cat.id,
            checkin_date=date(2026, 10, 1),
            checkout_date=date(2026, 10, 3),
            total_nights=2,
            agreed_rate_per_night=Decimal("2000.00")
        )
        db.session.add(booking)
        db.session.flush()

        br = BookingRoom(booking_id=booking.id, room_id=room.id, rate_per_night=Decimal("2000.00"))
        db.session.add(br)
        db.session.commit()

        # Finalize invoice
        inv = finalize_invoice(booking=booking, user_id=1)
        assert inv is not None
        assert inv.invoice_number.startswith("INV-")
        assert inv.snapshot_json is not None
        assert "PDF Test Guest" in inv.snapshot_json

        # Test PDF generator output
        pdf_buffer = generate_invoice_pdf(inv)
        assert pdf_buffer is not None
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 500  # Valid binary PDF stream generated
