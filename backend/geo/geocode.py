import requests
import logging
from functools import lru_cache
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def is_pincode(input_str: str) -> bool:
    """Checks if the input string is a valid 6-digit Indian PIN code."""
    return input_str.isdigit() and len(input_str) == 6

# 1. The Public Function (Handles the cleaning)
def geocode(input_value: str) -> Optional[Dict[str, Any]]:
    """Geocodes a place name or PIN. Cleans input for optimal caching."""
    if not input_value:
        return None
    
    # Clean it BEFORE it hits the cache!
    clean_input = input_value.strip().lower()
    
    if not clean_input:
        return None
        
    return _geocode_cached(clean_input)

# 2. The Private Cached Function (Does the heavy lifting)
@lru_cache(maxsize=128)
def _geocode_cached(clean_input: str) -> Optional[Dict[str, Any]]:
    """Internal function that actually calls the API."""
    url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        "format": "json",
        "limit": 1
    }

    if is_pincode(clean_input):
        params["postalcode"] = clean_input
        params["countrycodes"] = "in"
    else:
        params["q"] = f"{clean_input}, India"
        params["countrycodes"] = "in"

    try:
        response = requests.get(
            url,
            params=params,
            headers={"User-Agent": "hazard-app/3.1"}, 
            timeout=10 
        )
        response.raise_for_status() 
        data = response.json()

        if not data:
            logging.warning(f"No location found for: '{clean_input}'")
            return None

        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "name": data[0]["display_name"]
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Network/API Error for '{clean_input}': {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logging.error(f"Data parsing error for '{clean_input}': {e}")
        return None

# --- Example Usage ---
if __name__ == "__main__":
    print("1. Fetching 'Chennai'...")
    print(geocode("Chennai"))

    print("\n2. Fetching '  chennai  ' (Hits the exact same cache now!)...")
    print(geocode("  chennai  "))
