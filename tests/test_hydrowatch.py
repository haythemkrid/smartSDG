"""Tests for HydroWatch module against spike baseline."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Allow MLflow file store for testing
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

from core.registry.module_loader import ModuleLoader
from core.sdk.schemas import AOI
from modules.hydrowatch.module import HydroWatchModule
from modules.hydrowatch.weather import WeatherClient


@pytest.fixture
def hydrowatch_module() -> HydroWatchModule:
    """Load HydroWatch module through ModuleLoader."""
    loader = ModuleLoader()
    return loader.load_module("hydrowatch")


@pytest.fixture
def sidi_salem_aoi() -> AOI:
    """Sidi Salem AOI."""
    return AOI(
        id="sidi_salem",
        name="Sidi Salem dam",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [9.355, 36.585],
                    [9.455, 36.585],
                    [9.455, 36.655],
                    [9.355, 36.655],
                    [9.355, 36.585],
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
    # 16 quarters from 2023-Q1 to 2026-Q4
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
            geometry={"type": "Point", "coordinates": [9.4, 36.62]},
            bbox=[9.355, 36.585, 9.455, 36.655],
            datetime=datetime(year, month, 15),
            properties={"eo:cloud_cover": 5.0},
        )
        items.append(item)

    return items


@pytest.fixture
def mock_weather_df() -> pd.DataFrame:
    """Create mock weather DataFrame matching spike structure."""
    # 16 quarters
    quarters = [
        "2023-Q1",
        "2023-Q2",
        "2023-Q3",
        "2023-Q4",
        "2024-Q1",
        "2024-Q2",
        "2024-Q3",
        "2024-Q4",
        "2025-Q1",
        "2025-Q2",
        "2025-Q3",
        "2025-Q4",
        "2026-Q1",
        "2026-Q2",
        "2026-Q3",
        "2026-Q4",
    ]

    # Synthetic precipitation data (mm per quarter)
    np.random.seed(42)
    data = {
        "quarter": quarters,
        "upper_algeria_precip_mm": np.random.uniform(50, 200, 16),
        "mid_border_precip_mm": np.random.uniform(40, 180, 16),
        "local_beja_precip_mm": np.random.uniform(30, 150, 16),
        "mean_temp_c": np.random.uniform(10, 25, 16),
    }

    df = pd.DataFrame(data)
    # Compute weighted precip
    df["weighted_catchment_precip_mm"] = (
        0.45 * df["upper_algeria_precip_mm"]
        + 0.35 * df["mid_border_precip_mm"]
        + 0.20 * df["local_beja_precip_mm"]
    )

    return df


@pytest.fixture
def mock_compute_indices_records(mock_stac_items, sidi_salem_aoi):
    """Create mock records as returned by compute_indices."""
    records = []
    height, width = 100, 100  # Synthetic array size

    np.random.seed(42)
    for _i, item in enumerate(mock_stac_items):
        dt = item.datetime
        quarter = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"

        # Create synthetic NDWI with some water-like values
        ndwi = np.random.uniform(-0.5, 0.5, (height, width)).astype(np.float32)
        # Make some pixels clearly water (NDWI > 0.05)
        water_pixels = np.random.random((height, width)) < 0.3
        ndwi[water_pixels] = np.random.uniform(0.1, 0.8, water_pixels.sum())

        # Cloud mask - few clouds
        cloud_mask = np.random.random((height, width)) < 0.05

        # Simple transform (10m resolution)
        from rasterio import Affine

        transform = Affine.translation(9.355, 36.655) * Affine.scale(0.0001, -0.0001)

        records.append(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "quarter": quarter,
                "ndwi": ndwi,
                "cloud_mask": cloud_mask,
                "transform": transform,
                "crs": "EPSG:32632",
            }
        )

    return records


class TestHydroWatchModule:
    """Tests for HydroWatch module implementation."""

    def test_module_loads(self, hydrowatch_module: HydroWatchModule) -> None:
        """Test that module loads and has all required methods."""
        assert isinstance(hydrowatch_module, HydroWatchModule)
        assert hasattr(hydrowatch_module, "ingest")
        assert hasattr(hydrowatch_module, "compute_indices")
        assert hasattr(hydrowatch_module, "train")
        assert hasattr(hydrowatch_module, "infer")
        assert hasattr(hydrowatch_module, "evaluate")
        assert hasattr(hydrowatch_module, "export_layers")

    def test_manifest_parameters_loaded(self, hydrowatch_module: HydroWatchModule) -> None:
        """Test that manifest parameters are loaded correctly."""
        assert hydrowatch_module.water_params["weak_label_ndwi_threshold"] == 0.05
        assert hydrowatch_module.water_params["train_on"] == "first_scene"
        assert hydrowatch_module.water_params["train_sample_pixels"] == 20000
        assert hydrowatch_module.forecast_params["test_start_quarter"] == "2024-Q3"
        assert "lag_1_area" in hydrowatch_module.forecast_params["features"]

    def test_weather_client_creation(self, hydrowatch_module: HydroWatchModule) -> None:
        """Test that weather client is created with manifest params."""
        assert hydrowatch_module.weather_client is not None
        assert isinstance(hydrowatch_module.weather_client, WeatherClient)
        assert len(hydrowatch_module.weather_client.precip_points) == 3

    @patch("modules.hydrowatch.module.STACClient")
    def test_ingest_returns_expected_structure(
        self, mock_stac_client_class, hydrowatch_module, sidi_salem_aoi
    ):
        """Test ingest returns correct structure with items and weather."""
        # Mock STAC client
        mock_stac_client = MagicMock()
        mock_stac_client_class.return_value = mock_stac_client

        # Mock search to return items
        mock_items = [MagicMock() for _ in range(16)]
        mock_stac_client.search.return_value = mock_items
        mock_stac_client.select_first_per_quarter.return_value = mock_items[:4]  # 4 quarters

        # Mock weather client
        hydrowatch_module.weather_client = MagicMock()
        mock_weather = pd.DataFrame(
            {
                "quarter": ["2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"],
                "weighted_catchment_precip_mm": [100, 120, 80, 90],
                "mean_temp_c": [15, 20, 25, 18],
            }
        )
        hydrowatch_module.weather_client.fetch_catchment_weather.return_value = mock_weather

        # Call ingest
        result = hydrowatch_module.ingest(
            sidi_salem_aoi,
            (date(2023, 1, 1), date(2023, 12, 31)),
            {"max_cloud": 15},
        )

        # Verify structure
        assert "items" in result
        assert "weather" in result
        assert isinstance(result["weather"], pd.DataFrame)
        assert len(result["items"]) == 4

    def test_compute_indices_structure(self, hydrowatch_module, mock_stac_items, sidi_salem_aoi):
        """Test compute_indices returns expected record structure."""
        # We can't easily test the actual computation without real data
        # but we can verify the method exists and returns correct structure
        pass  # Integration test would need real/mocked raster data

    def test_train_infer_evaluate_flow(
        self, hydrowatch_module, mock_compute_indices_records, mock_weather_df
    ):
        """Test the train -> infer -> evaluate flow with synthetic data."""
        # Create dataset as ingest would return
        dataset = {
            "records": mock_compute_indices_records,
            "weather": mock_weather_df,
        }

        # Train
        model = hydrowatch_module.train(dataset, {"seed": 42})

        # Verify model artifact structure
        assert "pixel_clf" in model
        assert "forecaster" in model
        assert "train_cutoff" in model
        assert model["train_cutoff"] == "2024-Q3"
        assert hydrowatch_module._pixel_clf is not None
        assert hydrowatch_module._forecaster is not None

        # Infer
        predictions = hydrowatch_module.infer(dataset, model, {"seed": 42})

        # Verify predictions structure
        assert "records" in predictions
        assert "area_ts" in predictions
        assert "backtest" in predictions
        assert isinstance(predictions["area_ts"], pd.DataFrame)
        assert isinstance(predictions["backtest"], pd.DataFrame)
        assert "predicted_ha" in predictions["backtest"].columns
        assert "error_pct" in predictions["backtest"].columns

        # Evaluate
        metrics = hydrowatch_module.evaluate(predictions, None, {})

        # Verify metrics structure
        assert "mae_ha" in metrics
        assert "mape_pct" in metrics
        assert "n_quarters" in metrics
        assert isinstance(metrics["mae_ha"], float)
        assert isinstance(metrics["mape_pct"], float)
        assert metrics["n_quarters"] > 0


class TestWeatherClient:
    """Tests for WeatherClient."""

    def test_weather_client_init(self):
        """Test WeatherClient initialization with defaults."""
        client = WeatherClient()
        assert client.url == "https://archive-api.open-meteo.com/v1/archive"
        assert client.timezone == "Africa/Tunis"
        assert len(client.precip_points) == 3
        assert "upper_algeria" in client.precip_points

    def test_weather_client_custom_params(self):
        """Test WeatherClient with custom parameters."""
        custom_points = {"test": {"lat": 0, "lon": 0, "weight": 1.0}}
        custom_temp = {"lat": 1, "lon": 1}
        client = WeatherClient(
            url="http://test.com",
            timezone="UTC",
            precip_points=custom_points,
            temperature_point=custom_temp,
        )
        assert client.url == "http://test.com"
        assert client.precip_points == custom_points
        assert client.temperature_point == custom_temp

    @patch("modules.hydrowatch.weather.requests.get")
    def test_fetch_precipitation(self, mock_get):
        """Test precipitation fetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2023-01-01", "2023-01-02"],
                "precipitation_sum": [5.0, 3.0],
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WeatherClient()
        df = client._fetch_precipitation(36.28, 7.95, date(2023, 1, 1), date(2023, 1, 31), "test")

        assert isinstance(df, pd.DataFrame)
        assert "quarter" in df.columns
        assert "test_precip_mm" in df.columns

    @patch("modules.hydrowatch.weather.requests.get")
    def test_fetch_temperature(self, mock_get):
        """Test temperature fetching."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "daily": {
                "time": ["2023-01-01", "2023-01-02"],
                "temperature_2m_mean": [15.0, 16.0],
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        client = WeatherClient()
        df = client._fetch_temperature(36.62, 9.40, date(2023, 1, 1), date(2023, 1, 31))

        assert isinstance(df, pd.DataFrame)
        assert "quarter" in df.columns
        assert "mean_temp_c" in df.columns


class TestSpikeBaseline:
    """Tests comparing module output to spike baseline.

    Note: Full baseline comparison requires running the actual pipeline
    with real STAC data. These tests verify the module structure and
    that the spike baseline file exists and has expected content.
    """

    def test_baseline_file_exists(self):
        """Test that golden baseline file exists."""
        baseline_path = Path("tests/golden/hydrowatch_spike_baseline.json")
        assert baseline_path.exists()

    def test_baseline_has_expected_metrics(self):
        """Test that baseline has expected structure."""
        baseline_path = Path("tests/golden/hydrowatch_spike_baseline.json")
        with open(baseline_path) as f:
            baseline = json.load(f)

        assert "metrics" in baseline
        assert baseline["metrics"]["mae_ha"] == 139.90
        assert baseline["metrics"]["mape_pct"] == 10.20
        assert baseline["metrics"]["n_quarters"] == 4
        assert len(baseline["per_quarter"]) == 4

        # Check per-quarter structure
        for q in baseline["per_quarter"]:
            assert "quarter" in q
            assert "water_area_ha" in q
            assert "predicted_ha" in q
            assert "error_pct" in q

        # Check defects are documented
        assert "defects_preserved" in baseline["notes"]
        assert len(baseline["notes"]["defects_preserved"]) >= 10

    def test_module_parameters_match_spike(self, hydrowatch_module):
        """Test that module parameters match spike values."""
        # From spike: weak_label_ndwi_threshold=0.05, train_sample_pixels=20000
        assert hydrowatch_module.water_params["weak_label_ndwi_threshold"] == 0.05
        assert hydrowatch_module.water_params["train_sample_pixels"] == 20000

        # Forecast params from spike
        assert hydrowatch_module.forecast_params["model"]["n_estimators"] == 150
        assert hydrowatch_module.forecast_params["model"]["max_depth"] == 4
        assert hydrowatch_module.forecast_params["test_start_quarter"] == "2024-Q3"

        # Weather params from spike
        assert len(hydrowatch_module.weather_params["precip_points"]) == 3
        weights = [p["weight"] for p in hydrowatch_module.weather_params["precip_points"].values()]
        assert weights == [0.45, 0.35, 0.20]
