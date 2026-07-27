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
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "earnings", "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "earnings", "processed")

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


def _period_months(start, end):
    """Inclusive length of an XBRL period in months, or None if undatable.

    XBRL start/end are ISO dates. A discrete quarter spans 3, a half 6, a
    three-quarter YTD 9, a fiscal year 12. Day-level jitter (52/53-week
    retail calendars) is absorbed by rounding on month boundaries.
    """
    if not start or not end:
        return None
    try:
        sy, sm, _ = (int(p) for p in start.split("-"))
        ey, em, _ = (int(p) for p in end.split("-"))
    except (ValueError, AttributeError):
        return None
    return (ey - sy) * 12 + (em - sm) + 1


def _calendar_quarter(end):
    """Map a period END date to the calendar quarter it falls in.

    Fiscal labels are NOT usable for time alignment: Booz Allen's fiscal year
    ends 03-31, so its fiscal Q4 (Jan-Mar) carries fp=FY/fy=2025 and the old
    code labelled it 2025-Q4 — which the composite then expanded to Oct-Dec,
    placing the data nine months late. Accenture (Aug year-end) skews the
    other way. Deriving from the end date puts every filer on one axis.
    """
    try:
        ey, em, _ = (int(p) for p in end.split("-"))
    except (ValueError, AttributeError):
        return None
    return f"{ey}-Q{(em - 1) // 3 + 1}"


def _parse_xbrl_revenue_entries(usd_entries):
    """
    Parse USD-denominated XBRL entries into DISCRETE quarterly revenue.

    Two defects this guards against, both found in the 2026-07 audit:

    1. Annual totals booked as Q4. A 10-K carries fp=FY holding the full-year
       figure; the old code mapped it straight to Q4. Booz Allen FY2025 then
       published a Q4 of $11,980M against ~$2,900M quarters — a 3.99x spike
       every fourth quarter that produced two of the index's three phase
       transitions. Real Q4 = FY - (Q1+Q2+Q3) = $2,974.6M.

    2. YTD entries silently substituted for discrete quarters. companyfacts
       returns BOTH cumulative and discrete rows under the same fp label
       (BAH fp=Q3 appears as 2024-04-01..2024-12-31 = $9,005.4M YTD *and*
       2024-10-01..2024-12-31 = $2,917.2M discrete). The old dedup kept
       whichever happened to appear last, so the series mixed the two.

    Only 3-month periods are accepted as quarters. 12-month periods are held
    aside and used solely to derive the one quarter a 10-K does not report
    discretely. Quarters are keyed to the CALENDAR quarter of the period end.

    Returns list of {quarter, value_mm} dicts, or empty list.
    """
    discrete = {}   # calendar quarter -> (value, filed) for 3-month periods
    annual = []     # 12-month periods, for Q4 derivation

    for entry in usd_entries:
        val = entry.get("val")
        start, end = entry.get("start"), entry.get("end")
        if val is None or not end:
            continue

        months = _period_months(start, end)
        if months is None:
            continue
        filed = entry.get("filed") or ""

        if months == 3:
            quarter = _calendar_quarter(end)
            if not quarter:
                continue
            # Restatements: prefer the most recently filed figure.
            prior = discrete.get(quarter)
            if prior is None or filed >= prior[1]:
                discrete[quarter] = (val, filed)
        elif months == 12:
            annual.append((start, end, val, filed))

    # Derive the unreported quarter of each fiscal year: FY total minus the
    # three discrete quarters that fall inside the same 12-month window.
    for start, end, total, filed in annual:
        target = _calendar_quarter(end)
        if not target or target in discrete:
            continue
        covered = [
            (q, v) for q, (v, _) in discrete.items()
            if start <= _quarter_end_date(q) <= end
        ]
        if len(covered) != 3:
            # Can't decompose safely — drop rather than publish an annual
            # figure in a quarterly slot.
            continue
        derived = total - sum(v for _, v in covered)
        if derived <= 0:
            continue
        discrete[target] = (derived, filed)

    quarterly = [
        {"quarter": q, "value_mm": round(v / 1_000_000, 1)}
        for q, (v, _) in sorted(discrete.items())
    ]
    return quarterly


_QUARTER_END_MMDD = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}


def _quarter_end_date(quarter):
    """Last day of a calendar quarter label, as an ISO date string."""
    year, qn = quarter.split("-Q")
    return f"{year}-{_QUARTER_END_MMDD[int(qn)]}"


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


# Unit keys that EDGAR uses for employee counts. See sec_workforce.py for
# the rationale — we explicitly avoid falling through to arbitrary unit keys
# because that would let currency-denominated values bleed into headcount.
HEADCOUNT_UNIT_KEYS = ("pure", "employee", "employees", "shares", "Person", "items", "number")


def _collect_headcount_entries(tag_data):
    """Return the entries list for a headcount XBRL tag, trying known unit keys."""
    if not tag_data:
        return []
    units = tag_data.get("units", {})
    for key in HEADCOUNT_UNIT_KEYS:
        if units.get(key):
            return units[key]
    for unit_entries in units.values():
        if not unit_entries:
            continue
        sample = unit_entries[0].get("val")
        if isinstance(sample, (int, float)) and 100 <= sample <= 10_000_000:
            return unit_entries
    return []


def _extract_headcount(facts):
    """
    Extract quarterly headcount data from XBRL facts.

    Tries BOTH dei:EntityNumberOfEmployees and ifrs-full:NumberOfEmployees
    (foreign filers often only populate the IFRS tag) and merges results.

    Returns dict mapping 'YYYY-QN' to headcount value.
    """
    all_facts = facts.get("facts", {})

    entries = []
    entries.extend(_collect_headcount_entries(all_facts.get("dei", {}).get(HEADCOUNT_TAG)))
    entries.extend(
        _collect_headcount_entries(all_facts.get("ifrs-full", {}).get(HEADCOUNT_TAG_IFRS))
    )

    headcount_map = {}
    for entry in entries:
        fy = entry.get("fy")
        fp = entry.get("fp")
        val = entry.get("val")
        if fy is None or val is None:
            continue

        try:
            val_int = int(val)
        except (TypeError, ValueError):
            continue
        if not 100 <= val_int <= 10_000_000:
            continue

        if fp == "FY":
            key = f"{fy}-Q4"
        elif fp in ("Q1", "Q2", "Q3", "Q4"):
            key = f"{fy}-{fp}"
        else:
            continue

        headcount_map[key] = val_int

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
            f"earnings_raw_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        )
        save_json(raw, raw_path)
        processed = process_earnings_data(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "revenue.json"))
    print("\nEarnings collection complete.")


if __name__ == "__main__":
    main()
