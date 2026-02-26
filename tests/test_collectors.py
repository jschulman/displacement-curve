#!/usr/bin/env python3
"""
Tests for the Displacement Curve data collectors and mock data generator.

Validates:
  - Mock data generation produces valid JSON files
  - Each collector's --mock mode outputs correct schema
  - Data has correct keys, date ranges, and numeric values
"""

import json
import os
import subprocess
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Add project root to path for imports
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, DATA_DIR)


class TestMockDataGenerator(unittest.TestCase):
    """Test the central mock data generator."""

    @classmethod
    def setUpClass(cls):
        """Run the mock data generator once before all tests."""
        result = subprocess.run(
            [sys.executable, os.path.join(DATA_DIR, "generate_mock_data.py")],
            capture_output=True, text=True, cwd=BASE_DIR,
        )
        assert result.returncode == 0, f"Generator failed: {result.stderr}"

    def _load_json(self, rel_path):
        path = os.path.join(DATA_DIR, rel_path)
        self.assertTrue(os.path.exists(path), f"File not found: {path}")
        with open(path) as f:
            return json.load(f)

    # -----------------------------------------------------------------------
    # BLS Employment
    # -----------------------------------------------------------------------

    def test_bls_file_exists_and_valid_json(self):
        data = self._load_json("bls/processed/employment.json")
        self.assertIn("metadata", data)
        self.assertIn("series", data)

    def test_bls_metadata(self):
        data = self._load_json("bls/processed/employment.json")
        meta = data["metadata"]
        self.assertEqual(meta["source"], "BLS CES")
        self.assertTrue(meta["mock"])
        self.assertIn("last_updated", meta)

    def test_bls_series_ids(self):
        data = self._load_json("bls/processed/employment.json")
        expected_ids = {
            "CES5541200001", "CES5541600001", "CES5541100001",
            "CES5541500001", "CES5000000001",
        }
        self.assertEqual(set(data["series"].keys()), expected_ids)

    def test_bls_series_data_structure(self):
        data = self._load_json("bls/processed/employment.json")
        for sid, series in data["series"].items():
            self.assertIn("name", series, f"Missing 'name' in {sid}")
            self.assertIn("data", series, f"Missing 'data' in {sid}")
            self.assertGreater(len(series["data"]), 30, f"Too few data points in {sid}")

            for point in series["data"]:
                self.assertIn("date", point)
                self.assertIn("value", point)
                self.assertRegex(point["date"], r"^\d{4}-\d{2}$")
                self.assertIsInstance(point["value"], (int, float))
                self.assertGreater(point["value"], 0)

    def test_bls_date_range(self):
        data = self._load_json("bls/processed/employment.json")
        first_series = next(iter(data["series"].values()))
        dates = [p["date"] for p in first_series["data"]]
        self.assertEqual(dates[0], "2022-11")
        self.assertEqual(dates[-1], "2026-02")

    def test_bls_value_ranges(self):
        """Verify values are in realistic BLS thousands range."""
        data = self._load_json("bls/processed/employment.json")
        accounting = data["series"]["CES5541200001"]
        vals = [p["value"] for p in accounting["data"]]
        self.assertTrue(all(900 < v < 1300 for v in vals),
                        f"Accounting values out of range: min={min(vals)}, max={max(vals)}")

        total = data["series"]["CES5000000001"]
        vals = [p["value"] for p in total["data"]]
        self.assertTrue(all(20000 < v < 25000 for v in vals),
                        f"Total P&BS values out of range: min={min(vals)}, max={max(vals)}")

    # -----------------------------------------------------------------------
    # Google Trends
    # -----------------------------------------------------------------------

    def test_trends_file_exists_and_valid_json(self):
        data = self._load_json("trends/processed/search_interest.json")
        self.assertIn("metadata", data)
        self.assertIn("categories", data)

    def test_trends_metadata(self):
        data = self._load_json("trends/processed/search_interest.json")
        meta = data["metadata"]
        self.assertEqual(meta["source"], "Google Trends")
        self.assertTrue(meta["mock"])
        self.assertEqual(meta["baseline"], "2023-01 = 100")

    def test_trends_categories(self):
        data = self._load_json("trends/processed/search_interest.json")
        expected = {"ai_adoption", "disruption_anxiety", "upskilling", "tool_adoption"}
        self.assertEqual(set(data["categories"].keys()), expected)

    def test_trends_category_structure(self):
        data = self._load_json("trends/processed/search_interest.json")
        for cat_name, cat in data["categories"].items():
            self.assertIn("terms", cat, f"Missing 'terms' in {cat_name}")
            self.assertIn("composite", cat, f"Missing 'composite' in {cat_name}")
            self.assertIsInstance(cat["terms"], list)
            self.assertGreater(len(cat["terms"]), 0)
            self.assertGreater(len(cat["composite"]), 30)

            for point in cat["composite"]:
                self.assertIn("date", point)
                self.assertIn("value", point)
                self.assertRegex(point["date"], r"^\d{4}-\d{2}$")
                self.assertIsInstance(point["value"], (int, float))
                self.assertGreater(point["value"], 0)

    def test_trends_date_range(self):
        data = self._load_json("trends/processed/search_interest.json")
        cat = next(iter(data["categories"].values()))
        dates = [p["date"] for p in cat["composite"]]
        self.assertEqual(dates[0], "2022-11")
        self.assertEqual(dates[-1], "2026-02")

    # -----------------------------------------------------------------------
    # GitHub Activity
    # -----------------------------------------------------------------------

    def test_github_file_exists_and_valid_json(self):
        data = self._load_json("github/processed/activity.json")
        self.assertIn("metadata", data)
        self.assertIn("categories", data)
        self.assertIn("aggregate", data)

    def test_github_metadata(self):
        data = self._load_json("github/processed/activity.json")
        meta = data["metadata"]
        self.assertEqual(meta["source"], "GitHub API")
        self.assertTrue(meta["mock"])

    def test_github_categories(self):
        data = self._load_json("github/processed/activity.json")
        expected = {"ai_accounting", "ai_legal", "ai_compliance", "llm_agents", "ai_automation"}
        self.assertEqual(set(data["categories"].keys()), expected)

    def test_github_category_structure(self):
        data = self._load_json("github/processed/activity.json")
        for cat_name, cat in data["categories"].items():
            self.assertIn("topic", cat, f"Missing 'topic' in {cat_name}")
            self.assertIn("data", cat, f"Missing 'data' in {cat_name}")
            self.assertGreater(len(cat["data"]), 30)

            for point in cat["data"]:
                self.assertIn("date", point)
                self.assertIn("new_repos", point)
                self.assertIn("total_stars", point)
                self.assertIn("contributors", point)
                self.assertRegex(point["date"], r"^\d{4}-\d{2}$")
                self.assertIsInstance(point["new_repos"], int)
                self.assertIsInstance(point["total_stars"], int)
                self.assertGreater(point["new_repos"], 0)
                self.assertGreater(point["total_stars"], 0)

    def test_github_aggregate(self):
        data = self._load_json("github/processed/activity.json")
        agg = data["aggregate"]
        self.assertGreater(len(agg), 30)

        for point in agg:
            self.assertIn("date", point)
            self.assertIn("total_new_repos", point)
            self.assertIn("total_stars", point)
            self.assertIn("total_contributors", point)

    def test_github_stars_growth(self):
        """Stars should grow over time (exponential pattern)."""
        data = self._load_json("github/processed/activity.json")
        agg = data["aggregate"]
        first_stars = agg[0]["total_stars"]
        last_stars = agg[-1]["total_stars"]
        self.assertGreater(last_stars, first_stars * 10,
                           "GitHub stars should show significant growth")

    def test_github_llm_agents_largest(self):
        """llm_agents category should be the largest by stars."""
        data = self._load_json("github/processed/activity.json")
        final_stars = {}
        for cat_name, cat in data["categories"].items():
            final_stars[cat_name] = cat["data"][-1]["total_stars"]
        largest = max(final_stars, key=final_stars.get)
        self.assertEqual(largest, "llm_agents",
                         f"Expected llm_agents to have most stars, got {largest}")

    def test_github_date_range(self):
        data = self._load_json("github/processed/activity.json")
        agg = data["aggregate"]
        self.assertEqual(agg[0]["date"], "2022-11")
        self.assertEqual(agg[-1]["date"], "2026-02")


class TestCollectorMockMode(unittest.TestCase):
    """Test each collector's --mock mode runs successfully."""

    def _run_collector(self, script, extra_args=None):
        args = [sys.executable, os.path.join(BASE_DIR, "collectors", script), "--mock"]
        if extra_args:
            args.extend(extra_args)
        result = subprocess.run(args, capture_output=True, text=True, cwd=BASE_DIR)
        self.assertEqual(result.returncode, 0,
                         f"{script} --mock failed:\nstdout: {result.stdout}\nstderr: {result.stderr}")
        return result

    def test_bls_collector_mock(self):
        self._run_collector("bls_employment.py")
        path = os.path.join(DATA_DIR, "bls", "processed", "employment.json")
        self.assertTrue(os.path.exists(path))

    def test_google_trends_collector_mock(self):
        self._run_collector("google_trends.py")
        path = os.path.join(DATA_DIR, "trends", "processed", "search_interest.json")
        self.assertTrue(os.path.exists(path))

    def test_github_collector_mock(self):
        self._run_collector("github_activity.py")
        path = os.path.join(DATA_DIR, "github", "processed", "activity.json")
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
