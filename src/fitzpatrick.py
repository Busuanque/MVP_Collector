import cv2
import numpy as np

def analyze_fitzpatrick(image_path):
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise Exception("Failed to load image.")

    # Convert to HSV for better skin tone analysis
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Calculate average skin tone (simplified)
    mean_hsv = np.mean(hsv_image, axis=(0, 1))
    hue = mean_hsv[0]

    # Simplified Fitzpatrick scale classification based on hue
    # This is a basic approximation; real applications need calibration
    if hue < 20:
        return "Type I-II (Very fair to fair)"
    elif hue < 40:
        return "Type III-IV (Medium to olive)"
    else:
        return "Type V-VI (Dark to very dark)"

    # Note: For accurate results, use machine learning models (e.g., pre-trained CNNs)
    # trained on labeled skin tone datasets.