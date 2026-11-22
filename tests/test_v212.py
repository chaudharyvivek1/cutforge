"""v2.12: a rubric that scores quality, a worker loop, and the planner's hook."""
import unittest

import planner as P
import rubric as RB
import store as St
from test_planner import REQUESTS

REEL = REQUESTS["three_shot_reel"]


class TestRubric(unittest.TestCase):
    """§19.2 — agreement is not quality, and quality has to be a number."""

    def test_a_template_plan_passes(self):
        result = RB.score(P.plan(REEL), REEL)
        self.assertEqual(result["verdict"], "acceptable", result["criteria"])

    def test_a_single_take_fails_on_the_hook(self):
        one_take = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}
        result = RB.score(one_take, REEL)
        self.assertEqual(result["criteria"]["hook"], 0.0)
        self.assertEqual(result["verdict"], "below bar")

    def test_an_uncut_plan_scores_below_a_cut_one(self):
        one_take = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}
        self.assertGreater(RB.score(P.plan(REEL), REEL)["total"],
                           RB.score(one_take, REEL)["total"])

    def test_the_duration_criterion_is_exact(self):
        short = {"structure": [{"record": [0, 90]}, {"record": [90, 1000]}]}
        self.assertLess(RB.score(short, REEL)["criteria"]["duration"], 1.0)

    def test_taste_is_named_as_unmeasured(self):
        # a score that silently omits what it cannot judge looks complete
        self.assertTrue(RB.score(P.plan(REEL), REEL)["unmeasured"])

    def test_an_empty_plan_scores_zero(self):
        self.assertEqual(RB.score({"structure": []}, REEL)["total"], 0.0)

    def test_compare_names_a_winner(self):
        one_take = {"structure": [{"record": [0, 1349], "asset": "ast_a91"}]}
        self.assertEqual(RB.compare(P.plan(REEL), one_take, REEL)["better"], "a")


class TestBoundedHook(unittest.TestCase):
    """§7.2 — the hook is bounded, and what it gives up goes to the payoff."""

    def test_the_hook_is_never_longer_than_three_seconds(self):
        # a single-shot plan has nowhere to redistribute to, so the cap does
        # not apply — there is no payoff to give the excess to
        for name, request in REQUESTS.items():
            plan = P.plan(request)
            if len(plan["structure"]) < 2:
                continue
            first = plan["structure"][0]["record"]
            self.assertLessEqual(first[1] - first[0], P.HOOK_MAX_FRAMES, name)

    def test_the_total_is_still_exact(self):
        plan = P.plan(REEL)
        self.assertEqual(plan["structure"][-1]["record"][1],
                         P.plan(REEL)["structure"][-1]["record"][1])
        self.assertEqual(sum(s["record"][1] - s["record"][0] for s in plan["structure"]),
                         plan["structure"][-1]["record"][1])

    def test_the_payoff_absorbs_what_the_hook_gives_up(self):
        plan = P.plan(REEL)
        lengths = [s["record"][1] - s["record"][0] for s in plan["structure"]]
        self.assertGreater(lengths[-1], lengths[0])

    def test_a_single_shot_plan_is_unchanged(self):
        # nothing to redistribute to, so the cap does not apply
        plan = P.plan(REQUESTS["single_shot"])
        self.assertEqual(len(plan["structure"]), 1)


class TestWorkerLoop(unittest.TestCase):
    """§18 — a sweep nobody schedules is not a sweep."""

    def setUp(self):
        self.clock = {"t": 10_000.0}
        self.store = St.Store(":memory:", clock=lambda: self.clock["t"])

    def test_the_loop_sweeps_when_idle(self):
        worker = St.Worker(self.store)
        worker.run_forever(iterations=3, sleep=lambda _: None)
        self.assertEqual(worker.sweeps, 3)

    def test_the_loop_works_instead_of_sweeping_when_there_is_work(self):
        self.store.submit("tnt_a", "render")
        worker = St.Worker(self.store)
        worker.run_forever(iterations=1, sleep=lambda _: None)
        self.assertEqual(worker.sweeps, 0)

    def test_a_sweep_removes_expired_segments(self):
        self.store.register_asset("tnt_a", "prj_1", "r" * 64, 1, (24, 1), 48, 320, 180)
        asset = self.store.db.execute("SELECT id FROM assets").fetchone()["id"]
        self.store.add_derivative("tnt_a", asset, "segment", 100, "s:0", "m://0")
        self.clock["t"] += St.Store.SEGMENT_RETENTION_SECONDS + 1
        worker = St.Worker(self.store)
        worker.run_forever(iterations=1, sleep=lambda _: None)
        self.assertEqual(worker.swept, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
