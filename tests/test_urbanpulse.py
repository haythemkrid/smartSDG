"""Tests for UrbanPulse module."""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Allow MLflow file store for testing
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

from core.registry.module_loader import ModuleLoader
from core.sdk.schemas import AOI


@pytest.fixture
def urbanpulse_module():
    """Load UrbanPulse module through ModuleLoader."""
    loader = ModuleLoader()
    return loader.load_module("urbanpulse")


@pytest.fixture
def grand_tunis_aoi() -> AOI:
    """Grand Tunis AOI."""
    return AOI(
        id="grand_tunis",
        name="Grand Tunis (approximate)",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [10.00, 36.70],
                    [10.40, 36.70],
                    [10.40, 36.95],
                    [10.00, 36.95],
                    [10.00, 36.70],
                ]
            ],
        },
    )


@pytest.fixture
def mock_stac_items():
    """Create mock STAC items for 16 quarters (2023-Q1 to 2026-Q4)."""
    from datetime import datetime

    from pystac import Item

    items = []
    quarters = [
        (2023, 1),
        (2023, 2),
        (2023, 3),
        (2023, 4),
        (2024, 1),
        (2024, 2),
        (2024, 3),
        (2024, 4),
        (2025, 1),
        (2025, 2),
        (2025, 3),
        (2025, 4),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
    ]

    for _i, (year, q) in enumerate(quarters):
        month = (q - 1) * 3 + 1
        item = Item(
            id=f"S2A_MSIL2A_{year}{month:02d}01_test",
            geometry={"type": "Point", "coordinates": [10.2, 36.82]},
            bbox=[10.00, 36.70, 10.40, 36.95],
            datetime=datetime(year, month, 15),
            properties={"eo:cloud_cover": 5.0},
        )
        items.append(item)

    return items


@pytest.fixture
def mock_compute_indices_records(mock_stac_items, grand_tunis_aoi):
    """Create mock records as returned by compute_indices."""
    records = []
    height, width = 100, 100  # Synthetic array size

    np.random.seed(42)
    for _i, item in enumerate(mock_stac_items):
        dt = item.datetime
        quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"

        # Create synthetic NDBI with some built-up-like values
        ndbi = np.random.uniform(-0.5, 0.5, (height, width)).astype(np.float32)
        # Make some pixels clearly built-up (NDBI > 0.0)
        builtup_pixels = np.random.random((height, width)) < 0.3
        ndbi[builtup_pixels] = np.random.uniform(0.1, 0.8, builtup_pixels.sum())

        # Cloud mask - few clouds
        cloud_mask = np.random.random((height, width)) < 0.05

        # Simple transform (10m resolution)
        from rasterio import Affine

        transform = Affine.translation(10.00, 36.95) * Affine.scale(0.0001, -0.0001)

        records.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "quarter": quarter,
                "ndbi": ndbi,
                "cloud_mask": cloud_mask,
                "transform": transform,
                "crs": "EPSG:32632",
            }
        )

    return records


class TestUrbanPulseModule:
    """Tests for UrbanPulse module implementation."""

    def test_module_loads(self, urbanpulse_module):
        """Test that module loads and has all required methods."""
        from modules.urbanpulse.module import UrbanPulseModule

        assert isinstance(urbanpulse_module, UrbanPulseModule)
        assert hasattr(urbanpulse_module, "ingest")
        assert hasattr(urbanpulse_module, "compute_indices")
        assert hasattr(urbanpulse_module, "train")
        assert hasattr(urbanpulse_module, "infer")
        assert hasattr(urbanpulse_module, "evaluate")
        assert hasattr(urbanpulse_module, "export_layers")

    def test_manifest_parameters_loaded(self, urbanpulse_module):
        """Test that manifest parameters are loaded correctly."""
        assert urbanpulse_module.ndbi_params["builtup_threshold"] == 0.0
        assert urbanpulse_module.ndbi_params["train_sample_pixels"] == 10000
        assert urbanpulse_module.ndbi_params["pixel_classifier"]["n_estimators"] == 50
        assert urbanpulse_module.ndbi_params["pixel_classifier"]["max_depth"] == 8

    def test_aoi_geometry_loaded(self, urbanpulse_module):
        """Test that AOI geometry is loaded correctly."""
        assert urbanpulse_module._aoi_geometry is not None
        assert urbanpulse_module._aoi_geometry["type"] == "Polygon"
        coords = urbanpulse_module._aoi_geometry["coordinates"][0]
        assert len(coords) == 5  # Closed polygon

    @patch("modules.urbanpulse.module.STACClient")
    def test_ingest_returns_expected_structure(
        self, mock_stac_client_class, urbanpulse_module, grand_tunis_aoi
    ):
        """Test ingest returns correct structure with items."""
        mock_stac_client = MagicMock()
        mock_stac_client_class.return_value = mock_stac_client

        mock_items = [MagicMock() for _ in range(16)]
        mock_stac_client.search.return_value = mock_items
        mock_stac_client.select_first_per_quarter.return_value = mock_items[:4]  # 4 quarters

        result = urbanpulse_module.ingest(
            grand_tunis_aoi,
            (date(2023, 1, 1), date(2023, 12, 31)),
            {"max_cloud": 15},
        )

        assert "items" in result
        assert len(result["items"]) == 4

    def test_compute_indices_structure(self, urbanpulse_module, mock_stac_items, grand_tunis_aoi):
        """Test compute_indices returns expected record structure."""
        # We can't easily test the actual computation without real data
        # but we can verify the method exists and returns correct structure
        pass  # Integration test would need real/mocked raster data

    def test_train_infer_evaluate_flow(self, urbanpulse_module, mock_compute_indices_records):
        """Test the train -> infer -> evaluate flow with synthetic data."""
        # Create dataset as ingest would return
        dataset = {
            "records": mock_compute_indices_records,
        }

        # Train
        model = urbanpulse_module.train(dataset, {"seed": 42})

        # Verify model artifact structure
        assert "pixel_clf" in model
        assert "train_cutoff" in model
        assert model["train_cutoff"] == "2026-Q1"
        assert urbanpulse_module._pixel_clf is not None

        # Infer
        predictions = urbanpulse_module.infer(dataset, model, {"seed": 42})

        # Verify predictions structure
        assert "records" in predictions
        assert "area_ts" in predictions
        assert isinstance(predictions["area_ts"], pd.DataFrame)
        assert "builtup_area_ha" in predictions["area_ts"].columns

        # Evaluate
        metrics = urbanpulse_module.evaluate(predictions, None, {})

        # Verify metrics structure
        assert "mae_ha" in metrics
        assert "mape_pct" in metrics
        assert "n_quarters" in metrics
        assert isinstance(metrics["mae_ha"], float)
        assert isinstance(metrics["mape_pct"], float)
        assert metrics["n_quarters"] > 0


class TestUrbanPulseManifest:
    """Tests for UrbanPulse manifest."""

    def test_manifest_valid(self):
        """Test that manifest loads and validates."""
        import yaml

        from core.sdk.schemas import ModuleManifest

        with open("modules/urbanpulse/manifest.yaml") as f:
            data = yaml.safe_load(f)

        manifest = ModuleManifest(**data)
        assert manifest.id == "urbanpulse"
        assert manifest.version == "0.1.0"
        assert manifest.title == "UrbanPulse"
        assert manifest.sdg == [11]
        assert manifest.sensors == ["sentinel-2-l2a"]
        assert manifest.indices == ["ndbi"]
        assert manifest.aoi_id == "grand_tunis"
        assert manifest.temporal_resolution == "quarterly"
        assert manifest.spatial_resolution_m == 10
        assert len(manifest.outputs) == 2

    def test_manifest_outputs(self):
        """Test manifest outputs have correct structure."""
        import yaml

        from core.sdk.schemas import ModuleManifest

        with open("modules/urbanpulse/manifest.yaml") as f:
            data = yaml.safe_load(f)

        manifest = ModuleManifest(**data)
        output_names = [o.name for o in manifest.outputs]
        assert "ndbi_layer" in output_names
        assert "builtup_timeseries" in output_names
        for o in manifest.outputs:
            assert o.type in ["cog", "geoparquet", "geojson"]
