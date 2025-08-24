from flask import Blueprint, request, jsonify, session
from src.models.user import db, User
from src.models.product import Product, CartItem, Order, OrderItem

cart_bp = Blueprint('cart', __name__)

def require_auth():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)

@cart_bp.route('/cart', methods=['GET'])
def get_cart():
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        return jsonify([item.to_dict() for item in cart_items]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/cart', methods=['POST'])
def add_to_cart():
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data or not data.get('product_id'):
            return jsonify({'error': 'Product ID is required'}), 400
        
        product_id = int(data['product_id'])
        quantity = int(data.get('quantity', 1))
        custom_image_url = data.get('custom_image_url', '')
        custom_text = data.get('custom_text', '')
        
        # Validate product exists and is active
        product = Product.query.get(product_id)
        if not product or not product.is_active:
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if item already exists in cart
        existing_item = CartItem.query.filter_by(
            user_id=user.id,
            product_id=product_id
        ).first()
        
        if existing_item:
            # Update quantity and custom fields
            existing_item.quantity += quantity
            if custom_image_url:
                existing_item.custom_image_url = custom_image_url
            if custom_text:
                existing_item.custom_text = custom_text
            cart_item = existing_item
        else:
            # Create new cart item
            cart_item = CartItem(
                user_id=user.id,
                product_id=product_id,
                quantity=quantity,
                custom_image_url=custom_image_url,
                custom_text=custom_text
            )
            db.session.add(cart_item)
        
        db.session.commit()
        return jsonify(cart_item.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/cart/<int:item_id>', methods=['PUT'])
def update_cart_item(item_id):
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        cart_item = CartItem.query.filter_by(id=item_id, user_id=user.id).first()
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if 'quantity' in data:
            quantity = int(data['quantity'])
            if quantity <= 0:
                db.session.delete(cart_item)
            else:
                cart_item.quantity = quantity
        
        if 'custom_image_url' in data:
            cart_item.custom_image_url = data['custom_image_url']
        
        if 'custom_text' in data:
            cart_item.custom_text = data['custom_text']
        
        db.session.commit()
        
        if quantity <= 0:
            return jsonify({'message': 'Item removed from cart'}), 200
        else:
            return jsonify(cart_item.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/cart/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        cart_item = CartItem.query.filter_by(id=item_id, user_id=user.id).first()
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'Item removed from cart'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/cart/clear', methods=['DELETE'])
def clear_cart():
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        CartItem.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        return jsonify({'message': 'Cart cleared'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/checkout', methods=['POST'])
def checkout():
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data or not data.get('shipping_address'):
            return jsonify({'error': 'Shipping address is required'}), 400
        
        # Get cart items
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Calculate total
        total_amount = 0
        for item in cart_items:
            total_amount += item.product.price * item.quantity
        
        # Create order
        order = Order(
            user_id=user.id,
            total_amount=total_amount,
            shipping_address=data['shipping_address'],
            status='pending'
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
                custom_image_url=cart_item.custom_image_url,
                custom_text=cart_item.custom_text
            )
            db.session.add(order_item)
        
        # Clear cart
        CartItem.query.filter_by(user_id=user.id).delete()
        
        db.session.commit()
        return jsonify({
            'message': 'Order placed successfully',
            'order': order.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/orders', methods=['GET'])
def get_orders():
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).all()
        return jsonify([order.to_dict() for order in orders]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        user = require_auth()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        order = Order.query.filter_by(id=order_id, user_id=user.id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify(order.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

