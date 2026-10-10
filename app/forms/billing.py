"""Forms for Payments and Checkout finalization."""
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class PaymentForm(FlaskForm):
    amount = DecimalField('Payment Amount (₹)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI / GPay / PhonePe', 'UPI / QR Code'),
        ('Credit / Debit Card', 'Card Payment'),
        ('Bank Transfer / NEFT', 'Bank Transfer'),
        ('Online Gateway', 'Online Payment')
    ], default='Cash')
    transaction_ref = StringField('Transaction Ref / Note', validators=[Optional(), Length(max=100)])
    notes = StringField('Receipt Remarks', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Record Payment & Generate Receipt')


class CheckoutFinalizeForm(FlaskForm):
    apply_early_fee = BooleanField('Apply Early Check-in Fee')
    late_hours = DecimalField('Late Check-out Extra Hours', places=1, default=0.0, validators=[NumberRange(min=0)])
    discount_amount = DecimalField('Additional Discount (₹)', places=2, default=0.00, validators=[NumberRange(min=0)])
    payment_amount = DecimalField('Payment Collected Now (₹)', places=2, default=0.00, validators=[NumberRange(min=0)])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI / GPay / PhonePe', 'UPI / QR Code'),
        ('Credit / Debit Card', 'Card Payment'),
        ('Bank Transfer / NEFT', 'Bank Transfer')
    ], default='Cash')
    transaction_ref = StringField('Transaction / Card Ref', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Invoice Notes / Guest Feedback', validators=[Optional()])
    submit = SubmitField('Finalize Invoice & Complete Check-out')
