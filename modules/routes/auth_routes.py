from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db.db_config import reg_info, logs
from modules.auth.session import SESSION
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

def get_user_info():
    user_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.user_agent.string
    return user_ip, user_agent

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        number = request.form["number"]

        if reg_info.find_one({"username": username}):
            flash("Username already exists!", "error")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        user_ip, user_browser = get_user_info()

        register_data = {
            "username": username, 
            "password": hashed_password,
            "number": number,
            "register_date": datetime.now(),
            "ip_address": user_ip,
            "browser": user_browser
        }

        reg_info.insert_one(register_data)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = reg_info.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            SESSION.login(username)
            flash("Login successful!", "success")
            
            # Add a log entry for successful login
            logs.insert_one({
                "user": username,
                "action": "login",
                "timestamp": datetime.now()
            })
            
            return redirect(url_for("core.home"))
        else:
            flash("Invalid username or password", "error")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    # Get the username before clearing the session
    user = SESSION.get_current_user()

    # Add a log entry for logout
    if user:
        logs.insert_one({
            "user": user,
            "action": "logout",
            "timestamp": datetime.now()
        })
    
    SESSION.logout()
    flash("Logged out successfully!", "info")
    return redirect(url_for("auth.login"))