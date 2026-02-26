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

        total_rev = q.get("total_revenue_mm") or 0
        ai_rev = q.get("ai_revenue_mm") or 0
        headcount = q.get("headcount") or 0

        # AI percentage of total revenue
        if total_rev > 0 and q.get("ai_revenue_mm") is not None:
            entry["ai_pct"] = round(ai_rev / total_rev * 100, 2)
        else:
            entry["ai_pct"] = None

        # Revenue per employee (thousands per employee per quarter)
        if headcount > 0 and total_rev > 0:
            entry["revenue_per_employee"] = round(
                (total_rev * 1_000_000) / headcount / 1000, 1
            )
        else:
            entry["revenue_per_employee"] = None

        # Relabeling index (requires previous quarter with ai_revenue data)
        if i > 0 and q.get("ai_revenue_mm") is not None:
            prev = quarterly_data[i - 1]
            prev_ai = prev.get("ai_revenue_mm") or 0
            prev_total = prev.get("total_revenue_mm") or 0
            ai_growth = compute_growth_rate(ai_rev, prev_ai)
            total_growth = compute_growth_rate(total_rev, prev_total)

            if abs(total_growth) > 0.001:
                relabel_idx = ai_growth / total_growth
            else:
                relabel_idx = abs(ai_growth) * 100 if ai_growth > 0 else 0.0

            entry["relabeling_index"] = round(max(0, relabel_idx), 2)
            entry["relabeling_flag"] = entry["relabeling_index"] > RELABELING_THRESHOLD
        else:
            entry["relabeling_index"] = None
            entry["relabeling_flag"] = False

        normalized.append(entry)

    return normalized


def compute_aggregate(firms):
    """Recompute aggregate statistics from normalized firm data."""
    # Collect all quarters across all firms
    all_quarters = set()
    for ticker, firm in firms.items():
        for q in firm["quarterly"]:
            all_quarters.add(q["quarter"])
    quarters = sorted(all_quarters)

    # Build lookup by (ticker, quarter) for easy access
    firm_by_quarter = {}
    for ticker, firm in firms.items():
        for q in firm["quarterly"]:
            firm_by_quarter[(ticker, q["quarter"])] = q

    aggregate = []
    for q_label in quarters:
        total_ai = 0
        ai_pcts = []
        relabel_indices = []
        rev_per_emps = []

        for ticker in firms:
            q = firm_by_quarter.get((ticker, q_label))
            if q is None:
                continue
            if q.get("ai_revenue_mm") is not None:
                total_ai += q["ai_revenue_mm"]
            if q.get("ai_pct") is not None:
                ai_pcts.append(q["ai_pct"])
            if q.get("relabeling_index") is not None:
                relabel_indices.append(q["relabeling_index"])
            if q.get("revenue_per_employee") is not None:
                rev_per_emps.append(q["revenue_per_employee"])

        aggregate.append({
            "quarter": q_label,
            "total_ai_revenue_mm": total_ai if total_ai > 0 else None,
            "avg_ai_pct": round(sum(ai_pcts) / len(ai_pcts), 1) if ai_pcts else None,
            "avg_relabeling_index": round(sum(relabel_indices) / len(relabel_indices), 1) if relabel_indices else None,
            "avg_rev_per_employee": round(sum(rev_per_emps) / len(rev_per_emps), 1) if rev_per_emps else None,
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
        ai_pct_str = f"{last_q['ai_pct']}%" if last_q.get('ai_pct') is not None else "N/A"
        relabel_str = last_q.get('relabeling_index') or "N/A"
        print(f"    AI %: {ai_pct_str}  |  Relabeling Index: {relabel_str}")
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
