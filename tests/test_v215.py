"""v2.15: blind labelling, and a gate that can refuse."""
import json
import unittest
import urllib.error
import urllib.request

import auth as A
import calibration as Cal
import planner as P
import service as S
import store as St
from test_planner import REQUESTS

REEL = REQUESTS["three_shot_reel"]
ONE_TAKE = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}


class TestBlindLabelling(unittest.TestCase):
    """§19.2 — expectations written from the request, before a plan exists."""

    def test_expectations_are_derived_from_the_request(self):
        expect = Cal.label_from_request(REEL)
        self.assertEqual(expect["target_ms"], REEL["duration_target_ms"])
        self.assertEqual(expect["shots_available"], 2)      # one excluded by must_avoid

    def test_the_expectations_are_stated_before_scoring(self):
        # a list of what will be accepted, so a label cannot be revised later
        self.assertGreaterEqual(len(Cal.label_from_request(REEL)["accept_if"]), 4)

    def test_the_judge_and_the_planner_share_one_rule(self):
        # two copies of one rule is this repository's recurring defect: a judge
        # with its own 3000 ms rejected the planner's 90-frame hook by 3 ms
        self.assertEqual(Cal.label_from_request(REEL)["expected_hook_max_frames"],
                         P.HOOK_MAX_FRAMES)

    def test_the_planner_passes_its_own_expectations(self):
        self.assertEqual(Cal.judge(P.plan(REEL), REEL)["label"], "good")

    def test_a_single_take_fails_them(self):
        result = Cal.judge(ONE_TAKE, REEL)
        self.assertEqual(result["label"], "bad")
        self.assertIn("hook", result["why"])

    def test_an_empty_plan_fails_with_a_reason(self):
        self.assertEqual(Cal.judge({"structure": []}, REEL)["why"], "no structure")

    def test_the_judge_agrees_with_the_rubric_on_the_labelled_set(self):
        # two independent judges on the same plans: where they disagree, one of
        # them is wrong and the disagreement is the useful artefact
        import rubric
        request = {"duration_target_ms": 45011, "shots": [{"labels": []}] * 6}
        disagreements = [row["why"] for row in Cal.labelled_set()
                         if (Cal.judge(row["plan"], request)["label"] == "good")
                         != (rubric.score(row["plan"], request)["verdict"] == "acceptable")]
        self.assertEqual(disagreements, [], disagreements)


class TestGateRefusal(unittest.TestCase):
    """§7.5 — a plan the repair cannot lift is refused, not queued."""

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
            headers={"Authorization": "Bearer tok_a", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_an_unrepairable_plan_is_refused(self):
        code, body = self._post({"plan": {"structure": []}, "request": REEL})
        self.assertEqual(code, 422)
        self.assertEqual(body["error"]["code"], "PLAN_UNREPAIRABLE")

    def test_the_refusal_names_the_criterion(self):
        _, body = self._post({"plan": {"structure": []}, "request": REEL})
        self.assertIn("structure", body["error"]["details"]["unrepairable"])

    def test_a_repairable_plan_is_accepted_and_reported(self):
        code, body = self._post({"plan": ONE_TAKE, "request": REEL})
        self.assertEqual(code, 202)
        self.assertEqual(body["quality"]["after"], "acceptable")

    def test_a_refused_plan_creates_no_job(self):
        self._post({"plan": {"structure": []}, "request": REEL})
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) n FROM jobs").fetchone()["n"], 0)

    def test_a_good_plan_is_untouched(self):
        _, body = self._post({"plan": P.plan(REEL), "request": REEL})
        self.assertEqual(body["quality"]["repairs"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
