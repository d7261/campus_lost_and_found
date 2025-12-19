from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, make_response
from flask_login import login_required, current_user
from models import db, Item, Notification, Category, CampusLocation
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from modules.matching_simple import matching_engine
from fpdf import FPDF

# Import conditionally based on AI_ENABLED
try:
    from modules.ai_processing import image_engine
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️ Visual module not available. Image matching disabled.")

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
    # Fetch categories and locations from DB
    categories = Category.query.filter_by(category_is_active=True).all()
    locations = CampusLocation.query.filter_by(location_is_active=True).all()

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
                return render_template('reporting/report.html', categories=categories, locations=locations)
            
            # Parse date
            date_obj = datetime.strptime(form_data['date_lost_found'], '%Y-%m-%d')
            
            # Check if Visual Processing is enabled in config
            ai_enabled = current_app.config.get('AI_ENABLED', False) and AI_AVAILABLE
            
            # Start database transaction
            new_item = Item(
                item_type=form_data['type'],
                item_category=form_data['category'],
                item_title=form_data['title'],
                item_description=form_data['description'],
                item_location=form_data['location'],
                item_date_lost_found=date_obj,
                owner_id=current_user.user_id,
                item_status='pending'
            )
            
            db.session.add(new_item)
            db.session.flush()  # Get item_id without committing
            
            # Process image if provided
            image_file = request.files.get('image')
            image_processed = False
            image_matches = []

            if image_file and image_file.filename:
                # Validate file
                if not allowed_file(image_file.filename):
                    flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, BMP, WEBP', 'error')
                    return render_template('reporting/report.html', categories=categories, locations=locations)
                
                # Check file size
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(0)
                
                if file_size > MAX_FILE_SIZE:
                    flash(f'File too large. Maximum size is {MAX_FILE_SIZE//1024//1024}MB', 'error')
                    return render_template('reporting/report.html', categories=categories, locations=locations)
                
                # Save image
                try:
                    # 🔴 FIX 1: Use .item_id instead of .id
                    filename = secure_filename(f"{new_item.item_id}_{image_file.filename}")
                    
                    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    filepath = os.path.join(upload_dir, filename)
                    
                    image_file.save(filepath)
                    
                    # 🔴 FIX 2: Use .item_image_path instead of .image_path
                    new_item.item_image_path = filename
                    image_processed = True
                    
                    # Process with Visual Engine if enabled
                    print(f"🔍 AI_ENABLED in config: {current_app.config.get('AI_ENABLED', False)}")
                    print(f"🔍 AI_AVAILABLE (module loaded): {AI_AVAILABLE}")
                    print(f"🔍 ai_enabled (both true): {ai_enabled}")
                    
                    if ai_enabled:
                        try:
                            print(f"🖼️ Starting visual processing for item {new_item.item_id}")
                            # 🛑 IMPORTANT: Open the file we just saved to disk
                            # We use 'rb' (read binary)
                            with open(filepath, 'rb') as f_stream:
                                # We pass the item_id and the file stream
                                image_matches = image_engine.process_new_item(new_item.item_id, f_stream)
                                print(f"✅ Visual system processed image. Found {len(image_matches)} visual matches")
                                if len(image_matches) > 0:
                                    for match in image_matches:
                                        print(f"   - Match: Item #{match['item'].item_id}, Similarity: {match['similarity']:.2%}")
                        except Exception as ai_error:
                            print(f"⚠️ Visual processing error: {ai_error}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"⚠️ Visual processing skipped (ai_enabled={ai_enabled})")
                    
                except Exception as e:
                    print(f"❌ Image save error: {e}")
                    flash('Item saved, but image upload failed', 'warning')
            
            # Commit the item to database
            db.session.commit()
            
            # ===== TEXT-BASED MATCHING =====
            text_matches_count = 0
            try:
                text_matches_count = matching_engine.find_potential_matches(new_item)
                if text_matches_count > 0:
                    db.session.commit()
                print(f"✅ Text matching found {text_matches_count} matches")
            except Exception as e:
                print(f"⚠️ Text matching error: {e}")
            
            # ===== PROCESS IMAGE MATCHES (if any) =====
            image_notifications = 0
            if image_matches and ai_enabled:
                for match in image_matches:
                    matched_item = match['item']
                    similarity = match['similarity']
                    
                    if matched_item.owner_id == current_user.user_id:
                        continue
                    
                    # Determine notification details - SEND TO BOTH PARTIES
                    if new_item.item_type == 'lost' and matched_item.item_type == 'found':
                        # Notify the person who lost the item (current user)
                        notification_to_loser = Notification(
                            user_id=current_user.user_id,
                            item_id=matched_item.item_id,
                            notification_message=f"📸 Visual match found! We found an item that looks like your lost '{new_item.item_title}'. Similarity: {similarity:.1%}",
                            notification_type='visual_match',
                            notification_is_seen=False
                        )
                        db.session.add(notification_to_loser)
                        
                        # Notify the finder (owner of found item)
                        notification_to_finder = Notification(
                            user_id=matched_item.owner_id,
                            item_id=new_item.item_id,
                            notification_message=f"📸 Visual match found! Someone reported a lost item that looks like your found '{matched_item.item_title}'. Similarity: {similarity:.1%}",
                            notification_type='visual_match',
                            notification_is_seen=False
                        )
                        db.session.add(notification_to_finder)
                        image_notifications += 1
                    
                    elif new_item.item_type == 'found' and matched_item.item_type == 'lost':
                        # Notify the person who lost the item (owner of matched item)
                        notification_to_loser = Notification(
                            user_id=matched_item.owner_id,
                            item_id=new_item.item_id,
                            notification_message=f"📸 Visual match found! Someone found an item that looks like your lost '{matched_item.item_title}'. Similarity: {similarity:.1%}",
                            notification_type='visual_match',
                            notification_is_seen=False
                        )
                        db.session.add(notification_to_loser)
                        
                        # Notify the finder (current user)
                        notification_to_finder = Notification(
                            user_id=current_user.user_id,
                            item_id=matched_item.item_id,
                            notification_message=f"📸 Visual match found! Your found item '{new_item.item_title}' matches a lost report. Similarity: {similarity:.1%}",
                            notification_type='visual_match',
                            notification_is_seen=False
                        )
                        db.session.add(notification_to_finder)
                        image_notifications += 1
                        
                    else:
                        continue
                
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
                flash('✅ Item reported with image!', 'success')
            else:
                flash('✅ Item reported!', 'success')
            
            return redirect(url_for('reporting.my_items'))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Critical error in report_item: {e}")
            flash(f'Error reporting item: {str(e)[:100]}', 'error')
            return render_template('reporting/report.html', categories=categories, locations=locations)
    
    return render_template('reporting/report.html', categories=categories, locations=locations)


@reporting_bp.route('/my-items')
@login_required
def my_items():
    if current_user.user_role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    """Display user's reported items"""
    try:
        user_items = Item.query.filter_by(
            owner_id=current_user.user_id  
        ).order_by(
            Item.item_created_at.desc() 
        ).all()
        
        # Organize by status
        items_by_status = {
            'pending': [],
            'claimed': [],
            'resolved': []
        }
        
        for item in user_items:
            # ✅ CORRECTED: Use item_status (not status)
            items_by_status[item.item_status].append(item)
        
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
        item = Item.query.filter_by(item_id=item_id).first_or_404()  # ✅ Use filter_by with item_id
        
        # ✅ CORRECTED: Check ownership - use owner_id (not user_id) and current_user.user_id (not current_user.id)
        if item.owner_id != current_user.user_id:
            flash('You can only update your own items', 'error')
            return redirect(url_for('reporting.my_items'))
        
        new_status = request.form.get('status')
        valid_statuses = ['pending', 'claimed', 'resolved']
        
        if new_status not in valid_statuses:
            flash('Invalid status', 'error')
            return redirect(url_for('reporting.my_items'))
        
        old_status = item.item_status  # ✅ Use item_status
        item.item_status = new_status  # ✅ Use item_status
        
        # Create notification if marked as resolved
        if new_status == 'resolved' and old_status != 'resolved':
            notification = Notification(
                user_id=item.owner_id,  # ✅ Use owner_id (not user_id)
                item_id=item.item_id,  # ✅ Use item_id (not id)
                notification_message=f"Your item '{item.item_title}' has been marked as resolved",  # ✅ Use item_title and correct field name
                notification_type='item_resolved'  # ✅ Use correct field name
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
    item = Item.query.filter_by(item_id=item_id).first_or_404()  # ✅ Use filter_by with item_id
    
    # ✅ CORRECTED: Check ownership
    if item.owner_id != current_user.user_id:  # Use owner_id and current_user.user_id
        flash('You can only edit your own items', 'error')
        return redirect(url_for('reporting.my_items'))
    
    if request.method == 'POST':
        try:
            # ✅ CORRECTED: Update fields with prefixed names
            item.item_title = request.form.get('title', item.item_title).strip()  # Use item_title
            item.item_description = request.form.get('description', item.item_description).strip()  # Use item_description
            item.item_location = request.form.get('location', item.item_location).strip()  # Use item_location
            item.item_category = request.form.get('category', item.item_category)  # Use item_category
            
            # Handle new image
            image_file = request.files.get('image')
            if image_file and image_file.filename and allowed_file(image_file.filename):
                # Delete old image if exists
                if item.item_image_path:  # ✅ Use item_image_path
                    upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                    old_path = os.path.join(upload_dir, item.item_image_path)  # ✅ Use item_image_path
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # Save new image
                filename = secure_filename(f"item_{item.item_id}_{image_file.filename}")  # ✅ Use item_id
                upload_dir = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                
                image_file.save(filepath)
                item.item_image_path = filename  # ✅ Use item_image_path
            
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('reporting.my_items'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'error')
    
    # Fetch categories and locations for editing
    categories = Category.query.filter_by(category_is_active=True).all()
    locations = CampusLocation.query.filter_by(location_is_active=True).all()
    
    return render_template('reporting/edit_item.html', item=item, categories=categories, locations=locations)

@reporting_bp.route('/item/<int:item_id>/claim', methods=['POST'])
@login_required
def claim_item(item_id):
    """
    Handle a user claiming a found item.
    Instead of changing status directly, it sends a message to the owner.
    """
    try:
        item = Item.query.get_or_404(item_id)
        
        # Validation
        if item.item_type != 'found':
            flash('Only found items can be claimed.', 'error')
            return redirect(url_for('view_item', item_id=item_id))
            
        if item.owner_id == current_user.user_id:
            flash('You cannot claim your own item.', 'warning')
            return redirect(url_for('view_item', item_id=item_id))
            
        if item.item_status != 'pending':
            flash('This item is no longer available.', 'error')
            return redirect(url_for('view_item', item_id=item_id))
            
        # Create the claim message
        # We import Message locally to avoid circular imports if any
        from models import Message
        
        claim_msg = Message(
            message_sender_id=current_user.user_id,
            message_recipient_id=item.owner_id,
            message_body=f"👋 I believe this item '{item.item_title}' is mine. I would like to claim it.",
            message_item_id=item.item_id, # Link message to item for "Smart" actions
            message_is_read=False
        )
        
        # Create notification for the owner
        notification = Notification(
            user_id=item.owner_id,
            item_id=item.item_id,
            notification_sender_id=current_user.user_id,
            notification_message=f"{current_user.user_username} has sent a claim request for '{item.item_title}'",
            notification_type='message', # We treat it as a message notification
            notification_is_seen=False
        )
        
        db.session.add(claim_msg)
        db.session.add(notification)
        db.session.commit()
        
        flash('Claim request sent! The finder has been notified.', 'success')
        # Redirect to conversation with finder so they can follow up
        return redirect(url_for('messaging.conversation', user_id=item.owner_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in claim_item: {e}")
        flash('An error occurred while sending your claim request.', 'error')
        return redirect(url_for('view_item', item_id=item_id))

@reporting_bp.route('/item/<int:item_id>/accept_claim/<int:claimant_id>', methods=['POST'])
@login_required
def accept_claim(item_id, claimant_id):
    """
    Owner accepts a claim request.
    Sets status to 'claimed' and notifies the claimant.
    """
    try:
        item = Item.query.get_or_404(item_id)
        
        # Security check: Only owner can accept claims
        if item.owner_id != current_user.user_id:
            flash('Unauthorized action.', 'error')
            return redirect(url_for('dashboard'))
            
        if item.item_status != 'pending':
            flash('Item is already processed.', 'warning')
            return redirect(url_for('reporting.my_items'))
            
        # Update Status
        item.item_status = 'claimed'
        
        # Notify Claimant
        notification = Notification(
            user_id=claimant_id,
            item_id=item.item_id,
            notification_sender_id=current_user.user_id,
            notification_message=f"Good news! Your claim for '{item.item_title}' was accepted by the finder.",
            notification_type='message', 
            notification_is_seen=False
        )
        
        # Optional: Send confirmation message
        from models import Message
        confirm_msg = Message(
            message_sender_id=current_user.user_id,
            message_recipient_id=claimant_id,
            message_body=f"✅ I've accepted your claim for '{item.item_title}'. Let's coordinate the return.",
            message_item_id=item.item_id,
            message_is_read=False
        )
        
        db.session.add(notification)
        db.session.add(confirm_msg)
        db.session.commit()
        
        flash(f'Claim accepted! Item marked as "In Progress".', 'success')
        return redirect(url_for('messaging.conversation', user_id=claimant_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in accept_claim: {e}")
        flash('An error occurred.', 'error')
        return redirect(url_for('reporting.my_items'))

@reporting_bp.route('/my-items/download-pdf')
@login_required
def download_my_items_pdf():
    try:
        items = Item.query.filter_by(owner_id=current_user.user_id).order_by(Item.item_created_at.desc()).all()
        
        class ModernPDF(FPDF):
            def header(self):
                # --- Brand Header ---
                # Set Emerald Green Color (R, G, B)
                self.set_fill_color(16, 185, 129) 
                self.rect(0, 0, 210, 40, 'F') # Full width rectangle at top
                
                # Title
                self.set_font('Helvetica', 'B', 24)
                self.set_text_color(255, 255, 255) # White text
                self.set_y(15)
                self.cell(0, 10, 'Campus Lost & Found', 0, 1, 'C')
                
                # Subtitle
                self.set_font('Helvetica', '', 12)
                self.cell(0, 10, 'Personal Items Report', 0, 1, 'C')
                self.ln(20) # Add spacing after header

            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128, 128, 128) # Grey text
                self.cell(0, 10, f'Generated by Campus Lost & Found System | Page {self.page_no()}', 0, 0, 'C')

        # Create PDF
        pdf = ModernPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # --- User Info Section ---
        pdf.set_text_color(50, 50, 50)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f"Report Owner: {current_user.user_username}", 0, 1)
        
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Email: {current_user.user_email}", 0, 1)
        pdf.cell(0, 6, f"Generated On: {datetime.now().strftime('%B %d, %Y at %H:%M')}", 0, 1)
        pdf.cell(0, 6, f"Total Items: {len(items)}", 0, 1)
        pdf.ln(10)

        # --- Table Header ---
        pdf.set_font('Arial', 'B', 10)
        pdf.set_fill_color(240, 240, 240) # Light Grey for header
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(200, 200, 200) # Light grey borders
        
        # Column Widths
        w_title = 65
        w_type = 25
        w_cat = 40
        w_status = 25
        w_date = 35

        pdf.cell(w_title, 10, 'Item Title', 1, 0, 'L', 1)
        pdf.cell(w_type, 10, 'Type', 1, 0, 'C', 1)
        pdf.cell(w_cat, 10, 'Category', 1, 0, 'L', 1)
        pdf.cell(w_status, 10, 'Status', 1, 0, 'C', 1)
        pdf.cell(w_date, 10, 'Date', 1, 1, 'C', 1)

        # --- Table Content ---
        pdf.set_font('Arial', '', 9)
        fill = False # For zebra striping

        for item in items:
            # Set zebra color (Very light green vs White)
            if fill:
                pdf.set_fill_color(245, 255, 250) # Mint cream
            else:
                pdf.set_fill_color(255, 255, 255) # White

            # Helper to sanitize text (remove emojis/non-latin)
            def clean(text):
                return text.encode('latin-1', 'ignore').decode('latin-1').strip()

            title = clean(item.item_title)
            # Truncate title if too long
            if len(title) > 35: title = title[:32] + "..."

            pdf.cell(w_title, 10, title, 1, 0, 'L', 1)
            pdf.cell(w_type, 10, item.item_type.upper(), 1, 0, 'C', 1)
            pdf.cell(w_cat, 10, clean(item.item_category), 1, 0, 'L', 1)
            
            # Status Logic (Maybe bold pending?)
            pdf.cell(w_status, 10, item.item_status.title(), 1, 0, 'C', 1)
            
            pdf.cell(w_date, 10, item.item_created_at.strftime('%Y-%m-%d'), 1, 1, 'C', 1)
            
            fill = not fill # Toggle striping

        # Output
        response = make_response(pdf.output(dest='S').encode('latin-1', 'replace'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=Report_{current_user.user_username}_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response

    except Exception as e:
        print(f"Error generating PDF: {e}")
        flash("Error generating PDF report", "error")
        return redirect(url_for('reporting.my_items'))