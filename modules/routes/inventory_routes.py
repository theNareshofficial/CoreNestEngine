# modules/routes/inventory_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from modules.auth.session import SESSION
from db.db_config import inward_info, logs
from datetime import datetime
from bson.objectid import ObjectId

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/dashboard', methods=['GET'])
@SESSION.login_required
def dashboard():
    SESSION.check_session_timeout()
    search_query = request.args.get('search', '')

    query = {}
    if search_query:
        query = {"product_name": {"$regex": search_query, "$options": "i"}}
    
    stock_items = list(inward_info.find(query))
    for item in stock_items:
        item['_id'] = str(item['_id'])
        
    return render_template("dashboard.html", inward_stock=stock_items, search_query=search_query)


@inventory_bp.route('/inward', methods=['GET', 'POST'])
@SESSION.login_required
def inward():
    SESSION.check_session_timeout()
    if request.method == "POST":
        
        inward_data = {
            "product_name": request.form.get("product_name", "").strip().capitalize(),
            "dealer": request.form.get("dealer", "").strip().capitalize(),
            "quantity": int(request.form.get("quantity", "0").strip()),
            "rate": float(request.form.get("rate", "0").strip()),
            "price": float(request.form.get("price", "0").strip()),
            "user": SESSION.get_current_user(),
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        inward_info.insert_one(inward_data)
        flash("Inward stock added successfully!", "success")
        return redirect(url_for("inventory.inward"))

    stock_items = list(inward_info.find())
    return render_template("inward.html", inward_stock=stock_items)

def log_stock_change(user, product_id, product_name, action, quantity):

    logs.insert_one({
        "dealer": dealer,
        "user": user,
        "product_id": ObjectId(product_id),
        "product_name": product_name,
        "action": action,
        "quantity": quantity,
        "timestamp": datetime.now(),
    })

@inventory_bp.route('/update_stock/<item_id>', methods=['POST'])
@SESSION.login_required
def update_stock(item_id):
    user = SESSION.get_current_user()
    data = request.get_json()
    
    try:
        # Positive quantity for adding, negative for deleting
        quantity_change = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid quantity!"}), 400

    if quantity_change == 0:
        return jsonify({"status": "error", "message": "Quantity cannot be zero."}), 400

    item = inward_info.find_one({"_id": ObjectId(item_id)})
    if not item:
        return jsonify({"status": "error", "message": "Item not found."}), 404

    current_quantity = item.get("quantity", 0)


    if quantity_change < 0 and abs(quantity_change) > current_quantity:
        return jsonify({"status": "error", "message": f"Cannot remove {abs(quantity_change)}. Only {current_quantity} available."}), 400

    # Update stock
    inward_info.update_one({"_id": ObjectId(item_id)}, {"$inc": {"quantity": quantity_change}})
    
    # Log the action
    action = "added" if quantity_change > 0 else "deleted"
    log_stock_change(user, item_id, item['product_name'], action, abs(quantity_change))
    
    message = f"✅ {abs(quantity_change)} stock {'added to' if action == 'added' else 'removed from'} '{item['product_name']}'."
    return jsonify({"status": "success", "message": message})


@inventory_bp.route("/view_logs/<item_id>")
@SESSION.login_required
def view_logs(item_id):
    product_logs = list(logs.find({"product_id": ObjectId(item_id)}).sort("timestamp", -1))

    for log in product_logs:
        log['_id'] = str(log['_id'])
        log['product_id'] = str(log['product_id'])
        log['timestamp'] = log['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        
    return jsonify({"status": "success", "logs": product_logs})