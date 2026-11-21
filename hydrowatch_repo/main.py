import sys
import os
# Ensure the repo is in system path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingestion import Sentinel2IngestionPipeline
from features import fetch_catchment_weather, process_water_masks, build_ml_dataset
from model import HydroWatchForecaster

def run_end_to_end_pipeline():
    bbox = [9.355, 36.585, 9.455, 36.655]
    
    print("--- Step 1: Sentinel-2 Data Ingestion & Cloud Masking ---")
    pipeline = Sentinel2IngestionPipeline(bbox, max_cloud=15)
    scenes = pipeline.ingest_time_series(start_date="2023-01-01", end_date="2026-11-01")
    print(f"Ingested {len(scenes)} seasonal scenes.")

    print("\n--- Step 2: Feature Engineering & Catchment Weather ---")
    weather_df = fetch_catchment_weather(start_date="2023-01-01", end_date="2026-11-01")
    ts_raw_df = process_water_masks(scenes)
    dataset = build_ml_dataset(ts_raw_df, weather_df)
    print("ML feature dataset built successfully.")

    print("\n--- Step 3: Model Training & 2026 Backtest Validation ---")
    train_df = dataset[dataset["quarter"] < "2026-Q1"].copy()
    test_df = dataset[dataset["quarter"] >= "2026-Q1"].copy()

    forecaster = HydroWatchForecaster()
    forecaster.fit(train_df)
    
    results, mae, mape = forecaster.run_backtest(train_df, test_df)
    print("\n=== 2026 Backtest Validation Results ===")
    print(results[["quarter", "water_area_ha", "predicted_ha", "error_pct"]].to_string(index=False))
    print(f"\nBacktest MAE: {mae:.2f} ha")
    print(f"Backtest MAPE: {mape:.2f}%")

if __name__ == "__main__":
    run_end_to_end_pipeline()
