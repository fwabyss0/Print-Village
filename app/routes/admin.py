from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.extensions import db
from app.models import User, Product, ProductImage, Order, Category, Role, Staff
from app.utils.email import send_mail, get_feedback_link
from app.utils.uploads import save_file
from sqlalchemy import func
import datetime

class OrderStatusLog(db.Model):
    __tablename__ = 'order_status_logs'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role_name != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_customers': User.query.join(Role).filter(Role.name == 'customer').count(),
        'total_products': Product.query.count(),
        'total_orders': Order.query.count(),
        'total_revenue': db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status == 'Completed').scalar() or 0,
        'pending_orders': Order.query.filter_by(status='Pending').count(),
        'claimed_orders': Order.query.filter_by(status='Claimed').count(),
        'denied_orders': Order.query.filter_by(status='Denied').count(),
        'completed_orders': Order.query.filter_by(status='Completed').count(),
        'cancelled_orders': Order.query.filter_by(status='Cancelled').count(),
        'total_staffs': Staff.query.count()
    }
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    all_users = User.query.order_by(User.created_at.desc()).all()
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    all_categories = Category.query.all()
    all_staff = Staff.query.order_by(Staff.created_at.desc()).all()
    
    departments = [d[0] for d in db.session.query(Staff.department).distinct() if d[0]]
    positions = [p[0] for p in db.session.query(Staff.position).distinct() if p[0]]

    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_orders=recent_orders,
                           users=all_users,
                           products=all_products,
                           orders=all_orders,
                           categories=all_categories,
                           staff=all_staff,
                           departments=departments,
                           positions=positions)


# ── USERS ────────────────────────────────────────────────────────────────────

@bp.route('/users')
@login_required
@admin_required
def users():
    # Deprecated for main view, kept for safety / fallback
    role_filter = request.args.get('role', '')
    q = User.query.join(Role)
    if role_filter:
        q = q.filter(Role.name == role_filter)
    all_users = q.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users, role_filter=role_filter)


@bp.route('/users/<int:uid>/toggle', methods=['POST'])
@login_required
@admin_required
def user_toggle(uid):
    u = User.query.get_or_404(uid)
    u.is_active_account = not u.is_active_account
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Account {"enabled" if u.is_active_account else "disabled"}.',
        'is_active': u.is_active_account
    })


@bp.route('/users/<int:uid>/delete', methods=['POST'])
@login_required
@admin_required
def user_delete(uid):
    u = User.query.get_or_404(uid)
    try:
        db.session.delete(u)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully.'})
    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Cannot delete user. They may have active orders. Try disabling the account instead.'
        }), 400


# ── PRODUCTS ─────────────────────────────────────────────────────────────────


@bp.route('/add-product', methods=['GET', 'POST'])
def add_product():
    """Add a new product to the catalogue (auth temporarily disabled)."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price_raw = request.form.get('price', '')
        stock_raw = request.form.get('stock', '100')
        category_id = request.form.get('category_id') or None
        offer_raw = request.form.get('offer', '')
        offer_duration = request.form.get('offer_duration', '').strip()

        if not name or not price_raw:
            flash('Product name and price are required.', 'danger')
            return redirect(url_for('admin.add_product'))
        try:
            price_val = float(price_raw)
            stock_val = int(stock_raw) if stock_raw else 100
            offer_val = float(offer_raw) if offer_raw else None
        except ValueError:
            flash('Invalid price, stock, or offer value.', 'danger')
            return redirect(url_for('admin.add_product'))

        # Get the first admin user as the seller_id placeholder
        admin_user = User.query.join(Role).filter(Role.name == 'admin').first()
        seller_id = admin_user.id if admin_user else 1

        new_product = Product(
            name=name,
            description=description,
            price=price_val,
            stock=stock_val,
            category_id=category_id,
            seller_id=seller_id,
            is_active=True,
            offer=offer_val,
            offer_duration=offer_duration if offer_duration else None,
        )
        db.session.add(new_product)
        db.session.flush()  # get new_product.id before committing

        # Handle image uploads
        images = request.files.getlist('images')
        for img_file in images:
            if img_file and img_file.filename:
                saved = save_file(img_file, 'products')
                if saved:
                    db.session.add(ProductImage(product_id=new_product.id, filename=saved))

        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin.dashboard') + '#products')

    categories = Category.query.all()
    return render_template('admin/add_product.html', categories=categories)


@bp.route('/products/<int:pid>/edit', methods=['POST'])
def product_edit(pid):
    """AJAX endpoint to update product price, stock, name, description, offer and offer_duration."""
    p = Product.query.get_or_404(pid)
    data = request.get_json(silent=True) or request.form

    try:
        if 'price' in data:
            p.price = float(data['price'])
        if 'stock' in data:
            p.stock = int(data['stock'])
        if 'name' in data and data['name'].strip():
            p.name = data['name'].strip()
        if 'description' in data:
            p.description = data['description'].strip()
        if 'offer' in data and data['offer']:
            p.offer = float(data['offer'])
        else:
            p.offer = None
        if 'offer_duration' in data and data['offer_duration']:
            p.offer_duration = data['offer_duration'].strip()
        else:
            p.offer_duration = None
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'message': f'Invalid value: {e}'}), 400

    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Product #{pid} updated successfully.',
        'price': p.price,
        'stock': p.stock,
        'name': p.name,
        'offer': p.offer,
        'offer_duration': p.offer_duration,
    })


@bp.route('/products')
@login_required
@admin_required
def products():
    # Deprecated for main view, kept for safety
    items = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=items)


@bp.route('/products/<int:pid>/toggle', methods=['POST'])
@login_required
@admin_required
def product_toggle(pid):
    p = Product.query.get_or_404(pid)
    p.is_active = not p.is_active
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Product {"activated" if p.is_active else "deactivated"}.',
        'is_active': p.is_active
    })


@bp.route('/products/<int:pid>/delete', methods=['POST'])
@login_required
@admin_required
def product_delete(pid):
    p = Product.query.get_or_404(pid)
    try:
        db.session.delete(p)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted.'})
    except Exception:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Cannot delete product. It is linked to existing orders. Try deactivating instead.'
        }), 400


# ── ORDERS ───────────────────────────────────────────────────────────────────

@bp.route('/orders')
@login_required
@admin_required
def orders():
    return redirect(url_for('admin.dashboard') + '#orders')


@bp.route('/orders/<int:oid>/claim', methods=['POST'])
@login_required
@admin_required
def order_claim(oid):
    order = Order.query.get_or_404(oid)
    order.status = 'Claimed'
    order.claimed_by = current_user.id
    order.claimed_at = datetime.datetime.utcnow()
    
    log = OrderStatusLog(order_id=order.id, status='Claimed', notes=f'Order claimed by admin: {current_user.full_name}')
    db.session.add(log)
    db.session.commit()
    
    # Send email to customer
    customer_body = f"""
    <p>Hello {order.customer_name},</p>
    <p>Your order has been claimed and is now being processed by our team.</p>
    <p>Your order has been claimed and will be delivered to you soon.</p>
    <p>Thank you for choosing Print Village.</p>
    <p>Regards,<br>Print Village Team</p>
    """
    send_mail(order.customer_email, "Print Village - Order Claimed", customer_body)
    
    return jsonify({'success': True, 'message': 'Order successfully claimed.'})


@bp.route('/orders/<int:oid>/deny', methods=['POST'])
@login_required
@admin_required
def order_deny(oid):
    order = Order.query.get_or_404(oid)
    
    # Get reason from request
    reason = ""
    if request.is_json:
        reason = request.get_json().get('reason', '').strip()
    else:
        reason = request.form.get('reason', '').strip()
        
    if not reason:
        return jsonify({'success': False, 'message': 'Reason for denial is required.'}), 400
        
    order.status = 'Denied'
    order.denied_by = current_user.id
    order.denied_at = datetime.datetime.utcnow()
    order.denied_reason = reason
    
    log = OrderStatusLog(order_id=order.id, status='Denied', notes=f'Order denied by admin: {current_user.full_name}. Reason: {reason}')
    db.session.add(log)
    db.session.commit()
    
    # Send email to customer
    customer_body = f"""
    <p>Hello {order.customer_name},</p>
    <p>Unfortunately your order has been denied.</p>
    <p>Reason:</p>
    <p>{reason}</p>
    <p>If you believe this was a mistake, please contact us.</p>
    <p>Regards,<br>Print Village Team</p>
    """
    send_mail(order.customer_email, "Print Village - Order Denied", customer_body)
    
    return jsonify({'success': True, 'message': 'Order denied successfully.'})


@bp.route('/orders/<int:oid>/complete', methods=['POST'])
@login_required
@admin_required
def order_complete(oid):
    order = Order.query.get_or_404(oid)
    order.status = 'Completed'
    order.completed_by = current_user.id
    order.completed_at = datetime.datetime.utcnow()
    
    log = OrderStatusLog(order_id=order.id, status='Completed', notes=f'Order completed by admin: {current_user.full_name}')
    db.session.add(log)
    db.session.commit()
    
    # Send email to customer
    customer_body = f"""
    <p>Hello {order.customer_name},</p>
    <p>Your order has been completed.</p>
    <p>Thank you for choosing Print Village.</p>
    <p>Regards,<br>Print Village Team</p>
    """
    send_mail(order.customer_email, "Print Village - Order Completed", customer_body)
    
    return jsonify({'success': True, 'message': 'Order completed successfully.'})


@bp.route('/order-details/<int:oid>')
@login_required
@admin_required
def order_details(oid):
    order = Order.query.get_or_404(oid)
    logs = OrderStatusLog.query.filter_by(order_id=oid).order_by(OrderStatusLog.created_at.desc()).all()
    return render_template('admin/_order_details_modal.html', order=order, logs=logs)


# ── CATEGORIES ───────────────────────────────────────────────────────────────

@bp.route('/categories')
@login_required
@admin_required
def categories():
    cats = Category.query.all()
    return render_template('admin/categories.html', categories=cats)


@bp.route('/categories/add', methods=['POST'])
@login_required
@admin_required
def category_add():
    name = request.form.get('name', '').strip()
    slug = name.lower().replace(' ', '-')
    icon = request.form.get('icon', 'bi-box')
    if name:
        if Category.query.filter_by(slug=slug).first():
            return jsonify({'success': False, 'message': 'Category with this name/slug already exists.'}), 400
        cat = Category(name=name, slug=slug, icon=icon)
        db.session.add(cat)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category added successfully.', 'id': cat.id, 'name': cat.name, 'slug': cat.slug, 'icon': cat.icon})
    return jsonify({'success': False, 'message': 'Category name cannot be empty.'}), 400


@bp.route('/categories/<int:cid>/delete', methods=['POST'])
@login_required
@admin_required
def category_delete(cid):
    c = Category.query.get_or_404(cid)
    try:
        db.session.delete(c)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category deleted.'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Cannot delete category. It may contain associated products.'}), 400


# ── ANALYTICS API ────────────────────────────────────────────────────────────

@bp.route('/analytics/data')
@login_required
@admin_required
def analytics_data():
    # Revenue per month
    monthly = db.session.query(
        func.date_format(Order.created_at, '%Y-%m'),
        func.sum(Order.total_amount)
    ).filter(Order.status == 'Completed')\
     .group_by(func.date_format(Order.created_at, '%Y-%m')).all()

    status_dist = db.session.query(Order.status, func.count(Order.id))\
        .group_by(Order.status).all()

    top_customers = db.session.query(User.full_name, func.sum(Order.total_amount))\
        .join(Order, Order.buyer_id == User.id)\
        .filter(Order.status == 'Completed')\
        .group_by(User.full_name)\
        .order_by(func.sum(Order.total_amount).desc()).limit(5).all()

    return jsonify({
        'monthly': {'labels': [r[0] for r in monthly], 'data': [float(r[1] or 0) for r in monthly]},
        'status_dist': {'labels': [r[0] for r in status_dist], 'data': [int(r[1]) for r in status_dist]},
        'top_sellers': {'labels': [r[0] for r in top_customers], 'data': [float(r[1] or 0) for r in top_customers]},
    })


# ── NOTIFICATIONS CENTER ─────────────────────────────────────────────────────

@bp.route('/notifications')
@login_required
@admin_required
def get_notifications():
    from app.models import Notification
    # Get latest notifications first
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    unread_count = Notification.query.filter_by(is_read=False).count()
    
    list_data = []
    for n in notifications:
        list_data.append({
            'id': n.id,
            'order_id': n.order_id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    return jsonify({
        'success': True,
        'unread_count': unread_count,
        'notifications': list_data
    })


@bp.route('/notifications/<int:nid>/read', methods=['POST'])
@login_required
@admin_required
def mark_notification_read(nid):
    from app.models import Notification
    n = Notification.query.get_or_404(nid)
    n.is_read = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Notification marked as read.'})


@bp.route('/notifications/read-all', methods=['POST'])
@login_required
@admin_required
def mark_all_notifications_read():
    from app.models import Notification
    Notification.query.filter_by(is_read=False).update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'success': True, 'message': 'All notifications marked as read.'})


# ── NOTIFICATIONS (unread count helper) ─────────────────────────────────────

@bp.route('/notifications/unread-count')
@login_required
@admin_required
def unread_notification_count():
    count = Notification.query.filter_by(is_read=False).count()
    return jsonify({'success': True, 'count': count})


# ── STAFF MANAGEMENT ────────────────────────────────────────────────────────

@bp.route('/staff')
@login_required
@admin_required
def staff():
    return redirect(url_for('admin.dashboard') + '#staff')


@bp.route('/staff/list')
@login_required
@admin_required
def staff_list():
    q = request.args.get('q', '').strip()
    dept = request.args.get('department', '').strip()
    pos = request.args.get('position', '').strip()
    sort = request.args.get('sort', 'newest').strip()
    
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
        
    per_page = 6
    query = Staff.query
    
    # Filtering / Searching
    if q:
        query = query.filter(
            (Staff.full_name.ilike(f'%{q}%')) |
            (Staff.position.ilike(f'%{q}%')) |
            (Staff.department.ilike(f'%{q}%'))
        )
    if dept:
        query = query.filter(Staff.department == dept)
    if pos:
        query = query.filter(Staff.position == pos)
        
    # Sorting
    if sort == 'oldest':
        query = query.order_by(Staff.joining_date.asc(), Staff.id.asc())
    elif sort == 'alpha_asc':
        query = query.order_by(Staff.full_name.asc())
    elif sort == 'alpha_desc':
        query = query.order_by(Staff.full_name.desc())
    else: # newest
        query = query.order_by(Staff.joining_date.desc(), Staff.id.desc())
        
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    staff_data = []
    for s in pagination.items:
        staff_data.append({
            'id': s.id,
            'full_name': s.full_name,
            'position': s.position,
            'department': s.department or '',
            'email': s.email or '',
            'phone': s.phone or '',
            'joining_date': s.joining_date.strftime('%Y-%m-%d') if s.joining_date else '',
            'photo': s.photo,
            'biography': s.biography or '',
            'is_active': s.is_active
        })
        
    return jsonify({
        'success': True,
        'staff': staff_data,
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    })


@bp.route('/staff/<int:sid>')
@login_required
@admin_required
def staff_detail(sid):
    s = Staff.query.get_or_404(sid)
    return jsonify({
        'success': True,
        'id': s.id,
        'full_name': s.full_name,
        'position': s.position,
        'department': s.department or '',
        'email': s.email or '',
        'phone': s.phone or '',
        'joining_date': s.joining_date.strftime('%Y-%m-%d') if s.joining_date else '',
        'photo': s.photo,
        'biography': s.biography or '',
        'is_active': s.is_active
    })


@bp.route('/staff/add', methods=['POST'])
@login_required
@admin_required
def staff_add():
    full_name = request.form.get('full_name') or request.form.get('name')
    position = request.form.get('position')
    department = request.form.get('department')
    email = request.form.get('email')
    phone = request.form.get('phone')
    biography = request.form.get('biography') or request.form.get('bio')
    joining_date_str = request.form.get('joining_date')
    
    joining_date = datetime.date.today()
    if joining_date_str:
        try:
            joining_date = datetime.datetime.strptime(joining_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    photo_name = 'default_avatar.png'
    photo_file = request.files.get('photo') or request.files.get('profile_photo')
    if photo_file and photo_file.filename != '':
        photo = save_file(photo_file, 'staff')
        if photo:
            photo_name = photo

    if full_name and position:
        new_staff = Staff(
            full_name=full_name, position=position, department=department,
            email=email, phone=phone, biography=biography, joining_date=joining_date,
            photo=photo_name, is_active=True
        )
        db.session.add(new_staff)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Staff member added successfully.'})
            
    return jsonify({'success': False, 'message': 'Full Name and Position are required.'}), 400


@bp.route('/staff/<int:sid>/edit', methods=['POST'])
@login_required
@admin_required
def staff_edit(sid):
    s = Staff.query.get_or_404(sid)
    s.full_name = request.form.get('full_name') or request.form.get('name', s.full_name)
    s.position = request.form.get('position', s.position)
    s.department = request.form.get('department', s.department)
    s.email = request.form.get('email', s.email)
    s.phone = request.form.get('phone', s.phone)
    s.biography = request.form.get('biography') or request.form.get('bio', s.biography)
    
    joining_date_str = request.form.get('joining_date')
    if joining_date_str:
        try:
            s.joining_date = datetime.datetime.strptime(joining_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    photo_file = request.files.get('photo') or request.files.get('profile_photo')
    if photo_file and photo_file.filename != '':
        photo = save_file(photo_file, 'staff')
        if photo:
            # Delete old photo if it is not default
            if s.photo and s.photo != 'default_avatar.png':
                import os
                from flask import current_app
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], s.photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Error removing old photo: {e}")
            s.photo = photo
            
    db.session.commit()
    return jsonify({'success': True, 'message': 'Staff member updated successfully.'})


@bp.route('/staff/<int:sid>/delete', methods=['POST'])
@login_required
@admin_required
def staff_delete(sid):
    s = Staff.query.get_or_404(sid)
    # Delete associated photo file
    if s.photo and s.photo != 'default_avatar.png':
        import os
        from flask import current_app
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], s.photo)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing photo: {e}")
                
    db.session.delete(s)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Staff member removed successfully.'})


@bp.route('/staff/<int:sid>/toggle', methods=['POST'])
@login_required
@admin_required
def staff_toggle(sid):
    s = Staff.query.get_or_404(sid)
    s.is_active = not s.is_active
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Staff visibility {"activated" if s.is_active else "deactivated"}.',
        'is_active': s.is_active
    })


# ── ADMIN PROFILE SETTINGS ───────────────────────────────────────────────────

@bp.route('/profile/update', methods=['POST'])
@login_required
@admin_required
def profile_update():
    f = request.form
    current_user.full_name = f.get('full_name', current_user.full_name)
    current_user.email = f.get('email', current_user.email)
    
    if 'profile_photo' in request.files and request.files['profile_photo'].filename != '':
        photo = save_file(request.files['profile_photo'], 'admin')
        if photo:
            current_user.profile_photo = photo
            
    if f.get('new_password'):
        if not current_user.check_password(f.get('current_password', '')):
            return jsonify({'success': False, 'message': 'Current password verification failed.'}), 400
        if f.get('new_password') != f.get('confirm_password'):
            return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
        current_user.set_password(f['new_password'])
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile settings updated successfully.'})
