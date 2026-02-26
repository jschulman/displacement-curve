#!/usr/bin/env python3
"""
VC Funding Collector for the Displacement Curve.

Fetches AI-startup funding data from SEC EDGAR Form D filings, filtered by
relevant SIC/NAICS codes for AI-native professional services startups.

Categories tracked:
  ai_audit       - AI-Native Audit/Accounting
  ai_legal       - AI Legal Services
  ai_consulting  - AI Consulting/Strategy
  ai_compliance  - AI Compliance/Regulatory
  ai_staffing    - AI-Native Staffing
  horizontal_ai  - Horizontal AI Agents

Usage:
  python collectors/vc_funding.py              # live API (SEC EDGAR)
  python collectors/vc_funding.py --mock       # generate mock data
  python collectors/vc_funding.py --start-year 2022 --end-year 2025
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
RAW_DIR = os.path.join(BASE_DIR, "data", "vc", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "vc", "processed")

EDGAR_FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FORM_D_SEARCH = "https://efts.sec.gov/LATEST/search-index"

# SIC codes relevant to AI professional services startups
RELEVANT_SIC = [
    "7372",  # Prepackaged Software
    "7371",  # Computer Programming, Data Processing
    "7374",  # Computer Processing and Data Preparation
    "7389",  # Services-Misc Business Services
    "8721",  # Accounting, Auditing & Bookkeeping
    "8111",  # Legal Services
    "8742",  # Management Consulting Services
]

# Keywords for filtering Form D filings to AI-relevant companies
AI_KEYWORDS = [
    "artificial intelligence", "machine learning", "AI-powered",
    "AI-native", "generative AI", "large language model", "LLM",
    "automated audit", "AI compliance", "AI legal", "AI staffing",
]

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

USER_AGENT = "DisplacementCurve/1.0 (secedgar@1to3.co)"


# ---------------------------------------------------------------------------
# SEC EDGAR API Fetch (Live Mode)
# ---------------------------------------------------------------------------

def fetch_edgar_form_d(start_year, end_year):
    """
    Fetch Form D filings from SEC EDGAR EFTS full-text search.

    In production, this queries the EDGAR full-text search for Form D filings
    with AI-related keywords, then aggregates funding amounts by quarter and
    category. For now, the live endpoint is structured but would need
    EDGAR API access and parsing logic for real deployment.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    all_filings = []

    for keyword in AI_KEYWORDS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                params = {
                    "q": f'"{keyword}"',
                    "dateRange": "custom",
                    "startdt": f"{start_year}-01-01",
                    "enddt": f"{end_year}-12-31",
                    "forms": "D",
                }
                print(f"  EDGAR search: '{keyword}' (attempt {attempt}/{MAX_RETRIES})...")
                resp = requests.get(
                    "https://efts.sec.gov/LATEST/search-index",
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                hits = data.get("hits", {}).get("hits", [])
                all_filings.extend(hits)
                print(f"    Found {len(hits)} filings for '{keyword}'")
                break

            except requests.RequestException as exc:
                print(f"  Request failed: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    print(f"  WARNING: Skipping keyword '{keyword}' after {MAX_RETRIES} failures")

        # Rate-limit: SEC asks for <= 10 requests/sec
        time.sleep(0.2)

    return all_filings


def classify_filing(filing):
    """Classify a Form D filing into one of our 6 categories based on SIC + text."""
    text = json.dumps(filing).lower()

    if any(term in text for term in ["audit", "accounting", "bookkeep"]):
        return "ai_audit"
    elif any(term in text for term in ["legal", "law", "attorney"]):
        return "ai_legal"
    elif any(term in text for term in ["consulting", "strategy", "advisory"]):
        return "ai_consulting"
    elif any(term in text for term in ["compliance", "regulatory", "regtech"]):
        return "ai_compliance"
    elif any(term in text for term in ["staffing", "recruiting", "talent", "hiring"]):
        return "ai_staffing"
    else:
        return "horizontal_ai"


def process_edgar_filings(filings, start_year, end_year):
    """Transform raw EDGAR filings into our standard VC funding schema."""
    # Build quarter buckets
    quarters = []
    for year in range(start_year, end_year + 1):
        sq = 4 if year == start_year and start_year == 2022 else 1
        for q in range(sq, 5):
            quarters.append(f"{year}-Q{q}")

    cat_keys = ["ai_audit", "ai_legal", "ai_consulting", "ai_compliance", "ai_staffing", "horizontal_ai"]
    cat_names = {
        "ai_audit": "AI-Native Audit/Accounting",
        "ai_legal": "AI Legal Services",
        "ai_consulting": "AI Consulting/Strategy",
        "ai_compliance": "AI Compliance/Regulatory",
        "ai_staffing": "AI-Native Staffing",
        "horizontal_ai": "Horizontal AI Agents",
    }

    # Initialize buckets
    buckets = {cat: {q: {"funding_mm": 0.0, "deal_count": 0} for q in quarters} for cat in cat_keys}

    for filing in filings:
        cat = classify_filing(filing)
        # Extract date and amount from filing (simplified)
        source = filing.get("_source", {})
        filed_date = source.get("file_date", "")
        if not filed_date:
            continue
        try:
            dt = datetime.strptime(filed_date[:10], "%Y-%m-%d")
        except ValueError:
            continue
        q_num = (dt.month - 1) // 3 + 1
        q_label = f"{dt.year}-Q{q_num}"
        if q_label not in buckets[cat]:
            continue

        # Attempt to extract offering amount (Form D specific)
        amount_mm = source.get("offeringAmount", 0) / 1_000_000 if source.get("offeringAmount") else 1.0

        buckets[cat][q_label]["funding_mm"] = round(buckets[cat][q_label]["funding_mm"] + amount_mm, 1)
        buckets[cat][q_label]["deal_count"] += 1

    # Build output
    categories = {}
    for cat in cat_keys:
        quarterly = []
        for q in quarters:
            quarterly.append({
                "quarter": q,
                "funding_mm": buckets[cat][q]["funding_mm"],
                "deal_count": buckets[cat][q]["deal_count"],
            })
        categories[cat] = {"name": cat_names[cat], "quarterly": quarterly}

    # Aggregate
    aggregate = []
    cumulative = 0.0
    for q in quarters:
        total_funding = round(sum(buckets[cat][q]["funding_mm"] for cat in cat_keys), 1)
        total_deals = sum(buckets[cat][q]["deal_count"] for cat in cat_keys)
        cumulative = round(cumulative + total_funding, 1)
        aggregate.append({
            "quarter": q,
            "total_funding_mm": total_funding,
            "total_deals": total_deals,
            "cumulative_mm": cumulative,
        })

    return {
        "metadata": {
            "source": "SEC EDGAR Form D",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "categories": categories,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock(start_year, end_year):
    """Delegate to the central Phase 3 mock generator and return VC data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase3 import generate_vc_funding
    data = generate_vc_funding()
    # Filter to requested year range
    for cat_key in data["categories"]:
        data["categories"][cat_key]["quarterly"] = [
            q for q in data["categories"][cat_key]["quarterly"]
            if start_year <= int(q["quarter"][:4]) <= end_year
        ]
    data["aggregate"] = [
        q for q in data["aggregate"]
        if start_year <= int(q["quarter"][:4]) <= end_year
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
    parser = argparse.ArgumentParser(description="VC Funding Collector (SEC EDGAR Form D)")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling API")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")
    args = parser.parse_args()

    print("VC Funding Collector")
    print(f"  Range: {args.start_year}-{args.end_year}")
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE (SEC EDGAR)'}\n")

    if args.mock:
        processed = generate_mock(args.start_year, args.end_year)
    else:
        raw_filings = fetch_edgar_form_d(args.start_year, args.end_year)
        # Save raw response
        raw_path = os.path.join(RAW_DIR, f"edgar_formd_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw_filings, raw_path)
        processed = process_edgar_filings(raw_filings, args.start_year, args.end_year)

    save_json(processed, os.path.join(PROCESSED_DIR, "funding.json"))
    print("\nVC funding collection complete.")


if __name__ == "__main__":
    main()
