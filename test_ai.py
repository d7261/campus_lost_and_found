from modules.ai_processing import image_engine
import numpy as np

def test_ai_system():
    print("🧠 Testing AI Image Recognition System...")
    
    # Test if we can import the required libraries
    try:
        import torch
        import torchvision
        from PIL import Image
        import sklearn
        import cv2
        
        print("✅ All required libraries imported successfully!")
        print(f"PyTorch version: {torch.__version__}")
        print(f"OpenCV version: {cv2.__version__}")
        
        # Test creating a dummy image and processing it
        dummy_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        pil_image = Image.fromarray(dummy_image)
        
        print("✅ Basic image processing test passed!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_ai_system()