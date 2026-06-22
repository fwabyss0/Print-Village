from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.extensions import db
from app.models import Product

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    featured = Product.query.filter_by(is_active=True).order_by(Product.views.desc()).limit(8).all()
    return render_template('index.html', featured=featured)

@bp.route('/services')
def services(): return render_template('services.html')

@bp.route('/about')
def about():
    from app.models import Staff
    staff_members = Staff.query.filter_by(is_active=True).all()
    return render_template('about.html', staff_members=staff_members)

@bp.route('/contact')
def contact():
    return render_template('contact.html')