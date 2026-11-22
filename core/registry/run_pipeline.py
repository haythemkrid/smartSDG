#!/usr/bin/env python
"""Helper to run DVC pipeline for a specific module."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


def get_module_stages(module_id: str) -> list[str]:
    """Get all DVC stage names for a module."""
    dvc_path = Path("dvc.yaml")
    if not dvc_path.exists():
        return []

    with open(dvc_path) as f:
        dvc_data = yaml.safe_load(f)

    stages = dvc_data.get("stages", {})
    module_stages = [name for name in stages if name.startswith(f"{module_id}_")]
    return module_stages


def _extract_out_paths(outs: list) -> list[str]:
    """Extract output paths from DVC outs list (handles both strings and dicts)."""
    paths = []
    for out in outs:
        if isinstance(out, dict):
            paths.append(list(out.keys())[0])
        else:
            paths.append(out)
    return paths


def get_module_final_outputs(module_id: str) -> list[str]:
    """Get final output files for a module (stages with no downstream dependencies)."""
    dvc_path = Path("dvc.yaml")
    if not dvc_path.exists():
        return []

    with open(dvc_path) as f:
        dvc_data = yaml.safe_load(f)

    stages = dvc_data.get("stages", {})
    module_stages = {name: data for name, data in stages.items() if name.startswith(f"{module_id}_")}

    if not module_stages:
        return []

    # Build dependency graph
    stage_deps = {name: set(data.get("deps", [])) for name, data in module_stages.items()}
    stage_outs = {name: set(_extract_out_paths(data.get("outs", []))) for name, data in module_stages.items()}

    # Find stages that are not depended upon by other stages in this module
    all_deps = set()
    for deps in stage_deps.values():
        for dep in deps:
            # Check if dep is an output of another stage in this module
            for other_name, outs in stage_outs.items():
                if dep in outs:
                    all_deps.add(other_name)
                    break

    # Final stages are those not in all_deps
    final_stages = [name for name in module_stages if name not in all_deps]

    # Get outputs of final stages
    final_outputs = []
    for stage_name in final_stages:
        final_outputs.extend(_extract_out_paths(module_stages[stage_name].get("outs", [])))

    return final_outputs


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python -m core.registry.run_pipeline <module_id>")
        return 1

    module_id = sys.argv[1]

    # Check if module has stages
    stages = get_module_stages(module_id)
    if not stages:
        print(f"Error: Module '{module_id}' has no DVC stages defined in dvc.yaml")
        all_stages = get_module_stages("")
        if all_stages:
            print(f"Available stages: {', '.join(all_stages)}")
        return 1

    print(f"Running DVC pipeline for module: {module_id}")
    print(f"Stages: {', '.join(stages)}")

    # Run dvc repro on all stages for this module
    cmd = [".venv/bin/dvc", "repro"] + stages
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())