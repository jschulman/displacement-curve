#!/usr/bin/env python3
"""
Composite Displacement Index for the Displacement Curve.

Reads all 8 processed signal files, normalizes each to 0-100 within its
historical range, applies weights, and produces a single 0-100 composite
displacement score per month.

Signals and weights:
  employment       0.25  (BLS headcount - INVERTED: decline = displacement)
  rev_per_employee 0.20  (Earnings revenue per employee)
  vc_funding       0.15  (AI startup VC funding)
  job_ratio        0.15  (AI / traditional job posting ratio)
  trends           0.10  (Google Trends search interest)
  github           0.10  (GitHub AI activity index)
  regulatory       0.05  (Regulatory document count)

Phase labels:
   0-25  Pre-disruption
  26-50  Productivity
  51-75  Erosion
  76-100 Displacement

Usage:
  python normalizers/composite_index.py              # compute from signal files
  python normalizers/composite_index.py --mock       # generate mock composite
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Tests redirect reads/writes via DC_DATA_DIR; defaults to project data/.
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "composite", "displacement_index.json")

# Signal source files
SIGNAL_FILES = {
    "employment":      os.path.join(DATA_DIR, "bls", "processed", "employment.json"),
    "rev_per_employee": os.path.join(DATA_DIR, "earnings", "processed", "normalized.json"),
    "vc_funding":      os.path.join(DATA_DIR, "vc", "processed", "funding.json"),
    "job_ratio":       os.path.join(DATA_DIR, "jobs", "processed", "postings.json"),
    "trends":          os.path.join(DATA_DIR, "trends", "processed", "search_interest.json"),
    "github":          os.path.join(DATA_DIR, "github", "processed", "activity.json"),
    "regulatory":      os.path.join(DATA_DIR, "regulatory", "processed", "guidance.json"),
    "apprenticeship":  os.path.join(DATA_DIR, "apprenticeship", "processed", "collapse.json"),
}

# 2026-07 methodology audit — two signals retired from the score.
#
#   vc_funding (was 0.1275): EDGAR full-text search does not return offering amounts,
#     so all 46 matched Form D filings carry an unknown value and every one of the 17
#     quarters reported $0.0M. The signal contributed 0.0 in 44/44 months, which capped
#     the achievable score at 87.25 while the phase thresholds still assumed 100.
#     Retired rather than repaired: the keyword classifier is independently broken
#     (top match was an infrastructure fund), so recovering the amounts would have
#     produced precise figures for the wrong deals.
#
#   apprenticeship (was 0.15): Census ACS is annual and the latest release is 2024-01,
#     so the series was forward-filled flat at 5.7 for 30 consecutive months and read 0
#     in 13 others. Because it bypassed min-max normalization its raw range topped out
#     near 6 on a 0-100 scale, giving it 1.4% of realized influence against a 15%
#     nominal weight. Still collected and still shown on the dashboard — excluded from
#     the score until the next ACS release makes it a live series.
#
# Both are still loaded via SIGNAL_FILES/EXTRACTORS so the data remains available; only
# the scoring weights are removed. The remaining six are the original pre-apprenticeship
# weights renormalized over 0.7225 so the set sums to 1.0 and relative importance holds.
# Signal polarity. A signal is INVERTED when a RISING raw value means LESS
# displacement, so the normalizer must flip it before scoring.
#
#   employment   BLS professional & business services headcount. More people
#                employed = less displacement. Inverted (always was).
#   job_ratio    JOLTS openings index, Nov-2022 = 1.0. More job openings = less
#                displacement. NOT inverted until the 2026-07 audit — this was a
#                live sign error on 17.65% of the index. Professional-services
#                openings fell 0.987 -> 0.701 (a 29% collapse in labour demand,
#                the cleanest displacement signal in the set) and the index
#                scored that decline 75.5 -> 30.8, reading a collapsing job
#                market as displacement RECEDING. The bug entered when the
#                signal was honestly renamed from `ai_to_traditional_ratio`
#                (rising = more displacement) to JOLTS `openings_index`
#                (rising = less); the semantics flipped, the polarity didn't.
#
# Not inverted, verified in the same audit: rev_per_employee (more output per
# head = more displacement), trends, github, regulatory (more AI attention,
# activity, and regulatory response = more displacement).
#
# Polarity is now expressed ONLY in the ANCHORS table below, as zero > hundred.
# There is deliberately no separate invert flag: two sources of truth for the same
# property is precisely how the job_ratio error survived a rename.

# Fixed normalization anchors (2026-07 audit) — what 0 and 100 MEAN for each signal,
# declared a priori instead of derived from the observed range. `zero` is the raw
# measure that scores 0 (no displacement); `hundred` scores 100 (displacement
# complete). When zero > hundred the mapping inverts naturally, so polarity lives
# here and nowhere else.
#
# These thresholds are editorial judgments, not measurements, and they are the most
# arguable numbers in the project. They are declared in one table precisely so they
# can be challenged, cited, and changed deliberately rather than drifting silently
# with the data. Every one is stated in METHODOLOGY.
#
#   employment        % change vs 2022-11 (ChatGPT launch, the project's baseline).
#                     0 at +2% (sector still growing), 100 at -10% (a contraction
#                     with no post-war precedent in professional services).
#                     Currently -1.25%.
#   rev_per_employee  Multiple of the 2022-11 baseline. 0 at 1.0x, 100 at 1.5x —
#                     a 50% lift in output per head is the productivity signature
#                     the displacement thesis predicts. Currently 1.11x.
#   job_ratio         JOLTS openings, already indexed to 2022-11 = 1.0. 0 at 1.0
#                     (hiring at pre-AI levels), 100 at 0.5 (openings halved).
#                     Currently 0.70.
#   trends            Google Trends' native 0-100 scale, used as-is. Deliberately
#                     NOT rescaled to its observed max: search interest is nowhere
#                     near saturation and pretending otherwise would inflate the
#                     weakest signal in the set. Currently ~23.
#   github            New AI-tooling repositories per month (flow). 0 at none,
#                     100 at 5,000/month as a saturated-developer-attention
#                     ceiling. Currently ~3,200.
#   regulatory        AI guidance documents issued per quarter (flow). 0 at none,
#                     100 at 20/quarter across the seven tracked regulators.
#                     Currently 4-13.
ANCHORS = {
    "employment":       {"kind": "pct_vs_baseline",   "baseline_month": "2022-11", "zero": 2.0,   "hundred": -10.0},
    "rev_per_employee": {"kind": "ratio_vs_baseline", "baseline_month": "2022-11", "zero": 1.0,   "hundred": 1.5},
    "job_ratio":        {"kind": "absolute",                                       "zero": 1.0,   "hundred": 0.5},
    "trends":           {"kind": "absolute",                                       "zero": 0.0,   "hundred": 100.0},
    "github":           {"kind": "absolute",                                       "zero": 0.0,   "hundred": 5000.0},
    "regulatory":       {"kind": "absolute",                                       "zero": 0.0,   "hundred": 20.0},
}

WEIGHTS = {
    "employment": 0.2941,
    "rev_per_employee": 0.2353,
    "job_ratio": 0.1765,
    "trends": 0.1176,
    "github": 0.1176,
    "regulatory": 0.0589,
}

EVENTS = [
    {"date": "2022-11", "label": "ChatGPT Launch", "type": "ai_release"},
    {"date": "2023-03", "label": "GPT-4 Release", "type": "ai_release"},
    {"date": "2023-07", "label": "Claude 2 Launch", "type": "ai_release"},
    {"date": "2024-03", "label": "Claude 3 Launch", "type": "ai_release"},
    {"date": "2024-06", "label": "EU AI Act Final", "type": "regulatory"},
    {"date": "2024-11", "label": "GPT-4o Launch", "type": "ai_release"},
    {"date": "2025-02", "label": "Claude 3.5 Opus", "type": "ai_release"},
    {"date": "2025-06", "label": "Accenture AI Revenue $3B", "type": "earnings"},
    # Layoff events use an attribution_quality field to distinguish narrative-led
    # announcements from those corroborated by financial signals. See
    # METHODOLOGY.md: "Corporate AI Layoff Attribution".
    {
        "date": "2026-05",
        "label": "Coinbase -700 (14%) cites AI",
        "type": "layoff",
        "attribution_quality": "marketing",
    },
    {
        "date": "2026-05",
        "label": "Cloudflare -1,100 (~20%) AI restructuring",
        "type": "layoff",
        "attribution_quality": "validated",
    },
]

# Monthly axis starts 2022-11 (ChatGPT public release). The end month is
# determined dynamically from the latest signal data so the composite rolls
# forward automatically as new BLS / earnings / etc. arrive.
SERIES_START = "2022-11"


def _month_iter(start, end):
    """Yield 'YYYY-MM' strings from start through end inclusive."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y}-{m:02d}"
        m += 1
        if m == 13:
            m = 1
            y += 1


def _build_months(raw_series):
    """Latest month is anchored to BLS employment (the foundational monthly
    signal). Slower-cadence series are forward-filled in _forward_fill so the
    composite stays computable through the most recent BLS print."""
    employment = raw_series.get("employment", {})
    if not employment:
        return []
    latest = max(employment.keys())
    return list(_month_iter(SERIES_START, latest))


def _forward_fill(series, months):
    """Return a new dict that carries the most recent value forward into any
    month in `months` after the series' last observation. Lower-cadence
    signals (quarterly VC funding, regulatory, earnings) would otherwise drop
    to 0 once BLS data extends past their last quarter."""
    if not series:
        return {}
    sorted_dates = sorted(series.keys())
    filled = dict(series)
    last_known = sorted_dates[-1]
    last_val = series[last_known]
    for m in months:
        if m > last_known and m not in filled:
            filled[m] = last_val
    return filled


def get_phase(score):
    """Return phase label and range string for a given score."""
    if score <= 25:
        return "Pre-disruption", "0-25"
    elif score <= 50:
        return "Productivity", "26-50"
    elif score <= 75:
        return "Erosion", "51-75"
    else:
        return "Displacement", "76-100"


# ---------------------------------------------------------------------------
# Signal Extraction (Live Mode)
# ---------------------------------------------------------------------------

def load_json(path):
    """Load a JSON file, returning None if missing."""
    if not os.path.exists(path):
        print(f"  WARNING: Signal file not found: {path}")
        return None
    with open(path, "r") as f:
        return json.load(f)


def extract_monthly_employment(data):
    """Extract monthly headcount from BLS employment data."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("total_employment", entry.get("employment", 0))
    elif data and "series" in data:
        # Real BLS data: series.CES6000000001.data[].{date, value}.
        # CES6000000001 = supersector 60 "Professional and Business Services",
        # all employees in thousands, seasonally adjusted. Earlier code keyed
        # on CES5000000001 which is supersector 50 (Information) — wrong by
        # roughly 7x. CES5000000001 is accepted as a fallback for any data
        # collected before the ID fix.
        series_map = data["series"]
        chosen = series_map.get("CES6000000001") or series_map.get("CES5000000001")
        if chosen:
            for entry in chosen.get("data", []):
                values[entry["date"]] = entry["value"]
    elif data and "aggregate" in data:
        for entry in data["aggregate"]:
            values[entry.get("date", "")] = entry.get("total_employment", 0)
    return values


def extract_monthly_rev_per_employee(data):
    """Extract avg revenue per employee from earnings normalized data."""
    values = {}
    if data and "aggregate" in data:
        # Quarterly data - expand to months
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            rev_pe = entry.get("avg_rev_per_employee")
            if rev_pe is None:
                continue
            # Assign to each month in the quarter
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = rev_pe
    return values


def extract_monthly_vc_funding(data):
    """Extract quarterly VC funding, expand to monthly."""
    values = {}
    if data and "aggregate" in data:
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            funding = entry.get("total_funding_mm") or 0
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = funding / 3  # Spread quarterly over months
    return values


def extract_monthly_job_ratio(data):
    """Extract the JOLTS openings index from postings data. JOLTS doesn't
    publish an AI-vs-traditional breakdown, so this is really a labor-demand
    index keyed to Nov 2022 = 1.0. Reads `openings_index` (current) and
    falls back to `ai_to_traditional_ratio` (legacy name)."""
    values = {}
    if data and "monthly" in data:
        for entry in data["monthly"]:
            val = entry.get("openings_index")
            if val is None:
                val = entry.get("ai_to_traditional_ratio")
            if val is not None:
                values[entry["date"]] = val
    return values


def extract_monthly_trends(data):
    """Extract Google Trends search interest, averaging across category
    composites. The trends collector outputs
    {categories: {<cat>: {composite: [{date, value}]}}} — no top-level array."""
    values = {}
    if not data:
        return values

    categories = data.get("categories", {})
    if categories:
        by_date = {}
        for cat_data in categories.values():
            composite = cat_data.get("composite") or cat_data.get("data") or []
            for point in composite:
                date = point.get("date")
                val = point.get("value")
                if date and val is not None:
                    by_date.setdefault(date, []).append(val)
        for date, vals in by_date.items():
            values[date] = round(sum(vals) / len(vals), 1)
        return values

    # Fall back to legacy shapes used in some mock files
    if "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("interest", entry.get("value", 0))
    elif "aggregate" in data:
        for entry in data["aggregate"]:
            values[entry.get("date", "")] = entry.get("interest", 0)
    return values


def extract_monthly_github(data):
    """Extract GitHub activity index from the aggregate cumulative-stars series.
    The github collector outputs
    {categories: {...}, aggregate: [{date, total_new_repos, total_stars, ...}]}.
    The composite previously looked only at a non-existent top-level `monthly`
    key, so this signal contributed zero to every score."""
    values = {}
    if not data:
        return values

    # FLOW, not stock (2026-07 audit). This previously read `total_stars`, which the
    # collector accumulates — a monotone ratchet. Fed to a min-max normalizer, a
    # counter that can only rise pins its latest month to ~100 by construction and
    # carries no directional information at all. `total_new_repos` is the genuine
    # per-month flow: new AI-tooling repositories created that month.
    agg = data.get("aggregate", [])
    if agg:
        for entry in agg:
            date = entry.get("date")
            new_repos = entry.get("total_new_repos")
            if date and new_repos is not None:
                values[date] = new_repos
        return values

    # Legacy / mock shape
    if "monthly" in data:
        for entry in data["monthly"]:
            values[entry["date"]] = entry.get("activity_index", entry.get("stars", 0))
    return values


def extract_monthly_regulatory(data):
    """Regulatory guidance ISSUED PER QUARTER, expanded to months.

    FLOW, not stock (2026-07 audit). This previously read `cumulative_documents`,
    a monotone counter that min-max normalization pins to ~100 at the latest month
    regardless of whether regulators are accelerating or going quiet. The rate of
    new guidance is the signal; the running total is an artifact of how long the
    project has been collecting.

    Caveat retained from the audit: the zeros before 2025-Q3 are a feed-depth
    artifact, not regulatory silence — the collector reads live RSS feeds that only
    carry recent items, so NIST's AI RMF (Jan 2023) and the EU AI Act (2024) fall
    inside the all-zero window. Fixing that requires a document ledger, not a
    normalization change; tracked separately.
    """
    values = {}
    if data and "aggregate" in data:
        for entry in data["aggregate"]:
            q = entry.get("quarter", "")
            if not q:
                continue
            year = int(q[:4])
            qn = int(q[-1])
            docs = entry.get("total_documents")
            if docs is None:
                continue
            for m in range(1, 4):
                month_num = (qn - 1) * 3 + m
                date_str = f"{year}-{month_num:02d}"
                values[date_str] = docs
    return values


def extract_monthly_apprenticeship(data):
    """Apprenticeship signal = CROSSOVER-PROGRESS toward the inflection, on the Census
    youth-share (data/apprenticeship/processed/collapse.json, youth_share_u25).

    Returns a 0-100 scale = how far the youth share has fallen from its 2015-2019
    baseline toward the 50% threshold ('the college hire is the exception'). 0 = at
    baseline (apprenticeship intact), 100 = halved (crossover reached). This is the
    SAME logic as the Apprenticeship Inflection Distance panel, so the composite stays
    coherent with it. Crucially it is NOT min-max normalized downstream — a near-flat
    youth share correctly contributes ~0, instead of being stretched into a false
    high reading. Higher progress = more displacement (no inversion)."""
    if not data or "monthly" not in data:
        return {}
    series = {}
    for e in data["monthly"]:
        v = e.get("youth_share_u25", e.get("value"))
        if v is not None:
            series[e["date"]] = v
    if not series:
        return {}
    base = [v for k, v in series.items() if k[:4] in ("2015", "2016", "2017", "2018", "2019")]
    baseline = (sum(base) / len(base)) if base else max(series.values())
    span = baseline - baseline * 0.50  # baseline -> 50%-of-baseline threshold
    out = {}
    for date, v in series.items():
        prog = 0.0 if span <= 0 else (baseline - v) / span * 100.0
        out[date] = round(max(0.0, min(100.0, prog)), 1)
    return out


EXTRACTORS = {
    "employment": extract_monthly_employment,
    "rev_per_employee": extract_monthly_rev_per_employee,
    "vc_funding": extract_monthly_vc_funding,
    "job_ratio": extract_monthly_job_ratio,
    "trends": extract_monthly_trends,
    "github": extract_monthly_github,
    "regulatory": extract_monthly_regulatory,
    "apprenticeship": extract_monthly_apprenticeship,
}


def _baseline_value(values, month):
    """Raw value at the declared baseline month, or None if it isn't present.

    Deliberately does NOT fall back to the earliest available month. An earlier
    draft did, and it silently re-scaled the entire series whenever the baseline
    was missing — reintroducing the exact look-ahead defect anchors exist to
    remove. A missing baseline is a data problem and must surface as one.
    """
    if not values:
        return None
    return values.get(month)


def normalize_to_anchors(values, anchor):
    """Map a raw series to 0-100 against FIXED anchors.

    Replaces min-max-over-observed-range (2026-07 audit). Min-max had three
    defects, all fatal for a published index:

      1. Retroactive rewriting. lo/hi were recomputed from the whole series every
         run, so each new extreme silently restated every previously published
         month. A weekly run rewrote all 44 months; a score screenshotted last
         month could not be reproduced this month.
      2. Look-ahead bias. The score for month M depended on data from months
         after M, so no value was knowable at the time it described.
      3. Implicit re-weighting. A signal's influence became a function of its
         observed range, not its assigned weight — which is how a 0.15-weight
         signal ended up with 1.4% of realized influence.

    Anchors fix all three: `zero` and `hundred` are declared a priori, so a
    month's score depends only on that month's data and never changes.

    Polarity is carried by the anchors themselves — when `zero` > `hundred`
    (employment, job_ratio) the mapping inverts naturally. There is no separate
    invert flag to fall out of sync with a renamed signal, which is exactly how
    the job_ratio sign error survived.

    Returns (normalized, zero, hundred). Values are clamped to [0, 100]; an
    excursion past an anchor is reported via the clamp count, not by silently
    rescaling everything else.
    """
    if not values:
        return {}, None, None

    kind = anchor["kind"]
    zero, hundred = anchor["zero"], anchor["hundred"]

    if kind in ("pct_vs_baseline", "ratio_vs_baseline"):
        base = _baseline_value(values, anchor["baseline_month"])
        if not base:
            print(
                f"  ERROR: baseline month {anchor['baseline_month']} missing from series "
                f"— cannot normalize against an absent baseline; signal dropped"
            )
            return {}, zero, hundred

    normalized = {}
    for date, val in values.items():
        if kind == "pct_vs_baseline":
            measure = (val - base) / base * 100.0
        elif kind == "ratio_vs_baseline":
            measure = val / base
        else:
            measure = val
        score = (measure - zero) / (hundred - zero) * 100.0
        normalized[date] = round(max(0.0, min(100.0, score)), 1)

    return normalized, zero, hundred


def _run_health_gate(allow_degraded):
    """Refuse to compute a published score from broken inputs.

    The composite is what the audit caught silently averaging in a dead signal, so
    the gate lives here, not only in CI: no path — cron, manual, or a future caller —
    can publish a number without every scored signal passing. `--allow-degraded`
    exists as a deliberate, logged override for local experimentation; it must never
    be the default in a workflow.
    """
    import validate  # local import: validate.py imports this module

    health = validate.validate()
    if health["gate"] == "pass":
        print(f"  Health gate: PASS ({health['as_of']})")
        return
    failures = ", ".join(health["scored_failures"])
    if allow_degraded:
        print(f"  Health gate: FAIL ({failures}) — proceeding under --allow-degraded")
        return
    print(f"  Health gate: FAIL — scored signals broken: {failures}")
    print("  Refusing to publish a composite from broken inputs. "
          "Fix the collector, or re-run with --allow-degraded to override.")
    sys.exit(1)


def compute_composite_from_signals(allow_degraded=False):
    """Load all signal files, normalize, weight, and produce composite index."""
    _run_health_gate(allow_degraded)

    print("  Loading signal files...")

    # Load all signal data
    signal_data = {}
    for key, path in SIGNAL_FILES.items():
        signal_data[key] = load_json(path)

    # Extract monthly series for each signal
    raw_series = {}
    for key, extractor in EXTRACTORS.items():
        raw_series[key] = extractor(signal_data[key])
        print(f"    {key}: {len(raw_series[key])} monthly values")

    # Normalize each series to 0-100
    norm_series = {}
    for key in WEIGHTS:
        if key == "apprenticeship":
            # Already a 0-100 crossover-progress scale (see extractor). Do NOT min-max
            # normalize: youth-share is near-flat, and min-max would amplify that noise
            # into a false ~80/100 reading that contradicts the inflection panel.
            norm_series[key] = {d: max(0.0, min(100.0, v)) for d, v in raw_series.get(key, {}).items()}
            print(f"    {key}: crossover-progress (raw 0-100, no min-max)")
            continue
        norm_series[key], zero, hundred = normalize_to_anchors(
            raw_series.get(key, {}), ANCHORS[key]
        )
        print(f"    {key} anchors: 0 = {zero}, 100 = {hundred}")

    # Build monthly composite. Anchor the month axis to BLS, then forward-fill
    # slower-cadence signals so months past their last reported quarter still
    # contribute their most recent value rather than dropping to 0.
    months = _build_months(raw_series)
    print(f"  Month axis: {months[0]} .. {months[-1]} ({len(months)} months)")

    for key in raw_series:
        raw_series[key] = _forward_fill(raw_series[key], months)

    # Re-normalize after forward-fill so normalized lookups stay in range.
    norm_series = {}
    for key in WEIGHTS:
        if key == "apprenticeship":
            norm_series[key] = {d: max(0.0, min(100.0, v)) for d, v in raw_series.get(key, {}).items()}
            continue
        norm_series[key], _, _ = normalize_to_anchors(
            raw_series.get(key, {}), ANCHORS[key]
        )

    monthly = []
    prev_score = None

    for date_label in months:
        components = {}
        score = 0.0

        for key in WEIGHTS:
            raw_val = raw_series.get(key, {}).get(date_label, 0)
            norm_val = norm_series.get(key, {}).get(date_label, 0)
            weighted = round(norm_val * WEIGHTS[key], 2)

            components[key] = {
                "raw_value": raw_val,
                "normalized": norm_val,
                "weighted": weighted,
            }
            score += weighted

        score = round(score, 1)
        phase_label, phase_range = get_phase(score)

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
            "components": components,
            "trend": trend,
        })

    return {
        "metadata": {
            "source": "Displacement Curve Composite",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "mock": False,
            "version": "1.0",
        },
        "weights": WEIGHTS,
        "monthly": monthly,
        "events": EVENTS,
    }


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def generate_mock():
    """Delegate to the central Phase 4 mock generator for composite data."""
    sys.path.insert(0, os.path.join(BASE_DIR, "data"))
    from generate_mock_phase4 import generate_composite
    return generate_composite()


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

def save_snapshot(data):
    """Write an immutable dated copy of each published index.

    With min-max normalization a re-run silently restated every historical month,
    so a score cited last week could not be reproduced this week. Fixed anchors
    make scores stable in principle; snapshots make that auditable in practice —
    if a published number ever does move, the diff is on disk.

    Named by the newest month covered rather than by wall-clock date, so re-running
    the same inputs overwrites its own snapshot instead of accumulating duplicates.
    """
    snap_dir = os.path.join(DATA_DIR, "composite", "snapshots")
    os.makedirs(snap_dir, exist_ok=True)
    latest = data["monthly"][-1]["date"] if data.get("monthly") else "empty"
    path = os.path.join(snap_dir, f"displacement_index_through_{latest}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Snapshot: {os.path.relpath(path, BASE_DIR)}")


def report_influence(data):
    """Compare each signal's NOMINAL weight to its REALIZED influence.

    Realized influence is the share of total across-signal movement a signal
    actually supplies — its weighted contribution's range over the series divided
    by the sum of all such ranges. A weight table is a claim about influence, and
    before the 2026-07 audit that claim was false by an order of magnitude: the
    apprenticeship signal carried 15% nominal weight and delivered 1.4%.

    A gap is not automatically a defect — a signal that genuinely holds steady
    within its anchor band SHOULD contribute stably rather than being stretched to
    fill 0-100, which is what min-max used to do. The point is that the gap is now
    visible every run instead of discoverable only by audit.
    """
    weights, monthly = data.get("weights", {}), data.get("monthly", [])
    if not weights or not monthly:
        return
    spans = {
        k: max(x["components"][k]["weighted"] for x in monthly)
        - min(x["components"][k]["weighted"] for x in monthly)
        for k in weights
    }
    total = sum(spans.values())
    print("\n  Nominal weight vs realized influence:")
    for key in sorted(weights, key=lambda k: -weights[k]):
        realized = (spans[key] / total * 100) if total else 0.0
        nominal = weights[key] * 100
        flag = "  <-- inert" if realized < 1.0 else ""
        print(f"    {key:18s} nominal {nominal:5.2f}%   realized {realized:5.1f}%{flag}")


def main():
    parser = argparse.ArgumentParser(description="Composite Displacement Index")
    parser.add_argument("--mock", action="store_true", help="Generate mock composite data directly")
    parser.add_argument("--allow-degraded", action="store_true",
                        help="Publish even if the signal health gate fails (logged override)")
    args = parser.parse_args()

    print("Composite Displacement Index")
    print(f"  Mode: {'MOCK' if args.mock else 'LIVE (from signal files)'}\n")

    if args.mock:
        data = generate_mock()
    else:
        data = compute_composite_from_signals(allow_degraded=args.allow_degraded)

    save_json(data, OUTPUT_PATH)
    if not args.mock:
        save_snapshot(data)
        report_influence(data)

    # Print summary
    first = data["monthly"][0]
    last = data["monthly"][-1]
    print(f"\n  Score trajectory: {first['score']} ({first['phase']}) -> {last['score']} ({last['phase']})")
    print(f"  Months: {len(data['monthly'])}")
    print(f"  Events: {len(data['events'])}")
    print("\nComposite index generation complete.")


if __name__ == "__main__":
    main()
