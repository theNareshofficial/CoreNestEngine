from flask import session, redirect, url_for, flash
from datetime import datetime, timedelta

class SESSION:
    @staticmethod
    def login_required(func):
        """Decorator to protect routes and ensure user is logged in."""
        def wrapper(*args, **kwargs):
            if not session.get("user"):
                flash("You need to log in first!", "error")
                return redirect(url_for("auth.login"))
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper

    @staticmethod
    def login(user):
        """Sets session variables upon login."""
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
        return session.get("user") is not None

    @staticmethod
    def check_session_timeout():
        last_active = session.get("last_active")
        if last_active:
            last_active_time = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_active_time > timedelta(minutes=10):
                SESSION.logout()
                print("Session expired! Please log in again.")
                flash("Session expired! Please log in again.", "error")
                return redirect(url_for("auth.login"))
        session["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
