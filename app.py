from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import secrets
import os

# Import from your modular system
from models import db, User, Item, Notification, ImageEmbedding, Match
from modules.auth import auth_bp
from modules.reporting import reporting_bp
from modules.matching_simple import matching_engine
from modules.admin import admin_bp

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'campus-lost-found-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

import os

# Ensure upload folder exists
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
# Register Blueprints WITHOUT name parameter
app.register_blueprint(auth_bp)
app.register_blueprint(reporting_bp)
app.register_blueprint(admin_bp)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Fixed SQLAlchemy 2.0 warning

# ... rest of your app.py routes remain the same ...

# ===== ROUTES THAT STAY IN APP.PY =====

@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('dashboard/index.html')
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard/index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    items = []
    
    if query:
        items = Item.query.filter(
            (Item.title.ilike(f'%{query}%')) |
            (Item.description.ilike(f'%{query}%')) |
            (Item.category.ilike(f'%{query}%')) |
            (Item.location.ilike(f'%{query}%'))
        ).filter_by(status='pending').all()
    
    return render_template('search.html', items=items, query=query)

@app.route('/notifications')
@login_required
def notifications():
    from sqlalchemy.orm import joinedload
    user_notifications = Notification.query.options(
        joinedload(Notification.item).joinedload(Item.owner)
    ).filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/list.html', notifications=user_notifications)
@app.route('/notifications/mark_seen/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_seen(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.is_seen = True
    db.session.commit()
    
    return redirect(url_for('notifications'))

@app.route('/notifications/mark_all_seen', methods=['POST'])
@login_required
def mark_all_notifications_seen():
    try:
        Notification.query.filter_by(user_id=current_user.id, is_seen=False).update(
            {'is_seen': True}
        )
        db.session.commit()
        flash('All notifications marked as read', 'success')
    except Exception as e:
        flash('Error marking notifications as read', 'error')
        print(f"Error marking all notifications as read: {e}")
    
    return redirect(url_for('notifications'))

@app.route('/item/<int:item_id>/claim', methods=['POST'])
@login_required
def claim_item(item_id):
    """Claim a found item as yours"""
    try:
        item = Item.query.get_or_404(item_id)
        
        if item.type != 'found':
            flash('Only found items can be claimed', 'error')
            return redirect(url_for('search'))
        
        if item.status != 'pending':
            flash('This item has already been claimed or resolved', 'error')
            return redirect(url_for('search'))
        
        item.status = 'claimed'
        
        # Get recommended location
        recommended_location = recommend_location(item)
        
        # Create notification for the finder
        notification = Notification(
            message=f"Your found item '{item.title}' has been claimed by {current_user.username}. 🎓 REQUIRED: Both parties must bring valid student ID. Recommended pickup: {recommended_location}. Contact them at {current_user.email} to arrange handoff.",
            notification_type='item_claimed',
            user_id=item.user_id,
            item_id=item.id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash(f'Item claimed successfully! 🎓 REQUIRED: Bring your student ID. Recommended pickup: {recommended_location}. Check your items page for details.', 'success')
        
    except Exception as e:
        flash('Error claiming item', 'error')
        print(f"Error claiming item: {e}")
        db.session.rollback()
    
    return redirect(url_for('my_items'))
@app.route('/item/<int:item_id>/resolve', methods=['POST'])
@login_required
def resolve_item(item_id):
    """Mark an item as resolved"""
    try:
        item = Item.query.get_or_404(item_id)
        
        if item.user_id != current_user.id:
            flash('You are not authorized to resolve this item', 'error')
            return redirect(url_for('my_items'))
        
        item.status = 'resolved'
        db.session.commit()
        
        flash('Item marked as resolved!', 'success')
        
    except Exception as e:
        flash('Error resolving item', 'error')
        print(f"Error resolving item: {e}")
        db.session.rollback()
    
    return redirect(url_for('my_items'))

@app.route('/campus_locations')
def campus_locations():
    """Display campus pickup locations with detailed information"""
    locations = [
        {
            'name': 'Main Gate Office',
            'building': 'Main Gate',
            'room': 'Office', 
            'hours': 'Mon-Fri 8AM-9PM, Sat-Sun 10AM-6PM',
            'contact': 'Security Officer / Gate Attendant',
            'phone': 'x1001',
            'specialties': 'General items, access cards, small personal belongings',
            'notes': 'First point of contact for items found near campus entrance. Available for after-hours coordination.',
            'icon': 'fas fa-shield-alt',
            'color': 'primary'
        },
        {
            'name': 'Main Library Help Desk',
            'building': 'Library',
            'room': 'Ground Floor, near entrance', 
            'hours': 'Mon-Fri 8AM-9PM, Sat 10AM-6PM, Sun 12PM-8PM',
            'contact': 'Circulation Desk Staff',
            'phone': 'x2001',
            'specialties': 'Textbooks, laptops, academic materials, research items, calculators',
            'notes': 'Ideal for academic items. Bring student ID for verification. Most convenient location for students.',
            'icon': 'fas fa-book',
            'color': 'success'
        },
        {
            'name': 'Cafeteria Reception Desk', 
            'building': 'Cafeteria',
            'room': 'Ground Floor, near entrance',
            'hours': 'Mon-Fri 8AM-9PM, Sat 10AM-6PM, Sun 12PM-8PM',
            'contact': 'Cafeteria Manager / Reception Staff',
            'phone': 'x3001',
            'specialties': 'Lunch boxes, water bottles, clothing items, small bags, accessories',
            'notes': 'High-traffic location. Perfect for items commonly lost during meal times.',
            'icon': 'fas fa-utensils',
            'color': 'warning'
        }
    ]
    return render_template('campus_locations.html', locations=locations)@app.route('/forgot-password', methods=['GET', 'POST'])



# TEMPORARY COMPATIBILITY ROUTES - Add this to your app.py
@app.route('/report')
@login_required
def report():
    return redirect(url_for('reporting.report_item'))

@app.route('/my-items')
@login_required 
def my_items():
    return redirect(url_for('reporting.my_items'))


def recommend_location(item):
    """Recommend the best campus location based on item type"""
    item_lower = item.title.lower()
    
    # Academic items -> Library
    academic_keywords = ['book', 'textbook', 'laptop', 'calculator', 'notes', 'pen', 'academic', 'research']
    if any(keyword in item_lower for keyword in academic_keywords):
        return 'Main Library Help Desk'
    
    # Food-related items -> Cafeteria  
    food_keywords = ['lunch', 'bottle', 'water', 'food', 'container', 'thermos']
    if any(keyword in item_lower for keyword in food_keywords):
        return 'Cafeteria Reception Desk'
    
    # Valuable items -> Main Gate (most secure)
    valuable_keywords = ['phone', 'wallet', 'money', 'card', 'id', 'passport', 'key']
    if any(keyword in item_lower for keyword in valuable_keywords):
        return 'Main Gate Office'
    
    # Default to Library (most convenient for students)
    return 'Main Library Help Desk'

# Add this temporary debug route to app.py
@app.route('/debug/notifications')
@login_required
def debug_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).all()
    return f"User {current_user.username} has {len(notifications)} notifications: {[n.message for n in notifications]}"

@app.route('/item/<int:item_id>')
@login_required
def view_item(item_id):
    """View detailed information about a specific item"""
    item = Item.query.get_or_404(item_id)
    
    # Check if this is a potential match for the current user's items
    is_potential_match = False
    user_items = Item.query.filter_by(user_id=current_user.id).all()
    for user_item in user_items:
        if user_item.type != item.type:  # One is lost, other is found
            similarity_score = matching_engine.calculate_text_similarity(user_item, item)
            if similarity_score >= matching_engine.text_threshold:
                is_potential_match = True
                break
    
    return render_template('item_details.html', 
                         item=item, 
                         is_potential_match=is_potential_match)
# ===== MAIN EXECUTION =====
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(username='admin', email='admin@campus.edu', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("👑 Admin user created: admin / admin123")
        
        print("=" * 50)
        print("🎓 Campus Lost & Found Application - UNIFIED VERSION")
        print("✅ Database initialized successfully!")
        print("✅ Modular system integrated!")
        print("✅ Matching engine activated!")
        print("🌐 Running on: http://localhost:5000")
        print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)