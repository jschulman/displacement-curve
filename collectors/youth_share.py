#!/usr/bin/env python3
"""
Apprenticeship signal collector — youth share of professional-services employment.

The apprenticeship collapse is a labor-DEMOGRAPHIC phenomenon, measured at the sector
level (matching this composite's altitude) rather than from per-firm job postings —
entry/campus hiring is recruited off the public experienced-hire boards for many firms,
so a demographic measure is both more consistent and more authoritative.

Source: Census ACS 1-year PUMS API (api.census.gov). Per year, pull person-level AGEP
(age) + PWGTP (person weight) for the professional-services INDP industry codes, and
compute the PWGTP-weighted share of workers under 25 and under 35. A falling youth share
= the entry/apprenticeship tier thinning, sector-wide.

INDP codes mirror displacement-curve's existing tracked sectors:
  7270 Legal · 7280 Accounting/Tax · 7380 Computer Systems Design · 7390 Mgmt/Sci/Tech Consulting

Requires a free Census API key in CENSUS_API_KEY (api.census.gov/data/key_signup.html).
NOTE: do NOT send a browser User-Agent — the Census API returns "Invalid Key" HTML to
browser-like UAs even with a valid key. Use the default urllib UA (no override).

Usage:
  CENSUS_API_KEY=... python collectors/youth_share.py
  CENSUS_API_KEY=... python collectors/youth_share.py --years 2015-2023
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DC_DATA_DIR") or os.path.join(BASE_DIR, "data")
OUT_PATH = os.path.join(DATA_DIR, "apprenticeship", "processed", "collapse.json")

INDP_CODES = ["7270", "7280", "7380", "7390"]   # legal, accounting, comp-sys-design, consulting
# ACS 1-year exists 2005-2019, 2021-2023 (no 2020 ACS1). Default to the AI-era window.
DEFAULT_YEARS = [2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023]


def fetch_indp_year(year, code, key):
    """Return list of (pwgtp, agep) for one industry code in one year, or [] on miss."""
    url = (f"https://api.census.gov/data/{year}/acs/acs1/pums"
           f"?get=PWGTP,AGEP&INDP={code}&ucgid=0100000US&key={key}")
    try:
        # Deliberately no User-Agent override (browser UA triggers a false Invalid Key).
        with urllib.request.urlopen(url, timeout=90) as r:
            rows = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"    {year} INDP {code}: HTTP {e.code} (skip)")
        return []
    out = []
    for row in rows[1:]:               # row[0] is the header
        try:
            out.append((float(row[0]), int(row[1])))
        except (ValueError, TypeError):
            continue
    return out


def weighted_median_age(records):
    """PWGTP-weighted median age of employed (AGEP>=16)."""
    pairs = sorted((age, w) for w, age in records if age >= 16)
    total = sum(w for _, w in pairs)
    if total == 0:
        return None
    half, cum = total / 2, 0.0
    for age, w in pairs:
        cum += w
        if cum >= half:
            return age
    return pairs[-1][0]


def youth_shares(records):
    """PWGTP-weighted shares of employed (AGEP>=16) under 25 and under 35, + median age.
    Three demographic angles triangulate the apprenticeship signal: a thinning entry
    tier should show up as falling youth shares AND rising median age."""
    total = u25 = u35 = 0.0
    for w, age in records:
        if age < 16:
            continue
        total += w
        if age < 25:
            u25 += w
        if age < 35:
            u35 += w
    if total == 0:
        return None
    return {"u25": round(u25 / total, 4), "u35": round(u35 / total, 4),
            "median_age": weighted_median_age(records), "weighted_total": int(total)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", help="e.g. 2015-2023")
    args = p.parse_args()

    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("  ERROR: CENSUS_API_KEY not set (free key: api.census.gov/data/key_signup.html)")
        sys.exit(1)

    years = DEFAULT_YEARS
    if args.years:
        lo, hi = (int(x) for x in args.years.split("-"))
        years = [y for y in range(lo, hi + 1) if y != 2020]  # no ACS1 2020

    monthly = []
    for year in years:
        recs = []
        for code in INDP_CODES:
            recs.extend(fetch_indp_year(year, code, key))
        s = youth_shares(recs)
        if not s:
            print(f"  {year}: no data")
            continue
        # value = under-25 share (the apprenticeship tier). Composite inverts it.
        monthly.append({
            "date": f"{year}-01", "value": s["u25"],
            "youth_share_u25": s["u25"], "youth_share_u35": s["u35"],
            "median_age": s["median_age"],
            "weighted_employment": s["weighted_total"],
        })
        print(f"  {year}: under-25 {s['u25']:.1%} · under-35 {s['u35']:.1%} · median age {s['median_age']} · n(weighted) {s['weighted_total']:,}")

    out = {
        "metadata": {
            "source": "Census ACS 1-year PUMS",
            "signal": "professional_services_youth_share",
            "description": "PWGTP-weighted share of professional-services employment (legal, accounting, "
                           "computer systems design, mgmt/sci/tech consulting) under age 25. Falling = "
                           "apprenticeship tier thinning. Composite inverts (lower share -> higher displacement).",
            "indp_codes": INDP_CODES,
            "invert": True,
            "last_updated": monthly[-1]["date"] if monthly else None,
            "mock": False,
        },
        "monthly": monthly,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"  wrote {len(monthly)} year(s) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
