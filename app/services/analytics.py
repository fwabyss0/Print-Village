from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Order, OrderItem, Product

def seller_overview(seller_id):
    base = Order.query.filter_by(seller_id=seller_id)
    revenue = db.session.query(func.coalesce(func.sum(Order.total_amount),0))\
        .filter(Order.seller_id==seller_id, Order.status=='Completed').scalar()
    return {
        'total_orders': base.count(),
        'claimed': base.filter_by(status='Claimed').count(),
        'denied':  base.filter_by(status='Denied').count(),
        'completed': base.filter_by(status='Completed').count(),
        'total_revenue': float(revenue or 0),
        'total_products': Product.query.filter_by(seller_id=seller_id).count(),
    }

def daily_sales(seller_id, days=14):
    start = datetime.utcnow() - timedelta(days=days)
    rows = db.session.query(func.date(Order.created_at), func.sum(Order.total_amount))\
        .filter(Order.seller_id==seller_id, Order.created_at>=start, Order.status=='Completed')\
        .group_by(func.date(Order.created_at)).all()
    return {'labels':[str(r[0]) for r in rows], 'data':[float(r[1] or 0) for r in rows]}

def monthly_sales(seller_id):
    rows = db.session.query(func.date_format(Order.created_at,'%Y-%m'), func.sum(Order.total_amount))\
        .filter(Order.seller_id==seller_id, Order.status=='Completed')\
        .group_by(func.date_format(Order.created_at,'%Y-%m')).all()
    return {'labels':[r[0] for r in rows], 'data':[float(r[1] or 0) for r in rows]}

def top_products(seller_id, limit=5):
    rows = db.session.query(Product.name, func.sum(OrderItem.quantity))\
        .join(OrderItem).join(Order)\
        .filter(Order.seller_id==seller_id, Order.status=='Completed')\
        .group_by(Product.name).order_by(func.sum(OrderItem.quantity).desc()).limit(limit).all()
    return {'labels':[r[0] for r in rows], 'data':[int(r[1]) for r in rows]}

def status_distribution(seller_id):
    rows = db.session.query(Order.status, func.count(Order.id))\
        .filter(Order.seller_id==seller_id).group_by(Order.status).all()
    return {'labels':[r[0] for r in rows], 'data':[int(r[1]) for r in rows]}