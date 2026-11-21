import requests
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def fetch_catchment_weather(start_date="2023-01-01", end_date="2026-11-01"):
    """
    Queries and aggregates historical multi-point rainfall across the Medjerda basin.
    """
    locations = {
        "upper_algeria": {"lat": 36.28, "lon": 7.95},
        "mid_border": {"lat": 36.45, "lon": 8.44},
        "local_beja": {"lat": 36.62, "lon": 9.40}
    }

    dfs = []
    for key, loc in locations.items():
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={loc['lat']}&longitude={loc['lon']}&start_date={start_date}&end_date={end_date}"
            f"&daily=precipitation_sum&timezone=Africa%2FTunis"
        )
        res = requests.get(url).json()["daily"]
        w_df = pd.DataFrame(res)
        w_df["date"] = pd.to_datetime(w_df["time"])
        w_df["quarter"] = w_df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")

        q_df = w_df.groupby("quarter").agg(
            **{f"{key}_precip_mm": ("precipitation_sum", "sum")}
        ).reset_index()
        dfs.append(q_df)

    basin_df = dfs[0]
    for d in dfs[1:]:
        basin_df = basin_df.merge(d, on="quarter", how="left")

    temp_url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude=36.62&longitude=9.40&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_mean&timezone=Africa%2FTunis"
    )
    res_temp = requests.get(temp_url).json()["daily"]
    t_df = pd.DataFrame(res_temp)
    t_df["date"] = pd.to_datetime(t_df["time"])
    t_df["quarter"] = t_df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")
    temp_q = t_df.groupby("quarter").agg(mean_temp_c=("temperature_2m_mean", "mean")).reset_index()

    basin_df = basin_df.merge(temp_q, on="quarter", how="left")
    return basin_df

def process_water_masks(scenes, seed=42):
    """
    Applies an RF pixel classifier to extract the final water surface area time series.
    """
    timeseries = []
    for i, rec in enumerate(scenes):
        ndwi = rec["ndwi"]
        cloud_mask = rec["cloud_mask"]

        X = np.column_stack([
            ndwi.ravel(),
            np.gradient(ndwi, axis=0).ravel(),
            np.gradient(ndwi, axis=1).ravel()
        ])
        y_weak = (ndwi.ravel() > 0.05).astype(int)

        if i == 0:
            clf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=seed, n_jobs=-1)
            idx = np.random.RandomState(seed).choice(len(X), size=min(20000, len(X)), replace=False)
            clf.fit(X[idx], y_weak[idx])

        preds = clf.predict(X)
        water_mask = preds.reshape(ndwi.shape).astype(np.uint8)
        clean_water_mask = np.where(cloud_mask, 0, water_mask)
        rec["water_mask"] = clean_water_mask

        area_ha = round(int(clean_water_mask.sum()) * 0.01, 2)
        timeseries.append({
            "quarter": rec["quarter"],
            "water_area_ha": area_ha
        })

    return pd.DataFrame(timeseries)

def build_ml_dataset(ts_df, basin_df):
    """
    Combines time series with weather data and engineers hydrological lag features.
    """
    df = ts_df.merge(basin_df, on="quarter", how="left").fillna(0)
    df["weighted_catchment_precip_mm"] = (
        0.45 * df["upper_algeria_precip_mm"] +
        0.35 * df["mid_border_precip_mm"] +
        0.20 * df["local_beja_precip_mm"]
    )
    df["lag_1_area"] = df["water_area_ha"].shift(1).bfill()
    df["lag_1_catchment_precip_mm"] = df["weighted_catchment_precip_mm"].shift(1).bfill()
    df["q_num"] = df["quarter"].str[-1].astype(int)
    df["sin_q"] = np.sin(2 * np.pi * df["q_num"] / 4.0)
    df["cos_q"] = np.cos(2 * np.pi * df["q_num"] / 4.0)
    return df
