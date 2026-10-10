"""General helper functions and Jinja filters."""
from datetime import datetime, date
from decimal import Decimal
from typing import Union


def format_currency(value: Union[Decimal, float, int, str], symbol: str = '₹') -> str:
    """Format a monetary number nicely as currency (e.g. ₹ 2,500.00)."""
    if value is None or value == '':
        return f"{symbol} 0.00"
    try:
        dec_val = Decimal(str(value))
        return f"{symbol} {dec_val:,.2f}"
    except Exception:
        return f"{symbol} {value}"


def format_date(dt: Union[datetime, date, str], fmt: str = '%d %b %Y') -> str:
    """Format a date or datetime object."""
    if not dt:
        return '-'
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d')
        except ValueError:
            return dt
    return dt.strftime(fmt)


def format_datetime(dt: Union[datetime, str], fmt: str = '%d %b %Y, %I:%M %p') -> str:
    """Format datetime object with hour/minute/AM/PM."""
    if not dt:
        return '-'
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime(fmt)


def calculate_overdue_text(planned_checkout: datetime) -> str:
    """Calculate human-readable overdue duration string."""
    if not planned_checkout:
        return '-'
    now = datetime.utcnow()
    if now <= planned_checkout:
        return 'On schedule'
    diff = now - planned_checkout
    hours, remainder = divmod(int(diff.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h overdue"
    return f"{hours}h {minutes}m overdue"
