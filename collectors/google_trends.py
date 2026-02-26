#!/usr/bin/env python3
"""
Google Trends Data Collector for the Displacement Curve.

Fetches search-interest data via the pytrends library for four
categories of AI-displacement signals. Applies a 12-week rolling
average for smoothing.

Usage:
  python collectors/google_trends.py              # live pytrends
  python collectors/google_trends.py --mock        # generate mock data
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# pytrends is optional at import time so --mock works without it
try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "trends", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "trends", "processed")

CATEGORIES = {
    "ai_adoption": [
        "AI agent for accounting",
        "AI audit tool",
        "AI compliance software",
    ],
    "disruption_anxiety": [
        "AI replacing consultants",
        "AI replacing accountants",
        "AI replacing lawyers",
    ],
    "upskilling": [
        "AI certification accounting",
        "AI for CPAs",
        "prompt engineering for consultants",
    ],
    "tool_adoption": [
        "ChatGPT for audit",
        "Claude for accounting",
        "AI tax preparation",
    ],
}

RATE_LIMIT_SECONDS = 2  # pytrends gets blocked easily


# ---------------------------------------------------------------------------
# Rolling average helper
# ---------------------------------------------------------------------------

def rolling_average(values, window=12):
    """Compute rolling average with given window size. Pads start with available data."""
    result = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = values[start:i + 1]
        result.append(round(sum(chunk) / len(chunk), 1))
    return result


# ---------------------------------------------------------------------------
# Live fetch
# ---------------------------------------------------------------------------

def fetch_trends_data():
    """Fetch Google Trends data via pytrends for all categories."""
    if TrendReq is None:
        print("ERROR: pytrends is not installed. Install with: pip install pytrends")
        sys.exit(1)

    pytrends = TrendReq(hl="en-US", tz=360)
    timeframe = "2022-11-01 2026-02-28"
    raw_results = {}

    for cat_name, terms in CATEGORIES.items():
        print(f"  Fetching category: {cat_name}")
        cat_raw = {}

        for term in terms:
            print(f"    Term: {term}")
            pytrends.build_payload([term], cat=0, timeframe=timeframe, geo="US")
            df = pytrends.interest_over_time()

            if df.empty:
                print(f"    WARNING: No data for '{term}'")
                cat_raw[term] = []
                continue

            points = []
            for idx, row in df.iterrows():
                points.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "value": int(row[term]),
                })
            cat_raw[term] = points

            time.sleep(RATE_LIMIT_SECONDS)

        raw_results[cat_name] = cat_raw

    return raw_results


def process_trends_raw(raw_results):
    """
    Process raw per-term weekly data into monthly composite with 12-week smoothing.
    Rebase to Jan 2023 = 100.
    """
    categories_out = {}

    for cat_name, terms_data in raw_results.items():
        # Aggregate by month: average across terms
        monthly = {}
        for term, points in terms_data.items():
            for p in points:
                ym = p["date"][:7]  # YYYY-MM
                monthly.setdefault(ym, []).append(p["value"])

        composite_raw = []
        for ym in sorted(monthly.keys()):
            vals = monthly[ym]
            composite_raw.append({"date": ym, "value": round(sum(vals) / len(vals), 1)})

        # Apply smoothing
        values = [p["value"] for p in composite_raw]
        smoothed = rolling_average(values, window=3)  # 3-month rolling for monthly data

        # Rebase to Jan 2023 = 100
        jan_2023_val = None
        for i, p in enumerate(composite_raw):
            if p["date"] == "2023-01":
                jan_2023_val = smoothed[i]
                break

        if jan_2023_val and jan_2023_val > 0:
            scale = 100.0 / jan_2023_val
            smoothed = [round(v * scale, 1) for v in smoothed]

        composite = [{"date": composite_raw[i]["date"], "value": smoothed[i]}
                     for i in range(len(composite_raw))]

        categories_out[cat_name] = {
            "terms": CATEGORIES[cat_name],
            "composite": composite,
        }

    return {
        "metadata": {
            "source": "Google Trends",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
            "baseline": "2023-01 = 100",
        },
        "categories": categories_out,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to central mock generator."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_data import generate_trends_data
    return generate_trends_data()


# ---------------------------------------------------------------------------
# I/O
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
    parser = argparse.ArgumentParser(description="Google Trends Data Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling pytrends")
    args = parser.parse_args()

    print("Google Trends Collector")
    print(f"  Mode: {'MOCK' if args.mock else 'LIVE (pytrends)'}\n")

    if args.mock:
        processed = generate_mock()
    else:
        raw = fetch_trends_data()
        raw_path = os.path.join(RAW_DIR, f"trends_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw, raw_path)
        processed = process_trends_raw(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "search_interest.json"))
    print("\nGoogle Trends collection complete.")


if __name__ == "__main__":
    main()
