"""HydroWatch pipeline runner for DVC stages."""

from __future__ import annotations

import json
import pickle
from datetime import date
from pathlib import Path
from typing import Any

import click
import pandas as pd

from core.ingestion.geo import NoDataError
from core.registry.module_loader import ModuleLoader
from core.sdk.schemas import AOI


@click.group()
def cli() -> None:
    """HydroWatch pipeline commands."""
    pass


def load_module() -> Any:
    """Load HydroWatch module."""
    loader = ModuleLoader()
    return loader.load_module("hydrowatch")


def load_aoi() -> AOI:
    """Load Sidi Salem AOI from configs."""
    import yaml

    with open("configs/tunisia_aois.geojson") as f:
        geojson = yaml.safe_load(f)
    for feature in geojson["features"]:
        if feature["properties"]["id"] == "sidi_salem":
            return AOI(
                id=feature["properties"]["id"],
                name=feature["properties"]["name"],
                geometry=feature["geometry"],
            )
    raise NoDataError("sidi_salem AOI not found")


def load_params() -> dict:
    """Load parameters from configs and manifest."""
    import yaml

    with open("configs/pipeline_default.yaml") as f:
        global_params = yaml.safe_load(f)

    with open("modules/hydrowatch/manifest.yaml") as f:
        manifest = yaml.safe_load(f)

    # Merge params: global < manifest
    params = {}
    params.update(global_params)
    params.update(manifest.get("params", {}))
    params["aoi_id"] = manifest.get("aoi_id", "sidi_salem")

    return params


@cli.command()
@click.option("--output", default="data/processed/hydrowatch/ingest.json")
def ingest(output: str) -> None:
    """Run ingestion stage: search STAC items and fetch weather."""
    module = load_module()
    aoi = load_aoi()
    params = load_params()

    date_range = (
        date.fromisoformat(params["date_range"]["start"]),
        date.fromisoformat(params["date_range"]["end"]),
    )

    result = module.ingest(aoi, date_range, params)

    # Save items and weather
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert items to serializable format
    items_data = []
    for item in result["items"]:
        items_data.append(
            {
                "id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "bbox": item.bbox,
                "geometry": item.geometry,
                "properties": item.properties,
                "assets": {k: v.href for k, v in item.assets.items()},
            }
        )

    weather_data = result["weather"].to_dict("records")

    with open(output_path, "w") as f:
        json.dump({"items": items_data, "weather": weather_data}, f)

    click.echo(f"Ingest complete: {len(items_data)} items, {len(weather_data)} weather records")


@cli.command()
@click.option("--input", default="data/processed/hydrowatch/ingest.json")
@click.option("--output", default="data/processed/hydrowatch/indices.json")
def compute_indices(input: str, output: str) -> None:
    """Run compute_indices stage."""
    load_module()

    with open(input) as f:
        json.load(f)

    # Reconstruct items (simplified - in reality would need full STAC items)
    # For now, we need the actual STAC items to compute indices
    # This stage requires network access to read bands
    click.echo("compute_indices requires network access to read STAC assets")
    click.echo("Run the full pipeline via the module's ingest method instead")

    # Save placeholder
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"records": [], "note": "Requires STAC asset access"}, f)


@cli.command()
@click.option("--input", default="data/processed/hydrowatch/indices.json")
@click.option("--output", default="data/processed/hydrowatch/model.pkl")
def train(input: str, output: str) -> None:
    """Run train stage."""
    module = load_module()
    params = load_params()

    with open(input) as f:
        data = json.load(f)

    if "records" not in data or not data["records"]:
        raise NoDataError("No records to train on")

    dataset = {
        "records": data["records"],
        "weather": pd.DataFrame(data["weather"]),
    }

    model = module.train(dataset, params)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        pickle.dump(model, f)

    click.echo(f"Training complete. Model saved to {output}")


@cli.command()
@click.option("--input", default="data/processed/hydrowatch/indices.json")
@click.option("--model", default="data/processed/hydrowatch/model.pkl")
@click.option("--output", default="data/processed/hydrowatch/predictions.json")
def infer(input: str, model: str, output: str) -> None:
    """Run infer stage."""
    module = load_module()
    params = load_params()

    with open(input) as f:
        data = json.load(f)

    with open(model, "rb") as f:
        model_artifact = pickle.load(f)

    dataset = {
        "records": data["records"],
        "weather": pd.DataFrame(data["weather"]),
    }

    predictions = module.infer(dataset, model_artifact, params)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert predictions to serializable format
    pred_data = {
        "area_ts": predictions["area_ts"].to_dict("records"),
        "backtest": predictions["backtest"].to_dict("records"),
    }

    with open(output_path, "w") as f:
        json.dump(pred_data, f)

    click.echo(f"Inference complete. Predictions saved to {output}")


@cli.command()
@click.option("--input", default="data/processed/hydrowatch/predictions.json")
@click.option("--output", default="data/outputs/hydrowatch/metrics.json")
def evaluate(input: str, output: str) -> None:
    """Run evaluate stage."""
    module = load_module()
    params = load_params()

    with open(input) as f:
        predictions = json.load(f)

    # Reconstruct predictions object
    pred_obj = {
        "backtest": pd.DataFrame(predictions["backtest"]),
    }

    metrics = module.evaluate(pred_obj, None, params)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)

    click.echo(f"Evaluation complete. Metrics: {metrics}")


@cli.command()
@click.option("--input", default="data/processed/hydrowatch/predictions.json")
@click.option("--output-dir", default="data/outputs/hydrowatch")
def export(input: str, output_dir: str) -> None:
    """Run export stage: write COG and GeoParquet."""
    module = load_module()
    load_params()

    with open(input) as f:
        predictions = json.load(f)

    # Reconstruct predictions object
    pred_obj = {
        "records": predictions.get("records", []),
        "area_ts": pd.DataFrame(predictions["area_ts"]),
    }

    layers = module.export_layers(pred_obj, Path(output_dir))

    click.echo(f"Export complete. {len(layers)} layers written to {output_dir}")
    for layer in layers:
        click.echo(f"  - {layer.name} ({layer.kind}): {layer.path}")


@cli.command()
def run_all() -> None:
    """Run full pipeline (requires network for STAC access)."""
    click.echo("Full pipeline requires network access for STAC search and asset reading.")
    click.echo("Run individual stages or use the module directly in a script.")


if __name__ == "__main__":
    cli()
