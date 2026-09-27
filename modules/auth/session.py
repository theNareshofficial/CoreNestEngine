from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime, timedelta

SESSION_TIMEOUT_MINUTES = 60


class SESSION:
    @staticmethod
    def login_required(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not SESSION.is_logged_in():
                flash("You need to log in first!", "error")
                return redirect(url_for("auth.login"))

            if SESSION.is_expired():
                SESSION.logout()
                flash("Session expired! Please log in again.", "warning")
                return redirect(url_for("auth.login"))

            SESSION.refresh_activity()
            return func(*args, **kwargs)
        return wrapper

    @staticmethod
    def login(user):
        
        session["user"] = user
        session["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_current_user():
        return session.get("user")

    @staticmethod
    def logout():
        session.clear()

    @staticmethod
    def is_logged_in():
        return bool(session.get("user"))

    @staticmethod
    def is_expired(timeout_minutes=SESSION_TIMEOUT_MINUTES):
        last_active = session.get("last_active")
        if last_active:
            try:
                last_active_time = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_active_time > timedelta(minutes=timeout_minutes):
                    return True
            except (ValueError, TypeError):
                return False
        return False

    @staticmethod
    def refresh_activity():
        if SESSION.is_logged_in():
            session["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def check_session_timeout():
        if SESSION.is_expired():
            SESSION.logout()
            flash("Session expired! Please log in again.", "warning")
            return redirect(url_for("auth.login"))
        SESSION.refresh_activity()
        return None
