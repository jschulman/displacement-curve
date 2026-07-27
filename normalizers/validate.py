#!/usr/bin/env python3
"""
Signal health gate for the Displacement Curve.

WHY THIS EXISTS
---------------
The 2026-07 audit found a signal (VC funding) that had contributed exactly zero to
the published index for 44 consecutive months while every CI run reported success.
The collector ran, wrote a valid JSON file, exited 0 — and the number it produced was
garbage that the composite silently averaged in as a real floor reading. Green CI
carried no information about whether the data was any good.

This module is the missing gate. It validates the series each scored signal ACTUALLY
CONTRIBUTES to the composite — by re-running the composite's own extractors against the
live files — and fails loudly when a signal is empty, stalled, or entirely zero. It is
designed so that it CANNOT be satisfied by a valid-but-empty file: an empty extract is a
failure, not a pass.

WHAT IT CANNOT BE FOOLED BY
---------------------------
- A file that exists and parses but extracts to nothing  -> caught by `present`.
- A file whose values are all zero (the VC failure mode)  -> caught by `has_nonzero`.
- A collector that stopped updating weeks ago             -> caught by `fresh`
  (and freshness is measured on the newest NON-FUTURE month, so quarterly signals
  whose expansion runs past today can't spoof it).
- A signal quietly dropping most of its history           -> caught by `min_records`.

"Legitimately zero" vs "collector failed" is the distinction the audit demanded. It is
resolved by two separate tests: a signal may have zero-valued months (regulatory and
trends both do, early on, for documented reasons) as long as it has SOME non-zero value
somewhere (`has_nonzero`) AND its newest observation is recent (`fresh`). A dead
collector fails one or both; a legitimately-sparse one passes both.

USAGE
-----
  python normalizers/validate.py                 # report; exit 1 if a scored signal fails
  python normalizers/validate.py --report-only   # always exit 0 (for local inspection)

Writes data/composite/signal_health.json on every run.
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import composite_index as ci  # noqa: E402  reuse the exact extractors the composite scores

HEALTH_PATH = os.path.join(ci.DATA_DIR, "composite", "signal_health.json")

# Per-signal health contract.
#   scored        — does this signal feed the composite score? Only scored-signal
#                   failures set the non-zero exit code. Informational signals
#                   (still collected, still shown on the dashboard) are reported but
#                   never block publication.
#   min_records   — fewest monthly values the extractor may return.
#   max_lag_mo    — newest non-future observation must be within this many months of
#                   the current month. Sized to each source's real publication lag:
#                   BLS/JOLTS/Trends/GitHub are monthly; earnings and regulatory are
#                   quarterly and lag further.
#
# A signal is a scored signal iff it is in ci.WEIGHTS; the `scored` field below must
# agree with that and is asserted at load time so the two can't drift apart.
HEALTH_RULES = {
    "employment":       {"scored": True,  "min_records": 24, "max_lag_mo": 3},
    "rev_per_employee": {"scored": True,  "min_records": 24, "max_lag_mo": 6},
    "job_ratio":        {"scored": True,  "min_records": 24, "max_lag_mo": 4},
    "trends":           {"scored": True,  "min_records": 24, "max_lag_mo": 3},
    "github":           {"scored": True,  "min_records": 24, "max_lag_mo": 3},
    "regulatory":       {"scored": True,  "min_records": 24, "max_lag_mo": 6},
    # Informational — collected and shown, NOT scored (retired in the 2026-07 audit).
    "apprenticeship":   {"scored": False, "min_records": 1,  "max_lag_mo": 999},
    "vc_funding":       {"scored": False, "min_records": 1,  "max_lag_mo": 999},
}


def _month_index(ym):
    """Convert a 'YYYY-MM' string to an absolute month count, or None."""
    try:
        y, m = ym.split("-")
        return int(y) * 12 + int(m)
    except (ValueError, AttributeError):
        return None


def _newest_non_future(series, current_idx):
    """Newest month in the series that is not in the future, as (ym, month_index)."""
    dated = [
        (ym, _month_index(ym)) for ym in series
        if _month_index(ym) is not None and _month_index(ym) <= current_idx
    ]
    if not dated:
        return None, None
    return max(dated, key=lambda t: t[1])


def check_signal(key, series, rule, current_idx):
    """Return a health record for one signal. `ok` is the AND of all applicable checks."""
    checks = {}

    # present — the extractor produced at least one value. An empty extract from a
    # valid-but-empty file lands here, which is the whole point.
    checks["present"] = bool(series)
    if not series:
        return {
            "scored": rule["scored"],
            "ok": False if rule["scored"] else True,  # informational-absent doesn't block
            "checks": checks,
            "n_records": 0,
            "n_nonzero": 0,
            "newest": None,
            "lag_months": None,
            "reason": "extractor returned no values (missing file, unparseable, or shape drift)",
        }

    n = len(series)
    n_nonzero = sum(1 for v in series.values() if v)
    newest_ym, newest_idx = _newest_non_future(series, current_idx)
    lag = (current_idx - newest_idx) if newest_idx is not None else None

    checks["min_records"] = n >= rule["min_records"]
    checks["has_nonzero"] = n_nonzero > 0
    checks["fresh"] = lag is not None and lag <= rule["max_lag_mo"]

    ok = all(checks.values())
    reasons = []
    if not checks["min_records"]:
        reasons.append(f"only {n} records (need {rule['min_records']})")
    if not checks["has_nonzero"]:
        reasons.append("every value is zero — collector is producing nothing usable")
    if not checks["fresh"]:
        reasons.append(
            f"newest non-future data is {newest_ym} ({lag} months stale, max {rule['max_lag_mo']})"
        )

    return {
        "scored": rule["scored"],
        "ok": ok,
        "checks": checks,
        "n_records": n,
        "n_nonzero": n_nonzero,
        "newest": newest_ym,
        "lag_months": lag,
        "reason": "; ".join(reasons) if reasons else "healthy",
    }


def validate(current_ym=None, gate_signals=None):
    """Run every signal through its health contract. Returns the full health dict.

    `gate_signals` optionally restricts which scored signals set the FAIL verdict —
    every signal is still checked and reported, but only the named ones can fail the
    gate. This lets each collection workflow hard-fail on the signal IT just produced
    (turning that job red at the point of breakage) without being blocked by an
    unrelated signal that happens to be mid-cycle. The publish path passes no
    restriction, so it enforces the full scored set.
    """
    # scored field must match ci.WEIGHTS exactly — guard against silent drift.
    for key, rule in HEALTH_RULES.items():
        in_weights = key in ci.WEIGHTS
        if rule["scored"] != in_weights:
            raise AssertionError(
                f"HEALTH_RULES['{key}'].scored={rule['scored']} but "
                f"{'is' if in_weights else 'is NOT'} in WEIGHTS — reconcile before running"
            )

    if current_ym is None:
        today = date.today()
        current_idx = today.year * 12 + today.month
        current_ym = f"{today.year}-{today.month:02d}"
    else:
        current_idx = _month_index(current_ym)

    signal_data = {k: ci.load_json(p) for k, p in ci.SIGNAL_FILES.items()}

    results = {}
    for key, rule in HEALTH_RULES.items():
        series = ci.EXTRACTORS[key](signal_data.get(key))
        results[key] = check_signal(key, series, rule, current_idx)

    scored_fail = [k for k, r in results.items() if r["scored"] and not r["ok"]]
    if gate_signals is not None:
        unknown = set(gate_signals) - set(HEALTH_RULES)
        if unknown:
            raise AssertionError(f"--signals names unknown signal(s): {sorted(unknown)}")
        gating_fail = [k for k in scored_fail if k in gate_signals]
    else:
        gating_fail = scored_fail

    return {
        "as_of": current_ym,
        "gate": "pass" if not gating_fail else "FAIL",
        "gate_scope": sorted(gate_signals) if gate_signals is not None else "all_scored",
        "scored_failures": scored_fail,       # every failing scored signal, for the report
        "gating_failures": gating_fail,       # the subset that actually fails the gate
        "signals": results,
    }


def print_report(health):
    print(f"Signal health gate — as of {health['as_of']}\n")
    header = f"  {'signal':18s} {'role':6s} {'ok':4s} {'n':>4s} {'nz':>4s} {'newest':>8s}  detail"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key, r in health["signals"].items():
        role = "score" if r["scored"] else "info"
        mark = "ok" if r["ok"] else "FAIL"
        newest = r["newest"] or "--"
        detail = "" if r["reason"] == "healthy" else r["reason"]
        print(f"  {key:18s} {role:6s} {mark:4s} {r['n_records']:>4d} {r['n_nonzero']:>4d} {newest:>8s}  {detail}")
    print()
    scope = health["gate_scope"]
    scope_str = "all scored signals" if scope == "all_scored" else f"gating on {', '.join(scope)}"
    # A signal that failed but is outside this run's gate scope is surfaced, not hidden.
    non_gating = [k for k in health["scored_failures"] if k not in health["gating_failures"]]
    if non_gating:
        print(f"  NOTE: {', '.join(non_gating)} failing but outside this run's gate scope "
              f"(will block the weekly publish).")
    if health["gate"] == "pass":
        print(f"  GATE: PASS ({scope_str}).")
    else:
        print(f"  GATE: FAIL ({scope_str}) — failing: {', '.join(health['gating_failures'])}")


def save_health(health):
    os.makedirs(os.path.dirname(HEALTH_PATH), exist_ok=True)
    with open(HEALTH_PATH, "w") as f:
        json.dump(health, f, indent=2)
    print(f"\n  Wrote {os.path.relpath(HEALTH_PATH, ci.BASE_DIR)}")


def main():
    parser = argparse.ArgumentParser(description="Displacement Curve signal health gate")
    parser.add_argument("--report-only", action="store_true",
                        help="Print and write the report but always exit 0")
    parser.add_argument("--signals", metavar="a,b,c",
                        help="Only these scored signals set the exit code (all are still reported)")
    parser.add_argument("--as-of", metavar="YYYY-MM",
                        help="Treat this month as 'now' (for testing freshness)")
    args = parser.parse_args()

    gate_signals = [s.strip() for s in args.signals.split(",")] if args.signals else None
    health = validate(current_ym=args.as_of, gate_signals=gate_signals)
    print_report(health)
    save_health(health)

    if health["gate"] == "FAIL" and not args.report_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
