from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from datetime import datetime
import json
from modules.auth.session import SESSION
from db.database import (
    get_inventory,
    get_inventory_item,
    add_inward_stock,
    get_inward_history,
    get_inward_suggestions,
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

        # ERP Fields
        category = request.form.get("category", "").strip()
        models_raw = request.form.get("models", "").strip()
        models_list = request.form.getlist("models[]")
        free_quantity = request.form.get("free_quantity", "").strip()
        invoice_no = request.form.get("invoice_no", "").strip()
        tax_rate = request.form.get("tax_rate", "").strip()
        rack_number = request.form.get("rack_number", "").strip()
        client_timestamp = request.form.get("timestamp", "").strip()

        # Dynamic Pricing Fields
        margin_rate = request.form.get("margin_rate", "").strip()
        landed_cost_str = request.form.get("landed_cost", "0").strip()
        calc_mode = request.form.get("calc_mode", "auto").strip()
        pack_size = request.form.get("pack_size", "").strip()

        # Parse models
        parsed_models = []
        if models_list:
            parsed_models = [m.strip() for m in models_list if m.strip()]
        elif models_raw:
            try:
                parsed = json.loads(models_raw)
                if isinstance(parsed, list):
                    parsed_models = [str(m).strip() for m in parsed if str(m).strip()]
                else:
                    parsed_models = [str(models_raw).strip()]
            except Exception:
                parsed_models = [m.strip() for m in models_raw.split(",") if m.strip()]

        # Validations for Required Fields
        if not product_name:
            flash("Product Name is required!", "error")
            return redirect(url_for("inventory.inward"))

        if not parsed_models:
            flash("At least one Product Model tag is required!", "error")
            return redirect(url_for("inventory.inward"))

        if not dealer:
            flash("Dealer / Supplier is required!", "error")
            return redirect(url_for("inventory.inward"))

        if not category:
            flash("Category & Sub-Category is required!", "error")
            return redirect(url_for("inventory.inward"))

        try:
            quantity = int(quantity_str)
            rate = float(rate_str)
            price = float(price_str)
        except ValueError:
            flash("Invalid quantity, rate, or price! Please enter valid numbers.", "error")
            return redirect(url_for("inventory.inward"))

        if quantity < 1:
            flash("Quantity must be at least 1.", "error")
            return redirect(url_for("inventory.inward"))

        if rate < 0 or price < 0:
            flash("Purchase Rate and Sale Price cannot be negative.", "error")
            return redirect(url_for("inventory.inward"))

        # Parse landed_cost as float
        try:
            landed_cost = float(landed_cost_str)
        except (ValueError, TypeError):
            landed_cost = 0.0

        # Default optional fields to 'NA' if empty
        free_quantity_val = free_quantity if free_quantity else "NA"
        invoice_no_val = invoice_no if invoice_no else "NA"
        tax_rate_val = tax_rate if tax_rate else "NA"
        rack_number_val = rack_number if rack_number else "NA"
        margin_rate_val = margin_rate if margin_rate else "NA"
        pack_size_val = pack_size if pack_size else "NA"
        calc_mode_val = calc_mode if calc_mode in ("auto", "manual") else "auto"

        # System-managed timestamp formatted as DD-MM-YYYY hh:mm:ss AM/PM
        now = datetime.now()
        timestamp_str = now.strftime('%d-%m-%Y %I:%M:%S %p')
        user = SESSION.get_current_user() or "System"

        add_inward_stock(
            product_name=product_name,
            dealer=dealer,
            quantity=quantity,
            rate=rate,
            price=price,
            user=user,
            models=parsed_models,
            category=category,
            free_quantity=free_quantity_val,
            invoice_no=invoice_no_val,
            tax_rate=tax_rate_val,
            rack_number=rack_number_val,
            timestamp_str=timestamp_str,
            margin_rate=margin_rate_val,
            landed_cost=landed_cost,
            calc_mode=calc_mode_val,
            pack_size=pack_size_val
        )

        flash(f"Inward Inventory Entry for '{product_name}' ({quantity} units) saved successfully!", "success")
        return redirect(url_for("inventory.inward"))

    suggestions = get_inward_suggestions()
    inward_history = get_inward_history(limit=50)
    current_user = SESSION.get_current_user() or "admin"

    return render_template(
        "inward.html",
        inward_stock=inward_history,
        suggestions=suggestions,
        current_user=current_user
    )


@inventory_bp.route('/api/inward/suggestions', methods=['GET'])
@SESSION.login_required
def api_inward_suggestions():
    return jsonify(get_inward_suggestions())


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
