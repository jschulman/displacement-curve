#!/usr/bin/env python3
"""
SEC Workforce Disclosure Collector for the Displacement Curve.

Parses 10-K Item 1 / Human Capital disclosures from SEC EDGAR for
headcount and contractor percentage data.

Targets (11 firms):
  IT Services: ACN, CTSH, INFY, WIT, EPAM, GLOB, IT, BAH
  Staffing:    KFRC, RHI, MAN

Usage:
  python collectors/sec_workforce.py              # live (stub)
  python collectors/sec_workforce.py --mock       # generate mock data
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
RAW_DIR = os.path.join(BASE_DIR, "data", "sec", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "sec", "processed")

TICKERS_IT = ["ACN", "CTSH", "INFY", "WIT", "EPAM", "GLOB", "IT", "BAH"]
TICKERS_STAFFING = ["KFRC", "RHI", "MAN"]
ALL_TICKERS = TICKERS_IT + TICKERS_STAFFING

# CIK mappings for EDGAR (would be used in live mode)
CIK_MAP = {
    "ACN": "0001281761",
    "CTSH": "0001058290",
    "INFY": "0001067491",
    "WIT": "0001357450",
    "EPAM": "0001352010",
    "GLOB": "0001557860",
    "IT": "0000749251",
    "BAH": "0001443646",
    "KFRC": "0000930420",
    "RHI": "0000315213",
    "MAN": "0000871763",
}

EDGAR_FILING_URL = "https://efts.sec.gov/LATEST/search-index"


# ---------------------------------------------------------------------------
# Live Mode (Stub)
# ---------------------------------------------------------------------------

def fetch_workforce_from_edgar(tickers):
    """
    Stub for live EDGAR 10-K parsing.

    In production this would:
    1. Query EDGAR full-text search for each CIK's latest 10-K
    2. Locate Item 1 - "Human Capital Resources" section
    3. Extract:
       - Total employee count (regex for headcount / employees / workforce)
       - Contractor/contingent worker percentage (regex for contractor,
         contingent, temporary, supplemental workforce)
    4. Fall back to proxy statement (DEF 14A) if 10-K lacks headcount
    """
    raise NotImplementedError(
        "Live EDGAR 10-K parsing not yet implemented. Use --mock for development."
    )


def process_edgar_workforce(raw_data):
    """
    Stub for processing raw EDGAR filings into workforce schema.

    Would produce:
    {firms: {TICKER: {name, ticker, annual: [{year, total_headcount, contractor_pct}]}}}
    """
    raise NotImplementedError(
        "Live EDGAR workforce processing not yet implemented. Use --mock for development."
    )


# ---------------------------------------------------------------------------
# Mock Mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to the Phase 2 mock generator."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase2 import generate_workforce_data
    return generate_workforce_data()


# ---------------------------------------------------------------------------
# I/O Helpers
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
    parser = argparse.ArgumentParser(description="SEC Workforce Disclosure Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of parsing EDGAR")
    args = parser.parse_args()

    print("SEC Workforce Disclosure Collector")
    print(f"  Tickers: {', '.join(ALL_TICKERS)}")
    print(f"  Mode:    {'MOCK' if args.mock else 'LIVE (EDGAR 10-K)'}\n")

    if args.mock:
        processed = generate_mock()
    else:
        try:
            raw = fetch_workforce_from_edgar(ALL_TICKERS)
            raw_path = os.path.join(
                RAW_DIR,
                f"workforce_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            )
            save_json(raw, raw_path)
            processed = process_edgar_workforce(raw)
        except NotImplementedError as e:
            print(f"  ERROR: {e}")
            print("  Falling back to --mock mode.\n")
            processed = generate_mock()

    save_json(processed, os.path.join(PROCESSED_DIR, "workforce.json"))
    print("\nSEC workforce collection complete.")


if __name__ == "__main__":
    main()
