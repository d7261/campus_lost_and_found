import os
import numpy as np
from app import app
from models import db, ImageEmbedding, Item

def calculate_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return np.dot(v1, v2) / (norm1 * norm2)

def analyze_embeddings():
    with app.app_context():
        embeddings = ImageEmbedding.query.all()
        print(f"Loaded {len(embeddings)} embeddings from database.\n")
        
        # Mapping item_id to features
        item_data = {}
        for e in embeddings:
            features = np.frombuffer(e.image_embedding_data, dtype=np.float32)
            item = Item.query.get(e.item_id)
            if item:
                item_data[e.item_id] = {
                    'title': item.item_title,
                    'type': item.item_type,
                    'features': features
                }

        item_ids = list(item_data.keys())
        matches_found = []

        print(f"{'Item A':<30} | {'Item B':<30} | {'Similarity':<10}")
        print("-" * 75)

        for i in range(len(item_ids)):
            for j in range(i + 1, len(item_ids)):
                id1, id2 = item_ids[i], item_ids[j]
                item1, item2 = item_data[id1], item_data[id2]
                
                # We usually match Lost vs Found
                # But for debug, let's just see all high similarities
                similarity = calculate_similarity(item1['features'], item2['features'])
                
                if similarity > 0.5: # Threshold for display
                    print(f"{item1['title'][:28]:<30} | {item2['title'][:28]:<30} | {similarity:.2%}")
                    if similarity > 0.75: # Standard threshold
                        matches_found.append((id1, id2, similarity))

        print(f"\nTotal potential matches (>75%): {len(matches_found)}")

if __name__ == "__main__":
    analyze_embeddings()
