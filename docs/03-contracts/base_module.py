"""BaseSDGModule contract. SOURCE OF TRUTH until T02 copies it verbatim to core/sdk/base_module.py.
Do not modify without human approval."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any

from .schemas import AOI, GeoLayer, ModuleManifest


class BaseSDGModule(ABC):
    """Stateless between runs. All parameters come from configs + manifest params."""

    def __init__(self, manifest: ModuleManifest) -> None:
        self.manifest = manifest

    @abstractmethod
    def ingest(self, aoi: AOI, date_range: tuple[date, date], params: dict) -> Any:
        """Return an item collection. Must save the hashed STAC query."""

    @abstractmethod
    def compute_indices(self, items: Any, params: dict) -> Any:
        """Return a dataset-like object: xarray.Dataset preferred; per-scene records (as in the spike) accepted for the MVP."""

    @abstractmethod
    def train(self, dataset: Any, params: dict) -> Any:
        """Return a model artifact (may be a calibrated threshold). Must be seeded."""

    @abstractmethod
    def infer(self, dataset: Any, model: Any, params: dict) -> Any:
        """Return predictions (e.g. water mask and per-date surface)."""

    @abstractmethod
    def evaluate(self, predictions: Any, reference: Any, params: dict) -> dict[str, float]:
        """Return metrics (e.g. rmse, f1, iou) against the reference."""

    @abstractmethod
    def export_layers(self, predictions: Any, out_dir: Path) -> list[GeoLayer]:
        """Write COG/GeoParquet files (incl. the time series) to out_dir; return GeoLayers."""
