"""Module discovery, validation, and loading."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import yaml

from core.sdk.schemas import ModuleManifest


class ModuleLoader:
    """Discovers, validates, and loads SDG modules."""

    def __init__(
        self,
        modules_dir: Path = Path("modules"),
        deployed_file: Path = Path("configs/deployed_modules.yaml"),
    ) -> None:
        self.modules_dir = modules_dir
        self.deployed_file = deployed_file

    def discover_modules(self) -> dict[str, ModuleManifest]:
        """Scan modules/*/manifest.yaml and validate with ModuleManifest.

        Returns:
            Dict mapping module_id to validated ModuleManifest.

        Raises:
            ValueError: If a manifest is invalid, naming the field.
        """
        manifests = {}
        for manifest_path in self.modules_dir.glob("*/manifest.yaml"):
            module_id = manifest_path.parent.name
            try:
                with open(manifest_path) as f:
                    data = yaml.safe_load(f)
                manifest = ModuleManifest(**data)
                manifests[module_id] = manifest
            except Exception as e:
                raise ValueError(f"Invalid manifest for module '{module_id}': {e}") from e
        return manifests

    def get_deployed_modules(self) -> list[str]:
        """Read deployed module IDs from configs/deployed_modules.yaml.

        Returns:
            List of deployed module IDs.
        """
        if not self.deployed_file.exists():
            return []
        with open(self.deployed_file) as f:
            data = yaml.safe_load(f)
        return data.get("deployed", [])

    def load_module(self, module_id: str) -> Any:
        """Import and instantiate a module class.

        Args:
            module_id: The module identifier (e.g., "hydrowatch").

        Returns:
            An instance of the module's BaseSDGModule subclass.

        Raises:
            ImportError: If the module cannot be imported.
            ValueError: If the module class is not found or doesn't inherit from BaseSDGModule.
        """
        # Import the module's module.py
        module_path = f"modules.{module_id}.module"
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Cannot import module '{module_id}': {e}") from e

        # Find the BaseSDGModule subclass
        from core.sdk.base_module import BaseSDGModule

        module_class = None
        for _name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseSDGModule)
                and obj is not BaseSDGModule
            ):
                module_class = obj
                break

        if module_class is None:
            raise ValueError(f"No BaseSDGModule subclass found in {module_path}")

        # Get the manifest for this module
        manifests = self.discover_modules()
        if module_id not in manifests:
            raise ValueError(f"Module '{module_id}' not found in discovered modules")

        # Instantiate with manifest
        return module_class(manifests[module_id])

    def deploy_module(self, module_id: str) -> None:
        """
        Deploy a module by validating its manifest and adding it to deployed_modules.yaml.

        This validates the module can be loaded, then registers it in the deployed list.

        Args:
            module_id: The module identifier to deploy.

        Raises:
            ValueError: If the module is not found or manifest is invalid.
        """
        # Validate by discovering modules (validates manifests)
        manifests = self.discover_modules()
        if module_id not in manifests:
            raise ValueError(f"Module '{module_id}' not found in discovered modules")

        # Validate the module can be loaded (checks import and BaseSDGModule subclass)
        self.load_module(module_id)

        # Get current deployed modules
        deployed = self.get_deployed_modules()

        # Add if not already deployed
        if module_id not in deployed:
            deployed.append(module_id)
            self._save_deployed_modules(deployed)

    def _save_deployed_modules(self, deployed: list[str]) -> None:
        """Save deployed module list to YAML file."""
        import yaml

        self.deployed_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.deployed_file, "w") as f:
            yaml.dump({"deployed": deployed}, f, sort_keys=False)
