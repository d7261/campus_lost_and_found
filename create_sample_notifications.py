from app import app, db, User, Item, Notification
from datetime import datetime

def create_sample_notifications():
    with app.app_context():
        # Get a user to create notifications for
        user = User.query.first()
        
        if not user:
            print("No users found. Please register a user first.")
            return
        
        # Create sample notifications
        notifications = [
            Notification(
                message="Potential match found for your lost 'iPhone 13'. Similarity: 85%",
                notification_type='potential_match',
                user_id=user.user_id,
                item_id=1  # This would be an actual item ID
            ),
            Notification(
                message="Your found 'Calculus Textbook' might match a lost item. Similarity: 72%", 
                notification_type='potential_match',
                user_id=user.user_id,
                item_id=2
            ),
            Notification(
                message="New item matching your search for 'water bottle' has been reported",
                notification_type='search_match',
                user_id=user.id, 
                item_id=3
            )
        ]
        
        for notification in notifications:
            db.session.add(notification)
        
        db.session.commit()
        print(f"✅ Created {len(notifications)} sample notifications for user: {user.username}")

if __name__ == '__main__':
    create_sample_notifications()