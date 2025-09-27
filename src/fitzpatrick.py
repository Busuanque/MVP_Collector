from PIL import Image
import numpy as np

def analyze_fitzpatrick(image_path):
    """Analyze skin type based on Fitzpatrick scale (simplified version)."""
    try:
        # Open and convert image
        img = Image.open(image_path)
        img = img.convert('RGB')
        img = img.resize((100, 100))  # Resize for processing
        
        # Convert to numpy array
        img_array = np.array(img)
        
        # Calculate average RGB values
        avg_r = np.mean(img_array[:,:,0])
        avg_g = np.mean(img_array[:,:,1])  
        avg_b = np.mean(img_array[:,:,2])
        
        # Simple brightness calculation
        brightness = (avg_r + avg_g + avg_b) / 3
        
        # Map brightness to Fitzpatrick types (simplified)
        if brightness > 200:
            return "Tipo I"
        elif brightness > 180:
            return "Tipo II"
        elif brightness > 160:
            return "Tipo III"
        elif brightness > 140:
            return "Tipo IV"
        elif brightness > 120:
            return "Tipo V"
        else:
            return "Tipo VI"
            
    except Exception as e:
        print(f"Fitzpatrick analysis error: {e}")
        return "Tipo III"  # Default fallback
