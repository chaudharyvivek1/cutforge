"""§18 — a job survives its worker, and a cancellation is honoured at a boundary.

v2.1's service kept jobs in a dictionary. These are the claims that needs a
file to keep: a restart loses nothing, a dead worker's job comes back, a
resume starts at the last checkpoint, and a cancelled job does not resume.
"""
import tempfile
import unittest
from pathlib import Path

import store as St


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = str(Path(self.dir) / "jobs.db")
        self.store = St.Store(self.path)

    def tearDown(self):
        self.store.db.close()

    def test_a_restart_loses_nothing(self):
        job, _ = self.store.submit("tnt_a", "render", "key-1")
        self.store.db.close()
        reopened = St.Store(self.path)
        try:
            self.assertEqual(reopened.get("tnt_a", job["id"])["state"], "queued")
        finally:
            reopened.db.close()
        self.store = St.Store(":memory:")        # for tearDown

    def test_the_idempotency_key_survives_a_restart(self):
        # §15.1: a retried submission after a crash must not double-charge
        first, created = self.store.submit("tnt_a", "render", "key-2")
        self.assertTrue(created)
        self.store.db.close()
        reopened = St.Store(self.path)
        try:
            again, created_again = reopened.submit("tnt_a", "render", "key-2")
            self.assertFalse(created_again)
            self.assertEqual(again["id"], first["id"])
        finally:
            reopened.db.close()
        self.store = St.Store(":memory:")


class TestRetryPolicy(unittest.TestCase):
    """§18 — retry by failure class, then quarantine."""

    def setUp(self):
        self.store = St.Store(":memory:")

    def test_a_transient_failure_is_retried(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.claim("w1")
        result = self.store.fail(job["id"], "TRANSIENT")
        self.assertEqual(result["state"], "queued")
        self.assertEqual(result["attempt"], 2)

    def test_a_permanent_failure_is_not_retried(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.claim("w1")
        result = self.store.fail(job["id"], "PERMANENT")
        self.assertEqual(result["state"], "failed")

    def test_a_budget_failure_is_not_retried(self):
        # retrying spends more of a budget that is already exhausted
        job, _ = self.store.submit("tnt_a", "render")
        self.store.claim("w1")
        self.assertEqual(self.store.fail(job["id"], "BUDGET")["state"], "failed")

    def test_three_identical_failures_quarantine(self):
        # §18's poison class: a loop that costs money and never succeeds
        job, _ = self.store.submit("tnt_a", "render")
        for _ in range(3):
            self.store.claim("w1")
            result = self.store.fail(job["id"], "TRANSIENT")
            if result["state"] == "quarantined":
                break
        self.assertEqual(result["state"], "quarantined")
        self.assertEqual(result["error"], "POISON")

    def test_a_quarantined_job_is_not_claimed(self):
        job, _ = self.store.submit("tnt_a", "render")
        for _ in range(3):
            self.store.claim("w1")
            self.store.fail(job["id"], "TRANSIENT")
        self.assertIsNone(self.store.claim("w2"))


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.store = St.Store(":memory:")

    def test_a_job_runs_to_completion(self):
        job, _ = self.store.submit("tnt_a", "render")
        done = St.Worker(self.store).run_once()
        self.assertEqual(done["state"], "succeeded")
        self.assertEqual(done["segments_done"], 4)

    def test_a_dead_worker_leaves_a_job_that_comes_back(self):
        # §18: checkpointing means the resume starts at the last segment
        job, _ = self.store.submit("tnt_a", "render")
        claimed = self.store.claim("w1")
        self.store.checkpoint(claimed["id"], 2)
        self.assertEqual(self.store.requeue_orphans(), 1)
        resumed = St.Worker(self.store, "w2").run_once()
        self.assertEqual(resumed["state"], "succeeded")
        self.assertEqual(resumed["attempt"], 2)

    def test_two_workers_cannot_claim_one_job(self):
        self.store.submit("tnt_a", "render")
        self.assertIsNotNone(self.store.claim("w1"))
        self.assertIsNone(self.store.claim("w2"))

    def test_a_cancelled_job_does_not_resume(self):
        # §18: cancellation is cooperative and bounded, and it is terminal
        job, _ = self.store.submit("tnt_a", "render")
        self.store.cancel("tnt_a", job["id"])
        self.assertIsNone(St.Worker(self.store).run_once())
        self.assertEqual(self.store.get("tnt_a", job["id"])["state"], "cancelled")

    def test_a_terminal_state_is_final(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "failed", "VERIFICATION_FAILED")
        self.store.finish(job["id"], "succeeded")
        self.assertEqual(self.store.get("tnt_a", job["id"])["state"], "failed")

    def test_an_unanswered_hold_expires_to_failed(self):
        job, _ = self.store.submit("tnt_a", "render")
        with self.store.tx() as db:
            db.execute("UPDATE jobs SET state='awaiting_input', hold_deadline=? WHERE id=?",
                       (0.0, job["id"]))
        self.assertEqual(self.store.expire_holds(), 1)
        self.assertEqual(self.store.get("tnt_a", job["id"])["state"], "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
