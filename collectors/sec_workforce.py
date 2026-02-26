#!/usr/bin/env python3
"""
SEC Workforce Disclosure Collector for the Displacement Curve.

Fetches headcount data from SEC EDGAR Company Facts XBRL API
(EntityNumberOfEmployees tag) for 11 IT services / staffing firms.

Targets (11 firms):
  IT Services: ACN, CTSH, INFY, WIT, EPAM, GLOB, IT, BAH
  Staffing:    KFRC, RHI, MAN

Usage:
  python collectors/sec_workforce.py              # live (SEC EDGAR)
  python collectors/sec_workforce.py --mock       # generate mock data
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
RAW_DIR = os.path.join(BASE_DIR, "data", "sec", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "sec", "processed")

TICKERS_IT = ["ACN", "CTSH", "INFY", "WIT", "EPAM", "GLOB", "IT", "BAH"]
TICKERS_STAFFING = ["KFRC", "RHI", "MAN"]
ALL_TICKERS = TICKERS_IT + TICKERS_STAFFING

CIK_MAP = {
    "ACN": "0001467373",   # Accenture plc
    "CTSH": "0001058290",  # Cognizant Technology Solutions
    "INFY": "0001067491",  # Infosys Ltd
    "WIT": "0001123799",   # Wipro Ltd
    "EPAM": "0001352010",  # EPAM Systems
    "GLOB": "0001557860",  # Globant S.A.
    "IT": "0000749251",    # Gartner Inc
    "BAH": "0001443646",   # Booz Allen Hamilton
    "KFRC": "0000930420",  # Kforce Inc
    "RHI": "0000315213",   # Robert Half Inc.
    "MAN": "0000871763",   # ManpowerGroup Inc.
}

FIRM_NAMES = {
    "ACN": "Accenture",
    "CTSH": "Cognizant",
    "INFY": "Infosys",
    "WIT": "Wipro",
    "EPAM": "EPAM Systems",
    "GLOB": "Globant",
    "IT": "Gartner",
    "BAH": "Booz Allen Hamilton",
    "KFRC": "Kforce",
    "RHI": "Robert Half",
    "MAN": "ManpowerGroup",
}

EDGAR_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

USER_AGENT = "DisplacementCurve/1.0 (secedgar@1to3.co)"

HEADCOUNT_TAG = "EntityNumberOfEmployees"
HEADCOUNT_TAG_IFRS = "NumberOfEmployees"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
SEC_RATE_LIMIT_SLEEP = 0.15  # seconds between SEC requests


# ---------------------------------------------------------------------------
# Live Mode (SEC EDGAR Company Facts API)
# ---------------------------------------------------------------------------

def fetch_workforce_from_edgar(tickers):
    """
    Fetch Company Facts XBRL data from SEC EDGAR for each ticker.

    Returns dict keyed by ticker containing the full companyfacts JSON.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    raw_data = {}

    for ticker in tickers:
        cik = CIK_MAP.get(ticker)
        if not cik:
            print(f"  WARNING: No CIK mapping for {ticker}, skipping")
            continue

        url = EDGAR_COMPANY_FACTS_URL.format(cik=cik)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"  Fetching EDGAR Company Facts for {ticker} (CIK {cik}, attempt {attempt}/{MAX_RETRIES})...")
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                raw_data[ticker] = data
                print(f"  OK: {ticker} - received {len(json.dumps(data))} bytes")
                break
            except requests.RequestException as exc:
                print(f"  Request failed for {ticker}: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    print(f"  WARNING: Skipping {ticker} after {MAX_RETRIES} failures")

        time.sleep(SEC_RATE_LIMIT_SLEEP)

    return raw_data


def _extract_annual_headcount(facts):
    """
    Extract annual headcount from XBRL tags.

    Checks dei:EntityNumberOfEmployees first, then
    ifrs-full:NumberOfEmployees for foreign filers.
    Filters to annual filings (fp = 'FY').

    Returns list of {year, total_headcount} dicts.
    """
    all_facts = facts.get("facts", {})
    entries = []

    # Try dei:EntityNumberOfEmployees first
    dei = all_facts.get("dei", {})
    tag_data = dei.get(HEADCOUNT_TAG)
    if tag_data:
        units = tag_data.get("units", {})
        entries = units.get("pure", []) or units.get("employee", [])
        if not entries:
            for unit_key, unit_entries in units.items():
                if unit_entries:
                    entries = unit_entries
                    break

    # Fall back to ifrs-full:NumberOfEmployees
    if not entries:
        ifrs = all_facts.get("ifrs-full", {})
        tag_data = ifrs.get(HEADCOUNT_TAG_IFRS)
        if tag_data:
            units = tag_data.get("units", {})
            entries = units.get("pure", []) or units.get("number", [])
            if not entries:
                for unit_key, unit_entries in units.items():
                    if unit_entries:
                        entries = unit_entries
                        break

    # Filter to annual (FY) filings, deduplicate by year (keep latest)
    yearly = {}
    for entry in entries:
        fy = entry.get("fy")
        fp = entry.get("fp")
        val = entry.get("val")
        filed = entry.get("filed", "")

        if fy is None or val is None:
            continue

        # Only annual filings
        if fp != "FY":
            continue

        # Filter out obviously wrong values
        if int(val) < 100:
            continue

        year = int(fy)
        # Keep the most recently filed value for each fiscal year
        if year not in yearly or filed > yearly[year]["filed"]:
            yearly[year] = {"year": year, "total_headcount": int(val), "filed": filed}

    # Convert to sorted list, drop the filed date
    result = []
    for year in sorted(yearly.keys()):
        result.append({
            "year": yearly[year]["year"],
            "total_headcount": yearly[year]["total_headcount"],
            "contractor_pct": None,  # Not available in XBRL
        })

    return result


def process_workforce_data(raw_data):
    """
    Process raw EDGAR Company Facts data into the standard workforce schema.
    """
    firms = {}

    for ticker in ALL_TICKERS:
        facts = raw_data.get(ticker)
        if not facts:
            print(f"  No data for {ticker}, skipping")
            continue

        annual = _extract_annual_headcount(facts)
        firms[ticker] = {
            "name": FIRM_NAMES.get(ticker, ticker),
            "ticker": ticker,
            "annual": annual,
        }

    # Build aggregate data by year
    year_totals = {}
    for ticker, firm_data in firms.items():
        for entry in firm_data["annual"]:
            year = entry["year"]
            if year not in year_totals:
                year_totals[year] = 0
            year_totals[year] += entry["total_headcount"]

    aggregate = []
    for year in sorted(year_totals.keys()):
        aggregate.append({
            "year": year,
            "total_headcount": year_totals[year],
            "avg_contractor_pct": None,  # Not available in XBRL
        })

    return {
        "metadata": {
            "source": "SEC EDGAR XBRL",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "firms": firms,
        "aggregate": aggregate,
    }


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
    print(f"  Mode:    {'MOCK' if args.mock else 'LIVE (EDGAR)'}\n")

    if args.mock:
        processed = generate_mock()
    else:
        raw = fetch_workforce_from_edgar(ALL_TICKERS)
        # Save raw response
        raw_path = os.path.join(
            RAW_DIR,
            f"workforce_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        )
        save_json(raw, raw_path)
        processed = process_workforce_data(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "workforce.json"))
    print("\nSEC workforce collection complete.")


if __name__ == "__main__":
    main()
