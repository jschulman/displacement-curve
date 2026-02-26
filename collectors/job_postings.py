#!/usr/bin/env python3
"""
Job Postings Collector for the Displacement Curve.

Fetches JOLTS (Job Openings and Labor Turnover Survey) data from the
BLS Public Data API v2 for Professional & Business Services sector.

JOLTS Series:
  JTS540000000000000JOL - Job Openings
  JTS540000000000000HIL - Hires
  JTS540000000000000TSL - Total Separations
  JTS540000000000000QUL - Quits

Usage:
  python collectors/job_postings.py                           # live API
  python collectors/job_postings.py --mock                    # generate mock data
  python collectors/job_postings.py --start-year 2022 --end-year 2025
  python collectors/job_postings.py --api-key YOUR_KEY
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
RAW_DIR = os.path.join(BASE_DIR, "data", "jobs", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "jobs", "processed")

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

JOLTS_SERIES = {
    "JTS540099000000000JOL": "Job Openings - Prof & Business Services",
    "JTS540099000000000HIL": "Hires - Prof & Business Services",
    "JTS540099000000000TSL": "Total Separations - Prof & Business Services",
    "JTS540099000000000QUL": "Quits - Prof & Business Services",
}

# Map series IDs to short field names for output
SERIES_FIELD_MAP = {
    "JTS540099000000000JOL": "job_openings",
    "JTS540099000000000HIL": "hires",
    "JTS540099000000000TSL": "separations",
    "JTS540099000000000QUL": "quits",
}

# Baseline month for indexing: November 2022 = 100
BASELINE_DATE = "2022-11"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


# ---------------------------------------------------------------------------
# Live Mode (BLS JOLTS API)
# ---------------------------------------------------------------------------

def fetch_jolts_data(series_ids, start_year, end_year, api_key=None):
    """
    Fetch JOLTS data from BLS Public Data API v2.

    Returns raw API response JSON.
    """
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  BLS JOLTS API request (attempt {attempt}/{MAX_RETRIES})...")
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


def process_jolts_data(raw_data):
    """
    Transform raw BLS JOLTS API response into standard job postings schema.

    Indexes job openings to baseline month (Nov 2022 = 100) for
    total_postings_idx, and computes ai_to_traditional_ratio as
    job_openings / baseline_openings (labor demand ratio).
    """
    # Parse each series into {date: value} dicts
    series_data = {}
    for s in raw_data.get("Results", {}).get("series", []):
        sid = s["seriesID"]
        field = SERIES_FIELD_MAP.get(sid)
        if not field:
            continue

        points = {}
        for item in s.get("data", []):
            period = item.get("period", "")
            if not period.startswith("M"):
                continue
            month = int(period[1:])
            if month < 1 or month > 12:
                continue
            year = int(item["year"])
            date_label = f"{year}-{month:02d}"
            val = float(item["value"])
            points[date_label] = val

        series_data[field] = points

    # Collect all dates across all series
    all_dates = set()
    for field_points in series_data.values():
        all_dates.update(field_points.keys())
    all_dates = sorted(all_dates)

    # Find baseline value for job openings (Nov 2022)
    job_openings_data = series_data.get("job_openings", {})
    baseline_openings = job_openings_data.get(BASELINE_DATE)

    if baseline_openings is None or baseline_openings == 0:
        # Fall back to first available data point
        if job_openings_data:
            first_date = sorted(job_openings_data.keys())[0]
            baseline_openings = job_openings_data[first_date]
            print(f"  WARNING: No data for baseline {BASELINE_DATE}, using {first_date} = {baseline_openings}")
        else:
            baseline_openings = 1  # Avoid division by zero

    # Build monthly output
    monthly = []
    for date_label in all_dates:
        jo = series_data.get("job_openings", {}).get(date_label)
        hi = series_data.get("hires", {}).get(date_label)
        sep = series_data.get("separations", {}).get(date_label)
        qu = series_data.get("quits", {}).get(date_label)

        # Index to baseline
        if jo is not None and baseline_openings:
            total_postings_idx = round((jo / baseline_openings) * 100, 1)
            ai_to_trad_ratio = round(jo / baseline_openings, 3)
        else:
            total_postings_idx = None
            ai_to_trad_ratio = None

        monthly.append({
            "date": date_label,
            "total_postings_idx": total_postings_idx,
            "ai_postings_pct": None,
            "traditional_pct": None,
            "ai_to_traditional_ratio": ai_to_trad_ratio,
            "job_openings": jo,
            "hires": hi,
            "separations": sep,
            "quits": qu,
        })

    return {
        "metadata": {
            "source": "BLS JOLTS",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "monthly": monthly,
        "firms": {},
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock(start_year, end_year):
    """Delegate to the central Phase 3 mock generator and return job data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase3 import generate_job_postings
    data = generate_job_postings()
    # Filter to requested year range
    data["monthly"] = [
        m for m in data["monthly"]
        if start_year <= int(m["date"][:4]) <= end_year
    ]
    for ticker in data["firms"]:
        data["firms"][ticker]["monthly"] = [
            m for m in data["firms"][ticker]["monthly"]
            if start_year <= int(m["date"][:4]) <= end_year
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
    parser = argparse.ArgumentParser(description="Job Postings Collector (BLS JOLTS)")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling API")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")
    parser.add_argument("--api-key", type=str, default=os.environ.get("BLS_API_KEY"),
                        help="BLS API v2 key (or set BLS_API_KEY env var)")
    args = parser.parse_args()

    print("Job Postings Collector (BLS JOLTS)")
    print(f"  Range: {args.start_year}-{args.end_year}")
    api_ver = "v2 (keyed)" if args.api_key else "v2 (no key)"
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE API ' + api_ver}\n")

    if args.mock:
        processed = generate_mock(args.start_year, args.end_year)
    else:
        raw = fetch_jolts_data(list(JOLTS_SERIES.keys()), args.start_year, args.end_year, args.api_key)
        # Save raw response
        raw_path = os.path.join(RAW_DIR, f"jolts_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw, raw_path)
        processed = process_jolts_data(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "postings.json"))
    print("\nJob postings collection complete.")


if __name__ == "__main__":
    main()
