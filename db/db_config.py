# db/db_config.py
"""
Database configuration and export module.
Now powered by SQLite (built-in, zero external server dependencies).
"""

from db.database import (
    get_db,
    init_db,
    close_db,
    get_user_by_username,
    create_user,
    get_all_users,
    log_event,
    get_activity_logs,
    get_deleted_logs,
    get_logs_for_product,
    get_inventory,
    get_inventory_item,
    get_inventory_item_by_name,
    add_inward_stock,
    update_inventory_stock,
    get_available_stock,
    create_bill,
    get_bill,
    get_recent_bills,
    update_bill,
    get_sales_stats,
    get_sales_by_product,
    get_daily_sales_history,
    seed_sample_data,
    get_inward_history,
    get_inward_suggestions,
    get_billing_history
)

__all__ = [
    "get_db",
    "init_db",
    "close_db",
    "get_user_by_username",
    "create_user",
    "get_all_users",
    "log_event",
    "get_activity_logs",
    "get_deleted_logs",
    "get_logs_for_product",
    "get_inventory",
    "get_inventory_item",
    "get_inventory_item_by_name",
    "add_inward_stock",
    "get_inward_history",
    "get_inward_suggestions",
    "update_inventory_stock",
    "get_available_stock",
    "create_bill",
    "get_bill",
    "get_recent_bills",
    "update_bill",
    "get_sales_stats",
    "get_sales_by_product",
    "get_daily_sales_history",
    "seed_sample_data",
    "get_billing_history"
]
