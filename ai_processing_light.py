import cv2
import numpy as np
from PIL import Image
import io
from sklearn.metrics.pairwise import cosine_similarity
from models import db, ImageEmbedding, Item

class LightImageRecognition:
    def __init__(self):
        # Load OpenCV's pre-trained deep learning model
        self.net = cv2.dnn.readNetFromTensorflow('models/opencv_face_detector_uint8.pb', 
                                               'models/opencv_face_detector.pbtxt')
        
    def extract_features_simple(self, image_file):
        """Extract features using OpenCV and simple image processing"""
        try:
            if isinstance(image_file, str):
                image = cv2.imread(image_file)
            else:
                image_array = np.frombuffer(image_file.read(), np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                return None
            
            # Resize image to standard size
            image = cv2.resize(image, (224, 224))
            
            # Convert to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Simple feature extraction: color histogram + edge features
            features = []
            
            # Color histogram (global features)
            hist_r = cv2.calcHist([image_rgb], [0], None, [64], [0, 256])
            hist_g = cv2.calcHist([image_rgb], [1], None, [64], [0, 256])
            hist_b = cv2.calcHist([image_rgb], [2], None, [64], [0, 256])
            
            # Normalize histograms
            hist_r = cv2.normalize(hist_r, hist_r).flatten()
            hist_g = cv2.normalize(hist_g, hist_g).flatten()
            hist_b = cv2.normalize(hist_b, hist_b).flatten()
            
            # Edge features
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Combine all features
            features.extend(hist_r)
            features.extend(hist_g)
            features.extend(hist_b)
            features.append(edge_density)
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            print(f"Error in light feature extraction: {e}")
            return None
    
    def save_image_embedding(self, item_id, image_file):
        """Save image embedding to database"""
        try:
            features = self.extract_features_simple(image_file)
            if features is not None:
                features_bytes = features.tobytes()
                
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
    
    def find_similar_items(self, query_features, threshold=0.6, max_results=10):
        """Find similar items based on image features"""
        try:
            all_embeddings = ImageEmbedding.query.all()
            similar_items = []
            
            for embedding in all_embeddings:
                stored_features = np.frombuffer(embedding.embedding, dtype=np.float32)
                
                # Ensure same length
                min_len = min(len(query_features), len(stored_features))
                query_trunc = query_features[:min_len]
                stored_trunc = stored_features[:min_len]
                
                similarity = cosine_similarity([query_trunc], [stored_trunc])[0][0]
                
                if similarity >= threshold:
                    similar_items.append({
                        'item': embedding.item,
                        'similarity': similarity,
                        'embedding_id': embedding.id
                    })
            
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_items[:max_results]
            
        except Exception as e:
            print(f"Error finding similar items: {e}")
            return []

# Global instance
light_image_engine = LightImageRecognition()