"""§7.6, §7.7 — the deterministic planner that P0 ships before any model."""
import json
import unittest
from fractions import Fraction as F
from pathlib import Path

import planner as P

FPS = F(30000, 1001)
GOLDEN = Path(__file__).parent / "golden" / "plans.json"

REQUESTS = {
    "three_shot_reel": {
        "goal": "45s vertical product reel",
        "duration_target_ms": 45011,
        "shots": [
            {"asset": "ast_a91", "in": 1440, "out": 1751, "labels": ["product close-up"]},
            {"asset": "ast_b07", "in": 96, "out": 361, "labels": ["person:ceo"]},
            {"asset": "ast_c13", "in": 60, "out": 254, "labels": []},
        ],
        "must_keep": ["product close-up"],
        "must_avoid": ["person:ceo"],
    },
    "short_hook": {
        "goal": "10s teaser",
        "duration_target_ms": 10010,
        "shots": [{"asset": "ast_a91", "in": 0, "out": 240, "labels": []},
                  {"asset": "ast_c13", "in": 0, "out": 240, "labels": []}],
    },
    "single_shot": {
        "goal": "5s end card",
        "duration_target_ms": 5005,
        "shots": [{"asset": "ast_a91", "in": 2160, "out": 2400, "labels": ["logo"]}],
        "must_keep": ["logo"],
    },
}


class TestPlanner(unittest.TestCase):
    def test_plans_match_their_goldens(self):
        golden = json.loads(GOLDEN.read_text())
        for name, request in REQUESTS.items():
            self.assertEqual(P.plan(request), golden[name], name)

    def test_excluded_shots_never_appear(self):
        # §8.3: filtering happens before the planner chooses
        plan = P.plan(REQUESTS["three_shot_reel"])
        self.assertNotIn("ast_b07", [s["asset"] for s in plan["structure"]])

    def test_must_keep_comes_first(self):
        plan = P.plan(REQUESTS["three_shot_reel"])
        self.assertEqual(plan["structure"][0]["asset"], "ast_a91")

    def test_structure_is_contiguous(self):
        plan = P.plan(REQUESTS["three_shot_reel"])
        self.assertEqual(plan["structure"][0]["record"][0], 0)
        for a, b in zip(plan["structure"], plan["structure"][1:]):
            self.assertEqual(a["record"][1], b["record"][0])

    def test_duration_lands_in_the_accept_band(self):
        # §7.7: ±2% is the accept band, and the template planner hits it exactly
        plan = P.plan(REQUESTS["three_shot_reel"])
        self.assertEqual(P.plan_duration_frames(plan), 1349)
        self.assertEqual(P.validate(plan, FPS), [])

    def test_the_remainder_goes_to_the_payoff(self):
        plan = P.plan(REQUESTS["three_shot_reel"])
        durations = [s["record"][1] - s["record"][0] for s in plan["structure"]]
        self.assertGreaterEqual(durations[-1], max(durations[:-1]))

    def test_every_shot_excluded_is_an_error(self):
        request = dict(REQUESTS["three_shot_reel"])
        request["must_avoid"] = ["product close-up", "person:ceo"]
        request["shots"] = [s for s in request["shots"] if s["labels"]]
        with self.assertRaises(ValueError):
            P.plan(request)

    def test_the_ladder_is_stated_in_the_plan(self):
        ladder = P.plan(REQUESTS["three_shot_reel"])["duration_ladder"]
        self.assertEqual(ladder["repair_above_ms"], 900)     # 2% of 45011
        self.assertEqual(ladder["fallback_above_ms"], 2251)  # 5% of 45011


if __name__ == "__main__":
    unittest.main(verbosity=2)
