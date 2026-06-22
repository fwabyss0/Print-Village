# Define your application's data models here
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    company_name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    profile_photo = db.Column(db.String(255), default='default_avatar.png')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active_account = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    otp_code = db.Column(db.String(10), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    products = db.relationship('Product', backref='seller', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
    @property
    def role_name(self): return self.role.name if self.role else None


@login_manager.user_loader
def load_user(uid): return User.query.get(int(uid))


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(80), default='bi-box')
    products = db.relationship('Product', backref='category', lazy=True)


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    offer = db.Column(db.Float, nullable=True)
    offer_duration = db.Column(db.String(50), nullable=True)
    offer_enabled = db.Column(db.Boolean, default=False)
    offer_type = db.Column(db.String(20), default='percentage')
    offer_value = db.Column(db.Float, nullable=True)
    offer_start = db.Column(db.DateTime, nullable=True)
    offer_end = db.Column(db.DateTime, nullable=True)
    stock = db.Column(db.Integer, default=100)
    is_active = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    images = db.relationship('ProductImage', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    @property
    def primary_image(self):
        return self.images[0].filename if self.images else None

    @property
    def is_offer_active(self):
        if not self.offer_enabled:
            return False
        now = datetime.utcnow()
        if self.offer_start and self.offer_start > now:
            return False
        if self.offer_end and self.offer_end < now:
            return False
        return True

    @property
    def discounted_price(self):
        if not self.is_offer_active or self.offer_value is None:
            return self.price
        if self.offer_type == 'percentage':
            discount = self.price * (self.offer_value / 100.0)
            return max(0.0, self.price - discount)
        elif self.offer_type == 'fixed':
            return max(0.0, self.price - self.offer_value)
        return self.price


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    customer_name = db.Column(db.String(120))
    customer_email = db.Column(db.String(120))
    customer_phone = db.Column(db.String(20))
    size = db.Column(db.String(80))
    material = db.Column(db.String(80))
    color = db.Column(db.String(80))
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Pending')
    claimed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    denied_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    denied_at = db.Column(db.DateTime, nullable=True)
    denied_reason = db.Column(db.Text, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller_user = db.relationship('User', foreign_keys=[seller_id])
    claimer = db.relationship('User', foreign_keys=[claimed_by])
    completer = db.relationship('User', foreign_keys=[completed_by])
    denier = db.relationship('User', foreign_keys=[denied_by])
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    files = db.relationship('OrderFile', backref='order', lazy=True, cascade='all, delete-orphan')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0.0)


class OrderFile(db.Model):
    __tablename__ = 'order_files'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)


class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Staff(db.Model):
    __tablename__ = 'staffs'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    joining_date = db.Column(db.Date, default=datetime.utcnow)
    photo = db.Column(db.String(255), default='default_avatar.png')
    biography = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('User', foreign_keys=[admin_id])
    order = db.relationship('Order', foreign_keys=[order_id])


class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), unique=True, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship('Order', backref=db.backref('feedback', uselist=False))


class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)