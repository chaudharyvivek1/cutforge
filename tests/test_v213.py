"""v2.13: the rubric calibrated against labels it was not tuned on."""
import unittest

import calibration as Cal
import planner as P
import repair as Rp
import rubric as RB
from test_planner import REQUESTS

REEL = REQUESTS["three_shot_reel"]
ONE_TAKE = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}


class TestCalibration(unittest.TestCase):
    """§19.2 — a rubric that cannot separate plans it was not tuned on is decoration."""

    @classmethod
    def setUpClass(cls):
        cls.result = Cal.separation()

    def test_every_pair_is_ordered_correctly(self):
        self.assertEqual(self.result["separation"], 1.0,
                         [r["why"] for r in self.result["scored"]
                          if r["label"] == "good" and r["verdict"] != "acceptable"])

    def test_every_accepted_plan_is_acceptable(self):
        for row in self.result["scored"]:
            if row["label"] == "good":
                self.assertEqual(row["verdict"], "acceptable", row["why"])

    def test_every_rejected_plan_is_not_acceptable(self):
        # "no structure" is its own verdict and a more useful one than
        # "below bar": an empty plan has nothing to score, not a low score.
        for row in self.result["scored"]:
            if row["label"] == "bad":
                self.assertNotEqual(row["verdict"], "acceptable", row["why"])

    def test_an_empty_plan_says_why_rather_than_scoring_zero(self):
        verdicts = {r["why"]: r["verdict"] for r in self.result["scored"]}
        self.assertEqual(verdicts["no structure at all"], "no structure")

    def test_every_label_states_its_reason(self):
        # a label without a reason is an opinion with a number attached
        for row in Cal.labelled_set():
            self.assertTrue(row["why"].strip())

    def test_the_labels_do_not_mention_a_threshold(self):
        # the point of labelling by construction is that no label encodes the
        # number the rubric is being checked against
        for row in Cal.labelled_set():
            self.assertNotIn("0.", row["why"])
            self.assertNotIn("threshold", row["why"].lower())

    def test_the_set_has_both_labels(self):
        self.assertGreaterEqual(self.result["good"], 3)
        self.assertGreaterEqual(self.result["bad"], 5)


class TestQualityRepair(unittest.TestCase):
    """§7.5 — a plan that validates and scores badly should not ship."""

    def test_a_single_take_is_repaired(self):
        fixed = Rp.apply_quality_repair(ONE_TAKE, REEL)
        self.assertEqual(RB.score(fixed, REEL)["verdict"], "acceptable")

    def test_the_repair_never_changes_the_total(self):
        fixed = Rp.apply_quality_repair(ONE_TAKE, REEL)
        self.assertEqual(fixed["structure"][-1]["record"][1],
                         ONE_TAKE["structure"][-1]["record"][1])

    def test_the_repair_is_idempotent(self):
        once = Rp.apply_quality_repair(ONE_TAKE, REEL)
        self.assertEqual(Rp.apply_quality_repair(once, REEL), once)

    def test_a_good_plan_is_left_alone(self):
        good = P.plan(REEL)
        self.assertEqual(Rp.apply_quality_repair(good, REEL), good)

    def test_four_even_cuts_are_repaired(self):
        even = {"structure": [{"record": [0, 337]}, {"record": [337, 674]},
                              {"record": [674, 1011]}, {"record": [1011, 1349]}]}
        fixed = Rp.apply_quality_repair(even, REEL)
        self.assertEqual(RB.score(fixed, REEL)["verdict"], "acceptable")
        self.assertEqual(fixed["structure"][-1]["record"][1], 1349)

    def test_the_diff_names_a_criterion_not_a_score(self):
        diff = Rp.quality_diff(ONE_TAKE, REEL)
        criteria = [r["criterion"] for r in diff["repairs"]]
        self.assertIn("hook", criteria)
        self.assertTrue(all("detail" in r for r in diff["repairs"]))

    def test_a_good_plan_produces_an_empty_diff(self):
        self.assertEqual(Rp.quality_diff(P.plan(REEL), REEL)["repairs"], [])

    def test_an_empty_plan_is_named_rather_than_crashing(self):
        diff = Rp.quality_diff({"structure": []}, REEL)
        self.assertEqual(diff["repairs"][0]["criterion"], "structure")

    def test_the_repair_terminates(self):
        # three passes, then stop: an oscillating repair is an incident
        fixed = Rp.apply_quality_repair(ONE_TAKE, REEL, passes=3)
        self.assertIsNotNone(fixed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
