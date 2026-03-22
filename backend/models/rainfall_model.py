import pandas as pd
import numpy as np
from typing import Dict, Any

MAX_RISK = 100.0
EXTREME_THRESHOLD = 100.0  # mm/day

def classify_risk(risk: float) -> str:
    if risk < 20: return "Low"
    if risk < 40: return "Mild"
    if risk < 60: return "Moderate"
    if risk < 80: return "High"
    return "Extreme"


def extreme_rainfall_model(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detects extreme rainfall events based on intensity and anomaly.
    v3: Handles zero-rain, strict typing, flat-line percentiles, and constant-series edge cases.
    """
    # 1. Validation
    if not isinstance(df, pd.DataFrame) or df.empty or "Precip_mm" not in df.columns:
        return {"risk": 0.0, "severity": "Low", "error": "Invalid input: missing or empty 'Precip_mm' data"}

    df_calc = df.copy()

    # 2. Ensure datetime index safely
    if not pd.api.types.is_datetime64_any_dtype(df_calc.index):
        try:
            df_calc.index = pd.to_datetime(df_calc.index)
        except Exception as e:
            return {"risk": 0.0, "severity": "Low", "error": f"Datetime conversion failed: {e}"}

    df_calc = df_calc.sort_index()

    # 3. Resample daily rainfall ("1D" is safer for modern pandas)
    daily_rain = df_calc["Precip_mm"].resample("1D").sum().fillna(0.0)

    if daily_rain.empty:
        return {"risk": 0.0, "severity": "Low", "error": "No valid data after resampling"}

    # 4. Current rainfall
    current_rain = float(daily_rain.iloc[-1])

    # 5 & 6 & 7. Handle factors and edge cases
    if current_rain <= 0:
        percentile = 0.0
        intensity_factor = 0.0
        anomaly_factor = 0.0
    else:
        if daily_rain.nunique() <= 1:
            percentile = 50.0
        else:
            percentile = float((daily_rain < current_rain).mean() * 100)
            
        intensity_factor = min(current_rain / EXTREME_THRESHOLD, 1.0)
        anomaly_factor = percentile / 100.0

    # 8. Risk calculation
    risk = (
        0.6 * intensity_factor +
        0.4 * anomaly_factor
    ) * MAX_RISK

    # Clip and round securely
    risk = round(float(np.clip(risk, 0.0, MAX_RISK)), 2)

    return {
        "risk": risk,
        "severity": classify_risk(risk),
        "metrics": {
            "daily_rain_mm": round(current_rain, 2),
            "percentile": round(percentile, 2),
            "intensity_factor": round(intensity_factor, 3),
            "anomaly_factor": round(anomaly_factor, 3)
        }
    }
