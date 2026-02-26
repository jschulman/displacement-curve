#!/usr/bin/env python3
"""
Earnings Transcript Collector for the Displacement Curve.

Collects quarterly revenue, AI revenue, and headcount data from
SEC EDGAR earnings transcripts for 8 IT services / consulting firms.

Targets:
  ACN  - Accenture
  CTSH - Cognizant
  INFY - Infosys
  WIT  - Wipro
  EPAM - EPAM Systems
  GLOB - Globant
  IT   - Gartner
  BAH  - Booz Allen Hamilton

Usage:
  python collectors/earnings_transcripts.py             # live (stub)
  python collectors/earnings_transcripts.py --mock      # generate mock data
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
RAW_DIR = os.path.join(BASE_DIR, "data", "earnings", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "earnings", "processed")

TICKERS = ["ACN", "CTSH", "INFY", "WIT", "EPAM", "GLOB", "IT", "BAH"]

EDGAR_BASE_URL = "https://efts.sec.gov/LATEST/search-index?q="


# ---------------------------------------------------------------------------
# Live Mode (Stub)
# ---------------------------------------------------------------------------

def fetch_earnings_from_edgar(tickers):
    """
    Stub for live EDGAR earnings transcript fetching.

    In production this would:
    1. Query EDGAR XBRL API for 10-Q/10-K filings by CIK
    2. Parse revenue line items from XBRL tags:
       - us-gaap:Revenues / us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax
    3. Extract AI-specific revenue from earnings call transcripts
       (regex for 'AI revenue', 'generative AI', 'artificial intelligence' segments)
    4. Pull headcount from Item 1 / HR disclosures
    """
    raise NotImplementedError(
        "Live EDGAR fetching not yet implemented. Use --mock for development."
    )


def process_edgar_response(raw_data):
    """
    Stub for processing raw EDGAR filing data into standard schema.

    Would transform XBRL/JSON-LD filings into:
    {firms: {TICKER: {name, quarterly: [{quarter, total_revenue_mm, ai_revenue_mm, headcount, revenue_per_employee}]}}}
    """
    raise NotImplementedError(
        "Live EDGAR processing not yet implemented. Use --mock for development."
    )


# ---------------------------------------------------------------------------
# Mock Mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to the Phase 2 mock generator."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase2 import generate_earnings_data
    return generate_earnings_data()


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
    parser = argparse.ArgumentParser(description="Earnings Transcript Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling EDGAR")
    args = parser.parse_args()

    print("Earnings Transcript Collector")
    print(f"  Tickers: {', '.join(TICKERS)}")
    print(f"  Mode:    {'MOCK' if args.mock else 'LIVE (EDGAR)'}\n")

    if args.mock:
        processed = generate_mock()
    else:
        try:
            raw = fetch_earnings_from_edgar(TICKERS)
            raw_path = os.path.join(
                RAW_DIR,
                f"earnings_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
            )
            save_json(raw, raw_path)
            processed = process_edgar_response(raw)
        except NotImplementedError as e:
            print(f"  ERROR: {e}")
            print("  Falling back to --mock mode.\n")
            processed = generate_mock()

    save_json(processed, os.path.join(PROCESSED_DIR, "revenue.json"))
    print("\nEarnings collection complete.")


if __name__ == "__main__":
    main()
