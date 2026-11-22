"""The identity state machine of §8.5, with no biometrics in it.

The interesting part of identity resolution is not the matching, it is what
happens when the match is uncertain: the job holds, the hold has a deadline,
and a timeout is not consent. That is testable with integers.
"""
from enum import Enum


class State(str, Enum):
    RESOLVED = "resolved"
    UNCERTAIN = "uncertain"
    HOLD = "awaiting_input"
    PROCEED = "proceeding"
    FAILED = "failed"


def resolve(distance, accept=0.35, reject=0.55):
    """§8.5 step 1-2: above the accept threshold resolves, the band does not."""
    if distance <= accept:
        return State.RESOLVED
    if distance >= reject:
        return State.FAILED
    return State.UNCERTAIN


def on_uncertain(state):
    """§8.5 step 3: uncertain does not guess, it holds."""
    if state is not State.UNCERTAIN:
        raise ValueError("only an uncertain match can hold")
    return State.HOLD


def on_answer(state, answer):
    """§8.5 step 4: a hold proceeds only on a resolution or an explicit accept."""
    if state is not State.HOLD:
        raise ValueError("only a held job can be answered")
    if answer == "confirm":
        return State.RESOLVED
    if answer == "accept_degraded":
        return State.PROCEED
    raise ValueError(f"unknown answer {answer}")


def on_timeout(state):
    """A timeout is not consent: an unanswered hold expires to failed."""
    if state is not State.HOLD:
        raise ValueError("only a held job can time out")
    return State.FAILED
