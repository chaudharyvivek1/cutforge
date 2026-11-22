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


# --------------------------------------------------------------- quality repair
def quality_diff(plan, request):
    """The rubric's verdict as a structured diff the planner can act on.

    §7.5's loop repaired schema violations and never consulted quality, so a
    plan that validated and scored badly shipped. The diff names the criterion
    rather than the score, because "the hook is 22 seconds" is actionable and
    "0.54" is not.
    """
    import rubric
    result = rubric.score(plan, request)
    structure = plan.get("structure", [])
    lengths = [s["record"][1] - s["record"][0] for s in structure]
    diff = {"verdict": result["verdict"], "total": result["total"], "repairs": []}
    if not structure:
        diff["repairs"].append({"criterion": "structure", "detail": "no shots"})
        return diff

    criteria = result["criteria"]
    if criteria["hook"] == 0:
        diff["repairs"].append({"criterion": "hook", "detail": f"first shot is {lengths[0]} frames"})
    if criteria["duration"] < 1.0:
        diff["repairs"].append({"criterion": "duration",
                                "detail": f"total {sum(lengths)} frames"})
    if criteria["pacing"] < 1.0:
        diff["repairs"].append({"criterion": "pacing",
                                "detail": f"{len(structure)} cuts for {sum(lengths)} frames"})
    if criteria["payoff"] == 0:
        diff["repairs"].append({"criterion": "payoff",
                                "detail": f"last shot is {lengths[-1]} frames"})
    return diff


def apply_quality_repair(plan, request, hook_max=None, passes=3):
    """Repair to a fixed point, bounded.

    The criteria interact: capping a hook needs a second shot to give the
    excess to, and splitting a single take creates one. So one pass is not
    enough and an unbounded loop can oscillate — three passes, then stop and
    let the caller see the score. Applying it twice must equal applying it
    once, which is what `passes` converging guarantees.
    """
    current = plan
    for _ in range(passes):
        before = current
        current = _repair_once(current, request, hook_max)
        if current == before:
            break
    return current


def _repair_once(plan, request, hook_max=None):
    """One pass of three corrections, each of which moves a boundary only.

    v2.13's first version shifted every later shot when it capped the hook,
    which silently shortened the film by the amount it had removed — a repair
    that fixes the score by losing footage. A correction moves the boundary
    between two shots, so the total cannot change.
    """
    import rubric
    hook_max = hook_max or 90
    structure = [dict(s, record=list(s["record"])) for s in plan.get("structure", [])]
    if not structure:
        return plan
    total_before = structure[-1]["record"][1]

    def lengths():
        return [s["record"][1] - s["record"][0] for s in structure]

    # 1. Hook: shorten the first shot and give the time to the second.
    if len(structure) >= 2 and lengths()[0] > hook_max:
        structure[0]["record"][1] = structure[0]["record"][0] + hook_max
        structure[1]["record"][0] = structure[0]["record"][1]

    # 2. Payoff: borrow from the longest middle shot by moving its end.
    if len(structure) >= 2:
        current = lengths()
        others = sorted(current[:-1])
        median = others[len(others) // 2]
        if current[-1] < median:
            need = median - current[-1]
            donor = max(range(len(structure) - 1), key=lambda i: current[i])
            give = min(need, max(0, current[donor] - 1))
            if give:
                structure[donor]["record"][1] -= give
                for shot in structure[donor + 1:]:
                    shot["record"][0] -= give
                    shot["record"][1] -= give
                structure[-1]["record"][1] += give

    # 3. Pacing: split the longest shot at its midpoint — a new boundary.
    result = rubric.score({"structure": structure}, request)
    if result["criteria"]["pacing"] < 1.0 and len(structure) < 8:
        current = lengths()
        longest = max(range(len(structure)), key=lambda i: current[i])
        shot = structure[longest]
        middle = (shot["record"][0] + shot["record"][1]) // 2
        if shot["record"][0] < middle < shot["record"][1]:
            structure[longest:longest + 1] = [
                dict(shot, record=[shot["record"][0], middle]),
                dict(shot, record=[middle, shot["record"][1]]),
            ]

    # The total is the one thing a repair may never change.
    structure[-1]["record"][1] = total_before
    return dict(plan, structure=structure)
