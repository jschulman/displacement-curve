#!/usr/bin/env python3
"""
Job Postings Collector for the Displacement Curve.

Collects AI vs traditional job posting data from Indeed Hiring Lab and
LinkedIn Workforce Reports for 8 IT services / consulting firms.

Firms tracked:
  ACN  - Accenture          EPAM - EPAM Systems
  CTSH - Cognizant          GLOB - Globant
  INFY - Infosys            IT   - Gartner
  WIT  - Wipro              BAH  - Booz Allen Hamilton

Usage:
  python collectors/job_postings.py              # live scrape
  python collectors/job_postings.py --mock       # generate mock data
  python collectors/job_postings.py --start-year 2022 --end-year 2025
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
RAW_DIR = os.path.join(BASE_DIR, "data", "jobs", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "jobs", "processed")

# Indeed Hiring Lab publishes aggregate data as downloadable CSVs
INDEED_HIRING_LAB_URL = "https://data.indeed.com/api/v1/job-trends"

# Company identifiers for job board searches
TRACKED_FIRMS = {
    "ACN": "Accenture",
    "CTSH": "Cognizant",
    "INFY": "Infosys",
    "WIT": "Wipro",
    "EPAM": "EPAM Systems",
    "GLOB": "Globant",
    "IT": "Gartner",
    "BAH": "Booz Allen Hamilton",
}

AI_JOB_KEYWORDS = [
    "artificial intelligence", "machine learning", "AI engineer",
    "ML engineer", "data scientist", "LLM", "generative AI",
    "AI researcher", "prompt engineer", "AI ops",
]

TRADITIONAL_JOB_KEYWORDS = [
    "software engineer", "java developer", "project manager",
    "business analyst", "QA engineer", "systems administrator",
    "network engineer", "database administrator",
]

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

USER_AGENT = "DisplacementCurve/1.0 (research@example.com)"


# ---------------------------------------------------------------------------
# Live Mode: Indeed / LinkedIn scraping
# ---------------------------------------------------------------------------

def fetch_job_postings(start_year, end_year):
    """
    Fetch job posting data from Indeed Hiring Lab API.

    In production, this would:
    1. Query Indeed Hiring Lab aggregate data for AI vs traditional roles
    2. Scrape LinkedIn Workforce Reports for firm-specific postings
    3. Aggregate and normalize the results

    The Indeed Hiring Lab publishes monthly aggregate job posting indices.
    LinkedIn Workforce Reports provide firm-level hiring data.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    all_data = []

    for firm_ticker, firm_name in TRACKED_FIRMS.items():
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"  Fetching job data for {firm_name} (attempt {attempt}/{MAX_RETRIES})...")
                # Indeed Hiring Lab API (would need API key in production)
                params = {
                    "company": firm_name,
                    "start_date": f"{start_year}-01",
                    "end_date": f"{end_year}-12",
                    "keywords": ",".join(AI_JOB_KEYWORDS[:3]),
                }
                resp = requests.get(
                    INDEED_HIRING_LAB_URL,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                all_data.append({"ticker": firm_ticker, "name": firm_name, "data": data})
                break

            except requests.RequestException as exc:
                print(f"  Request failed: {exc}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    print(f"  WARNING: Skipping {firm_name} after {MAX_RETRIES} failures")

        time.sleep(0.5)  # rate limit

    return all_data


def process_job_data(raw_data, start_year, end_year):
    """Transform raw job posting data into our standard schema."""
    # Build month labels
    months = []
    for year in range(start_year, end_year + 1):
        sm = 11 if year == start_year and start_year == 2022 else 1
        for m in range(sm, 13):
            months.append(f"{year}-{m:02d}")

    firms = {}
    for entry in raw_data:
        ticker = entry["ticker"]
        monthly = []
        for date_label in months:
            # In production, extract real counts from response
            monthly.append({
                "date": date_label,
                "ai_roles": 0,
                "traditional_roles": 0,
            })
        firms[ticker] = {"name": entry["name"], "monthly": monthly}

    market_monthly = []
    for date_label in months:
        market_monthly.append({
            "date": date_label,
            "total_postings_idx": 100.0,
            "ai_postings_pct": 0.0,
            "traditional_pct": 0.0,
            "ai_to_traditional_ratio": 0.0,
        })

    return {
        "metadata": {
            "source": "Indeed Hiring Lab / LinkedIn",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "monthly": market_monthly,
        "firms": firms,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock(start_year, end_year):
    """Delegate to the central Phase 3 mock generator and return job data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase3 import generate_job_postings
    data = generate_job_postings()
    # Filter to requested year range
    data["monthly"] = [
        m for m in data["monthly"]
        if start_year <= int(m["date"][:4]) <= end_year
    ]
    for ticker in data["firms"]:
        data["firms"][ticker]["monthly"] = [
            m for m in data["firms"][ticker]["monthly"]
            if start_year <= int(m["date"][:4]) <= end_year
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
    parser = argparse.ArgumentParser(description="Job Postings Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of scraping")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")
    args = parser.parse_args()

    print("Job Postings Collector")
    print(f"  Range: {args.start_year}-{args.end_year}")
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE (Indeed/LinkedIn)'}\n")

    if args.mock:
        processed = generate_mock(args.start_year, args.end_year)
    else:
        raw = fetch_job_postings(args.start_year, args.end_year)
        # Save raw response
        raw_path = os.path.join(RAW_DIR, f"jobs_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw, raw_path)
        processed = process_job_data(raw, args.start_year, args.end_year)

    save_json(processed, os.path.join(PROCESSED_DIR, "postings.json"))
    print("\nJob postings collection complete.")


if __name__ == "__main__":
    main()
