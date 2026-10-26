import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from scripts.validate_submission import validate


class ValidateSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.reference = self.root / "sample.tif"
        self.candidate = self.root / "candidate.tif"
        self.profile = {
            "driver": "GTiff",
            "height": 4,
            "width": 5,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:32611",
            "transform": from_origin(400000, 4500000, 100, 100),
            "nodata": np.nan,
        }
        arr = np.zeros((4, 5), dtype=np.float32)
        arr[0, 0] = np.nan
        with rasterio.open(self.reference, "w", **self.profile) as ds:
            ds.write(arr, 1)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_candidate(self, array, **overrides):
        profile = {**self.profile, **overrides}
        with rasterio.open(self.candidate, "w", **profile) as ds:
            ds.write(array.astype(profile["dtype"]), 1)

    def test_accepts_valid_probability_raster_with_nodata_outside(self):
        arr = np.full((4, 5), 0.25, dtype=np.float32)
        arr[0, 0] = np.nan
        self.write_candidate(arr)
        result = validate(self.candidate, self.reference)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["checks"]["candidate"]["crs"], "EPSG:32611")
        self.assertTrue(result["checks"]["range_0_1_inside_footprint"])

    def test_rejects_value_above_one(self):
        arr = np.full((4, 5), 0.25, dtype=np.float32)
        arr[1, 2] = 1.01
        arr[0, 0] = np.nan
        self.write_candidate(arr)
        result = validate(self.candidate, self.reference)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["range_0_1_inside_footprint"])

    def test_rejects_nan_inside_footprint(self):
        arr = np.full((4, 5), 0.25, dtype=np.float32)
        arr[2, 2] = np.nan
        self.write_candidate(arr)
        result = validate(self.candidate, self.reference)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["no_nan_inside_footprint"])

    def test_rejects_dtype_other_than_float32(self):
        arr = np.full((4, 5), 0.25, dtype=np.float64)
        self.write_candidate(arr, dtype="float64")
        result = validate(self.candidate, self.reference)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["dtype_is_float32"])

    def test_rejects_transform_mismatch(self):
        arr = np.full((4, 5), 0.25, dtype=np.float32)
        self.write_candidate(arr, transform=from_origin(400001, 4500000, 100, 100))
        result = validate(self.candidate, self.reference)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["transform_match"])

    def test_rejects_inside_values_marked_as_nodata(self):
        arr = np.zeros((4, 5), dtype=np.float32)
        self.write_candidate(arr, nodata=0.0)
        result = validate(self.candidate, self.reference)
        self.assertFalse(result["ok"])
        self.assertFalse(result["checks"]["mask_valid_inside_footprint"])


if __name__ == "__main__":
    unittest.main()
