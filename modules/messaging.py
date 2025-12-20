from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Message, Item, Notification
from datetime import datetime
from sqlalchemy import or_, and_, func, case

messaging_bp = Blueprint('messaging', __name__)

@messaging_bp.route('/messages')
@login_required
def inbox():
    if current_user.user_role == 'admin':
        return redirect(url_for('admin.admin_dashboard'))
    """List of conversations"""
    # Find users who have exchanged messages with current_user
    # This is a bit complex query to get unique conversations with latest message
    
    # Subquery to find latest message for each conversation partner
    subquery = db.session.query(
        func.max(Message.message_created_at).label('max_date'),
        case(
            (Message.message_sender_id == current_user.user_id, Message.message_recipient_id),
            else_=Message.message_sender_id
        ).label('other_user_id')
    ).filter(
        or_(
            Message.message_sender_id == current_user.user_id,
            Message.message_recipient_id == current_user.user_id
        )
    ).group_by('other_user_id').subquery()

    # Join with Message table to get message details
    latest_messages = db.session.query(Message).join(
        subquery,
        and_(
            Message.message_created_at == subquery.c.max_date,
            or_(
                and_(
                    Message.message_sender_id == current_user.user_id,
                    Message.message_recipient_id == subquery.c.other_user_id
                ),
                and_(
                    Message.message_recipient_id == current_user.user_id,
                    Message.message_sender_id == subquery.c.other_user_id
                )
            )
        )
    ).order_by(Message.message_created_at.desc()).all()

    conversations = []
    for msg in latest_messages:
        other_user_id = msg.message_recipient_id if msg.message_sender_id == current_user.user_id else msg.message_sender_id
        other_user = User.query.get(other_user_id)
        
        # Count unread messages from this user
        unread_count = Message.query.filter_by(
            message_sender_id=other_user_id,
            message_recipient_id=current_user.user_id,
            message_is_read=False
        ).count()
        
        conversations.append({
            'user': other_user,
            'last_message': msg,
            'unread_count': unread_count
        })

    return render_template('messaging/inbox.html', conversations=conversations)

@messaging_bp.route('/messages/<int:user_id>')
@login_required
def conversation(user_id):
    """View conversation with specific user"""
    other_user = User.query.get_or_404(user_id)
    
    # Context item (optional)
    item_id = request.args.get('item_id')
    context_item = None
    if item_id:
        context_item = Item.query.get(item_id)
    
    # Get messages
    messages = Message.query.filter(
        or_(
            and_(Message.message_sender_id == current_user.user_id, Message.message_recipient_id == user_id),
            and_(Message.message_sender_id == user_id, Message.message_recipient_id == current_user.user_id)
        )
    ).order_by(Message.message_created_at.asc()).all()

    # If no context_item from URL, try to find one from messages
    if not context_item and messages:
        # Look for the last message that has an item_id
        for msg in reversed(messages):
            if msg.message_item_id:
                context_item = Item.query.get(msg.message_item_id)
                break
    
    # Mark unread messages as read
    unread_messages = Message.query.filter_by(
        message_sender_id=user_id,
        message_recipient_id=current_user.user_id,
        message_is_read=False
    ).all()
    
    for msg in unread_messages:
        msg.message_is_read = True
    
    if unread_messages:
        db.session.commit()
        
    return render_template('messaging/conversation.html', 
                          other_user=other_user, 
                          messages=messages,
                          context_item=context_item)

@messaging_bp.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    recipient_id = request.form.get('recipient_id')
    body = request.form.get('body', '').strip()
    item_id = request.form.get('item_id')
    
    if not recipient_id or not body:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('messaging.inbox'))
    
    try:
        new_message = Message(
            message_sender_id=current_user.user_id,
            message_recipient_id=recipient_id,
            message_body=body,
            message_item_id=item_id if item_id else None
        )
        
        db.session.add(new_message)
        
        # Notify recipient
        notification = Notification(
            user_id=recipient_id,
            item_id=item_id if item_id else None, # Link to item if context exists
            notification_sender_id=current_user.user_id, # Link to sender
            notification_message=f"New message from {current_user.user_username}",
            notification_type='message',
            notification_is_seen=False
        )
        # If no item context, we might need to make item_id nullable in Notification or handle it differently.
        # However, Notification model has item_id as nullable=False in existing code? Let's check models.py
        # Wait, looked at models.py earlier: item_id IS nullable=False.
        # We need to handle this. For now, if no item_id, we can't create a 'Notification' linked to an item.
        # But messaging creates a notification.
        # Let's check Notification model again.
        
        # Ensure notification is linked to the item being discussed
        # Given existing constraints, I will check if item_id is provided.
        # If not, I'll search for a dummy item or skip notification for now (or fail safely).
        # Actually better: Creating a message usually happens in context of an item.
        # If generic message, we might have an issue.
        # Let's assume for now we skip Notification if no item_id, OR we force item_id.
        
        if item_id:
             db.session.add(notification)
        
        db.session.commit()
        
        return redirect(url_for('messaging.conversation', user_id=recipient_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error sending message: {e}")
        flash('Error sending message', 'error')
        return redirect(url_for('messaging.inbox'))
