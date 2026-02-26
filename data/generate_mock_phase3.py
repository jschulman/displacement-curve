#!/usr/bin/env python3
"""
Phase 3 Mock Data Generator for the Displacement Curve project.

Generates realistic mock data for:
  - VC Funding: AI-native startup funding across 6 categories (SEC EDGAR Form D)
  - Job Postings: AI vs traditional role postings for 8 IT services firms

Time range:
  VC Funding: Q4 2022 through Q4 2025 (13 quarters)
  Job Postings: 2022-11 through 2025-12 (38 months)

All data is mock but calibrated to publicly available figures and realistic
AI hype-cycle growth curves.
"""

import json
import math
import os
import random

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 13 quarters: 2022-Q4 through 2025-Q4
QUARTERS = []
for year in range(2022, 2026):
    start_q = 4 if year == 2022 else 1
    end_q = 4
    for q in range(start_q, end_q + 1):
        QUARTERS.append(f"{year}-Q{q}")

TOTAL_QUARTERS = len(QUARTERS)  # 13

# 38 months: 2022-11 through 2025-12
MONTHS = []
for year in range(2022, 2026):
    start_m = 11 if year == 2022 else 1
    end_m = 12
    for m in range(start_m, end_m + 1):
        MONTHS.append(f"{year}-{m:02d}")

TOTAL_MONTHS = len(MONTHS)  # 38


def smooth_growth(start, end, n, curvature=1.5):
    """Generate n values from start to end with smooth power-curve growth."""
    values = []
    for i in range(n):
        t = i / max(1, n - 1)
        val = start + (end - start) * (t ** curvature)
        values.append(val)
    return values


def write_json(data, rel_path):
    """Write JSON data to a path relative to this script's directory."""
    path = os.path.join(SCRIPT_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {path}  ({os.path.getsize(path)} bytes)")


# ---------------------------------------------------------------------------
# VC Funding Data Generator
# ---------------------------------------------------------------------------

VC_CATEGORIES = {
    "ai_audit": {
        "name": "AI-Native Audit/Accounting",
        "funding_start": 12.0, "funding_end": 280.0,
        "deals_start": 2, "deals_end": 14,
        "curvature": 2.0,
    },
    "ai_legal": {
        "name": "AI Legal Services",
        "funding_start": 18.0, "funding_end": 350.0,
        "deals_start": 3, "deals_end": 18,
        "curvature": 1.9,
    },
    "ai_consulting": {
        "name": "AI Consulting/Strategy",
        "funding_start": 25.0, "funding_end": 420.0,
        "deals_start": 4, "deals_end": 22,
        "curvature": 1.8,
    },
    "ai_compliance": {
        "name": "AI Compliance/Regulatory",
        "funding_start": 8.0, "funding_end": 200.0,
        "deals_start": 1, "deals_end": 10,
        "curvature": 2.1,
    },
    "ai_staffing": {
        "name": "AI-Native Staffing",
        "funding_start": 15.0, "funding_end": 310.0,
        "deals_start": 2, "deals_end": 16,
        "curvature": 2.0,
    },
    "horizontal_ai": {
        "name": "Horizontal AI Agents",
        "funding_start": 30.0, "funding_end": 650.0,
        "deals_start": 5, "deals_end": 30,
        "curvature": 1.7,
    },
}


def generate_vc_funding():
    """Generate quarterly VC funding data across 6 AI categories."""
    random.seed(3001)

    categories = {}

    for cat_key, cfg in VC_CATEGORIES.items():
        funding_curve = smooth_growth(
            cfg["funding_start"], cfg["funding_end"],
            TOTAL_QUARTERS, cfg["curvature"]
        )
        deals_curve = smooth_growth(
            cfg["deals_start"], cfg["deals_end"],
            TOTAL_QUARTERS, cfg["curvature"]
        )

        quarterly = []
        for i, q_label in enumerate(QUARTERS):
            funding = round(funding_curve[i] + random.gauss(0, funding_curve[i] * 0.08), 1)
            funding = max(1.0, funding)
            deals = max(1, round(deals_curve[i] + random.gauss(0, 0.8)))
            quarterly.append({
                "quarter": q_label,
                "funding_mm": funding,
                "deal_count": deals,
            })

        categories[cat_key] = {
            "name": cfg["name"],
            "quarterly": quarterly,
        }

    # Build aggregate per quarter with cumulative
    aggregate = []
    cumulative = 0.0

    for i, q_label in enumerate(QUARTERS):
        total_funding = round(sum(
            categories[k]["quarterly"][i]["funding_mm"] for k in categories
        ), 1)
        total_deals = sum(
            categories[k]["quarterly"][i]["deal_count"] for k in categories
        )
        cumulative = round(cumulative + total_funding, 1)

        aggregate.append({
            "quarter": q_label,
            "total_funding_mm": total_funding,
            "total_deals": total_deals,
            "cumulative_mm": cumulative,
        })

    return {
        "metadata": {
            "source": "SEC EDGAR Form D",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "categories": categories,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Job Postings Data Generator
# ---------------------------------------------------------------------------

JOB_FIRMS = {
    "ACN": {
        "name": "Accenture",
        "ai_roles_start": 12, "ai_roles_end": 185,
        "trad_roles_start": 340, "trad_roles_end": 245,
        "ai_curve": 1.8, "trad_curve": 1.0,
        "ai_noise": 3, "trad_noise": 15,
    },
    "CTSH": {
        "name": "Cognizant",
        "ai_roles_start": 8, "ai_roles_end": 130,
        "trad_roles_start": 280, "trad_roles_end": 200,
        "ai_curve": 1.8, "trad_curve": 1.0,
        "ai_noise": 2, "trad_noise": 12,
    },
    "INFY": {
        "name": "Infosys",
        "ai_roles_start": 6, "ai_roles_end": 110,
        "trad_roles_start": 260, "trad_roles_end": 190,
        "ai_curve": 1.9, "trad_curve": 1.0,
        "ai_noise": 2, "trad_noise": 10,
    },
    "WIT": {
        "name": "Wipro",
        "ai_roles_start": 5, "ai_roles_end": 90,
        "trad_roles_start": 220, "trad_roles_end": 160,
        "ai_curve": 1.8, "trad_curve": 1.0,
        "ai_noise": 2, "trad_noise": 10,
    },
    "EPAM": {
        "name": "EPAM Systems",
        "ai_roles_start": 3, "ai_roles_end": 55,
        "trad_roles_start": 120, "trad_roles_end": 85,
        "ai_curve": 1.9, "trad_curve": 1.0,
        "ai_noise": 1, "trad_noise": 5,
    },
    "GLOB": {
        "name": "Globant",
        "ai_roles_start": 2, "ai_roles_end": 42,
        "trad_roles_start": 80, "trad_roles_end": 60,
        "ai_curve": 2.0, "trad_curve": 1.0,
        "ai_noise": 1, "trad_noise": 4,
    },
    "IT": {
        "name": "Gartner",
        "ai_roles_start": 4, "ai_roles_end": 60,
        "trad_roles_start": 95, "trad_roles_end": 72,
        "ai_curve": 1.8, "trad_curve": 1.0,
        "ai_noise": 1, "trad_noise": 4,
    },
    "BAH": {
        "name": "Booz Allen Hamilton",
        "ai_roles_start": 10, "ai_roles_end": 140,
        "trad_roles_start": 180, "trad_roles_end": 130,
        "ai_curve": 1.7, "trad_curve": 1.0,
        "ai_noise": 3, "trad_noise": 8,
    },
}


def generate_job_postings():
    """Generate monthly job posting data for 8 IT services firms."""
    random.seed(3002)

    # --- Per-firm monthly data ---
    firms = {}

    for ticker, cfg in JOB_FIRMS.items():
        ai_curve = smooth_growth(
            cfg["ai_roles_start"], cfg["ai_roles_end"],
            TOTAL_MONTHS, cfg["ai_curve"]
        )
        trad_curve = smooth_growth(
            cfg["trad_roles_start"], cfg["trad_roles_end"],
            TOTAL_MONTHS, cfg["trad_curve"]
        )

        monthly = []
        for i, date_label in enumerate(MONTHS):
            ai = max(1, round(ai_curve[i] + random.gauss(0, cfg["ai_noise"])))
            trad = max(10, round(trad_curve[i] + random.gauss(0, cfg["trad_noise"])))
            monthly.append({
                "date": date_label,
                "ai_roles": ai,
                "traditional_roles": trad,
            })

        firms[ticker] = {"name": cfg["name"], "monthly": monthly}

    # --- Market-level monthly aggregates ---
    # ai_postings_pct: ~3.2% (Nov 2022) -> ~18% (Dec 2025)
    # traditional_pct: ~72.1% (Nov 2022) -> ~55% (Dec 2025)
    # total_postings_idx: 100 baseline, grows modestly to ~112

    ai_pct_curve = smooth_growth(3.2, 18.0, TOTAL_MONTHS, 1.6)
    trad_pct_curve = smooth_growth(72.1, 55.0, TOTAL_MONTHS, 1.0)
    total_idx_curve = smooth_growth(100.0, 112.0, TOTAL_MONTHS, 1.0)

    market_monthly = []
    for i, date_label in enumerate(MONTHS):
        ai_pct = round(ai_pct_curve[i] + random.gauss(0, 0.3), 1)
        ai_pct = max(1.0, ai_pct)
        trad_pct = round(trad_pct_curve[i] + random.gauss(0, 0.5), 1)
        trad_pct = max(30.0, trad_pct)
        total_idx = round(total_idx_curve[i] + random.gauss(0, 0.8), 1)
        total_idx = max(90.0, total_idx)

        ratio = round(ai_pct / trad_pct, 3)

        market_monthly.append({
            "date": date_label,
            "total_postings_idx": total_idx,
            "ai_postings_pct": ai_pct,
            "traditional_pct": trad_pct,
            "ai_to_traditional_ratio": ratio,
        })

    return {
        "metadata": {
            "source": "Indeed Hiring Lab / LinkedIn",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "monthly": market_monthly,
        "firms": firms,
    }


# ---------------------------------------------------------------------------
# Main: write all Phase 3 mock data files
# ---------------------------------------------------------------------------

def main():
    print("Generating Phase 3 mock data for the Displacement Curve...\n")

    vc_data = generate_vc_funding()
    write_json(vc_data, "vc/processed/funding.json")

    jobs_data = generate_job_postings()
    write_json(jobs_data, "jobs/processed/postings.json")

    print("\nPhase 3 mock data generation complete.")


if __name__ == "__main__":
    main()
