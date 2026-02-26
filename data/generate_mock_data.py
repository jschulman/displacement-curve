#!/usr/bin/env python3
"""
Mock Data Generator for the Displacement Curve project.

Generates realistic mock data for all 3 signals:
  - BLS Employment (monthly, thousands of employees)
  - Google Trends (search interest indexed to Jan 2023 = 100)
  - GitHub Activity (repos, stars, contributors by month)

Time range: November 2022 (ChatGPT launch) through February 2026.
"""

import json
import math
import os
import random
from datetime import datetime

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
START_YEAR, START_MONTH = 2022, 11
END_YEAR, END_MONTH = 2026, 2


def date_range():
    """Yield (year, month) tuples from START through END inclusive."""
    y, m = START_YEAR, START_MONTH
    while (y, m) <= (END_YEAR, END_MONTH):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def date_label(y, m):
    return f"{y}-{m:02d}"


def months_list():
    return [date_label(y, m) for y, m in date_range()]


def month_index(y, m):
    """Return 0-based index from start of time range."""
    return (y - START_YEAR) * 12 + (m - START_MONTH)


TOTAL_MONTHS = month_index(END_YEAR, END_MONTH) + 1  # 40 months

# Seasonal pattern: slight Q1 bump, Q3 dip (typical professional services)
SEASONAL = {1: 0.3, 2: 0.2, 3: 0.1, 4: 0.0, 5: -0.1, 6: -0.1,
            7: -0.2, 8: -0.2, 9: -0.1, 10: 0.0, 11: 0.1, 12: 0.2}


# ---------------------------------------------------------------------------
# BLS Employment Mock Data
# ---------------------------------------------------------------------------

def generate_bls_data():
    """Generate realistic BLS CES employment data (thousands)."""

    series_config = {
        "CES5541200001": {
            "name": "Accounting & Tax Preparation",
            "base": 1055.0,
            "monthly_growth": 0.0012,
            "flatten_after": "2024-09",  # growth flattens mid-2024
            "seasonal_amp": 8.0,
            "noise_std": 1.5,
        },
        "CES5541600001": {
            "name": "Management & Technical Consulting",
            "base": 1610.0,
            "monthly_growth": 0.0018,
            "flatten_after": None,
            "seasonal_amp": 6.0,
            "noise_std": 2.0,
        },
        "CES5541100001": {
            "name": "Legal Services",
            "base": 1155.0,
            "monthly_growth": 0.0004,  # very flat
            "flatten_after": None,
            "seasonal_amp": 3.0,
            "noise_std": 1.2,
        },
        "CES5541500001": {
            "name": "Computer Systems Design",
            "base": 2105.0,
            "monthly_growth": 0.0025,
            "decline_after": "2025-06",  # slight decline late 2025
            "decline_rate": -0.0015,
            "seasonal_amp": 5.0,
            "noise_std": 3.0,
        },
        "CES5000000001": {
            "name": "Total Professional & Business Services",
            "base": 22520.0,
            "monthly_growth": 0.0010,
            "flatten_after": None,
            "seasonal_amp": 30.0,
            "noise_std": 12.0,
        },
    }

    random.seed(42)  # reproducibility
    series = {}

    for sid, cfg in series_config.items():
        data = []
        val = cfg["base"]
        for y, m in date_range():
            dl = date_label(y, m)
            idx = month_index(y, m)

            # Determine growth rate
            growth = cfg["monthly_growth"]
            if cfg.get("flatten_after") and dl >= cfg["flatten_after"]:
                growth *= 0.15  # near-zero growth
            if cfg.get("decline_after") and dl >= cfg["decline_after"]:
                growth = cfg["decline_rate"]

            val *= (1 + growth)
            seasonal = cfg["seasonal_amp"] * SEASONAL.get(m, 0)
            noise = random.gauss(0, cfg["noise_std"])
            reported = round(val + seasonal + noise, 1)

            data.append({"date": dl, "value": reported})

        series[sid] = {"name": cfg["name"], "data": data}

    return {
        "metadata": {
            "source": "BLS CES",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "series": series,
    }


# ---------------------------------------------------------------------------
# Google Trends Mock Data
# ---------------------------------------------------------------------------

def _trends_curve(months, pattern, seed_offset=0):
    """Generate a composite search-interest curve."""
    random.seed(100 + seed_offset)
    data = []
    dates = months_list()

    for i, dl in enumerate(dates):
        t = i / (TOTAL_MONTHS - 1)  # 0..1 normalised time

        if pattern == "ai_adoption":
            # Starts low, spikes at ChatGPT, steady exponential-ish growth
            base = 15 + 335 * (1 - math.exp(-3.0 * t))
            # Extra spike around ChatGPT launch (index 0-2)
            if i <= 2:
                base = 15 + 85 * i  # ramp 15 -> 100 -> ~185
            if i == 2:
                base = 100  # anchor Jan 2023 = 100

        elif pattern == "disruption_anxiety":
            base = 10 + 90 * t
            # Sharp spike around GPT-4 (Mar 2023, index ~4)
            if 3 <= i <= 6:
                spike = 200 * math.exp(-0.5 * (i - 4) ** 2)
                base += spike
            # Second wave late 2024
            if 20 <= i <= 26:
                base += 60 * math.exp(-0.3 * (i - 23) ** 2)
            base = min(base, 300)
            # Settle toward 250 at end
            if i >= 30:
                base = 220 + 30 * ((i - 30) / (TOTAL_MONTHS - 30))

        elif pattern == "upskilling":
            # Near-zero start, slow growth, accelerates 2025 -> ~180 by end
            base = 3 + 177 * (t ** 2.5)
            base = min(base, 200)

        elif pattern == "tool_adoption":
            # Near-zero, exponential through 2024-2025 -> ~400 by end
            base = 5 + 395 * (t ** 2.2)
            base = min(base, 450)

        noise = random.gauss(0, max(3, base * 0.05))
        val = max(1, round(base + noise))
        data.append({"date": dl, "value": val})

    return data


def generate_trends_data():
    categories = {
        "ai_adoption": {
            "terms": [
                "AI agent for accounting",
                "AI audit tool",
                "AI compliance software",
            ],
            "composite": _trends_curve(TOTAL_MONTHS, "ai_adoption", seed_offset=0),
        },
        "disruption_anxiety": {
            "terms": [
                "AI replacing consultants",
                "AI replacing accountants",
                "AI replacing lawyers",
            ],
            "composite": _trends_curve(TOTAL_MONTHS, "disruption_anxiety", seed_offset=1),
        },
        "upskilling": {
            "terms": [
                "AI certification accounting",
                "AI for CPAs",
                "prompt engineering for consultants",
            ],
            "composite": _trends_curve(TOTAL_MONTHS, "upskilling", seed_offset=2),
        },
        "tool_adoption": {
            "terms": [
                "ChatGPT for audit",
                "Claude for accounting",
                "AI tax preparation",
            ],
            "composite": _trends_curve(TOTAL_MONTHS, "tool_adoption", seed_offset=3),
        },
    }

    return {
        "metadata": {
            "source": "Google Trends",
            "last_updated": "2026-02-26",
            "mock": True,
            "baseline": "2023-01 = 100",
        },
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# GitHub Activity Mock Data
# ---------------------------------------------------------------------------

def _github_category(topic, base_repos, base_stars, base_contributors, growth_rate, seed_offset=0):
    """Generate monthly GitHub activity for a topic category."""
    random.seed(200 + seed_offset)
    data = []
    cumulative_stars = base_stars
    cumulative_contributors = base_contributors

    for i, dl in enumerate(months_list()):
        t = i / (TOTAL_MONTHS - 1)

        # Exponential growth: slow start, big acceleration mid-2023 onward
        growth_mult = math.exp(growth_rate * i)

        new_repos = max(1, round(base_repos * growth_mult + random.gauss(0, max(1, base_repos * growth_mult * 0.15))))
        month_stars = max(10, round(base_stars * 0.15 * growth_mult + random.gauss(0, base_stars * growth_mult * 0.02)))
        month_contribs = max(5, round(base_contributors * 0.4 * growth_mult + random.gauss(0, base_contributors * growth_mult * 0.05)))

        cumulative_stars += month_stars
        cumulative_contributors += month_contribs

        data.append({
            "date": dl,
            "new_repos": new_repos,
            "total_stars": cumulative_stars,
            "contributors": cumulative_contributors,
        })

    return {"topic": topic, "data": data}


def generate_github_data():
    categories = {
        "ai_accounting": _github_category("ai-accounting", 3, 120, 45, 0.08, seed_offset=0),
        "ai_legal": _github_category("ai-legal", 2, 90, 30, 0.07, seed_offset=1),
        "ai_compliance": _github_category("ai-compliance", 2, 100, 35, 0.075, seed_offset=2),
        "llm_agents": _github_category("ai-agent", 8, 1500, 500, 0.10, seed_offset=3),
        "ai_automation": _github_category("ai-automation", 5, 700, 200, 0.09, seed_offset=4),
    }

    # Build aggregate
    dates = months_list()
    aggregate = []
    for i, dl in enumerate(dates):
        total_repos = sum(cat["data"][i]["new_repos"] for cat in categories.values())
        total_stars = sum(cat["data"][i]["total_stars"] for cat in categories.values())
        total_contribs = sum(cat["data"][i]["contributors"] for cat in categories.values())
        aggregate.append({
            "date": dl,
            "total_new_repos": total_repos,
            "total_stars": total_stars,
            "total_contributors": total_contribs,
        })

    return {
        "metadata": {
            "source": "GitHub API",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "categories": categories,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Main: write all mock data files
# ---------------------------------------------------------------------------

def write_json(data, rel_path):
    path = os.path.join(SCRIPT_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {path}  ({os.path.getsize(path)} bytes)")


def main():
    print("Generating mock data for the Displacement Curve project...\n")

    bls = generate_bls_data()
    write_json(bls, "bls/processed/employment.json")

    trends = generate_trends_data()
    write_json(trends, "trends/processed/search_interest.json")

    github = generate_github_data()
    write_json(github, "github/processed/activity.json")

    print("\nDone. All mock data files generated.")


if __name__ == "__main__":
    main()
