import requests
import os
import time
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

load_dotenv()  # Carrega .env

# FIX: Use a key correta do .env (OPENUV)
API_KEY = os.getenv("OPENUV_API_KEY") 

# Cache simples (dict global: chave=lat_lng, valor=(uv, timestamp))
uv_cache = {}
CACHE_TTL = 1800  # 30 minutos em segundos

def get_uv_index(location=None, lat=None, lng=None):
    # Primeiro, obtenha lat/lng (como antes)
    if lat is not None and lng is not None:
        # Use lat/lng direto (rápido, sem geocode)
        print("Usando lat/lng direto (otimizado)")
        cache_key = f"{lat}_{lng}"
    elif location:
        # Fallback para geocode se só location
        geolocator = Nominatim(user_agent="SCP_Collector")
        try:
            start_geo = time.time()
            location_data = geolocator.geocode(location, timeout=10)  # Timeout no geocode
            print(f"Geocode tempo: {time.time() - start_geo:.2f}s")
            if not location_data:
                raise Exception("Invalid location. Please enter a valid city and country (e.g., 'Lisbon, Portugal').")
            lat = location_data.latitude
            lng = location_data.longitude
            cache_key = f"{lat}_{lng}"
        except Exception as e:
            raise Exception(f"Geocoding failed: {str(e)}")
    else:
        raise Exception("Forneça 'location' OU 'lat' e 'lng'")

    # <-- NOVO: Checa cache primeiro (instantâneo!)
    if cache_key in uv_cache:
        cached_uv, cached_time = uv_cache[cache_key]
        if time.time() - cached_time < CACHE_TTL:
            print(f"Cache hit para {cache_key}: UV {cached_uv} (válido por mais {(CACHE_TTL - (time.time() - cached_time)) / 60:.1f} min)")
            return float(cached_uv)
        else:
            print(f"Cache expirado para {cache_key}, atualizando...")

    # OpenUV API configuration (só se cache miss)
    alt = 0  # Altitude default (opcional)
    url = f"https://api.openuv.io/api/v1/uv?lat={lat}&lng={lng}&alt={alt}"
    headers = {"x-access-token": API_KEY}

    # Make API request (com retry, como antes)
    uv_index = 4.4  # Default UV index in case of failure
    try:
        start_api = time.time()
        for attempt in range(3):  # Retry 3x
            try:
                response = requests.get(url, headers=headers, timeout=15)  # 15s
                print(f"API tentativa {attempt+1}: tempo {time.time() - start_api:.2f}s, status: {response.status_code}")
                response.raise_for_status()
                break
            except requests.exceptions.Timeout:
                print(f"Timeout na tentativa {attempt+1}/3. Aguardando...")
                time.sleep(2 ** attempt)
                if attempt == 2:
                    raise
        else:
            raise requests.exceptions.Timeout("Todas tentativas falharam")

        data = response.json()
        uv_index = data.get("result", {}).get("uv")
        if uv_index is None:
            raise Exception("UV index not found in API response.")
        
        # <-- NOVO: Salva no cache após sucesso
        uv_cache[cache_key] = (float(uv_index), time.time())
        print(f"Cache atualizado para {cache_key}: UV {uv_index}")
        
        return uv_index
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}. Using default UV index value.")
        raise Exception(f"Failed to fetch UV index: {str(e)}")
    finally:
        return uv_index