"""Billing and invoice calculation service using Python Decimal."""
import json
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List
from app.extensions import db
from app.models.hotel import HotelSettings
from app.models.booking import Booking, Stay
from app.models.billing import Invoice, InvoiceLineItem, Payment, GuestFolioCharge, InvoiceStatus


def quantize_amount(val: Any) -> Decimal:
    """Safely convert any numeric value into Decimal with 2 decimal places."""
    if val is None:
        return Decimal('0.00')
    if isinstance(val, (int, float, str)):
        dec = Decimal(str(val))
    elif isinstance(val, Decimal):
        dec = val
    else:
        dec = Decimal('0.00')
    return dec.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_stay_billing(booking: Booking, stay: Stay = None, late_hours: float = 0.0, apply_early_fee: bool = False, discount: Decimal = None) -> Dict[str, Any]:
    """
    Computes an itemized preview or breakdown of the stay charges.
    Returns a dictionary of line items, subtotal, tax breakdown, total paid, and balance due.
    """
    settings = HotelSettings.get_settings()
    nights = max(1, booking.total_nights)
    if stay and stay.actual_checkin and stay.actual_checkout:
        stay_nights = max(1, (stay.actual_checkout.date() - stay.actual_checkin.date()).days)
        nights = stay_nights

    items = []
    subtotal = Decimal('0.00')
    total_tax = Decimal('0.00')

    room_tax_rate = quantize_amount(settings.room_tax_rate)

    # 1. Room Night Charges
    for br in booking.booking_rooms:
        rate = quantize_amount(br.rate_per_night or booking.agreed_rate_per_night)
        room_line_total = quantize_amount(rate * nights)
        tax = quantize_amount(room_line_total * (room_tax_rate / Decimal('100.00')))
        
        items.append({
            'item_type': 'room',
            'description': f"Room {br.room.room_number if br.room else 'Accommodation'} - {nights} night(s) @ ₹{rate}/night",
            'quantity': Decimal(nights),
            'unit_price': rate,
            'total_price': room_line_total,
            'tax_rate': room_tax_rate,
            'tax_amount': tax
        })
        subtotal += room_line_total
        total_tax += tax

        # Extra bed charge per room
        if br.has_extra_bed and br.extra_bed_charge > 0:
            bed_rate = quantize_amount(br.extra_bed_charge)
            bed_total = quantize_amount(bed_rate * nights)
            bed_tax = quantize_amount(bed_total * (room_tax_rate / Decimal('100.00')))
            items.append({
                'item_type': 'extra_bed',
                'description': f"Extra Bed (Room {br.room.room_number}) - {nights} night(s)",
                'quantity': Decimal(nights),
                'unit_price': bed_rate,
                'total_price': bed_total,
                'tax_rate': room_tax_rate,
                'tax_amount': bed_tax
            })
            subtotal += bed_total
            total_tax += bed_tax

    # 2. Extra Person Charge (if applicable on booking level)
    if booking.extra_person_charge > 0:
        ep_rate = quantize_amount(booking.extra_person_charge)
        ep_total = quantize_amount(ep_rate * nights)
        ep_tax = quantize_amount(ep_total * (room_tax_rate / Decimal('100.00')))
        items.append({
            'item_type': 'extra_person',
            'description': f"Extra Person Charge - {nights} night(s)",
            'quantity': Decimal(nights),
            'unit_price': ep_rate,
            'total_price': ep_total,
            'tax_rate': room_tax_rate,
            'tax_amount': ep_tax
        })
        subtotal += ep_total
        total_tax += ep_tax

    # 3. Early Check-in Fee
    if apply_early_fee or (stay and stay.early_checkin_applied):
        early_fee = quantize_amount(settings.early_checkin_fee)
        if early_fee > 0:
            early_tax = quantize_amount(early_fee * (room_tax_rate / Decimal('100.00')))
            items.append({
                'item_type': 'early_late',
                'description': "Early Check-in Service Fee",
                'quantity': Decimal('1.00'),
                'unit_price': early_fee,
                'total_price': early_fee,
                'tax_rate': room_tax_rate,
                'tax_amount': early_tax
            })
            subtotal += early_fee
            total_tax += early_tax

    # 4. Late Check-out Fee
    if late_hours > 0 or (stay and stay.late_checkout_applied):
        hourly_rate = quantize_amount(settings.late_checkout_hourly_fee)
        hours = Decimal(str(round(late_hours, 1))) if late_hours > 0 else Decimal('1.00')
        late_fee = quantize_amount(hourly_rate * hours)
        if late_fee > 0:
            late_tax = quantize_amount(late_fee * (room_tax_rate / Decimal('100.00')))
            items.append({
                'item_type': 'early_late',
                'description': f"Late Check-out Fee ({hours} hr(s))",
                'quantity': hours,
                'unit_price': hourly_rate,
                'total_price': late_fee,
                'tax_rate': room_tax_rate,
                'tax_amount': late_tax
            })
            subtotal += late_fee
            total_tax += late_tax

    # 5. Posted Folio Charges (Restaurant / Room Service)
    folio_charges = GuestFolioCharge.query.filter_by(booking_id=booking.id, is_billed=False).all()
    rest_tax_rate = quantize_amount(settings.restaurant_tax_rate)
    for fc in folio_charges:
        charge_amt = quantize_amount(fc.amount)
        # Check if tax is already inside or added
        items.append({
            'item_type': fc.charge_type,
            'description': f"{fc.description}",
            'quantity': Decimal('1.00'),
            'unit_price': charge_amt,
            'total_price': charge_amt,
            'tax_rate': Decimal('0.00'),  # Already taxed at POS or inclusive
            'tax_amount': Decimal('0.00'),
            'folio_charge_id': fc.id
        })
        subtotal += charge_amt

    # 6. Additional Miscellaneous charges on booking
    if booking.additional_charges > 0:
        add_charge = quantize_amount(booking.additional_charges)
        items.append({
            'item_type': 'other',
            'description': "Additional Services / Amenities",
            'quantity': Decimal('1.00'),
            'unit_price': add_charge,
            'total_price': add_charge,
            'tax_rate': Decimal('0.00'),
            'tax_amount': Decimal('0.00')
        })
        subtotal += add_charge

    # Discount
    applied_discount = quantize_amount(discount if discount is not None else booking.discount_amount)
    grand_total = quantize_amount(subtotal + total_tax - applied_discount)
    if grand_total < Decimal('0.00'):
        grand_total = Decimal('0.00')

    # Payments already made
    total_paid = quantize_amount(
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter(Payment.booking_id == booking.id)
        .scalar()
    )

    balance_due = quantize_amount(grand_total - total_paid)

    return {
        'items': items,
        'subtotal': subtotal,
        'tax_rate': room_tax_rate,
        'tax_amount': total_tax,
        'discount_amount': applied_discount,
        'grand_total': grand_total,
        'total_paid': total_paid,
        'balance_due': balance_due,
        'nights': nights
    }


def finalize_invoice(booking: Booking, user_id: int, stay: Stay = None, late_hours: float = 0.0, apply_early_fee: bool = False, discount: Decimal = None, notes: str = None) -> Invoice:
    """
    Creates and finalizes an immutable Invoice record with line items and snapshot JSON.
    """
    settings = HotelSettings.get_settings()
    calc = calculate_stay_billing(booking, stay=stay, late_hours=late_hours, apply_early_fee=apply_early_fee, discount=discount)

    # Generate invoice number
    timestamp_str = datetime.utcnow().strftime('%Y%m%d')
    count = Invoice.query.filter(Invoice.created_at >= datetime.utcnow().date()).count() + 1
    inv_number = f"{settings.invoice_prefix}{timestamp_str}-{count:04d}"

    invoice = Invoice(
        invoice_number=inv_number,
        booking_id=booking.id,
        guest_id=booking.guest_id,
        stay_id=stay.id if stay else None,
        status=InvoiceStatus.PAID if calc['balance_due'] <= Decimal('0.00') else InvoiceStatus.FINALIZED,
        subtotal=calc['subtotal'],
        tax_rate=calc['tax_rate'],
        tax_amount=calc['tax_amount'],
        discount_amount=calc['discount_amount'],
        grand_total=calc['grand_total'],
        paid_amount=calc['total_paid'],
        balance_amount=calc['balance_due'],
        created_at=datetime.utcnow(),
        finalized_at=datetime.utcnow(),
        finalized_by_id=user_id,
        notes=notes
    )
    db.session.add(invoice)
    db.session.flush()

    # Create line items
    snapshot_items = []
    for itm in calc['items']:
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            item_type=itm['item_type'],
            description=itm['description'],
            quantity=itm['quantity'],
            unit_price=itm['unit_price'],
            total_price=itm['total_price'],
            tax_rate=itm['tax_rate'],
            tax_amount=itm['tax_amount']
        )
        db.session.add(line_item)
        snapshot_items.append({
            'item_type': itm['item_type'],
            'description': itm['description'],
            'quantity': str(itm['quantity']),
            'unit_price': str(itm['unit_price']),
            'total_price': str(itm['total_price']),
            'tax_rate': str(itm['tax_rate']),
            'tax_amount': str(itm['tax_amount'])
        })

        # Mark folio charges as billed
        if 'folio_charge_id' in itm:
            fc = GuestFolioCharge.query.get(itm['folio_charge_id'])
            if fc:
                fc.is_billed = True

    # Link existing advance payments to this invoice
    existing_payments = Payment.query.filter_by(booking_id=booking.id, invoice_id=None).all()
    snapshot_payments = []
    for p in existing_payments:
        p.invoice_id = invoice.id
        snapshot_payments.append({
            'receipt_number': p.receipt_number,
            'amount': str(p.amount),
            'method': p.payment_method,
            'date': p.payment_date.strftime('%Y-%m-%d %H:%M'),
            'transaction_ref': p.transaction_ref
        })

    # Build full snapshot JSON for archival immutability
    snapshot_data = {
        'invoice_number': inv_number,
        'hotel_name': settings.hotel_name,
        'hotel_address': f"{settings.address_line}, {settings.city}, {settings.state} - {settings.pincode}",
        'hotel_phone': settings.phone,
        'hotel_email': settings.email,
        'hotel_gstin': settings.gstin,
        'currency_symbol': settings.currency_symbol,
        'guest_name': booking.guest.full_name,
        'guest_mobile': booking.guest.mobile,
        'guest_email': booking.guest.email,
        'guest_id_type': booking.guest.id_type,
        'guest_id_number': booking.guest.id_number,
        'booking_number': booking.booking_number,
        'rooms': booking.assigned_room_numbers,
        'checkin_date': booking.checkin_date.strftime('%Y-%m-%d'),
        'checkout_date': booking.checkout_date.strftime('%Y-%m-%d'),
        'actual_checkin': stay.actual_checkin.strftime('%Y-%m-%d %H:%M') if (stay and stay.actual_checkin) else None,
        'actual_checkout': stay.actual_checkout.strftime('%Y-%m-%d %H:%M') if (stay and stay.actual_checkout) else None,
        'nights': calc['nights'],
        'subtotal': str(calc['subtotal']),
        'tax_rate': str(calc['tax_rate']),
        'tax_amount': str(calc['tax_amount']),
        'discount_amount': str(calc['discount_amount']),
        'grand_total': str(calc['grand_total']),
        'paid_amount': str(calc['total_paid']),
        'balance_amount': str(calc['balance_due']),
        'items': snapshot_items,
        'payments': snapshot_payments,
        'finalized_at': invoice.finalized_at.strftime('%Y-%m-%d %H:%M:%S')
    }
    invoice.snapshot_json = json.dumps(snapshot_data)

    db.session.commit()
    return invoice


def record_payment(booking_id: int, amount: Decimal, payment_method: str, user_id: int, invoice_id: int = None, transaction_ref: str = None, notes: str = None, is_advance: bool = False) -> Payment:
    """Records a payment receipt against a booking and/or invoice."""
    booking = Booking.query.get_or_404(booking_id)
    settings = HotelSettings.get_settings()
    
    timestamp_str = datetime.utcnow().strftime('%Y%m%d')
    count = Payment.query.filter(Payment.payment_date >= datetime.utcnow().date()).count() + 1
    receipt_number = f"RCP-{timestamp_str}-{count:04d}"

    quantized_amt = quantize_amount(amount)

    payment = Payment(
        receipt_number=receipt_number,
        invoice_id=invoice_id,
        booking_id=booking.id,
        guest_id=booking.guest_id,
        amount=quantized_amt,
        payment_method=payment_method,
        transaction_ref=transaction_ref,
        notes=notes,
        is_advance=is_advance,
        received_by_id=user_id,
        payment_date=datetime.utcnow()
    )
    db.session.add(payment)

    # If linked to invoice, recalculate invoice balance
    if invoice_id:
        invoice = Invoice.query.get(invoice_id)
        if invoice:
            invoice.paid_amount = quantize_amount(invoice.paid_amount + quantized_amt)
            invoice.balance_amount = quantize_amount(invoice.grand_total - invoice.paid_amount)
            if invoice.balance_amount <= Decimal('0.00'):
                invoice.status = InvoiceStatus.PAID

    db.session.commit()
    return payment
