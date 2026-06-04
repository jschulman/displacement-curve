#!/usr/bin/env python3
"""
The Displacement Curve - Apprenticeship Inflection Distance Estimator

The analog of quantum-qanary's Q-Day Distance: estimates how many years until the
college-hire job description is the EXCEPTION rather than the norm.

Crossover definition (Jay, 2026-06-04): the entry tier has structurally HALVED — the
youth share of professional-services employment falls to 50% of its 2015-2019 pre-AI
baseline. At that point the bottom-of-pyramid apprenticeship hire is no longer the
modal hire; it's the exception.

Method (mirrors qday_distance.py — anchor-and-modify, NOT naive extrapolation, because
the lagging demographic is still flat and would extrapolate to 'never'):
  - BASE anchor: forecast consensus for when AI structurally cuts entry professional
    work (residency-thesis window + analyst future-of-work timelines).
  - MODIFIERS nudge the timeline:
      * crossover progress (how far youth-share has moved toward the 50% line)
      * youth-share trajectory (declining compresses; flat pushes out)
      * JOLTS hires-rate trajectory (leading demand; falling compresses)
      * composite displacement score / phase (Erosion+ compresses)
  - midpoint = base_years * weighted_composite_modifier; +/-30% band.
  - Caveat: unlike Q-Day, this inflection is a CHOICE, not physics — firms can preserve
    the apprenticeship deliberately (the residency model). Treat as trajectory, not fate.

Usage:
  python normalizers/inflection_distance.py
"""

import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "composite")

# Forecast anchor — credible target years for the entry-hire inflection. The "vendor
# roadmap consensus" analog. Externalize to data/forecasts/ later; embedded for now.
FORECASTS = [
    {"source": "Residency thesis — hiring slows", "year": 2028, "weight": 2.0},
    {"source": "Residency thesis — AI-native cohort at manager", "year": 2030, "weight": 2.5},
    {"source": "Residency thesis — pipeline crisis visible", "year": 2032, "weight": 2.0},
    {"source": "Future-of-work analyst consensus (prof. services)", "year": 2031, "weight": 1.5},
]
BASELINE_YEARS = ("2015", "2016", "2017", "2018", "2019")
CROSSOVER_FRACTION = 0.50  # entry tier at 50% of pre-AI baseline = "the exception"


def load_json(rel):
    p = os.path.join(BASE_DIR, rel)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  [WARN] {rel}: {e}", file=sys.stderr)
        return None


def youth_series(apprenticeship_data):
    """Return {year: under-25 share} from the youth-share signal."""
    out = {}
    for m in (apprenticeship_data or {}).get("monthly", []):
        yr = str(m.get("date", ""))[:4]
        v = m.get("youth_share_u25", m.get("value"))
        if yr and v is not None:
            out[yr] = v
    return out


def crossover_component(apprenticeship_data):
    """Progress toward the 50%-of-baseline crossover, on the lagging youth-share."""
    ys = youth_series(apprenticeship_data)
    base_vals = [ys[y] for y in BASELINE_YEARS if y in ys]
    if not base_vals or not ys:
        return {"baseline": None, "threshold": None, "current": None, "progress_pct": 0.0, "trajectory": "unknown"}
    baseline = sum(base_vals) / len(base_vals)
    threshold = baseline * CROSSOVER_FRACTION
    latest_year = max(ys.keys())
    current = ys[latest_year]
    span = baseline - threshold
    progress = max(0.0, min(1.0, (baseline - current) / span)) if span else 0.0
    # Trajectory: recent 3-year slope vs baseline.
    recent = sorted(ys.items())[-3:]
    slope = (recent[-1][1] - recent[0][1]) if len(recent) >= 2 else 0.0
    trajectory = "declining" if slope < -0.2 else ("flat" if abs(slope) <= 0.2 else "rising")
    # Express shares as percentages for readability (source values are fractions).
    return {"baseline": round(baseline * 100, 2), "threshold": round(threshold * 100, 2),
            "current": round(current * 100, 2), "current_year": latest_year,
            "progress_pct": round(progress * 100, 1), "trajectory": trajectory}


def hires_trajectory_component(jobs_data):
    """JOLTS hires-rate: latest hires_index vs trailing-6. Falling = leading toward inflection."""
    monthly = [m for m in (jobs_data or {}).get("monthly", []) if m.get("hires_index") is not None]
    if len(monthly) < 7:
        return {"hires_index_latest": None, "trailing": None, "falling": None}
    latest = monthly[-1]["hires_index"]
    trailing = sum(m["hires_index"] for m in monthly[-7:-1]) / 6
    return {"hires_index_latest": round(latest, 3), "trailing": round(trailing, 3), "falling": latest < trailing}


def composite_component(composite_data):
    """Latest composite displacement score + phase."""
    months = (composite_data or {}).get("monthly", []) or (composite_data or {}).get("series", [])
    if not months:
        return {"score": None, "phase": None}
    last = months[-1]
    return {"score": last.get("score"), "phase": last.get("phase", last.get("phase_label"))}


def estimate(crossover, hires, composite):
    current_year = datetime.now().year
    # Base anchor: weighted forecast consensus.
    wsum = sum(f["year"] * f["weight"] for f in FORECASTS)
    wtot = sum(f["weight"] for f in FORECASTS)
    anchor_year = round(wsum / wtot)
    base_years = max(1, anchor_year - current_year)

    # Crossover-progress modifier: very early (<10%) pushes the estimate out (like qday's
    # factoring <5% -> 1.5). Far along compresses.
    p = crossover["progress_pct"] / 100.0
    if p < 0.10:
        prog_mod = 1.4
    elif p < 0.25:
        prog_mod = 1.2
    elif p < 0.50:
        prog_mod = 1.0
    else:
        prog_mod = 0.7

    # Trajectory modifier: flat lagging demographic = not started yet -> push out.
    traj_mod = {"declining": 0.85, "flat": 1.15, "rising": 1.3, "unknown": 1.1}[crossover["trajectory"]]

    # Leading hires modifier: falling hires compresses.
    hires_mod = 0.9 if hires.get("falling") else 1.05

    # Composite phase modifier.
    phase = (composite.get("phase") or "").lower()
    if "displacement" in phase:
        comp_mod = 0.8
    elif "erosion" in phase:
        comp_mod = 0.9
    elif "productivity" in phase:
        comp_mod = 1.0
    else:
        comp_mod = 1.1

    weights = {"prog": 0.35, "traj": 0.30, "hires": 0.20, "comp": 0.15}
    composite_modifier = (prog_mod * weights["prog"] + traj_mod * weights["traj"]
                          + hires_mod * weights["hires"] + comp_mod * weights["comp"])

    midpoint = round(base_years * composite_modifier, 1)
    spread = max(2.0, midpoint * 0.3)
    low, high = max(1, round(midpoint - spread / 2)), round(midpoint + spread / 2)
    return {
        "anchor_year": anchor_year, "base_years": base_years,
        "composite_modifier": round(composite_modifier, 3),
        "midpoint_years": midpoint, "low_years": low, "high_years": high,
        "crossover_year_low": current_year + low, "crossover_year_mid": round(current_year + midpoint),
        "crossover_year_high": current_year + high,
        "modifiers": {"progress": prog_mod, "trajectory": traj_mod, "hires": hires_mod, "composite": comp_mod},
    }


def main():
    appr = load_json("data/apprenticeship/processed/collapse.json")
    jobs = load_json("data/jobs/processed/postings.json")
    comp = load_json("data/composite/displacement_index.json")

    crossover = crossover_component(appr)
    hires = hires_trajectory_component(jobs)
    composite = composite_component(comp)
    est = estimate(crossover, hires, composite)

    print("Apprenticeship Inflection Distance")
    print(f"  Crossover: youth-share {crossover['current']}% (baseline {crossover['baseline']}%, "
          f"threshold {crossover['threshold']}%) -> {crossover['progress_pct']}% there, trajectory {crossover['trajectory']}")
    print(f"  Anchor year (forecast consensus): {est['anchor_year']}  | composite modifier {est['composite_modifier']}")
    print(f"  ESTIMATE: college-hire JD becomes the exception ~{est['crossover_year_low']}-{est['crossover_year_high']} "
          f"(midpoint {est['crossover_year_mid']}, {est['midpoint_years']} yrs out)")

    out = {
        "metadata": {"last_updated": datetime.now().strftime("%Y-%m-%d")},
        "crossover_definition": f"youth share of professional-services employment falls to {int(CROSSOVER_FRACTION*100)}% of its {BASELINE_YEARS[0]}-{BASELINE_YEARS[-1]} baseline",
        "estimate": est,
        "components": {"crossover": crossover, "hires_trajectory": hires, "composite": composite},
        "caveat": ("Unlike Q-Day, this inflection is a choice, not physics. Firms can "
                   "deliberately preserve the apprenticeship (the residency model). This is a "
                   "trajectory on current behavior, not a fixed date — and the lagging "
                   "demographic has not yet begun to move."),
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "inflection_distance.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\n  wrote {os.path.join(OUTPUT_DIR, 'inflection_distance.json')}")


if __name__ == "__main__":
    main()
