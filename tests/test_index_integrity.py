#!/usr/bin/env python3
"""
Integrity tests for the composite index math and the signal-health gate.

These are the tests the 2026-07 audit wished had existed. The pre-existing suite
(test_collectors.py) only ran collectors in --mock mode and asserted
`metadata.mock is True`, so it was structurally incapable of catching a dead signal,
a sign error, or a normalization defect in the real pipeline. Everything here targets
the actual scoring logic and the gate that guards it — no mock generators.

Run: python -m unittest tests.test_index_integrity
"""

import os
import sys
import unittest

_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_ROOT, "normalizers"))
sys.path.insert(0, _ROOT)  # for `collectors.*`
import composite_index as ci  # noqa: E402
import validate as V  # noqa: E402


def _series(start_ym, values):
    """Build a {YYYY-MM: value} series of consecutive months from a start month."""
    y, m = (int(p) for p in start_ym.split("-"))
    out = {}
    for v in values:
        out[f"{y}-{m:02d}"] = v
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


class TestWeights(unittest.TestCase):
    def test_weights_sum_to_one(self):
        # A composite whose weights don't sum to 1.0 silently mis-scales every score.
        self.assertAlmostEqual(sum(ci.WEIGHTS.values()), 1.0, places=6)

    def test_every_scored_signal_has_an_anchor(self):
        for key in ci.WEIGHTS:
            self.assertIn(key, ci.ANCHORS, f"scored signal {key} has no normalization anchor")

    def test_polarity_lives_only_in_anchors(self):
        # The job_ratio sign error survived because polarity was tracked in a second
        # place that fell out of sync. Guard that there is no separate invert flag.
        self.assertFalse(hasattr(ci, "INVERT_SIGNALS"),
                         "INVERT_SIGNALS reintroduced — polarity must live only in ANCHORS")


class TestAnchorNormalization(unittest.TestCase):
    def test_inverted_signal_scores_backwards(self):
        # job_ratio: falling openings = MORE displacement. Anchor zero=1.0, hundred=0.5.
        anchor = ci.ANCHORS["job_ratio"]
        norm, _, _ = ci.normalize_to_anchors({"2024-01": 1.0, "2024-02": 0.5}, anchor)
        self.assertEqual(norm["2024-01"], 0.0)    # hiring at baseline -> no displacement
        self.assertEqual(norm["2024-02"], 100.0)  # openings halved -> full displacement

    def test_non_inverted_signal_scores_forward(self):
        anchor = ci.ANCHORS["github"]  # zero=0, hundred=5000
        norm, _, _ = ci.normalize_to_anchors({"2024-01": 0, "2024-02": 5000}, anchor)
        self.assertEqual(norm["2024-01"], 0.0)
        self.assertEqual(norm["2024-02"], 100.0)

    def test_clamped_to_range(self):
        anchor = ci.ANCHORS["github"]
        norm, _, _ = ci.normalize_to_anchors({"a": -100, "b": 999999}, anchor)
        self.assertEqual(norm["a"], 0.0)
        self.assertEqual(norm["b"], 100.0)

    def test_no_lookahead_bias(self):
        # A month's normalized score must not depend on data from later months.
        # This is the property min-max normalization violated.
        anchor = ci.ANCHORS["github"]
        early = {"2024-01": 1000, "2024-02": 2000}
        late = dict(early, **{"2024-03": 4900})  # a new high
        n_early, _, _ = ci.normalize_to_anchors(early, anchor)
        n_late, _, _ = ci.normalize_to_anchors(late, anchor)
        self.assertEqual(n_early["2024-01"], n_late["2024-01"])
        self.assertEqual(n_early["2024-02"], n_late["2024-02"])

    def test_missing_baseline_does_not_silently_rescale(self):
        # pct_vs_baseline with the baseline month absent must refuse, not fall back
        # to the earliest month (which would reintroduce look-ahead).
        anchor = ci.ANCHORS["employment"]  # baseline_month 2022-11
        norm, _, _ = ci.normalize_to_anchors({"2025-01": 22000, "2025-02": 21000}, anchor)
        self.assertEqual(norm, {}, "missing baseline should drop the signal, not rescale it")


class TestHealthGate(unittest.TestCase):
    """The gate must fail loudly on every way a collector can silently die."""

    def setUp(self):
        self.rule = {"scored": True, "min_records": 24, "max_lag_mo": 3}
        self.good = _series("2024-01", [100 + i for i in range(31)])  # 2024-01..2026-07
        self.now = "2026-07"
        self.now_idx = 2026 * 12 + 7

    def _ok(self, series):
        return V.check_signal("github", series, self.rule, self.now_idx)["ok"]

    def test_healthy_passes(self):
        self.assertTrue(self._ok(self.good))

    def test_all_zero_fails(self):
        # The VC failure mode: file present, valid, every value zero.
        self.assertFalse(self._ok({k: 0 for k in self.good}))

    def test_empty_fails(self):
        # A valid-but-empty file must not pass.
        self.assertFalse(self._ok({}))

    def test_stale_fails(self):
        stale = {k: v for k, v in self.good.items() if k < "2026-02"}
        self.assertFalse(self._ok(stale))

    def test_too_few_records_fails(self):
        self.assertFalse(self._ok({"2026-06": 1, "2026-07": 2}))

    def test_partial_zeros_pass(self):
        # regulatory/trends are legitimately zero early on; a series with SOME
        # non-zero recent data must pass.
        partial = dict(self.good)
        for k in list(partial)[:15]:
            partial[k] = 0
        self.assertTrue(self._ok(partial))

    def test_future_dated_zero_does_not_spoof_freshness(self):
        # Quarterly expansion can emit months past today. A future zero must not
        # count as the "newest" fresh observation.
        s = {k: v for k, v in self.good.items() if k <= "2026-01"}  # real data ends Jan
        s["2026-12"] = 0  # future-dated zero from quarter expansion
        self.assertFalse(self._ok(s), "future-dated zero masked a stalled collector")

    def test_gate_rules_match_weights(self):
        # HEALTH_RULES scored-flags must agree with WEIGHTS, or validate() raises.
        health = V.validate(current_ym="2026-07")
        self.assertIn(health["gate"], ("pass", "FAIL"))


class TestLiveDataIsHealthy(unittest.TestCase):
    """Against the committed production data, every scored signal must be alive.

    This is the single test that, had it existed, would have caught the VC signal
    dying for 44 months. It reads the real processed files.
    """

    def test_no_scored_signal_is_dead(self):
        health = V.validate()
        dead = [k for k in ci.WEIGHTS if not health["signals"][k]["ok"]]
        self.assertEqual(dead, [], f"scored signals failing health gate: {dead}")

    def test_gate_passes_on_live_data(self):
        self.assertEqual(V.validate()["gate"], "pass")


class TestQ4Parser(unittest.TestCase):
    """The earnings parser must not book annual totals as Q4, mix YTD with discrete
    quarters, or align on fiscal instead of calendar periods."""

    def setUp(self):
        from collectors.earnings_transcripts import _parse_xbrl_revenue_entries
        self.parse = _parse_xbrl_revenue_entries

    def test_fy_decomposed_not_booked_as_q4(self):
        entries = [
            {"start": "2024-01-01", "end": "2024-03-31", "val": 100e6, "filed": "2024-04-15"},
            {"start": "2024-04-01", "end": "2024-06-30", "val": 110e6, "filed": "2024-07-15"},
            {"start": "2024-07-01", "end": "2024-09-30", "val": 120e6, "filed": "2024-10-15"},
            {"start": "2024-01-01", "end": "2024-12-31", "val": 500e6, "filed": "2025-02-15"},  # FY
        ]
        out = {r["quarter"]: r["value_mm"] for r in self.parse(entries)}
        # Q4 must be FY - (Q1+Q2+Q3) = 500 - 330 = 170, NOT the 500 annual total.
        self.assertEqual(out["2024-Q4"], 170.0)
        self.assertEqual(out["2024-Q1"], 100.0)

    def test_ytd_entries_rejected(self):
        entries = [
            {"start": "2024-01-01", "end": "2024-03-31", "val": 100e6, "filed": "2024-04-15"},
            {"start": "2024-01-01", "end": "2024-06-30", "val": 210e6, "filed": "2024-07-15"},  # YTD
        ]
        out = {r["quarter"]: r["value_mm"] for r in self.parse(entries)}
        # The 6-month YTD row must not become a quarter; only the discrete Q1 survives.
        self.assertEqual(out, {"2024-Q1": 100.0})

    def test_calendar_quarter_from_end_date(self):
        # A period ending 2025-03-31 is calendar Q1 2025 regardless of fiscal labels.
        entries = [{"start": "2025-01-01", "end": "2025-03-31", "val": 42e6, "filed": "2025-04-15"}]
        out = self.parse(entries)
        self.assertEqual(out[0]["quarter"], "2025-Q1")


if __name__ == "__main__":
    unittest.main()
