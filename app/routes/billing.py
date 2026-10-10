"""Billing, Invoices, Payments, and PDF generation routes."""
import io
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from app.extensions import db
from app.models.hotel import HotelSettings
from app.models.billing import Invoice, InvoiceLineItem, Payment, InvoiceStatus
from app.models.booking import Booking, Guest
from app.forms.billing import PaymentForm
from app.services.billing_service import record_payment, quantize_amount
from app.services.audit_service import log_activity
from app.utils.pdf_generator import generate_invoice_pdf
from app.utils.decorators import receptionist_required

billing_bp = Blueprint('billing', __name__)


@billing_bp.route('/')
@login_required
def index():
    status_filter = request.args.get('status', '')
    search_query = request.args.get('q', '').strip()

    query = Invoice.query.join(Guest)

    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if search_query:
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(f"%{search_query}%"),
                Guest.full_name.ilike(f"%{search_query}%"),
                Guest.mobile.ilike(f"%{search_query}%")
            )
        )

    invoices = query.order_by(Invoice.finalized_at.desc()).all()

    total_billed = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(Invoice.status != 'Cancelled').scalar()
    total_received = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    total_outstanding = db.session.query(func.coalesce(func.sum(Invoice.balance_amount), 0)).filter(Invoice.status != 'Cancelled').scalar()

    return render_template(
        'billing/index.html',
        invoices=invoices,
        status_filter=status_filter,
        search_query=search_query,
        total_billed=total_billed,
        total_received=total_received,
        total_outstanding=total_outstanding,
        InvoiceStatus=InvoiceStatus
    )


@billing_bp.route('/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    settings = HotelSettings.get_settings()
    payment_form = PaymentForm()
    return render_template('billing/invoice_view.html', invoice=invoice, settings=settings, payment_form=payment_form)


@billing_bp.route('/invoice/<int:invoice_id>/print')
@login_required
def print_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    settings = HotelSettings.get_settings()
    return render_template('billing/invoice_print.html', invoice=invoice, settings=settings)


@billing_bp.route('/invoice/<int:invoice_id>/pdf')
@login_required
def download_pdf(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    pdf_buffer = generate_invoice_pdf(invoice)
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@billing_bp.route('/invoice/<int:invoice_id>/pay', methods=['POST'])
@login_required
@receptionist_required
def add_payment(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    form = PaymentForm()

    if form.validate_on_submit():
        amt = quantize_amount(form.amount.data)
        if amt <= Decimal('0.00'):
            flash("Payment amount must be greater than zero.", "danger")
            return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))

        payment = record_payment(
            booking_id=invoice.booking_id,
            amount=amt,
            payment_method=form.payment_method.data,
            user_id=current_user.id,
            invoice_id=invoice.id,
            transaction_ref=form.transaction_ref.data,
            notes=form.notes.data
        )

        log_activity('RECORD_PAYMENT', 'Invoice', invoice.id, f"Recorded payment {payment.receipt_number} of ₹{amt} via {payment.payment_method}")
        flash(f"Payment of ₹{amt:,.2f} recorded successfully (Receipt #{payment.receipt_number}).", "success")
        return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))

    flash("Invalid payment form submission.", "danger")
    return redirect(url_for('billing.view_invoice', invoice_id=invoice.id))


@billing_bp.route('/receipt/<int:payment_id>/print')
@login_required
def print_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    settings = HotelSettings.get_settings()
    return render_template('billing/receipt_print.html', payment=payment, settings=settings)
