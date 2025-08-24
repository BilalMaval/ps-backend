import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.product import product_bp
from src.routes.cart import cart_bp
from src.routes.admin import admin_bp
# from src.routes.upload import upload_bp  # Temporarily disabled for deployment

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(product_bp, url_prefix='/api')
app.register_blueprint(cart_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
# app.register_blueprint(upload_bp, url_prefix='/api')  # Temporarily disabled for deployment

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create tables and add sample data
with app.app_context():
    db.create_all()
    
    # Import models after db initialization
    from src.models.user import User
    from src.models.product import Product
    
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@petnicstudio.com',
            first_name='Admin',
            last_name='User',
            is_admin=True
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
    
    # Add sample products if none exist
    if Product.query.count() == 0:
        sample_products = [
            {
                'name': 'Custom Pet T-Shirt',
                'description': 'High-quality cotton t-shirt with your pet\'s custom portrait',
                'price': 29.99,
                'category': 'apparel',
                'image_url': '/assets/sample-tshirt.jpg',
                'stock_quantity': 100,
                'is_featured': True
            },
            {
                'name': 'Pet Portrait Mug',
                'description': 'Ceramic mug featuring your pet\'s beautiful portrait',
                'price': 19.99,
                'category': 'drinkware',
                'image_url': '/assets/sample-mug.jpg',
                'stock_quantity': 50,
                'is_featured': True
            },
            {
                'name': 'Canvas Pet Print',
                'description': 'Premium canvas print of your pet in artistic style',
                'price': 49.99,
                'category': 'prints',
                'image_url': '/assets/sample-canvas.jpg',
                'stock_quantity': 25,
                'is_featured': True
            },
            {
                'name': 'Pet Phone Case',
                'description': 'Protective phone case with your pet\'s photo',
                'price': 24.99,
                'category': 'accessories',
                'image_url': '/assets/sample-phonecase.jpg',
                'stock_quantity': 75,
                'is_featured': False
            },
            {
                'name': 'Pet Pillow',
                'description': 'Soft pillow featuring your beloved pet',
                'price': 34.99,
                'category': 'home',
                'image_url': '/assets/sample-pillow.jpg',
                'stock_quantity': 30,
                'is_featured': False
            }
        ]
        
        for product_data in sample_products:
            product = Product(**product_data)
            db.session.add(product)
    
    db.session.commit()

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
