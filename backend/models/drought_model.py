import pandas as pd
import numpy as np
from typing import Dict, Any

MAX_RISK = 100.0


def classify_risk(risk: float) -> str:
    """Classifies risk into categories based on thresholds."""
    if risk < 20:
        return "Low"
    if risk < 40:
        return "Mild"
    if risk < 60:
        return "Moderate"
    if risk < 80:
        return "High"
    return "Extreme"


def drought_model(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates drought risk based on rainfall deficit.
    Requires a DataFrame with a DatetimeIndex and 'Precip_mm'.
    """
    # 1. Strict validation
    if not isinstance(df, pd.DataFrame) or df.empty or "Precip_mm" not in df.columns:
        return {"risk": 0.0, "severity": "Low", "error": "Invalid or empty DataFrame"}

    # 2. Avoid mutating the original dataframe
    df_calc = df.copy()

    # 3. Optional Performance Tweak: 
    # Uncomment to limit dataset to ~120 days if you only need short-term 
    # relative percentiles rather than deep historical climate averages.
    # df_calc = df_calc.tail(120)

    # 4. Ensure datetime index safely
    if not pd.api.types.is_datetime64_any_dtype(df_calc.index):
        try:
            df_calc.index = pd.to_datetime(df_calc.index)
        except Exception:
            return {"risk": 0.0, "severity": "Low", "error": "Index conversion failed"}

    df_calc = df_calc.sort_index()

    # 5. Resample daily
    daily_rain = df_calc["Precip_mm"].resample("D").sum().fillna(0.0)

    # 6. Handle empty resampled data
    if daily_rain.empty:
        return {"risk": 0.0, "severity": "Low", "error": "No valid data after resampling"}

    # 7. Rolling totals (min_periods=1 prevents NaNs on small datasets)
    roll_30 = daily_rain.rolling(window=30, min_periods=1).sum()
    roll_90 = daily_rain.rolling(window=90, min_periods=1).sum()

    current_30 = roll_30.iloc[-1]
    current_90 = roll_90.iloc[-1]

    # 8. Percentile calculations (drop NaNs to keep the denominator accurate)
    percentile_30 = (roll_30.dropna() <= current_30).mean() * 100
    percentile_90 = (roll_90.dropna() <= current_90).mean() * 100

    # 9. Drought risk logic with NaN safeguarding
    if pd.isna(percentile_30) or pd.isna(percentile_90):
        risk = 0.0
    else:
        risk = (
            (1 - percentile_30 / 100) * 0.6 + 
            (1 - percentile_90 / 100) * 0.4
        ) * MAX_RISK

    # 10. Clamp risk precisely using numpy, then round
    risk = round(float(np.clip(risk, 0.0, MAX_RISK)), 2)

    # 11. Return safe standard Python types
    return {
        "risk": risk,
        "severity": classify_risk(risk),
        "metrics": {
            "30day_rain_mm": round(float(current_30), 2) if not pd.isna(current_30) else 0.0,
            "90day_rain_mm": round(float(current_90), 2) if not pd.isna(current_90) else 0.0,
            "percentile_30": round(float(percentile_30), 2) if not pd.isna(percentile_30) else 0.0,
            "percentile_90": round(float(percentile_90), 2) if not pd.isna(percentile_90) else 0.0
        }
    }
