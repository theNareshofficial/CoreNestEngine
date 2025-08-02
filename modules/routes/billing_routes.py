# modules/routes/billing_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from modules.auth.session import SESSION
from db.db_config import inward_info, bill_collection_data, sales_history, logs
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import DESCENDING
from io import BytesIO
from xhtml2pdf import pisa
import random

billing_bp = Blueprint('billing', __name__)

@billing_bp.route("/billing", methods=['GET', 'POST'])
@SESSION.login_required
def billing_page():
    SESSION.check_session_timeout()
    if request.method == 'POST':
        # ... (rest of your billing creation logic is correct)
        customer_name = request.form.get("customer_name", "").strip().capitalize()
        items_to_bill = []
        total_amount = 0
        for key, quantity_str in request.form.items():
            if key.startswith("quantity_"):
                product_name = key.replace("quantity_", "")
                quantity = int(quantity_str)
                if quantity > 0:
                    item_data = inward_info.find_one({"product_name": product_name})
                    if not item_data or quantity > item_data.get("quantity", 0):
                        flash(f"Not enough stock for {product_name}!", "error")
                        return redirect(url_for("billing.billing_page"))
                    total = quantity * item_data.get("price", 0)
                    total_amount += total
                    items_to_bill.append({
                        "product_name": product_name,
                        "quantity": quantity,
                        "sale_price": item_data.get("price", 0),
                        "total": total
                    })
        if not items_to_bill:
            flash("No items selected for billing.", "error")
            return redirect(url_for("billing.billing_page"))
        bill_number = f"BILL-{random.randint(1000, 9999)}"
        bill_data = {
            "user": SESSION.get_current_user(),
            "bill_no": bill_number,
            "bill_date": datetime.now(),
            "customer_name": customer_name,
            "mobile_number": request.form.get("mobile_number", "").strip(),
            "items": items_to_bill,
            "total_amount": total_amount
        }
        bill_collection_data.insert_one(bill_data)
        sales_history.insert_one(bill_data)
        for item in items_to_bill:
            inward_info.update_one(
                {"product_name": item["product_name"]},
                {"$inc": {"quantity": -item["quantity"]}}
            )
        return render_template("bill_template.html", bill_data=bill_data)

    stock_items = list(inward_info.find({"quantity": {"$gt": 0}}))
    return render_template("billing.html", stock_items=stock_items)


@billing_bp.route("/bill_detail", methods=["GET"])
@SESSION.login_required
def bill_detail():
    SESSION.check_session_timeout()
    bill_no = request.args.get("bill_no", "").strip().upper()
    bill_data = None

    if bill_no:
        bill_data = bill_collection_data.find_one({"bill_no": bill_no})

    recent_bills = list(
        bill_collection_data.find({}).sort("bill_date", DESCENDING).limit(25)
    )

    # Prepare safe dates for the template
    for bill in recent_bills:
        bill_date = bill.get('bill_date')
        if isinstance(bill_date, datetime):
            bill['formatted_date'] = bill_date.strftime('%d-%b-%Y')
        else:
            bill['formatted_date'] = bill_date

    if bill_data:
        bill_date = bill_data.get('bill_date')
        if isinstance(bill_date, datetime):
            bill_data['formatted_date'] = bill_date.strftime('%d-%b-%Y %I:%M %p')
        else:
            bill_data['formatted_date'] = bill_date

    return render_template(
        "bill_detail.html",
        bill_data=bill_data,
        recent_bills=recent_bills,
        bill_no=bill_no
    )

@billing_bp.route("/edit_bill/<bill_no>", methods=["GET"])
@SESSION.login_required
def edit_bill(bill_no):
    """Displays the form to edit an existing bill."""
    SESSION.check_session_timeout()
    
    bill_data = bill_collection_data.find_one({"bill_no": bill_no})
    if not bill_data:
        flash(f"No bill found with number {bill_no}", "error")
        return redirect(url_for('billing.bill_detail'))

    return render_template("edit_bill.html", bill_data=bill_data)


@billing_bp.route("/update_bill/<bill_no>", methods=["POST"])
@SESSION.login_required
def update_bill(bill_no):
    """Processes the form submission from the edit_bill page."""
    SESSION.check_session_timeout()

    old_bill = bill_collection_data.find_one({"bill_no": bill_no})
    if not old_bill:
        flash("Bill not found!", "danger")
        return redirect(url_for("billing.edit_bill", bill_no=bill_no))
    
    # --- Part 1: Calculate stock changes (Your existing logic is good) ---
    old_items_map = {item["product_name"]: item["quantity"] for item in old_bill.get("items", [])}
    product_names = request.form.getlist("product_name[]")
    quantities = request.form.getlist("quantity[]")
    sale_prices = request.form.getlist("sale_price[]")
    
    new_items = []
    new_total_amount = 0

    for i in range(len(product_names)):
        product_name = product_names[i]
        new_qty = int(quantities[i])
        sale_price = float(sale_prices[i])
        
        new_items.append({
            "product_name": product_name,
            "quantity": new_qty,
            "sale_price": sale_price,
            "total": new_qty * sale_price
        })
        new_total_amount += (new_qty * sale_price)

        old_qty = old_items_map.get(product_name, 0)
        stock_change = old_qty - new_qty
        inward_info.update_one({"product_name": product_name}, {"$inc": {"quantity": stock_change}})

    removed_products = set(old_items_map.keys()) - set(product_names)
    for product_name in removed_products:
        old_qty = old_items_map[product_name]
        inward_info.update_one({"product_name": product_name}, {"$inc": {"quantity": old_qty}})
    
    # --- Part 2: Prepare the final update data ---
    update_data = {
        "items": new_items, 
        "total_amount": new_total_amount, 
        "last_edited": datetime.now()
    }

    # --- Part 3: Update BOTH collections with the same data ---
    # Update the main bill record
    bill_collection_data.update_one({"bill_no": bill_no}, {"$set": update_data})
    
    # ALSO, update the corresponding record in sales_history
    sales_history.update_one({"bill_no": bill_no}, {"$set": update_data})

    flash("Bill and sales history updated successfully!", "success")
    return redirect(url_for("billing.bill_detail", bill_no=bill_no))

@billing_bp.route("/generate_pdf/<bill_no>")
@SESSION.login_required
def generate_pdf(bill_no):
    """Generates and serves a PDF for a given bill number."""
    SESSION.check_session_timeout()

    bill_data = bill_collection_data.find_one({"bill_no": bill_no})
    if not bill_data:
        flash(f"Bill {bill_no} not found.", "error")
        return redirect(url_for('billing.bill_detail'))

    # FIX: Prepare a safe, pre-formatted date string for the template
    bill_date = bill_data.get('bill_date')
    if isinstance(bill_date, datetime):
        bill_data['formatted_date'] = bill_date.strftime('%B %d, %Y, %I:%M %p')
    else:
        # If it's already a string, just use it
        bill_data['formatted_date'] = bill_date

    rendered_html = render_template("bill_pdf_template.html", bill_data=bill_data)
    
    # ... (rest of your PDF generation code)
    pdf_result = BytesIO()
    pisa_status = pisa.CreatePDF(
        src=BytesIO(rendered_html.encode("UTF-8")),
        dest=pdf_result
    )

    if pisa_status.err:
        return "Error creating PDF", 500

    pdf_result.seek(0)
    response = make_response(pdf_result.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=bill_{bill_no}.pdf'
    
    return response