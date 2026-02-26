#!/usr/bin/env python3
"""
Composite Displacement Index for the Displacement Curve.

Reads all 8 processed signal files, normalizes each to 0-100 within its
historical range, applies weights, and produces a single 0-100 composite
displacement score per month.

Signals and weights:
  employment       0.25  (BLS headcount - INVERTED: decline = displacement)
  rev_per_employee 0.20  (Earnings revenue per employee)
  vc_funding       0.15  (AI startup VC funding)
  job_ratio        0.15  (AI / traditional job posting ratio)
  trends           0.10  (Google Trends search interest)
  github           0.10  (GitHub AI activity index)
  regulatory       0.05  (Regulatory document count)

Phase labels:
   0-25  Pre-disruption
  26-50  Productivity
  51-75  Erosion
  76-100 Displacement

Usage:
  python normalizers/composite_index.py              # compute from signal files
  python normalizers/composite_index.py --mock       # generate mock composite
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "composite", "displacement_index.json")

# Signal source files
SIGNAL_FILES = {
    "employment":      os.path.join(DATA_DIR, "bls", "processed", "employment.json"),
    "rev_per_employee": os.path.join(DATA_DIR, "earnings", "processed", "normalized.json"),
    "vc_funding":      os.path.join(DATA_DIR, "vc", "processed", "funding.json"),
    "job_ratio":       os.path.join(DATA_DIR, "jobs", "processed", "postings.json"),
    "trends":          os.path.join(DATA_DIR, "trends", "processed", "search_interest.json"),
    "github":          os.path.join(DATA_DIR, "github", "processed", "activity.json"),
    "regulatory":      os.path.join(DATA_DIR, "regulatory", "processed", "guidance.json"),
}

WEIGHTS = {
    "employment": 0.25,
    "rev_per_employee": 0.20,
    "vc_funding": 0.15,
    "job_ratio": 0.15,
    "trends": 0.10,
    "github": 0.10,
    "regulatory": 0.05,
}

EVENTS = [
    {"date": "2022-11", "label": "ChatGPT Launch", "type": "ai_release"},
    {"date": "2023-03", "label": "GPT-4 Release", "type": "ai_release"},
    {"date": "2023-07", "label": "Claude 2 Launch", "type": "ai_release"},
    {"date": "2024-03", "label": "Claude 3 Launch", "type": "ai_release"},
    {"date": "2024-06", "label": "EU AI Act Final", "type": "regulatory"},
    {"date": "2024-11", "label": "GPT-4o Launch", "type": "ai_release"},
    {"date": "2025-02", "label": "Claude 3.5 Opus", "type": "ai_release"},
    {"date": "2025-06", "label": "Accenture AI Revenue $3B", "type": "earnings"},
]

# 38 months: 2022-11 through 2025-12
MONTHS = []
for year in range(2022, 2026):
    start_m = 11 if year == 2022 else 1
    for m in range(start_m, 13):
        MONTHS.append(f"{year}-{m:02d}")


def get_phase(score):
    """Return phase label and range string for a given score."""
    if score <= 25:
        return "Pre-disruption", "0-25"
    elif score <= 50:
        return "Productivity", "26-50"
    elif score <= 75:
        return "Erosion", "51-75"
    else:
        return "Displacement", "76-100"


# ---------------------------------------------------------------------------
# Signal Extraction (Live Mode)
# ---------------------------------------------------------------------------

def load_json(path):
    """Load a JSON file, returning None if missing."""
    if not os.path.exists(path):
        print(f"  WARNING: Signal file not found: {path}")
        return None
    with open(path, "r") as f:
        return json.load(f)


def extract_monthly_employment(data):
    """Extract monthly headcount from BLS employment data."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("total_employment", entry.get("employment", 0))
    elif data and "series" in data:
        # Real BLS data: series.CES5000000001.data[].{date, value}
        for sid, series in data["series"].items():
            if sid == "CES5000000001":
                for entry in series.get("data", []):
                    values[entry["date"]] = entry["value"]
    elif data and "aggregate" in data:
        for entry in data["aggregate"]:
            values[entry.get("date", "")] = entry.get("total_employment", 0)
    return values


def extract_monthly_rev_per_employee(data):
    """Extract avg revenue per employee from earnings normalized data."""
    values = {}
    if data and "aggregate" in data:
        # Quarterly data - expand to months
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            rev_pe = entry.get("avg_rev_per_employee")
            if rev_pe is None:
                continue
            # Assign to each month in the quarter
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = rev_pe
    return values


def extract_monthly_vc_funding(data):
    """Extract quarterly VC funding, expand to monthly."""
    values = {}
    if data and "aggregate" in data:
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            funding = entry.get("total_funding_mm") or 0
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = funding / 3  # Spread quarterly over months
    return values


def extract_monthly_job_ratio(data):
    """Extract AI-to-traditional job ratio from postings data."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            val = entry.get("ai_to_traditional_ratio")
            if val is not None:
                values[entry["date"]] = val
    return values


def extract_monthly_trends(data):
    """Extract Google Trends search interest."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("interest", entry.get("value", 0))
    elif data and "aggregate" in data:
        for entry in data["aggregate"]:
            values[entry.get("date", "")] = entry.get("interest", 0)
    return values


def extract_monthly_github(data):
    """Extract GitHub activity index."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("activity_index", entry.get("stars", 0))
    return values


def extract_monthly_regulatory(data):
    """Extract cumulative regulatory document count, expand quarterly to monthly."""
    values = {}
    if data and "aggregate" in data:
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            cum_docs = entry.get("cumulative_documents", 0)
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = cum_docs
    return values


EXTRACTORS = {
    "employment": extract_monthly_employment,
    "rev_per_employee": extract_monthly_rev_per_employee,
    "vc_funding": extract_monthly_vc_funding,
    "job_ratio": extract_monthly_job_ratio,
    "trends": extract_monthly_trends,
    "github": extract_monthly_github,
    "regulatory": extract_monthly_regulatory,
}


def normalize_series(values, invert=False):
    """Normalize a dict of {date: value} to 0-100 based on min/max range."""
    if not values:
        return {}, 0, 0
    vals = list(values.values())
    lo = min(vals)
    hi = max(vals)
    span = hi - lo if hi != lo else 1

    normalized = {}
    for date, val in values.items():
        if invert:
            normalized[date] = round((hi - val) / span * 100, 1)
        else:
            normalized[date] = round((val - lo) / span * 100, 1)
    return normalized, lo, hi


def compute_composite_from_signals():
    """Load all signal files, normalize, weight, and produce composite index."""
    print("  Loading signal files...")

    # Load all signal data
    signal_data = {}
    for key, path in SIGNAL_FILES.items():
        signal_data[key] = load_json(path)

    # Extract monthly series for each signal
    raw_series = {}
    for key, extractor in EXTRACTORS.items():
        raw_series[key] = extractor(signal_data[key])
        print(f"    {key}: {len(raw_series[key])} monthly values")

    # Normalize each series to 0-100
    norm_series = {}
    for key in WEIGHTS:
        invert = (key == "employment")  # Lower headcount = higher displacement
        norm_series[key], lo, hi = normalize_series(raw_series.get(key, {}), invert=invert)
        print(f"    {key} range: {lo:.1f} - {hi:.1f} {'(inverted)' if invert else ''}")

    # Build monthly composite
    monthly = []
    prev_score = None

    for date_label in MONTHS:
        components = {}
        score = 0.0

        for key in WEIGHTS:
            raw_val = raw_series.get(key, {}).get(date_label, 0)
            norm_val = norm_series.get(key, {}).get(date_label, 0)
            weighted = round(norm_val * WEIGHTS[key], 2)

            components[key] = {
                "raw_value": raw_val,
                "normalized": norm_val,
                "weighted": weighted,
            }
            score += weighted

        score = round(score, 1)
        phase_label, phase_range = get_phase(score)

        if prev_score is None:
            trend = "flat"
        elif score > prev_score + 0.5:
            trend = "up"
        elif score < prev_score - 0.5:
            trend = "down"
        else:
            trend = "flat"

        prev_score = score

        monthly.append({
            "date": date_label,
            "score": score,
            "phase": phase_label,
            "phase_range": phase_range,
            "components": components,
            "trend": trend,
        })

    return {
        "metadata": {
            "source": "Displacement Curve Composite",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
            "version": "1.0",
        },
        "weights": WEIGHTS,
        "monthly": monthly,
        "events": EVENTS,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to the central Phase 4 mock generator for composite data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase4 import generate_composite
    return generate_composite()


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
    parser = argparse.ArgumentParser(description="Composite Displacement Index")
    parser.add_argument("--mock", action="store_true", help="Generate mock composite data directly")
    args = parser.parse_args()

    print("Composite Displacement Index")
    print(f"  Mode: {'MOCK' if args.mock else 'LIVE (from signal files)'}\n")

    if args.mock:
        data = generate_mock()
    else:
        data = compute_composite_from_signals()

    save_json(data, OUTPUT_PATH)

    # Print summary
    first = data["monthly"][0]
    last = data["monthly"][-1]
    print(f"\n  Score trajectory: {first['score']} ({first['phase']}) -> {last['score']} ({last['phase']})")
    print(f"  Months: {len(data['monthly'])}")
    print(f"  Events: {len(data['events'])}")
    print("\nComposite index generation complete.")


if __name__ == "__main__":
    main()
