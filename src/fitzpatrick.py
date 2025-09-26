from PIL import Image
import os

def analyze_fitzpatrick(photo_path):
    """Basic Fitzpatrick skin type analysis based on average skin tone RGB."""
    if not os.path.exists(photo_path):
        raise FileNotFoundError("Photo not found")
    
    try:
        img = Image.open(photo_path)
        img = img.convert('RGB')
        # Sample center 50% of image for skin tone (simplified; real would use face detection)
        width, height = img.size
        crop_box = (width//4, height//4, 3*width//4, 3*height//4)
        cropped = img.crop(crop_box)
        pixels = list(cropped.getdata())
        
        # Average RGB
        r_total, g_total, b_total = 0, 0, 0
        for pixel in pixels:
            r, g, b = pixel
            r_total += r
            g_total += g
            b_total += b
        num_pixels = len(pixels)
        avg_r = r_total / num_pixels
        avg_g = g_total / num_pixels
        avg_b = b_total / num_pixels
        
        # Simple mapping: Lighter skin (higher R/G/B) -> Type I/II, etc. (Placeholder logic)
        lightness = (avg_r + avg_g + avg_b) / 3
        if lightness > 200:
            return "I"  # Very fair
        elif lightness > 150:
            return "II"  # Fair
        elif lightness > 100:
            return "III"  # Medium
        elif lightness > 50:
            return "IV"  # Olive
        else:
            return "V-VI"  # Dark
        
    except Exception as e:
        raise ValueError(f"Analysis error: {e}")