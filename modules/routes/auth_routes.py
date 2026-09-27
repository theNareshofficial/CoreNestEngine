# modules/routes/auth_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from modules.auth.session import SESSION
from db.database import (
    get_user_by_username,
    create_user,
    log_event
)

auth_bp = Blueprint('auth', __name__)


def get_user_info():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1")
    if "," in user_ip:
        user_ip = user_ip.split(",")[0].strip()
    user_agent = str(request.user_agent) if request.user_agent else "Unknown"
    return user_ip, user_agent


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        number = request.form.get("number", "").strip()

        if not username:
            flash("Username is required!", "error")
            return redirect(url_for("auth.register"))

        if not password:
            flash("Password is required!", "error")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("auth.register"))

        if get_user_by_username(username):
            flash("Username already exists! Please choose another.", "error")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)
        user_ip, user_browser = get_user_info()

        create_user(
            username=username,
            hashed_password=hashed_password,
            number=number,
            ip_address=user_ip,
            browser=user_browser
        )

        log_event(
            user=username,
            action="register",
            details={"ip": user_ip, "browser": user_browser}
        )

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if SESSION.is_logged_in():
        return redirect(url_for("core.home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_username(username)
        if user and check_password_hash(user["password"], password):
            SESSION.login(user["username"])
            flash(f"Welcome back, {user['username']}!", "success")

            user_ip, _ = get_user_info()
            log_event(
                user=user["username"],
                action="login",
                details={"ip": user_ip}
            )

            return redirect(url_for("core.home"))
        else:
            flash("Invalid username or password!", "error")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    user = SESSION.get_current_user()
    if user:
        log_event(
            user=user,
            action="logout"
        )

    SESSION.logout()
    flash("Logged out successfully!", "info")
    return redirect(url_for("auth.login"))
