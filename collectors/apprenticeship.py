#!/usr/bin/env python3
"""
Apprenticeship Collapse Collector for the Displacement Curve.

Unlike the other collectors, this signal is produced by a separate engine,
`displacement-signals` (TypeScript/Postgres), which scans professional-services
firms' public job postings, classifies seniority, and computes a treatment-cohort
median junior:senior ratio. This collector is just the TRANSPORT step: it copies
that engine's exported feed into data/apprenticeship/processed/collapse.json so the
composite can read it like any other signal.

Source resolution order:
  1. --source <path>             explicit local path to collapse.json
  2. APPRENTICESHIP_FEED env     local path
  3. APPRENTICESHIP_FEED_URL env https URL to fetch

See METHODOLOGY.md "Signal 7: The Apprenticeship Collapse".

Usage:
  python collectors/apprenticeship.py --source /opt/displacement-signals/output/apprenticeship/collapse.json
  python collectors/apprenticeship.py --mock
"""

import argparse
import json
import os
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
OUT_PATH = os.path.join(DATA_DIR, "apprenticeship", "processed", "collapse.json")


def load_from_source(args):
    src = args.source or os.environ.get("APPRENTICESHIP_FEED")
    if src and os.path.exists(src):
        with open(src, "r") as f:
            return json.load(f)
    url = os.environ.get("APPRENTICESHIP_FEED_URL")
    if url:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    return None


def mock():
    # A short synthetic decline so the composite can be exercised end-to-end.
    return {
        "metadata": {"source": "mock", "signal": "apprenticeship_collapse", "invert": True, "mock": True},
        "monthly": [
            {"date": "2026-03", "value": 0.42},
            {"date": "2026-04", "value": 0.31},
            {"date": "2026-05", "value": 0.22},
            {"date": "2026-06", "value": 0.16},
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", help="path to displacement-signals collapse.json")
    p.add_argument("--mock", action="store_true")
    args = p.parse_args()

    data = mock() if args.mock else load_from_source(args)
    if not data:
        print("  ERROR: no apprenticeship feed found (set --source / APPRENTICESHIP_FEED[_URL])")
        sys.exit(1)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    n = len(data.get("monthly", []))
    print(f"  apprenticeship: wrote {n} monthly point(s) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
