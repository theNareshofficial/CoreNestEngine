# modules/routes/core_routes.py
from flask import Blueprint, render_template, redirect, url_for
from modules.auth.session import SESSION
from db.db_config import sales_history, reg_info, logs
from datetime import datetime, time, timedelta
from pymongo import DESCENDING

core_bp = Blueprint('core', __name__)

@core_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@core_bp.route('/home')
@SESSION.login_required
def home():
    SESSION.check_session_timeout()

    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    today_end = datetime.combine(now.date(), time.max)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    def get_sales_stats(start_date, end_date):
        pipeline = [
            {"$match": {"bill_date": {"$gte": start_date, "$lte": end_date}}},
            {"$unwind": "$items"},
            {"$group": {
                "_id": None,
                "total_sales": {"$sum": "$items.total"},
                "total_items": {"$sum": "$items.quantity"}
            }}
        ]
        result = list(sales_history.aggregate(pipeline))
        return result[0] if result else {"total_sales": 0, "total_items": 0}

    daily_stats = get_sales_stats(today_start, today_end)
    weekly_stats = get_sales_stats(week_start, today_end)
    monthly_stats = get_sales_stats(month_start, today_end)
    
    daily_sales_pipeline = [
        {"$match": {"bill_date": {"$gte": today_start, "$lte": today_end}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_name",
            "quantity_sold": {"$sum": "$items.quantity"}
        }},
        {"$project": {"product_name": "$_id", "quantity_sold": 1, "_id": 0}}
    ]
    daily_sales = list(sales_history.aggregate(daily_sales_pipeline))

    weekly_sales_chart_data = list(sales_history.aggregate([
        {"$match": {"bill_date": {"$gte": week_start, "$lte": today_end}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.product_name",
            "quantity_sold": {"$sum": "$items.quantity"}
        }},
        {"$project": {"product_name": "$_id", "quantity_sold": 1, "_id": 0}}
    ]))
    
    return render_template(
        "home.html",
        daily_total=f"₹{daily_stats['total_sales']:.2f}",
        weekly_total=f"₹{weekly_stats['total_sales']:.2f}",
        monthly_total=f"₹{monthly_stats['total_sales']:.2f}",
        daily_items_sold=daily_stats['total_items'],
        weekly_items_sold=weekly_stats['total_items'],
        monthly_items_sold=monthly_stats['total_items'],
        daily_sales=daily_sales,
        weekly_sales=weekly_sales_chart_data
    )

@core_bp.route('/user_accounts')
@SESSION.login_required
def user_accounts():
    """Displays a list of all user accounts."""
    SESSION.check_session_timeout()
    users = list(reg_info.find({}, {"username": 1, "number": 1, "_id": 0}))
    return render_template("user_accounts.html", user_accounts=users)

@core_bp.route('/activity_log')
@SESSION.login_required
def activity_log():
    """Displays a log of user logins and logouts."""
    SESSION.check_session_timeout()
    logs_data = list(logs.find(
        {"action": {"$in": ["login", "logout"]}}
    ).sort("timestamp", DESCENDING).limit(100))
    return render_template("activity_log.html", activity_logs=logs_data)

@core_bp.route('/daily_sales')
@SESSION.login_required
def daily_sales():
    """Displays a report of total sales for each day."""
    SESSION.check_session_timeout()
    pipeline = [
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$bill_date"}},
                "total_sales": {"$sum": "$total_amount"}
            }
        },
        {"$sort": {"_id": -1}}
    ]
    sales_data = list(sales_history.aggregate(pipeline))
    return render_template("daily_sales.html", daily_sales=sales_data)