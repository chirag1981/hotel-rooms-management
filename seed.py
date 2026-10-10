"""Database Seeder with realistic hotel and restaurant operational demo data."""
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.hotel import HotelSettings, Floor, RoomCategory, Room, RoomStatus
from app.models.booking import Guest, Booking, BookingRoom, Stay, BookingStatus
from app.models.billing import Invoice, InvoiceLineItem, Payment, GuestFolioCharge, InvoiceStatus
from app.models.restaurant import (
    RestaurantTable, TableReservation, MenuCategory, MenuItem,
    RestaurantOrder, RestaurantOrderItem, TableStatus
)
from app.services.billing_service import finalize_invoice, record_payment, quantize_amount

app = create_app()

with app.app_context():
    print("Dropping and recreating database tables...")
    db.drop_all()
    db.create_all()

    print("Seeding Hotel Settings...")
    settings = HotelSettings(
        hotel_name="Hotel Rooms Management",
        tagline="Premier Accommodation & Room Management Experience",
        address_line="108 Sea Breeze Boulevard, Marine Drive",
        city="Mumbai",
        state="Maharashtra",
        pincode="400020",
        country="India",
        phone="+91 98765 43210",
        email="reservations@hotelroomsmanagement.com",
        gstin="27AAACG0123M1Z5",
        currency_code="INR",
        currency_symbol="₹",
        timezone="Asia/Kolkata",
        standard_checkin_time="14:00",
        standard_checkout_time="11:00",
        room_tax_rate=Decimal("12.00"),
        restaurant_tax_rate=Decimal("5.00"),
        early_checkin_fee=Decimal("500.00"),
        late_checkout_hourly_fee=Decimal("250.00"),
        extra_bed_charge=Decimal("800.00"),
        extra_person_charge=Decimal("500.00")
    )
    db.session.add(settings)

    print("Seeding Staff User Accounts...")
    admin_user = User(
        username="admin",
        email="admin@grandhorizonhotel.com",
        full_name="Alexander Wright (GM)",
        role=Role.ADMIN,
        is_active=True
    )
    admin_user.set_password("admin123")

    manager_user = User(
        username="manager",
        email="manager@grandhorizonhotel.com",
        full_name="Priya Sharma (Operations Manager)",
        role=Role.MANAGER,
        is_active=True
    )
    manager_user.set_password("manager123")

    reception_user = User(
        username="reception",
        email="frontdesk@grandhorizonhotel.com",
        full_name="Rahul Verma (Front Desk Lead)",
        role=Role.RECEPTIONIST,
        is_active=True
    )
    reception_user.set_password("staff123")

    restaurant_user = User(
        username="chef",
        email="dining@grandhorizonhotel.com",
        full_name="Chef Sanjeev Kapur (F&B Lead)",
        role=Role.RESTAURANT_STAFF,
        is_active=True
    )
    restaurant_user.set_password("chef123")

    db.session.add_all([admin_user, manager_user, reception_user, restaurant_user])
    db.session.flush()

    print("Seeding Floors...")
    floor_g = Floor(floor_number=0, name="Ground Floor (Lobby & Garden)", sort_order=0)
    floor_1 = Floor(floor_number=1, name="1st Floor (Standard & Deluxe)", sort_order=1)
    floor_2 = Floor(floor_number=2, name="2nd Floor (Executive Suites)", sort_order=2)
    floor_3 = Floor(floor_number=3, name="3rd Floor (Penthouse & Royal Suites)", sort_order=3)
    db.session.add_all([floor_g, floor_1, floor_2, floor_3])
    db.session.flush()

    print("Seeding Room Categories...")
    cat_standard = RoomCategory(
        name="Standard Room",
        description="Cozy, well-appointed guest room with modern amenities and high-speed Wi-Fi.",
        base_price=Decimal("1800.00"),
        max_guests=2,
        is_ac=True,
        bed_type="Queen Bed",
        bed_count=1,
        tax_rate=Decimal("12.00"),
        extra_adult_price=Decimal("500.00"),
        extra_child_price=Decimal("250.00"),
        amenities="Wi-Fi, LED TV, Geyser, Wardrobe, Electric Kettle"
    )
    cat_deluxe = RoomCategory(
        name="Deluxe Room",
        description="Spacious elegant room featuring sea-facing balcony and ergonomic work desk.",
        base_price=Decimal("2800.00"),
        max_guests=3,
        is_ac=True,
        bed_type="King Bed",
        bed_count=1,
        tax_rate=Decimal("12.00"),
        extra_adult_price=Decimal("600.00"),
        extra_child_price=Decimal("300.00"),
        amenities="Wi-Fi, 4K Smart TV, Mini Fridge, Balcony, Safe, Tea Maker"
    )
    cat_suite = RoomCategory(
        name="AC Executive Suite",
        description="Premium luxury suite with a private living room, dining area, and bathtub.",
        base_price=Decimal("4500.00"),
        max_guests=4,
        is_ac=True,
        bed_type="King Bed",
        bed_count=2,
        tax_rate=Decimal("12.00"),
        extra_adult_price=Decimal("800.00"),
        extra_child_price=Decimal("400.00"),
        amenities="Living Room, Bathtub, High-speed Wi-Fi, 55' OLED TV, Espresso Machine, Safe"
    )
    cat_presidential = RoomCategory(
        name="Presidential Royal Suite",
        description="Top-tier luxury penthouse suite with panoramic coastal views, jacuzzi, and butler service.",
        base_price=Decimal("7500.00"),
        max_guests=4,
        is_ac=True,
        bed_type="Super King Bed",
        bed_count=2,
        tax_rate=Decimal("12.00"),
        extra_adult_price=Decimal("1000.00"),
        extra_child_price=Decimal("500.00"),
        amenities="Panoramic View, Private Jacuzzi, Butler Service, Mini Bar, Smart Automation"
    )
    db.session.add_all([cat_standard, cat_deluxe, cat_suite, cat_presidential])
    db.session.flush()

    print("Seeding Physical Hotel Rooms...")
    rooms_data = [
        # 1st Floor (Standard & Deluxe)
        ("101", floor_1.id, cat_standard.id, RoomStatus.AVAILABLE, 2),
        ("102", floor_1.id, cat_standard.id, RoomStatus.AVAILABLE, 2),
        ("103", floor_1.id, cat_standard.id, RoomStatus.CLEANING, 2),
        ("104", floor_1.id, cat_deluxe.id, RoomStatus.AVAILABLE, 3),
        ("105", floor_1.id, cat_deluxe.id, RoomStatus.OCCUPIED, 3),
        ("106", floor_1.id, cat_deluxe.id, RoomStatus.RESERVED, 3),
        
        # 2nd Floor (Deluxe & Executive Suites)
        ("201", floor_2.id, cat_deluxe.id, RoomStatus.AVAILABLE, 3),
        ("202", floor_2.id, cat_deluxe.id, RoomStatus.OCCUPIED, 3),
        ("203", floor_2.id, cat_suite.id, RoomStatus.AVAILABLE, 4),
        ("204", floor_2.id, cat_suite.id, RoomStatus.OCCUPIED, 4),
        ("205", floor_2.id, cat_suite.id, RoomStatus.MAINTENANCE, 4),
        
        # 3rd Floor (Presidential Suites)
        ("301", floor_3.id, cat_suite.id, RoomStatus.AVAILABLE, 4),
        ("302", floor_3.id, cat_presidential.id, RoomStatus.AVAILABLE, 4),
        ("303", floor_3.id, cat_presidential.id, RoomStatus.OCCUPIED, 4),
    ]

    created_rooms = {}
    for rnum, fid, cid, status, max_occ in rooms_data:
        r = Room(
            room_number=rnum,
            floor_id=fid,
            category_id=cid,
            status=status,
            max_occupancy=max_occ,
            is_active=True
        )
        db.session.add(r)
        created_rooms[rnum] = r
    db.session.flush()

    print("Seeding Restaurant Dining Tables...")
    tables_data = [
        ("T-01", 2, "Indoor AC", floor_g.id, TableStatus.AVAILABLE),
        ("T-02", 4, "Indoor AC", floor_g.id, TableStatus.OCCUPIED),
        ("T-03", 4, "Indoor AC", floor_g.id, TableStatus.AVAILABLE),
        ("T-04", 6, "Family Dining", floor_g.id, TableStatus.RESERVED),
        ("T-05", 8, "Family Dining", floor_g.id, TableStatus.AVAILABLE),
        ("G-01", 4, "Outdoor Garden", floor_g.id, TableStatus.AVAILABLE),
        ("G-02", 4, "Outdoor Garden", floor_g.id, TableStatus.CLEANING),
        ("R-01", 2, "Rooftop Terrace", floor_3.id, TableStatus.OCCUPIED),
        ("R-02", 4, "Rooftop Terrace", floor_3.id, TableStatus.AVAILABLE),
    ]
    created_tables = {}
    for tnum, cap, sec, fid, status in tables_data:
        tbl = RestaurantTable(
            table_number=tnum,
            capacity=cap,
            section=sec,
            floor_id=fid,
            status=status,
            is_active=True
        )
        db.session.add(tbl)
        created_tables[tnum] = tbl
    db.session.flush()

    print("Seeding Restaurant Menu...")
    cat_starters = MenuCategory(name="Starters & Appetizers", sort_order=1)
    cat_mains = MenuCategory(name="Main Course", sort_order=2)
    cat_breads = MenuCategory(name="Breads & Rice", sort_order=3)
    cat_beverages = MenuCategory(name="Beverages & Cocktails", sort_order=4)
    cat_desserts = MenuCategory(name="Desserts", sort_order=5)
    db.session.add_all([cat_starters, cat_mains, cat_breads, cat_beverages, cat_desserts])
    db.session.flush()

    menu_items = [
        # Starters
        (cat_starters.id, "Paneer Tikka Angara", "Charcoal grilled spiced cottage cheese with mint chutney", Decimal("280.00"), True),
        (cat_starters.id, "Crispy Corn Pepper Salt", "Wok tossed sweet corn with bell peppers and fresh scallions", Decimal("220.00"), True),
        (cat_starters.id, "Tandoori Chicken Wings", "Spiced succulent chicken wings roasted in clay oven", Decimal("340.00"), False),
        (cat_starters.id, "Coastal Fish Fry", "Fresh catch of the day marinated in Konkani spice paste", Decimal("390.00"), False),

        # Mains
        (cat_mains.id, "Paneer Butter Masala", "Cottage cheese simmered in rich creamy tomato cashew gravy", Decimal("320.00"), True),
        (cat_mains.id, "Dal Makhani Hotel", "Slow cooked black lentils with churned white butter", Decimal("260.00"), True),
        (cat_mains.id, "Butter Chicken Boneless", "Tender chicken tikka in authentic velvety makhani sauce", Decimal("380.00"), False),
        (cat_mains.id, "Mutton Rogan Josh", "Kashmiri style aromatic slow braised lamb curry", Decimal("450.00"), False),

        # Breads & Rice
        (cat_breads.id, "Garlic Butter Naan", "Clay oven baked flatbread brushed with garlic and butter", Decimal("60.00"), True),
        (cat_breads.id, "Tandoori Roti", "Whole wheat bread baked in tandoor", Decimal("35.00"), True),
        (cat_breads.id, "Hyderabadi Dum Biryani (Chicken)", "Fragrant basmati rice layered with marinated chicken and saffron", Decimal("360.00"), False),
        (cat_breads.id, "Jeera Rice & Dal Tadka Combo", "Cumin spiced tempered basmati rice with yellow lentil tadka", Decimal("240.00"), True),

        # Beverages
        (cat_beverages.id, "Fresh Lime Soda", "Refreshing sweet and salted carbonated lime juice", Decimal("90.00"), True),
        (cat_beverages.id, "Mango Lassi", "Chilled traditional yogurt smoothie with Alphonso pulp", Decimal("140.00"), True),
        (cat_beverages.id, "Masala Chai", "Brewed Indian tea with cardamom, ginger and cinnamon", Decimal("60.00"), True),

        # Desserts
        (cat_desserts.id, "Gulab Jamun with Ice Cream", "Warm milk solid dumplings served with vanilla bean gelato", Decimal("150.00"), True),
        (cat_desserts.id, "Saffron Rasmalai", "Soft cottage cheese discs soaked in saffron cardamom milk", Decimal("160.00"), True),
    ]

    created_menu_items = []
    for cid, name, desc, price, is_veg in menu_items:
        mi = MenuItem(
            category_id=cid,
            name=name,
            description=desc,
            price=price,
            tax_rate=Decimal("5.00"),
            is_veg=is_veg,
            is_available=True
        )
        db.session.add(mi)
        created_menu_items.append(mi)
    db.session.flush()

    print("Seeding Guests & Stays...")
    today = date.today()
    now = datetime.utcnow()

    # Guest 1: In-House Active Stay (Room 105)
    g1 = Guest(
        full_name="Vikramaditya Singhania",
        mobile="+91 98201 11222",
        email="vikram.singhania@gmail.com",
        city="Delhi",
        state="Delhi",
        country="India",
        id_type="Passport",
        id_number="Z4892011",
        notes="VIP Corporate guest. Prefers morning newspaper."
    )
    db.session.add(g1)
    db.session.flush()

    b1 = Booking(
        booking_number="BK-2026-0001",
        guest_id=g1.id,
        room_category_id=cat_deluxe.id,
        booking_source="Corporate",
        status=BookingStatus.CHECKED_IN,
        checkin_date=today - timedelta(days=1),
        checkout_date=today + timedelta(days=2),
        expected_checkin_time="14:00",
        expected_checkout_time="11:00",
        adults_count=2,
        children_count=0,
        total_nights=3,
        agreed_rate_per_night=Decimal("2800.00"),
        extra_bed_charge=Decimal("0.00"),
        tax_rate=Decimal("12.00"),
        tax_amount=Decimal("1008.00"),
        total_amount=Decimal("9408.00"),
        advance_payment=Decimal("3000.00"),
        payment_method="UPI / GPay / PhonePe",
        created_by_id=reception_user.id
    )
    db.session.add(b1)
    db.session.flush()

    br1 = BookingRoom(
        booking_id=b1.id,
        room_id=created_rooms["105"].id,
        rate_per_night=Decimal("2800.00")
    )
    db.session.add(br1)

    stay1 = Stay(
        booking_id=b1.id,
        guest_id=g1.id,
        room_id=created_rooms["105"].id,
        planned_checkin=datetime.combine(today - timedelta(days=1), datetime.min.time()),
        planned_checkout=datetime.combine(today + timedelta(days=2), datetime.min.time()),
        actual_checkin=datetime.utcnow() - timedelta(days=1),
        status="Active",
        checked_in_by_id=reception_user.id
    )
    db.session.add(stay1)

    # Add Advance payment for b1
    record_payment(
        booking_id=b1.id,
        amount=Decimal("3000.00"),
        payment_method="UPI / GPay / PhonePe",
        user_id=reception_user.id,
        transaction_ref="UPI-REF-88992211",
        notes="Advance booking deposit",
        is_advance=True
    )

    # Add Room Service Folio Charge for b1
    fc1 = GuestFolioCharge(
        booking_id=b1.id,
        guest_id=g1.id,
        stay_id=stay1.id,
        charge_type="restaurant",
        description="Room Service Dinner (Butter Chicken & Garlic Naan)",
        amount=Decimal("640.00"),
        posted_by_id=restaurant_user.id,
        posted_at=datetime.utcnow() - timedelta(hours=14),
        is_billed=False
    )
    db.session.add(fc1)

    # Guest 2: OVERDUE Check-out Stay (Room 202)
    g2 = Guest(
        full_name="Sunita Mehta",
        mobile="+91 99304 44555",
        email="sunita.mehta@yahoo.com",
        city="Pune",
        state="Maharashtra",
        id_type="Aadhaar Card",
        id_number="8912-3456-7890"
    )
    db.session.add(g2)
    db.session.flush()

    b2 = Booking(
        booking_number="BK-2026-0002",
        guest_id=g2.id,
        room_category_id=cat_deluxe.id,
        booking_source="Walk-in",
        status=BookingStatus.CHECKED_IN,
        checkin_date=today - timedelta(days=2),
        checkout_date=today,
        expected_checkin_time="12:00",
        expected_checkout_time="10:00",
        adults_count=1,
        total_nights=2,
        agreed_rate_per_night=Decimal("2800.00"),
        tax_rate=Decimal("12.00"),
        tax_amount=Decimal("672.00"),
        total_amount=Decimal("6272.00"),
        advance_payment=Decimal("2000.00"),
        payment_method="Cash",
        created_by_id=reception_user.id
    )
    db.session.add(b2)
    db.session.flush()

    br2 = BookingRoom(
        booking_id=b2.id,
        room_id=created_rooms["202"].id,
        rate_per_night=Decimal("2800.00")
    )
    db.session.add(br2)

    # Planned checkout was 3 hours ago -> Clearly OVERDUE!
    stay2 = Stay(
        booking_id=b2.id,
        guest_id=g2.id,
        room_id=created_rooms["202"].id,
        planned_checkin=now - timedelta(days=2),
        planned_checkout=now - timedelta(hours=3, minutes=30),
        actual_checkin=now - timedelta(days=2),
        status="Active",
        checked_in_by_id=reception_user.id
    )
    db.session.add(stay2)

    record_payment(
        booking_id=b2.id,
        amount=Decimal("2000.00"),
        payment_method="Cash",
        user_id=reception_user.id,
        transaction_ref="CASH-COUNTER",
        notes="Cash advance deposit",
        is_advance=True
    )

    # Guest 3: Future Confirmed Booking arriving today (Room 106)
    g3 = Guest(
        full_name="David Henderson",
        mobile="+44 7700 900123",
        email="d.henderson@london-travel.co.uk",
        country="United Kingdom",
        id_type="Passport",
        id_number="GB9920199"
    )
    db.session.add(g3)
    db.session.flush()

    b3 = Booking(
        booking_number="BK-2026-0003",
        guest_id=g3.id,
        room_category_id=cat_deluxe.id,
        booking_source="Online Website",
        status=BookingStatus.CONFIRMED,
        checkin_date=today,
        checkout_date=today + timedelta(days=3),
        expected_checkin_time="15:00",
        expected_checkout_time="11:00",
        adults_count=2,
        total_nights=3,
        agreed_rate_per_night=Decimal("2800.00"),
        tax_rate=Decimal("12.00"),
        tax_amount=Decimal("1008.00"),
        total_amount=Decimal("9408.00"),
        advance_payment=Decimal("4000.00"),
        payment_method="Credit / Debit Card",
        created_by_id=reception_user.id
    )
    db.session.add(b3)
    db.session.flush()

    br3 = BookingRoom(
        booking_id=b3.id,
        room_id=created_rooms["106"].id,
        rate_per_night=Decimal("2800.00")
    )
    db.session.add(br3)

    record_payment(
        booking_id=b3.id,
        amount=Decimal("4000.00"),
        payment_method="Credit / Debit Card",
        user_id=reception_user.id,
        transaction_ref="VISA-ONLINE-GATEWAY-9911",
        notes="Online card advance booking",
        is_advance=True
    )

    # Guest 4: Past Finalized Stay with Paid Invoice (Room 204)
    g4 = Guest(
        full_name="Ananya Roy",
        mobile="+91 97112 33445",
        email="ananya.roy@gmail.com",
        city="Kolkata",
        state="West Bengal",
        id_type="Voter ID",
        id_number="WB-09-12345"
    )
    db.session.add(g4)
    db.session.flush()

    b4 = Booking(
        booking_number="BK-2026-0004",
        guest_id=g4.id,
        room_category_id=cat_suite.id,
        booking_source="Phone Call",
        status=BookingStatus.CHECKED_OUT,
        checkin_date=today - timedelta(days=4),
        checkout_date=today - timedelta(days=1),
        expected_checkin_time="14:00",
        expected_checkout_time="11:00",
        adults_count=2,
        total_nights=3,
        agreed_rate_per_night=Decimal("4500.00"),
        tax_rate=Decimal("12.00"),
        tax_amount=Decimal("1620.00"),
        total_amount=Decimal("15120.00"),
        created_by_id=reception_user.id
    )
    db.session.add(b4)
    db.session.flush()

    br4 = BookingRoom(
        booking_id=b4.id,
        room_id=created_rooms["204"].id,
        rate_per_night=Decimal("4500.00")
    )
    db.session.add(br4)

    stay4 = Stay(
        booking_id=b4.id,
        guest_id=g4.id,
        room_id=created_rooms["204"].id,
        planned_checkin=now - timedelta(days=4),
        planned_checkout=now - timedelta(days=1),
        actual_checkin=now - timedelta(days=4),
        actual_checkout=now - timedelta(days=1),
        status="Completed",
        checked_in_by_id=reception_user.id,
        checked_out_by_id=reception_user.id
    )
    db.session.add(stay4)
    db.session.flush()

    # Finalize Invoice for Guest 4
    inv4 = finalize_invoice(
        booking=b4,
        user_id=reception_user.id,
        stay=stay4,
        notes="Guest had a pleasant stay and settled via corporate card."
    )
    # Record payment for full amount
    record_payment(
        booking_id=b4.id,
        amount=inv4.grand_total,
        payment_method="Credit / Debit Card",
        user_id=reception_user.id,
        invoice_id=inv4.id,
        transaction_ref="CORP-AMEX-0021"
    )

    print("Seeding Table Reservations & Active Orders...")
    res1 = TableReservation(
        reservation_number="RES-2026-0001",
        table_id=created_tables["T-04"].id,
        customer_name="Amitabh Sen",
        contact_number="+91 98450 67890",
        reservation_date=today,
        start_time="19:30",
        end_time="21:30",
        guest_count=6,
        special_requests="Family dinner table, birthday celebration",
        status="Confirmed",
        created_by_id=restaurant_user.id
    )
    db.session.add(res1)

    # Active Dining Order on Table T-02
    ord1 = RestaurantOrder(
        order_number="ORD-2026-0001",
        order_type="Dine-In",
        table_id=created_tables["T-02"].id,
        customer_name="Rohit Sharma",
        waiter_name="Sunil",
        status="In Progress",
        payment_status="Pending",
        subtotal=Decimal("860.00"),
        tax_rate=Decimal("5.00"),
        tax_amount=Decimal("43.00"),
        grand_total=Decimal("903.00"),
        created_by_id=restaurant_user.id
    )
    db.session.add(ord1)
    db.session.flush()

    oi1 = RestaurantOrderItem(
        order_id=ord1.id,
        menu_item_id=created_menu_items[0].id,
        item_name=created_menu_items[0].name,
        quantity=1,
        unit_price=Decimal("280.00"),
        total_price=Decimal("280.00")
    )
    oi2 = RestaurantOrderItem(
        order_id=ord1.id,
        menu_item_id=created_menu_items[6].id,
        item_name=created_menu_items[6].name,
        quantity=1,
        unit_price=Decimal("380.00"),
        total_price=Decimal("380.00")
    )
    oi3 = RestaurantOrderItem(
        order_id=ord1.id,
        menu_item_id=created_menu_items[8].id,
        item_name=created_menu_items[8].name,
        quantity=2,
        unit_price=Decimal("60.00"),
        total_price=Decimal("120.00")
    )
    oi4 = RestaurantOrderItem(
        order_id=ord1.id,
        menu_item_id=created_menu_items[11].id,
        item_name=created_menu_items[11].name,
        quantity=2,
        unit_price=Decimal("40.00"),
        total_price=Decimal("80.00")
    )
    db.session.add_all([oi1, oi2, oi3, oi4])

    db.session.commit()
    print("Database seeding completed successfully! Rich operational demo data ready.")
