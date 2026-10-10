"""PDF generation utility for invoices and receipts using ReportLab."""
import io
import json
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.models.billing import Invoice
from app.models.hotel import HotelSettings


def generate_invoice_pdf(invoice: Invoice) -> io.BytesIO:
    """Generate a high quality, clean PDF invoice using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    settings = HotelSettings.get_settings()
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748b')
    )
    inv_title_style = ParagraphStyle(
        'InvTitle',
        parent=styles['Heading2'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#4f46e5'),
        alignment=2,  # Right aligned
        fontName='Helvetica-Bold'
    )
    inv_meta_style = ParagraphStyle(
        'InvMeta',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        alignment=2
    )
    section_head_style = ParagraphStyle(
        'SecHead',
        parent=styles['Heading3'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    table_text_style = ParagraphStyle(
        'TText',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    table_head_style = ParagraphStyle(
        'THead',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )

    story = []

    # Header Table: Hotel Details (Left) + Invoice Info (Right)
    hotel_info = f"""<b>{settings.hotel_name}</b><br/>
{settings.tagline or ''}<br/>
{settings.address_line or ''}, {settings.city or ''}, {settings.state or ''} - {settings.pincode or ''}<br/>
Phone: {settings.phone or ''} | Email: {settings.email or ''}<br/>
GSTIN: {settings.gstin or 'N/A'}
"""
    inv_info = f"""<b>TAX INVOICE</b><br/>
Invoice #: <b>{invoice.invoice_number}</b><br/>
Date: {invoice.finalized_at.strftime('%d %b %Y')}<br/>
Booking Ref: {invoice.booking.booking_number}<br/>
Status: <b>{invoice.status.upper()}</b>
"""

    header_data = [
        [Paragraph(hotel_info, subtitle_style), Paragraph(inv_info, inv_meta_style)]
    ]
    header_table = Table(header_data, colWidths=[4.0 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    # Guest Details & Stay Info Table
    guest = invoice.guest
    guest_details = f"""<b>Billed To:</b><br/>
<b>{guest.full_name}</b><br/>
Mobile: {guest.mobile}<br/>
Email: {guest.email or 'N/A'}<br/>
ID: {guest.id_type} ({guest.id_number or 'Verified'})<br/>
Address: {guest.address or ''} {guest.city or ''}
"""
    rooms_str = ", ".join(invoice.booking.assigned_room_numbers) if invoice.booking.assigned_room_numbers else "N/A"
    stay_details = f"""<b>Stay Particulars:</b><br/>
Room(s): <b>{rooms_str}</b><br/>
Check-in: {invoice.booking.checkin_date.strftime('%d %b %Y')} ({invoice.booking.expected_checkin_time})<br/>
Check-out: {invoice.booking.checkout_date.strftime('%d %b %Y')} ({invoice.booking.expected_checkout_time})<br/>
Nights: {invoice.booking.total_nights} | Guests: {invoice.booking.adults_count} Adults, {invoice.booking.children_count} Kids
"""

    guest_stay_data = [
        [Paragraph(guest_details, subtitle_style), Paragraph(stay_details, subtitle_style)]
    ]
    guest_stay_table = Table(guest_stay_data, colWidths=[3.75 * inch, 3.75 * inch])
    guest_stay_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(guest_stay_table)
    story.append(Spacer(1, 15))

    # Line Items Table
    item_rows = [
        [
            Paragraph("<b>#</b>", table_head_style),
            Paragraph("<b>Description</b>", table_head_style),
            Paragraph("<b>Qty / Nights</b>", table_head_style),
            Paragraph("<b>Rate (₹)</b>", table_head_style),
            Paragraph("<b>Tax (₹)</b>", table_head_style),
            Paragraph("<b>Total (₹)</b>", table_head_style)
        ]
    ]

    for idx, item in enumerate(invoice.items, start=1):
        item_rows.append([
            Paragraph(str(idx), table_text_style),
            Paragraph(item.description, table_text_style),
            Paragraph(str(item.quantity), table_text_style),
            Paragraph(f"{item.unit_price:,.2f}", table_text_style),
            Paragraph(f"{item.tax_amount:,.2f}", table_text_style),
            Paragraph(f"{item.total_price:,.2f}", table_text_style)
        ])

    items_table = Table(item_rows, colWidths=[0.3 * inch, 3.2 * inch, 0.9 * inch, 1.0 * inch, 0.9 * inch, 1.2 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 12))

    # Summary Totals Table
    summary_data = [
        ['', 'Subtotal:', f"₹ {invoice.subtotal:,.2f}"],
        ['', f"Taxes (GST):", f"₹ {invoice.tax_amount:,.2f}"],
        ['', 'Discount:', f"- ₹ {invoice.discount_amount:,.2f}"],
        ['', 'Grand Total:', f"₹ {invoice.grand_total:,.2f}"],
        ['', 'Total Paid:', f"₹ {invoice.paid_amount:,.2f}"],
        ['', 'Balance Due:', f"₹ {invoice.balance_amount:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[4.0 * inch, 2.0 * inch, 1.5 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 3), (-1, 3), 'Helvetica-Bold'),
        ('FONTNAME', (1, 5), (-1, 5), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1, 5), (-1, 5), colors.HexColor('#e11d48') if invoice.balance_amount > 0 else colors.HexColor('#059669')),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (1, 3), (-1, 3), 1, colors.HexColor('#cbd5e1')),
        ('LINEABOVE', (1, 5), (-1, 5), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 15))

    # Footer note
    footer_text = f"""Thank you for staying at <b>{settings.hotel_name}</b>.<br/>
For any billing queries, please contact front desk at {settings.phone} or {settings.email}.<br/>
<i>This is a computer generated invoice and requires no physical signature.</i>"""
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
    story.append(Paragraph(footer_text, subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
