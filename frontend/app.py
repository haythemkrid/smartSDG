"""Streamlit frontend for SmartSDG Core Engine."""

from __future__ import annotations

import requests
import streamlit as st

# Page config
st.set_page_config(
    page_title="SmartSDG Core Engine",
    page_icon="🌍",
    layout="wide",
)

# Read API_BASE from secrets (works on Streamlit Cloud and locally with .streamlit/secrets.toml)
try:
    API_BASE = st.secrets.get("API_BASE", "http://localhost:8000")
except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_BASE = "http://localhost:8000"


@st.cache_data(ttl=60)
def fetch_modules() -> list[dict]:
    """Fetch deployed modules from the API."""
    try:
        response = requests.get(f"{API_BASE}/modules", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch modules: {e}")
        return []


@st.cache_data(ttl=60)
def fetch_timeseries(module_id: str) -> list[dict]:
    """Fetch time series data for a module."""
    try:
        response = requests.get(f"{API_BASE}/modules/{module_id}/timeseries", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch time series: {e}")
        return []


@st.cache_data(ttl=60)
def fetch_layers(module_id: str) -> list[dict]:
    """Fetch layers for a module."""
    try:
        response = requests.get(f"{API_BASE}/modules/{module_id}/layers", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch layers: {e}")
        return []


def main() -> None:
    st.title("🌍 SmartSDG Core Engine")
    st.caption("SDG Monitoring in Tunisia from Satellite Data")

    # Fetch modules
    modules = fetch_modules()

    if not modules:
        st.warning(
            "No deployed modules found. Make sure the API is running at http://localhost:8000"
        )
        st.info(
            "Run `make up` to start the stack, or check that modules are deployed in configs/deployed_modules.yaml"
        )
        return

    # Module selector in sidebar
    st.sidebar.header("Module Selection")
    module_options = {f"{m['title']} ({m['id']})": m for m in modules}
    selected_label = st.sidebar.selectbox("Select Module", list(module_options.keys()))
    selected_module = module_options[selected_label]

    # Display module info
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(selected_module["title"])
        st.write(f"**ID:** {selected_module['id']}")
        st.write(f"**Version:** {selected_module['version']}")
        st.write(f"**SDG:** {', '.join(f'SDG {s}' for s in selected_module['sdg'])}")
        st.write(f"**Sensors:** {', '.join(selected_module['sensors'])}")
        st.write(
            f"**Indices:** {', '.join(selected_module['indices']) if selected_module['indices'] else 'N/A'}"
        )
        st.write(f"**AOI:** {selected_module['aoi_id']}")
        st.write(f"**Temporal Resolution:** {selected_module['temporal_resolution'] or 'N/A'}")
        st.write(f"**Spatial Resolution:** {selected_module['spatial_resolution_m'] or 'N/A'} m")

    with col2:
        st.subheader("Outputs")
        for output in selected_module["outputs"]:
            st.write(f"- {output['name']} ({output['type']})")

    # Time series chart
    st.divider()
    st.subheader("📈 Time Series")

    timeseries = fetch_timeseries(selected_module["id"])
    if timeseries:
        import pandas as pd

        df = pd.DataFrame(timeseries)
        if not df.empty:
            # Convert time to datetime for plotting
            df["time"] = pd.to_datetime(df["time"])

            # Get unique metrics
            metrics = df["metric"].unique()

            if len(metrics) > 1:
                selected_metric = st.selectbox("Select Metric", metrics)
                df = df[df["metric"] == selected_metric]

            # Line chart
            st.line_chart(df.set_index("time")["value"])
            st.caption(f"Showing {len(df)} data points")
        else:
            st.info("No time series data available for this module.")
    else:
        st.info("No time series data available for this module.")

    # Layer display placeholder
    st.divider()
    st.subheader("🗺️ Map Layers")
    st.info(
        "Map layer display (COG/GeoParquet) requires a running API with actual data outputs. "
        "This will be implemented when pipeline outputs are available."
    )

    # Layers list
    layers = fetch_layers(selected_module["id"])
    if layers:
        st.write("Available layers:")
        for layer in layers:
            st.write(f"- {layer.get('name', 'Unknown')} ({layer.get('kind', 'Unknown')})")
    else:
        st.write("No layers available yet.")


if __name__ == "__main__":
    main()
