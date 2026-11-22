"""The repair loop of §7.4, and the budget that stops it becoming an incident.

Preview, check, feed a structured diff back to the planner, at most twice, under
a call ceiling and a deadline. The loop is small; what matters is that the two
ways it can go wrong are both named — a loop that never terminates, and a loop
that fails without saying which budget it hit.
"""
import time


class Budget:
    def __init__(self, max_attempts=2, max_calls=6, deadline_s=30.0, clock=time.monotonic):
        self.max_attempts = max_attempts
        self.max_calls = max_calls
        self.deadline_s = deadline_s
        self.clock = clock
        self.calls = 0
        self.attempts = 0
        self.started = clock()

    def spend(self, n=1):
        self.calls += n
        if self.calls > self.max_calls:
            raise BudgetExceeded("CALL_CEILING")
        if self.clock() - self.started > self.deadline_s:
            raise BudgetExceeded("DEADLINE")


class BudgetExceeded(Exception):
    def __init__(self, which):
        super().__init__(which)
        self.which = which


def run(request, plan_fn, check_fn, repair_fn, budget=None):
    """Plan, check, repair — and say exactly why it stopped.

    `check_fn(plan)` returns a list of problems; `repair_fn(plan, problems)`
    returns a new plan or raises if it cannot improve. Returns a result dict
    rather than raising, because a job that fails must fail with a code.
    """
    budget = budget or Budget()
    try:
        plan = plan_fn(request)
        budget.spend()

        while True:
            problems = check_fn(plan)
            if not problems:
                return {"ok": True, "attempts": budget.attempts + 1, "plan": plan}
            if budget.attempts >= budget.max_attempts:
                return {"ok": False, "code": "REPAIR_EXHAUSTED",
                        "attempts": budget.attempts + 1, "problems": problems}
            budget.attempts += 1
            budget.spend()
            try:
                plan = repair_fn(plan, problems)
            except Exception:
                return {"ok": False, "code": "REPAIR_FAILED", "attempts": budget.attempts}
    except BudgetExceeded as exc:
        # the budget can bite on the first call as easily as the fourth
        return {"ok": False, "code": f"BUDGET_{exc.which}", "attempts": budget.attempts}
