#!/usr/bin/env python3
"""
BLS Employment Data Collector for the Displacement Curve.

Fetches Current Employment Statistics (CES) data from the Bureau of Labor
Statistics Public Data API v2 (API key required, 500 queries/day).

Series tracked:
  CES5541200001 - Accounting & Tax Preparation
  CES5541600001 - Management & Technical Consulting
  CES5541100001 - Legal Services
  CES5541500001 - Computer Systems Design
  CES5000000001 - Total Professional & Business Services

Usage:
  python collectors/bls_employment.py              # live API
  python collectors/bls_employment.py --mock        # generate mock data
  python collectors/bls_employment.py --start-year 2022 --end-year 2026
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "bls", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "bls", "processed")

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

SERIES = {
    "CES5541200001": "Accounting & Tax Preparation",
    "CES5541600001": "Management & Technical Consulting",
    "CES5541100001": "Legal Services",
    "CES5541500001": "Computer Systems Design",
    "CES5000000001": "Total Professional & Business Services",
}

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


# ---------------------------------------------------------------------------
# API Fetch
# ---------------------------------------------------------------------------

def fetch_bls_data(series_ids, start_year, end_year, api_key=None):
    """Fetch data from BLS Public Data API v2."""
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  BLS API request (attempt {attempt}/{MAX_RETRIES})...")
            resp = requests.post(BLS_API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "REQUEST_SUCCEEDED":
                msg = data.get("message", ["Unknown error"])
                print(f"  BLS API error: {msg}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
                raise RuntimeError(f"BLS API returned non-success status: {msg}")

            return data

        except requests.RequestException as exc:
            print(f"  Request failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise

    raise RuntimeError("All BLS API retries exhausted")


def process_bls_response(raw_data):
    """Transform raw BLS API response into our standard schema."""
    series_output = {}

    for s in raw_data.get("Results", {}).get("series", []):
        sid = s["seriesID"]
        name = SERIES.get(sid, sid)
        points = []

        for item in sorted(s.get("data", []), key=lambda x: (x["year"], x["period"])):
            if not item["period"].startswith("M"):
                continue
            month = int(item["period"][1:])
            year = int(item["year"])
            dl = f"{year}-{month:02d}"
            val = float(item["value"])
            points.append({"date": dl, "value": val})

        series_output[sid] = {"name": name, "data": points}

    return {
        "metadata": {
            "source": "BLS CES",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "series": series_output,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock(start_year, end_year):
    """Delegate to the central mock generator and return BLS data."""
    # Import the shared generator so we have one source of truth for mock data
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_data import generate_bls_data
    data = generate_bls_data()
    # Filter to requested year range
    for sid in data["series"]:
        data["series"][sid]["data"] = [
            p for p in data["series"][sid]["data"]
            if start_year <= int(p["date"][:4]) <= end_year
        ]
    return data


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved {path} ({os.path.getsize(path)} bytes)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="BLS Employment Data Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling API")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (default: 2026)")
    parser.add_argument("--api-key", type=str, default=os.environ.get("BLS_API_KEY"), help="BLS API v2 key (or set BLS_API_KEY env var)")
    args = parser.parse_args()

    print("BLS Employment Collector")
    print(f"  Range: {args.start_year}-{args.end_year}")
    api_ver = "v2 (keyed)" if args.api_key else "v2 (no key)"
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE API ' + api_ver}\n")

    if args.mock:
        processed = generate_mock(args.start_year, args.end_year)
    else:
        raw = fetch_bls_data(list(SERIES.keys()), args.start_year, args.end_year, args.api_key)
        # Save raw response
        raw_path = os.path.join(RAW_DIR, f"bls_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw, raw_path)
        processed = process_bls_response(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "employment.json"))
    print("\nBLS collection complete.")


if __name__ == "__main__":
    main()
