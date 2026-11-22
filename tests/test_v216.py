"""v2.16: a second judge of a different shape, and what it actually adds."""
import unittest

import calibration as Cal
import distribution as Dist
import rubric as RB
from test_planner import REQUESTS

REEL = REQUESTS["three_shot_reel"]
SET_REQUEST = {"duration_target_ms": 45011, "shots": [{"labels": []}] * 6}


class TestDistributionJudge(unittest.TestCase):
    """§19.2 — a second opinion has to measure something the first does not."""

    def test_an_evenly_divided_plan_is_caught(self):
        even = {"structure": Cal.sequential([270] * 5)}
        self.assertEqual(Dist.judge(even)["label"], "bad")

    def test_a_varied_plan_passes(self):
        varied = {"structure": Cal.sequential([90, 330, 380, 300, 249])}
        self.assertEqual(Dist.judge(varied)["label"], "good")

    def test_a_single_take_is_caught(self):
        self.assertEqual(Dist.judge({"structure": Cal.sequential([1349])})["label"], "bad")

    def test_a_fast_montage_is_not_caught(self):
        # equal beats are a legitimate form when the cuts are short
        montage = {"structure": Cal.sequential([70] * 18)}
        self.assertEqual(Dist.judge(montage)["label"], "good")

    def test_an_empty_plan_is_caught(self):
        self.assertEqual(Dist.judge({"structure": []})["label"], "bad")

    def test_the_spread_is_reported_not_just_the_verdict(self):
        varied = {"structure": Cal.sequential([90, 330, 380, 300, 249])}
        self.assertGreater(Dist.judge(varied)["cv"], 0.2)


class TestCoverage(unittest.TestCase):
    """The measurement that decided whether the second judge earns its place."""

    @classmethod
    def setUpClass(cls):
        cls.result = Dist.coverage(Cal.labelled_set(), SET_REQUEST)

    def test_every_bad_plan_is_caught_by_at_least_one_judge(self):
        self.assertEqual(self.result["caught_by_either"], self.result["bad"])

    def test_the_shape_judge_raises_no_false_alarms(self):
        self.assertEqual(self.result["shape_false_alarms"], 0)

    def test_the_shape_judge_has_exactly_one_unique_catch(self):
        # v2.16 measured zero and said the judge added nothing. v2.17 added the
        # plan that proves otherwise: fifteen identical three-second shots pass
        # every threshold and are a slideshow.
        self.assertEqual(self.result["caught_by_shape_only"], 1)

    def test_the_threshold_judge_catches_what_shape_cannot(self):
        self.assertGreaterEqual(self.result["caught_by_threshold_only"], 1)

    def test_agreement_is_reported_as_a_number(self):
        comparison = Dist.compare_with_thresholds(Cal.labelled_set(), SET_REQUEST)
        self.assertGreaterEqual(comparison["agree"], 15)


class TestExpectationListComparison(unittest.TestCase):
    """§19.2 — the harness a second author needs."""

    def test_identical_lists_show_no_differences(self):
        first = Cal.label_from_request(REEL)
        second = Cal.label_from_request(REEL)
        self.assertEqual(Cal.compare_expectation_lists(first, second)["differences"], [])

    def test_a_changed_expectation_is_named(self):
        first = Cal.label_from_request(REEL)
        second = dict(first, expected_cuts=first["expected_cuts"] + 1)
        diffs = Cal.compare_expectation_lists(first, second)["differences"]
        self.assertEqual(diffs[0]["field"], "expected_cuts")

    def test_a_changed_accept_rule_is_named(self):
        first = Cal.label_from_request(REEL)
        second = dict(first, accept_if=first["accept_if"] + ["one extra rule"])
        diffs = Cal.compare_expectation_lists(first, second)["differences"]
        self.assertIn("accept_if", [d["field"] for d in diffs])


class TestJudgesStillAgreeWhereItMatters(unittest.TestCase):
    """The regression guard v2.15 built must keep working."""

    def test_both_judges_reject_a_single_take(self):
        one = {"structure": Cal.sequential([1349])}
        self.assertEqual(Dist.judge(one)["label"], "bad")
        self.assertNotEqual(RB.score(one, REEL)["verdict"], "acceptable")

    def test_both_judges_accept_the_planner(self):
        import planner
        plan = planner.plan(REEL)
        self.assertEqual(Dist.judge(plan)["label"], "good")
        self.assertEqual(RB.score(plan, REEL)["verdict"], "acceptable")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestSlideshowRefused(unittest.TestCase):
    """v2.17 — the plan only the shape judge catches is refused by the gate."""

    def test_the_threshold_judge_accepts_it(self):
        slideshow = {"structure": Cal.sequential([90] * 15)}
        self.assertEqual(RB.score(slideshow, REEL)["verdict"], "acceptable")

    def test_the_shape_judge_rejects_it(self):
        slideshow = {"structure": Cal.sequential([90] * 15)}
        self.assertEqual(Dist.judge(slideshow)["label"], "bad")

    def test_the_gate_requires_both(self):
        import json
        import urllib.error
        import urllib.request
        import auth as A
        import service as S
        import store as St

        store = St.Store(":memory:")
        tokens = A.Tokens()
        tokens.issue("tok_a", "tnt_test")
        server = S.Server(store, tokens).__enter__()
        try:
            body = json.dumps({"kind": "plan", "payload": {
                "plan": {"structure": Cal.sequential([90] * 15)},
                "request": REEL}}).encode()
            request = urllib.request.Request(
                f"{server.url}/v1/jobs", data=body, method="POST",
                headers={"Authorization": "Bearer tok_a",
                         "Content-Type": "application/json"})
            try:
                urllib.request.urlopen(request)
                code = 202
            except urllib.error.HTTPError as error:
                code = error.code
        finally:
            server.__exit__(None, None, None)
        self.assertEqual(code, 422)
