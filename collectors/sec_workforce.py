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
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "sec", "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "sec", "processed")

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


# Unit keys that EDGAR uses for employee counts. "pure" is by far the most
# common for dei:EntityNumberOfEmployees; older or foreign filings may use
# any of the others. We deliberately do NOT fall through to arbitrary unit
# keys (e.g. USD) since those carry currency amounts, not headcount.
HEADCOUNT_UNIT_KEYS = ("pure", "employee", "employees", "shares", "Person", "items", "number")


def _collect_headcount_entries(tag_data):
    """Return the entries list for a headcount XBRL tag, trying known unit keys."""
    if not tag_data:
        return []
    units = tag_data.get("units", {})
    for key in HEADCOUNT_UNIT_KEYS:
        if units.get(key):
            return units[key]
    # Last resort: pick the unit whose values look like employee counts
    # (integers in the 100..10_000_000 range). Skip anything that looks
    # like currency.
    for unit_entries in units.values():
        if not unit_entries:
            continue
        sample = unit_entries[0].get("val")
        if isinstance(sample, (int, float)) and 100 <= sample <= 10_000_000:
            return unit_entries
    return []


def _extract_annual_headcount(facts):
    """
    Extract annual headcount from XBRL company facts.

    Tries BOTH dei:EntityNumberOfEmployees and ifrs-full:NumberOfEmployees
    (foreign filers like Infosys/Wipro often only populate the IFRS tag) and
    merges the results, keeping the most recently filed value per fiscal year.

    Accepts fp=FY (US domestic 10-K) and fp=Q4 (sometimes used by foreign
    20-F/40-F filers for the year-end snapshot). Filters out implausible
    values: under 100 (likely stale or wrong) or over 10M (likely currency
    bleeding through from a mis-tagged unit).

    Returns list of {year, total_headcount, contractor_pct} dicts.
    """
    all_facts = facts.get("facts", {})

    entries = []
    entries.extend(_collect_headcount_entries(all_facts.get("dei", {}).get(HEADCOUNT_TAG)))
    entries.extend(
        _collect_headcount_entries(all_facts.get("ifrs-full", {}).get(HEADCOUNT_TAG_IFRS))
    )

    yearly = {}
    for entry in entries:
        fy = entry.get("fy")
        fp = entry.get("fp")
        val = entry.get("val")
        filed = entry.get("filed", "")

        if fy is None or val is None:
            continue
        if fp not in ("FY", "Q4"):
            continue

        try:
            val_int = int(val)
        except (TypeError, ValueError):
            continue
        if not 100 <= val_int <= 10_000_000:
            continue

        year = int(fy)
        existing = yearly.get(year)
        # FY takes precedence over Q4; otherwise keep the most recently filed.
        if existing is None:
            yearly[year] = {"year": year, "total_headcount": val_int, "filed": filed, "fp": fp}
        elif existing["fp"] != "FY" and fp == "FY":
            yearly[year] = {"year": year, "total_headcount": val_int, "filed": filed, "fp": fp}
        elif existing["fp"] == fp and filed > existing["filed"]:
            yearly[year] = {"year": year, "total_headcount": val_int, "filed": filed, "fp": fp}

    return [
        {"year": yearly[y]["year"], "total_headcount": yearly[y]["total_headcount"], "contractor_pct": None}
        for y in sorted(yearly.keys())
    ]


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
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
            f"workforce_raw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        )
        save_json(raw, raw_path)
        processed = process_workforce_data(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "workforce.json"))
    print("\nSEC workforce collection complete.")


if __name__ == "__main__":
    main()
