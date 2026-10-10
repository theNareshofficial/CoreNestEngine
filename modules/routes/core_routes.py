# modules/routes/core_routes.py
import sys
import subprocess
from datetime import datetime, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from modules.auth.session import SESSION
from db.database import (
    get_all_users,
    get_activity_logs,
    get_deleted_logs,
    get_sales_stats,
    get_sales_by_product,
    get_daily_sales_history,
    get_billing_history
)

core_bp = Blueprint("core", __name__)


def resolve_filter_range(filter_type, start_date_str=None, end_date_str=None):
    """Calculates start_date, end_date and human label for Billing History filters."""
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)
    
    filter_type = (filter_type or "daily").lower().strip()
    
    if filter_type == "daily":
        start_date = today_start
        end_date = today_end
        label = f"Daily ({now.strftime('%d %b %Y')})"
    elif filter_type == "weekly":
        start_date = today_start - timedelta(days=6)
        end_date = today_end
        label = f"Weekly ({start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')})"
    elif filter_type == "monthly":
        start_date = today_start.replace(day=1)
        end_date = today_end
        label = f"Monthly ({now.strftime('%B %Y')})"
    elif filter_type == "custom":
        if start_date_str and end_date_str:
            try:
                s_dt = datetime.strptime(start_date_str.strip(), "%Y-%m-%d")
                e_dt = datetime.strptime(end_date_str.strip(), "%Y-%m-%d")
                start_date = datetime.combine(s_dt.date(), time.min)
                end_date = datetime.combine(e_dt.date(), time.max)
                label = f"Custom ({s_dt.strftime('%d %b %Y')} - {e_dt.strftime('%d %b %Y')})"
            except ValueError:
                start_date = today_start
                end_date = today_end
                filter_type = "daily"
                label = f"Daily ({now.strftime('%d %b %Y')})"
        else:
            start_date = today_start
            end_date = today_end
            filter_type = "daily"
            label = f"Daily ({now.strftime('%d %b %Y')})"
    else:
        filter_type = "daily"
        start_date = today_start
        end_date = today_end
        label = f"Daily ({now.strftime('%d %b %Y')})"

    return filter_type, start_date, end_date, label


@core_bp.route("/")
def index():
    if SESSION.is_logged_in():
        return redirect(url_for("core.home"))
    return redirect(url_for("auth.login"))


@core_bp.route("/home")
@SESSION.login_required
def home():
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    daily_stats = get_sales_stats(today_start, today_end)
    weekly_stats = get_sales_stats(week_start, today_end)
    monthly_stats = get_sales_stats(month_start, today_end)

    daily_sales = get_sales_by_product(today_start, today_end)
    weekly_sales_chart_data = get_sales_by_product(week_start, today_end)

    # Billing History Filters
    req_filter = request.args.get("filter", "daily")
    start_date_param = request.args.get("start_date", "")
    end_date_param = request.args.get("end_date", "")

    active_filter, hist_start, hist_end, filter_label = resolve_filter_range(
        req_filter, start_date_param, end_date_param
    )
    history_data = get_billing_history(hist_start, hist_end)

    return render_template(
        "home.html",
        daily_total=f"₹{daily_stats['total_sales']:.2f}",
        weekly_total=f"₹{weekly_stats['total_sales']:.2f}",
        monthly_total=f"₹{monthly_stats['total_sales']:.2f}",
        daily_items_sold=daily_stats["total_items"],
        weekly_items_sold=weekly_stats["total_items"],
        monthly_items_sold=monthly_stats["total_items"],
        daily_sales=daily_sales,
        weekly_sales=weekly_sales_chart_data,
        billing_history=history_data["bills"],
        billing_total_sales=f"₹{history_data['total_sales']:,.2f}",
        billing_total_sales_raw=history_data["total_sales"],
        billing_total_bills=history_data["total_bills"],
        billing_total_items=history_data["total_items"],
        active_filter=active_filter,
        filter_label=filter_label,
        start_date_val=hist_start.strftime("%Y-%m-%d"),
        end_date_val=hist_end.strftime("%Y-%m-%d")
    )


@core_bp.route("/api/billing_history", methods=["GET"])
@SESSION.login_required
def api_billing_history():
    req_filter = request.args.get("filter", "daily")
    start_date_param = request.args.get("start_date", "")
    end_date_param = request.args.get("end_date", "")

    active_filter, hist_start, hist_end, filter_label = resolve_filter_range(
        req_filter, start_date_param, end_date_param
    )
    history_data = get_billing_history(hist_start, hist_end)

    serialized_bills = []
    for b in history_data["bills"]:
        serialized_bills.append({
            "id": b["id"],
            "bill_no": b["bill_no"],
            "formatted_date": b["formatted_date"],
            "formatted_date_short": b["formatted_date_short"],
            "customer_name": b["customer_name"],
            "mobile_number": b["mobile_number"],
            "total_amount": b["total_amount"],
            "formatted_total_amount": f"₹{b['total_amount']:,.2f}",
            "user": b["user"],
            "is_edited": b["is_edited"],
            "formatted_last_edited": b["formatted_last_edited"],
            "total_quantity": b["total_quantity"],
            "items": b["items"]
        })

    return jsonify({
        "status": "success",
        "filter": active_filter,
        "filter_label": filter_label,
        "start_date": hist_start.strftime("%Y-%m-%d"),
        "end_date": hist_end.strftime("%Y-%m-%d"),
        "total_sales": history_data["total_sales"],
        "formatted_total_sales": f"₹{history_data['total_sales']:,.2f}",
        "total_bills": history_data["total_bills"],
        "total_items": history_data["total_items"],
        "bills": serialized_bills
    })


@core_bp.route("/user_accounts")
@SESSION.login_required
def user_accounts():
    """Displays a list of all user accounts."""
    users = get_all_users()
    return render_template("user_accounts.html", user_accounts=users)


@core_bp.route("/activity_log")
@SESSION.login_required
def activity_log():
    """Displays a log of user logins and logouts."""
    logs_data = get_activity_logs(limit=100)
    return render_template("activity_log.html", activity_logs=logs_data)


@core_bp.route("/daily_sales")
@SESSION.login_required
def daily_sales():
    """Displays a report of total sales for each day."""
    sales_data = get_daily_sales_history()
    return render_template("daily_sales.html", daily_sales=sales_data)


@core_bp.route("/deleted_log")
@SESSION.login_required
def deleted_log():
    """Displays a detailed log of all deleted stock items."""
    deleted_items = get_deleted_logs()
    return render_template("deleted_log.html", deleted_logs=deleted_items)


@core_bp.route("/update_app", methods=["POST"])
@SESSION.login_required
def update_app():
    script_path = "scripts/update.py"
    python_executable = sys.executable

    try:
        process = subprocess.run(
            [python_executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30
        )
        update_log = process.stdout
        if process.stderr:
            update_log += "\n" + process.stderr
    except Exception as e:
        update_log = f"Failed to execute update script: {str(e)}"

    return render_template("update_status.html", update_log=update_log)
