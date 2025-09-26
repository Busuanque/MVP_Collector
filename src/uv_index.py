import requests
import os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

def get_uv_index(location_str):
    """Fetch UV index using OpenUV API. Requires lat/lng from location."""
    try:
        api_key = os.getenv("OPENV_API_KEY")
        if not api_key:
            raise ValueError("OPENV_API_KEY not set in .env")
        
        # Geocode location to lat/lng
        geolocator = Nominatim(user_agent="mvp_collector")
        location = geolocator.geocode(location_str)
        if not location:
            raise GeocoderUnavailable("Could not geocode location")
        
        lat, lng = location.latitude, location.longitude
        url = f"https://api.openuv.io/api/v1/uv?lat={lat}&lng={lng}"
        headers = {"x-access-token": api_key}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return {"uv": data.get("result", {}).get("uv", 0), "location": location_str}
        else:
            raise ValueError(f"API error: {response.status_code}")
    except Exception as e:
        print(f"UV fetch error: {e}")
        return {"uv": 3, "location": location_str}  # Default medium UV