import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-this-in-production'
    
    # PostgreSQL configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://campus_user:secure_password123@localhost:5432/campus_lost_found'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Image upload settings (disabled for now)
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Disable AI features for now
    AI_ENABLED = True