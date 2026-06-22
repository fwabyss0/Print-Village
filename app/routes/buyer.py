from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, Category, Order, OrderItem, OrderFile, Favorite
from app.routes.admin import OrderStatusLog
from app.utils.email import send_mail
from app.utils.uploads import save_file
from app.services.recommendation import recommend_for_user
from datetime import datetime

bp = Blueprint('buyer', __name__, url_prefix='/buyer')


@bp.route('/dashboard')
@login_required
def dashboard():
    recs = recommend_for_user(current_user.id)
    all_orders = Order.query.filter_by(buyer_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    recent = all_orders[:5]
    fav_ids = [f.product_id for f in current_user.favorites]
    fav_products = Product.query.filter(Product.id.in_(fav_ids), Product.is_active == True).all()
    
    return render_template('buyer/dashboard.html',
                           recommendations=recs,
                           recent_orders=recent,
                           orders=all_orders,
                           fav_products=fav_products,
                           fav_ids=set(fav_ids))


@bp.route('/products')
def products():
    q = request.args.get('q', '').strip()
    cat = request.args.get('category', '')
    sort = request.args.get('sort', 'new')
    query = Product.query.filter_by(is_active=True)
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    if cat:
        query = query.join(Category).filter(Category.slug == cat)
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'popular':
        query = query.order_by(Product.views.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    items = query.all()
    fav_ids = set()
    if current_user.is_authenticated:
        fav_ids = {f.product_id for f in current_user.favorites}
    return render_template('buyer/products.html',
                           products=items,
                           categories=Category.query.all(),
                           q=q,
                           current_cat=cat,
                           sort=sort,
                           fav_ids=fav_ids)


@bp.route('/product/<int:pid>')
def product_detail(pid):
    p = Product.query.get_or_404(pid)
    p.views = (p.views or 0) + 1
    db.session.commit()
    related = Product.query.filter(
        Product.category_id == p.category_id,
        Product.id != p.id,
        Product.is_active == True
    ).limit(4).all()
    is_fav = False
    if current_user.is_authenticated:
        is_fav = Favorite.query.filter_by(
            user_id=current_user.id, product_id=pid).first() is not None
    return render_template('buyer/product_detail.html',
                           product=p,
                           related=related,
                           is_fav=is_fav)


@bp.route('/order/<int:pid>', methods=['POST'])
@login_required
def place_order(pid):
    p = Product.query.get_or_404(pid)
    f = request.form
    qty = int(f.get('quantity', 1))

    if p.stock < qty:
        flash(f'Sorry, only {p.stock} units available.', 'danger')
        return redirect(url_for('buyer.product_detail', pid=pid))

    # Find the default admin user to assign as the seller_id for the order
    admin_user = Product.query.filter_by(id=p.id).first().seller # Fallback to product's seller_id
    if not admin_user:
        from app.models import User, Role
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            admin_user = User.query.filter_by(role_id=admin_role.id).first()

    order = Order(
        buyer_id=current_user.id,
        seller_id=admin_user.id if admin_user else p.seller_id,
        customer_name=f.get('customer_name', current_user.full_name),
        customer_email=f.get('customer_email', current_user.email),
        customer_phone=f.get('customer_phone', current_user.phone),
        size=f.get('size'),
        material=f.get('material'),
        color=f.get('color'),
        description=f.get('description'),
        instructions=f.get('instructions'),
        total_amount=p.discounted_price * qty,
        status='Pending'
    )
    db.session.add(order)
    db.session.flush()
    
    # Log the initial pending status
    db.session.add(OrderStatusLog(order_id=order.id, status='Pending', notes='Order submitted by customer.'))
    
    db.session.add(OrderItem(
        order_id=order.id, product_id=p.id,
        quantity=qty, unit_price=p.discounted_price
    ))

    p.stock -= qty

    for f_up in request.files.getlist('design_files'):
        fname = save_file(f_up, 'orders')
        if fname:
            db.session.add(OrderFile(order_id=order.id, filename=fname))
    db.session.commit()

    # Create notification record in database
    from app.models import Notification
    amount_str = f"Rs. {order.total_amount:,.2f}"
    comp_name = getattr(current_user, 'company_name', 'N/A') or 'N/A'
    
    notif = Notification(
        admin_id=None,
        order_id=order.id,
        title="🔔 New Order Received",
        message=f"Customer: {order.customer_name}\nAmount: {amount_str}\nOrder ID: {order.id}",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.session.add(notif)
    db.session.commit()

    # Admin email alert
    admin_email_body = f"""
    <p>A new order has been placed.</p>
    <p><b>Order ID:</b> {order.id}</p>
    <p><b>Customer:</b> {order.customer_name}</p>
    <p><b>Company:</b> {comp_name}</p>
    <p><b>Amount:</b> {amount_str}</p>
    <p>Please review the order in the Admin Dashboard.</p>
    """
    send_mail("print.resolution@gmail.com", "New Order Received - Print Village", admin_email_body)

    flash(f'Order #{order.id} placed successfully! We\'ll contact you shortly.', 'success')
    return redirect(url_for('buyer.dashboard') + '#orders')


@bp.route('/orders/<int:oid>/cancel', methods=['POST'])
@login_required
def order_cancel(oid):
    o = Order.query.filter_by(id=oid, buyer_id=current_user.id).first_or_404()
    if o.status == 'Pending':
        o.status = 'Cancelled'
        o.cancelled_at = datetime.utcnow()
        log = OrderStatusLog(order_id=o.id, status='Cancelled', notes='Cancelled by customer.')
        db.session.add(log)
        db.session.commit()
        
        # Send cancellation email to admin
        cancel_body = f"""
        <h3>Order #{o.id} Cancelled by Customer</h3>
        <p><b>Customer Name:</b> {o.customer_name}</p>
        <p><b>Company Name:</b> {getattr(current_user, 'company_name', 'N/A')}</p>
        <p><b>Email:</b> {o.customer_email}</p>
        <p><b>Cancellation Timestamp:</b> {o.cancelled_at}</p>
        """
        send_mail("print.resolution01@gmail.com", f"Order #{o.id} Cancelled - Print Village", cancel_body)
        
        return jsonify({'success': True, 'message': 'Order has been cancelled.'})
    else:
        return jsonify({'success': False, 'message': 'Only pending orders can be cancelled.'}), 400


@bp.route('/order-details/<int:oid>')
@login_required
def order_details(oid):
    o = Order.query.filter_by(id=oid, buyer_id=current_user.id).first_or_404()
    logs = OrderStatusLog.query.filter_by(order_id=oid).order_by(OrderStatusLog.created_at.desc()).all()
    return render_template('buyer/_order_details_modal.html', order=o, logs=logs)


@bp.route('/favorite/<int:pid>', methods=['POST'])
@login_required
def toggle_fav(pid):
    existing = Favorite.query.filter_by(
        user_id=current_user.id, product_id=pid).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'favorited': False})
    db.session.add(Favorite(user_id=current_user.id, product_id=pid))
    db.session.commit()
    return jsonify({'favorited': True})


@bp.route('/profile/update', methods=['POST'])
@login_required
def profile_update():
    f = request.form
    current_user.full_name = f.get('full_name', current_user.full_name)
    current_user.phone = f.get('phone', current_user.phone)
    current_user.whatsapp = f.get('whatsapp', current_user.whatsapp)
    current_user.company_name = f.get('company_name', current_user.company_name)
    
    if f.get('new_password'):
        if not current_user.check_password(f.get('current_password', '')):
            return jsonify({'success': False, 'message': 'Current password incorrect.'}), 400
        current_user.set_password(f['new_password'])
        
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully!'})


@bp.route('/orders/<int:oid>/feedback', methods=['GET', 'POST'])
def feedback_submission(oid):
    o = Order.query.get_or_404(oid)
    from app.models import Feedback
    existing = Feedback.query.filter_by(order_id=oid).first()
    if request.method == 'POST':
        if existing:
            flash('Feedback has already been submitted for this order.', 'warning')
            return redirect(url_for('buyer.dashboard'))
        rating = int(request.form.get('rating', 5))
        comments = request.form.get('comments', '')
        fb = Feedback(order_id=oid, rating=rating, comments=comments)
        db.session.add(fb)
        db.session.commit()
        flash('Thank you for your feedback! It helps us improve.', 'success')
        return render_template('buyer/feedback_success.html')
    return render_template('buyer/feedback.html', order=o, existing=existing)