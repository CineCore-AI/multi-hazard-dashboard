import pandas as pd
import numpy as np
from typing import Dict, Any

MAX_RISK = 100.0
TRIGGER_REF = 120.0   
SATURATION_REF = 300.0 

def classify_risk(risk: float) -> str:
    """Standardized risk classification for frontend consistency."""
    if risk < 20: return "Low"
    if risk < 40: return "Mild"
    if risk < 60: return "Moderate"
    if risk < 80: return "High"
    return "Extreme"


def landslide_model(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Estimates landslide risk using a Trigger-Cause model with 
    weighted data confidence scaling.
    """
    # 1. Validation & Consistency
    # Always return 'Low' severity on failure to prevent frontend crashes
    if not isinstance(df, pd.DataFrame) or df.empty or "Precip_mm" not in df.columns:
        return {"risk": 0.0, "severity": "Low", "error": "Invalid input format"}

    df_calc = df.copy()

    # 2. Datetime Handling
    if not pd.api.types.is_datetime64_any_dtype(df_calc.index):
        try:
            df_calc.index = pd.to_datetime(df_calc.index)
        except Exception as e:
            return {"risk": 0.0, "severity": "Low", "error": f"Index error: {e}"}

    df_calc = df_calc.sort_index()

    # 3. Daily Resampling
    daily_rain = df_calc["Precip_mm"].resample("1D").sum().fillna(0.0)
    days_available = len(daily_rain)

    if days_available < 1:
        return {"risk": 0.0, "severity": "Low", "error": "No daily data points"}

    # 4. Metric Calculation
    rain_3 = float(daily_rain.tail(3).sum())
    rain_30 = float(daily_rain.tail(30).sum())

    # 5. Normalized Factors (Capped at 1.0)
    trigger_factor = min(rain_3 / TRIGGER_REF, 1.0)
    saturation_factor = min(rain_30 / SATURATION_REF, 1.0)

    # 6. Risk & Confidence Scaling
    # Logic: 60% weight on immediate trigger, 40% on long-term saturation
    raw_risk = (0.60 * trigger_factor + 0.40 * saturation_factor) * MAX_RISK
    
    # Apply confidence: Risk is penalized if we lack a full 30-day history
    confidence_multiplier = 1.0 if days_available >= 30 else (days_available / 30.0)
    
    final_risk = raw_risk * confidence_multiplier
    final_risk = round(float(np.clip(final_risk, 0.0, MAX_RISK)), 2)

    return {
        "risk": final_risk,
        "severity": classify_risk(final_risk),
        "data_confidence": round(confidence_multiplier, 2),
        "metrics": {
            "rain_3day_mm": round(rain_3, 2),
            "rain_30day_mm": round(rain_30, 2),
            "trigger_factor": round(trigger_factor, 3),
            "saturation_factor": round(saturation_factor, 3)
        }
    }
