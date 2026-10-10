# 🏨 Grand Horizon - Hotel & Restaurant Management System

A production-grade, full-featured **Hotel and Restaurant Management System** built with **Python Flask**, **Flask-SQLAlchemy**, **Flask-Login**, **Flask-WTF**, and styled with a modern **Light UI design system featuring 3D tactile aesthetics**.

---

## 🌟 Key Features

### 1. Dual Main Dashboard
- **Hotel Operations**: Real-time metrics for total rooms, occupied rooms, available rooms, reserved rooms, cleaning/maintenance rooms, today's check-ins, today's check-outs, overdue check-outs alert, today's room revenue, and outstanding payments.
- **Restaurant Operations**: Live metrics for total dining tables, table occupancy status, today's POS orders count, and dining revenue.
- **Quick Action Trays**: Direct access to New Walk-in Check-in, Advance Booking, POS Terminal, Table Reservations, and Billing.

### 2. Room Categories & Rate Management
- Dynamic category creation (Standard, Deluxe, AC Deluxe, Suite, Executive, etc.).
- Configurable base prices, maximum guests, AC/Non-AC, bed count, tax rates, extra adult/child pricing.
- **Historical Rate Preservation**: Bookings lock in the agreed rate at reservation confirmation time so subsequent rate adjustments do not alter past or active bookings.

### 3. Floor-Wise & Room Management (3D Room Grid)
- Floor grouping with visual room cards featuring tactile 3D elevation and status indicators (`Available`, `Occupied`, `Reserved`, `Cleaning`, `Maintenance`, `Out of Service`).
- Room status modal for quick notes update and maintenance tagging.
- Quick **"Mark Cleaned"** workflow to safely return rooms from `Cleaning` to `Available`.
- **Double-Booking & Conflict Prevention**: Strict database validation preventing overlapping stays or conflicting room reservations.

### 4. Guest Registration & Advance Bookings
- Fast guest lookup and profile registration with government ID tracking.
- Immediate Walk-in Check-in with auto-generated booking references (`BK-XXXXXX`).
- Advance reservation scheduling with date/time conflict verification.
- Searchable directory of guests, active stays, and upcoming bookings.

### 5. Check-In & Check-Out Operations
- **Dedicated Check-In Workflow**: Instant verification, allocated room readiness check, and automatic timestamp recording.
- **Dedicated Check-Out Workflow**: Automatic night calculation using `Decimal` arithmetic, extra bed/charges aggregation, restaurant folio consolidation, instant bill generation, and automatic room transition to `Cleaning`.
- **Overdue Check-out Monitoring**: Real-time elapsed duration calculation comparing planned departure timestamp vs. current time.

### 6. Billing, Payments & PDF Invoices
- Itemized invoicing with room tariff breakdown, tax calculations (GST), restaurant folio charges, and partial/full payment tracking.
- **Immutable Invoice Snapshots**: Finalized bills store complete JSON line items and rate snapshots.
- **Dual Invoice Format**: Printable clean HTML invoice with browser print styling and server-side downloadable PDF generated with ReportLab.

### 7. Restaurant Dining & Table POS
- Visual 3D dining table grid by seating capacity and dining section (Indoor, Outdoor Terrace, Family Dining).
- Table reservation system with start/end time slot conflict prevention.
- Interactive POS terminal with dynamic category switching, live cart computation, takeaway handling, and payment options.
- **Post to Guest Room Folio**: Restaurant orders can be charged directly to a checked-in guest's room bill folio.

### 8. Analytics & Operational Reports
- Daily, weekly, monthly revenue summaries.
- Occupancy reports by floor and room category.
- In-house guest roster and overdue stay tracking.
- One-click **CSV Data Export** for all operational reports.

### 9. Role-Based Access Control (RBAC) & Audit Logging
- Enforced server-side permission decorators (`admin_required`, `manager_required`, `receptionist_required`, `restaurant_required`).
- Comprehensive audit trail recording every check-in, check-out, bill payment, status change, and login event.

---

## 👥 Default Demo User Credentials

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Full system access, rates, taxes, user management, audit logs |
| **Manager** | `manager` | `manager123` | Operational dashboard, room status, reports, billing |
| **Receptionist** | `reception` | `staff123` | Front desk, walk-ins, check-in/out, folio billing, room service orders |
| **Restaurant Staff** | `chef` | `chef123` | Table seating, POS order management, dining reservations |

---

## 🚀 Installation & Running Locally

### 1. Prerequisites
- Python 3.10, 3.11, or newer.
- Git (optional).

### 2. Setup Virtual Environment
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize & Seed Demo Database
```bash
python seed.py
```

### 5. Launch the Application
```bash
python run.py
```
Open your browser and navigate to: **http://127.0.0.1:5000**

---

## 🧪 Automated Testing

Run the test suite with pytest:
```bash
python -m pytest tests/ -v
```
All 17 automated tests cover authentication, role permissions, overlap prevention, check-in/check-out lifecycle, decimal billing, invoice generation, restaurant POS folio charging, and reports.

---

## 📂 Project Architecture

```text
Hotel-Room-Management/
├── app/
│   ├── __init__.py            # Flask Application Factory
│   ├── config.py              # Configuration environments (Dev, Test, Prod)
│   ├── extensions.py          # SQLAlchemy, Flask-Login, CSRF, Migrate instances
│   ├── models/                # Normalized domain models
│   │   ├── user.py            # User, Role, AuditLog
│   │   ├── hotel.py           # HotelSettings, Floor, RoomCategory, Room, RoomStatus
│   │   ├── booking.py         # Guest, Booking, BookingRoom, Stay, BookingStatus
│   │   ├── billing.py         # Invoice, InvoiceLineItem, Payment, GuestFolioCharge
│   │   └── restaurant.py      # RestaurantTable, TableReservation, Menu, Orders
│   ├── forms/                 # Flask-WTF validation forms
│   ├── routes/                # Blueprint controllers
│   │   ├── auth.py            # Authentication & profile management
│   │   ├── dashboard.py       # Dual operational metrics dashboard
│   │   ├── rooms.py           # 3D Floor-wise room grid & status updates
│   │   ├── categories.py      # Room category & dynamic rate management
│   │   ├── bookings.py        # Guest registration & reservations
│   │   ├── checkin_out.py     # Check-in, check-out & overdue monitoring
│   │   ├── billing.py         # Invoice generation, PDF export, payment receipts
│   │   ├── restaurant.py      # Dining tables, POS terminal, room folio posting
│   │   ├── reports.py         # Operational reports & CSV downloads
│   │   └── settings.py        # Hotel settings, tax rates, audit trail
│   ├── services/              # Encapsulated business logic
│   │   ├── availability.py    # Date-range room & table collision detection
│   │   ├── billing_service.py # Decimal calculations, line item snapshots, PDF generation
│   │   └── audit_service.py   # Activity audit trail logger
│   └── utils/
│       ├── decorators.py      # Server-side RBAC decorators
│       └── helpers.py         # Currency, date, and overdue text formatters
├── static/
│   ├── css/
│   │   ├── tokens.css         # Design tokens & color palette
│   │   └── custom.css         # Light UI 3D tactile styling & elevations
│   └── js/
│       ├── main.js            # Interactive modals, tooltips, dynamic helpers
│       └── pos.js             # Restaurant POS dynamic shopping cart & search
├── templates/                 # Jinja2 templates
│   ├── base.html              # Layout shell with sidebar navigation
│   ├── auth/                  # Login & password update views
│   ├── dashboard/             # Dual operations dashboard
│   ├── rooms/                 # Floor room grid & room CRUD
│   ├── categories/            # Category & rate management
│   ├── bookings/              # Guest registration & booking list
│   ├── checkin_out/           # Check-in, check-out & overdue monitors
│   ├── billing/               # Invoices list, HTML invoice, payment receipts
│   ├── restaurant/            # Table grid, reservations, interactive POS
│   ├── reports/               # Financial & occupancy reports
│   ├── settings/              # Settings & audit logs
│   └── errors/                # 403, 404, 500 error views
├── tests/                     # 17 automated test suites
├── seed.py                    # Database seeder with realistic test data
├── run.py                     # Entry point development server
├── requirements.txt           # Pinned production dependencies
└── .env.example               # Environment variables template
```
