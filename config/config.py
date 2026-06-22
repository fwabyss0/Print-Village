import os
from datetime import timedelta
from urllib.parse import quote
import dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
dotenv.load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'print-village-secret-2026')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASS = os.environ.get('MYSQL_PASS', 'qlz@9766#')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'print-village')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{quote(MYSQL_PASS, safe='')}@{MYSQL_HOST}/{MYSQL_DB}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'jpg','jpeg','png','pdf','psd','ai','gif','webp'}
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # SMTP Configuration
    # IMPORTANT: Set MAIL_PASSWORD environment variable to your Gmail App Password
    # To create an App Password: https://support.google.com/accounts/answer/185833
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'print.resolution@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'APP_PASSWORD')  # REPLACE WITH YOUR GMAIL APP PASSWORD
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'print.resolution@gmail.com')