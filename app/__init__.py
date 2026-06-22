from flask import Flask
from config.config import Config
from .extensions import db, login_manager, mail
from flask_login import current_user
import pymysql


def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    from config.config import Config
    config = Config()
    try:
        connection = pymysql.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASS
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error creating database: {e}")


def migrate_database():
    """Migrates the schema to add order tracking columns, notifications, updates staff, and product offer fields"""
    from sqlalchemy import text
    from .extensions import db
    
    # 1. Add missing order tracking columns
    columns = [
        ("status", "VARCHAR(20) DEFAULT 'Pending'"),
        ("claimed_by", "INT NULL, ADD CONSTRAINT fk_orders_claimed_by FOREIGN KEY (claimed_by) REFERENCES users(id)"),
        ("claimed_at", "DATETIME NULL"),
        ("completed_by", "INT NULL, ADD CONSTRAINT fk_orders_completed_by FOREIGN KEY (completed_by) REFERENCES users(id)"),
        ("completed_at", "DATETIME NULL"),
        ("denied_by", "INT NULL, ADD CONSTRAINT fk_orders_denied_by FOREIGN KEY (denied_by) REFERENCES users(id)"),
        ("denied_at", "DATETIME NULL"),
        ("denied_reason", "TEXT NULL")
    ]
    
    for col_name, col_def in columns:
        try:
            # Check if column exists
            db.session.execute(text(f"SELECT {col_name} FROM orders LIMIT 1"))
            db.session.rollback()
        except Exception:
            db.session.rollback()
            try:
                db.session.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
                print(f"Migration: Added column {col_name} to orders table.")
            except Exception as e:
                db.session.rollback()
                print(f"Migration error for {col_name}: {e}")

    # 2. Check if we need to drop staffs to recreate with full_name, photo, biography
    try:
        db.session.execute(text("SELECT name FROM staffs LIMIT 1"))
        db.session.rollback()
        # If it succeeds, the old staffs table exists. Drop it so SQLAlchemy creates the new table.
        try:
            db.session.execute(text("DROP TABLE staffs"))
            db.session.commit()
            print("Migration: Dropped old staffs table to recreate with new schema.")
        except Exception as e:
            db.session.rollback()
            print(f"Migration: Error dropping staffs table: {e}")
    except Exception:
        db.session.rollback()

    # 3. Add offer and offer_duration columns to products table
    product_columns = [
        ("offer", "FLOAT NULL"),
        ("offer_duration", "VARCHAR(50) NULL"),
        ("offer_enabled", "BOOLEAN DEFAULT FALSE"),
        ("offer_type", "VARCHAR(20) DEFAULT 'percentage'"),
        ("offer_value", "FLOAT NULL"),
        ("offer_start", "DATETIME NULL"),
        ("offer_end", "DATETIME NULL")
    ]
    
    for col_name, col_def in product_columns:
        try:
            # Check if column exists
            db.session.execute(text(f"SELECT {col_name} FROM products LIMIT 1"))
            db.session.rollback()
        except Exception:
            db.session.rollback()
            try:
                db.session.execute(text(f"ALTER TABLE products ADD COLUMN {col_name} {col_def}"))
                db.session.commit()
                print(f"Migration: Added column {col_name} to products table.")
            except Exception as e:
                db.session.rollback()
                print(f"Migration error for {col_name}: {e}")


def create_app():
    # Create database if it doesn't exist
    create_database_if_not_exists()
    
    app = Flask(__name__, static_folder='../static', template_folder='../templates')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Make current_user available globally, including inside Jinja2 macros
    app.add_template_global(current_user, 'current_user')

    with app.app_context():
        from .routes.auth import bp as auth_bp
        from .routes.main import bp as main_bp
        from .routes.buyer import bp as buyer_bp
        from .routes.admin import bp as admin_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(buyer_bp)
        app.register_blueprint(admin_bp)

        from .models import Role, Category, Staff
        migrate_database()
        db.create_all()
        seed_default_data()

    return app


def seed_default_data():
    from .models import Role, Category, Staff
    roles = ['customer', 'admin']
    for role_name in roles:
        if not Role.query.filter_by(name=role_name).first():
            db.session.add(Role(name=role_name))

    default_categories = [
        {'name': 'Posters',           'slug': 'posters',          'icon': 'bi-card-heading'},
        {'name': 'Stickers',          'slug': 'stickers',         'icon': 'bi-stickies'},
        {'name': 'Books',             'slug': 'books',            'icon': 'bi-journal-bookmark'},
        {'name': 'Business Cards',    'slug': 'business-cards',   'icon': 'bi-briefcase'},
        {'name': 'Flyers',            'slug': 'flyers',           'icon': 'bi-file-earmark-text'},
        {'name': 'Brochures',         'slug': 'brochures',        'icon': 'bi-book-half'},
        {'name': 'Banners',           'slug': 'banners',          'icon': 'bi-flag'},
        {'name': 'Frames',            'slug': 'frames',           'icon': 'bi-image'},
        {'name': 'Token of Love',     'slug': 'token-of-love',    'icon': 'bi-heart'},
        {'name': 'Photo Printing',    'slug': 'photo-printing',   'icon': 'bi-camera'},
        {'name': 'Customized Gifts',  'slug': 'customized-gifts', 'icon': 'bi-gift'},
        {'name': 'Corporate Branding','slug': 'corporate-branding','icon': 'bi-building'},
    ]
    for category_data in default_categories:
        if not Category.query.filter_by(slug=category_data['slug']).first():
            db.session.add(Category(**category_data))

    # Create default admin account
    from .models import User
    admin_role = Role.query.filter_by(name='admin').first()
    if admin_role and not User.query.filter_by(email='print.resolution01@gmail.com').first():
        default_admin = User(
            full_name='Print Village Admin',
            company_name='Print Village Corporate HQ',
            email='print.resolution01@gmail.com',
            phone='9800000000',
            whatsapp='9800000000',
            role_id=admin_role.id,
            is_active_account=True,
            email_verified=True,
            approved=True
        )
        default_admin.set_password('Admin@123')
        db.session.add(default_admin)

    # Create default staff accounts
    default_staff = [
        {
            'full_name': 'Ramesh Shrestha',
            'position': 'CEO & Founder',
            'department': 'Management',
            'email': 'ramesh@printvillage.com',
            'biography': 'Printing industry veteran with 15+ years of experience. Visionary leader driving Print Village forward.'
        },
        {
            'full_name': 'Sita Maharjan',
            'position': 'Head of Operations',
            'department': 'Production',
            'email': 'sita@printvillage.com',
            'biography': 'Oversees day-to-day operations ensuring on-time delivery and quality control across all orders.'
        },
        {
            'full_name': 'Bikash Tamang',
            'position': 'Lead Print Technician',
            'department': 'Technical',
            'email': 'bikash@printvillage.com',
            'biography': 'HP Indigo certified technician with 10+ years of expertise in digital and offset printing.'
        },
        {
            'full_name': 'Anita Gurung',
            'position': 'Customer Success Manager',
            'department': 'Support',
            'email': 'anita@printvillage.com',
            'biography': 'Dedicated to ensuring every customer gets exactly what they need with a smile.'
        }
    ]
    for s_info in default_staff:
        if not Staff.query.filter_by(full_name=s_info['full_name']).first():
            db.session.add(Staff(**s_info))

    db.session.commit()
