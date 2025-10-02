import requests
import os
from geopy.geocoders import Nominatim

API_KEY = os.getenv("IPGEOLOCATION_API_KEY")

def get_uv_index(location):
    """
    Fetch real-time UV index for a given location using OpenUV API.
    
    Args:
        location (str): Location string (e.g., "Lisbon, Portugal").
    
    Returns:
        float: UV index value.
    
    Raises:
        Exception: If location is invalid, API key is missing, or API request fails.
    """
    # Initialize geocoder
    geolocator = Nominatim(user_agent="SCP_Collector")
    
    # Convert location to latitude and longitude
    try:
        location_data = geolocator.geocode(location)
        if not location_data:
            raise Exception("Invalid location. Please enter a valid city and country (e.g., 'Lisbon, Portugal').")
        lat = location_data.latitude
        lng = location_data.longitude
    except Exception as e:
        raise Exception(f"Geocoding failed: {str(e)}")

    # OpenUV API configuration
    api_key = "openuv-1s7ggrmdefauin-io"  # Replace with your actual OpenUV API key
    url = f"https://api.openuv.io/api/v1/uv?lat={lat}&lng={lng}"
    headers = {"x-access-token": api_key}

    # Make API request
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        
        # Extract UV index
        uv_index = data.get("result", {}).get("uv")
        #print("Extracted UV Index:", uv_index)

        if uv_index is None:
            raise Exception("UV index not found in API response.")
        
        return float(uv_index)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch UV index: {str(e)}")