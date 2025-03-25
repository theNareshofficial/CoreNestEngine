import random
from flask import Flask, render_template, redirect, url_for, request, flash, session, make_response, json, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db.db_config import reg_info, inward_info, bill_collection_data, sales_history
from config.flask_config import app_key, app_config
from modules.auth.session import SESSION
from datetime import datetime, timedelta
from bson.json_util import dumps

app = Flask(__name__)
app.secret_key = app_key()
app.config.update = app_config()

def get_user_info():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.user_agent.string
    return user_ip, user_agent

# Home Route redirects to login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        number = request.form["number"]

        if reg_info.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        user_ip, user_browser = get_user_info()
        register_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        register_data = {
            "username": username, 
            "password": hashed_password,
            "number": number,
            "register_date": register_date,
            "ip_address": user_ip,
            "browser": user_browser
        }

        reg_info.insert_one(register_data)
        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = reg_info.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password", "error")
            return render_template("login.html")

    return render_template('login.html')

# Dashboard with Live Search
@app.route('/dashboard.html', methods=['GET', 'POST'])
def dashboard():
    search_query = request.args.get('search', '')

    if search_query:
        stock_items = list(inward_info.find(
            {"product_name": {"$regex": search_query, "$options": "i"}},
            {"_id": 1, "product_name": 1, "quantity": 1, "rate": 1, "price": 1}
        ))
    else:
        stock_items = list(inward_info.find({}, {"_id": 1, "product_name": 1, "quantity": 1, "rate": 1, "price": 1}))

    return render_template("dashboard.html", inward_stock=stock_items, search_query=search_query)

# Route to handle deletion
@app.route('/delete_item/<item_id>', methods=['POST'])
def delete_item(item_id):
    user = "Admin"  # Replace with dynamic user session info later if needed

    item = inward_info.find_one({"_id": item_id})
    if item:
        inward_info.delete_one({"_id": item_id})
        logs.insert_one({
            "user": user,
            "item_name": item['product_name'],
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return jsonify({"status": "success", "message": "Item deleted successfully"})
    return jsonify({"status": "error", "message": "Item not found"})

def clean_json(data):
    """ Convert MongoDB cursor data into clean JSON format """
    if isinstance(data, list):
        return [clean_json(item) for item in data]
    if isinstance(data, dict):
        return {k: (str(v) if k == "_id" else v) for k, v in data.items()}
    return data

# 🔥 Route: Home Page with Sales Tracking
@app.route('/home')
def home():
    today = datetime.now().strftime("%Y-%m-%d")
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
    month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")

    # Fetch data and clean JSON
    daily_sales = clean_json(list(sales_history.find({"date": today})))
    weekly_sales = clean_json(list(sales_history.find({"date": {"$gte": week_start}})))
    monthly_sales = clean_json(list(sales_history.find({"date": {"$gte": month_start}})))

    daily_total = sum(item['quantity_sold'] for item in daily_sales)
    weekly_total = sum(item['quantity_sold'] for item in weekly_sales)
    monthly_total = sum(item['quantity_sold'] for item in monthly_sales)

    return render_template(
        "home.html",
        daily_sales=daily_sales,
        weekly_sales=weekly_sales,
        monthly_sales=monthly_sales,
        daily_total=daily_total,
        weekly_total=weekly_total,
        monthly_total=monthly_total
    )

# ✅ API Route: JSON Response (optional)
@app.route('/api/sales', methods=['GET'])
def api_sales():
    sales_data = list(sales_history.find())
    return jsonify(json.loads(dumps(sales_data)))

# Inward Stock Route
@app.route('/inward', methods=['GET', 'POST'])
def inward():
    SESSION.login()
    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip().capitalize()
        quantity = request.form.get("quantity", "0").strip()
        rate = request.form.get("rate", "0").strip()
        price = request.form.get("price", "0").strip()  # Now takes manual price

        if not product_name or not quantity or not rate or not price:
            flash("All fields are required!", "error")
            return redirect(url_for("inward"))

        inward_data = {
            "product_name": product_name,
            "quantity": int(quantity),
            "rate": float(rate),
            "price": float(price),  # Uses manual price now
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        inward_info.insert_one(inward_data)
        flash("Inward stock added successfully!", "success")
        return redirect(url_for("inward"))

    stock_items = list(inward_info.find({}, {"_id": 0}))
    return render_template("inward.html", inward_stock=stock_items)

# Bill Detail Route
@app.route("/bill_detail.html", methods=["GET"])
def bill_detail():
    SESSION.login()
    bill_no = request.args.get("bill_no", "").strip().upper()
    bill_data = None

    if bill_no:
        bill_data = bill_collection_data.find_one({"bill_no": bill_no}, {"_id": 0})

    return render_template("bill_detail.html", bill_data=bill_data, bill_no=bill_no)

@app.route('/billing', methods=['GET', 'POST'])
def billing_page():
    if request.method == 'POST':
        customer_name = request.form.get("customer_name", "").strip().capitalize()
        mobile_number = request.form.get("mobile_number", "").strip()
        selected_items = [item["product_name"] for item in inward_info.find({}, {"_id": 0, "product_name": 1})]

        if not customer_name:
            flash("Customer name is required!", "error")
            return redirect(url_for("billing_page"))

        items = []
        total_amount = 0

        for item_name in selected_items:
            quantity = int(request.form.get(f"quantity_{item_name}", "0"))
            item_data = inward_info.find_one({"product_name": item_name}, {"_id": 0, "price": 1, "quantity": 1})

            if not item_data:
                continue 
            
            available_stock = int(item_data.get("quantity", 0))  # Get available stock
            sale_price = float(item_data.get("price", 1))

            # **Validation: Prevent ordering more than available stock**
            if quantity > available_stock:
                flash(f"❌ Cannot order more than {available_stock} for {item_name}!", "error")
                return redirect(url_for("billing_page"))

            if quantity > 0:
                total = quantity * sale_price
                total_amount += total

                items.append({
                    "product_name": item_name,
                    "quantity": quantity,
                    "sale_price": sale_price,
                    "total": total
                })

        bill_number = f"BILL-{random.randint(1000, 9999)}"
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bill_data = {
            "bill_no": bill_number,
            "bill_date": bill_date,
            "customer_name": customer_name,
            "mobile_number": mobile_number,
            "items": items,
            "total_amount": total_amount
        }

        # Add this after bill_data is created:
        for item in items:
            sales_history.update_one(
                {"date": datetime.now().strftime("%Y-%m-%d"), "product_name": item["product_name"]},
                {"$inc": {"quantity_sold": item["quantity"]}},
                upsert=True
            )

        # **Update stock after billing**
        for item in items:
            inward_info.update_one(
                {"product_name": item["product_name"]},
                {"$inc": {"quantity": -item["quantity"]}}  # Reduce stock
            )

        bill_collection_data.insert_one(bill_data)
        return render_template("bill_template.html", bill_data=bill_data)

    stock_items = list(inward_info.find({}, {"_id": 0, "product_name": 1, "price": 1, "quantity": 1}))


    return render_template("billing.html", stock_items=stock_items)

# Logout Route
@app.route('/logout')
def logout():
    SESSION.logout()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

# Error Handler
@app.errorhandler(404)
def not_found(error):
    return make_response(render_template('404.html'), 404)

@app.errorhandler(505)
def http_version_not_supported(error):
    return make_response(render_template('505.html'), 505)

if __name__ == "__main__":
    app.run(debug=True)
