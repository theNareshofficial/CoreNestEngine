# modules/routes/inventory_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from modules.auth.session import SESSION
from db.database import (
    get_inventory,
    get_inventory_item,
    add_inward_stock,
    update_inventory_stock,
    get_logs_for_product
)

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/dashboard', methods=['GET'])
@SESSION.login_required
def dashboard():
    search_query = request.args.get('search', '').strip()
    stock_items = get_inventory(search_query=search_query if search_query else None)
    return render_template("dashboard.html", inward_stock=stock_items, search_query=search_query)


@inventory_bp.route('/inward', methods=['GET', 'POST'])
@SESSION.login_required
def inward():
    if request.method == "POST":
        product_name = request.form.get("product_name", "").strip()
        dealer = request.form.get("dealer", "").strip()
        quantity_str = request.form.get("quantity", "0").strip()
        rate_str = request.form.get("rate", "0").strip()
        price_str = request.form.get("price", "0").strip()

        if not product_name:
            flash("Product name cannot be empty!", "error")
            return redirect(url_for("inventory.inward"))

        try:
            quantity = int(quantity_str)
            rate = float(rate_str)
            price = float(price_str)
        except ValueError:
            flash("Invalid quantity, rate, or price! Please enter valid numbers.", "error")
            return redirect(url_for("inventory.inward"))

        if quantity <= 0:
            flash("Quantity must be greater than zero.", "error")
            return redirect(url_for("inventory.inward"))

        if rate < 0 or price < 0:
            flash("Rate and Price cannot be negative.", "error")
            return redirect(url_for("inventory.inward"))

        user = SESSION.get_current_user() or "System"
        add_inward_stock(
            product_name=product_name,
            dealer=dealer,
            quantity=quantity,
            rate=rate,
            price=price,
            user=user
        )

        flash(f"Inward stock for '{product_name}' ({quantity} units) added successfully!", "success")
        return redirect(url_for("inventory.inward"))

    stock_items = get_inventory()
    return render_template("inward.html", inward_stock=stock_items)


@inventory_bp.route('/update_stock/<item_id>', methods=['POST'])
@SESSION.login_required
def update_stock(item_id):
    user = SESSION.get_current_user() or "System"
    data = request.get_json(silent=True) or {}

    try:
        quantity_change = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid quantity provided!"}), 400

    if quantity_change == 0:
        return jsonify({"status": "error", "message": "Quantity cannot be zero."}), 400

    try:
        int_item_id = int(item_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid item ID format."}), 400

    success, message = update_inventory_stock(int_item_id, quantity_change, user)
    if not success:
        return jsonify({"status": "error", "message": message}), 400

    return jsonify({"status": "success", "message": f"✅ {message}"})


@inventory_bp.route("/view_logs/<item_id>")
@SESSION.login_required
def view_logs(item_id):
    try:
        int_item_id = int(item_id)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid item ID", "logs": []}), 400

    product_logs = get_logs_for_product(int_item_id)
    return jsonify({"status": "success", "logs": product_logs})
