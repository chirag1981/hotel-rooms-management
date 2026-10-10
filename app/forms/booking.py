"""Forms for Guest Registration, Reservations, and Walk-in Check-in."""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DecimalField, IntegerField, DateField,
    SelectField, SelectMultipleField, BooleanField, SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Length, Optional, Email
from app.models.booking import BookingStatus


class GuestForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    mobile = StringField('Mobile Number', validators=[DataRequired(), Length(min=8, max=20)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    address = StringField('Address', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=100)])
    country = StringField('Country', default='India', validators=[Optional(), Length(max=100)])
    id_type = SelectField('Government ID Type', choices=[
        ('Aadhaar Card', 'Aadhaar Card'),
        ('Passport', 'Passport'),
        ('Driving License', 'Driving License'),
        ('Voter ID', 'Voter ID Card'),
        ('PAN Card', 'PAN Card'),
        ('National ID', 'Other National ID')
    ], default='Aadhaar Card')
    id_number = StringField('ID Number (Confidential)', validators=[Optional(), Length(max=100)])
    emergency_contact = StringField('Emergency Contact', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Guest Notes / Preferences', validators=[Optional()])
    submit = SubmitField('Save Guest Details')


class BookingForm(FlaskForm):
    # Guest details (for inline new or existing lookup)
    guest_id = SelectField('Select Existing Guest', coerce=int, validators=[Optional()])
    new_guest_name = StringField('Guest Full Name', validators=[Optional(), Length(max=120)])
    new_guest_mobile = StringField('Mobile Number', validators=[Optional(), Length(max=20)])
    new_guest_email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    new_guest_id_type = SelectField('ID Type', choices=[
        ('Aadhaar Card', 'Aadhaar Card'),
        ('Passport', 'Passport'),
        ('Driving License', 'Driving License'),
        ('Voter ID', 'Voter ID Card'),
        ('PAN Card', 'PAN Card')
    ], default='Aadhaar Card')
    new_guest_id_number = StringField('ID Number', validators=[Optional()])
    new_guest_city = StringField('City / State', validators=[Optional()])

    # Booking parameters
    booking_source = SelectField('Booking Source', choices=[
        ('Walk-in', 'Walk-in'),
        ('Phone Call', 'Phone Call'),
        ('Online Website', 'Online / Web'),
        ('OTA (MakeMyTrip/Booking)', 'OTA Partner'),
        ('Corporate', 'Corporate Travel')
    ], default='Walk-in')
    
    room_category_id = SelectField('Room Category', coerce=int, validators=[DataRequired()])
    allocated_rooms = SelectMultipleField('Allocate Room(s)', coerce=int, validators=[DataRequired()])
    
    checkin_date = DateField('Check-in Date', default=date.today, validators=[DataRequired()])
    checkout_date = DateField('Check-out Date', validators=[DataRequired()])
    expected_checkin_time = StringField('Expected Check-in Time', default='14:00', validators=[DataRequired()])
    expected_checkout_time = StringField('Expected Check-out Time', default='11:00', validators=[DataRequired()])
    
    adults_count = IntegerField('Adults', default=1, validators=[DataRequired(), NumberRange(min=1)])
    children_count = IntegerField('Children', default=0, validators=[NumberRange(min=0)])
    
    agreed_rate_per_night = DecimalField('Agreed Rate per Room per Night (₹)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    has_extra_bed = BooleanField('Add Extra Bed')
    extra_bed_charge = DecimalField('Extra Bed Charge per Night (₹)', places=2, default=0.00, validators=[NumberRange(min=0)])
    discount_amount = DecimalField('Discount (₹)', places=2, default=0.00, validators=[NumberRange(min=0)])
    advance_payment = DecimalField('Advance Deposit Paid (₹)', places=2, default=0.00, validators=[NumberRange(min=0)])
    payment_method = SelectField('Advance Payment Method', choices=[
        ('Cash', 'Cash'),
        ('UPI / GPay / PhonePe', 'UPI / QR Code'),
        ('Credit / Debit Card', 'Card Payment'),
        ('Bank Transfer / NEFT', 'Bank Transfer'),
        ('Online Gateway', 'Online Payment')
    ], default='Cash')
    
    special_requests = TextAreaField('Special Requests / Remarks', validators=[Optional()])
    
    # Quick Check-in toggle (for Walk-in immediate occupancy)
    checkin_now = BooleanField('Check-in Immediately (Walk-in)', default=False)
    
    submit = SubmitField('Confirm Booking')
