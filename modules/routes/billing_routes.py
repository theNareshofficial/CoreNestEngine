# modules/routes/billing_routes.py
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, make_response
from modules.auth.session import SESSION
from db.database import (
    get_available_stock,
    get_inventory_item_by_name,
    create_bill,
    get_bill,
    get_recent_bills,
    update_bill as db_update_bill
)

billing_bp = Blueprint('billing', __name__)


@billing_bp.route("/billing", methods=['GET', 'POST'])
@SESSION.login_required
def billing_page():
    if request.method == 'POST':
        customer_name = request.form.get("customer_name", "").strip()
        mobile_number = request.form.get("mobile_number", "").strip()
        user = SESSION.get_current_user() or "System"

        items_to_bill = []
        for key, quantity_str in request.form.items():
            if key.startswith("quantity_"):
                product_name = key.replace("quantity_", "")
                try:
                    quantity = int(quantity_str.strip())
                except ValueError:
                    continue

                if quantity > 0:
                    item_data = get_inventory_item_by_name(product_name)
                    if not item_data:
                        flash(f"Product '{product_name}' not found in inventory!", "error")
                        return redirect(url_for("billing.billing_page"))

                    if quantity > item_data.get("quantity", 0):
                        flash(f"Not enough stock for '{product_name}'! Available: {item_data.get('quantity', 0)}", "error")
                        return redirect(url_for("billing.billing_page"))

                    sale_price = float(item_data.get("price", 0.0))
                    total = quantity * sale_price
                    items_to_bill.append({
                        "product_name": product_name,
                        "quantity": quantity,
                        "sale_price": sale_price,
                        "total": total
                    })

        if not items_to_bill:
            flash("No items selected for billing. Please enter quantity for at least one item.", "error")
            return redirect(url_for("billing.billing_page"))

        try:
            bill_data = create_bill(
                customer_name=customer_name,
                mobile_number=mobile_number,
                items=items_to_bill,
                user=user
            )
            flash(f"Bill #{bill_data['bill_no']} created successfully!", "success")
            return render_template("bill_template.html", bill_data=bill_data)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("billing.billing_page"))

    stock_items = get_available_stock()
    return render_template("billing.html", stock_items=stock_items)


@billing_bp.route("/bill_detail", methods=["GET"])
@SESSION.login_required
def bill_detail():
    bill_no = request.args.get("bill_no", "").strip().upper()
    bill_data = None

    if bill_no:
        bill_data = get_bill(bill_no)

    recent_bills = get_recent_bills(limit=25)

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
    bill_data = get_bill(bill_no)
    if not bill_data:
        flash(f"No bill found with number '{bill_no}'.", "error")
        return redirect(url_for('billing.bill_detail'))

    return render_template("edit_bill.html", bill_data=bill_data)


@billing_bp.route("/update_bill/<bill_no>", methods=["POST"])
@SESSION.login_required
def update_bill(bill_no):
    """Processes the form submission from the edit_bill page."""
    user = SESSION.get_current_user() or "System"

    product_names = request.form.getlist("product_name[]")
    quantities = request.form.getlist("quantity[]")
    sale_prices = request.form.getlist("sale_price[]")

    if not product_names:
        flash("A bill must contain at least one item.", "error")
        return redirect(url_for("billing.edit_bill", bill_no=bill_no))

    new_items = []
    for i in range(len(product_names)):
        p_name = product_names[i].strip()
        try:
            qty = int(quantities[i])
            price = float(sale_prices[i])
        except (ValueError, IndexError):
            flash("Invalid quantity or price entered in the bill items!", "error")
            return redirect(url_for("billing.edit_bill", bill_no=bill_no))

        if qty <= 0:
            flash(f"Quantity for '{p_name}' must be greater than zero.", "error")
            return redirect(url_for("billing.edit_bill", bill_no=bill_no))

        new_items.append({
            "product_name": p_name,
            "quantity": qty,
            "sale_price": price,
            "total": qty * price
        })

    success, message = db_update_bill(bill_no, new_items, user)
    if not success:
        flash(message, "error")
        return redirect(url_for("billing.edit_bill", bill_no=bill_no))

    flash("Bill and stock records updated successfully!", "success")
    return redirect(url_for("billing.bill_detail", bill_no=bill_no))


@billing_bp.route("/generate_pdf/<bill_no>")
@SESSION.login_required
def generate_pdf(bill_no):
    """Generates and serves a PDF for a given bill number using WeasyPrint."""
    bill_data = get_bill(bill_no)
    if not bill_data:
        flash(f"Bill '{bill_no}' not found.", "error")
        return redirect(url_for('billing.bill_detail'))

    rendered_html = render_template("bill_pdf_template.html", bill_data=bill_data)

    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=bill_{bill_no}.pdf'
        return response
    except Exception as e:
        flash(f"Failed to generate PDF: {str(e)}", "error")
        return redirect(url_for("billing.bill_detail", bill_no=bill_no))
