"""v2.14: a calibration set big enough to disagree, and a gate that runs it."""
import json
import unittest
import urllib.error
import urllib.request

import auth as A
import calibration as Cal
import repair as Rp
import rubric as RB
import service as S
import store as St
from test_planner import REQUESTS

REEL = REQUESTS["three_shot_reel"]
ONE_TAKE = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}


class TestCalibrationSet(unittest.TestCase):
    """§19.2 — a set that never disagrees proves nothing."""

    @classmethod
    def setUpClass(cls):
        cls.result = Cal.separation()
        cls.disagreements = Cal.disagreements()

    def test_there_are_twenty_labelled_plans(self):
        self.assertEqual(self.result["good"] + self.result["bad"], 20)

    def test_the_rubric_orders_every_pair(self):
        self.assertEqual(self.result["separation"], 1.0)

    def test_the_rubric_and_the_labels_agree(self):
        self.assertEqual(self.disagreements, [],
                         [d["why"] for d in self.disagreements])

    def test_a_plan_with_no_hook_and_no_cuts_is_rejected(self):
        verdicts = {r["why"]: r["verdict"] for r in self.result["scored"]}
        self.assertNotEqual(verdicts["one unbroken 45-second take"], "acceptable")

    def test_too_many_cuts_is_rejected(self):
        # v2.13's rubric scored forty cuts in 45 s a perfect 1.0: pacing asked
        # only whether there were enough cuts, never whether there were too many
        verdicts = {r["why"]: r["verdict"] for r in self.result["scored"]}
        self.assertNotEqual(
            verdicts["forty cuts in forty-five seconds is a slideshow"], "acceptable")

    def test_a_small_shortfall_is_tolerated(self):
        verdicts = {r["why"]: r["verdict"] for r in self.result["scored"]}
        self.assertEqual(
            verdicts["fifty frames short — 3.7 per cent, inside delivery tolerance"],
            "acceptable")


class TestQualityGate(unittest.TestCase):
    """§7.5 — the repair is called by the service, not by a test."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.tokens = A.Tokens()
        self.tokens.issue("tok_a", "tnt_test")
        self.server = S.Server(self.store, self.tokens).__enter__()
        self.url = self.server.url

    def tearDown(self):
        self.server.__exit__(None, None, None)

    def _post(self, payload, kind="plan"):
        data = json.dumps({"kind": kind, "payload": payload}).encode()
        request = urllib.request.Request(
            f"{self.url}/v1/jobs", data=data, method="POST",
            headers={"Authorization": "Bearer tok_a",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_a_bad_plan_is_repaired_on_submission(self):
        code, body = self._post({"plan": ONE_TAKE, "request": REEL})
        self.assertEqual(code, 202)
        self.assertEqual(body["quality"]["before"], "below bar")
        self.assertEqual(body["quality"]["after"], "acceptable")

    def test_the_gate_says_what_it_changed(self):
        _, body = self._post({"plan": ONE_TAKE, "request": REEL})
        criteria = [r["criterion"] for r in body["quality"]["repairs"]]
        self.assertIn("hook", criteria)

    def test_a_good_plan_passes_through_untouched(self):
        _, body = self._post({"plan": REQUESTS and __import__("planner").plan(REEL),
                              "request": REEL})
        self.assertEqual(body["quality"]["repairs"], [])
        self.assertEqual(body["quality"]["before"], "acceptable")

    def test_a_non_plan_job_has_no_gate(self):
        code, body = self._post({"prompt": "make a reel"}, kind="render")
        self.assertEqual(code, 202)
        self.assertIsNone(body["quality"])

    def test_a_plan_less_payload_is_not_gated(self):
        code, body = self._post({}, kind="plan")
        self.assertEqual(code, 202)
        self.assertIsNone(body["quality"])


class TestRepairContract(unittest.TestCase):
    """The properties a repair must hold, restated for the gate."""

    def test_the_total_is_never_changed(self):
        fixed = Rp.apply_quality_repair(ONE_TAKE, REEL)
        self.assertEqual(fixed["structure"][-1]["record"][1], 1349)

    def test_the_result_is_acceptable(self):
        self.assertEqual(RB.score(Rp.apply_quality_repair(ONE_TAKE, REEL), REEL)["verdict"],
                         "acceptable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
