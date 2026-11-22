"""HydroWatch module for water surface monitoring (SDG 6, 13).

Migrated from hydrowatch_repo/ as-is, including known defects.
See docs/11-spike-review.md for documented limitations.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

from core.ingestion import (
    NoDataError,
    STACClient,
    cloud_mask_from_scl,
    load_bands,
    ndwi,
)
from core.ingestion.geo import write_cog
from core.sdk.base_module import BaseSDGModule
from core.sdk.schemas import AOI, GeoLayer
from modules.hydrowatch.weather import WeatherClient


class _MLflowShim:
    """Optional MLflow shim - only active if MLflow is enabled."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._mlflow = None
        if enabled:
            try:
                import mlflow

                self._mlflow = mlflow
            except ImportError:
                self.enabled = False

    def set_tracking_uri(self, uri: str) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.set_tracking_uri(uri)

    def set_experiment(self, name: str) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.set_experiment(name)

    def start_run(self, run_name: str | None = None) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.start_run(run_name=run_name)

    def end_run(self) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.end_run()

    def log_param(self, key: str, value: Any) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.log_param(key, value)

    def log_metric(self, key: str, value: float) -> None:
        if self.enabled and self._mlflow:
            self._mlflow.log_metric(key, value)

    def log_model(self, model: Any, name: str) -> None:
        if self.enabled and self._mlflow:
            # Use trusted types for sklearn models
            self._mlflow.sklearn.log_model(
                model, name, skops_trusted_types=["sklearn.tree._tree.Tree"]
            )


class HydroWatchModule(BaseSDGModule):
    """HydroWatch module for water surface monitoring (SDG 6, 13)."""

    def __init__(self, manifest: Any, enable_mlflow: bool = True) -> None:
        super().__init__(manifest)
        # Extract parameters from manifest
        self.water_params = manifest.params.get("water", {})
        self.forecast_params = manifest.params.get("forecast", {})
        self.weather_params = manifest.params.get("weather", {})

        # STAC client - lazy initialization (created in ingest())
        self._stac_client: STACClient | None = None

        # Initialize weather client from manifest params
        self.weather_client = WeatherClient(
            url=self.weather_params.get("url", "https://archive-api.open-meteo.com/v1/archive"),
            timezone=self.weather_params.get("timezone", "Africa/Tunis"),
            precip_points=self.weather_params.get("precip_points"),
            temperature_point=self.weather_params.get("temperature_point"),
        )

        # MLflow shim
        self._mlflow = _MLflowShim(enabled=enable_mlflow)

        # Pixel classifier (trained in train())
        self._pixel_clf: RandomForestClassifier | None = None
        # Forecaster (trained in train())
        self._forecaster: RandomForestRegressor | None = None
        # Training cutoff quarter
        self._train_cutoff: str | None = None

        # Load AOI geometry for exports
        self._aoi_geometry = self._load_aoi_geometry()

    @property
    def stac_client(self) -> STACClient:
        """Lazy initialization of STAC client."""
        if self._stac_client is None:
            self._stac_client = STACClient()
        return self._stac_client

    def _load_aoi_geometry(self) -> dict[str, Any]:
        """Load AOI geometry from configs/tunisia_aois.geojson."""
        import yaml

        with open("configs/tunisia_aois.geojson") as f:
            geojson = yaml.safe_load(f)
        for feature in geojson["features"]:
            if feature["properties"]["id"] == self.manifest.aoi_id:
                return feature["geometry"]
        raise NoDataError(f"AOI {self.manifest.aoi_id} not found in configs/tunisia_aois.geojson")

    def _init_mlflow(self, run_name: str | None = None) -> None:
        """Initialize MLflow tracking."""
        self._mlflow.set_tracking_uri("file:./mlruns")
        self._mlflow.set_experiment(self.manifest.id)
        self._mlflow.start_run(run_name=run_name)

    def _log_params(self, params: dict) -> None:
        """Log parameters to MLflow."""
        # Log key parameters
        self._mlflow.log_param("module_id", self.manifest.id)
        self._mlflow.log_param("module_version", self.manifest.version)
        self._mlflow.log_param("seed", params.get("seed", 42))

        # Water params
        self._mlflow.log_param(
            "weak_label_ndwi_threshold", self.water_params.get("weak_label_ndwi_threshold")
        )
        self._mlflow.log_param("train_sample_pixels", self.water_params.get("train_sample_pixels"))
        self._mlflow.log_param(
            "pixel_clf_n_estimators",
            self.water_params.get("pixel_classifier", {}).get("n_estimators"),
        )
        self._mlflow.log_param(
            "pixel_clf_max_depth", self.water_params.get("pixel_classifier", {}).get("max_depth")
        )

        # Forecast params
        self._mlflow.log_param(
            "forecaster_n_estimators", self.forecast_params.get("model", {}).get("n_estimators")
        )
        self._mlflow.log_param(
            "forecaster_max_depth", self.forecast_params.get("model", {}).get("max_depth")
        )
        self._mlflow.log_param("test_start_quarter", self.forecast_params.get("test_start_quarter"))

        # Weather params
        self._mlflow.log_param(
            "precip_points_count", len(self.weather_params.get("precip_points", {}))
        )
        weights = list(self.weather_params.get("precip_points", {}).values())
        if weights:
            self._mlflow.log_param("precip_weight_upper", weights[0].get("weight"))
            self._mlflow.log_param("precip_weight_mid", weights[1].get("weight"))
            self._mlflow.log_param("precip_weight_local", weights[2].get("weight"))

    def ingest(self, aoi: AOI, date_range: tuple[date, date], params: dict) -> dict[str, Any]:
        """
        Search Sentinel-2 L2A scenes and fetch weather data.

        Returns:
            Dict with "items" (list of selected STAC items) and "weather" (DataFrame)
        """
        # Get STAC params from global config + manifest
        max_cloud = params.get("max_cloud", 15)
        collections = params.get("collections", ["sentinel-2-l2a"])

        # Search STAC
        items = self.stac_client.search(aoi, date_range, collections, max_cloud)

        # Select first scene per quarter
        selected_items = self.stac_client.select_first_per_quarter(items)

        # Fetch weather data
        weather_df = self.weather_client.fetch_catchment_weather(
            date_range[0],
            date_range[1],
            cache_dir=Path("data/raw/weather"),
        )

        return {
            "items": selected_items,
            "weather": weather_df,
        }

    def compute_indices(self, items: list, params: dict) -> list[dict[str, Any]]:
        """
        Compute NDWI and cloud mask for each scene.

        Args:
            items: List of STAC items from ingest()
            params: Parameters including scl_cloud_classes

        Returns:
            List of per-scene records with ndwi, cloud_mask, transform, crs, date, quarter
        """
        scl_cloud_classes = params.get("scl_cloud_classes", [3, 8, 9, 10])
        aoi = params.get("aoi")

        records = []

        for item in items:
            # Load bands: B03 (green), B08 (nir), SCL
            bands = load_bands(
                item,
                band_names=["B03", "B08", "SCL"],
                aoi=aoi,
                target_resolution=None,  # Read at native resolution
            )

            green_data, green_transform, green_crs = bands["B03"]
            nir_data, _, _ = bands["B08"]
            scl_data, _, _ = bands["SCL"]

            # Compute NDWI using raw DN (as in spike - defect #2 in spike review)
            ndwi_data = ndwi(green_data.astype(np.float32), nir_data.astype(np.float32))

            # Cloud mask from SCL
            cloud_mask = cloud_mask_from_scl(scl_data, scl_cloud_classes)

            # Extract date and quarter
            dt = item.datetime
            if dt is None:
                continue
            date_str = dt.strftime("%Y-%m-%d")
            quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"

            records.append(
                {
                    "date": date_str,
                    "quarter": quarter,
                    "ndwi": ndwi_data,
                    "cloud_mask": cloud_mask,
                    "transform": green_transform,
                    "crs": green_crs,
                }
            )

        return records

    def _segment_scenes(self, scenes: list[dict], params: dict) -> pd.DataFrame:
        """
        Apply pixel classifier to extract water surface area time series.

        This is a shared helper used by both train() and infer().
        """
        water_params = params.get("water", {})
        weak_label_threshold = water_params.get("weak_label_ndwi_threshold", 0.05)
        train_on = water_params.get("train_on", "first_scene")
        train_sample_pixels = water_params.get("train_sample_pixels", 20000)
        clf_params = water_params.get("pixel_classifier", {"n_estimators": 50, "max_depth": 8})
        seed = params.get("seed", 42)

        timeseries = []

        for i, rec in enumerate(scenes):
            ndwi_data = rec["ndwi"]
            cloud_mask = rec["cloud_mask"]

            # Features: NDWI + two spatial gradients
            X = np.column_stack(
                [
                    ndwi_data.ravel(),
                    np.gradient(ndwi_data, axis=0).ravel(),
                    np.gradient(ndwi_data, axis=1).ravel(),
                ]
            )

            # Weak labels: ndwi > threshold
            y_weak = (ndwi_data.ravel() > weak_label_threshold).astype(int)

            # Train pixel classifier on first scene (or as configured)
            if i == 0 or (train_on == "first_scene" and self._pixel_clf is None):
                self._pixel_clf = RandomForestClassifier(
                    n_estimators=clf_params.get("n_estimators", 50),
                    max_depth=clf_params.get("max_depth", 8),
                    random_state=seed,
                    n_jobs=-1,
                )
                rng = np.random.RandomState(seed)
                idx = rng.choice(len(X), size=min(train_sample_pixels, len(X)), replace=False)
                self._pixel_clf.fit(X[idx], y_weak[idx])

            # Predict water mask
            if self._pixel_clf is None:
                raise RuntimeError("Pixel classifier not trained")

            preds = self._pixel_clf.predict(X)
            water_mask = preds.reshape(ndwi_data.shape).astype(np.uint8)

            # Cloud pixels forced to 0 (non-water) - defect #3 in spike review
            clean_water_mask = np.where(cloud_mask, 0, water_mask)
            rec["water_mask"] = clean_water_mask

            # Area in hectares (0.01 ha per 10m pixel - defect #11 in spike review)
            area_ha = round(int(clean_water_mask.sum()) * 0.01, 2)
            timeseries.append(
                {
                    "quarter": rec["quarter"],
                    "water_area_ha": area_ha,
                }
            )

        return pd.DataFrame(timeseries)

    def _build_ml_dataset(self, ts_df: pd.DataFrame, basin_df: pd.DataFrame) -> pd.DataFrame:
        """Build ML dataset with lag features (as in spike features.py)."""
        df = ts_df.merge(basin_df, on="quarter", how="left").fillna(0)

        # Weighted catchment precipitation
        if "weighted_catchment_precip_mm" not in df.columns:
            # Compute from individual points if not present
            weights = {
                name: p["weight"]
                for name, p in self.weather_params.get("precip_points", {}).items()
            }
            precip_cols = [
                f"{name}_precip_mm" for name in self.weather_params.get("precip_points", {}).keys()
            ]
            if precip_cols and all(c in df.columns for c in precip_cols):
                df["weighted_catchment_precip_mm"] = sum(
                    df[col] * weights[name]
                    for name, col in zip(
                        self.weather_params.get("precip_points", {}).keys(),
                        precip_cols,
                        strict=False,
                    )
                )

        # Lag features (with bfill as in spike - defect #8)
        df["lag_1_area"] = df["water_area_ha"].shift(1).bfill()
        df["lag_1_catchment_precip_mm"] = df["weighted_catchment_precip_mm"].shift(1).bfill()

        # Quarterly cyclical features
        df["q_num"] = df["quarter"].str[-1].astype(int)
        df["sin_q"] = np.sin(2 * np.pi * df["q_num"] / 4.0)
        df["cos_q"] = np.cos(2 * np.pi * df["q_num"] / 4.0)

        return df

    def train(self, dataset: dict[str, Any], params: dict) -> dict[str, Any]:
        """
        Train pixel classifier and forecaster.

        Args:
            dataset: Dict with "records" (from compute_indices) and "weather" (from ingest)
            params: Training parameters

        Returns:
            Model artifact with pixel_clf, forecaster, train_cutoff
        """
        self._init_mlflow(run_name="train")
        try:
            self._log_params(params)

            records = dataset["records"]
            weather_df = dataset["weather"]

            # Generate water area time series using pixel classifier
            ts_df = self._segment_scenes(records, params)

            # Build ML dataset
            ml_df = self._build_ml_dataset(ts_df, weather_df)

            # Split train/test by quarter
            test_start = self.forecast_params.get("test_start_quarter", "2026-Q1")
            train_df = ml_df[ml_df["quarter"] < test_start].copy()
            ml_df[ml_df["quarter"] >= test_start].copy()

            if len(train_df) == 0:
                raise NoDataError(f"No training data before {test_start}")

            # Train forecaster
            feature_cols = self.forecast_params.get(
                "features",
                [
                    "lag_1_area",
                    "weighted_catchment_precip_mm",
                    "lag_1_catchment_precip_mm",
                    "mean_temp_c",
                    "sin_q",
                    "cos_q",
                ],
            )

            model_params = self.forecast_params.get("model", {"n_estimators": 150, "max_depth": 4})
            seed = params.get("seed", 42)

            self._forecaster = RandomForestRegressor(
                n_estimators=model_params.get("n_estimators", 150),
                max_depth=model_params.get("max_depth", 4),
                random_state=seed,
            )

            self._forecaster.fit(train_df[feature_cols], train_df["water_area_ha"])
            self._train_cutoff = test_start

            # Log model to MLflow
            self._mlflow.log_model(self._forecaster, "forecaster")
            self._mlflow.log_model(self._pixel_clf, "pixel_classifier")

            # Log training metrics
            train_pred = self._forecaster.predict(train_df[feature_cols])
            train_mae = mean_absolute_error(train_df["water_area_ha"], train_pred)
            train_mape = mean_absolute_percentage_error(train_df["water_area_ha"], train_pred) * 100
            self._mlflow.log_metric("train_mae_ha", train_mae)
            self._mlflow.log_metric("train_mape_pct", train_mape)
            self._mlflow.log_metric("train_samples", len(train_df))

            return {
                "pixel_clf": self._pixel_clf,
                "forecaster": self._forecaster,
                "train_cutoff": self._train_cutoff,
                "feature_cols": feature_cols,
            }
        finally:
            self._mlflow.end_run()

    def infer(self, dataset: dict[str, Any], model: dict[str, Any], params: dict) -> dict[str, Any]:
        """
        Run inference: pixel classification + recursive forecasting.

        Args:
            dataset: Dict with "records" and "weather"
            model: Model artifact from train()
            params: Inference parameters

        Returns:
            Dict with "records" (with water_mask), "area_ts", "backtest"
        """
        self._init_mlflow(run_name="infer")
        try:
            records = dataset["records"]
            weather_df = dataset["weather"]

            forecaster = model["forecaster"]
            feature_cols = model["feature_cols"]
            train_cutoff = model["train_cutoff"]

            # Generate water area time series for all scenes
            ts_df = self._segment_scenes(records, params)

            # Build ML dataset
            ml_df = self._build_ml_dataset(ts_df, weather_df)

            # Split train/test
            train_df = ml_df[ml_df["quarter"] < train_cutoff].copy()
            test_df = ml_df[ml_df["quarter"] >= train_cutoff].copy()

            # Initialize predicted_ha column (will be filled for test quarters)
            test_df["predicted_ha"] = np.nan
            test_df["error_pct"] = np.nan

            # Recursive walk-forward backtest (as in spike model.py)
            backtest_preds = []
            if len(train_df) > 0:
                prev_area = train_df["water_area_ha"].iloc[-1]
            else:
                prev_area = 0.0

            for i, row in test_df.reset_index(drop=True).iterrows():
                prev_precip = (
                    train_df["weighted_catchment_precip_mm"].iloc[-1]
                    if i == 0 and len(train_df) > 0
                    else (test_df["weighted_catchment_precip_mm"].iloc[i - 1] if i > 0 else 0.0)
                )

                X_row = pd.DataFrame(
                    [
                        {
                            "lag_1_area": prev_area,
                            "weighted_catchment_precip_mm": row["weighted_catchment_precip_mm"],
                            "lag_1_catchment_precip_mm": prev_precip,
                            "mean_temp_c": row["mean_temp_c"],
                            "sin_q": row["sin_q"],
                            "cos_q": row["cos_q"],
                        }
                    ]
                )

                pred = float(forecaster.predict(X_row[feature_cols])[0])
                backtest_preds.append(round(pred, 2))
                prev_area = pred

                test_df.loc[test_df.index[i], "predicted_ha"] = round(pred, 2)

            # Compute error percentage (hindcast with oracle weather - defect #4)
            if len(test_df) > 0:
                test_df["error_pct"] = (
                    np.abs(test_df["water_area_ha"] - test_df["predicted_ha"])
                    / test_df["water_area_ha"]
                    * 100
                ).round(2)

            # Combine train and test for full area time series
            train_part = train_df[["quarter", "water_area_ha"]].rename(
                columns={"water_area_ha": "area_ha"}
            )
            if len(test_df) > 0:
                test_part = test_df[["quarter", "water_area_ha", "predicted_ha"]].rename(
                    columns={"water_area_ha": "area_ha"}
                )
                area_ts = pd.concat([train_part, test_part], ignore_index=True)
            else:
                area_ts = train_part.copy()

            return {
                "records": records,
                "area_ts": area_ts,
                "backtest": test_df[["quarter", "water_area_ha", "predicted_ha", "error_pct"]],
            }
        finally:
            self._mlflow.end_run()

    def evaluate(
        self, predictions: dict[str, Any], reference: Any, params: dict
    ) -> dict[str, float]:
        """
        Evaluate forecast metrics.

        Args:
            predictions: Output from infer() with "backtest" DataFrame
            reference: Not used (no external ground truth - defect #6)
            params: Evaluation parameters

        Returns:
            Dict with MAE (ha), MAPE (%), and per-quarter errors
        """
        self._init_mlflow(run_name="evaluate")
        try:
            backtest = predictions["backtest"]

            if len(backtest) == 0:
                return {"mae_ha": 0.0, "mape_pct": 0.0, "n_quarters": 0}

            # Reference is satellite-derived area (same as predictions["area_ts"] for test quarters)
            y_true = backtest["water_area_ha"].values
            y_pred = backtest["predicted_ha"].values

            mae = mean_absolute_error(y_true, y_pred)
            mape = mean_absolute_percentage_error(y_true, y_pred) * 100

            metrics = {
                "mae_ha": round(float(mae), 2),
                "mape_pct": round(float(mape), 2),
                "n_quarters": len(backtest),
            }

            # Add per-quarter errors
            for _, row in backtest.iterrows():
                metrics[f"error_pct_{row['quarter']}"] = float(row["error_pct"])

            # Log to MLflow
            self._mlflow.log_metric("test_mae_ha", metrics["mae_ha"])
            self._mlflow.log_metric("test_mape_pct", metrics["mape_pct"])
            self._mlflow.log_metric("test_samples", metrics["n_quarters"])
            for key, value in metrics.items():
                if key.startswith("error_pct_"):
                    self._mlflow.log_metric(key, value)

            return metrics
        finally:
            self._mlflow.end_run()

    def export_layers(self, predictions: dict[str, Any], out_dir: Path) -> list[GeoLayer]:
        """
        Export water mask COGs and area time series as GeoParquet.

        Args:
            predictions: Output from infer() with "records" and "area_ts"
            out_dir: Output directory

        Returns:
            List of GeoLayer objects
        """
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        layers = []
        records = predictions["records"]
        area_ts = predictions["area_ts"]

        # Export water mask COG per quarter
        for rec in records:
            if "water_mask" not in rec:
                continue

            quarter = rec["quarter"]
            water_mask = rec["water_mask"]
            transform = rec["transform"]
            crs = rec["crs"]

            cog_path = out_dir / f"water_mask_{quarter}.tif"
            write_cog(
                water_mask,
                transform,
                crs,
                cog_path,
                dtype="uint8",
                nodata=0,
            )

            # Parse quarter like "2024-Q1" -> date(2024, 1, 1)
            year, q = quarter.split("-Q")
            month = (int(q) - 1) * 3 + 1
            approx_date = pd.Timestamp(year=int(year), month=month, day=1).date()

            layers.append(
                GeoLayer(
                    module_id=self.manifest.id,
                    name=f"water_mask_{quarter}",
                    kind="cog",
                    path=cog_path,
                    time=approx_date,
                    bbox=None,
                )
            )

        # Export area time series as GeoParquet with AOI geometry
        import geopandas as gpd
        from shapely.geometry import shape

        aoi_shape = shape(self._aoi_geometry)

        gdf = gpd.GeoDataFrame(
            area_ts.copy(),
            geometry=[aoi_shape] * len(area_ts),
            crs="EPSG:4326",
        )

        ts_path = out_dir / "area_timeseries.parquet"
        gdf.to_parquet(ts_path, index=False)

        layers.append(
            GeoLayer(
                module_id=self.manifest.id,
                name="area_timeseries",
                kind="geoparquet",
                path=ts_path,
                time=None,
                bbox=None,
            )
        )

        return layers
