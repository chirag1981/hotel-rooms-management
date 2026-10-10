"""Forms package initialization."""
from app.forms.auth import LoginForm, ChangePasswordForm
from app.forms.hotel import FloorForm, RoomCategoryForm, RoomForm
from app.forms.booking import GuestForm, BookingForm
from app.forms.billing import PaymentForm, CheckoutFinalizeForm
from app.forms.restaurant import (
    TableForm, TableReservationForm, MenuCategoryForm, MenuItemForm
)
from app.forms.settings import HotelSettingsForm, UserAccountForm

__all__ = [
    'LoginForm', 'ChangePasswordForm',
    'FloorForm', 'RoomCategoryForm', 'RoomForm',
    'GuestForm', 'BookingForm',
    'PaymentForm', 'CheckoutFinalizeForm',
    'TableForm', 'TableReservationForm', 'MenuCategoryForm', 'MenuItemForm',
    'HotelSettingsForm', 'UserAccountForm'
]
