from models import db, Item, Notification
from datetime import datetime

class SimpleMatchingEngine:
    def __init__(self, similarity_threshold=0.3):
        self.similarity_threshold = similarity_threshold
    
    def find_potential_matches(self, new_item):
        """Find potential matches for a new item and create notifications"""
        print(f"🔍 Text Matching: Scanning for '{new_item.item_title}'...")
        
        try:
            # 1. Get candidates
            if new_item.item_type == 'lost':
                candidate_items = Item.query.filter_by(item_type='found', item_status='pending').all()
            else:
                candidate_items = Item.query.filter_by(item_type='lost', item_status='pending').all()
            
            matches_found = 0
            
            for candidate in candidate_items:
                # Use candidate item ID
                if candidate.item_id == new_item.item_id:
                    continue
                
                # Calculate score
                similarity_score = self.calculate_similarity(new_item, candidate)
                
                # Only print if there's some similarity, to reduce noise
                if similarity_score > 0.1:
                    print(f"   -> Comparing with '{candidate.item_title}': Score {similarity_score:.2f}")
                
                if similarity_score >= self.similarity_threshold:
                    self.create_match_notification(new_item, candidate, similarity_score)
                    matches_found += 1
            
            return matches_found
            
        except Exception as e:
            # This is where your error log was coming from
            print(f"❌ Error finding matches: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def calculate_similarity(self, item1, item2):
        try:
            def clean(s): return str(s).lower() if s else ""
            
            # Combine fields
            text1 = f"{clean(item1.item_title)} {clean(item1.item_description)} {clean(item1.item_category)} {clean(item1.item_location)}"
            text2 = f"{clean(item2.item_title)} {clean(item2.item_description)} {clean(item2.item_category)} {clean(item2.item_location)}"
            
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            if not words1 and not words2: return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
        except:
            return 0.0
    
    def create_match_notification(self, item1, item2, similarity_score):
        try:
            if item1.item_type == 'lost':
                lost_item, found_item = item1, item2
            else:
                lost_item, found_item = item2, item1
            
            # Use owner_id column from database
            # Do NOT use .owner.user_id (Relationship) to avoid loading errors
            lost_owner_id = lost_item.owner_id
            found_owner_id = found_item.owner_id
            
            # Prevent self-notification
            if lost_owner_id == found_owner_id:
                return

            # Notification for Lost Item Owner
            n1 = Notification(
                notification_message=f"🔍 Match Found! A found '{found_item.item_title}' matches your lost report. (Similarity: {similarity_score:.0%})",
                notification_type='potential_match',
                user_id=lost_item.owner_id,      # Recipient (Lost item owner)
                item_id=found_item.item_id       # Related found item
            )
            
            # Notification for Found Item Reporter
            n2 = Notification(
                notification_message=f"🔍 Match Found! Your found '{found_item.item_title}' matches a lost report. (Similarity: {similarity_score:.0%})",
                notification_type='potential_match',
                user_id=found_item.owner_id,     # Recipient (Found item finder)
                item_id=lost_item.item_id        # Related lost item
            )
            
            db.session.add(n1)
            db.session.add(n2)
            # We don't commit here because reporting.py does the commit
            
            print(f"✅ Notifications created for User {lost_owner_id} and User {found_owner_id}")
            
        except Exception as e:
            print(f"❌ Error creating notification: {e}")

# Initialize
matching_engine = SimpleMatchingEngine()