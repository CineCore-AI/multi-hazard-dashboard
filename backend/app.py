import time
import uuid
import logging
from functools import lru_cache
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# -----------------------------------
# MODEL & GEO IMPORTS (Active ✅)
# -----------------------------------
from geo.geocode import geocode
from models.heatwave_model import heatwave_model
from models.flood_model import flood_model
from models.drought_model import drought_model
from models.extreme_rainfall_model import extreme_rainfall_model
from models.landslide_model import landslide_model

# Configure logging for easier debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ENABLE CORS (Frontend ready ✅)
CORS(app)

# MODERN FLASK JSON CONFIG (Preserves response order ✅)
app.json.sort_keys = False

# -----------------------------------
# ROUTE 0: HEALTH CHECK
# -----------------------------------

@app.route("/", methods=["GET"])
def home():
    """Quick check to see if the server is alive."""
    return jsonify({"status": "API running", "version": "v7"}), 200

# -----------------------------------
# DATA FETCHING & CACHING ENGINE
# -----------------------------------

def get_historical_weather_data(lat: float, lon: float, req_id: str) -> pd.DataFrame:
    """
    TEMP: Generates dummy weather data. 
    Ready to be replaced with actual NASA/weather API fetching logic.
    """
    logger.info(f"[{req_id}] Fetching external data for coordinates: {lat}, {lon}")
    dates = pd.date_range(datetime.today() - timedelta(days=40), periods=40)

    # Simulating a slight network delay for the timer
    time.sleep(0.12) 

    return pd.DataFrame({
        "Precip_mm": np.random.uniform(0, 60, len(dates)),
        "MaxTemp_C": np.random.uniform(30, 45, len(dates))
    }, index=dates)

@lru_cache(maxsize=64)
def compute_risk_cached(lat: float, lon: float):
    """
    Caches the data fetch and model execution. 
    Returns instantly if the same lat/lon is requested.
    """
    # Using "cache" as the req_id here since it might be reused across multiple actual requests
    df = get_historical_weather_data(lat, lon, "cache")
    
    return {
        "heatwave": heatwave_model(df),
        "flood": flood_model(df),
        "drought": drought_model(df),
        "extreme_rainfall": extreme_rainfall_model(df),
        "landslide": landslide_model(df)
    }

# -----------------------------------
# ROUTE 1: SEARCH
# -----------------------------------

@app.route("/api/search", methods=["GET"])
def search():
    req_id = str(uuid.uuid4())[:8]
    place = request.args.get("place")
    
    logger.info(f"[{req_id}] Incoming /api/search for place='{place}'")

    if not place:
        return jsonify({"request_id": req_id, "error": "No place provided"}), 400

    try:
        search_start = time.time()
        result = geocode(place)
        search_time = time.time() - search_start
        logger.info(f"[{req_id}] Geocoding took {search_time:.3f}s")
        
        if not result:
            return jsonify({"request_id": req_id, "error": "Location not found"}), 404
            
        # Hydrate with tracing info
        result["request_id"] = req_id
        result["timings"] = {
            "search_s": round(search_time, 3),
            "total_s": round(search_time, 3) 
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"[{req_id}] Geocoding error: {e}", exc_info=True)
        return jsonify({"request_id": req_id, "error": "An error occurred during geocoding"}), 500

# -----------------------------------
# ROUTE 2: RISK ENGINE
# -----------------------------------

@app.route("/api/risk", methods=["GET"])
def risk():
    req_id = str(uuid.uuid4())[:8]
    lat_str = request.args.get("lat")
    lon_str = request.args.get("lon")

    logger.info(f"[{req_id}] Incoming /api/risk for lat={lat_str}, lon={lon_str}")

    if not lat_str or not lon_str:
        return jsonify({"request_id": req_id, "error": "Missing lat/lon parameters"}), 400

    # 1. Convert to float safely
    try:
        lat = round(float(lat_str), 4) # Rounding prevents microscopic float differences from breaking cache
        lon = round(float(lon_str), 4)
    except ValueError:
        return jsonify({"request_id": req_id, "error": "Coordinates must be valid numbers"}), 400

    # 2. Validate coordinate bounds
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"request_id": req_id, "error": "Coordinates out of valid range"}), 400

    # 3. Compute Risk (Cached!)
    compute_start = time.time()
    try:
        risk_data = compute_risk_cached(lat, lon)
        compute_time = time.time() - compute_start
        
        cache_status = "HIT" if compute_time < 0.05 else "MISS"
        logger.info(f"[{req_id}] Compute [Cache {cache_status}] took {compute_time:.3f}s")
        
        result = {
            "request_id": req_id,
            "location": {"lat": lat, "lon": lon},
            "timings": {
                "compute_s": round(compute_time, 3),
                "total_s": round(compute_time, 3)
            },
            **risk_data  # Unpacks the cached dictionary directly into the response!
        }
        
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"[{req_id}] Model execution error: {e}", exc_info=True)
        return jsonify({"request_id": req_id, "error": "An error occurred while calculating risk"}), 500

# -----------------------------------
# RUN SERVER
# -----------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
