import pandas as pd


def heatwave_model(df, threshold=38):

    if df.empty or "MaxTemp_C" not in df.columns:
        return {
            "risk": 0,
            "severity": "Low"
        }

    df = df.copy()

    # Hot day condition
    df["HotDay"] = df["MaxTemp_C"] >= threshold

    # 2 of 3 rule
    df["Hot2of3"] = df["HotDay"].rolling(3).sum() >= 2

    # 7-day persistence
    df["Duration7d"] = df["HotDay"].rolling(7).mean()

    # Temperature exceedance
    df["Exceed"] = (df["MaxTemp_C"] - threshold).clip(lower=0)

    # Risk calculation
    risk = (
        df["Exceed"] * 8 +
        df["Duration7d"] * 40 +
        df["Hot2of3"].astype(int) * 12
    )

    risk = risk.clip(0, 100)

    latest_risk = float(risk.iloc[-1])

    return {
        "risk": latest_risk,
        "severity": classify_risk(latest_risk)
    }


def classify_risk(risk):

    if risk < 20:
        return "Low"

    elif risk < 40:
        return "Mild"

    elif risk < 60:
        return "Moderate"

    elif risk < 80:
        return "High"

    else:
        return "Extreme"
