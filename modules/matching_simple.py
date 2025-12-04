from models import db, Item, Notification
from datetime import datetime
from sqlalchemy.orm import joinedload

class SimpleMatchingEngine:
    def __init__(self, text_threshold=0.3):
        self.text_threshold = text_threshold
    
    def find_potential_matches(self, new_item):
        """Find potential matches based on text similarity and CREATE NOTIFICATIONS for relevant users"""
        try:
            # Eagerly load user relationships to avoid 'user' attribute errors
            if new_item.type == 'lost':
                # Look for FOUND items that might match this LOST item
                candidate_items = Item.query.options(joinedload(Item.owner)).filter_by(
                    type='found', status='pending'
                ).all()
            else:
                # Look for LOST items that might match this FOUND item
                candidate_items = Item.query.options(joinedload(Item.owner)).filter_by(
                    type='lost', status='pending'
                ).all()
            
            # Also ensure the new_item has user relationship loaded
            if not hasattr(new_item, 'owner'):
                new_item = Item.query.options(joinedload(Item.owner)).get(new_item.id)
            
            notifications_created = 0
            
            for candidate in candidate_items:
                if candidate.id == new_item.id:
                    continue
                
                similarity_score = self.calculate_text_similarity(new_item, candidate)
                
                if similarity_score >= self.text_threshold:
                    # CREATE NOTIFICATION for the relevant user
                    notifications_created += self.create_match_notification(new_item, candidate, similarity_score)
            
            return notifications_created  # Return count of actual notifications created
            
        except Exception as e:
            print(f"Error finding matches: {e}")
            return 0
    
    def create_match_notification(self, new_item, candidate_item, similarity_score):
        """Create notification for the relevant user about a potential match"""
        try:
            # Determine who should get notified based on the item types
            if new_item.type == 'lost' and candidate_item.type == 'found':
                # User reported LOST item, found matching FOUND item
                # Notify the user who reported the LOST item (they found their item!)
                notification_user_id = new_item.user_id
                message = f"🔍 Potential match found! We found an item that might be your lost '{new_item.title}'. Similarity: {similarity_score:.1%}."
                linked_item_id = candidate_item.id  # Link to the FOUND item so they can claim it
                
            elif new_item.type == 'found' and candidate_item.type == 'lost':
                # User reported FOUND item, found matching LOST item  
                # Notify the user who lost the item (their item might be found!)
                notification_user_id = candidate_item.user_id
                message = f"🔍 Potential match found! Someone found an item that might be your lost '{candidate_item.title}'. Similarity: {similarity_score:.1%}."
                linked_item_id = new_item.id  # Link to the FOUND item so they can claim it
            else:
                # Same type items (shouldn't happen with our filtering) or other cases
                return 0
            
            # Only create notification if it's for a different user
            if notification_user_id != new_item.user_id or new_item.type == 'lost':
                notification = Notification(
                    message=message,
                    notification_type='potential_match',
                    user_id=notification_user_id,
                    item_id=linked_item_id
                )
                
                db.session.add(notification)
                print(f"✅ Created text match notification for user {notification_user_id} - {message}")
                return 1
            else:
                print(f"⚠️  Skipping notification - would notify user about their own item")
                return 0
            
        except Exception as e:
            print(f"❌ Error creating match notification: {e}")
            return 0
    
    def calculate_text_similarity(self, item1, item2):
        """Calculate text similarity based on multiple fields"""
        try:
            # Combine relevant text fields with weights
            text1 = f"{item1.title} {item1.description} {item1.category} {item1.location}".lower()
            text2 = f"{item2.title} {item2.description} {item2.category} {item2.location}".lower()
            
            return self.simple_similarity(text1, text2)
        except:
            return 0.0
    
    def simple_similarity(self, text1, text2):
        """Simple text similarity using word overlap"""
        try:
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            if not words1 and not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union)
        except:
            return 0.0

matching_engine = SimpleMatchingEngine()