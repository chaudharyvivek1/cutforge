"""§8.5 — the state machine, with no biometrics in it.

The matching accuracy is finding 4 of the v2.1 list and needs a labelled set.
What does not need one is the behaviour on uncertainty, which is where the
product promise lives: a hard constraint blocks, and a timeout is not consent.
"""
import unittest

import identity as I


class TestResolution(unittest.TestCase):
    def test_a_close_match_resolves(self):
        self.assertIs(I.resolve(0.20), I.State.RESOLVED)

    def test_a_distant_match_fails(self):
        self.assertIs(I.resolve(0.90), I.State.FAILED)

    def test_the_grey_band_does_not_guess(self):
        self.assertIs(I.resolve(0.45), I.State.UNCERTAIN)


class TestHold(unittest.TestCase):
    def test_uncertain_holds(self):
        self.assertIs(I.on_uncertain(I.State.UNCERTAIN), I.State.HOLD)

    def test_only_uncertain_can_hold(self):
        with self.assertRaises(ValueError):
            I.on_uncertain(I.State.RESOLVED)

    def test_a_confirmation_proceeds(self):
        self.assertIs(I.on_answer(I.State.HOLD, "confirm"), I.State.RESOLVED)

    def test_explicit_acceptance_proceeds_degraded(self):
        # §8.5: the only route to a degraded result, and it is recorded
        self.assertIs(I.on_answer(I.State.HOLD, "accept_degraded"), I.State.PROCEED)

    def test_a_timeout_is_not_consent(self):
        self.assertIs(I.on_timeout(I.State.HOLD), I.State.FAILED)

    def test_an_unheld_job_cannot_time_out(self):
        with self.assertRaises(ValueError):
            I.on_timeout(I.State.RESOLVED)

    def test_an_unknown_answer_is_rejected(self):
        with self.assertRaises(ValueError):
            I.on_answer(I.State.HOLD, "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
