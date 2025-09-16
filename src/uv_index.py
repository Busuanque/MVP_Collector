import os
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from geopy.geocoders import Nominatim

def get_uv_index(location):
    """
    Fetch real-time UV index with retries e fallback.
    """
    # Geocoding
    geolocator = Nominatim(user_agent="skin_cancer_prevention_app")
    loc_data = geolocator.geocode(location)
    if not loc_data:
        raise Exception("Localização inválida.")
    lat, lng = loc_data.latitude, loc_data.longitude

    # Configuração da API
    api_key = os.getenv("OPENUV_API_KEY", "")
    url = f"https://api.openuv.io/api/v1/uv?lat={lat}&lng={lng}"
    headers = {"x-access-token": api_key}

    # Sessão com retries
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1,
                    status_forcelist=[429,500,502,503,504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        uv = response.json().get("result", {}).get("uv")
        if uv is None:
            raise Exception("UV index ausente na resposta.")
        return float(uv)
    except Exception as e:
        # Fallback e log
        print(f"⚠️ Warning: get_uv_index falhou: {e}")
        return -1.0



"""
import requests
from geopy.geocoders import Nominatim

def get_uv_index(location):
    Fetch real-time UV index for a given location using OpenUV API.
    
    Args:
        location (str): Location string (e.g., "Lisbon, Portugal").
    
    Returns:
        float: UV index value.
    
    Raises:
        Exception: If location is invalid, API key is missing, or API request fails.
    # Initialize geocoder
    geolocator = Nominatim(user_agent="skin_cancer_prevention_app")
    
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
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()  # Raise exception for bad status codes
        data = response.json()
        
        # Extract UV index
        uv_index = data.get("result", {}).get("uv")
        if uv_index is None:
            raise Exception("UV index not found in API response.")
        return float(uv_index)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch UV index: {str(e)}")
  """
