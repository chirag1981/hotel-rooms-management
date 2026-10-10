"""Forms for Hotel Settings and Staff User Management."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, SelectField, BooleanField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange, Length, Optional
from app.models.user import Role


class HotelSettingsForm(FlaskForm):
    hotel_name = StringField('Hotel & Resort Name', validators=[DataRequired(), Length(max=150)])
    tagline = StringField('Tagline / Subtitle', validators=[Optional(), Length(max=255)])
    address_line = StringField('Street Address', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=100)])
    pincode = StringField('Pincode / Postal Code', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone / Reception', validators=[Optional(), Length(max=50)])
    email = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    gstin = StringField('GSTIN / Tax ID Number', validators=[Optional(), Length(max=50)])
    currency_code = StringField('Currency Code', default='INR', validators=[DataRequired(), Length(max=10)])
    currency_symbol = StringField('Currency Symbol', default='₹', validators=[DataRequired(), Length(max=10)])
    timezone = StringField('Timezone', default='Asia/Kolkata', validators=[DataRequired(), Length(max=50)])
    
    standard_checkin_time = StringField('Standard Check-in Time', default='14:00', validators=[DataRequired()])
    standard_checkout_time = StringField('Standard Check-out Time', default='11:00', validators=[DataRequired()])
    
    room_tax_rate = DecimalField('Room GST Rate (%)', places=2, default=12.00, validators=[DataRequired(), NumberRange(min=0, max=100)])
    restaurant_tax_rate = DecimalField('Restaurant GST Rate (%)', places=2, default=5.00, validators=[Optional(), NumberRange(min=0, max=100)])
    
    early_checkin_fee = DecimalField('Early Check-in Fee (₹)', places=2, default=500.00, validators=[NumberRange(min=0)])
    late_checkout_hourly_fee = DecimalField('Late Check-out Hourly Rate (₹)', places=2, default=250.00, validators=[NumberRange(min=0)])
    extra_bed_charge = DecimalField('Default Extra Bed Rate (₹)', places=2, default=800.00, validators=[NumberRange(min=0)])
    extra_person_charge = DecimalField('Default Extra Person Rate (₹)', places=2, default=500.00, validators=[NumberRange(min=0)])
    
    invoice_prefix = StringField('Invoice Number Prefix', default='INV-', validators=[DataRequired(), Length(max=20)])
    booking_prefix = StringField('Booking Number Prefix', default='BK-', validators=[DataRequired(), Length(max=20)])
    restaurant_order_prefix = StringField('Restaurant Order Prefix', default='ORD-', validators=[Optional(), Length(max=20)])
    
    submit = SubmitField('Update Hotel Settings')


class UserAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Staff Full Name', validators=[DataRequired(), Length(max=100)])
    role = SelectField('System Role', choices=Role.CHOICES, default=Role.RECEPTIONIST)
    password = PasswordField('Password (leave empty to keep current)', validators=[Optional(), Length(min=6, max=100)])
    is_active = BooleanField('Active Account', default=True)
    submit = SubmitField('Save Staff User')
