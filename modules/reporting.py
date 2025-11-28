from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Item, Notification
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from modules.matching_simple import matching_engine
from modules.ai_processing import image_engine

reporting_bp = Blueprint('reporting', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@reporting_bp.route('/report', methods=['GET', 'POST'])
@login_required
def report_item():
    if request.method == 'POST':
        try:
            item_type = request.form.get('type')
            category = request.form.get('category')
            title = request.form.get('title')
            description = request.form.get('description')
            location = request.form.get('location')
            date_lost_found = request.form.get('date_lost_found')
            image_file = request.files.get('image')
            
            # Validation
            if not all([item_type, category, title, description, location, date_lost_found]):
                flash('Please fill all required fields', 'error')
                return render_template('reporting/report.html')
            
            # Create new item
            new_item = Item(
                type=item_type,
                category=category,
                title=title,
                description=description,
                location=location,
                date_lost_found=datetime.strptime(date_lost_found, '%Y-%m-%d'),
                user_id=current_user.id
            )
            
            db.session.add(new_item)
            db.session.commit()
            # Process image if provided (now optional)
            image_matches = []
            if image_file and allowed_file(image_file.filename):
                try:
                    # Reset file stream position to beginning
                    image_file.stream.seek(0)
                    
                    # Save the actual image file first
                    image_saved = image_engine.save_uploaded_image(new_item.id, image_file)
                    
                    if image_saved:
                        # Reset file stream again for AI processing
                        image_file.stream.seek(0)
                        
                        # Process image with AI for matching
                        image_matches = image_engine.process_new_item(new_item.id, image_file)
                        
                        if image_matches:
                            # Create notifications for image-based matches
                            for match in image_matches:
                                notification = Notification(
                                    message=f"Visual match found! Your {new_item.type} item '{new_item.title}' looks similar to an item in our system ({(match['similarity'] * 100):.1f}% match)",
                                    notification_type='visual_match',
                                    user_id=current_user.id,
                                    item_id=new_item.id
                                )
                                db.session.add(notification)
                            
                            db.session.commit()
                            flash(f'Item reported successfully! Found {len(image_matches)} visual matches.', 'success')
                        else:
                            flash('Item reported successfully! Image uploaded and processed.', 'success')
                    else:
                        flash('Item reported successfully! (Image upload failed)', 'warning')
                        
                except Exception as e:
                    print(f"Error processing image: {e}")
                    flash('Item reported successfully! (Image processing failed)', 'warning')
            else:
                # No image provided - show helpful message
                flash('Item reported successfully! 💡 Tip: Adding a photo greatly increases recovery chances.', 'info')

            # ==== CRITICAL FIX: MOVE TEXT MATCHING OUTSIDE THE IMAGE BLOCK ====
# Text-based matching should happen for ALL items (with or without images)
            try:
                text_matches_count = matching_engine.find_potential_matches(new_item)
                print(f"✅ Text matching completed. Found {text_matches_count} matches for item {new_item.id}")
            except Exception as e:
                print(f"❌ Error in text matching: {e}")
                text_matches_count = 0

            # Provide appropriate feedback
            if image_matches and text_matches_count > 0:
                flash(f'Found {len(image_matches)} visual matches and {text_matches_count} text matches!', 'success')
            elif text_matches_count > 0:
                flash(f'Item reported successfully! Found {text_matches_count} potential text matches.', 'success')
            elif image_matches:
                flash(f'Item reported successfully! Found {len(image_matches)} visual matches.', 'success')
            else:
                flash('Item reported successfully! We will notify you if any matches are found.', 'success')
        except Exception as e:
            flash(f'Error reporting item: {str(e)}', 'error')
            db.session.rollback()
            return render_template('reporting/report.html')
    
    return render_template('reporting/report.html')

@reporting_bp.route('/my-items')
@login_required
def my_items():
    user_items = Item.query.filter_by(user_id=current_user.id).order_by(Item.created_at.desc()).all()
    return render_template('reporting/my_items.html', items=user_items)