"""§7.4 — the repair loop, and the two ways it must stop."""
import unittest

import planner as P
import repair as Rp
from fractions import Fraction as F

FPS = F(30000, 1001)
REQUEST = {"duration_target_ms": 45011,
           "shots": [{"asset": f"ast_{i}", "in": 0, "out": 300, "labels": []}
                     for i in range(4)]}


def check(plan):
    return P.validate(plan, FPS)


class TestRepair(unittest.TestCase):
    def test_a_good_plan_needs_no_repair(self):
        result = Rp.run(REQUEST, P.plan, check, lambda p, problems: p)
        self.assertTrue(result["ok"])
        self.assertEqual(result["attempts"], 1)

    def test_a_repairable_plan_is_repaired_within_two_attempts(self):
        calls = {"n": 0}

        def flaky(request):
            # a first plan that is short, repaired on the second call
            plan = P.plan(request)
            if calls["n"] == 0:
                calls["n"] += 1
                plan["structure"] = plan["structure"][:-1]
                plan["structure"][-1]["record"][1] -= 200   # leaves a hole
            return plan

        def fix(plan, problems):
            return P.plan(REQUEST)

        result = Rp.run(REQUEST, flaky, check, fix)
        self.assertTrue(result["ok"], result)
        self.assertLessEqual(result["attempts"], 3)

    def test_it_stops_when_repair_cannot_improve(self):
        def flaky(request):
            plan = P.plan(request)
            plan["structure"][0]["record"][0] = 10          # an illegal start
            return plan

        result = Rp.run(REQUEST, flaky, check, lambda p, problems: p)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "REPAIR_EXHAUSTED")
        self.assertEqual(result["attempts"], 3)              # one try plus two repairs

    def test_a_call_ceiling_is_named(self):
        def flaky(request):
            plan = P.plan(request)
            plan["structure"][0]["record"][0] = 10
            return plan

        budget = Rp.Budget(max_attempts=5, max_calls=1)
        result = Rp.run(REQUEST, flaky, check, lambda p, problems: p, budget)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "BUDGET_CALL_CEILING")

    def test_a_deadline_is_named(self):
        ticks = {"t": 0.0}

        def clock():
            ticks["t"] += 10.0
            return ticks["t"]

        def flaky(request):
            plan = P.plan(request)
            plan["structure"][0]["record"][0] = 10
            return plan

        budget = Rp.Budget(max_attempts=5, max_calls=99, deadline_s=1.0, clock=clock)
        result = Rp.run(REQUEST, flaky, check, lambda p, problems: p, budget)
        self.assertFalse(result["ok"])
        self.assertTrue(result["code"].startswith("BUDGET_"))

    def test_a_planner_that_raises_fails_with_a_code(self):
        def boom(request):
            raise ValueError("NO_CANDIDATE")

        with self.assertRaises(ValueError):
            Rp.run(REQUEST, boom, check, lambda p, problems: p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
