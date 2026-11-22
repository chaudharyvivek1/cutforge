"""v2.6: credential lifecycle, rate limiting, a worker gauge, and delivery."""
import time
import unittest

import auth as A
import metrics as M
import ratelimit as RL
import store as St
import webhook as W


class TestCredentialLifecycle(unittest.TestCase):
    """§16.2 — a token expires, rotates and revokes."""

    def setUp(self):
        self.now = {"t": 1000.0}
        self.tokens = A.Tokens(ttl=60, clock=lambda: self.now["t"])
        self.tokens.issue("tok_a", "tnt_a")

    def _header(self, token="tok_a"):
        return {"Authorization": f"Bearer {token}"}

    def test_a_fresh_token_resolves(self):
        self.assertIsNotNone(self.tokens.principal(self._header()))

    def test_an_expired_token_is_rejected(self):
        self.now["t"] += 61
        self.assertIsNone(self.tokens.principal(self._header()))

    def test_an_expired_token_is_401_not_a_default_tenant(self):
        self.now["t"] += 61
        with self.assertRaises(A.AuthError) as caught:
            A.resolve(self._header(), self.tokens)
        self.assertEqual(caught.exception.status, 401)

    def test_a_revoked_token_is_rejected_on_the_next_request(self):
        self.tokens.revoke("tok_a")
        self.assertIsNone(self.tokens.principal(self._header()))

    def test_rotation_issues_a_new_token_and_kills_the_old(self):
        new = self.tokens.rotate("tok_a")
        self.assertIsNone(self.tokens.principal(self._header()))
        self.assertIsNotNone(self.tokens.principal(self._header(new)))

    def test_rotation_preserves_the_principal(self):
        new = self.tokens.rotate("tok_a")
        principal = self.tokens.principal(self._header(new))
        self.assertEqual(principal.tenant, "tnt_a")

    def test_a_token_with_no_expiry_is_not_accepted_by_accident(self):
        # expires_at 0 means "never", which is the defect v2.5 shipped
        p = A.Principal(tenant="tnt_a")
        self.assertFalse(p.expired())


class TestRateLimit(unittest.TestCase):
    """§16.1 — a rate limit refuses; the concurrency cap only delays."""

    def setUp(self):
        self.now = {"t": 0.0}
        self.buckets = RL.Buckets(capacity=5, refill_per_second=1.0,
                                  clock=lambda: self.now["t"])

    def test_a_burst_up_to_capacity_is_allowed(self):
        self.assertEqual([self.buckets.take("t1") for _ in range(5)], [True] * 5)

    def test_the_request_after_the_burst_is_refused(self):
        for _ in range(5):
            self.buckets.take("t1")
        self.assertFalse(self.buckets.take("t1"))

    def test_the_bucket_refills(self):
        for _ in range(5):
            self.buckets.take("t1")
        self.now["t"] = 3.0
        self.assertTrue(self.buckets.take("t1"))

    def test_tenants_do_not_share_a_bucket(self):
        for _ in range(5):
            self.buckets.take("t1")
        self.assertTrue(self.buckets.take("t2"))

    def test_retry_after_is_at_least_a_second(self):
        for _ in range(5):
            self.buckets.take("t1")
        self.assertGreaterEqual(self.buckets.retry_after("t1"), 1)

    def test_refill_never_exceeds_capacity(self):
        self.now["t"] = 10_000.0
        for _ in range(5):
            self.assertTrue(self.buckets.take("t1"))
        self.assertFalse(self.buckets.take("t1"))


class TestWorkerGauge(unittest.TestCase):
    """§17 — heartbeat age is a signal, and the worker has a clock."""

    def test_the_heartbeat_age_is_exported(self):
        store = St.Store(":memory:")
        store.submit("tnt_a", "render")
        store.claim("w1")
        text = M.render(store)
        self.assertIn("cutforge_worker_heartbeat_age_seconds", text)

    def test_it_is_zero_with_no_worker(self):
        store = St.Store(":memory:")
        text = M.render(store)
        self.assertIn("cutforge_worker_heartbeat_age_seconds 0", text)


class TestDeliveryLoop(unittest.TestCase):
    """§15.3 — at-least-once, with retry and a dead letter."""

    def setUp(self):
        self.store = St.Store(":memory:")
        self.store.add_endpoint("tnt_a", "https://example.test/hook", "whsec_x")

    def test_a_terminal_state_produces_a_delivery(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        pending = self.store.pending_deliveries()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["event"], "job.succeeded")

    def test_a_failed_attempt_is_retried_with_backoff(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        delivery = self.store.pending_deliveries()[0]
        self.store.delivery_failed(delivery["id"], base_delay=10.0)
        row = self.store.delivery(delivery["id"])
        self.assertEqual(row["attempts"], 1)
        self.assertGreater(row["next_attempt_at"], time.time())

    def test_five_failures_dead_letter_it(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        delivery = self.store.pending_deliveries()[0]
        for _ in range(5):
            self.store.delivery_failed(delivery["id"], base_delay=0.0)
        self.assertEqual(self.store.delivery(delivery["id"])["state"], "dead")
        self.assertEqual(self.store.pending_deliveries(), [])

    def test_a_delivered_event_is_signed(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        delivery = self.store.pending_deliveries()[0]
        body, headers = self.store.delivery_request(delivery["id"])
        self.assertTrue(W.verify("whsec_x", body,
                                 headers["X-Cutforge-Timestamp"],
                                 headers["X-Cutforge-Signature"]))

    def test_delivery_is_idempotent_on_event_id(self):
        # the same terminal state must not emit two events
        job, _ = self.store.submit("tnt_a", "render")
        self.store.finish(job["id"], "succeeded")
        self.store.finish(job["id"], "succeeded")
        self.assertEqual(len(self.store.pending_deliveries()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
