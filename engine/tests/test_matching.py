"""Synthetic unit tests for temporal eligibility and point-to-line matching.

All geometries are invented metre-plane fixtures. They are not Calgary assets.
SYNTHETIC = True
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from pipe_dreams_engine.matching import (
    AMBIG_M,
    ASSOC_M,
    associate_breaks,
    eligible_at_cutoff,
    historically_attributable,
)

SYNTHETIC = True


def _pipes(rows):
    """rows: (asset_id, install_year, coords)."""
    return pd.DataFrame(
        {
            "asset_id": [r[0] for r in rows],
            "install_year": [r[1] for r in rows],
            "geometry": [LineString(r[2]) for r in rows],
        }
    )


def _breaks(rows):
    """rows: (break_id, break_year, xy)."""
    return pd.DataFrame(
        {
            "break_id": [r[0] for r in rows],
            "break_year": [r[1] for r in rows],
            "geometry": [Point(r[2]) for r in rows],
        }
    )


class MatchingTemporalTests(unittest.TestCase):
    def test_synthetic_fixtures_are_flagged(self):
        self.assertTrue(SYNTHETIC)

    def test_historically_attributable_excludes_same_year(self):
        self.assertFalse(bool(historically_attributable(2024, 2024)))
        self.assertFalse(bool(historically_attributable(2025, 2024)))
        self.assertTrue(bool(historically_attributable(2023, 2024)))

    def test_same_year_replacement_is_not_attributed(self):
        """A same-year repair segment at the break must not take the event.

        Recovered rule used install_year <= break_year and would attach this
        break to the 2024 replacement. Protocol requires install_year < break_year.
        """
        pipes = _pipes(
            [
                ("repair_2024", 2024, [(0.0, 0.0), (10.0, 0.0)]),
                ("older_main", 1975, [(0.0, 8.0), (10.0, 8.0)]),
            ]
        )
        breaks = _breaks([("break_2024", 2024, (5.0, 0.5))])

        result = associate_breaks(breaks, pipes)

        self.assertTrue(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "nearest_segment_id"], "older_main")
        self.assertEqual(result.loc[0, "candidate_count_within_threshold"], 2)
        self.assertGreater(result.loc[0, "nearest_distance_m"], 7.0)

    def test_nearest_eligible_pipe_not_nearest_ineligible(self):
        """Closer ineligible (same-year) pipe is skipped; farther eligible pipe is kept."""
        pipes = _pipes(
            [
                ("new_same_year", 2019, [(0.0, 0.0), (20.0, 0.0)]),
                ("eligible_older", 1990, [(0.0, 12.0), (20.0, 12.0)]),
            ]
        )
        breaks = _breaks([("b1", 2019, (10.0, 1.0))])

        result = associate_breaks(breaks, pipes)

        self.assertTrue(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "nearest_segment_id"], "eligible_older")
        self.assertLess(result.loc[0, "nearest_distance_m"], ASSOC_M)

    def test_point_to_line_uses_line_distance_not_midpoint(self):
        """A break near one end of a long line is closer to that line than to a
        short segment whose midpoint is nearer the break than the long-line
        midpoint is.
        """
        pipes = _pipes(
            [
                ("long_line", 1980, [(0.0, 0.0), (100.0, 0.0)]),
                ("short_near_break_x", 1980, [(88.0, 20.0), (92.0, 20.0)]),
            ]
        )
        breaks = _breaks([("near_end", 2000, (90.0, 2.0))])

        result = associate_breaks(breaks, pipes)

        self.assertTrue(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "nearest_segment_id"], "long_line")
        self.assertEqual(result.loc[0, "nearest_distance_m"], 2.0)

    def test_no_eligible_candidate_when_only_same_year_pipe_is_nearby(self):
        pipes = _pipes(
            [
                ("same_year", 2016, [(0.0, 0.0), (10.0, 0.0)]),
                ("far_older", 1970, [(0.0, 80.0), (10.0, 80.0)]),
            ]
        )
        breaks = _breaks([("b1", 2016, (5.0, 1.0))])

        result = associate_breaks(breaks, pipes)

        self.assertFalse(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "nearest_segment_idx"], -1)
        self.assertEqual(result.loc[0, "candidate_count_within_threshold"], 1)

    def test_no_eligible_candidate_when_all_pipes_beyond_threshold(self):
        pipes = _pipes([("far", 1970, [(0.0, 80.0), (10.0, 80.0)])])
        breaks = _breaks([("b1", 2016, (5.0, 0.0))])

        result = associate_breaks(breaks, pipes)

        self.assertFalse(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "candidate_count_within_threshold"], 0)

    def test_ambiguous_when_second_eligible_pipe_within_gap(self):
        pipes = _pipes(
            [
                ("near", 1980, [(0.0, 0.0), (10.0, 0.0)]),
                ("also_near", 1980, [(0.0, 3.0), (10.0, 3.0)]),
            ]
        )
        breaks = _breaks([("b1", 2000, (5.0, 1.0))])

        result = associate_breaks(breaks, pipes)

        self.assertTrue(bool(result.loc[0, "associated"]))
        self.assertEqual(result.loc[0, "nearest_segment_id"], "near")
        gap = result.loc[0, "second_nearest_distance_m"] - result.loc[0, "nearest_distance_m"]
        self.assertLessEqual(gap, AMBIG_M)
        self.assertTrue(bool(result.loc[0, "ambiguous"]))

    def test_cutoff_eligibility_includes_install_in_cutoff_year(self):
        self.assertTrue(bool(eligible_at_cutoff(2013, 2013)))
        self.assertTrue(bool(eligible_at_cutoff(2012, 2013)))
        self.assertFalse(bool(eligible_at_cutoff(2014, 2013)))

    def test_cutoff_eligibility_is_independent_of_break_attribution(self):
        """A pipe installed in 2022 is a planning candidate at cutoff 2022, but a
        2022 break still cannot be attributed to it.
        """
        self.assertTrue(bool(eligible_at_cutoff(2022, 2022)))
        self.assertFalse(bool(historically_attributable(2022, 2022)))

        pipes = _pipes([("installed_2022", 2022, [(0.0, 0.0), (10.0, 0.0)])])
        breaks = _breaks([("break_2022", 2022, (5.0, 0.5))])
        result = associate_breaks(breaks, pipes)

        self.assertFalse(bool(result.loc[0, "associated"]))
        self.assertTrue(bool(eligible_at_cutoff(pipes.loc[0, "install_year"], 2022)))


    def test_missing_and_invalid_years_are_ineligible(self):
        for bad in [None, pd.NA, np.nan, "invalid"]:
            with self.subTest(bad_year=repr(bad)):
                self.assertFalse(bool(historically_attributable(bad, 2020)))
                self.assertFalse(bool(historically_attributable(2010, bad)))
                self.assertFalse(bool(eligible_at_cutoff(bad, 2020)))
                self.assertFalse(bool(eligible_at_cutoff(2010, bad)))

    def test_valid_year_rules_remain_correct(self):
        self.assertTrue(bool(historically_attributable(2019, 2020)))
        self.assertFalse(bool(historically_attributable(2020, 2020)))
        self.assertTrue(bool(eligible_at_cutoff(2020, 2020)))


if __name__ == "__main__":
    unittest.main()
