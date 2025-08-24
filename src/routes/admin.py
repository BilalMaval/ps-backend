from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.product import Product, Order, OrderItem
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def require_admin():
    """Decorator to require admin authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            user = User.query.get(user_id)
            if not user or not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@admin_bp.route('/dashboard', methods=['GET'])
@require_admin()
def admin_dashboard():
    try:
        # Get dashboard statistics
        total_users = User.query.count()
        total_products = Product.query.filter_by(is_active=True).count()
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Revenue calculation (last 30 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.created_at >= thirty_days_ago
        ).scalar() or 0
        
        return jsonify({
            'stats': {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'recent_revenue': float(recent_revenue)
            },
            'recent_orders': [order.to_dict() for order in recent_orders]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
@require_admin()
def get_users():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = User.query
        
        if search:
            query = query.filter(
                (User.username.contains(search)) |
                (User.email.contains(search)) |
                (User.first_name.contains(search)) |
                (User.last_name.contains(search))
            )
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin()
def update_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update allowed fields
        if 'is_admin' in data:
            user.is_admin = bool(data['is_admin'])
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'address' in data:
            user.address = data['address']
        
        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products', methods=['GET'])
@require_admin()
def admin_get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        query = Product.query
        
        if search:
            query = query.filter(
                (Product.name.contains(search)) |
                (Product.description.contains(search))
            )
        
        if category:
            query = query.filter_by(category=category)
        
        products = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'products': [product.to_dict() for product in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products', methods=['POST'])
@require_admin()
def admin_create_product():
    try:
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('price'):
            return jsonify({'error': 'Name and price are required'}), 400
        
        product = Product(
            name=data['name'],
            description=data.get('description', ''),
            price=float(data['price']),
            category=data.get('category', 'general'),
            image_url=data.get('image_url', ''),
            stock_quantity=int(data.get('stock_quantity', 0)),
            is_featured=bool(data.get('is_featured', False))
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify(product.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
@require_admin()
def admin_update_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if 'name' in data:
            product.name = data['name']
        if 'description' in data:
            product.description = data['description']
        if 'price' in data:
            product.price = float(data['price'])
        if 'category' in data:
            product.category = data['category']
        if 'image_url' in data:
            product.image_url = data['image_url']
        if 'stock_quantity' in data:
            product.stock_quantity = int(data['stock_quantity'])
        if 'is_featured' in data:
            product.is_featured = bool(data['is_featured'])
        if 'is_active' in data:
            product.is_active = bool(data['is_active'])
        
        db.session.commit()
        return jsonify(product.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
@require_admin()
def admin_delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        product.is_active = False  # Soft delete
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/orders', methods=['GET'])
@require_admin()
def admin_get_orders():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', '')
        
        query = Order.query
        
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
@require_admin()
def update_order_status(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        order.status = data['status']
        db.session.commit()
        
        return jsonify(order.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

