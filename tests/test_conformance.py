"""Conformance tests: the specification's worked examples, executed.

Every test names the section it proves. A failure here means the document and
the code disagree, and the document is the thing that ships — so either the
document is wrong or the implementation is, and the test does not care which.

    python -m unittest discover -s tests -v
"""
import unittest
from fractions import Fraction as F

import spec_rules as R
import vfr_fixture as V

FPS_2997 = F(30000, 1001)


class TestTimeModel(unittest.TestCase):
    """§5.1, §5.5, §5.6, §5.9.3"""

    def test_rounding_is_half_away_from_zero(self):
        # §5.1. Python's round() would give 500 and 2 here.
        self.assertEqual(R.round_half_away(F(1001, 2)), 501)
        self.assertEqual(R.round_half_away(F(5, 2)), 3)
        self.assertEqual(R.round_half_away(F(-5, 2)), -3)

    def test_sequence_samples(self):
        # §5.5: 1349 frames at 30000/1001 is 2,160,558.4 samples, rounded.
        self.assertEqual(R.samples_for(1349, FPS_2997), 2160558)

    def test_native_projection_and_conformed_consumption_differ(self):
        # §5.9.3: the two numbers side by side.
        self.assertEqual(R.native_projection(300, 1, 25, FPS_2997), 250)
        self.assertEqual(R.conformed_consumption(300, 1), 300)
        self.assertEqual(R.native_projection(300, 2, 25, FPS_2997), 501)
        self.assertEqual(R.conformed_consumption(300, 2), 600)

    def test_double_rounding_is_off_by_one(self):
        # §5.9.3: conforming the native answer gives 601, not 600.
        m = R.AffineConformMap(25, FPS_2997, native_duration=100000)
        self.assertEqual(m.to_conformed(501), 601)
        self.assertNotEqual(m.to_conformed(501), R.conformed_consumption(300, 2))


class TestConformMap(unittest.TestCase):
    """§5.9, §5.9.1, Appendix A"""

    def test_ten_second_case(self):
        # §5.9.1: 250 native frames of 25 fps are 300 conformed frames.
        m = R.AffineConformMap(25, FPS_2997, native_duration=250)
        self.assertEqual(m.to_conformed(250), 300)

    def test_map_is_total_at_the_boundary(self):
        # §5.9: defined on the closed interval, which is what bounds checks need.
        m = R.AffineConformMap(25, FPS_2997, native_duration=250)
        self.assertEqual(m.to_conformed(0), 0)
        with self.assertRaises(ValueError):
            m.to_conformed(251)

    def test_invertible_within_one_frame(self):
        # §5.9: |toConformed(toNative(c)) - c| <= 1
        m = R.AffineConformMap(25, FPS_2997, native_duration=1000)
        for c in range(0, 1100, 7):
            self.assertLessEqual(abs(m.to_conformed(round(m.to_native(c))) - c), 1)

    def test_monotone_over_random_rates(self):
        # §5.9: property test over rate pairs, as §19 asks.
        pairs = [(24000 / 1001, 30000 / 1001), (25, 30000 / 1001),
                 (60000 / 1001, 30000 / 1001), (30, 60), (24000 / 1001, 25)]
        for src, proj in pairs:
            m = R.AffineConformMap(F(src).limit_denominator(100000),
                                   F(proj).limit_denominator(100000), 5000)
            prev = -1
            for n in range(0, 5001, 13):
                c = m.to_conformed(n)
                self.assertGreaterEqual(c, prev)
                prev = c

    def test_appendix_a_clips(self):
        # Appendix A, Table A3: every conformed span equals its record duration.
        clips = [("c1", F(24000, 1001), 1440, 1689, 311, +62),
                 ("c2", F(25), 96, 317, 265, +44),
                 ("c3", F(30000, 1001), 60, 254, 194, 0),
                 ("c4", F(60000, 1001), 900, 1562, 331, -331),
                 ("c5", F(24000, 1001), 2160, 2397, 296, +59)]
        for name, fps, a, b, record, drift in clips:
            m = R.AffineConformMap(fps, FPS_2997, native_duration=100000)
            span = m.to_conformed(b) - m.to_conformed(a)
            self.assertEqual(span, record, name)
            self.assertEqual(record - (b - a), drift, name)


class TestVFR(unittest.TestCase):
    """§5.4, §5.9.4 — the fixture the specification asks for."""

    def setUp(self):
        self.pts = V.generate()
        self.m = R.TableConformMap(self.pts, FPS_2997)

    def test_fixture_is_actually_vfr(self):
        self.assertTrue(V.is_vfr(self.pts), f"spread {V.spread(self.pts):.2%}")

    def test_six_frame_excerpt(self):
        # §5.9.4: the worked table.
        pts = [0, 33333, 66667, 133333, 166667, 200000]
        m = R.TableConformMap(pts, FPS_2997)
        self.assertEqual([m.to_conformed(n) for n in range(6)], [0, 1, 2, 4, 5, 6])
        self.assertEqual(m.skipped_indices(), [3])
        self.assertEqual(m.conformed_duration, 7)     # one frame longer than native

    def test_map_is_non_decreasing_and_total(self):
        prev = -1
        for n in range(self.m.native_duration):
            c = self.m.to_conformed(n)
            self.assertGreaterEqual(c, prev)
            prev = c
        with self.assertRaises(ValueError):
            self.m.to_conformed(self.m.native_duration)

    def test_reordering_does_not_change_the_map(self):
        # §5.9.4: ingest sorts, so a reordered stream maps identically.
        shuffled = R.TableConformMap(V.reorder(self.pts), FPS_2997)
        self.assertEqual([shuffled.to_conformed(n) for n in range(200)],
                         [self.m.to_conformed(n) for n in range(200)])

    def test_shared_timestamp_is_legal(self):
        # §5.9.4: two packets at one PTS map to one conformed frame.
        m = R.TableConformMap([0, 33333, 33333, 66667], FPS_2997)
        self.assertEqual([m.to_conformed(n) for n in range(4)], [0, 1, 1, 2])


class TestVfrThreshold(unittest.TestCase):
    """§5.4 — the boundary, which the obvious fixture never touches."""

    def test_just_below_is_constant_rate(self):
        pts = V.near_threshold(0.9)
        self.assertAlmostEqual(V.spread(pts), 0.009, places=4)
        self.assertFalse(V.is_vfr(pts))

    def test_just_above_is_variable_rate(self):
        pts = V.near_threshold(1.1)
        self.assertAlmostEqual(V.spread(pts), 0.011, places=4)
        self.assertTrue(V.is_vfr(pts))

    def test_exactly_at_the_threshold_is_not_vfr(self):
        # §5.4 says "beyond 1%", so 1.0% is still constant rate.
        pts = V.near_threshold(1.0)
        self.assertFalse(V.is_vfr(pts))


class TestSpeed(unittest.TestCase):
    """§5.11 — at ratios that do not decompose."""

    def test_37x_is_exact(self):
        self.assertEqual(R.conformed_consumption(300, F(37, 10)), 1110)
        self.assertEqual(R.samples_for(1110, FPS_2997), 1777776)
        self.assertEqual(R.samples_for(300, FPS_2997), 480480)
        self.assertEqual(F(1777776, 480480), F(37, 10))

    def test_inverse_37x_needs_rounding(self):
        self.assertEqual(R.conformed_consumption(300, F(10, 37)), 81)
        exact = F(81) / FPS_2997 * 48000
        self.assertNotEqual(exact.denominator, 1)          # 129,729.6
        self.assertEqual(R.round_half_away(exact), 129730)

    def test_cascade_stays_inside_the_filter_range(self):
        for speed in (F(4), F(37, 10), F(1, 3), F(16), F(1, 16)):
            factors = R.atempo_cascade(speed)
            for f in factors:
                self.assertGreaterEqual(f, F(1, 2))
                self.assertLessEqual(f, 2)

    def test_seven_decimals_beat_six(self):
        # §5.11 quotes the bound, not one ratio's luck: 3.7 is exact at two
        # decimals, so only the bound shows why seven places are required.
        out = R.samples_for(1349, FPS_2997)               # a 45-second output
        self.assertAlmostEqual(float(R.atempo_drift_bound(out, 6)), 2.16, places=2)
        self.assertAlmostEqual(float(R.atempo_drift_bound(out, 7)), 0.216, places=3)
        self.assertLessEqual(R.atempo_drift_bound(out, 7), 1)

    def test_awkward_ratio_stays_within_one_sample(self):
        out = R.samples_for(1349, FPS_2997)
        for speed in (F(1, 3), F(37, 10), F(100, 37), F(7, 3)):
            self.assertLessEqual(R.atempo_drift(speed, out, 7), 1, str(speed))

    def test_out_of_range_speeds_rejected(self):
        for bad in (F(0), F(-1), F(17), F(1, 17)):
            with self.assertRaises(ValueError):
                R.atempo_cascade(bad)


class TestTransitions(unittest.TestCase):
    """§5.7 — picture and audio handles, in the right domain."""

    def test_picture_handle_follows_speed(self):
        self.assertEqual(R.handle_source_frames(12, 1), 6)
        self.assertEqual(R.handle_source_frames(12, 2), 12)
        self.assertEqual(R.handle_source_frames(12, F(1, 2)), 3)

    def test_audio_handle_rounds_once(self):
        # samples_for(12) is 19,219; 2 x samples_for(6) is 19,220. The second
        # is the double-rounding bug this rule exists to prevent.
        once = R.handle_source_samples(12, 2, FPS_2997)
        twice = 2 * R.samples_for(6, FPS_2997)
        self.assertEqual(once, 19219)
        self.assertEqual(twice, 19220)
        self.assertNotEqual(once, twice)


class TestAnnotations(unittest.TestCase):
    """§5.10 — captions, markers and the beat grid."""

    def test_source_to_record_endpoints(self):
        m = R.AffineConformMap(25, FPS_2997, native_duration=100000)
        self.assertEqual(R.record_frame_for(96, m, 96, 299, 1), 299)
        self.assertEqual(R.record_frame_for(317, m, 96, 299, 1), 299 + 265)

    def test_beat_interval_scales_with_speed(self):
        self.assertAlmostEqual(float(R.beat_interval_frames(124, FPS_2997)), 14.5016, 4)
        self.assertAlmostEqual(float(R.beat_interval_frames(124, FPS_2997, F(105, 100))),
                               13.8111, 4)


class TestTableMapUnderSpeed(unittest.TestCase):
    """§5.9.5 — record, then speed, then the table, in that order."""

    def test_two_x_walk(self):
        m = R.TableConformMap([0, 33333, 66667, 133333, 166667, 200000], FPS_2997)
        walk = [m.to_native(r * 2) for r in range(4)]
        # f0, f2, f3, f5 — a uniform walk would have taken f4 instead of f3
        self.assertEqual([round(float(t) * 1_000_000) for t in walk],
                         [0, 66667, 133333, 200000])

    def test_skipped_frames_are_not_the_uniform_ones(self):
        m = R.TableConformMap([0, 33333, 66667, 133333, 166667, 200000], FPS_2997)
        visited = {round(float(m.to_native(r * 2)) * 1_000_000) for r in range(4)}
        self.assertIn(133333, visited)        # f3, which a stride of 2 would miss
        self.assertNotIn(166667, visited)     # f4, which a stride of 2 would take


class TestDurationLadder(unittest.TestCase):
    """§7.7 — four bands, no gap."""

    def test_bands(self):
        self.assertEqual(R.duration_band(1349, 1349), "accept")
        self.assertEqual(R.duration_band(1349, 1323), "accept")      # -1.93%
        self.assertEqual(R.duration_band(1349, 1315), "repair")      # -2.5%
        self.assertEqual(R.duration_band(1349, 1290), "repair")      # -4.4%
        self.assertEqual(R.duration_band(1349, 1280), "fallback")    # -5.1%
        self.assertEqual(R.duration_band(1349, 1200), "fallback")    # -11%


class TestErasureAndCost(unittest.TestCase):
    """§16.6.1, §20.3"""

    def test_deadlines_are_configurable_per_jurisdiction(self):
        self.assertEqual(R.erasure_deadline("withdrawn"), 30)
        self.assertEqual(R.erasure_deadline("withdrawn", {"withdrawn": 7,
                                                          "retained_lawful": 90,
                                                          "restored": 0}), 7)
        with self.assertRaises(ValueError):
            R.erasure_deadline("quarantined")

    def test_egress_is_tiered(self):
        self.assertEqual(R.egress_cost(1000), 90)            # first TB at $0.09
        self.assertEqual(R.egress_cost(3000), 190)           # + 2 TB at $0.05
        self.assertLess(R.egress_cost(3000) / 3, 90)         # blended rate falls


if __name__ == "__main__":
    unittest.main(verbosity=2)
