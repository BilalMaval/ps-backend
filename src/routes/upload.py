from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
import io

upload_bp = Blueprint('upload', __name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    """Create upload folder if it doesn't exist"""
    upload_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', UPLOAD_FOLDER)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path

def resize_image(image_data, max_width=1200, max_height=1200, quality=85):
    """Resize image while maintaining aspect ratio"""
    try:
        image = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Calculate new dimensions
        width, height = image.size
        if width > max_width or height > max_height:
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()
    except Exception as e:
        print(f"Error resizing image: {e}")
        return image_data

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 16MB'}), 400
        
        if file and allowed_file(file.filename):
            # Create upload folder
            upload_path = create_upload_folder()
            
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Read and process image
            file_data = file.read()
            
            # Resize image if it's too large
            if file_extension in ['jpg', 'jpeg', 'png', 'webp']:
                file_data = resize_image(file_data)
                unique_filename = f"{uuid.uuid4().hex}.jpg"  # Convert to JPEG
            
            # Save file
            file_path = os.path.join(upload_path, unique_filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Return URL relative to static folder
            file_url = f"/{UPLOAD_FOLDER}/{unique_filename}"
            
            return jsonify({
                'success': True,
                'filename': unique_filename,
                'url': file_url,
                'size': len(file_data)
            }), 200
        
        return jsonify({'error': 'Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, WEBP'}), 400
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@upload_bp.route('/upload/multiple', methods=['POST'])
def upload_multiple_files():
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # Check file size
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    errors.append(f'{file.filename}: File too large')
                    continue
                
                if allowed_file(file.filename):
                    # Create upload folder
                    upload_path = create_upload_folder()
                    
                    # Generate unique filename
                    file_extension = file.filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
                    
                    # Read and process image
                    file_data = file.read()
                    
                    # Resize image if it's too large
                    if file_extension in ['jpg', 'jpeg', 'png', 'webp']:
                        file_data = resize_image(file_data)
                        unique_filename = f"{uuid.uuid4().hex}.jpg"  # Convert to JPEG
                    
                    # Save file
                    file_path = os.path.join(upload_path, unique_filename)
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    
                    # Return URL relative to static folder
                    file_url = f"/{UPLOAD_FOLDER}/{unique_filename}"
                    
                    uploaded_files.append({
                        'original_name': file.filename,
                        'filename': unique_filename,
                        'url': file_url,
                        'size': len(file_data)
                    })
                else:
                    errors.append(f'{file.filename}: Invalid file type')
                    
            except Exception as e:
                errors.append(f'{file.filename}: {str(e)}')
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'errors': errors
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@upload_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Secure the filename
        secure_name = secure_filename(filename)
        upload_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', UPLOAD_FOLDER)
        file_path = os.path.join(upload_path, secure_name)
        
        # Check if file exists and delete it
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True, 'message': 'File deleted successfully'}), 200
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

