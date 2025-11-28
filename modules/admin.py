from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Item, Notification, Match
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin Dashboard Overview"""
    # Statistics
    total_users = User.query.count()
    total_items = Item.query.count()
    pending_items = Item.query.filter_by(status='pending').count()
    resolved_items = Item.query.filter_by(status='resolved').count()
    total_matches = Match.query.count()
    
    # Recent activity
    recent_items = Item.query.order_by(Item.created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # System stats
    today = datetime.utcnow().date()
    items_today = Item.query.filter(Item.created_at >= today).count()
    users_today = User.query.filter(User.created_at >= today).count()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_items=total_items,
                         pending_items=pending_items,
                         resolved_items=resolved_items,
                         total_matches=total_matches,
                         recent_items=recent_items,
                         recent_users=recent_users,
                         items_today=items_today,
                         users_today=users_today)

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """Manage Users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/items')
@login_required
@admin_required
def manage_items():
    """Manage Items"""
    items = Item.query.order_by(Item.created_at.desc()).all()
    return render_template('admin/items.html', items=items)

@admin_bp.route('/admin/notifications')
@login_required
@admin_required
def manage_notifications():
    """Manage Notifications"""
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
    return render_template('admin/notifications.html', notifications=notifications)

@admin_bp.route('/admin/matches')
@login_required
@admin_required
def manage_matches():
    """Manage Matches"""
    matches = Match.query.order_by(Match.created_at.desc()).all()
    return render_template('admin/matches.html', matches=matches)

@admin_bp.route('/admin/user/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    """Toggle user status (for future use)"""
    user = User.query.get_or_404(user_id)
    flash(f'User {user.username} status updated.', 'info')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/item/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_item(item_id):
    """Delete an item and all related data"""
    try:
        item = Item.query.get_or_404(item_id)
        
        # Delete related image embeddings first (if they exist)
        if hasattr(item, 'embedding') and item.embedding:
            db.session.delete(item.embedding)
        
        # Delete related notifications
        Notification.query.filter_by(item_id=item_id).delete()
        
        # Delete the item itself
        db.session.delete(item)
        db.session.commit()
        
        # Also delete the image file from filesystem if it exists
        try:
            if item.image_path:
                import os
                image_path = os.path.join('static', 'uploads', item.image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
        except Exception as e:
            print(f"Warning: Could not delete image file: {e}")
        
        flash('Item deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'error')
        print(f"Error deleting item: {e}")
    
    return redirect(url_for('admin.manage_items'))

@admin_bp.route('/admin/notification/<int:notification_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_notification(notification_id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(notification_id)
    db.session.delete(notification)
    db.session.commit()
    
    flash('Notification deleted successfully.', 'success')
    return redirect(url_for('admin.manage_notifications'))

@admin_bp.route('/admin/stats')
@login_required
@admin_required
def system_stats():
    """System Statistics"""
    # Get total items first
    total_items = Item.query.count()
    
    # User growth (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    user_growth = User.query.filter(User.created_at >= seven_days_ago).count()
    
    # Item statistics by type
    lost_items = Item.query.filter_by(type='lost').count()
    found_items = Item.query.filter_by(type='found').count()
    
    # Category distribution
    categories = db.session.query(Item.category, db.func.count(Item.id)).group_by(Item.category).all()
    
    # Resolution rate
    total_resolved = Item.query.filter_by(status='resolved').count()
    resolution_rate = (total_resolved / total_items * 100) if total_items > 0 else 0
    
    return render_template('admin/stats.html',
                         total_items=total_items,  # Add this
                         user_growth=user_growth,
                         lost_items=lost_items,
                         found_items=found_items,
                         categories=categories,
                         resolution_rate=resolution_rate)
    
@admin_bp.route('/admin/user/<int:user_id>')
@login_required
@admin_required
def view_user(user_id):
    """View user profile and details"""
    user = User.query.get_or_404(user_id)
    
    # Get user statistics
    user_items = Item.query.filter_by(user_id=user_id).all()
    lost_items = [item for item in user_items if item.type == 'lost']
    found_items = [item for item in user_items if item.type == 'found']
    pending_items = [item for item in user_items if item.status == 'pending']
    resolved_items = [item for item in user_items if item.status == 'resolved']
    
    # Get user notifications
    user_notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(10).all()
    
    return render_template('admin/user_profile.html',
                         user=user,
                         user_items=user_items,
                         lost_items=lost_items,
                         found_items=found_items,
                         pending_items=pending_items,
                         resolved_items=resolved_items,
                         user_notifications=user_notifications)
    
@admin_bp.route('/admin/item/<int:item_id>')
@login_required
@admin_required
def view_item(item_id):
    """View item details"""
    item = Item.query.get_or_404(item_id)
    
    # Get related notifications for this item
    item_notifications = Notification.query.filter_by(item_id=item_id).order_by(Notification.created_at.desc()).all()
    
    # Get potential matches (if any)
    matches_as_lost = Match.query.filter_by(lost_item_id=item_id).all()
    matches_as_found = Match.query.filter_by(found_item_id=item_id).all()
    all_matches = matches_as_lost + matches_as_found
    
    return render_template('admin/item_details.html',
                         item=item,
                         item_notifications=item_notifications,
                         all_matches=all_matches)