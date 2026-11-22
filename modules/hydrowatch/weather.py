"""Weather client for HydroWatch - Open-Meteo archive API."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from core.ingestion.geo import NoDataError


class WeatherClient:
    """Client for fetching historical weather data from Open-Meteo."""

    def __init__(
        self,
        url: str = "https://archive-api.open-meteo.com/v1/archive",
        timezone: str = "Africa/Tunis",
        precip_points: dict[str, dict] | None = None,
        temperature_point: dict | None = None,
        timeout: int = 30,
    ) -> None:
        self.url = url
        self.timezone = timezone
        self.timeout = timeout

        # Default points from manifest/hydrowatch_repo
        self.precip_points = precip_points or {
            "upper_algeria": {"lat": 36.28, "lon": 7.95, "weight": 0.45},
            "mid_border": {"lat": 36.45, "lon": 8.44, "weight": 0.35},
            "local_beja": {"lat": 36.62, "lon": 9.40, "weight": 0.20},
        }
        self.temperature_point = temperature_point or {"lat": 36.62, "lon": 9.40}

    def fetch_catchment_weather(
        self,
        start_date: date,
        end_date: date,
        cache_dir: Path | None = None,
    ) -> pd.DataFrame:
        """
        Fetch and aggregate historical weather for the Medjerda catchment.

        Args:
            start_date: Start date for weather data
            end_date: End date for weather data
            cache_dir: Optional directory to cache responses

        Returns:
            DataFrame with columns: quarter, upper_algeria_precip_mm, mid_border_precip_mm,
            local_beja_precip_mm, weighted_catchment_precip_mm, mean_temp_c
        """
        # Create cache key
        cache_key = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "precip_points": self.precip_points,
            "temperature_point": self.temperature_point,
        }
        cache_hash = hashlib.sha256(json.dumps(cache_key, sort_keys=True).encode()).hexdigest()[:16]

        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"{cache_hash}.json"
            if cache_file.exists():
                with open(cache_file) as f:
                    cached = json.load(f)
                return pd.DataFrame(cached)

        # Fetch precipitation for each point
        precip_dfs = []
        for name, point in self.precip_points.items():
            df = self._fetch_precipitation(point["lat"], point["lon"], start_date, end_date, name)
            precip_dfs.append(df)

        # Merge precipitation data
        basin_df = precip_dfs[0]
        for df in precip_dfs[1:]:
            basin_df = basin_df.merge(df, on="quarter", how="outer")

        # Fetch temperature
        temp_df = self._fetch_temperature(
            self.temperature_point["lat"],
            self.temperature_point["lon"],
            start_date,
            end_date,
        )

        # Merge temperature
        basin_df = basin_df.merge(temp_df, on="quarter", how="outer")

        # Fill missing values with 0 (as in spike)
        basin_df = basin_df.fillna(0)

        # Compute weighted catchment precipitation
        weights = {name: p["weight"] for name, p in self.precip_points.items()}
        precip_cols = [f"{name}_precip_mm" for name in self.precip_points.keys()]
        basin_df["weighted_catchment_precip_mm"] = sum(
            basin_df[col] * weights[name]
            for name, col in zip(self.precip_points.keys(), precip_cols, strict=False)
        )

        # Cache if directory provided
        if cache_dir:
            with open(cache_file, "w") as f:
                json.dump(basin_df.to_dict("records"), f)

        return basin_df

    def _fetch_precipitation(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
        name: str,
    ) -> pd.DataFrame:
        """Fetch precipitation for a single point."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "precipitation_sum",
            "timezone": self.timezone,
        }

        response = requests.get(self.url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if "daily" not in data:
            raise NoDataError(f"No daily data in response for {name}")

        daily = data["daily"]
        df = pd.DataFrame(
            {
                "time": daily["time"],
                "precipitation_sum": daily["precipitation_sum"],
            }
        )
        df["date"] = pd.to_datetime(df["time"])
        df["quarter"] = df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")

        quarterly = (
            df.groupby("quarter")
            .agg(**{f"{name}_precip_mm": ("precipitation_sum", "sum")})
            .reset_index()
        )

        return quarterly

    def _fetch_temperature(
        self,
        lat: float,
        lon: float,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Fetch temperature for a single point."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": self.timezone,
        }

        response = requests.get(self.url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if "daily" not in data:
            raise NoDataError("No daily data in temperature response")

        daily = data["daily"]
        df = pd.DataFrame(
            {
                "time": daily["time"],
                "temperature_2m_mean": daily["temperature_2m_mean"],
            }
        )
        df["date"] = pd.to_datetime(df["time"])
        df["quarter"] = df["date"].dt.to_period("Q").astype(str).str.replace("Q", "-Q")

        quarterly = (
            df.groupby("quarter").agg(mean_temp_c=("temperature_2m_mean", "mean")).reset_index()
        )

        return quarterly
