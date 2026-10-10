"""Forms for Floors, Room Categories, and Rooms."""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from app.models.hotel import RoomStatus


class FloorForm(FlaskForm):
    floor_number = IntegerField('Floor Number', validators=[DataRequired()])
    name = StringField('Floor Name / Label', validators=[DataRequired(), Length(max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=200)])
    sort_order = IntegerField('Display Order', default=0)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Floor')


class RoomCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=80)])
    description = TextAreaField('Description', validators=[Optional()])
    base_price = DecimalField('Default Price per Night (₹)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    max_guests = IntegerField('Max Permitted Guests', default=2, validators=[DataRequired(), NumberRange(min=1)])
    is_ac = BooleanField('Air Conditioned (AC)', default=True)
    bed_type = SelectField('Bed Type', choices=[
        ('King Bed', 'King Bed'),
        ('Queen Bed', 'Queen Bed'),
        ('Twin Beds', 'Twin Beds'),
        ('Single Bed', 'Single Bed'),
        ('Double Bed', 'Double Bed'),
        ('Bunk Bed', 'Bunk Bed')
    ], default='King Bed')
    bed_count = IntegerField('Bed Count', default=1, validators=[DataRequired(), NumberRange(min=1)])
    tax_rate = DecimalField('Applicable GST Rate (%)', places=2, default=12.00, validators=[DataRequired(), NumberRange(min=0, max=100)])
    extra_adult_price = DecimalField('Extra Adult Charge per Night (₹)', places=2, default=600.00, validators=[NumberRange(min=0)])
    extra_child_price = DecimalField('Extra Child Charge per Night (₹)', places=2, default=300.00, validators=[NumberRange(min=0)])
    amenities = StringField('Amenities (comma separated)', default='Wi-Fi, TV, Geyser, Room Service, Safe')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')


class RoomForm(FlaskForm):
    room_number = StringField('Room Number / Name', validators=[DataRequired(), Length(max=20)])
    floor_id = SelectField('Floor', coerce=int, validators=[DataRequired()])
    category_id = SelectField('Room Category', coerce=int, validators=[DataRequired()])
    status = SelectField('Operational Status', choices=RoomStatus.CHOICES, default=RoomStatus.AVAILABLE)
    max_occupancy = IntegerField('Max Occupancy', default=2, validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('Notes / Maintenance remarks', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Room')
