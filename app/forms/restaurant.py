"""Forms for Restaurant Tables, Reservations, Menu, and Orders."""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DecimalField, IntegerField, DateField,
    SelectField, BooleanField, SubmitField
)
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from app.models.restaurant import TableStatus


class TableForm(FlaskForm):
    table_number = StringField('Table Number / Name', validators=[DataRequired(), Length(max=20)])
    capacity = IntegerField('Seating Capacity', default=4, validators=[DataRequired(), NumberRange(min=1, max=30)])
    section = SelectField('Dining Section', choices=[
        ('Indoor AC', 'Indoor AC Hall'),
        ('Outdoor Garden', 'Outdoor Garden'),
        ('Family Section', 'Family Dining Section'),
        ('Rooftop Terrace', 'Rooftop Terrace'),
        ('Lounge / Bar', 'Lounge / Bar')
    ], default='Indoor AC')
    floor_id = SelectField('Floor', coerce=int, validators=[Optional()])
    status = SelectField('Current Status', choices=TableStatus.CHOICES, default=TableStatus.AVAILABLE)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Table')


class TableReservationForm(FlaskForm):
    table_id = SelectField('Table', coerce=int, validators=[DataRequired()])
    customer_name = StringField('Customer Name', validators=[DataRequired(), Length(max=120)])
    contact_number = StringField('Contact Phone', validators=[DataRequired(), Length(min=8, max=30)])
    reservation_date = DateField('Reservation Date', default=date.today, validators=[DataRequired()])
    start_time = StringField('Start Time (HH:MM)', default='19:00', validators=[DataRequired()])
    end_time = StringField('End Time (HH:MM)', default='21:00', validators=[DataRequired()])
    guest_count = IntegerField('Number of Guests', default=2, validators=[DataRequired(), NumberRange(min=1)])
    special_requests = TextAreaField('Special Requests (e.g. Candle light, High chair)', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Confirmed', 'Confirmed'),
        ('Seated', 'Seated (Arrived)'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('No-Show', 'No-Show')
    ], default='Confirmed')
    submit = SubmitField('Book Table')


class MenuCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=80)])
    description = StringField('Description', validators=[Optional(), Length(max=255)])
    sort_order = IntegerField('Display Order', default=0)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')


class MenuItemForm(FlaskForm):
    category_id = SelectField('Menu Category', coerce=int, validators=[DataRequired()])
    name = StringField('Dish / Item Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description / Ingredients', validators=[Optional()])
    price = DecimalField('Price (₹)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    tax_rate = DecimalField('GST Rate (%)', places=2, default=5.00, validators=[DataRequired(), NumberRange(min=0, max=100)])
    is_veg = BooleanField('Pure Vegetarian', default=True)
    is_available = BooleanField('Available', default=True)
    submit = SubmitField('Save Menu Item')
