import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import numpy as np
import io
import base64
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import os
from models import db, ImageEmbedding, Item

class ImageRecognitionEngine:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model()
        self.transform = self._get_transform()
        
    def _load_model(self):
        """Load pre-trained ResNet model for feature extraction"""
        model = models.resnet50(pretrained=True)
        # Remove the final classification layer to get feature embeddings
        model = torch.nn.Sequential(*(list(model.children())[:-1]))
        model.eval()
        model.to(self.device)
        return model
    
    def _get_transform(self):
        """Define image transformations for the model"""
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def extract_features(self, image_file):
        """Extract feature embeddings from an image"""
        try:
            # Open and preprocess image
            if isinstance(image_file, str):
                # If it's a file path
                image = Image.open(image_file).convert('RGB')
            else:
                # If it's a file upload object
                image = Image.open(image_file.stream).convert('RGB')
            
            # Apply transformations
            image_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Extract features
            with torch.no_grad():
                features = self.model(image_tensor)
                features = features.squeeze().cpu().numpy()
            
            return features.flatten()
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def save_image_embedding(self, item_id, image_file):
        """Save image embedding to database"""
        try:
            features = self.extract_features(image_file)
            if features is not None:
                # Convert to bytes for storage
                features_bytes = features.tobytes()
                
                # Save to database
                embedding = ImageEmbedding(
                    item_id=item_id,
                    embedding=features_bytes
                )
                db.session.add(embedding)
                db.session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error saving embedding: {e}")
            db.session.rollback()
            return False
    
    def find_similar_items(self, query_features, threshold=0.7, max_results=10):
        """Find similar items based on image features"""
        try:
            all_embeddings = ImageEmbedding.query.all()
            similar_items = []
            
            for embedding in all_embeddings:
                # Convert bytes back to numpy array
                stored_features = np.frombuffer(embedding.embedding, dtype=np.float32)
                
                # Calculate similarity
                similarity = cosine_similarity(
                    [query_features], 
                    [stored_features]
                )[0][0]
                
                if similarity >= threshold:
                    similar_items.append({
                        'item': embedding.item,
                        'similarity': similarity,
                        'embedding_id': embedding.id
                    })
            
            # Sort by similarity and return top results
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_items[:max_results]
            
        except Exception as e:
            print(f"Error finding similar items: {e}")
            return []
    
    def process_new_item(self, item_id, image_file):
        """Process a new item with image and find matches"""
        try:
            # Extract features from the new image
            query_features = self.extract_features(image_file)
            if query_features is None:
                return []
            
            # Save embedding
            self.save_image_embedding(item_id, image_file)
            
            # Find similar items
            similar_items = self.find_similar_items(query_features)
            
            return similar_items
            
        except Exception as e:
            print(f"Error processing new item: {e}")
            return []
    
    def save_uploaded_image(self, item_id, image_file):
        """Save the uploaded image to the filesystem and update database"""
        try:
            # Ensure upload directory exists
            upload_dir = 'static/uploads'
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate filename
            filename = f"{item_id}.jpg"
            filepath = os.path.join(upload_dir, filename)
            
            # Reset file stream position to beginning
            image_file.stream.seek(0)
            
            # Open and process image
            image = Image.open(image_file.stream).convert('RGB')
            
            # Resize image to reasonable size for web display
            image.thumbnail((800, 800), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            image.save(filepath, 'JPEG', quality=85)
            
            # Update item with image path in database
            item = Item.query.get(item_id)
            if item:
                item.image_path = filename
                db.session.commit()
                print(f"✅ Image saved: {filepath}")
                return True
            else:
                print(f"❌ Item not found: {item_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving image: {e}")
            return False
# Global instance
image_engine = ImageRecognitionEngine()