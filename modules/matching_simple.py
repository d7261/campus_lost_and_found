from models import db, Item, Notification
from datetime import datetime
from sqlalchemy.orm import joinedload  # ADD THIS IMPORT

class SimpleMatchingEngine:
    def __init__(self, text_threshold=0.3):
        self.text_threshold = text_threshold
    
    def find_potential_matches(self, new_item):
        """Find potential matches based on text similarity and CREATE NOTIFICATIONS"""
        try:
            # Eagerly load user relationships to avoid 'user' attribute errors
            if new_item.type == 'lost':
                candidate_items = Item.query.options(joinedload(Item.owner)).filter_by(
                    type='found', status='pending'
                ).all()
            else:
                candidate_items = Item.query.options(joinedload(Item.owner)).filter_by(
                    type='lost', status='pending'
                ).all()
            
            # Also ensure the new_item has user relationship loaded
            if not hasattr(new_item, 'owner'):
                new_item = Item.query.options(joinedload(Item.owner)).get(new_item.id)
            
            matches_found = 0
            
            for candidate in candidate_items:
                if candidate.id == new_item.id:
                    continue
                
                similarity_score = self.calculate_text_similarity(new_item, candidate)
                
                if similarity_score >= self.text_threshold:
                    # CREATE NOTIFICATIONS FOR BOTH USERS
                    self.create_match_notifications(new_item, candidate, similarity_score)
                    matches_found += 1
            
            return matches_found
            
        except Exception as e:
            print(f"Error finding matches: {e}")
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
    
    def create_match_notifications(self, item1, item2, similarity_score):
        """Create notifications for both users about a potential match"""
        try:
            print(f"🔍 Creating notifications between: {item1.title} (user: {item1.user_id}) and {item2.title} (user: {item2.user_id})")
            
            # Use the relationship - it should now be loaded
            lost_user = item1.owner if item1.type == 'lost' else item2.owner
            found_user = item2.owner if item1.type == 'lost' else item1.owner
            lost_item = item1 if item1.type == 'lost' else item2
            found_item = item2 if item1.type == 'lost' else item1
            
            print(f"📢 Notifying lost user: {lost_user.username} (ID: {lost_user.id})")
            print(f"📢 Notifying found user: {found_user.username} (ID: {found_user.id})")
            
            # Create notification for the person who lost the item
            lost_notification = Notification(
                message=f"🔍 Potential match found! Your lost '{lost_item.title}' might be this found item. Similarity: {similarity_score:.1%}. Check the item details.",
                notification_type='potential_match',
                user_id=lost_user.id,
                item_id=lost_item.id
            )
            
            # Create notification for the person who found the item  
            found_notification = Notification(
                message=f"🔍 Your found '{found_item.title}' might match a reported lost item. Similarity: {similarity_score:.1%}. The owner may contact you.",
                notification_type='potential_match',
                user_id=found_user.id,
                item_id=found_item.id
            )
            
            db.session.add(lost_notification)
            db.session.add(found_notification)
            db.session.commit()
            
            print(f"✅ Created match notifications between '{lost_item.title}' and '{found_item.title}'")
            
        except Exception as e:
            print(f"❌ Error creating match notifications: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            db.session.rollback()

matching_engine = SimpleMatchingEngine()