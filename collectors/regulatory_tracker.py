#!/usr/bin/env python3
"""
Regulatory Guidance Tracker for the Displacement Curve.

Monitors AI-related regulatory activity from 7 agencies:
  fed   - Federal Reserve
  occ   - OCC (Office of the Comptroller of the Currency)
  fdic  - FDIC (Federal Deposit Insurance Corporation)
  cfpb  - CFPB (Consumer Financial Protection Bureau)
  sec   - SEC (Securities and Exchange Commission)
  eu    - EU AI Act
  nist  - NIST (National Institute of Standards and Technology)

Tracks three document types per regulator per quarter:
  document_count    - Total AI-related documents published
  enforcement_count - Enforcement actions related to AI
  guidance_count    - Formal guidance documents on AI usage

Usage:
  python collectors/regulatory_tracker.py              # live RSS scan
  python collectors/regulatory_tracker.py --mock       # generate mock data
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None

try:
    import feedparser
except ImportError:
    feedparser = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "regulatory", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "regulatory", "processed")

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
USER_AGENT = "DisplacementCurve/1.0 (research@example.com)"

# RSS / Atom feed URLs for each regulator
REGULATOR_FEEDS = {
    "fed": {
        "name": "Federal Reserve",
        "feeds": [
            "https://www.federalreserve.gov/feeds/press_all.xml",
        ],
        "keywords": [
            "artificial intelligence", "machine learning", "AI",
            "automated decision", "algorithmic", "model risk",
        ],
    },
    "occ": {
        "name": "OCC",
        "feeds": [
            "https://www.occ.treas.gov/rss/occ-news-issuances.xml",
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning",
            "model risk", "automated", "algorithmic",
        ],
    },
    "fdic": {
        "name": "FDIC",
        "feeds": [
            "https://www.fdic.gov/rss/fdicrss.xml",
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning",
            "automated", "algorithmic", "fintech",
        ],
    },
    "cfpb": {
        "name": "CFPB",
        "feeds": [
            "https://www.consumerfinance.gov/feed/",
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning",
            "automated decision", "algorithmic", "chatbot",
        ],
    },
    "sec": {
        "name": "SEC",
        "feeds": [
            "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=rule&dateb=&owner=include&count=40&search_text=&action=getcompany&RSS=1",
            "https://www.sec.gov/rss/news/press.xml",
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning",
            "automated", "algorithmic trading", "robo-advisor",
        ],
    },
    "eu": {
        "name": "EU AI Act",
        "feeds": [
            "https://eur-lex.europa.eu/EN/display-news.rss",
        ],
        "keywords": [
            "artificial intelligence", "AI act", "AI regulation",
            "high-risk AI", "general-purpose AI", "foundation model",
        ],
    },
    "nist": {
        "name": "NIST",
        "feeds": [
            "https://www.nist.gov/news-events/news/rss.xml",
        ],
        "keywords": [
            "artificial intelligence", "AI", "machine learning",
            "AI risk", "AI framework", "trustworthy AI",
        ],
    },
}


# ---------------------------------------------------------------------------
# RSS Feed Processing (Live Mode)
# ---------------------------------------------------------------------------

def fetch_feed(url):
    """Fetch and parse an RSS/Atom feed."""
    if feedparser is None:
        print("  WARNING: feedparser not installed. Install with: pip install feedparser")
        return []

    try:
        feed = feedparser.parse(url)
        return feed.entries
    except Exception as exc:
        print(f"  ERROR parsing feed {url}: {exc}")
        return []


def entry_matches_keywords(entry, keywords):
    """Check if a feed entry matches any AI-related keywords."""
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", ""),
    ]).lower()
    return any(kw.lower() in text for kw in keywords)


def classify_entry(entry):
    """Classify a feed entry as enforcement, guidance, or general document."""
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
    ]).lower()

    if any(term in text for term in ["enforcement", "penalty", "fine", "action against", "cease and desist"]):
        return "enforcement"
    elif any(term in text for term in ["guidance", "framework", "standard", "bulletin", "advisory"]):
        return "guidance"
    else:
        return "document"


def get_entry_quarter(entry):
    """Extract the quarter label from a feed entry's published date."""
    for date_field in ["published_parsed", "updated_parsed"]:
        parsed = entry.get(date_field)
        if parsed:
            year = parsed.tm_year
            month = parsed.tm_mon
            q = (month - 1) // 3 + 1
            return f"{year}-Q{q}"
    return None


def scan_regulators(start_year=2022, end_year=2025):
    """Scan all regulator RSS feeds for AI-related content."""
    # Build quarter list
    quarters = []
    for year in range(start_year, end_year + 1):
        sq = 4 if year == start_year and start_year == 2022 else 1
        for q in range(sq, 5):
            quarters.append(f"{year}-Q{q}")

    regulators = {}
    raw_entries = {}

    for reg_key, cfg in REGULATOR_FEEDS.items():
        print(f"  Scanning {cfg['name']}...")
        buckets = {q: {"document_count": 0, "enforcement_count": 0, "guidance_count": 0} for q in quarters}
        raw_list = []

        for feed_url in cfg["feeds"]:
            entries = fetch_feed(feed_url)
            for entry in entries:
                if not entry_matches_keywords(entry, cfg["keywords"]):
                    continue

                quarter = get_entry_quarter(entry)
                if quarter is None or quarter not in buckets:
                    continue

                doc_type = classify_entry(entry)
                buckets[quarter]["document_count"] += 1
                if doc_type == "enforcement":
                    buckets[quarter]["enforcement_count"] += 1
                elif doc_type == "guidance":
                    buckets[quarter]["guidance_count"] += 1

                raw_list.append({
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "quarter": quarter,
                    "type": doc_type,
                })

            time.sleep(0.5)  # Rate limit between feeds

        quarterly = []
        for q in quarters:
            quarterly.append({
                "quarter": q,
                "document_count": buckets[q]["document_count"],
                "enforcement_count": buckets[q]["enforcement_count"],
                "guidance_count": buckets[q]["guidance_count"],
            })

        regulators[reg_key] = {"name": cfg["name"], "quarterly": quarterly}
        raw_entries[reg_key] = raw_list
        print(f"    Found {sum(b['document_count'] for b in buckets.values())} AI-related documents")

    # Build aggregate
    aggregate = []
    cumulative = 0
    for i, q in enumerate(quarters):
        total = sum(regulators[k]["quarterly"][i]["document_count"] for k in regulators)
        cumulative += total
        aggregate.append({
            "quarter": q,
            "total_documents": total,
            "cumulative_documents": cumulative,
        })

    processed = {
        "metadata": {
            "source": "Federal Regulators RSS",
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "mock": False,
        },
        "regulators": regulators,
        "aggregate": aggregate,
    }

    return processed, raw_entries


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to the central Phase 4 mock generator and return regulatory data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase4 import generate_regulatory
    return generate_regulatory()


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
    parser = argparse.ArgumentParser(description="Regulatory Guidance Tracker")
    parser.add_argument("--mock", action="store_true", help="Generate mock data instead of scanning feeds")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2025, help="End year (default: 2025)")
    args = parser.parse_args()

    print("Regulatory Guidance Tracker")
    print(f"  Range: {args.start_year}-{args.end_year}")
    print(f"  Mode:  {'MOCK' if args.mock else 'LIVE (RSS feeds)'}\n")

    if args.mock:
        processed = generate_mock()
    else:
        processed, raw_entries = scan_regulators(args.start_year, args.end_year)
        # Save raw entries
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_path = os.path.join(RAW_DIR, f"regulatory_scan_{ts}.json")
        save_json(raw_entries, raw_path)

    save_json(processed, os.path.join(PROCESSED_DIR, "guidance.json"))

    # Print summary
    last_agg = processed["aggregate"][-1]
    print(f"\n  Total cumulative documents: {last_agg['cumulative_documents']}")
    print(f"  Regulators tracked: {len(processed['regulators'])}")
    print("\nRegulatory guidance collection complete.")


if __name__ == "__main__":
    main()
