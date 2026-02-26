#!/usr/bin/env python3
"""
Phase 4 Mock Data Generator for the Displacement Curve project.

Generates realistic mock data for:
  - Regulatory Guidance: AI-related documents from 7 regulators (quarterly)
  - Composite Displacement Index: Weighted 0-100 score from all 8 signals (monthly)

Time range:
  Regulatory: Q4 2022 through Q4 2025 (13 quarters)
  Composite:  2022-11 through 2025-12 (38 months)

All data is mock but calibrated to reflect the accelerating pace of AI
regulation and the composite displacement trajectory (18 -> ~58 over 38 months).
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
    for q in range(start_q, 5):
        QUARTERS.append(f"{year}-Q{q}")

TOTAL_QUARTERS = len(QUARTERS)  # 13

# 38 months: 2022-11 through 2025-12
MONTHS = []
for year in range(2022, 2026):
    start_m = 11 if year == 2022 else 1
    for m in range(start_m, 13):
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
# Regulatory Guidance Data Generator
# ---------------------------------------------------------------------------

REGULATORS = {
    "fed": {
        "name": "Federal Reserve",
        "doc_start": 1, "doc_end": 8,
        "enforce_start": 0, "enforce_end": 2,
        "guidance_start": 1, "guidance_end": 6,
        "curvature": 2.2,
    },
    "occ": {
        "name": "OCC",
        "doc_start": 1, "doc_end": 7,
        "enforce_start": 0, "enforce_end": 3,
        "guidance_start": 1, "guidance_end": 5,
        "curvature": 2.0,
    },
    "fdic": {
        "name": "FDIC",
        "doc_start": 0, "doc_end": 5,
        "enforce_start": 0, "enforce_end": 1,
        "guidance_start": 0, "guidance_end": 4,
        "curvature": 2.3,
    },
    "cfpb": {
        "name": "CFPB",
        "doc_start": 1, "doc_end": 6,
        "enforce_start": 0, "enforce_end": 2,
        "guidance_start": 1, "guidance_end": 4,
        "curvature": 2.1,
    },
    "sec": {
        "name": "SEC",
        "doc_start": 2, "doc_end": 10,
        "enforce_start": 0, "enforce_end": 4,
        "guidance_start": 2, "guidance_end": 7,
        "curvature": 1.9,
    },
    "eu": {
        "name": "EU AI Act",
        "doc_start": 1, "doc_end": 12,
        "enforce_start": 0, "enforce_end": 3,
        "guidance_start": 1, "guidance_end": 9,
        "curvature": 1.8,
    },
    "nist": {
        "name": "NIST",
        "doc_start": 1, "doc_end": 6,
        "enforce_start": 0, "enforce_end": 0,
        "guidance_start": 1, "guidance_end": 6,
        "curvature": 2.0,
    },
}


def generate_regulatory():
    """Generate quarterly regulatory guidance data from 7 regulators."""
    random.seed(4001)

    regulators = {}

    for reg_key, cfg in REGULATORS.items():
        doc_curve = smooth_growth(
            cfg["doc_start"], cfg["doc_end"],
            TOTAL_QUARTERS, cfg["curvature"]
        )
        enforce_curve = smooth_growth(
            cfg["enforce_start"], cfg["enforce_end"],
            TOTAL_QUARTERS, cfg["curvature"]
        )
        guidance_curve = smooth_growth(
            cfg["guidance_start"], cfg["guidance_end"],
            TOTAL_QUARTERS, cfg["curvature"]
        )

        quarterly = []
        for i, q_label in enumerate(QUARTERS):
            doc_count = max(0, round(doc_curve[i] + random.gauss(0, 0.5)))
            enforce_count = max(0, round(enforce_curve[i] + random.gauss(0, 0.3)))
            guidance_count = max(0, round(guidance_curve[i] + random.gauss(0, 0.4)))

            # Ensure document_count >= enforcement_count + guidance_count makes sense
            # (documents is the umbrella count)
            doc_count = max(doc_count, enforce_count + guidance_count)

            quarterly.append({
                "quarter": q_label,
                "document_count": doc_count,
                "enforcement_count": enforce_count,
                "guidance_count": guidance_count,
            })

        regulators[reg_key] = {
            "name": cfg["name"],
            "quarterly": quarterly,
        }

    # Build aggregate per quarter with cumulative
    aggregate = []
    cumulative = 0

    for i, q_label in enumerate(QUARTERS):
        total_docs = sum(
            regulators[k]["quarterly"][i]["document_count"] for k in regulators
        )
        cumulative += total_docs
        aggregate.append({
            "quarter": q_label,
            "total_documents": total_docs,
            "cumulative_documents": cumulative,
        })

    return {
        "metadata": {
            "source": "Federal Regulators RSS",
            "last_updated": "2026-02-26",
            "mock": True,
        },
        "regulators": regulators,
        "aggregate": aggregate,
    }


# ---------------------------------------------------------------------------
# Composite Displacement Index Generator
# ---------------------------------------------------------------------------

# Phase labels by score range
def get_phase(score):
    if score <= 25:
        return "Pre-disruption", "0-25"
    elif score <= 50:
        return "Productivity", "26-50"
    elif score <= 75:
        return "Erosion", "51-75"
    else:
        return "Displacement", "76-100"


# Weights for each signal
WEIGHTS = {
    "employment": 0.25,
    "rev_per_employee": 0.20,
    "vc_funding": 0.15,
    "job_ratio": 0.15,
    "trends": 0.10,
    "github": 0.10,
    "regulatory": 0.05,
}

# Key milestone events
EVENTS = [
    {"date": "2022-11", "label": "ChatGPT Launch", "type": "ai_release"},
    {"date": "2023-03", "label": "GPT-4 Release", "type": "ai_release"},
    {"date": "2023-07", "label": "Claude 2 Launch", "type": "ai_release"},
    {"date": "2024-03", "label": "Claude 3 Launch", "type": "ai_release"},
    {"date": "2024-06", "label": "EU AI Act Final", "type": "regulatory"},
    {"date": "2024-11", "label": "GPT-4o Launch", "type": "ai_release"},
    {"date": "2025-02", "label": "Claude 3.5 Opus", "type": "ai_release"},
    {"date": "2025-06", "label": "Accenture AI Revenue $3B", "type": "earnings"},
]


def generate_composite():
    """Generate monthly composite displacement index with component detail.

    The composite score is designed to start around 18 (Pre-disruption) in
    Nov 2022 and rise to approximately 55-62 (early Erosion) by Dec 2025.
    Raw values and normalization ranges are calibrated against a broader
    theoretical range (not just the observed dataset) so the score stays
    within realistic bounds rather than spanning the full 0-100 scale.
    """
    random.seed(4002)

    # Define realistic raw value trajectories for each component over 38 months
    # These raw values represent the actual signal observations.

    # Employment: BLS headcount (thousands) - starts high, modest decline
    employment_raw = smooth_growth(1580.2, 1498.5, TOTAL_MONTHS, 1.2)
    # Rev per employee: quarterly revenue per employee ($K) - rising
    rev_per_emp_raw = smooth_growth(19.5, 34.8, TOTAL_MONTHS, 1.6)
    # VC funding: monthly AI startup funding ($M) - rising
    vc_funding_raw = smooth_growth(104.7, 580.0, TOTAL_MONTHS, 1.8)
    # Job ratio: AI postings / traditional postings - rising
    job_ratio_raw = smooth_growth(0.043, 0.32, TOTAL_MONTHS, 1.7)
    # Google Trends: search interest index 0-100 - rising
    trends_raw = smooth_growth(22, 88, TOTAL_MONTHS, 1.4)
    # GitHub activity: AI repo stars index - rising
    github_raw = smooth_growth(45, 92, TOTAL_MONTHS, 1.5)
    # Regulatory: cumulative documents count - rising slowly
    regulatory_raw = smooth_growth(2, 48, TOTAL_MONTHS, 2.0)

    # Normalization ranges represent the theoretical full-displacement
    # scenario (score=100). These are wider than observed data so current
    # readings map to the ~18-60 range instead of spanning the full 0-100.
    # Format: (theoretical_min, theoretical_max)
    ranges = {
        "employment":       (1350.0, 1620.0),   # inverted: headcount down to 1350 = full displacement
        "rev_per_employee": (12.0, 50.0),        # theoretical max $50K/employee/quarter
        "vc_funding":       (0.0, 900.0),        # theoretical peak $900M/month
        "job_ratio":        (0.0, 0.55),          # theoretical max 55% AI ratio
        "trends":           (0, 100),             # Google Trends is already 0-100
        "github":           (0, 100),             # normalized index already 0-100
        "regulatory":       (0, 100),             # theoretical max ~100 cumulative docs
    }

    def normalize(key, value):
        lo, hi = ranges[key]
        if hi == lo:
            return 50.0
        if key == "employment":
            # Inverted: lower headcount = higher displacement
            return max(0, min(100, round((hi - value) / (hi - lo) * 100, 1)))
        else:
            return max(0, min(100, round((value - lo) / (hi - lo) * 100, 1)))

    monthly = []
    prev_score = None

    for i, date_label in enumerate(MONTHS):
        # Add some noise to raw values
        emp = round(employment_raw[i] + random.gauss(0, 2.5), 1)
        rev = round(rev_per_emp_raw[i] + random.gauss(0, 0.4), 1)
        vc = round(vc_funding_raw[i] + random.gauss(0, 15), 1)
        jr = round(job_ratio_raw[i] + random.gauss(0, 0.008), 3)
        tr = round(trends_raw[i] + random.gauss(0, 2), 0)
        gh = round(github_raw[i] + random.gauss(0, 2), 0)
        reg = round(regulatory_raw[i] + random.gauss(0, 1), 0)

        # Clamp to reasonable bounds
        emp = max(1480, emp)
        rev = max(18, rev)
        vc = max(80, vc)
        jr = max(0.03, jr)
        tr = max(15, min(100, tr))
        gh = max(35, min(100, gh))
        reg = max(1, reg)

        # Normalize each component
        emp_n = normalize("employment", emp)
        rev_n = normalize("rev_per_employee", rev)
        vc_n = normalize("vc_funding", vc)
        jr_n = normalize("job_ratio", jr)
        tr_n = normalize("trends", tr)
        gh_n = normalize("github", gh)
        reg_n = normalize("regulatory", reg)

        # Weighted score
        score = round(
            emp_n * WEIGHTS["employment"] +
            rev_n * WEIGHTS["rev_per_employee"] +
            vc_n * WEIGHTS["vc_funding"] +
            jr_n * WEIGHTS["job_ratio"] +
            tr_n * WEIGHTS["trends"] +
            gh_n * WEIGHTS["github"] +
            reg_n * WEIGHTS["regulatory"],
            1
        )

        phase_label, phase_range = get_phase(score)

        # Determine trend vs prior month
        if prev_score is None:
            trend = "flat"
        elif score > prev_score + 0.5:
            trend = "up"
        elif score < prev_score - 0.5:
            trend = "down"
        else:
            trend = "flat"

        prev_score = score

        monthly.append({
            "date": date_label,
            "score": score,
            "phase": phase_label,
            "phase_range": phase_range,
            "components": {
                "employment": {
                    "raw_value": emp,
                    "normalized": emp_n,
                    "weighted": round(emp_n * WEIGHTS["employment"], 2),
                },
                "rev_per_employee": {
                    "raw_value": rev,
                    "normalized": rev_n,
                    "weighted": round(rev_n * WEIGHTS["rev_per_employee"], 2),
                },
                "vc_funding": {
                    "raw_value": vc,
                    "normalized": vc_n,
                    "weighted": round(vc_n * WEIGHTS["vc_funding"], 2),
                },
                "job_ratio": {
                    "raw_value": jr,
                    "normalized": jr_n,
                    "weighted": round(jr_n * WEIGHTS["job_ratio"], 2),
                },
                "trends": {
                    "raw_value": tr,
                    "normalized": tr_n,
                    "weighted": round(tr_n * WEIGHTS["trends"], 2),
                },
                "github": {
                    "raw_value": gh,
                    "normalized": gh_n,
                    "weighted": round(gh_n * WEIGHTS["github"], 2),
                },
                "regulatory": {
                    "raw_value": reg,
                    "normalized": reg_n,
                    "weighted": round(reg_n * WEIGHTS["regulatory"], 2),
                },
            },
            "trend": trend,
        })

    return {
        "metadata": {
            "source": "Displacement Curve Composite",
            "last_updated": "2026-02-26",
            "mock": True,
            "version": "1.0",
        },
        "weights": WEIGHTS,
        "monthly": monthly,
        "events": EVENTS,
    }


# ---------------------------------------------------------------------------
# Main: write all Phase 4 mock data files
# ---------------------------------------------------------------------------

def main():
    print("Generating Phase 4 mock data for the Displacement Curve...\n")

    reg_data = generate_regulatory()
    write_json(reg_data, "regulatory/processed/guidance.json")

    composite_data = generate_composite()
    write_json(composite_data, "composite/displacement_index.json")

    # Print summary
    first = composite_data["monthly"][0]
    last = composite_data["monthly"][-1]
    print(f"\n  Composite Index: {first['score']} ({first['phase']}) -> {last['score']} ({last['phase']})")
    print(f"  Regulatory docs total: {reg_data['aggregate'][-1]['cumulative_documents']}")
    print(f"  Months generated: {len(composite_data['monthly'])}")
    print(f"  Quarters generated: {len(reg_data['aggregate'])}")

    print("\nPhase 4 mock data generation complete.")


if __name__ == "__main__":
    main()
