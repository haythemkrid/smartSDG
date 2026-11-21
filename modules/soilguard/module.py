"""SoilGuard module - stub implementation for contract compliance."""

from __future__ import annotations

from typing import Any

from core.sdk.base_module import BaseSDGModule
from core.sdk.schemas import AOI


class SoilGuardModule(BaseSDGModule):
    """SoilGuard module for soil salinisation and oases (SDG 15)."""

    def ingest(self, aoi: AOI, date_range: tuple, params: dict) -> Any:
        raise NotImplementedError("SoilGuard ingest not implemented yet (T08)")

    def compute_indices(self, items: Any, params: dict) -> Any:
        raise NotImplementedError("SoilGuard compute_indices not implemented yet (T08)")

    def train(self, dataset: Any, params: dict) -> Any:
        raise NotImplementedError("SoilGuard train not implemented yet (T08)")

    def infer(self, dataset: Any, model: Any, params: dict) -> Any:
        raise NotImplementedError("SoilGuard infer not implemented yet (T08)")

    def evaluate(self, predictions: Any, reference: Any, params: dict) -> dict[str, float]:
        raise NotImplementedError("SoilGuard evaluate not implemented yet (T08)")

    def export_layers(self, predictions: Any, out_dir) -> list:
        raise NotImplementedError("SoilGuard export_layers not implemented yet (T08)")
