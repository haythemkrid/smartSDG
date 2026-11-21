"""Tests for ModuleLoader."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.registry.module_loader import ModuleLoader


def test_discover_modules() -> None:
    """Test that ModuleLoader discovers modules with valid manifests."""
    loader = ModuleLoader()
    manifests = loader.discover_modules()

    # Should find hydrowatch (has manifest.yaml)
    assert "hydrowatch" in manifests
    assert manifests["hydrowatch"].id == "hydrowatch"
    assert manifests["hydrowatch"].version == "0.1.0"
    assert manifests["hydrowatch"].title == "HydroWatch"
    assert manifests["hydrowatch"].sdg == [6, 13]
    assert manifests["hydrowatch"].sensors == ["sentinel-2-l2a"]
    assert manifests["hydrowatch"].indices == ["ndwi"]
    assert manifests["hydrowatch"].aoi_id == "sidi_salem"
    assert manifests["hydrowatch"].temporal_resolution == "quarterly"
    assert manifests["hydrowatch"].spatial_resolution_m == 10
    assert "water" in manifests["hydrowatch"].params
    assert "forecast" in manifests["hydrowatch"].params
    assert "weather" in manifests["hydrowatch"].params
    assert len(manifests["hydrowatch"].outputs) == 2


def test_discover_modules_invalid_manifest(tmp_path: Path) -> None:
    """Test that invalid manifest raises ValueError with field name."""
    # Create a temporary module with invalid manifest
    bad_module = tmp_path / "bad_module"
    bad_module.mkdir()
    (bad_module / "manifest.yaml").write_text("id: bad\nversion: not_a_version\n")

    loader = ModuleLoader(modules_dir=tmp_path)
    with pytest.raises(ValueError, match="Invalid manifest for module 'bad_module'"):
        loader.discover_modules()


def test_get_deployed_modules() -> None:
    """Test that get_deployed_modules reads deployed_modules.yaml."""
    loader = ModuleLoader()
    deployed = loader.get_deployed_modules()

    assert "hydrowatch" in deployed
    assert "urbanpulse" in deployed
    assert "soilguard" not in deployed


def test_get_deployed_modules_missing_file(tmp_path: Path) -> None:
    """Test that missing deployed_modules.yaml returns empty list."""
    loader = ModuleLoader(deployed_file=tmp_path / "nonexistent.yaml")
    deployed = loader.get_deployed_modules()
    assert deployed == []


def test_load_module_not_found() -> None:
    """Test that loading non-existent module raises ImportError."""
    loader = ModuleLoader()
    with pytest.raises(ImportError, match="Cannot import module 'nonexistent'"):
        loader.load_module("nonexistent")
