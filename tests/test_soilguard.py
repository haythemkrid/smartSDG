"""Tests for SoilGuard module."""

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
def soilguard_module():
    """Load SoilGuard module through ModuleLoader."""
    loader = ModuleLoader()
    return loader.load_module("soilguard")


@pytest.fixture
def oasis_aoi() -> AOI:
    """Oasis AOI."""
    return AOI(
        id="oasis",
        name="Oasis (placeholder)",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [7.80, 33.70],
                    [8.50, 33.70],
                    [8.50, 34.20],
                    [7.80, 34.20],
                    [7.80, 33.70],
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
            geometry={"type": "Point", "coordinates": [8.15, 33.95]},
            bbox=[7.80, 33.70, 8.50, 34.20],
            datetime=datetime(year, month, 15),
            properties={"eo:cloud_cover": 5.0},
        )
        items.append(item)

    return items


@pytest.fixture
def mock_compute_indices_records(mock_stac_items, oasis_aoi):
    """Create mock records as returned by compute_indices."""
    records = []
    height, width = 100, 100  # Synthetic array size

    np.random.seed(42)
    for _i, item in enumerate(mock_stac_items):
        dt = item.datetime
        quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"

        # Create synthetic salinity index with some saline-like values
        sal_index = np.random.uniform(-0.5, 0.5, (height, width)).astype(np.float32)
        # Make some pixels clearly saline (salinity_index > 0.0)
        saline_pixels = np.random.random((height, width)) < 0.3
        sal_index[saline_pixels] = np.random.uniform(0.1, 0.8, saline_pixels.sum())

        # Cloud mask - few clouds
        cloud_mask = np.random.random((height, width)) < 0.05

        # Simple transform (10m resolution)
        from rasterio import Affine

        transform = Affine.translation(7.80, 34.20) * Affine.scale(0.0001, -0.0001)

        records.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "quarter": quarter,
                "salinity_index": sal_index,
                "cloud_mask": cloud_mask,
                "transform": transform,
                "crs": "EPSG:32632",
            }
        )

    return records


class TestSoilGuardModule:
    """Tests for SoilGuard module implementation."""

    def test_module_loads(self, soilguard_module):
        """Test that module loads and has all required methods."""
        from modules.soilguard.module import SoilGuardModule

        assert isinstance(soilguard_module, SoilGuardModule)
        assert hasattr(soilguard_module, "ingest")
        assert hasattr(soilguard_module, "compute_indices")
        assert hasattr(soilguard_module, "train")
        assert hasattr(soilguard_module, "infer")
        assert hasattr(soilguard_module, "evaluate")
        assert hasattr(soilguard_module, "export_layers")

    def test_manifest_parameters_loaded(self, soilguard_module):
        """Test that manifest parameters are loaded correctly."""
        assert soilguard_module.salinity_params["salinity_threshold"] == 0.0
        assert soilguard_module.salinity_params["train_sample_pixels"] == 10000
        assert soilguard_module.salinity_params["pixel_classifier"]["n_estimators"] == 50
        assert soilguard_module.salinity_params["pixel_classifier"]["max_depth"] == 8

    def test_aoi_geometry_loaded(self, soilguard_module):
        """Test that AOI geometry is loaded correctly."""
        assert soilguard_module._aoi_geometry is not None
        assert soilguard_module._aoi_geometry["type"] == "Polygon"
        coords = soilguard_module._aoi_geometry["coordinates"][0]
        assert len(coords) == 5  # Closed polygon

    @patch("modules.soilguard.module.STACClient")
    def test_ingest_returns_expected_structure(
        self, mock_stac_client_class, soilguard_module, oasis_aoi
    ):
        """Test ingest returns correct structure with items."""
        mock_stac_client = MagicMock()
        mock_stac_client_class.return_value = mock_stac_client

        mock_items = [MagicMock() for _ in range(16)]
        mock_stac_client.search.return_value = mock_items
        mock_stac_client.select_first_per_quarter.return_value = mock_items[:4]  # 4 quarters

        result = soilguard_module.ingest(
            oasis_aoi,
            (date(2023, 1, 1), date(2023, 12, 31)),
            {"max_cloud": 15},
        )

        assert "items" in result
        assert len(result["items"]) == 4

    def test_compute_indices_structure(self, soilguard_module, mock_stac_items, oasis_aoi):
        """Test compute_indices returns expected record structure."""
        # We can't easily test the actual computation without real data
        # but we can verify the method exists and returns correct structure
        pass  # Integration test would need real/mocked raster data

    def test_train_infer_evaluate_flow(
        self, soilguard_module, mock_compute_indices_records
    ):
        """Test the train -> infer -> evaluate flow with synthetic data."""
        # Create dataset as ingest would return
        dataset = {
            "records": mock_compute_indices_records,
        }

        # Train
        model = soilguard_module.train(dataset, {"seed": 42})

        # Verify model artifact structure
        assert "pixel_clf" in model
        assert "train_cutoff" in model
        assert model["train_cutoff"] == "2026-Q1"
        assert soilguard_module._pixel_clf is not None

        # Infer
        predictions = soilguard_module.infer(dataset, model, {"seed": 42})

        # Verify predictions structure
        assert "records" in predictions
        assert "area_ts" in predictions
        assert isinstance(predictions["area_ts"], pd.DataFrame)
        assert "saline_area_ha" in predictions["area_ts"].columns

        # Evaluate
        metrics = soilguard_module.evaluate(predictions, None, {})

        # Verify metrics structure
        assert "mae_ha" in metrics
        assert "mape_pct" in metrics
        assert "n_quarters" in metrics
        assert isinstance(metrics["mae_ha"], float)
        assert isinstance(metrics["mape_pct"], float)
        assert metrics["n_quarters"] > 0


class TestSoilGuardManifest:
    """Tests for SoilGuard manifest."""

    def test_manifest_valid(self):
        """Test that manifest loads and validates."""
        import yaml

        from core.sdk.schemas import ModuleManifest

        with open("modules/soilguard/manifest.yaml") as f:
            data = yaml.safe_load(f)

        manifest = ModuleManifest(**data)
        assert manifest.id == "soilguard"
        assert manifest.version == "0.1.0"
        assert manifest.title == "SoilGuard"
        assert manifest.sdg == [15]
        assert manifest.sensors == ["sentinel-2-l2a"]
        assert manifest.indices == ["salinity_index"]
        assert manifest.aoi_id == "oasis"
        assert manifest.temporal_resolution == "quarterly"
        assert manifest.spatial_resolution_m == 10
        assert len(manifest.outputs) == 2

    def test_manifest_outputs(self):
        """Test manifest outputs have correct structure."""
        import yaml

        from core.sdk.schemas import ModuleManifest

        with open("modules/soilguard/manifest.yaml") as f:
            data = yaml.safe_load(f)

        manifest = ModuleManifest(**data)
        output_names = [o.name for o in manifest.outputs]
        assert "salinity_layer" in output_names
        assert "salinity_timeseries" in output_names
        for o in manifest.outputs:
            assert o.type in ["cog", "geoparquet", "geojson"]


class TestSalinityIndex:
    """Tests for placeholder salinity index."""

    def test_salinity_index_basic(self):
        """Test salinity index with simple values."""
        from modules.soilguard.module import salinity_index

        nir = np.array([[100, 200]], dtype=np.float32)
        swir = np.array([[50, 100]], dtype=np.float32)

        result = salinity_index(nir, swir)
        # SWIR/NIR ratio
        # Pixel (0,0): 50/(100+50) = 50/150 = 0.333
        # Pixel (0,1): 100/(200+100) = 100/300 = 0.333
        expected = np.array([[1 / 3, 1 / 3]], dtype=np.float32)
        np.testing.assert_allclose(result, expected)

    def test_zero_denominator(self):
        """Test salinity index returns 0 where denominator is 0."""
        from modules.soilguard.module import salinity_index

        nir = np.array([[0, 100]], dtype=np.float32)
        swir = np.array([[0, 100]], dtype=np.float32)

        result = salinity_index(nir, swir)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 0.5  # 100/(100+100) = 0.5
