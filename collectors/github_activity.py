#!/usr/bin/env python3
"""
GitHub Activity Data Collector for the Displacement Curve.

Uses the GitHub REST API to track open-source AI activity across
professional-services topics. Monitors new repos, stars, contributors,
and forks by month.

Usage:
  python collectors/github_activity.py                          # unauthenticated (60 req/hr)
  python collectors/github_activity.py --token ghp_xxxxx        # authenticated (5000 req/hr)
  python collectors/github_activity.py --mock                   # generate mock data
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
RAW_DIR = os.path.join(BASE_DIR, "data", "github", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "github", "processed")

GITHUB_API = "https://api.github.com"
SEARCH_REPOS = f"{GITHUB_API}/search/repositories"

TOPICS = {
    "ai_accounting": "ai-accounting",
    "ai_legal": "ai-legal",
    "ai_compliance": "ai-compliance",
    "llm_agents": "ai-agent",
    "ai_automation": "ai-automation",
}

MAX_RETRIES = 3
RETRY_DELAY = 5


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def month_ranges(start_year=2022, start_month=11, end_year=2026, end_month=2):
    """Yield (year, month, start_date, end_date) for each month in range."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        start = f"{y}-{m:02d}-01"
        # End of month approximation
        if m == 12:
            end = f"{y + 1}-01-01"
        else:
            end = f"{y}-{m + 1:02d}-01"
        yield y, m, start, end
        m += 1
        if m > 12:
            m = 1
            y += 1


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def github_headers(token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_repos_by_topic(topic, created_range, headers):
    """Search GitHub for repos with a topic created in a date range."""
    q = f"topic:{topic} created:{created_range}"
    params = {"q": q, "sort": "stars", "order": "desc", "per_page": 100}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(SEARCH_REPOS, params=params, headers=headers, timeout=30)

            # Handle rate limiting
            if resp.status_code == 403 and "rate limit" in resp.text.lower():
                reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
                wait = max(1, reset_time - int(time.time()))
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(min(wait, 60))
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.RequestException as exc:
            print(f"    Request failed (attempt {attempt}): {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                return {"total_count": 0, "items": []}

    return {"total_count": 0, "items": []}


# ---------------------------------------------------------------------------
# Live fetch + processing
# ---------------------------------------------------------------------------

def fetch_github_data(token=None):
    """Fetch GitHub activity data for all topics across the full date range."""
    headers = github_headers(token)
    raw_results = {}

    for cat_name, topic in TOPICS.items():
        print(f"  Fetching topic: {topic}")
        cat_data = []
        cumulative_stars = 0
        cumulative_contributors = 0

        for y, m, start, end in month_ranges():
            date_label = f"{y}-{m:02d}"
            created_range = f"{start}..{end}"

            result = search_repos_by_topic(topic, created_range, headers)
            items = result.get("items", [])

            new_repos = result.get("total_count", len(items))
            month_stars = sum(r.get("stargazers_count", 0) for r in items)
            month_forks = sum(r.get("forks_count", 0) for r in items)
            # Approximate contributors from watchers + a factor
            month_contribs = sum(r.get("watchers_count", 0) for r in items)

            cumulative_stars += month_stars
            cumulative_contributors += month_contribs

            cat_data.append({
                "date": date_label,
                "new_repos": new_repos,
                "total_stars": cumulative_stars,
                "contributors": cumulative_contributors,
                "forks": month_forks,
            })

            # Polite delay to avoid rate limits
            time.sleep(1)

        raw_results[cat_name] = {"topic": topic, "data": cat_data}
        print(f"    Done: {len(cat_data)} months collected")

    return raw_results


def build_aggregate(categories):
    """Build aggregate totals across all categories."""
    # Assume all categories have the same number of months
    first_cat = next(iter(categories.values()))
    num_months = len(first_cat["data"])
    aggregate = []

    for i in range(num_months):
        date = first_cat["data"][i]["date"]
        total_repos = sum(cat["data"][i]["new_repos"] for cat in categories.values())
        total_stars = sum(cat["data"][i]["total_stars"] for cat in categories.values())
        total_contribs = sum(cat["data"][i]["contributors"] for cat in categories.values())
        aggregate.append({
            "date": date,
            "total_new_repos": total_repos,
            "total_stars": total_stars,
            "total_contributors": total_contribs,
        })

    return aggregate


def process_github_raw(raw_categories):
    """Package raw GitHub data into our standard schema."""
    aggregate = build_aggregate(raw_categories)

    return {
        "metadata": {
            "source": "GitHub API",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "categories": raw_categories,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to central mock generator."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_data import generate_github_data
    return generate_github_data()


# ---------------------------------------------------------------------------
# I/O
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
    parser = argparse.ArgumentParser(description="GitHub Activity Data Collector")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of calling GitHub API")
    parser.add_argument("--token", type=str, default=None, help="GitHub personal access token (optional, raises rate limit)")
    args = parser.parse_args()

    print("GitHub Activity Collector")
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE API'}")
    if args.token:
        print("  Auth:  Token provided (5000 req/hr)")
    else:
        print("  Auth:  Unauthenticated (60 req/hr)")
    print()

    if args.mock:
        processed = generate_mock()
    else:
        raw = fetch_github_data(token=args.token)
        raw_path = os.path.join(RAW_DIR, f"github_raw_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        save_json(raw, raw_path)
        processed = process_github_raw(raw)

    save_json(processed, os.path.join(PROCESSED_DIR, "activity.json"))
    print("\nGitHub collection complete.")


if __name__ == "__main__":
    main()
