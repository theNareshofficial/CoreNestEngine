# config/flask_config.py

import os

def app_key():
    return os.urandom(32)

def app_config():
    return {
        "DEBUG": True,                    # Enables debug mode for development.
        "SESSION_COOKIE_SECURE": False,    # Ensures session cookies are sent over HTTPS only.
        "SESSION_COOKIE_HTTPONLY": True,   # Prevents JavaScript access to session cookies.
        "SESSION_COOKIE_SAMESITE": "Lax"   # Restricts cookies to the same site for CSRF protection.
    }
