from app.extensions import db
from app.models import Product, Order, OrderItem

def recommend_for_user(user_id, limit=8):
    cat_ids = db.session.query(Product.category_id).join(OrderItem).join(Order)\
        .filter(Order.buyer_id == user_id).distinct().all()
    cat_ids = [c[0] for c in cat_ids]
    if cat_ids:
        recs = Product.query.filter(Product.category_id.in_(cat_ids), Product.is_active==True)\
            .order_by(Product.views.desc()).limit(limit).all()
        if recs: return recs
    return Product.query.filter_by(is_active=True).order_by(Product.views.desc()).limit(limit).all()