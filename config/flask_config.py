# config/flask_config.py
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def app_key():
    secret = os.environ.get('SECRET_KEY')
    if not secret:
        secret = 'corenest-engine-secure-flask-key-2026-production'
    return secret


def app_config():
    is_debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')
    db_path = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'data', 'corenest.db'))

    return {
        'DEBUG': is_debug,
        'SECRET_KEY': app_key(),
        'DATABASE': db_path,
        'SESSION_COOKIE_SECURE': False,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'TEMPLATES_AUTO_RELOAD': True
    }
