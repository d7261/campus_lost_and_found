from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Item, Notification
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from modules.matching_simple import matching_engine

# Import conditionally based on AI_ENABLED
try:
    from modules.ai_processing import image_engine
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️ AI module not available. Image matching disabled.")

reporting_bp = Blueprint('reporting', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_form_data(data):
    """Validate form data and return errors"""
    errors = []
    
    # Required fields
    required_fields = ['type', 'category', 'title', 'description', 'location', 'date_lost_found']
    for field in required_fields:
        if not data.get(field) or not data.get(field).strip():
            errors.append(f"{field.replace('_', ' ').title()} is required")
    
    # Field length validation
    if len(data.get('title', '')) > 200:
        errors.append("Title must be less than 200 characters")
    
    if len(data.get('description', '')) > 1000:
        errors.append("Description must be less than 1000 characters")
    
    if len(data.get('location', '')) > 200:
        errors.append("Location must be less than 200 characters")
    
    # Date validation
    try:
        date_obj = datetime.strptime(data.get('date_lost_found', ''), '%Y-%m-%d')
        if date_obj > datetime.utcnow():
            errors.append("Date cannot be in the future")
        if date_obj.year == 2015:  # Fix for the 2015 bug
            errors.append("Please check the date (2015 detected)")
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD")
    
    return errors

@reporting_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_item():
    if request.method == 'POST':
        try:
            # Collect form data
            form_data = {
                'type': request.form.get('type'),
                'category': request.form.get('category'),
                'title': request.form.get('title', '').strip(),
                'description': request.form.get('description', '').strip(),
                'location': request.form.get('location', '').strip(),
                'date_lost_found': request.form.get('date_lost_found'),
            }
            
            # Validate form data
            validation_errors = validate_form_data(form_data)
            if validation_errors:
                for error in validation_errors:
                    flash(error, 'error')
                return render_template('reporting/report.html')
            
            # Parse date (already validated)
            date_obj = datetime.strptime(form_data['date_lost_found'], '%Y-%m-%d')
            
            # Check if AI is enabled in config
            ai_enabled = current_app.config.get('AI_ENABLED', False) and AI_AVAILABLE
            
            # Start database transaction
            new_item = Item(
                type=form_data['type'],
                category=form_data['category'],
                title=form_data['title'],
                description=form_data['description'],
                location=form_data['location'],
                date_lost_found=date_obj,
                user_id=current_user.id,
                status='pending'
            )
            
            db.session.add(new_item)
            db.session.flush()  # Get ID without committing
            
            # Process image if provided
            image_file = request.files.get('image')
            image_processed = False
            image_matches = []
            
            if image_file and image_file.filename:
                # Validate file
                if not allowed_file(image_file.filename):
                    flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, WEBP', 'error')
                    return render_template('reporting/report.html')
                
                # Check file size
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    flash(f'File too large. Maximum size is {MAX_FILE_SIZE//1024//1024}MB', 'error')
                    return render_template('reporting/report.html')
                
                # Save image
                try:
                    filename = secure_filename(f"{new_item.id}_{image_file.filename}")
                    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, filename)
                    
                    image_file.save(filepath)
                    new_item.image_path = filename
                    image_processed = True
                    
                    # Process with AI if enabled
                    if ai_enabled:
                        try:
                            # Reset file pointer for AI processing
                            with open(filepath, 'rb') as f:
                                image_matches = image_engine.process_new_item(new_item.id, f)
                                print(f"✅ AI processed image. Found {len(image_matches)} visual matches")
                        except Exception as ai_error:
                            print(f"⚠️ AI processing error: {ai_error}")
                            # Continue without AI - not critical
                    
                except Exception as e:
                    print(f"❌ Image save error: {e}")
                    flash('Item saved, but image upload failed', 'warning')
            
            # Commit the item to database
            db.session.commit()
            
            # ===== TEXT-BASED MATCHING =====
            text_matches_count = 0
            try:
                text_matches_count = matching_engine.find_potential_matches(new_item)
                print(f"✅ Text matching found {text_matches_count} matches")
            except Exception as e:
                print(f"⚠️ Text matching error: {e}")
            
            # ===== PROCESS IMAGE MATCHES (if any) =====
            image_notifications = 0
            if image_matches and ai_enabled:
                for match in image_matches:
                    matched_item = match['item']
                    similarity = match['similarity']
                    
                    # Skip if same user
                    if matched_item.user_id == current_user.id:
                        continue
                    
                    # Determine notification details
                    if new_item.type == 'lost' and matched_item.type == 'found':
                        # User lost item, found a match in found items
                        notification_user_id = current_user.id
                        message = f"📸 Visual match found! We found an item that looks like your lost '{new_item.title}'. Similarity: {similarity:.1%}"
                        linked_item_id = matched_item.id
                        
                    elif new_item.type == 'found' and matched_item.type == 'lost':
                        # User found item, found a match in lost items
                        notification_user_id = matched_item.user_id
                        message = f"📸 Visual match found! Someone found an item that looks like your lost '{matched_item.title}'. Similarity: {similarity:.1%}"
                        linked_item_id = new_item.id
                    else:
                        # Same type, skip
                        continue
                    
                    # Create notification
                    notification = Notification(
                        message=message,
                        notification_type='visual_match',
                        user_id=notification_user_id,
                        item_id=linked_item_id
                    )
                    db.session.add(notification)
                    image_notifications += 1
                
                if image_notifications > 0:
                    db.session.commit()
            
            # ===== FINAL FEEDBACK =====
            if text_matches_count > 0 and image_notifications > 0:
                flash(f'✅ Item reported! Found {text_matches_count} text matches and {image_notifications} visual matches!', 'success')
            elif text_matches_count > 0:
                flash(f'✅ Item reported! Found {text_matches_count} potential matches.', 'success')
            elif image_notifications > 0:
                flash(f'✅ Item reported! Found {image_notifications} visual matches.', 'success')
            elif image_processed:
                flash('✅ Item reported with image! We will notify you of any matches.', 'success')
            else:
                flash('✅ Item reported! We will notify you of any matches.', 'success')
            
            return redirect(url_for('reporting.my_items'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Critical error in report_item: {e}")
            flash(f'Error reporting item: {str(e)[:100]}', 'error')
            return render_template('reporting/report.html')
    
    return render_template('reporting/report.html')

@reporting_bp.route('/my-items')
@login_required
def my_items():
    """Display user's reported items"""
    try:
        user_items = Item.query.filter_by(
            user_id=current_user.id
        ).order_by(
            Item.created_at.desc()
        ).all()
        
        # Organize by status
        items_by_status = {
            'pending': [],
            'claimed': [],
            'resolved': []
        }
        
        for item in user_items:
            items_by_status[item.status].append(item)
        
        return render_template('reporting/my_items.html',
                             items=user_items,
                             items_by_status=items_by_status)
        
    except Exception as e:
        flash(f'Error loading your items: {str(e)}', 'error')
        return render_template('reporting/my_items.html', items=[])

@reporting_bp.route('/item/<int:item_id>/update-status', methods=['POST'])
@login_required
def update_item_status(item_id):
    """Update item status (e.g., mark as resolved)"""
    try:
        item = Item.query.get_or_404(item_id)
        
        # Check ownership
        if item.user_id != current_user.id:
            flash('You can only update your own items', 'error')
            return redirect(url_for('reporting.my_items'))
        
        new_status = request.form.get('status')
        valid_statuses = ['pending', 'claimed', 'resolved']
        
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('reporting.my_items'))
        
        old_status = item.status
        item.status = new_status
        
        # Create notification if marked as resolved
        if new_status == 'resolved' and old_status != 'resolved':
            notification = Notification(
                user_id=item.user_id,
                item_id=item.id,
                message=f"Your item '{item.title}' has been marked as resolved",
                notification_type='item_resolved'
            )
            db.session.add(notification)
        
        db.session.commit()
        
        if old_status != new_status:
            flash(f'Item status updated to {new_status}', 'success')
        
        return redirect(url_for('reporting.my_items'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating item: {str(e)}', 'error')
        return redirect(url_for('reporting.my_items'))

@reporting_bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing item"""
    item = Item.query.get_or_404(item_id)
    
    # Check ownership
    if item.user_id != current_user.id:
        flash('You can only edit your own items', 'error')
        return redirect(url_for('reporting.my_items'))
    
    if request.method == 'POST':
        try:
            # Update fields
            item.title = request.form.get('title', item.title).strip()
            item.description = request.form.get('description', item.description).strip()
            item.location = request.form.get('location', item.location).strip()
            item.category = request.form.get('category', item.category)
            
            # Handle new image
            image_file = request.files.get('image')
            if image_file and image_file.filename and allowed_file(image_file.filename):
                # Delete old image if exists
                if item.image_path:
                    old_path = os.path.join(
                        current_app.config.get('UPLOAD_FOLDER', 'static/uploads'),
                        item.image_path
                    )
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Save new image
                filename = secure_filename(f"{item.id}_{image_file.filename}")
                upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                
                image_file.save(filepath)
                item.image_path = filename
            
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('reporting.my_items'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'error')
    
    return render_template('reporting/edit_item.html', item=item)