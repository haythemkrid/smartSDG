"""Tests for spectral index formulas in core/ingestion/indices.py."""

from __future__ import annotations

import warnings

import numpy as np

from core.ingestion.indices import cloud_mask_from_scl, mndwi, ndbi, ndwi

# Suppress RuntimeWarning for divide by zero in tests (expected behavior)
warnings.filterwarnings(
    "ignore", message="invalid value encountered in divide", category=RuntimeWarning
)
warnings.filterwarnings(
    "ignore", message="divide by zero encountered in divide", category=RuntimeWarning
)


class TestNDWI:
    """Tests for NDWI formula."""

    def test_basic_ndwi(self) -> None:
        """Test NDWI with simple values."""
        green = np.array([[100, 200], [50, 150]], dtype=np.float32)
        nir = np.array([[50, 100], [25, 75]], dtype=np.float32)

        # NDWI = (green - nir) / (green + nir)
        # Pixel (0,0): (100-50)/(100+50) = 50/150 = 0.333
        # Pixel (0,1): (200-100)/(200+100) = 100/300 = 0.333
        # Pixel (1,0): (50-25)/(50+25) = 25/75 = 0.333
        # Pixel (1,1): (150-75)/(150+75) = 75/225 = 0.333
        result = ndwi(green, nir)
        expected = np.full((2, 2), 1 / 3, dtype=np.float32)
        np.testing.assert_allclose(result, expected)

    def test_zero_denominator(self) -> None:
        """Test NDWI returns 0 where denominator is 0."""
        green = np.array([[0, 100], [0, 0]], dtype=np.float32)
        nir = np.array([[0, 100], [0, 0]], dtype=np.float32)

        result = ndwi(green, nir)
        # Where both are 0, result should be 0
        assert result[0, 0] == 0.0
        assert result[1, 0] == 0.0
        assert result[1, 1] == 0.0
        # Where green=nir=100, result = 0
        assert result[0, 1] == 0.0

    def test_ndwi_range(self) -> None:
        """Test NDWI values are in [-1, 1] range."""
        green = np.random.rand(10, 10).astype(np.float32) * 1000
        nir = np.random.rand(10, 10).astype(np.float32) * 1000

        result = ndwi(green, nir)
        assert np.all(result >= -1.0)
        assert np.all(result <= 1.0)

    def test_water_high_ndwi(self) -> None:
        """Test water pixels have high NDWI (green > nir)."""
        green = np.array([[1000, 100]], dtype=np.float32)
        nir = np.array([[100, 1000]], dtype=np.float32)

        result = ndwi(green, nir)
        # Water: green > nir -> positive NDWI
        assert result[0, 0] > 0
        # Land: nir > green -> negative NDWI
        assert result[0, 1] < 0


class TestMNDWI:
    """Tests for MNDWI formula."""

    def test_basic_mndwi(self) -> None:
        """Test MNDWI with simple values."""
        green = np.array([[100, 200]], dtype=np.float32)
        swir = np.array([[50, 100]], dtype=np.float32)

        result = mndwi(green, swir)
        expected = np.array([[1 / 3, 1 / 3]], dtype=np.float32)
        np.testing.assert_allclose(result, expected)

    def test_zero_denominator(self) -> None:
        """Test MNDWI returns 0 where denominator is 0."""
        green = np.array([[0, 100]], dtype=np.float32)
        swir = np.array([[0, 100]], dtype=np.float32)

        result = mndwi(green, swir)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 0.0


class TestNDBI:
    """Tests for NDBI formula."""

    def test_basic_ndbi(self) -> None:
        """Test NDBI with simple values."""
        swir = np.array([[100, 200]], dtype=np.float32)
        nir = np.array([[50, 100]], dtype=np.float32)

        result = ndbi(swir, nir)
        expected = np.array([[1 / 3, 1 / 3]], dtype=np.float32)
        np.testing.assert_allclose(result, expected)

    def test_zero_denominator(self) -> None:
        """Test NDBI returns 0 where denominator is 0."""
        swir = np.array([[0, 100]], dtype=np.float32)
        nir = np.array([[0, 100]], dtype=np.float32)

        result = ndbi(swir, nir)
        assert result[0, 0] == 0.0
        assert result[0, 1] == 0.0


class TestCloudMaskFromSCL:
    """Tests for cloud mask from SCL."""

    def test_cloud_mask_basic(self) -> None:
        """Test cloud mask with default classes."""
        scl = np.array([[1, 3, 4], [8, 9, 10], [2, 6, 7]], dtype=np.uint8)
        # Classes 3, 8, 9, 10 are cloud/shadow
        result = cloud_mask_from_scl(scl, [3, 8, 9, 10])

        expected = np.array(
            [
                [False, True, False],
                [True, True, True],
                [False, False, False],
            ]
        )
        np.testing.assert_array_equal(result, expected)

    def test_custom_classes(self) -> None:
        """Test cloud mask with custom classes."""
        scl = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
        result = cloud_mask_from_scl(scl, [3, 6])

        expected = np.array(
            [
                [False, False, True],
                [False, False, True],
            ]
        )
        np.testing.assert_array_equal(result, expected)

    def test_no_clouds(self) -> None:
        """Test cloud mask with no cloud pixels."""
        scl = np.array([[1, 2, 4], [5, 7, 11]], dtype=np.uint8)
        result = cloud_mask_from_scl(scl, [3, 8, 9, 10])

        assert not np.any(result)

    def test_all_clouds(self) -> None:
        """Test cloud mask with all cloud pixels."""
        scl = np.array([[3, 8], [9, 10]], dtype=np.uint8)
        result = cloud_mask_from_scl(scl, [3, 8, 9, 10])

        assert np.all(result)
