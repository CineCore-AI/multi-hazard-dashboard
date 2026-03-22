import numpy as np
from typing import Dict, Any

MAX_RISK = 100.0

def classify_risk(risk: float) -> str:
    """Maps numerical risk to categorical severity."""
    if risk < 20: return "Low"
    if risk < 40: return "Mild"
    if risk < 60: return "Moderate"
    if risk < 80: return "High"
    return "Extreme"

def cyclone_model_v3(distance_km: float, wind_speed: float) -> Dict[str, Any]:
    """
    Calculates cyclone risk based on proximity and wind intensity.
    
    Args:
        distance_km: Distance from the cyclone center (eye) in km.
        wind_speed: Current wind speed in km/h.
    """
    # 1. Validation: Keep severity consistent with classify_risk categories
    if any(v is None or v < 0 for v in [distance_km, wind_speed]):
        return {
            "risk": 0.0, 
            "severity": "Low", 
            "error": "Invalid input"
        }

    # 2. Distance Factor (Exponential decay)
    distance_factor = np.exp(-distance_km / 250.0) 

    # 3. Wind Factor (Quadratic scaling, strict 1.0 cap for clean normalization)
    wind_factor = min((wind_speed / 250.0) ** 2, 1.0) 

    # 4. Risk Calculation (Weighted 40% proximity, 60% wind power)
    raw_risk = (0.4 * distance_factor + 0.6 * wind_factor) * MAX_RISK
    
    # 5. Final cleanup
    risk = round(float(np.clip(raw_risk, 0.0, MAX_RISK)), 2)

    return {
        "risk": risk,
        "severity": classify_risk(risk),
        "metrics": {
            "distance_km": round(distance_km, 2),
            "wind_speed_kmh": round(wind_speed, 2),
            "distance_factor": round(distance_factor, 3),
            "wind_factor": round(wind_factor, 3),
            "impact_ratio": round(distance_factor * wind_factor, 3)
        }
    }
