import pandas as pd
from typing import Dict, Any

# ==========================================
# FLOOD MODEL CONFIGURATION
# ==========================================

P3_REF = 100.0      # mm rainfall in 3 days
P7_REF = 150.0      # mm rainfall in 7 days
P30_REF = 400.0     # mm rainfall in 30 days

WEIGHT_R3 = 0.45
WEIGHT_R7 = 0.30
WEIGHT_R30 = 0.25

MAX_RISK = 100.0


def classify_risk(risk: float) -> str:
    """Classifies the numerical risk score into a severity category."""
    if risk < 20:
        return "Low"
    if risk < 40:
        return "Mild"
    if risk < 60:
        return "Moderate"
    if risk < 80:
        return "High"
    return "Extreme"


def flood_model(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates flood risk based on accumulated rainfall.
    Expects a pandas DataFrame with a DatetimeIndex and a 'Precip_mm' column.
    """
    # 1. Base case: invalid type, empty, or missing data
    if not isinstance(df, pd.DataFrame) or df.empty or "Precip_mm" not in df.columns:
        return {
            "risk": 0.0,
            "severity": "Low",
            "metrics": {
                "rain_3day_mm": 0.0,
                "rain_7day_mm": 0.0,
                "rain_30day_mm": 0.0
            }
        }

    # 2. Ensure the index is datetime for safe time-based operations
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError("DataFrame index must be a datetime object or convertible to datetime.")

    # 3. OPTIMIZATION: Keep only the last 30 days of data
    # This speeds up sorting and resampling on massive historical datasets safely.
    cutoff_date = df.index.max() - pd.Timedelta(days=30)
    df = df[df.index >= cutoff_date]

    # Sort to ensure chronological order
    df = df.sort_index()

    # 4. Resample to daily frequency ('1D') and sum. 
    # This guarantees that exactly 3 days equals 3 rows, filling missing days with 0.
    daily_rain = df["Precip_mm"].resample("1D").sum().fillna(0.0)

    # Accumulations
    rain_3 = float(daily_rain.tail(3).sum())
    rain_7 = float(daily_rain.tail(7).sum())
    rain_30 = float(daily_rain.tail(30).sum())

    # 5. Normalize rainfall (with division-by-zero safeguards)
    r3_norm = min(rain_3 / P3_REF, 1.0) if P3_REF > 0 else 0.0
    r7_norm = min(rain_7 / P7_REF, 1.0) if P7_REF > 0 else 0.0
    r30_norm = min(rain_30 / P30_REF, 1.0) if P30_REF > 0 else 0.0

    # 6. Risk calculation
    risk = (
        WEIGHT_R3 * r3_norm +
        WEIGHT_R7 * r7_norm +
        WEIGHT_R30 * r30_norm
    ) * MAX_RISK

    # Clamp bounds and round
    risk = round(max(0.0, min(risk, MAX_RISK)), 2)

    return {
        "risk": risk,
        "severity": classify_risk(risk),
        "metrics": {
            "rain_3day_mm": round(rain_3, 2),
            "rain_7day_mm": round(rain_7, 2),
            "rain_30day_mm": round(rain_30, 2)
        }
    }
