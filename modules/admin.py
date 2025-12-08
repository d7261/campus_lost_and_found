from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Item, Notification, Match
from datetime import datetime, timedelta
import os
from fpdf import FPDF
from flask import make_response

admin_bp = Blueprint('admin', __name__)

# Admin required decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_role != 'admin':
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
    pending_items = Item.query.filter_by(item_status='pending').count()
    resolved_items = Item.query.filter_by(item_status='resolved').count()
    total_matches = Match.query.count()
    
    # Recent activity - FIXED: Use item_created_at / user_created_at
    recent_items = Item.query.order_by(Item.item_created_at.desc()).limit(10).all()
    recent_users = User.query.order_by(User.user_created_at.desc()).limit(5).all()
    
    # System stats
    today = datetime.utcnow().date()
    # FIXED: Use item_created_at / user_created_at
    items_today = Item.query.filter(Item.item_created_at >= str(today)).count()
    users_today = User.query.filter(User.user_created_at >= str(today)).count()
    
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
    # FIXED: Use user_created_at
    users = User.query.order_by(User.user_created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/items')
@login_required
@admin_required
def manage_items():
    """Manage Items"""
    # FIXED: Use item_created_at
    items = Item.query.order_by(Item.item_created_at.desc()).all()
    return render_template('admin/items.html', items=items)

@admin_bp.route('/admin/notifications')
@login_required
@admin_required
def manage_notifications():
    """Manage Notifications"""
    # FIXED: Use notification_created_at
    notifications = Notification.query.order_by(Notification.notification_created_at.desc()).limit(100).all()
    return render_template('admin/notifications.html', notifications=notifications)

@admin_bp.route('/admin/matches')
@login_required
@admin_required
def manage_matches():
    """Manage Matches"""
    # FIXED: Use match_created_at
    matches = Match.query.order_by(Match.match_created_at.desc()).all()
    return render_template('admin/matches.html', matches=matches)

@admin_bp.route('/admin/user/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    """Toggle user status (for future use)"""
    user = User.query.get_or_404(user_id)
    flash(f'User {user.user_username} status updated.', 'info')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/admin/item/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_item(item_id):
    """Delete an item and all related data"""
    try:
        item = Item.query.get_or_404(item_id)
        
        # Delete related embeddings if they exist
        if hasattr(item, 'embedding') and item.embedding:
            db.session.delete(item.embedding)
        
        # Delete related notifications
        Notification.query.filter_by(item_id=item_id).delete()
        
        # Delete image file - FIXED: Use item_image_path
        if item.item_image_path:
            try:
                # Assuming app.config['UPLOAD_FOLDER'] is set, otherwise hardcode 'static/uploads'
                image_path = os.path.join('static', 'uploads', item.item_image_path)
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                print(f"Warning: Could not delete image file: {e}")
        
        # Delete item
        db.session.delete(item)
        db.session.commit()
        
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
    total_items = Item.query.count()
    
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    # FIXED: Use user_created_at
    user_growth = User.query.filter(User.user_created_at >= seven_days_ago).count()
    
    lost_items = Item.query.filter_by(item_type='lost').count()
    found_items = Item.query.filter_by(item_type='found').count()
    
    # Categories stats
    categories = db.session.query(
        Item.item_category, db.func.count(Item.item_id)
    ).group_by(Item.item_category).all()
    
    total_resolved = Item.query.filter_by(item_status='resolved').count()
    resolution_rate = (total_resolved / total_items * 100) if total_items > 0 else 0
    
    return render_template('admin/stats.html',
                         total_items=total_items,
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
    
    # FIXED: Use owner_id instead of user_id for items
    user_items = Item.query.filter_by(owner_id=user_id).all()
    
    lost_items = [i for i in user_items if i.item_type == 'lost']
    found_items = [i for i in user_items if i.item_type == 'found']
    pending_items = [i for i in user_items if i.item_status == 'pending']
    resolved_items = [i for i in user_items if i.item_status == 'resolved']
    
    # FIXED: Use notification_created_at
    user_notifications = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.notification_created_at.desc()).limit(10).all()
    
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
    
    # FIXED: Use notification_created_at
    item_notifications = Notification.query.filter_by(item_id=item_id)\
        .order_by(Notification.notification_created_at.desc()).all()
    
    matches_as_lost = Match.query.filter_by(lost_item_id=item_id).all()
    matches_as_found = Match.query.filter_by(found_item_id=item_id).all()
    all_matches = matches_as_lost + matches_as_found
    
    return render_template('admin/item_details.html',
                         item=item,
                         item_notifications=item_notifications,
                         all_matches=all_matches)
    
@admin_bp.route('/download-report')
@login_required
@admin_required
def download_system_report():
    try:
        # --- Gather Data ---
        total_users = User.query.count()
        total_items = Item.query.count()
        lost_count = Item.query.filter_by(item_type='lost').count()
        found_count = Item.query.filter_by(item_type='found').count()
        resolved_count = Item.query.filter_by(item_status='resolved').count()
        matches_count = Match.query.count()
        
        # Get last 50 items for the log
        recent_items = Item.query.order_by(Item.item_created_at.desc()).limit(50).all()

        # --- PDF Class definition ---
        class AdminPDF(FPDF):
            def header(self):
                # Brand Header (Emerald Green)
                self.set_fill_color(16, 185, 129)
                self.rect(0, 0, 210, 40, 'F')
                
                # Title
                self.set_font('Helvetica', 'B', 24)
                self.set_text_color(255, 255, 255)
                self.set_y(15)
                self.cell(0, 10, 'Campus Lost & Found', 0, 1, 'C')
                
                # Subtitle
                self.set_font('Helvetica', '', 12)
                self.cell(0, 10, 'System Administration Report', 0, 1, 'C')
                self.ln(25)

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 10, f'Confidential - Admin Only | Page {self.page_no()}', 0, 0, 'C')

        # --- Generate PDF ---
        pdf = AdminPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Helper to clean text
        def clean(text):
            if not text: return ""
            return text.encode('latin-1', 'ignore').decode('latin-1').strip()

        # 1. System Overview Section
        pdf.set_text_color(50, 50, 50)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'System Overview', 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Underline
        pdf.ln(5)

        # Stats Grid Logic
        pdf.set_font('Arial', '', 11)
        
        # Row 1
        pdf.cell(95, 10, f"Generated By: {clean(current_user.user_username)}", 0, 0)
        pdf.cell(95, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        
        # Row 2 (Stats)
        pdf.set_font('Arial', 'B', 11)
        pdf.ln(5)
        pdf.cell(63, 10, f"Total Users: {total_users}", 1, 0, 'C')
        pdf.cell(63, 10, f"Total Items: {total_items}", 1, 0, 'C')
        pdf.cell(63, 10, f"Total Matches: {matches_count}", 1, 1, 'C')
        
        # Row 3 (Breakdown)
        pdf.cell(63, 10, f"Lost Items: {lost_count}", 1, 0, 'C')
        pdf.cell(63, 10, f"Found Items: {found_count}", 1, 0, 'C')
        pdf.cell(63, 10, f"Resolved Cases: {resolved_count}", 1, 1, 'C')
        pdf.ln(15)

        # 2. Recent Activity Log
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Recent Item Activity (Last 50)', 0, 1)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

        # Table Header
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(240, 240, 240)
        pdf.set_draw_color(200, 200, 200)
        
        # Columns: ID(15), Title(60), Type(20), Owner(35), Status(25), Date(35)
        pdf.cell(15, 10, 'ID', 1, 0, 'C', 1)
        pdf.cell(60, 10, 'Item Title', 1, 0, 'L', 1)
        pdf.cell(20, 10, 'Type', 1, 0, 'C', 1)
        pdf.cell(35, 10, 'Reported By', 1, 0, 'L', 1)
        pdf.cell(25, 10, 'Status', 1, 0, 'C', 1)
        pdf.cell(35, 10, 'Date', 1, 1, 'C', 1)

        # Table Rows
        pdf.set_font('Arial', '', 8)
        fill = False

        for item in recent_items:
            if fill:
                pdf.set_fill_color(245, 255, 250) # Mint cream
            else:
                pdf.set_fill_color(255, 255, 255)

            title = clean(item.item_title)
            if len(title) > 30: title = title[:27] + "..."
            
            owner = clean(item.owner.user_username)
            if len(owner) > 18: owner = owner[:15] + "..."

            pdf.cell(15, 10, str(item.item_id), 1, 0, 'C', 1)
            pdf.cell(60, 10, title, 1, 0, 'L', 1)
            pdf.cell(20, 10, item.item_type.upper(), 1, 0, 'C', 1)
            pdf.cell(35, 10, owner, 1, 0, 'L', 1)
            pdf.cell(25, 10, item.item_status.title(), 1, 0, 'C', 1)
            pdf.cell(35, 10, item.item_created_at.strftime('%Y-%m-%d'), 1, 1, 'C', 1)
            
            fill = not fill

        # Output
        response = make_response(pdf.output(dest='S').encode('latin-1', 'replace'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Admin_System_Report_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response

    except Exception as e:
        print(f"Error generating Admin PDF: {e}")
        flash(f"Error generating report: {str(e)}", "error")
        return redirect(url_for('admin.admin_dashboard'))