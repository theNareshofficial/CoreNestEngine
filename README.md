# CoreNestEngine
: A powerful, centralized stock management system designed for seamless inventory tracking and efficient operations. 🚀
# CoreNestEngine 🚀
> A lightweight, centralized stock inventory and billing management system powered by Flask and a built-in SQLite database.

CoreNestEngine provides real-time inventory tracking, batch inward stock reception, point-of-sale billing, downloadable PDF invoices, audit logging, and sales analytics—with **zero external database dependencies**.

---

## 📋 Table of Contents
- [Highlights & Features](#-highlights--features)
- [Architecture & Built-in Database](#-architecture--built-in-database)
- [Project Directory Structure](#-project-directory-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Run (Windows)](#quick-run-windows)
  - [Quick Run (Linux / macOS)](#quick-run-linux--macos)
  - [Manual Installation](#manual-installation)
- [Default Login Credentials](#-default-login-credentials)
- [Configuration (.env)](#-configuration-env)
- [Application Flow & Routes](#-application-flow--routes)
- [Bugs Fixed & Improvements Made](#-bugs-fixed--improvements-made)
- [Tech Stack](#-tech-stack)

---

## ✨ Highlights & Features

- **Built-in Database**: Powered by standard Python SQLite3. Requires **no external MongoDB service** or separate database installation.
- **Auto-Initialization & Seeding**: Database tables, indexes, default admin account, and sample products are created automatically on the first run.
- **Stock Dashboard**: Real-time view of inventory levels, search functionality, in-stock/out-of-stock indicators, quick unit additions/deletions, and item log inspection.
- **Inward Stock Entry**: Add incoming product batches with purchase rate, sale price, dealer information, and automatic inventory synchronization.
- **Billing & POS System**: Select quantities from available stock with real-time total calculations, stock deduction checks, and interactive bill preview.
- **PDF Invoice Generation**: Download professional, print-ready PDF invoices generated dynamically using WeasyPrint.
- **Bill Search & Editing**: Search past invoices, view line items, edit quantities, and automatically reconcile stock adjustments.
- **Analytics & Daily Sales**: Visual sales overview powered by Chart.js, summarizing daily, weekly, and monthly revenue, units sold, and top products.
- **Audit & Activity Logs**: Comprehensive tracking of user logins/logouts, stock adjustments, deleted items, and invoice creations.
- **Responsive UI**: Modern interface built with Tailwind CSS, including mobile menu support and interactive alerts.

---

## 🗄️ Architecture & Built-in Database

CoreNestEngine replaces the previous MongoDB dependency with a robust, built-in SQLite database engine located in `db/database.py`.

### Database Schema Overview
- **`users`**: Stores user authentication credentials (hashed using Werkzeug pbkdf2/scrypt), phone numbers, registration dates, and login IP/browser metadata.
- **`inventory`**: Centralized inventory tracking with product name (case-insensitive unique index), dealer, current stock quantity, purchase rate, sale price, and audit timestamps.
- **`inward_history`**: Permanent historical record of every incoming stock batch received from suppliers.
- **`bills`**: Primary invoice registry containing unique bill numbers (`BILL-YYMMDD-XXXX`), customer details, mobile numbers, total amounts, and timestamps.
- **`bill_items`**: Line items for each bill referencing the parent bill via cascading foreign keys (`bill_id`).
- **`logs`**: Comprehensive system audit log capturing actions (`login`, `logout`, `inward`, `added`, `deleted`, `billing`, `bill_updated`), quantities, and JSON details.

Database connections are managed per-request via Flask's application context (`g.db`), with **WAL (Write-Ahead Logging)** mode and foreign key constraints enabled for optimal concurrency and data integrity.

---

## 📁 Project Directory Structure

```text
CoreNestEngine/
├── app.py                      # Application entry point & Flask factory
├── config/
│   └── flask_config.py         # App configuration & environment loader
├── db/
│   ├── database.py             # Built-in SQLite layer, schema, queries & seed data
│   └── db_config.py            # Database interface exports
├── modules/
│   ├── __init__.py
│   ├── auth/
│   │   └── session.py          # Session handling, timeout checks & auth decorators
│   └── routes/
│       ├── auth_routes.py      # Login, registration, and logout endpoints
│       ├── billing_routes.py   # Billing POS, bill search, edit & PDF generation
│       ├── core_routes.py      # Home analytics, user accounts, logs & update
│       └── inventory_routes.py # Stock dashboard, inward entry & stock adjustments
├── scripts/
│   └── update.py               # Self-update script via Git
├── templates/                  # Jinja2 HTML templates (Tailwind CSS)
│   ├── 404.html                # Custom 404 Not Found error page
│   ├── 500.html                # Custom 500 Internal Server Error page
│   ├── 505.html                # HTTP Version Not Supported error page
│   ├── activity_log.html       # User login/logout activity timeline
│   ├── base.html               # Base layout with responsive alert messages
│   ├── bill_detail.html        # Bill search and recent invoices view
│   ├── bill_pdf_template.html  # Clean HTML-to-PDF invoice template
│   ├── bill_template.html      # Post-checkout interactive bill receipt
│   ├── billing.html            # Point-of-sale product selection & checkout
│   ├── daily_sales.html        # Daily sales revenue breakdown
│   ├── dashboard.html          # Main inventory overview, stock actions & logs
│   ├── deleted_log.html        # Audit log for deleted items and reductions
│   ├── edit_bill.html          # Dynamic bill item modifier with stock rebalancing
│   ├── home.html               # Main analytics dashboard & Chart.js visualization
│   ├── inward.html             # Stock inward entry form & supplier batch list
│   ├── login.html              # User login screen with error notifications
│   ├── navbar.html             # Responsive navigation bar with mobile menu
│   ├── register.html           # New user registration screen
│   ├── settings.html           # Administrative settings layout
│   ├── update_status.html      # App update log display
│   └── user_accounts.html      # Registered user directory
├── .env.example                # Sample environment configuration file
├── .gitignore                  # Git ignore rules (includes *.db and data/)
├── requirements.txt            # Python package dependencies
├── run.sh                      # 1-Click execution script for Linux / macOS
└── setup.bat                   # 1-Click execution script for Windows
```

---

## 🚀 Getting Started

### Prerequisites
- Python **3.10** or higher installed.

---

### Quick Run (Windows)
Double-click `setup.bat` or run:
```cmd
setup.bat
```
*This automatically creates a virtual environment, installs dependencies, initializes the database, seeds default data, and starts the server.*

---

### Quick Run (Linux / macOS)
Execute the launch script:
```bash
./run.sh
```

---

### Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/theNareshofficial/CoreNestEngine.git
   cd CoreNestEngine
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```

5. **Start the application:**
   ```bash
   python app.py
   ```

6. **Open your browser:**
   Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔐 Default Login Credentials

Upon the initial run, the application automatically initializes the database and provisions a default administrator account:

| Field | Default Value |
|---|---|
| **Username** | `admin` |
| **Password** | `admin123` |

> 💡 *You can register new users through the `/register` page or manage user accounts from the Settings menu.*

---

## ⚙️ Configuration (.env)

The application supports configuration via `.env` (or standard environment variables):

```env
# Secret key for signing session cookies
SECRET_KEY=corenest-engine-secure-flask-key-2026-production

# Enable or disable debug mode
FLASK_DEBUG=True

# Server Host and Port
PORT=5000
HOST=127.0.0.1

# Path to the SQLite database file
DATABASE_PATH=data/corenest.db
```

---

## 🧭 Application Flow & Routes

| URL Route | Blueprint | Description |
|---|---|---|
| `/` | `core` | Landing redirect to `/home` (if authenticated) or `/login` |
| `/home` | `core` | Sales overview, KPI metrics & Chart.js graph |
| `/login` | `auth` | User login with session establishment |
| `/register` | `auth` | Account creation with password hashing |
| `/logout` | `auth` | Terminates session and logs audit event |
| `/dashboard` | `inventory` | Live inventory table with instant search and inline stock adjust |
| `/inward` | `inventory` | Form to receive inward stock from dealers |
| `/update_stock/<id>` | `inventory` | API endpoint to increase/decrease stock with negative-stock prevention |
| `/view_logs/<id>` | `inventory` | API endpoint returning stock item history |
| `/billing` | `billing` | Interactive checkout page for creating customer bills |
| `/bill_detail` | `billing` | Search invoices by bill number and view the last 25 bills |
| `/generate_pdf/<no>` | `billing` | Generates downloadable invoice PDF via WeasyPrint |
| `/edit_bill/<no>` | `billing` | Edit bill items and recalculate inventory automatically |
| `/daily_sales` | `core` | Daily revenue aggregate table |
| `/activity_log` | `core` | User authentication audit trail |
| `/deleted_log` | `core` | Record of stock removals and deleted items |
| `/user_accounts` | `core` | List of system user accounts |

---

## 🛠️ Bugs Fixed & Improvements Made

During the refactoring process, the following critical issues were resolved:

1. **Replaced MongoDB with Built-in SQLite**:
   - Eliminated the requirement to install and run an external MongoDB daemon (`localhost:27017`).
   - Replaced all PyMongo queries and ObjectId conversions with thread-safe, ACID-compliant SQLite operations using WAL mode.

2. **Fixed Broken Configuration in `app.py`**:
   - Fixed `app.config.update = app_config()` (which overwrote the dictionary update method) to `app.config.update(app_config())`.
   - Replaced random ephemeral secret keys with a persistent secret key to prevent user sessions from being discarded upon every server restart.

3. **Fixed Error Handlers & Broken Links**:
   - Fixed 500 handler which was returning a 505 error page with status code 505. Added dedicated `templates/500.html`.
   - Fixed broken `url_for('index')` in `templates/505.html` that threw `BuildError`.

4. **Fixed Broken PDF Generation**:
   - Removed uninstalled `xhtml2pdf` import that caused a `ModuleNotFoundError`.
   - Integrated `WeasyPrint` for fast, standards-compliant HTML-to-PDF invoice rendering with full UTF-8 Rupee (`₹`) symbol support.

5. **Fixed Incomplete Templates**:
   - `home.html`: Replaced an empty `<table ...></table>` tag with a populated "Products Sold Today" table.
   - `inward.html`: Fixed a table column mismatch where 7 header columns existed but only 6 row cells were rendered (missing Dealer column).
   - `deleted_log.html`: Fixed table `colspan="6"` to `colspan="7"`.
   - `navbar.html`: Populated the previously empty `#mobile-menu` container with mobile navigation links.
   - `bill_template.html`: Moved `<nav>` inclusion inside `<body>` instead of placing it before the `<!DOCTYPE html>` declaration.

6. **Fixed Session Expiration & Decorators**:
   - Updated `@SESSION.login_required` to use `functools.wraps`, preserving function signatures.
   - Fixed session timeout verification so expired sessions properly redirect to `/login` with a warning message.

7. **Fixed Form Feedback & Flash Messages**:
   - Added banner notifications to `base.html`, `login.html`, and `register.html` so validation failures and successes are visible.
   - Removed premature `SimpleSuccess()` alert on registration form submission.

8. **Fixed Stock Negative Value Glitches**:
   - Prevented inventory quantities from dropping below zero when deleting or adjusting stock.
   - Removed duplicate `log_stock_change` functions in `inventory_routes.py`.

---

## 📦 Tech Stack

- **Backend**: Python 3.10+, Flask 3.0+
- **Database**: SQLite3 (Built-in standard library)
- **PDF Engine**: WeasyPrint
- **Frontend**: Jinja2 Templates, Tailwind CSS (CDN), Chart.js
- **Environment**: Python-Dotenv, Werkzeug Security

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
