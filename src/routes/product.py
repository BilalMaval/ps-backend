from flask import Blueprint, request, jsonify
from src.models.user import db
from src.models.product import Product
import os

product_bp = Blueprint('product', __name__)

@product_bp.route('/products', methods=['GET'])
def get_products():
    try:
        category = request.args.get('category')
        featured = request.args.get('featured')
        
        query = Product.query.filter_by(is_active=True)
        
        if category:
            query = query.filter_by(category=category)
        
        if featured and featured.lower() == 'true':
            query = query.filter_by(is_featured=True)
        
        products = query.all()
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        if not product.is_active:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(product.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_bp.route('/products', methods=['POST'])
def create_product():
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

@product_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
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

@product_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        product.is_active = False  # Soft delete
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@product_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = db.session.query(Product.category).filter_by(is_active=True).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]
        return jsonify(category_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

