#!/usr/bin/env python3
"""
Earnings Normalizer for the Displacement Curve.

Reads data/earnings/processed/revenue.json and computes derived fields:
  - ai_pct:               AI revenue as % of total revenue
  - relabeling_index:     AI rev growth rate / total rev growth rate (>3x = likely relabeling)
  - revenue_per_employee: total_revenue / headcount (in thousands per employee per quarter)

Outputs data/earnings/processed/normalized.json with the same structure
plus computed fields added to each quarterly entry and aggregate.

Usage:
  python normalizers/earnings_normalizer.py
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, "data", "earnings", "processed", "revenue.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "earnings", "processed", "normalized.json")

RELABELING_THRESHOLD = 3.0  # Growth rate ratio above this = likely relabeling


# ---------------------------------------------------------------------------
# Normalization Logic
# ---------------------------------------------------------------------------

def compute_growth_rate(current, previous):
    """Compute percentage growth rate, handling zero/near-zero denominators."""
    if abs(previous) < 0.01:
        return 0.0
    return (current - previous) / previous


def normalize_firm(quarterly_data):
    """Add computed fields to a firm's quarterly data."""
    normalized = []

    for i, q in enumerate(quarterly_data):
        entry = dict(q)  # shallow copy

        # AI percentage of total revenue
        if q["total_revenue_mm"] > 0:
            entry["ai_pct"] = round(q["ai_revenue_mm"] / q["total_revenue_mm"] * 100, 2)
        else:
            entry["ai_pct"] = 0.0

        # Revenue per employee (thousands per employee per quarter)
        if q["headcount"] > 0:
            entry["revenue_per_employee"] = round(
                (q["total_revenue_mm"] * 1_000_000) / q["headcount"] / 1000, 1
            )
        else:
            entry["revenue_per_employee"] = 0.0

        # Relabeling index (requires previous quarter)
        if i > 0:
            prev = quarterly_data[i - 1]
            ai_growth = compute_growth_rate(q["ai_revenue_mm"], prev["ai_revenue_mm"])
            total_growth = compute_growth_rate(q["total_revenue_mm"], prev["total_revenue_mm"])

            if abs(total_growth) > 0.001:
                relabel_idx = ai_growth / total_growth
            else:
                # Total rev barely moved but AI rev grew -- strong relabeling signal
                relabel_idx = abs(ai_growth) * 100 if ai_growth > 0 else 0.0

            entry["relabeling_index"] = round(max(0, relabel_idx), 2)
            entry["relabeling_flag"] = entry["relabeling_index"] > RELABELING_THRESHOLD
        else:
            # First quarter: no prior data for comparison
            entry["relabeling_index"] = 1.0
            entry["relabeling_flag"] = False

        normalized.append(entry)

    return normalized


def compute_aggregate(firms):
    """Recompute aggregate statistics from normalized firm data."""
    # Determine quarter labels from first firm
    first_ticker = next(iter(firms))
    quarters = [q["quarter"] for q in firms[first_ticker]["quarterly"]]

    aggregate = []
    for i, q_label in enumerate(quarters):
        total_ai = 0
        ai_pcts = []
        relabel_indices = []
        rev_per_emps = []

        for ticker, firm in firms.items():
            q = firm["quarterly"][i]
            total_ai += q["ai_revenue_mm"]
            ai_pcts.append(q["ai_pct"])
            relabel_indices.append(q["relabeling_index"])
            rev_per_emps.append(q["revenue_per_employee"])

        n = len(firms)
        aggregate.append({
            "quarter": q_label,
            "total_ai_revenue_mm": total_ai,
            "avg_ai_pct": round(sum(ai_pcts) / n, 1),
            "avg_relabeling_index": round(sum(relabel_indices) / n, 1),
            "avg_rev_per_employee": round(sum(rev_per_emps) / n, 1),
            "firms_flagged_relabeling": sum(
                1 for idx in relabel_indices if idx > RELABELING_THRESHOLD
            ),
        })

    return aggregate


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Earnings Normalizer")
    print(f"  Input:  {INPUT_PATH}")
    print(f"  Output: {OUTPUT_PATH}\n")

    if not os.path.exists(INPUT_PATH):
        print(f"  ERROR: Input file not found: {INPUT_PATH}")
        print("  Run the earnings collector first (or generate mock data).")
        sys.exit(1)

    with open(INPUT_PATH, "r") as f:
        data = json.load(f)

    # Normalize each firm
    normalized_firms = {}
    for ticker, firm in data["firms"].items():
        normalized_quarterly = normalize_firm(firm["quarterly"])
        normalized_firms[ticker] = {
            "name": firm["name"],
            "quarterly": normalized_quarterly,
        }

        # Print summary for this firm
        last_q = normalized_quarterly[-1]
        print(f"  {ticker} ({firm['name']}):")
        print(f"    AI %: {last_q['ai_pct']}%  |  Relabeling Index: {last_q['relabeling_index']}")
        flagged = sum(1 for q in normalized_quarterly if q.get("relabeling_flag"))
        if flagged > 0:
            print(f"    WARNING: {flagged}/{len(normalized_quarterly)} quarters flagged for relabeling")

    # Recompute aggregate
    aggregate = compute_aggregate(normalized_firms)

    output = {
        "metadata": {
            "source": data["metadata"]["source"],
            "last_updated": data["metadata"]["last_updated"],
            "mock": data["metadata"].get("mock", False),
            "normalized": True,
            "relabeling_threshold": RELABELING_THRESHOLD,
        },
        "firms": normalized_firms,
        "aggregate": aggregate,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)} bytes)")
    print("\nNormalization complete.")


if __name__ == "__main__":
    main()
