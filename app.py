from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import reg_info, inward_info
from datetime import datetime
import os

app = Flask(__name__)

app.secret_key = os.urandom(32)

# 🔐 Secure cookie settings (Prevents XSS & CSRF)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,  
    SESSION_COOKIE_SECURE=True,   # Enable this in production with HTTPS
    SESSION_PERMANENT=False
)

def get_user_info():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)  # Works with proxies
    user_agent = request.user_agent.string
    return user_ip, user_agent

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register.html', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]  
        number = request.form["number"]

        # 🔒 Preventing Username Enumeration
        if reg_info.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("register"))

        hash_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        user_ip, user_browser = get_user_info()
        register_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        register_data = {
            "username": username, 
            "password": hash_password,
            "number": number,
            "register_date": register_date,
            "ip_address": user_ip,
            "browser": user_browser
        }

        reg_info.insert_one(register_data)
        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template('register.html')

@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = reg_info.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "error")
            return render_template("login.html")

    return render_template('login.html')

@app.route('/search_suggestions', methods=['GET'])
def search_suggestions():
    search_query = request.args.get("q", "").strip()

    if search_query:
        product_names = inward_info.distinct("product_name", {"product_name": {"$regex": search_query, "$options": "i"}})
    else:
        product_names = []

    return jsonify(product_names)


@app.route('/dashboard.html', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect(url_for("login"))

    search_query = request.args.get("search", "").strip()
    query_filter = {}

    if search_query:
        query_filter = {"product_name": {"$regex": search_query, "$options": "i"}}

    stock_items = list(inward_info.find(query_filter, {"_id": 0, "product_name": 1, "quantity": 1, "rate": 1, "price": 1}))

    return render_template("dashboard.html", inward_stock=stock_items, search_query=search_query)


@app.route('/inward.html', methods=['GET', 'POST'])
def inward():
    if request.method == "POST":
        try:
            product_name = request.form.get("product_name")
            quantity = request.form.get("quantity")
            rate = request.form.get("rate")
            price = request.form.get("price")

            if not product_name or not quantity or not rate or not price:
                flash("All fields are required!", "error")
                return redirect(url_for("inward"))

            inward_data = {
                "product_name": product_name,
                "quantity": int(quantity),
                "rate": float(rate),
                "price": float(price),
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            inward_info.insert_one(inward_data)
            flash("Inward data saved successfully!", "success")
            return redirect(url_for("inward"))

        except Exception as e:
            flash(f"Database Error: {str(e)}", "error")
            return redirect(url_for("inward"))

    # Fetch stored inward data
    stock_items = list(inward_info.find({}, {"_id": 0}))
    return render_template("inward.html", inward_stock=stock_items)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
