from models import db, Item, Notification
from datetime import datetime

class SimpleMatchingEngine:
    def __init__(self, similarity_threshold=0.3):
        self.similarity_threshold = similarity_threshold
    
    def find_potential_matches(self, new_item):
        """Find potential matches for a new item and create notifications"""
        try:
            if new_item.type == 'lost':
                # Look for found items that might match this lost item
                candidate_items = Item.query.filter_by(
                    type='found', 
                    status='pending'
                ).all()
            else:
                # Look for lost items that might match this found item
                candidate_items = Item.query.filter_by(
                    type='lost', 
                    status='pending'
                ).all()
            
            matches_found = 0
            
            for candidate in candidate_items:
                if candidate.id == new_item.id:
                    continue
                
                similarity_score = self.calculate_similarity(new_item, candidate)
                
                if similarity_score >= self.similarity_threshold:
                    # Create notification for both users
                    self.create_match_notification(new_item, candidate, similarity_score)
                    matches_found += 1
            
            return matches_found
            
        except Exception as e:
            print(f"Error finding matches: {e}")
            return 0
    
    def calculate_similarity(self, item1, item2):
        """Calculate similarity between two items based on text content"""
        try:
            # Combine relevant text fields
            text1 = f"{item1.title} {item1.description} {item1.category} {item1.location}".lower()
            text2 = f"{item2.title} {item2.description} {item2.category} {item2.location}".lower()
            
            # Simple word overlap similarity
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            if not words1 and not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            similarity = len(intersection) / len(union)
            return similarity
            
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def create_match_notification(self, item1, item2, similarity_score):
        """Create notifications for both users about a potential match"""
        try:
            # Determine which item is lost and which is found
            if item1.type == 'lost':
                lost_item = item1
                found_item = item2
                lost_user = item1.user
                found_user = item2.user
            else:
                lost_item = item2
                found_item = item1
                lost_user = item2.user
                found_user = item1.user
            
            # Create notification for the person who lost the item
            lost_notification = Notification(
                message=f"Potential match found for your lost '{lost_item.title}'. Similarity: {similarity_score:.1%}",
                notification_type='potential_match',
                user_id=lost_user.id,
                item_id=lost_item.id
            )
            
            # Create notification for the person who found the item
            found_notification = Notification(
                message=f"Your found '{found_item.title}' might match a lost item. Similarity: {similarity_score:.1%}",
                notification_type='potential_match', 
                user_id=found_user.id,
                item_id=found_item.id
            )
            
            db.session.add(lost_notification)
            db.session.add(found_notification)
            db.session.commit()
            
            print(f"✅ Created match notifications for items {lost_item.id} and {found_item.id}")
            
        except Exception as e:
            print(f"Error creating notifications: {e}")
            db.session.rollback()

# Create global instance
matching_engine = SimpleMatchingEngine()