#!/usr/bin/env python3
"""
Phase 2 Mock Data Generator for the Displacement Curve project.

Generates realistic mock data for:
  - Earnings transcripts: Revenue, AI revenue, headcount for 8 IT services firms
  - SEC workforce disclosures: Headcount and contractor % for 11 firms (8 IT + 3 staffing)

Time range:
  Earnings: Q4 2022 through Q4 2025 (13 quarters)
  Workforce: Annual 2022-2025

All data is mock but calibrated to publicly available figures.
"""

import json
import math
import os
import random

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

QUARTERS = []
for year in range(2022, 2026):
    start_q = 4 if year == 2022 else 1
    end_q = 4
    for q in range(start_q, end_q + 1):
        QUARTERS.append(f"{year}-Q{q}")

TOTAL_QUARTERS = len(QUARTERS)  # 13 quarters


def quarter_index(label):
    """Return 0-based index for a quarter label."""
    return QUARTERS.index(label)


def lerp(start, end, t):
    """Linear interpolation."""
    return start + (end - start) * t


def smooth_growth(start, end, n, curvature=1.5):
    """Generate n values from start to end with smooth exponential-ish growth."""
    values = []
    for i in range(n):
        t = i / max(1, n - 1)
        # Use power curve for acceleration
        val = start + (end - start) * (t ** curvature)
        values.append(val)
    return values


# ---------------------------------------------------------------------------
# Firm Configurations
# ---------------------------------------------------------------------------

EARNINGS_FIRMS = {
    "ACN": {
        "name": "Accenture",
        "total_rev_start": 15750, "total_rev_end": 16400,
        "ai_rev_start": 450, "ai_rev_end": 3000,
        "headcount_start": 738000, "headcount_end": 733000,
        "rev_growth_curve": 1.0,  # near linear total rev
        "ai_growth_curve": 1.8,  # accelerating AI rev
        "rev_noise": 150, "ai_noise": 30, "hc_noise": 800,
    },
    "CTSH": {
        "name": "Cognizant",
        "total_rev_start": 4800, "total_rev_end": 5050,
        "ai_rev_start": 80, "ai_rev_end": 500,
        "headcount_start": 351000, "headcount_end": 340000,
        "rev_growth_curve": 1.0,
        "ai_growth_curve": 1.7,
        "rev_noise": 60, "ai_noise": 10, "hc_noise": 500,
    },
    "INFY": {
        "name": "Infosys",
        "total_rev_start": 4500, "total_rev_end": 4850,
        "ai_rev_start": 60, "ai_rev_end": 400,
        "headcount_start": 346000, "headcount_end": 337000,
        "rev_growth_curve": 1.0,
        "ai_growth_curve": 1.7,
        "rev_noise": 55, "ai_noise": 8, "hc_noise": 500,
    },
    "WIT": {
        "name": "Wipro",
        "total_rev_start": 2700, "total_rev_end": 2900,
        "ai_rev_start": 30, "ai_rev_end": 200,
        "headcount_start": 258000, "headcount_end": 245000,
        "rev_growth_curve": 1.0,
        "ai_growth_curve": 1.6,
        "rev_noise": 35, "ai_noise": 5, "hc_noise": 400,
    },
    "EPAM": {
        "name": "EPAM Systems",
        "total_rev_start": 900, "total_rev_end": 1020,
        "ai_rev_start": 20, "ai_rev_end": 150,
        "headcount_start": 55000, "headcount_end": 52000,
        "rev_growth_curve": 1.1,
        "ai_growth_curve": 1.8,
        "rev_noise": 15, "ai_noise": 3, "hc_noise": 200,
    },
    "GLOB": {
        "name": "Globant",
        "total_rev_start": 500, "total_rev_end": 620,
        "ai_rev_start": 15, "ai_rev_end": 100,
        "headcount_start": 27000, "headcount_end": 28500,
        "rev_growth_curve": 1.2,
        "ai_growth_curve": 1.9,
        "rev_noise": 10, "ai_noise": 2, "hc_noise": 100,
    },
    "IT": {
        "name": "Gartner",
        "total_rev_start": 1400, "total_rev_end": 1520,
        "ai_rev_start": 30, "ai_rev_end": 180,
        "headcount_start": 19000, "headcount_end": 20200,
        "rev_growth_curve": 1.0,
        "ai_growth_curve": 1.7,
        "rev_noise": 20, "ai_noise": 4, "hc_noise": 80,
    },
    "BAH": {
        "name": "Booz Allen Hamilton",
        "total_rev_start": 2500, "total_rev_end": 2820,
        "ai_rev_start": 100, "ai_rev_end": 500,
        "headcount_start": 33000, "headcount_end": 34200,
        "rev_growth_curve": 1.1,
        "ai_growth_curve": 1.6,
        "rev_noise": 30, "ai_noise": 8, "hc_noise": 100,
    },
}

# Workforce: same 8 + 3 staffing firms
WORKFORCE_FIRMS = {
    "ACN": {"name": "Accenture", "hc": [738000, 733000, 730000, 725000], "contractor_pct": [12.5, 13.8, 15.2, 16.5]},
    "CTSH": {"name": "Cognizant", "hc": [351000, 348000, 344000, 340000], "contractor_pct": [10.2, 11.5, 13.0, 14.8]},
    "INFY": {"name": "Infosys", "hc": [346000, 343000, 340000, 337000], "contractor_pct": [9.8, 10.9, 12.4, 13.6]},
    "WIT": {"name": "Wipro", "hc": [258000, 253000, 249000, 245000], "contractor_pct": [11.0, 12.3, 13.8, 15.1]},
    "EPAM": {"name": "EPAM Systems", "hc": [55000, 54200, 53100, 52000], "contractor_pct": [8.5, 9.8, 11.5, 13.2]},
    "GLOB": {"name": "Globant", "hc": [27000, 27500, 28000, 28500], "contractor_pct": [7.2, 8.0, 9.1, 10.5]},
    "IT": {"name": "Gartner", "hc": [19000, 19400, 19800, 20200], "contractor_pct": [6.8, 7.5, 8.4, 9.2]},
    "BAH": {"name": "Booz Allen Hamilton", "hc": [33000, 33400, 33800, 34200], "contractor_pct": [14.0, 15.2, 16.5, 17.8]},
    "KFRC": {"name": "Kforce", "hc": [8200, 7900, 7700, 7500], "contractor_pct": [22.0, 24.5, 27.0, 29.5]},
    "RHI": {"name": "Robert Half", "hc": [14500, 13800, 13200, 12800], "contractor_pct": [18.5, 20.8, 23.2, 25.0]},
    "MAN": {"name": "ManpowerGroup", "hc": [28000, 27000, 26200, 25500], "contractor_pct": [20.0, 22.0, 24.5, 26.8]},
}


# ---------------------------------------------------------------------------
# Earnings Data Generator
# ---------------------------------------------------------------------------

def generate_earnings_data():
    """Generate quarterly earnings data for 8 IT services firms."""
    random.seed(2026)

    firms = {}

    for ticker, cfg in EARNINGS_FIRMS.items():
        total_revs = smooth_growth(
            cfg["total_rev_start"], cfg["total_rev_end"],
            TOTAL_QUARTERS, cfg["rev_growth_curve"]
        )
        ai_revs = smooth_growth(
            cfg["ai_rev_start"], cfg["ai_rev_end"],
            TOTAL_QUARTERS, cfg["ai_growth_curve"]
        )
        headcounts = smooth_growth(
            cfg["headcount_start"], cfg["headcount_end"],
            TOTAL_QUARTERS, 1.0
        )

        quarterly = []
        for i, q_label in enumerate(QUARTERS):
            total_rev = round(total_revs[i] + random.gauss(0, cfg["rev_noise"]))
            ai_rev = round(ai_revs[i] + random.gauss(0, cfg["ai_noise"]))
            ai_rev = max(ai_rev, 1)  # floor at 1
            ai_rev = min(ai_rev, total_rev)  # cap at total

            headcount = round(headcounts[i] + random.gauss(0, cfg["hc_noise"]))

            # revenue_per_employee in thousands per employee per quarter
            rev_per_emp = round((total_rev * 1_000_000) / headcount / 1000, 1)

            quarterly.append({
                "quarter": q_label,
                "total_revenue_mm": total_rev,
                "ai_revenue_mm": ai_rev,
                "headcount": headcount,
                "revenue_per_employee": rev_per_emp,
            })

        firms[ticker] = {"name": cfg["name"], "quarterly": quarterly}

    # Build aggregate per quarter
    aggregate = []
    for i, q_label in enumerate(QUARTERS):
        total_ai = sum(firms[t]["quarterly"][i]["ai_revenue_mm"] for t in firms)
        all_ai_pcts = []
        all_rev_per_emp = []
        all_relabel = []

        for t in firms:
            q = firms[t]["quarterly"][i]
            ai_pct = q["ai_revenue_mm"] / q["total_revenue_mm"] * 100 if q["total_revenue_mm"] > 0 else 0
            all_ai_pcts.append(ai_pct)
            all_rev_per_emp.append(q["revenue_per_employee"])

            # Relabeling index: ratio of ai_rev growth rate to total_rev growth rate
            if i > 0:
                prev = firms[t]["quarterly"][i - 1]
                ai_growth_rate = (q["ai_revenue_mm"] - prev["ai_revenue_mm"]) / max(1, prev["ai_revenue_mm"])
                total_growth_rate = (q["total_revenue_mm"] - prev["total_revenue_mm"]) / max(1, prev["total_revenue_mm"])
                if abs(total_growth_rate) > 0.001:
                    relabel = ai_growth_rate / total_growth_rate
                else:
                    relabel = ai_growth_rate * 100  # large number if total barely moved
                all_relabel.append(max(0, relabel))
            else:
                all_relabel.append(1.0)  # baseline

        avg_ai_pct = round(sum(all_ai_pcts) / len(all_ai_pcts), 1)
        avg_relabel = round(sum(all_relabel) / len(all_relabel), 1)
        avg_rev_per_emp = round(sum(all_rev_per_emp) / len(all_rev_per_emp), 1)

        aggregate.append({
            "quarter": q_label,
            "total_ai_revenue_mm": total_ai,
            "avg_ai_pct": avg_ai_pct,
            "avg_relabeling_index": avg_relabel,
            "avg_rev_per_employee": avg_rev_per_emp,
        })

    return {
        "metadata": {
            "source": "SEC EDGAR / Earnings Transcripts",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "firms": firms,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Workforce Data Generator
# ---------------------------------------------------------------------------

def generate_workforce_data():
    """Generate annual workforce disclosure data for 11 firms."""
    random.seed(2027)

    years = [2022, 2023, 2024, 2025]
    firms = {}

    for ticker, cfg in WORKFORCE_FIRMS.items():
        annual = []
        for j, year in enumerate(years):
            hc = cfg["hc"][j] + random.randint(-200, 200)
            cpct = round(cfg["contractor_pct"][j] + random.uniform(-0.3, 0.3), 1)
            annual.append({
                "year": year,
                "total_headcount": hc,
                "contractor_pct": cpct,
            })
        firms[ticker] = {
            "name": cfg["name"],
            "ticker": ticker,
            "annual": annual,
        }

    # Aggregate per year
    aggregate = []
    for j, year in enumerate(years):
        total_hc = sum(firms[t]["annual"][j]["total_headcount"] for t in firms)
        avg_cpct = round(
            sum(firms[t]["annual"][j]["contractor_pct"] for t in firms) / len(firms), 1
        )
        aggregate.append({
            "year": year,
            "total_headcount": total_hc,
            "avg_contractor_pct": avg_cpct,
        })

    return {
        "metadata": {
            "source": "SEC EDGAR 10-K/10-Q",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "firms": firms,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Main: write all Phase 2 mock data files
# ---------------------------------------------------------------------------

def write_json(data, rel_path):
    path = os.path.join(SCRIPT_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {path}  ({os.path.getsize(path)} bytes)")


def main():
    print("Generating Phase 2 mock data for the Displacement Curve...\n")

    earnings = generate_earnings_data()
    write_json(earnings, "earnings/processed/revenue.json")

    workforce = generate_workforce_data()
    write_json(workforce, "sec/processed/workforce.json")

    print("\nPhase 2 mock data generation complete.")


if __name__ == "__main__":
    main()
