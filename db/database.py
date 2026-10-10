# db/database.py
"""
Built-in SQLite Database Layer for CoreNestEngine.
Provides thread-safe connections, automatic schema initialization,
and helper functions for inventory, billing, users, and audit logs.
"""

import os
import json
import sqlite3
import random
from datetime import datetime
from flask import g, current_app

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "corenest.db")


def get_db_path():
    """Returns the database file path from Flask config or environment or default."""
    try:
        if current_app and "DATABASE" in current_app.config:
            return current_app.config["DATABASE"]
    except RuntimeError:
        pass
    return os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)


def get_db():
    """
    Returns a thread-safe SQLite connection.
    If within a Flask request context, reuses connection stored in `g`.
    """
    try:
        if "db" not in g:
            db_path = get_db_path()
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON;")
            g.db.execute("PRAGMA journal_mode = WAL;")
        return g.db
    except RuntimeError:
        # Outside Flask application context (scripts, migrations, seeding)
        db_path = get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn


def close_db(e=None):
    """Closes the current database connection if one was opened in `g`."""
    try:
        db = g.pop("db", None)
        if db is not None:
            db.close()
    except RuntimeError:
        pass


def init_db(app=None):
    """Initializes tables and indexes in SQLite."""
    conn = get_db()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password TEXT NOT NULL,
            number TEXT,
            register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            browser TEXT
        );

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE NOT NULL COLLATE NOCASE,
            dealer TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
            rate REAL NOT NULL DEFAULT 0.0 CHECK (rate >= 0),
            price REAL NOT NULL DEFAULT 0.0 CHECK (price >= 0),
            user TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS inward_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            dealer TEXT DEFAULT '',
            quantity INTEGER NOT NULL,
            rate REAL NOT NULL,
            price REAL NOT NULL,
            user TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT UNIQUE NOT NULL,
            bill_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            customer_name TEXT DEFAULT '',
            mobile_number TEXT DEFAULT '',
            total_amount REAL NOT NULL DEFAULT 0.0,
            user TEXT,
            last_edited TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
            bill_no TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            sale_price REAL NOT NULL CHECK (sale_price >= 0),
            total REAL NOT NULL CHECK (total >= 0)
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            action TEXT NOT NULL,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_inventory_product_name ON inventory(product_name);
        CREATE INDEX IF NOT EXISTS idx_bills_bill_no ON bills(bill_no);
        CREATE INDEX IF NOT EXISTS idx_bills_bill_date ON bills(bill_date);
        CREATE INDEX IF NOT EXISTS idx_bill_items_bill_id ON bill_items(bill_id);
        CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action);
        CREATE INDEX IF NOT EXISTS idx_logs_product_id ON logs(product_id);
        CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
        """)

        # Automatic column migrations for Inward ERP Schema
        for col, col_def in [
            ("models", "TEXT DEFAULT 'NA'"),
            ("category", "TEXT DEFAULT 'NA'"),
            ("free_quantity", "TEXT DEFAULT 'NA'"),
            ("invoice_no", "TEXT DEFAULT 'NA'"),
            ("tax_rate", "TEXT DEFAULT 'NA'"),
            ("rack_number", "TEXT DEFAULT 'NA'"),
            ("timestamp_str", "TEXT DEFAULT ''"),
            ("margin_rate", "TEXT DEFAULT 'NA'"),
            ("landed_cost", "REAL DEFAULT 0.0"),
            ("calc_mode", "TEXT DEFAULT 'auto'"),
            ("pack_size", "TEXT DEFAULT 'NA'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE inward_history ADD COLUMN {col} {col_def};")
            except Exception:
                pass

        for col, col_def in [
            ("models", "TEXT DEFAULT 'NA'"),
            ("category", "TEXT DEFAULT 'NA'"),
            ("rack_number", "TEXT DEFAULT 'NA'"),
            ("tax_rate", "TEXT DEFAULT 'NA'"),
            ("margin_rate", "TEXT DEFAULT 'NA'"),
            ("landed_cost", "REAL DEFAULT 0.0"),
            ("calc_mode", "TEXT DEFAULT 'auto'"),
            ("pack_size", "TEXT DEFAULT 'NA'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE inventory ADD COLUMN {col} {col_def};")
            except Exception:
                pass

    print("✅ Built-in SQLite database initialized successfully!")


def parse_timestamp(val):
    """Safely converts a timestamp string or object into a Python datetime."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                pass
    return datetime.now()


# -------------------------------------------------------------
# User / Auth Queries
# -------------------------------------------------------------

def get_user_by_username(username):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_user(username, hashed_password, number, ip_address, browser):
    conn = get_db()
    with conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute(
            """
            INSERT INTO users (username, password, number, register_date, ip_address, browser)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, hashed_password, number, now, ip_address, browser)
        )
        return cursor.lastrowid


def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, number FROM users ORDER BY username ASC")
    return [dict(row) for row in cursor.fetchall()]


# -------------------------------------------------------------
# Logs & Audit Queries
# -------------------------------------------------------------

def log_event(user, action, product_id=None, product_name=None, quantity=None, details=None):
    conn = get_db()
    with conn:
        cursor = conn.cursor()
        now = datetime.now()
        details_json = json.dumps(details) if isinstance(details, (dict, list)) else (details or "")
        cursor.execute(
            """
            INSERT INTO logs (user, action, product_id, product_name, quantity, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user, action, product_id, product_name, quantity, details_json, now)
        )
        return cursor.lastrowid


def get_activity_logs(limit=100):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM logs 
        WHERE action IN ('login', 'logout') 
        ORDER BY timestamp DESC 
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["timestamp"] = parse_timestamp(d.get("timestamp"))
        result.append(d)
    return result


def get_deleted_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM logs 
        WHERE action = 'deleted' 
        ORDER BY timestamp DESC
        """
    )
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["timestamp"] = parse_timestamp(d.get("timestamp"))
        raw_details = d.get("details")
        if isinstance(raw_details, str) and raw_details.strip():
            try:
                d["details"] = json.loads(raw_details)
            except Exception:
                d["details"] = {}
        elif isinstance(raw_details, dict):
            d["details"] = raw_details
        else:
            d["details"] = {}
        result.append(d)
    return result


def get_logs_for_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM logs WHERE product_id = ? ORDER BY timestamp DESC",
        (product_id,)
    )
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["_id"] = str(d["id"])
        d["product_id"] = str(d["product_id"])
        ts = parse_timestamp(d.get("timestamp"))
        d["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")
        result.append(d)
    return result


# -------------------------------------------------------------
# Inventory Queries
# -------------------------------------------------------------

def get_inventory(search_query=None):
    conn = get_db()
    cursor = conn.cursor()
    if search_query:
        cursor.execute(
            "SELECT * FROM inventory WHERE product_name LIKE ? ORDER BY product_name ASC",
            (f"%{search_query.strip()}%",)
        )
    else:
        cursor.execute("SELECT * FROM inventory ORDER BY product_name ASC")
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["_id"] = str(d["id"])
        result.append(d)
    return result


def get_inventory_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        d["_id"] = str(d["id"])
        return d
    return None


def get_inventory_item_by_name(product_name):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE product_name = ? COLLATE NOCASE", (product_name.strip(),))
    row = cursor.fetchone()
    if row:
        d = dict(row)
        d["_id"] = str(d["id"])
        return d
    return None


def add_inward_stock(
    product_name,
    dealer,
    quantity,
    rate,
    price,
    user,
    models=None,
    category="NA",
    free_quantity="NA",
    invoice_no="NA",
    tax_rate="NA",
    rack_number="NA",
    timestamp_str=None,
    margin_rate="NA",
    landed_cost=0.0,
    calc_mode="auto",
    pack_size="NA"
):
    """
    Adds inward stock with ERP schema support including dynamic pricing fields.
    If product exists in inventory, updates quantity, rate, price, dealer, models, category, and rack.
    Records entry in inward_history and system audit logs.
    """
    conn = get_db()
    with conn:
        cursor = conn.cursor()
        now = datetime.now()
        if not timestamp_str or not str(timestamp_str).strip():
            timestamp_str = now.strftime('%d-%m-%Y %I:%M:%S %p')

        # Format and validate models
        if isinstance(models, (list, tuple)):
            clean_models = [str(m).strip() for m in models if str(m).strip()]
            models_json = json.dumps(clean_models) if clean_models else "NA"
        elif isinstance(models, str) and models.strip():
            try:
                parsed = json.loads(models)
                if isinstance(parsed, list):
                    clean_models = [str(m).strip() for m in parsed if str(m).strip()]
                    models_json = json.dumps(clean_models) if clean_models else "NA"
                else:
                    models_json = json.dumps([models.strip()])
            except Exception:
                parts = [p.strip() for p in models.split(",") if p.strip()]
                models_json = json.dumps(parts) if parts else "NA"
        else:
            models_json = "NA"

        # Apply default "NA" logic for optional fields
        free_quantity = str(free_quantity).strip() if free_quantity not in (None, "", "NA") else "NA"
        invoice_no = str(invoice_no).strip() if invoice_no not in (None, "", "NA") else "NA"
        tax_rate = str(tax_rate).strip() if tax_rate not in (None, "", "NA") else "NA"
        rack_number = str(rack_number).strip() if rack_number not in (None, "", "NA") else "NA"
        category = str(category).strip() if category not in (None, "", "NA") else "NA"
        margin_rate = str(margin_rate).strip() if margin_rate not in (None, "", "NA") else "NA"
        calc_mode = str(calc_mode).strip() if calc_mode not in (None, "") else "auto"
        pack_size = str(pack_size).strip() if pack_size not in (None, "", "NA") else "NA"

        # Ensure landed_cost is numeric
        try:
            landed_cost = float(landed_cost)
        except (ValueError, TypeError):
            landed_cost = 0.0

        # 1. Record in inward_history
        cursor.execute(
            """
            INSERT INTO inward_history (
                product_name, models, dealer, quantity, free_quantity,
                rate, price, category, invoice_no, tax_rate,
                rack_number, timestamp_str, user, added_at,
                margin_rate, landed_cost, calc_mode, pack_size
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_name, models_json, dealer, quantity, free_quantity,
                rate, price, category, invoice_no, tax_rate,
                rack_number, timestamp_str, user, now,
                margin_rate, landed_cost, calc_mode, pack_size
            )
        )

        # 2. Check if product already exists in inventory
        cursor.execute("SELECT id, quantity FROM inventory WHERE product_name = ? COLLATE NOCASE", (product_name,))
        existing = cursor.fetchone()

        if existing:
            item_id = existing["id"]
            cursor.execute(
                """
                UPDATE inventory 
                SET quantity = quantity + ?, rate = ?, price = ?, dealer = ?,
                    models = ?, category = ?, rack_number = ?,
                    tax_rate = ?, margin_rate = ?, landed_cost = ?,
                    calc_mode = ?, pack_size = ?,
                    user = ?, updated_at = ?
                WHERE id = ?
                """,
                (quantity, rate, price, dealer, models_json, category, rack_number,
                 tax_rate, margin_rate, landed_cost, calc_mode, pack_size,
                 user, now, item_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO inventory (
                    product_name, models, category, rack_number,
                    dealer, quantity, rate, price, user, added_at, updated_at,
                    tax_rate, margin_rate, landed_cost, calc_mode, pack_size
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_name, models_json, category, rack_number,
                    dealer, quantity, rate, price, user, now, now,
                    tax_rate, margin_rate, landed_cost, calc_mode, pack_size
                )
            )
            item_id = cursor.lastrowid

        # 3. Log inward addition
        log_event(
            user=user,
            action="inward",
            product_id=item_id,
            product_name=product_name,
            quantity=quantity,
            details={
                "rate": rate,
                "price": price,
                "dealer": dealer,
                "category": category,
                "models": models_json,
                "invoice_no": invoice_no,
                "free_quantity": free_quantity,
                "tax_rate": tax_rate,
                "rack_number": rack_number,
                "margin_rate": margin_rate,
                "landed_cost": landed_cost,
                "calc_mode": calc_mode,
                "pack_size": pack_size,
                "timestamp_str": timestamp_str,
                "user": user
            }
        )

        return item_id


def get_inward_history(limit=50):
    """Returns recent inward stock historical records with parsed models."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM inward_history 
        ORDER BY id DESC 
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["_id"] = str(d["id"])
        raw_m = d.get("models") or "NA"
        if raw_m.startswith("[") and raw_m.endswith("]"):
            try:
                d["models_list"] = json.loads(raw_m)
            except Exception:
                d["models_list"] = [raw_m]
        elif raw_m != "NA":
            d["models_list"] = [m.strip() for m in raw_m.split(",") if m.strip()]
        else:
            d["models_list"] = []

        if not d.get("timestamp_str"):
            ts = parse_timestamp(d.get("added_at"))
            d["timestamp_str"] = ts.strftime('%d-%m-%Y %I:%M:%S %p')

        # Ensure defaults for legacy records
        for key in ("free_quantity", "invoice_no", "tax_rate", "rack_number", "category", "margin_rate", "calc_mode", "pack_size"):
            if not d.get(key) or d.get(key) == "":
                d[key] = "NA"
        if not d.get("landed_cost"):
            d["landed_cost"] = 0.0

        result.append(d)
    return result


def get_inward_suggestions():
    """
    Returns distinct historical values with entry frequency counts
    for Product Name, Models, Dealers, Categories, and Rack Numbers.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Products with historical count
    cursor.execute("""
        SELECT product_name, COUNT(*) as count 
        FROM inward_history 
        WHERE product_name IS NOT NULL AND product_name != ''
        GROUP BY product_name 
        ORDER BY count DESC, product_name ASC
    """)
    products = [{"value": r["product_name"], "count": r["count"]} for r in cursor.fetchall()]

    # Dealers with count
    cursor.execute("""
        SELECT dealer, COUNT(*) as count 
        FROM inward_history 
        WHERE dealer IS NOT NULL AND dealer != ''
        GROUP BY dealer 
        ORDER BY count DESC, dealer ASC
    """)
    dealers = [{"value": r["dealer"], "count": r["count"]} for r in cursor.fetchall()]

    # Categories with count
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM inward_history 
        WHERE category IS NOT NULL AND category != '' AND category != 'NA'
        GROUP BY category 
        ORDER BY count DESC, category ASC
    """)
    categories = [{"value": r["category"], "count": r["count"]} for r in cursor.fetchall()]

    # Racks with count
    cursor.execute("""
        SELECT rack_number, COUNT(*) as count 
        FROM inward_history 
        WHERE rack_number IS NOT NULL AND rack_number != '' AND rack_number != 'NA'
        GROUP BY rack_number 
        ORDER BY count DESC, rack_number ASC
    """)
    racks = [{"value": r["rack_number"], "count": r["count"]} for r in cursor.fetchall()]

    # Models with count
    cursor.execute("""
        SELECT models 
        FROM inward_history 
        WHERE models IS NOT NULL AND models != '' AND models != 'NA'
    """)
    model_counts = {}
    for r in cursor.fetchall():
        raw = r["models"]
        if raw.startswith("[") and raw.endswith("]"):
            try:
                m_list = json.loads(raw)
            except Exception:
                m_list = [m.strip() for m in raw.split(",") if m.strip()]
        else:
            m_list = [m.strip() for m in raw.split(",") if m.strip()]
        for m in m_list:
            clean = m.strip()
            if clean and clean != "NA":
                model_counts[clean] = model_counts.get(clean, 0) + 1

    models = [{"value": k, "count": v} for k, v in sorted(model_counts.items(), key=lambda x: (-x[1], x[0]))]

    return {
        "products": products,
        "dealers": dealers,
        "categories": categories,
        "racks": racks,
        "models": models
    }


def update_inventory_stock(item_id, quantity_change, user):
    """
    Adjusts stock for an item. Prevents negative stock.
    Records deletion / addition in audit log.
    """
    conn = get_db()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Item not found."
        item = dict(row)

        current_qty = item["quantity"]
        new_qty = current_qty + quantity_change

        if new_qty < 0:
            return False, f"Cannot reduce stock below zero. Current stock is {current_qty}."

        cursor.execute(
            "UPDATE inventory SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_qty, item_id)
        )

        action = "added" if quantity_change > 0 else "deleted"
        log_event(
            user=user,
            action=action,
            product_id=item_id,
            product_name=item["product_name"],
            quantity=abs(quantity_change),
            details={
                "rate": item["rate"],
                "price": item["price"],
                "dealer": item.get("dealer", "N/A"),
                "user": user
            }
        )

        return True, f"{abs(quantity_change)} stock {'added to' if action == 'added' else 'removed from'} '{item['product_name']}'."


# -------------------------------------------------------------
# Billing Queries
# -------------------------------------------------------------

def get_available_stock():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory WHERE quantity > 0 ORDER BY product_name ASC")
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["_id"] = str(d["id"])
        result.append(d)
    return result


def create_bill(customer_name, mobile_number, items, user):
    """
    Creates a new bill, its line items, and decrements stock in a single transaction.
    Returns the created bill_data dict or raises ValueError if insufficient stock.
    """
    conn = get_db()
    with conn:
        cursor = conn.cursor()

        # 1. Validate all stock availability first
        for itm in items:
            p_name = itm["product_name"]
            qty = itm["quantity"]
            cursor.execute("SELECT quantity, price FROM inventory WHERE product_name = ? COLLATE NOCASE", (p_name,))
            stock_row = cursor.fetchone()
            if not stock_row:
                raise ValueError(f"Product '{p_name}' not found in inventory!")
            if stock_row["quantity"] < qty:
                raise ValueError(f"Not enough stock for '{p_name}'. Available: {stock_row['quantity']}, Requested: {qty}")

        # 2. Generate unique bill number
        now = datetime.now()
        bill_number = f"BILL-{now.strftime('%y%m%d')}-{random.randint(1000, 9999)}"
        # Check collision
        while True:
            cursor.execute("SELECT id FROM bills WHERE bill_no = ?", (bill_number,))
            if not cursor.fetchone():
                break
            bill_number = f"BILL-{now.strftime('%y%m%d')}-{random.randint(1000, 9999)}"

        total_amount = sum(itm["total"] for itm in items)

        # 3. Insert bill
        cursor.execute(
            """
            INSERT INTO bills (bill_no, bill_date, customer_name, mobile_number, total_amount, user)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (bill_number, now, customer_name, mobile_number, total_amount, user)
        )
        bill_id = cursor.lastrowid

        # 4. Insert items and decrement stock
        for itm in items:
            cursor.execute(
                """
                INSERT INTO bill_items (bill_id, bill_no, product_name, quantity, sale_price, total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bill_id, bill_number, itm["product_name"], itm["quantity"], itm["sale_price"], itm["total"])
            )
            cursor.execute(
                "UPDATE inventory SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE product_name = ? COLLATE NOCASE",
                (itm["quantity"], itm["product_name"])
            )

        # 5. Log billing event
        log_event(
            user=user,
            action="billing",
            product_name=bill_number,
            quantity=len(items),
            details={"customer": customer_name, "total_amount": total_amount, "bill_no": bill_number}
        )

        bill_data = {
            "id": bill_id,
            "bill_no": bill_number,
            "bill_date": now,
            "formatted_date": now.strftime('%d-%b-%Y %I:%M %p'),
            "customer_name": customer_name,
            "mobile_number": mobile_number,
            "items": items,
            "total_amount": total_amount,
            "user": user
        }
        return bill_data


def get_bill(bill_no):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE bill_no = ?", (bill_no.strip(),))
    bill_row = cursor.fetchone()
    if not bill_row:
        return None

    bill_data = dict(bill_row)
    b_date = parse_timestamp(bill_data.get("bill_date"))
    bill_data["bill_date"] = b_date
    bill_data["formatted_date"] = b_date.strftime('%d-%b-%Y %I:%M %p')

    last_ed = bill_data.get("last_edited")
    if last_ed:
        last_ed_dt = parse_timestamp(last_ed)
        bill_data["is_edited"] = True
        bill_data["last_edited"] = last_ed_dt
        bill_data["formatted_last_edited"] = last_ed_dt.strftime('%d-%b-%Y %I:%M %p')
    else:
        bill_data["is_edited"] = False
        bill_data["formatted_last_edited"] = None

    cursor.execute("SELECT * FROM bill_items WHERE bill_id = ?", (bill_data["id"],))
    bill_data["items"] = [dict(r) for r in cursor.fetchall()]
    return bill_data


def get_recent_bills(limit=25):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills ORDER BY bill_date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        b_date = parse_timestamp(d.get("bill_date"))
        d["bill_date"] = b_date
        d["formatted_date"] = b_date.strftime('%d-%b-%Y')
        last_ed = d.get("last_edited")
        if last_ed:
            last_ed_dt = parse_timestamp(last_ed)
            d["is_edited"] = True
            d["last_edited"] = last_ed_dt
            d["formatted_last_edited"] = last_ed_dt.strftime('%d-%b-%Y %I:%M %p')
        else:
            d["is_edited"] = False
            d["formatted_last_edited"] = None
        result.append(d)
    return result


def update_bill(bill_no, updated_items, user):
    """
    Updates an existing bill items and adjusts stock differences accordingly.
    """
    conn = get_db()
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE bill_no = ?", (bill_no,))
        old_bill = cursor.fetchone()
        if not old_bill:
            return False, "Bill not found."

        bill_id = old_bill["id"]

        # Get old items
        cursor.execute("SELECT product_name, quantity FROM bill_items WHERE bill_id = ?", (bill_id,))
        old_items_map = {r["product_name"]: r["quantity"] for r in cursor.fetchall()}

        new_items_map = {item["product_name"]: item["quantity"] for item in updated_items}

        # Check stock for products whose quantity increased
        for p_name, new_qty in new_items_map.items():
            old_qty = old_items_map.get(p_name, 0)
            stock_needed = new_qty - old_qty
            if stock_needed > 0:
                cursor.execute("SELECT quantity FROM inventory WHERE product_name = ? COLLATE NOCASE", (p_name,))
                inv = cursor.fetchone()
                if not inv or inv["quantity"] < stock_needed:
                    avail = inv["quantity"] if inv else 0
                    return False, f"Not enough stock to increase '{p_name}'. Need {stock_needed}, available: {avail}"

        # Adjust inventory stock
        # For items updated or newly added:
        for item in updated_items:
            p_name = item["product_name"]
            new_qty = item["quantity"]
            old_qty = old_items_map.get(p_name, 0)
            stock_change = old_qty - new_qty  # If old was 5 and new is 3, stock_change is +2 back to inventory
            cursor.execute(
                "UPDATE inventory SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE product_name = ? COLLATE NOCASE",
                (stock_change, p_name)
            )

        # For items removed from the bill: return full old quantity back to stock
        removed_products = set(old_items_map.keys()) - set(new_items_map.keys())
        for p_name in removed_products:
            old_qty = old_items_map[p_name]
            cursor.execute(
                "UPDATE inventory SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE product_name = ? COLLATE NOCASE",
                (old_qty, p_name)
            )

        # Delete old bill_items and re-insert new items
        cursor.execute("DELETE FROM bill_items WHERE bill_id = ?", (bill_id,))
        new_total_amount = sum(item["total"] for item in updated_items)

        for item in updated_items:
            cursor.execute(
                """
                INSERT INTO bill_items (bill_id, bill_no, product_name, quantity, sale_price, total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (bill_id, bill_no, item["product_name"], item["quantity"], item["sale_price"], item["total"])
            )

        # Update bill record
        now = datetime.now()
        cursor.execute(
            """
            UPDATE bills 
            SET total_amount = ?, last_edited = ?
            WHERE id = ?
            """,
            (new_total_amount, now, bill_id)
        )

        log_event(
            user=user,
            action="bill_updated",
            product_name=bill_no,
            quantity=len(updated_items),
            details={"bill_no": bill_no, "new_total": new_total_amount}
        )

        return True, "Bill updated successfully."


# -------------------------------------------------------------
# Reporting & Analytics Queries
# -------------------------------------------------------------

def get_sales_stats(start_date, end_date):
    """Calculates total sales revenue and total quantity of items sold within range."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            COALESCE(SUM(bi.total), 0) AS total_sales,
            COALESCE(SUM(bi.quantity), 0) AS total_items
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.bill_date >= ? AND b.bill_date <= ?
        """,
        (start_date, end_date)
    )
    row = cursor.fetchone()
    return {"total_sales": float(row["total_sales"]), "total_items": int(row["total_items"])}


def get_sales_by_product(start_date, end_date):
    """Returns list of products sold in date range grouped by product_name."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            bi.product_name,
            SUM(bi.quantity) AS quantity_sold
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        WHERE b.bill_date >= ? AND b.bill_date <= ?
        GROUP BY bi.product_name
        ORDER BY quantity_sold DESC
        """,
        (start_date, end_date)
    )
    return [dict(r) for r in cursor.fetchall()]


def get_daily_sales_history():
    """Returns daily sales grouped by date descending."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            strftime('%Y-%m-%d', bill_date) AS date,
            strftime('%Y-%m-%d', bill_date) AS _id,
            SUM(total_amount) AS total_sales
        FROM bills
        GROUP BY strftime('%Y-%m-%d', bill_date)
        ORDER BY date DESC
        """
    )
    return [dict(r) for r in cursor.fetchall()]


def get_billing_history(start_date=None, end_date=None, limit=None, offset=0):
    """
    Retrieves bills and their associated bill_items within a given date range.
    Calculates aggregate sales amount, bill count, and total items sold.
    """
    conn = get_db()
    cursor = conn.cursor()

    conditions = []
    params = []

    if start_date:
        if isinstance(start_date, datetime):
            start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(start_date, str) and len(start_date.strip()) == 10:
            start_str = f"{start_date.strip()} 00:00:00"
        else:
            start_str = str(start_date).strip()
        conditions.append("b.bill_date >= ?")
        params.append(start_str)

    if end_date:
        if isinstance(end_date, datetime):
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(end_date, str) and len(end_date.strip()) == 10:
            end_str = f"{end_date.strip()} 23:59:59"
        else:
            end_str = str(end_date).strip()
        conditions.append("b.bill_date <= ?")
        params.append(end_str)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Aggregate stats for the period
    cursor.execute(
        f"""
        SELECT 
            COALESCE(SUM(b.total_amount), 0) AS total_sales,
            COUNT(b.id) AS total_bills
        FROM bills b
        {where_clause}
        """,
        params
    )
    agg_row = cursor.fetchone()
    total_sales = float(agg_row["total_sales"]) if agg_row else 0.0
    total_bills = int(agg_row["total_bills"]) if agg_row else 0

    # Total items quantity for the period
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(bi.quantity), 0) AS total_items
        FROM bill_items bi
        JOIN bills b ON bi.bill_id = b.id
        {where_clause}
        """,
        params
    )
    items_row = cursor.fetchone()
    total_items = int(items_row["total_items"]) if items_row else 0

    # Query matching bills
    query = f"SELECT * FROM bills b {where_clause} ORDER BY b.bill_date DESC"
    query_params = list(params)
    if limit is not None:
        query += " LIMIT ?"
        query_params.append(int(limit))
        if offset:
            query += " OFFSET ?"
            query_params.append(int(offset))

    cursor.execute(query, query_params)
    bill_rows = cursor.fetchall()

    if not bill_rows:
        return {
            "bills": [],
            "total_sales": total_sales,
            "total_bills": total_bills,
            "total_items": total_items
        }

    # Fetch items for all returned bills in one query
    bill_ids = [r["id"] for r in bill_rows]
    placeholders = ",".join("?" for _ in bill_ids)
    cursor.execute(
        f"""
        SELECT bill_id, product_name, quantity, sale_price, total
        FROM bill_items
        WHERE bill_id IN ({placeholders})
        ORDER BY id ASC
        """,
        bill_ids
    )
    items_by_bill = {}
    for item_row in cursor.fetchall():
        bid = item_row["bill_id"]
        if bid not in items_by_bill:
            items_by_bill[bid] = []
        items_by_bill[bid].append({
            "product_name": item_row["product_name"],
            "quantity": int(item_row["quantity"]),
            "sale_price": float(item_row["sale_price"]),
            "total": float(item_row["total"])
        })

    bills_list = []
    for r in bill_rows:
        b = dict(r)
        b_date = parse_timestamp(b.get("bill_date"))
        b["bill_date"] = b_date
        b["formatted_date"] = b_date.strftime('%d-%b-%Y %I:%M %p')
        b["formatted_date_short"] = b_date.strftime('%d-%b-%Y')
        b["customer_name"] = b.get("customer_name") or "Walk-in Customer"
        b["mobile_number"] = b.get("mobile_number") or "NA"
        b["total_amount"] = float(b.get("total_amount", 0.0))
        b["user"] = b.get("user") or "System"

        last_ed = b.get("last_edited")
        if last_ed:
            last_ed_dt = parse_timestamp(last_ed)
            b["is_edited"] = True
            b["last_edited"] = last_ed_dt
            b["formatted_last_edited"] = last_ed_dt.strftime('%d-%b-%Y %I:%M %p')
        else:
            b["is_edited"] = False
            b["formatted_last_edited"] = None

        bill_items = items_by_bill.get(b["id"], [])
        b["items"] = bill_items
        b["billed_items"] = bill_items
        b["total_quantity"] = sum(item["quantity"] for item in bill_items)
        bills_list.append(b)

    return {
        "bills": bills_list,
        "total_sales": total_sales,
        "total_bills": total_bills,
        "total_items": total_items
    }


def seed_sample_data(default_user="admin", default_pass="admin123"):
    """
    Populates default admin user and initial stock if the database is empty.
    Useful for instant out-of-the-box running!
    """
    from werkzeug.security import generate_password_hash

    conn = get_db()
    cursor = conn.cursor()

    # Check if users table is empty
    cursor.execute("SELECT COUNT(*) AS cnt FROM users")
    if cursor.fetchone()["cnt"] == 0:
        create_user(
            username=default_user,
            hashed_password=generate_password_hash(default_pass),
            number="9876543210",
            ip_address="127.0.0.1",
            browser="System Default"
        )
        print(f"✨ Default admin user created! (Username: {default_user}, Password: {default_pass})")

    # Check if inventory is empty
    cursor.execute("SELECT COUNT(*) AS cnt FROM inventory")
    if cursor.fetchone()["cnt"] == 0:
        sample_items = [
            ("MacBook Pro M3", "Apple Inc.", 10, 150000.0, 175000.0),
            ("Dell XPS 15", "Dell Corp.", 15, 110000.0, 130000.0),
            ("Sony WH-1000XM5", "Sony India", 25, 22000.0, 28000.0),
            ("Logitech MX Master 3S", "Logitech", 40, 6500.0, 8999.0),
            ("Samsung 32\" 4K Monitor", "Samsung", 12, 28000.0, 35000.0)
        ]
        for name, dealer, qty, rate, price in sample_items:
            add_inward_stock(name, dealer, qty, rate, price, default_user)
        print("✨ Sample inventory items seeded!")
