"""Availability services for rooms and restaurant tables."""
from datetime import datetime, date
from typing import List, Tuple
from sqlalchemy import and_, or_
from app.extensions import db
from app.models.hotel import Room, RoomStatus
from app.models.booking import Booking, BookingRoom, Stay, BookingStatus
from app.models.restaurant import RestaurantTable, TableReservation, TableStatus


def is_room_available(room_id: int, checkin_date: date, checkout_date: date, exclude_booking_id: int = None) -> Tuple[bool, str]:
    """
    Check if a specific room is available for the given date range.
    Returns (is_available, reason).
    """
    if checkin_date >= checkout_date:
        return False, "Check-out date must be after check-in date."

    room = Room.query.get(room_id)
    if not room or not room.is_active:
        return False, "Room is inactive or does not exist."

    # If checking for today and room is in Maintenance or Out of Service
    today = date.today()
    if checkin_date <= today <= checkout_date:
        if room.status in (RoomStatus.MAINTENANCE, RoomStatus.OUT_OF_SERVICE):
            return False, f"Room is currently in {room.status}."

    # Check overlapping confirmed/checked-in bookings for this room
    query = db.session.query(Booking).join(BookingRoom).filter(
        BookingRoom.room_id == room_id,
        Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
        Booking.checkin_date < checkout_date,
        Booking.checkout_date > checkin_date
    )

    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    conflicting_booking = query.first()
    if conflicting_booking:
        return False, f"Room is already booked (Ref: {conflicting_booking.booking_number}) from {conflicting_booking.checkin_date} to {conflicting_booking.checkout_date}."

    # Check active stays for today
    if checkin_date <= today:
        active_stay = Stay.query.filter(
            Stay.room_id == room_id,
            Stay.status == 'Active'
        ).first()
        if active_stay and (exclude_booking_id is None or active_stay.booking_id != exclude_booking_id):
            return False, "Room is currently occupied by an active guest stay."

    return True, "Available"


def get_available_rooms(checkin_date: date, checkout_date: date, category_id: int = None, exclude_booking_id: int = None) -> List[Room]:
    """Retrieve all available physical rooms for the given date range and optional category."""
    query = Room.query.filter(Room.is_active == True)
    if category_id:
        query = query.filter(Room.category_id == category_id)

    rooms = query.all()
    available = []
    for room in rooms:
        avail, _ = is_room_available(room.id, checkin_date, checkout_date, exclude_booking_id=exclude_booking_id)
        if avail:
            available.append(room)
    return available


def is_table_available(table_id: int, res_date: date, start_time: str, end_time: str, exclude_reservation_id: int = None) -> Tuple[bool, str]:
    """
    Check if a restaurant table is available for a given date and time range (HH:MM).
    """
    table = RestaurantTable.query.get(table_id)
    if not table or not table.is_active:
        return False, "Table is inactive or does not exist."

    if table.status == TableStatus.OUT_OF_SERVICE:
        return False, "Table is currently out of service."

    # Check overlapping reservations on that date
    query = TableReservation.query.filter(
        TableReservation.table_id == table_id,
        TableReservation.reservation_date == res_date,
        TableReservation.status.in_(['Confirmed', 'Seated']),
        TableReservation.start_time < end_time,
        TableReservation.end_time > start_time
    )

    if exclude_reservation_id:
        query = query.filter(TableReservation.id != exclude_reservation_id)

    conflict = query.first()
    if conflict:
        return False, f"Table has reservation (Ref: {conflict.reservation_number}) between {conflict.start_time} and {conflict.end_time}."

    return True, "Available"


def get_available_tables(res_date: date, start_time: str, end_time: str, min_capacity: int = 1) -> List[RestaurantTable]:
    """Get tables available for reservation."""
    tables = RestaurantTable.query.filter(
        RestaurantTable.is_active == True,
        RestaurantTable.capacity >= min_capacity
    ).order_by(RestaurantTable.table_number).all()

    available = []
    for table in tables:
        avail, _ = is_table_available(table.id, res_date, start_time, end_time)
        if avail:
            available.append(table)
    return available
