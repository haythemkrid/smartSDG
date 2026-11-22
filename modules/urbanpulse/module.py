"""UrbanPulse module for built-up area monitoring (SDG 11).

Contract-compliant skeleton with synthetic outputs on the Grand Tunis AOI.
NDBI = (B11 - B08) / (B11 + B08). Real thermal/heat-island science is post-MVP.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from core.ingestion import (
    NoDataError,
    STACClient,
    cloud_mask_from_scl,
    load_bands,
    ndbi,
)
from core.ingestion.geo import write_cog
from core.sdk.base_module import BaseSDGModule
from core.sdk.schemas import AOI, GeoLayer


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
            self._mlflow.sklearn.log_model(
                model, name, skops_trusted_types=["sklearn.tree._tree.Tree"]
            )


class UrbanPulseModule(BaseSDGModule):
    """UrbanPulse module for built-up area monitoring (SDG 11)."""

    def __init__(self, manifest: Any, enable_mlflow: bool = True) -> None:
        super().__init__(manifest)
        # Extract parameters from manifest
        self.ndbi_params = manifest.params.get("ndbi", {})

        # STAC client - lazy initialization (created in ingest())
        self._stac_client: STACClient | None = None

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
        self._mlflow.log_param("module_id", self.manifest.id)
        self._mlflow.log_param("module_version", self.manifest.version)
        self._mlflow.log_param("seed", params.get("seed", 42))

        # NDBI params
        self._mlflow.log_param("builtup_threshold", self.ndbi_params.get("builtup_threshold"))
        self._mlflow.log_param("train_sample_pixels", self.ndbi_params.get("train_sample_pixels"))
        self._mlflow.log_param(
            "pixel_clf_n_estimators",
            self.ndbi_params.get("pixel_classifier", {}).get("n_estimators"),
        )
        self._mlflow.log_param(
            "pixel_clf_max_depth", self.ndbi_params.get("pixel_classifier", {}).get("max_depth")
        )

    def ingest(self, aoi: AOI, date_range: tuple[date, date], params: dict) -> dict[str, Any]:
        """
        Search Sentinel-2 L2A scenes.

        Returns:
            Dict with "items" (list of selected STAC items)
        """
        max_cloud = params.get("max_cloud", 15)
        collections = params.get("collections", ["sentinel-2-l2a"])

        # Search STAC
        items = self.stac_client.search(aoi, date_range, collections, max_cloud)

        # Select first scene per quarter
        selected_items = self.stac_client.select_first_per_quarter(items)

        return {"items": selected_items}

    def compute_indices(self, items: list, params: dict) -> list[dict[str, Any]]:
        """
        Compute NDBI and cloud mask for each scene.

        Args:
            items: List of STAC items from ingest()
            params: Parameters including scl_cloud_classes

        Returns:
            List of per-scene records with ndbi, cloud_mask, transform, crs, date, quarter
        """
        scl_cloud_classes = params.get("scl_cloud_classes", [3, 8, 9, 10])
        aoi = params.get("aoi")

        records = []

        for item in items:
            # Load bands: B08 (nir), B11 (swir), SCL
            bands = load_bands(
                item,
                band_names=["B08", "B11", "SCL"],
                aoi=aoi,
                target_resolution=None,  # Read at native resolution
            )

            nir_data, nir_transform, nir_crs = bands["B08"]
            swir_data, _, _ = bands["B11"]
            scl_data, _, _ = bands["SCL"]

            # Compute NDBI using raw DN
            ndbi_data = ndbi(swir_data.astype(np.float32), nir_data.astype(np.float32))

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
                    "ndbi": ndbi_data,
                    "cloud_mask": cloud_mask,
                    "transform": nir_transform,
                    "crs": nir_crs,
                }
            )

        return records

    def _segment_scenes(self, scenes: list[dict], params: dict) -> pd.DataFrame:
        """
        Apply pixel classifier to extract built-up area time series.

        This is a shared helper used by both train() and infer().
        """
        ndbi_params = params.get("ndbi", {})
        builtup_threshold = ndbi_params.get("builtup_threshold", 0.0)
        train_sample_pixels = ndbi_params.get("train_sample_pixels", 10000)
        clf_params = ndbi_params.get("pixel_classifier", {"n_estimators": 50, "max_depth": 8})
        seed = params.get("seed", 42)

        timeseries = []

        for i, rec in enumerate(scenes):
            ndbi_data = rec["ndbi"]
            cloud_mask = rec["cloud_mask"]

            # Features: NDBI + two spatial gradients
            X = np.column_stack(
                [
                    ndbi_data.ravel(),
                    np.gradient(ndbi_data, axis=0).ravel(),
                    np.gradient(ndbi_data, axis=1).ravel(),
                ]
            )

            # Weak labels: ndbi > threshold
            y_weak = (ndbi_data.ravel() > builtup_threshold).astype(int)

            # Train pixel classifier on first scene (or as configured)
            if i == 0 or self._pixel_clf is None:
                self._pixel_clf = RandomForestClassifier(
                    n_estimators=clf_params.get("n_estimators", 50),
                    max_depth=clf_params.get("max_depth", 8),
                    random_state=seed,
                    n_jobs=-1,
                )
                rng = np.random.RandomState(seed)
                idx = rng.choice(len(X), size=min(train_sample_pixels, len(X)), replace=False)
                self._pixel_clf.fit(X[idx], y_weak[idx])

            # Predict built-up mask
            if self._pixel_clf is None:
                raise RuntimeError("Pixel classifier not trained")

            preds = self._pixel_clf.predict(X)
            builtup_mask = preds.reshape(ndbi_data.shape).astype(np.uint8)

            # Cloud pixels forced to 0 (non-builtup)
            clean_builtup_mask = np.where(cloud_mask, 0, builtup_mask)
            rec["builtup_mask"] = clean_builtup_mask

            # Area in hectares (0.01 ha per 10m pixel)
            area_ha = round(int(clean_builtup_mask.sum()) * 0.01, 2)
            timeseries.append(
                {
                    "quarter": rec["quarter"],
                    "builtup_area_ha": area_ha,
                }
            )

        return pd.DataFrame(timeseries)

    def train(self, dataset: dict[str, Any], params: dict) -> dict[str, Any]:
        """
        Train pixel classifier.

        Args:
            dataset: Dict with "records" (from compute_indices)
            params: Training parameters

        Returns:
            Model artifact with pixel_clf
        """
        self._init_mlflow(run_name="train")
        try:
            self._log_params(params)

            records = dataset["records"]

            # Generate built-up area time series using pixel classifier (to train classifier)
            self._segment_scenes(records, params)

            # For skeleton: just return the pixel classifier
            # No forecaster for UrbanPulse skeleton
            self._train_cutoff = "2026-Q1"  # placeholder

            # Log model to MLflow
            self._mlflow.log_model(self._pixel_clf, "pixel_classifier")

            return {
                "pixel_clf": self._pixel_clf,
                "train_cutoff": self._train_cutoff,
            }
        finally:
            self._mlflow.end_run()

    def infer(self, dataset: dict[str, Any], model: dict[str, Any], params: dict) -> dict[str, Any]:
        """
        Run inference: pixel classification only (no forecasting for skeleton).

        Args:
            dataset: Dict with "records"
            model: Model artifact from train()
            params: Inference parameters

        Returns:
            Dict with "records" (with builtup_mask), "area_ts"
        """
        self._init_mlflow(run_name="infer")
        try:
            records = dataset["records"]

            # Generate built-up area time series for all scenes
            ts_df = self._segment_scenes(records, params)

            return {
                "records": records,
                "area_ts": ts_df,
            }
        finally:
            self._mlflow.end_run()

    def evaluate(
        self, predictions: dict[str, Any], reference: Any, params: dict
    ) -> dict[str, float]:
        """
        Evaluate metrics (skeleton: returns dummy metrics).

        Args:
            predictions: Output from infer() with "area_ts" DataFrame
            reference: Not used for skeleton
            params: Evaluation parameters

        Returns:
            Dict with dummy metrics
        """
        self._init_mlflow(run_name="evaluate")
        try:
            area_ts = predictions["area_ts"]

            metrics = {
                "mae_ha": 0.0,
                "mape_pct": 0.0,
                "n_quarters": len(area_ts),
            }

            # Log to MLflow
            self._mlflow.log_metric("test_mae_ha", metrics["mae_ha"])
            self._mlflow.log_metric("test_mape_pct", metrics["mape_pct"])
            self._mlflow.log_metric("test_samples", metrics["n_quarters"])

            return metrics
        finally:
            self._mlflow.end_run()

    def export_layers(self, predictions: dict[str, Any], out_dir: Path) -> list[GeoLayer]:
        """
        Export built-up mask COGs and area time series as GeoParquet.

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

        # Export built-up mask COG per quarter
        for rec in records:
            if "builtup_mask" not in rec:
                continue

            quarter = rec["quarter"]
            builtup_mask = rec["builtup_mask"]
            transform = rec["transform"]
            crs = rec["crs"]

            cog_path = out_dir / f"builtup_mask_{quarter}.tif"
            write_cog(
                builtup_mask,
                transform,
                crs,
                cog_path,
                dtype="uint8",
                nodata=0,
            )

            layers.append(
                GeoLayer(
                    module_id=self.manifest.id,
                    name=f"builtup_mask_{quarter}",
                    kind="cog",
                    path=cog_path,
                    time=pd.to_datetime(quarter.replace("-Q", "-01")).date(),  # Approximate date
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

        ts_path = out_dir / "builtup_timeseries.parquet"
        gdf.to_parquet(ts_path, index=False)

        layers.append(
            GeoLayer(
                module_id=self.manifest.id,
                name="builtup_timeseries",
                kind="geoparquet",
                path=ts_path,
                time=None,
                bbox=None,
            )
        )

        return layers
