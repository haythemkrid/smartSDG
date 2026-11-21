"""HydroWatch module - stub implementation for contract compliance."""

from __future__ import annotations

from typing import Any

from core.sdk.base_module import BaseSDGModule
from core.sdk.schemas import AOI


class HydroWatchModule(BaseSDGModule):
    """HydroWatch module for water surface monitoring (SDG 6, 13)."""

    def ingest(self, aoi: AOI, date_range: tuple, params: dict) -> Any:
        raise NotImplementedError("HydroWatch ingest not implemented yet (T00/T05)")

    def compute_indices(self, items: Any, params: dict) -> Any:
        raise NotImplementedError("HydroWatch compute_indices not implemented yet (T00/T05)")

    def train(self, dataset: Any, params: dict) -> Any:
        raise NotImplementedError("HydroWatch train not implemented yet (T00/T06)")

    def infer(self, dataset: Any, model: Any, params: dict) -> Any:
        raise NotImplementedError("HydroWatch infer not implemented yet (T00/T06)")

    def evaluate(self, predictions: Any, reference: Any, params: dict) -> dict[str, float]:
        raise NotImplementedError("HydroWatch evaluate not implemented yet (T00/T06)")

    def export_layers(self, predictions: Any, out_dir) -> list:
        raise NotImplementedError("HydroWatch export_layers not implemented yet (T00/T06)")
