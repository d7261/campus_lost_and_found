from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import joinedload # Don't forget this import from before!
from datetime import datetime, timedelta
import secrets
import os

# Import from your modular system
from models import db, User, Item, Notification, ImageEmbedding, Match
from modules.auth import auth_bp
from modules.reporting import reporting_bp
from modules.matching_simple import matching_engine
from modules.admin import admin_bp
from modules.messaging import messaging_bp
from config import Config # Import your config file

# Initialize Flask app
app = Flask(__name__)

# ✅ CORRECT: Load configuration from config.py (PostgreSQL)
app.config.from_object(Config)

# Ensure upload folder exists
# (You can also move this logic to config.py if you want, but it's fine here)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login' # Add this to handle redirects properly

# ... rest of your app.py ...

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(reporting_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(messaging_bp)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ==========================
# HELPERS
# ==========================

@app.context_processor
def utility_processor():
    def get_status_badge(item):
        """Returns label, class, and icon based on item state"""
        if item.item_status == 'claimed':
            return {'label': 'In Progress', 'class': 'info', 'icon': 'spinner', 'bg': '#e0f2fe', 'color': '#0284c7'}
        
        if item.item_type == 'lost':
            if item.item_status == 'pending':
                return {'label': 'Active Search', 'class': 'warning', 'icon': 'search', 'bg': '#fff7ed', 'color': '#c2410c'}
            elif item.item_status == 'resolved':
                return {'label': 'Recovered', 'class': 'success', 'icon': 'check-circle', 'bg': '#f0fdf4', 'color': '#15803d'}
        else: # found
            if item.item_status == 'pending':
                return {'label': 'Available', 'class': 'primary', 'icon': 'box-open', 'bg': '#ecfdf5', 'color': '#047857'}
            elif item.item_status == 'resolved':
                return {'label': 'Returned', 'class': 'secondary', 'icon': 'hand-holding-heart', 'bg': '#f1f5f9', 'color': '#475569'}
        
        # Fallback
        return {'label': item.item_status.title(), 'class': 'secondary', 'icon': 'circle', 'bg': '#f1f5f9', 'color': '#64748b'}

    return dict(get_status_badge=get_status_badge)

# ==========================
# ROUTES
# ==========================

@app.route('/')
def index():
    if current_user.is_authenticated:
        # Get some basic data for the dashboard
        recent_items = Item.query.order_by(Item.item_created_at.desc()).limit(5).all()
        user_items = Item.query.filter_by(owner_id=current_user.user_id).count()
        unread_notifications = Notification.query.filter_by(
            user_id=current_user.user_id,
            notification_is_seen=False
        ).count()
        
        return render_template('dashboard/index.html',
                              recent_items=recent_items,
                              user_items=user_items,
                              unread_notifications=unread_notifications)
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    # Get recent items
    recent_items = Item.query.order_by(Item.item_created_at.desc()).limit(10).all()
    
    # Get statistics
    total_items = Item.query.count()
    pending_items = Item.query.filter_by(item_status='pending').count()
    resolved_items = Item.query.filter_by(item_status='resolved').count()
    
    # Get user's own items
    user_items = Item.query.filter_by(owner_id=current_user.user_id).order_by(
        Item.item_created_at.desc()
    ).limit(5).all()
    
    # Get user's notifications
    user_notifications = Notification.query.filter_by(
        user_id=current_user.user_id,
        notification_is_seen=False
    ).order_by(Notification.notification_created_at.desc()).limit(5).all()
    
    return render_template('dashboard/index.html',
                          recent_items=recent_items,
                          total_items=total_items,
                          pending_items=pending_items,
                          resolved_items=resolved_items,
                          user_items=user_items,
                          user_notifications=user_notifications)
@app.route('/search')
def search():
    query = request.args.get('q', '')
    items = []
    
    if query:
        items = Item.query.filter(
            (Item.item_title.ilike(f'%{query}%')) |
            (Item.item_description.ilike(f'%{query}%')) |
            (Item.item_category.ilike(f'%{query}%')) |
            (Item.item_location.ilike(f'%{query}%'))
        ).filter_by(item_status='pending').all()
    
    return render_template('search.html', items=items, query=query)

@app.route('/notifications')
@login_required
def notifications():
    from sqlalchemy.orm import joinedload
    user_notifications = Notification.query.options(
        joinedload(Notification.item).joinedload(Item.owner)
    ).filter_by(
        user_id=current_user.user_id
    ).order_by(Notification.notification_created_at.desc()).all()

    return render_template('notifications/list.html', notifications=user_notifications)

@app.route('/notifications/mark_seen/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_seen(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    notification.notification_is_seen = True
    db.session.commit()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'success': True, 'message': 'Marked as read'})
        
    return redirect(url_for('notifications'))

@app.route('/notifications/mark_all_seen', methods=['POST'])
@login_required
def mark_all_notifications_seen():
    try:
        Notification.query.filter_by(
            user_id=current_user.user_id,
            notification_is_seen=False
        ).update({'notification_is_seen': True})

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
        
        if item.item_type != 'found':
            flash('Only found items can be claimed', 'error')
            return redirect(url_for('search'))
        
        if item.item_status != 'pending':
            flash('This item has already been claimed or resolved', 'error')
            return redirect(url_for('search'))
        
        item.item_status = 'claimed'
        
        recommended_location = recommend_location(item)
        
        # Create notification for the finder
        notification = Notification(
            notification_message=(
                f"Your found item '{item.item_title}' has been claimed by "
                f"{current_user.user_username}. 🎓 REQUIRED: Both parties must bring valid student ID. "
                f"Recommended pickup: {recommended_location}. Contact them at "
                f"{current_user.user_email} to arrange handoff."
            ),
            notification_type='item_claimed',
            user_id=item.owner_id,
            item_id=item.item_id
        )
        
        db.session.add(notification)
        db.session.commit()
        
        flash(
            f'Item claimed successfully! 🎓 REQUIRED: Bring your student ID. '
            f'Recommended pickup: {recommended_location}.',
            'success'
        )
        
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
        
        if item.owner_id != current_user.user_id:
            flash('You are not authorized to resolve this item', 'error')
            return redirect(url_for('my_items'))
        
        item.item_status = 'resolved'
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
            'icon': 'fas fa-shield-alt',
            'color': 'primary'
        },
        {
            'name': 'Main Library Help Desk',
            'building': 'Library',
            'room': 'Ground Floor, near entrance', 
            'hours': 'Mon-Fri 8AM-9PM, Sat 10AM-6PM, Sun 12PM-8PM',
            'contact': 'Circulation Desk Staff',
            'icon': 'fas fa-book',
            'color': 'success'
        },
        {
            'name': 'Cafeteria Reception Desk', 
            'building': 'Cafeteria',
            'room': 'Ground Floor, near entrance',
            'hours': 'Mon-Fri 8AM-9PM, Sat 10AM-6PM, Sun 12PM-8PM',
            'contact': 'Cafeteria Manager / Reception Staff',
            'icon': 'fas fa-utensils',
            'color': 'warning'
        }
    ]
    return render_template('campus_locations.html', locations=locations)

# Compatibility Routes
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
    item_lower = item.item_title.lower()
    
    academic_keywords = ['book', 'textbook', 'laptop', 'calculator', 'notes', 'pen', 'academic', 'research']
    if any(keyword in item_lower for keyword in academic_keywords):
        return 'Main Library Help Desk'
    
    food_keywords = ['lunch', 'bottle', 'water', 'food', 'container', 'thermos']
    if any(keyword in item_lower for keyword in food_keywords):
        return 'Cafeteria Reception Desk'
    
    valuable_keywords = ['phone', 'wallet', 'money', 'card', 'id', 'passport', 'key']
    if any(keyword in item_lower for keyword in valuable_keywords):
        return 'Main Gate Office'
    
    return 'Main Library Help Desk'

@app.route('/debug/notifications')
@login_required
def debug_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.user_id).all()
    return f"User {current_user.user_username} has {len(notifications)} notifications: {[n.notification_message for n in notifications]}"

@app.route('/item/<int:item_id>')
@login_required
def view_item(item_id):
    item = Item.query.get_or_404(item_id)
    
    is_potential_match = False
    user_items = Item.query.filter_by(owner_id=current_user.user_id).all()

    for user_item in user_items:
        # Check if types are opposite (Lost vs Found)
        if user_item.item_type != item.item_type:
            # ✅ FIX: Use the correct function name 'calculate_similarity'
            similarity_score = matching_engine.calculate_similarity(user_item, item)
            
            # ✅ FIX: Use the correct variable name 'similarity_threshold'
            if similarity_score >= matching_engine.similarity_threshold:
                is_potential_match = True
                break
    
    return render_template('item_details.html', item=item, is_potential_match=is_potential_match)

@app.route('/debug/routes')
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify(routes)
@app.route('/debug/images')
@login_required
def debug_images():
    """Debug page to check image issues"""
    import os
    from models import Item
    
    # Get all items with their image info
    items = Item.query.all()
    debug_info = []
    
    for item in items:
        image_info = {
            'item_id': item.item_id,
            'item_title': item.item_title,
            'image_path_in_db': item.item_image_path,
            'has_image': bool(item.item_image_path)
        }
        
        if item.item_image_path:
            # Check if file exists on disk
            upload_dir = app.config.get('UPLOAD_FOLDER', 'static/uploads')
            full_path = os.path.join(upload_dir, item.item_image_path)
            image_info['file_exists'] = os.path.exists(full_path)
            image_info['full_path'] = full_path
            
            if os.path.exists(full_path):
                image_info['file_size'] = os.path.getsize(full_path)
        
        debug_info.append(image_info)
    
    # Check upload directory
    upload_dir = app.config.get('UPLOAD_FOLDER', 'static/uploads')
    upload_dir_exists = os.path.exists(upload_dir)
    files_in_uploads = []
    
    if upload_dir_exists:
        files_in_uploads = os.listdir(upload_dir)
    
    return render_template('debug_images.html',
                         debug_info=debug_info,
                         upload_dir=upload_dir,
                         upload_dir_exists=upload_dir_exists,
                         files_in_uploads=files_in_uploads)
# MAIN EXEC
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Fix admin creation
        admin_user = User.query.filter_by(user_username='admin').first()
        if not admin_user:
            admin = User(
                user_username='admin',
                user_email='admin@campus.edu',
                user_role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("👑 Admin user created: admin / admin123")
        
        print("=" * 50)
        print("🎓 Campus Lost & Found Application - UNIFIED VERSION")
        print("✅ Database initialized successfully!")
        print("🌐 Running on: http://localhost:5000")
        print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
