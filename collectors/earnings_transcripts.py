#!/usr/bin/env python3
"""
Earnings Transcript Collector for the Displacement Curve.

Collects quarterly revenue, AI revenue, and headcount data from
SEC EDGAR Company Facts XBRL API for 8 IT services / consulting firms.

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
  python collectors/earnings_transcripts.py             # live (SEC EDGAR)
  python collectors/earnings_transcripts.py --mock      # generate mock data
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
RAW_DIR = os.path.join(BASE_DIR, "data", "earnings", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "earnings", "processed")

TICKERS = ["ACN", "CTSH", "INFY", "WIT", "EPAM", "GLOB", "IT", "BAH"]

CIK_MAP = {
    "ACN": "0001467373",   # Accenture plc
    "CTSH": "0001058290",  # Cognizant Technology Solutions
    "INFY": "0001067491",  # Infosys Ltd
    "WIT": "0001123799",   # Wipro Ltd
    "EPAM": "0001352010",  # EPAM Systems
    "GLOB": "0001557860",  # Globant S.A.
    "IT": "0000749251",    # Gartner Inc
    "BAH": "0001443646",   # Booz Allen Hamilton
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
}

EDGAR_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

USER_AGENT = "DisplacementCurve/1.0 (secedgar@1to3.co)"

# XBRL revenue tags in preference order (us-gaap namespace)
REVENUE_TAGS_USGAAP = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueServicesNet",
]

# IFRS revenue tags for foreign filers (ifrs-full namespace)
REVENUE_TAGS_IFRS = [
    "Revenue",
    "RevenueFromContractsWithCustomers",
    "RevenueFromRenderingOfServices",
]

HEADCOUNT_TAG = "EntityNumberOfEmployees"
HEADCOUNT_TAG_IFRS = "NumberOfEmployees"

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
SEC_RATE_LIMIT_SLEEP = 0.15  # seconds between SEC requests


# ---------------------------------------------------------------------------
# Live Mode (SEC EDGAR Company Facts API)
# ---------------------------------------------------------------------------

def fetch_earnings_from_edgar(tickers):
    """
    Fetch Company Facts XBRL data from SEC EDGAR for each ticker.

    Returns a dict keyed by ticker, each containing the full companyfacts
    JSON response from EDGAR.
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


def _parse_xbrl_revenue_entries(usd_entries):
    """
    Parse USD-denominated XBRL entries into quarterly revenue data.

    Returns list of {quarter, value_mm} dicts, or empty list.
    """
    quarterly = []
    seen = set()
    for entry in usd_entries:
        fy = entry.get("fy")
        fp = entry.get("fp")
        val = entry.get("val")

        if fy is None or fp is None or val is None:
            continue

        # We want quarterly periods: Q1, Q2, Q3, Q4
        # fp values: Q1, Q2, Q3, FY (for annual)
        # For 10-K filings with fp=FY, that's the annual total - map to Q4
        if fp not in ("Q1", "Q2", "Q3", "Q4", "FY"):
            continue

        if fp == "FY":
            quarter_label = f"{fy}-Q4"
        else:
            quarter_label = f"{fy}-{fp}"

        # Deduplicate - keep latest filing for each quarter
        if quarter_label in seen:
            for q in quarterly:
                if q["quarter"] == quarter_label:
                    q["value_mm"] = round(val / 1_000_000, 1)
                    break
            continue

        seen.add(quarter_label)
        quarterly.append({
            "quarter": quarter_label,
            "value_mm": round(val / 1_000_000, 1),
        })

    if quarterly:
        quarterly.sort(key=lambda x: x["quarter"])
    return quarterly


def _extract_revenue_quarterly(facts):
    """
    Extract quarterly revenue data from XBRL facts.

    Searches us-gaap and ifrs-full namespaces for revenue tags.
    Picks the tag with the most recent data to avoid stale tags.
    Returns list of {quarter, value_mm} dicts.
    """
    all_facts = facts.get("facts", {})

    # Collect all candidate results from both namespaces
    candidates = []

    # Try us-gaap namespace
    us_gaap = all_facts.get("us-gaap", {})
    for tag in REVENUE_TAGS_USGAAP:
        tag_data = us_gaap.get(tag)
        if not tag_data:
            continue
        usd_entries = tag_data.get("units", {}).get("USD", [])
        if not usd_entries:
            continue
        result = _parse_xbrl_revenue_entries(usd_entries)
        if result:
            candidates.append(result)

    # Try ifrs-full namespace (for foreign filers like INFY, WIT, GLOB)
    ifrs = all_facts.get("ifrs-full", {})
    for tag in REVENUE_TAGS_IFRS:
        tag_data = ifrs.get(tag)
        if not tag_data:
            continue
        usd_entries = tag_data.get("units", {}).get("USD", [])
        if not usd_entries:
            continue
        result = _parse_xbrl_revenue_entries(usd_entries)
        if result:
            candidates.append(result)

    if not candidates:
        return []

    # Pick the candidate with the most recent quarter label
    # This avoids using stale tags when a newer tag has superseded them
    best = max(candidates, key=lambda c: c[-1]["quarter"] if c else "")
    return best


def _extract_headcount(facts):
    """
    Extract headcount data from XBRL facts.

    Checks dei:EntityNumberOfEmployees first, then
    ifrs-full:NumberOfEmployees for foreign filers.

    Returns dict mapping 'YYYY-QN' to headcount value.
    """
    all_facts = facts.get("facts", {})
    entries = []

    # Try dei:EntityNumberOfEmployees first
    dei = all_facts.get("dei", {})
    tag_data = dei.get(HEADCOUNT_TAG)
    if tag_data:
        units = tag_data.get("units", {})
        entries = units.get("pure", []) or units.get("number", []) or units.get("employee", [])
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

    headcount_map = {}
    for entry in entries:
        fy = entry.get("fy")
        fp = entry.get("fp")
        val = entry.get("val")
        if fy is None or val is None:
            continue

        # Filter out obviously wrong values (e.g., old filings with tiny numbers)
        if int(val) < 100:
            continue

        if fp == "FY":
            key = f"{fy}-Q4"
        elif fp in ("Q1", "Q2", "Q3", "Q4"):
            key = f"{fy}-{fp}"
        else:
            continue

        headcount_map[key] = int(val)

    return headcount_map


def process_earnings_data(raw_data):
    """
    Process raw EDGAR Company Facts data into the standard earnings schema.
    """
    firms = {}

    for ticker in TICKERS:
        facts = raw_data.get(ticker)
        if not facts:
            print(f"  No data for {ticker}, skipping")
            continue

        revenue_quarters = _extract_revenue_quarterly(facts)
        headcount_map = _extract_headcount(facts)

        quarterly = []
        for rq in revenue_quarters:
            quarter = rq["quarter"]
            total_rev = rq["value_mm"]
            hc = headcount_map.get(quarter)

            # revenue_per_employee in thousands: (total_revenue_mm * 1e6) / headcount / 1000
            rev_per_emp = None
            if hc and hc > 0 and total_rev:
                rev_per_emp = round((total_rev * 1_000_000) / hc / 1000, 1)

            quarterly.append({
                "quarter": quarter,
                "total_revenue_mm": total_rev,
                "ai_revenue_mm": None,
                "headcount": hc,
                "revenue_per_employee": rev_per_emp,
            })

        firms[ticker] = {
            "name": FIRM_NAMES.get(ticker, ticker),
            "quarterly": quarterly,
        }

    # Build aggregate data
    quarter_agg = {}
    for ticker, firm_data in firms.items():
        for q in firm_data["quarterly"]:
            quarter = q["quarter"]
            if quarter not in quarter_agg:
                quarter_agg[quarter] = {
                    "rev_per_emp_values": [],
                    "count": 0,
                }
            if q["revenue_per_employee"] is not None:
                quarter_agg[quarter]["rev_per_emp_values"].append(q["revenue_per_employee"])
            quarter_agg[quarter]["count"] += 1

    aggregate = []
    for quarter in sorted(quarter_agg.keys()):
        agg = quarter_agg[quarter]
        rev_per_emp_vals = agg["rev_per_emp_values"]
        avg_rpe = round(sum(rev_per_emp_vals) / len(rev_per_emp_vals), 1) if rev_per_emp_vals else None

        aggregate.append({
            "quarter": quarter,
            "total_ai_revenue_mm": None,
            "avg_ai_pct": None,
            "avg_relabeling_index": None,
            "avg_rev_per_employee": avg_rpe,
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
        raw = fetch_earnings_from_edgar(TICKERS)
        # Save raw response
        raw_path = os.path.join(
            RAW_DIR,
            f"earnings_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        )
        save_json(raw, raw_path)
        processed = process_earnings_data(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "revenue.json"))
    print("\nEarnings collection complete.")


if __name__ == "__main__":
    main()
