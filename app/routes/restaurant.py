"""Restaurant module: Table Management, Reservations, POS Orders, and Room Folio Posting."""
import json
from datetime import datetime, date
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_, and_
from app.extensions import db
from app.models.hotel import Floor, Room, HotelSettings
from app.models.booking import Booking, Stay, BookingStatus
from app.models.billing import GuestFolioCharge
from app.models.restaurant import (
    RestaurantTable, TableReservation, MenuCategory, MenuItem,
    RestaurantOrder, RestaurantOrderItem, TableStatus
)
from app.forms.restaurant import TableForm, TableReservationForm, MenuCategoryForm, MenuItemForm
from app.services.availability import is_table_available, get_available_tables
from app.services.billing_service import quantize_amount
from app.services.audit_service import log_activity
from app.utils.decorators import restaurant_required, manager_required

restaurant_bp = Blueprint('restaurant', __name__)


@restaurant_bp.route('/')
@login_required
def index():
    return redirect(url_for('restaurant.tables'))


@restaurant_bp.route('/tables')
@login_required
def tables():
    section_filter = request.args.get('section', '')
    status_filter = request.args.get('status', '')

    query = RestaurantTable.query.filter_by(is_active=True)

    if section_filter:
        query = query.filter_by(section=section_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_tables = query.order_by(RestaurantTable.table_number).all()
    
    sections = db.session.query(RestaurantTable.section).distinct().filter_by(is_active=True).all()
    section_list = [s[0] for s in sections]

    status_counts = {
        'total': RestaurantTable.query.filter_by(is_active=True).count(),
        'available': RestaurantTable.query.filter_by(is_active=True, status=TableStatus.AVAILABLE).count(),
        'occupied': RestaurantTable.query.filter_by(is_active=True, status=TableStatus.OCCUPIED).count(),
        'reserved': RestaurantTable.query.filter_by(is_active=True, status=TableStatus.RESERVED).count(),
        'cleaning': RestaurantTable.query.filter_by(is_active=True, status=TableStatus.CLEANING).count(),
    }

    return render_template(
        'restaurant/tables.html',
        tables=all_tables,
        sections=section_list,
        section_filter=section_filter,
        status_filter=status_filter,
        status_counts=status_counts,
        TableStatus=TableStatus
    )


@restaurant_bp.route('/tables/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_table():
    form = TableForm()
    form.floor_id.choices = [(0, '-- None --')] + [(f.id, f.name) for f in Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()]

    if form.validate_on_submit():
        existing = RestaurantTable.query.filter_by(table_number=form.table_number.data.strip()).first()
        if existing:
            flash(f"Table '{form.table_number.data}' already exists!", 'danger')
            return render_template('restaurant/table_form.html', form=form, title='Add Restaurant Table')

        table = RestaurantTable(
            table_number=form.table_number.data.strip(),
            capacity=form.capacity.data,
            section=form.section.data,
            floor_id=form.floor_id.data if form.floor_id.data != 0 else None,
            status=form.status.data,
            is_active=form.is_active.data
        )
        db.session.add(table)
        db.session.commit()

        log_activity('CREATE_TABLE', 'RestaurantTable', table.id, f"Created table {table.table_number} (Capacity: {table.capacity})")
        flash(f"Table {table.table_number} added successfully.", 'success')
        return redirect(url_for('restaurant.tables'))

    return render_template('restaurant/table_form.html', form=form, title='Add Restaurant Table')


@restaurant_bp.route('/tables/<int:table_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_table(table_id):
    table = RestaurantTable.query.get_or_404(table_id)
    form = TableForm(obj=table)
    form.floor_id.choices = [(0, '-- None --')] + [(f.id, f.name) for f in Floor.query.filter_by(is_active=True).order_by(Floor.sort_order).all()]
    if request.method == 'GET' and not table.floor_id:
        form.floor_id.data = 0

    if form.validate_on_submit():
        conflict = RestaurantTable.query.filter(RestaurantTable.table_number == form.table_number.data.strip(), RestaurantTable.id != table.id).first()
        if conflict:
            flash(f"Table number '{form.table_number.data}' is already used.", 'danger')
            return render_template('restaurant/table_form.html', form=form, title=f'Edit Table {table.table_number}')

        table.table_number = form.table_number.data.strip()
        table.capacity = form.capacity.data
        table.section = form.section.data
        table.floor_id = form.floor_id.data if form.floor_id.data != 0 else None
        table.status = form.status.data
        table.is_active = form.is_active.data
        db.session.commit()

        log_activity('UPDATE_TABLE', 'RestaurantTable', table.id, f"Updated table {table.table_number}")
        flash(f"Table {table.table_number} updated successfully.", 'success')
        return redirect(url_for('restaurant.tables'))

    return render_template('restaurant/table_form.html', form=form, title=f'Edit Table {table.table_number}')


@restaurant_bp.route('/tables/<int:table_id>/set-status', methods=['POST'])
@login_required
@restaurant_required
def set_table_status(table_id):
    table = RestaurantTable.query.get_or_404(table_id)
    new_status = request.form.get('status')
    if new_status in [c[0] for c in TableStatus.CHOICES]:
        table.status = new_status
        db.session.commit()
        log_activity('UPDATE_TABLE_STATUS', 'RestaurantTable', table.id, f"Changed table {table.table_number} status to {new_status}")
        flash(f"Table {table.table_number} marked as {new_status}.", "success")
    return redirect(request.referrer or url_for('restaurant.tables'))


@restaurant_bp.route('/reservations', methods=['GET', 'POST'])
@login_required
def reservations():
    form = TableReservationForm()
    active_tables = RestaurantTable.query.filter_by(is_active=True).order_by(RestaurantTable.table_number).all()
    form.table_id.choices = [(t.id, f"Table {t.table_number} ({t.section} - Cap: {t.capacity})") for t in active_tables]

    if form.validate_on_submit():
        res_date = form.reservation_date.data
        start_t = form.start_time.data.strip()
        end_t = form.end_time.data.strip()

        # Check table conflict
        avail, reason = is_table_available(form.table_id.data, res_date, start_t, end_t)
        if not avail:
            flash(f"Reservation conflict: {reason}", 'danger')
            return redirect(url_for('restaurant.reservations'))

        count = TableReservation.query.filter(TableReservation.created_at >= datetime.utcnow().date()).count() + 1
        res_num = f"RES-{datetime.utcnow().strftime('%Y%m%d')}-{count:04d}"

        reservation = TableReservation(
            reservation_number=res_num,
            table_id=form.table_id.data,
            customer_name=form.customer_name.data.strip(),
            contact_number=form.contact_number.data.strip(),
            reservation_date=res_date,
            start_time=start_t,
            end_time=end_t,
            guest_count=form.guest_count.data,
            special_requests=form.special_requests.data,
            status=form.status.data,
            created_by_id=current_user.id
        )
        db.session.add(reservation)

        # If reservation is for today within window, mark table reserved
        if res_date == date.today():
            t_obj = RestaurantTable.query.get(form.table_id.data)
            if t_obj and t_obj.status == TableStatus.AVAILABLE:
                t_obj.status = TableStatus.RESERVED

        db.session.commit()
        log_activity('CREATE_TABLE_RESERVATION', 'TableReservation', reservation.id, f"Booked {reservation.table.table_number} for {reservation.customer_name}")
        flash(f"Table reservation {reservation.reservation_number} confirmed for {reservation.customer_name}!", 'success')
        return redirect(url_for('restaurant.reservations'))

    reservations_list = TableReservation.query.order_by(TableReservation.reservation_date.desc(), TableReservation.start_time.desc()).all()
    return render_template('restaurant/reservations.html', form=form, reservations=reservations_list)


@restaurant_bp.route('/reservations/<int:res_id>/cancel', methods=['POST'])
@login_required
@restaurant_required
def cancel_reservation(res_id):
    res = TableReservation.query.get_or_404(res_id)
    res.status = 'Cancelled'
    if res.table.status == TableStatus.RESERVED:
        res.table.status = TableStatus.AVAILABLE
    db.session.commit()
    log_activity('CANCEL_TABLE_RESERVATION', 'TableReservation', res.id, f"Cancelled reservation {res.reservation_number}")
    flash(f"Reservation {res.reservation_number} cancelled.", "info")
    return redirect(url_for('restaurant.reservations'))


@restaurant_bp.route('/orders')
@login_required
def orders():
    status_filter = request.args.get('status', '')
    query = RestaurantOrder.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    all_orders = query.order_by(RestaurantOrder.created_at.desc()).all()
    return render_template('restaurant/orders.html', orders=all_orders, status_filter=status_filter)


@restaurant_bp.route('/pos', methods=['GET', 'POST'])
@login_required
@restaurant_required
def pos():
    """Interactive POS terminal for taking dining, takeaway, or room service orders."""
    settings = HotelSettings.get_settings()
    tables = RestaurantTable.query.filter_by(is_active=True).order_by(RestaurantTable.table_number).all()
    categories = MenuCategory.query.filter_by(is_active=True).order_by(MenuCategory.sort_order).all()
    active_stays = Stay.query.filter_by(status='Active').all()

    if request.method == 'POST':
        # Process order payload from client POS
        data = request.form
        order_type = data.get('order_type', 'Dine-In')
        table_id = int(data.get('table_id')) if data.get('table_id') and data.get('table_id') != '0' else None
        stay_id = int(data.get('stay_id')) if data.get('stay_id') and data.get('stay_id') != '0' else None
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        waiter_name = data.get('waiter_name', current_user.full_name)
        payment_action = data.get('payment_action', 'Pending')  # 'Paid', 'Pending', 'PostToRoom'
        payment_method = data.get('payment_method', 'Cash')
        notes = data.get('notes', '')

        # Items payload from hidden input
        raw_items_json = data.get('cart_items_json', '[]')
        try:
            cart_items = json.loads(raw_items_json)
        except Exception:
            cart_items = []

        if not cart_items:
            flash("Please add at least one dish/item to the order.", "danger")
            return redirect(url_for('restaurant.pos'))

        # Calculate subtotal and tax
        subtotal = Decimal('0.00')
        rest_tax_rate = quantize_amount(settings.restaurant_tax_rate)

        # Generate order number
        order_count = RestaurantOrder.query.filter(RestaurantOrder.created_at >= datetime.utcnow().date()).count() + 1
        order_number = f"{settings.restaurant_order_prefix}{datetime.utcnow().strftime('%Y%m%d')}-{order_count:04d}"

        # Resolve Hotel Guest link if Room Service or Posted to Room
        booking_id = None
        guest_id = None
        room_id = None
        if stay_id:
            stay_obj = Stay.query.get(stay_id)
            if stay_obj:
                booking_id = stay_obj.booking_id
                guest_id = stay_obj.guest_id
                room_id = stay_obj.room_id
                if not customer_name:
                    customer_name = stay_obj.guest.full_name

        order = RestaurantOrder(
            order_number=order_number,
            order_type=order_type,
            table_id=table_id,
            room_id=room_id,
            booking_id=booking_id,
            guest_id=guest_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            waiter_name=waiter_name,
            status='Served' if payment_action in ['Paid', 'PostToRoom'] else 'In Progress',
            payment_status='Paid' if payment_action == 'Paid' else ('Posted to Room' if payment_action == 'PostToRoom' else 'Pending'),
            payment_method=payment_method if payment_action == 'Paid' else None,
            tax_rate=rest_tax_rate,
            notes=notes,
            created_by_id=current_user.id
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            qty = int(item.get('quantity', 1))
            price = quantize_amount(item.get('price', 0))
            line_total = quantize_amount(price * qty)
            subtotal += line_total

            order_item = RestaurantOrderItem(
                order_id=order.id,
                menu_item_id=item.get('id'),
                item_name=item.get('name'),
                quantity=qty,
                unit_price=price,
                total_price=line_total,
                special_notes=item.get('notes')
            )
            db.session.add(order_item)

        tax_amt = quantize_amount(subtotal * (rest_tax_rate / Decimal('100.00')))
        grand_tot = quantize_amount(subtotal + tax_amt)

        order.subtotal = subtotal
        order.tax_amount = tax_amt
        order.grand_total = grand_tot

        # Update table status if Dine-In
        if table_id:
            table_obj = RestaurantTable.query.get(table_id)
            if table_obj:
                table_obj.status = TableStatus.OCCUPIED if payment_action != 'Paid' else TableStatus.CLEANING

        # If Posted to Room Folio, create GuestFolioCharge
        if payment_action == 'PostToRoom' and booking_id:
            folio_charge = GuestFolioCharge(
                booking_id=booking_id,
                guest_id=guest_id,
                stay_id=stay_id,
                charge_type='restaurant',
                description=f"Restaurant Order {order.order_number} ({order.order_type})",
                amount=grand_tot,
                reference_order_id=order.id,
                posted_by_id=current_user.id,
                is_billed=False
            )
            db.session.add(folio_charge)

        db.session.commit()

        log_activity('CREATE_ORDER', 'RestaurantOrder', order.id, f"Order {order.order_number} created (₹{grand_tot}) - {payment_action}")
        flash(f"Order {order.order_number} created successfully! Total: ₹{grand_tot:,.2f}", "success")
        return redirect(url_for('restaurant.order_detail', order_id=order.id))

    return render_template(
        'restaurant/pos.html',
        tables=tables,
        categories=categories,
        active_stays=active_stays,
        settings=settings
    )


@restaurant_bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = RestaurantOrder.query.get_or_404(order_id)
    settings = HotelSettings.get_settings()
    return render_template('restaurant/order_detail.html', order=order, settings=settings)


@restaurant_bp.route('/orders/<int:order_id>/bill-print')
@login_required
def print_bill(order_id):
    order = RestaurantOrder.query.get_or_404(order_id)
    settings = HotelSettings.get_settings()
    return render_template('restaurant/bill_print.html', order=order, settings=settings)


@restaurant_bp.route('/orders/<int:order_id>/pay', methods=['POST'])
@login_required
@restaurant_required
def pay_order(order_id):
    order = RestaurantOrder.query.get_or_404(order_id)
    pay_method = request.form.get('payment_method', 'Cash')
    
    order.payment_status = 'Paid'
    order.status = 'Served'
    order.payment_method = pay_method

    if order.table:
        order.table.status = TableStatus.CLEANING

    db.session.commit()
    log_activity('PAY_ORDER', 'RestaurantOrder', order.id, f"Order {order.order_number} settled via {pay_method}")
    flash(f"Order {order.order_number} marked as Paid.", "success")
    return redirect(url_for('restaurant.order_detail', order_id=order.id))


@restaurant_bp.route('/menu', methods=['GET', 'POST'])
@login_required
def menu():
    categories = MenuCategory.query.order_by(MenuCategory.sort_order).all()
    cat_form = MenuCategoryForm()
    item_form = MenuItemForm()
    item_form.category_id.choices = [(c.id, c.name) for c in categories]

    return render_template(
        'restaurant/menu.html',
        categories=categories,
        cat_form=cat_form,
        item_form=item_form
    )


@restaurant_bp.route('/menu/category/add', methods=['POST'])
@login_required
@manager_required
def add_category():
    form = MenuCategoryForm()
    if form.validate_on_submit():
        cat = MenuCategory(
            name=form.name.data.strip(),
            description=form.description.data,
            sort_order=form.sort_order.data,
            is_active=form.is_active.data
        )
        db.session.add(cat)
        db.session.commit()
        log_activity('CREATE_MENU_CATEGORY', 'MenuCategory', cat.id, f"Created menu category {cat.name}")
        flash(f"Menu category '{cat.name}' added successfully.", 'success')
    return redirect(url_for('restaurant.menu'))


@restaurant_bp.route('/menu/item/add', methods=['POST'])
@login_required
@manager_required
def add_menu_item():
    categories = MenuCategory.query.all()
    form = MenuItemForm()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        item = MenuItem(
            category_id=form.category_id.data,
            name=form.name.data.strip(),
            description=form.description.data,
            price=form.price.data,
            tax_rate=form.tax_rate.data,
            is_veg=form.is_veg.data,
            is_available=form.is_available.data
        )
        db.session.add(item)
        db.session.commit()
        log_activity('CREATE_MENU_ITEM', 'MenuItem', item.id, f"Created dish {item.name} (₹{item.price})")
        flash(f"Menu item '{item.name}' added successfully.", 'success')
    return redirect(url_for('restaurant.menu'))
