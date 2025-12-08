from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    user_username = db.Column(db.String(80), unique=True, nullable=False)
    user_email = db.Column(db.String(120), unique=True, nullable=False)
    user_password_hash = db.Column(db.String(128), nullable=False)
    user_role = db.Column(db.String(20), default='student')
    user_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships (these stay the same)
    items = db.relationship('Item', backref='owner', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    # Flask-Login requires get_id() to return the primary key as string
    def get_id(self):
        return str(self.user_id)
    
    def set_password(self, password):
        self.user_password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.user_password_hash.encode('utf-8'))

class Item(db.Model):
    __tablename__ = 'items'
    
    item_id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(20), nullable=False)  # 'lost' or 'found'
    item_category = db.Column(db.String(100), nullable=False)
    item_title = db.Column(db.String(200), nullable=False)
    item_description = db.Column(db.Text, nullable=False)
    item_location = db.Column(db.String(200), nullable=False)
    item_date_lost_found = db.Column(db.DateTime, nullable=False)
    item_image_path = db.Column(db.String(300))
    item_status = db.Column(db.String(20), default='pending')  # 'pending', 'claimed', 'resolved'
    item_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign key with new column name
    owner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    
    # Relationships
    embedding = db.relationship('ImageEmbedding', backref='item', uselist=False, lazy=True)
    notifications = db.relationship('Notification', backref='item', lazy=True)

class ImageEmbedding(db.Model):
    __tablename__ = 'image_embeddings'
    
    image_embedding_id = db.Column(db.Integer, primary_key=True)
    image_embedding_data = db.Column(db.LargeBinary, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), unique=True, nullable=False)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    notification_id = db.Column(db.Integer, primary_key=True)
    notification_message = db.Column(db.Text, nullable=False)
    notification_is_seen = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'potential_match', 'visual_match', etc.
    notification_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys with new column names
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)

class Match(db.Model):
    __tablename__ = 'matches'
    
    match_id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)
    match_similarity_score = db.Column(db.Float, nullable=False)
    match_status = db.Column(db.String(20), default='pending')  # 'pending', 'confirmed', 'rejected'
    match_created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    lost_item = db.relationship('Item', foreign_keys=[lost_item_id])
    found_item = db.relationship('Item', foreign_keys=[found_item_id])