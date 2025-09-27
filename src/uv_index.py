import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_uv_index(location):
    """Get UV index for location using OpenWeatherMap API."""
    try:
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return {"uv": 5.0}  # Default fallback
        
        # Parse location
        city = location.split(',')[0].strip()
        
        # Get coordinates first
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={api_key}"
        geo_response = requests.get(geo_url, timeout=5)
        
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            if geo_data:
                lat, lon = geo_data[0]['lat'], geo_data[0]['lon']
                
                # Get UV index
                uv_url = f"http://api.openweathermap.org/data/2.5/uvi?lat={lat}&lon={lon}&appid={api_key}"
                uv_response = requests.get(uv_url, timeout=5)
                
                if uv_response.status_code == 200:
                    uv_data = uv_response.json()
                    return {"uv": uv_data.get('value', 5.0)}
        
        return {"uv": 5.0}  # Default fallback
        
    except Exception as e:
        print(f"UV Index error: {e}")
        return {"uv": 5.0}  # Default fallback
