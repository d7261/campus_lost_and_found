import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import numpy as np
import io
import os
from sklearn.metrics.pairwise import cosine_similarity
from models import db, ImageEmbedding, Item

class ImageRecognitionEngine:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model()
        self.transform = self._get_transform()
        print(f"🤖 AI Engine initialized on {self.device}")
        
    def _load_model(self):
        """Load pre-trained ResNet model"""
        try:
            model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
            # Remove classification layer
            model = torch.nn.Sequential(*(list(model.children())[:-1]))
            model.eval()
            model.to(self.device)
            return model
        except Exception as e:
            print(f"⚠️ Error loading ResNet model: {e}")
            return None
    
    def _get_transform(self):
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def extract_features(self, image_input):
        """Extract feature embeddings from an image stream or path"""
        if self.model is None: return None
        
        try:
            # 🛑 FIX 1: Handle Stream Seeking (Reset cursor to start)
            if hasattr(image_input, 'seek') and hasattr(image_input, 'read'):
                image_input.seek(0)
                image = Image.open(image_input).convert('RGB')
            elif isinstance(image_input, str):
                image = Image.open(image_input).convert('RGB')
            else:
                return None
            
            # Transform and extract
            image_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                features = self.model(image_tensor)
                features = features.squeeze().cpu().numpy()
            
            return features.flatten()
            
        except Exception as e:
            print(f"❌ Error extracting features: {e}")
            return None
    
    def save_image_embedding(self, item_id, features):
        """
        Save pre-calculated features to database.
        🛑 FIX 2: Accepts 'features' array, not the file object
        """
        try:
            if features is not None:
                features_bytes = features.tobytes()
                
                # Check if embedding already exists
                existing = ImageEmbedding.query.filter_by(item_id=item_id).first()
                if existing:
                    existing.image_embedding_data = features_bytes
                else:
                    embedding = ImageEmbedding(
                        item_id=item_id,
                        image_embedding_data=features_bytes
                    )
                    db.session.add(embedding)
                
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"❌ Error saving embedding: {e}")
            db.session.rollback()
            return False
    
    def find_similar_items(self, query_features, threshold=0.60, max_results=5, exclude_item_id=None):
        """Find similar items using Cosine Similarity"""
        try:
            # Get all OTHER embeddings (optimize in production)
            all_embeddings = ImageEmbedding.query.all()
            similar_items = []
            
            # Normalize query vector for cosine similarity
            query_norm = np.linalg.norm(query_features)
            if query_norm == 0: return []
            
            for embedding in all_embeddings:
                # Skip if data is corrupted
                if not embedding.image_embedding_data: continue
                
                # Skip the current item itself
                if exclude_item_id and embedding.item_id == exclude_item_id:
                    continue
                
                stored_features = np.frombuffer(embedding.image_embedding_data, dtype=np.float32)
                
                # Calculate Cosine Similarity
                stored_norm = np.linalg.norm(stored_features)
                if stored_norm == 0: continue
                
                dot_product = np.dot(query_features, stored_features)
                similarity = dot_product / (query_norm * stored_norm)
                
                if similarity >= threshold:
                    similar_items.append({
                        'item': embedding.item,
                        'similarity': float(similarity), # Convert numpy float to python float
                        'embedding_id': embedding.image_embedding_id
                    })
            
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_items[:max_results]
            
        except Exception as e:
            print(f"❌ Error finding similar items: {e}")
            return []
    
    def process_new_item(self, item_id, image_file):
        """
        Main entry point: Extracts ONCE, Saves, then Matches.
        """
        print(f"🖼️ AI Processing started for Item {item_id}")
        try:
            # 1. Extract features ONCE
            features = self.extract_features(image_file)
            
            if features is None:
                print("⚠️ Could not extract features from image.")
                return []
            
            # 2. Save using the extracted features
            saved = self.save_image_embedding(item_id, features)
            if not saved:
                print("⚠️ Failed to save embedding.")
            
            # 3. Find similar items using the same features (exclude current item)
            matches = self.find_similar_items(features, exclude_item_id=item_id)
            
            print(f"✅ AI Complete. Saved: {saved}, Matches found: {len(matches)}")
            return matches
            
        except Exception as e:
            print(f"❌ Error in process_new_item: {e}")
            return []

# Global instance
image_engine = ImageRecognitionEngine()