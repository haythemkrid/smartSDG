"""Tests for STAC client in core/ingestion/stac_client.py."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.ingestion.stac_client import NoDataError, STACClient
from core.sdk.schemas import AOI


class TestSTACClient:
    """Tests for STACClient."""

    @pytest.fixture
    def sidi_salem_aoi(self) -> AOI:
        """Sidi Salem AOI from configs."""
        return AOI(
            id="sidi_salem",
            name="Sidi Salem dam",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [9.355, 36.585],
                        [9.455, 36.585],
                        [9.455, 36.655],
                        [9.355, 36.655],
                        [9.355, 36.585],
                    ]
                ],
            },
        )

    @patch("core.ingestion.stac_client.pystac_client.Client.open")
    def test_search_raises_no_data_error_on_empty(
        self, mock_catalog_open: MagicMock, sidi_salem_aoi: AOI
    ) -> None:
        """Test that search raises NoDataError when no items found."""
        # Mock the catalog to return no items
        mock_catalog = MagicMock()
        mock_search = MagicMock()
        mock_search.items.return_value = iter([])
        mock_catalog.search.return_value = mock_search
        mock_catalog_open.return_value = mock_catalog

        client = STACClient()

        with pytest.raises(NoDataError):
            client.search(
                aoi=sidi_salem_aoi,
                date_range=(date(2030, 1, 1), date(2030, 12, 31)),
                max_cloud=15,
            )

    def test_search_saves_query(self, sidi_salem_aoi: AOI, tmp_path: Path) -> None:
        """Test that search saves query to data/raw/queries/."""
        client = STACClient()

        # We can't test actual search without network, but we can test
        # the _save_query method directly
        from datetime import datetime

        from pystac import Item

        # Create mock items
        items = [
            Item(
                id="item1",
                geometry=None,
                bbox=[0, 0, 1, 1],
                datetime=datetime(2023, 1, 1),
                properties={},
            ),
            Item(
                id="item2",
                geometry=None,
                bbox=[0, 0, 1, 1],
                datetime=datetime(2023, 4, 1),
                properties={},
            ),
        ]

        query_hash = client._save_query(
            aoi=sidi_salem_aoi,
            date_range=(date(2023, 1, 1), date(2023, 12, 31)),
            collections=["sentinel-2-l2a"],
            max_cloud=15,
            items=items,
        )

        # Check hash is deterministic
        query_hash2 = client._save_query(
            aoi=sidi_salem_aoi,
            date_range=(date(2023, 1, 1), date(2023, 12, 31)),
            collections=["sentinel-2-l2a"],
            max_cloud=15,
            items=items,
        )
        assert query_hash == query_hash2

        # Check file exists
        query_file = Path("data/raw/queries") / f"{query_hash}.json"
        assert query_file.exists()

        # Check file content
        with open(query_file) as f:
            data = json.load(f)
        assert data["aoi_id"] == "sidi_salem"
        assert data["item_ids"] == ["item1", "item2"]

    def test_select_first_per_quarter(self, sidi_salem_aoi: AOI) -> None:
        """Test selecting first scene per quarter."""
        from datetime import datetime

        from pystac import Item, ItemCollection

        client = STACClient()

        # Create items spanning multiple quarters
        items = ItemCollection(
            [
                Item(
                    id="item1",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 1, 15),
                    properties={},
                ),
                Item(
                    id="item2",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 2, 1),
                    properties={},
                ),  # Same quarter
                Item(
                    id="item3",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 4, 10),
                    properties={},
                ),  # Q2
                Item(
                    id="item4",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 5, 1),
                    properties={},
                ),  # Same quarter
                Item(
                    id="item5",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 7, 1),
                    properties={},
                ),  # Q3
                Item(
                    id="item6",
                    geometry=None,
                    bbox=[0, 0, 1, 1],
                    datetime=datetime(2023, 10, 1),
                    properties={},
                ),  # Q4
            ]
        )

        selected = client.select_first_per_quarter(items)

        assert len(selected) == 4
        assert selected[0].id == "item1"  # Q1 earliest
        assert selected[1].id == "item3"  # Q2 earliest
        assert selected[2].id == "item5"  # Q3
        assert selected[3].id == "item6"  # Q4


class TestLoadBands:
    """Tests for load_bands function."""

    def test_load_bands_requires_valid_item(self) -> None:
        """Test that load_bands validates band names."""
        from datetime import datetime

        from pystac import Item

        item = Item(
            id="test",
            geometry=None,
            bbox=[0, 0, 1, 1],
            datetime=datetime(2023, 1, 1),
            properties={},
        )

        # Item has no assets, should raise
        with pytest.raises(ValueError, match="Band B03 not found"):
            from core.ingestion.stac_client import load_bands

            aoi = AOI(
                id="test",
                name="test",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                },
            )
            load_bands(item, ["B03"], aoi)
