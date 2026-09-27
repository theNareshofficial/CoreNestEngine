# modules/routes/core_routes.py
import sys
import subprocess
from datetime import datetime, time, timedelta
from flask import Blueprint, render_template, redirect, url_for
from modules.auth.session import SESSION
from db.database import (
    get_all_users,
    get_activity_logs,
    get_deleted_logs,
    get_sales_stats,
    get_sales_by_product,
    get_daily_sales_history
)

core_bp = Blueprint("core", __name__)


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

    return render_template(
        "home.html",
        daily_total=f"₹{daily_stats['total_sales']:.2f}",
        weekly_total=f"₹{weekly_stats['total_sales']:.2f}",
        monthly_total=f"₹{monthly_stats['total_sales']:.2f}",
        daily_items_sold=daily_stats["total_items"],
        weekly_items_sold=weekly_stats["total_items"],
        monthly_items_sold=monthly_stats["total_items"],
        daily_sales=daily_sales,
        weekly_sales=weekly_sales_chart_data
    )


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
