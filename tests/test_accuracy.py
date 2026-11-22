"""§8.6 and §11.4 — two tolerances that were prose and are now functions."""
import unittest

import accuracy as A
import colour as Col


class TestIdentityAccuracy(unittest.TestCase):
    def test_a_clean_corpus_meets_the_targets(self):
        result = A.rates(A.synthetic_corpus())
        self.assertEqual(A.meets_targets(result), [])

    def test_the_harness_notices_a_bad_threshold(self):
        # widen the accept threshold and the false positives appear
        result = A.rates(A.synthetic_corpus(), accept=0.95, reject=0.99)
        self.assertTrue(A.meets_targets(result), "a bad threshold must fail")

    def test_a_corpus_of_nothing_reports_zero_rather_than_crashing(self):
        result = A.rates([])
        self.assertEqual(result["fpr"], 0.0)
        self.assertEqual(result["grey_rate"], 0.0)

    def test_the_definitions_are_the_sections(self):
        # one false positive, one false negative, one in the band
        result = A.rates([(0.10, False), (0.90, True), (0.45, True)])
        self.assertEqual(result["counts"]["fp"], 1)
        self.assertEqual(result["counts"]["fn"], 1)
        self.assertEqual(result["counts"]["grey"], 1)
        self.assertEqual(result["fpr"], 1.0)
        self.assertEqual(result["fnr"], 1.0)


class TestColourTolerance(unittest.TestCase):
    def setUp(self):
        self.frame = [(128, 64, 32), (200, 200, 200), (10, 240, 90)]

    def test_identical_frames_have_no_difference(self):
        self.assertEqual(Col.mean_delta_e(self.frame, self.frame), 0.0)

    def test_a_gain_produces_a_measurable_difference(self):
        brighter = Col.apply_gain(self.frame, 1.2)
        self.assertGreater(Col.mean_delta_e(self.frame, brighter), 1.0)

    def test_a_small_gain_is_within_a_tolerance(self):
        # §11.4's acceptance test: two shots of one scene, matched within ΔE
        near = Col.apply_gain(self.frame, 1.02)
        self.assertLess(Col.mean_delta_e(self.frame, near), 2.0)

    def test_lab_round_trips_white(self):
        L, a, b = Col.rgb_to_lab((255, 255, 255))
        self.assertAlmostEqual(L, 100.0, places=1)
        self.assertAlmostEqual(a, 0.0, places=1)
        self.assertAlmostEqual(b, 0.0, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
