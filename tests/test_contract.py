"""Contract tests: every module must implement all 6 abstract methods."""

from __future__ import annotations

import pytest

from core.registry.module_loader import ModuleLoader
from core.sdk.base_module import BaseSDGModule

REQUIRED_METHODS = [
    "ingest",
    "compute_indices",
    "train",
    "infer",
    "evaluate",
    "export_layers",
]


def get_discovered_modules() -> list[str]:
    """Get list of modules that have a manifest.yaml."""
    loader = ModuleLoader()
    return list(loader.discover_modules().keys())


@pytest.mark.parametrize("module_id", get_discovered_modules())
def test_module_implements_contract(module_id: str) -> None:
    """Test that a module implements all 6 required methods."""
    loader = ModuleLoader()
    module_instance = loader.load_module(module_id)

    # Check it's a BaseSDGModule subclass
    assert isinstance(module_instance, BaseSDGModule), (
        f"{module_id} must inherit from BaseSDGModule"
    )

    # Check all required methods exist and are implemented
    for method_name in REQUIRED_METHODS:
        assert hasattr(module_instance, method_name), f"{module_id} missing method: {method_name}"
        method = getattr(module_instance, method_name)
        assert callable(method), f"{module_id}.{method_name} must be callable"
        # Ensure it's not the abstract method from the base class
        base_method = getattr(BaseSDGModule, method_name)
        assert method is not base_method, (
            f"{module_id}.{method_name} must be implemented (not abstract)"
        )


@pytest.mark.parametrize("module_id", get_discovered_modules())
def test_module_manifest_valid(module_id: str) -> None:
    """Test that module's manifest is valid and matches module_id."""
    loader = ModuleLoader()
    manifests = loader.discover_modules()
    manifest = manifests[module_id]

    assert manifest.id == module_id, (
        f"Manifest id '{manifest.id}' must match module directory '{module_id}'"
    )
