"""Mock module for API testing."""

from __future__ import annotations

from typing import Any

from core.sdk.base_module import BaseSDGModule
from core.sdk.schemas import AOI


class MockModule(BaseSDGModule):
    """Mock module for testing the API."""

    def ingest(self, aoi: AOI, date_range: tuple, params: dict) -> Any:
        return None

    def compute_indices(self, items: Any, params: dict) -> Any:
        return None

    def train(self, dataset: Any, params: dict) -> Any:
        return None

    def infer(self, dataset: Any, model: Any, params: dict) -> Any:
        return None

    def evaluate(self, predictions: Any, reference: Any, params: dict) -> dict[str, float]:
        return {}

    def export_layers(self, predictions: Any, out_dir) -> list:
        return []
