"""v2.5: authorisation, observability, signed delivery and a plan corpus."""
import json
import time
import unittest
from fractions import Fraction as F
from pathlib import Path

import auth as A
import metrics as M
import planner as P
import store as St
import webhook as W

FPS = F(30000, 1001)
GOLDEN = Path(__file__).parent / "golden"


class TestAuthorisation(unittest.TestCase):
    """§14.5 — the tenant comes from the token, never from a header."""

    def setUp(self):
        self.tokens = A.Tokens()
        self.tokens.issue("tok_a", "tnt_a")
        self.tokens.issue("tok_admin", "tnt_a", role="admin")

    def test_no_credential_is_unauthenticated(self):
        with self.assertRaises(A.AuthError) as caught:
            A.resolve({}, self.tokens)
        self.assertEqual(caught.exception.status, 401)

    def test_an_unknown_token_is_unauthenticated(self):
        with self.assertRaises(A.AuthError):
            A.resolve({"Authorization": "Bearer nope"}, self.tokens)

    def test_the_token_decides_the_tenant(self):
        self.assertEqual(A.resolve({"Authorization": "Bearer tok_a"}, self.tokens), "tnt_a")

    def test_a_tenant_cannot_name_another_tenant(self):
        with self.assertRaises(A.AuthError) as caught:
            A.resolve({"Authorization": "Bearer tok_a"}, self.tokens, "tnt_b")
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(caught.exception.code, "TENANT_OVERRIDE_FORBIDDEN")

    def test_an_admin_may_override(self):
        self.assertEqual(
            A.resolve({"Authorization": "Bearer tok_admin"}, self.tokens, "tnt_b"), "tnt_b")

    def test_the_credential_is_not_a_default(self):
        # a request with no Authorization header must never inherit a tenant
        self.assertIsNone(self.tokens.principal({"X-Tenant": "tnt_a"}))


class TestMetrics(unittest.TestCase):
    """§17 — the signals are emitted, not only specified."""

    def setUp(self):
        self.store = St.Store(":memory:")

    def test_the_queue_depth_is_exported(self):
        self.store.submit("tnt_a", "render")
        self.store.submit("tnt_a", "render")
        text = M.render(self.store)
        self.assertIn("cutforge_queue_depth 2", text)

    def test_the_format_is_prometheus_text(self):
        text = M.render(self.store)
        self.assertIn("# TYPE cutforge_jobs_total gauge", text)
        for line in text.splitlines():
            if line and not line.startswith("#"):
                self.assertRegex(line, r"^[a-z_]+(\{[a-z_]+=\"[^\"]*\"\})? [0-9.]+$")

    def test_the_oldest_job_age_is_reported(self):
        self.store.submit("tnt_a", "render")
        text = M.render(self.store, now=time.time() + 5)
        self.assertIn("cutforge_oldest_job_age_seconds", text)

    def test_retries_are_counted(self):
        job, _ = self.store.submit("tnt_a", "render")
        self.store.claim("w1")
        self.store.fail(job["id"], "TRANSIENT")
        self.assertIn("cutforge_retries_total 1", M.render(self.store))


class TestWebhookSignature(unittest.TestCase):
    """§15.3 — signed, timestamped, and not replayable."""

    SECRET = "whsec_test"

    def test_a_fresh_delivery_verifies(self):
        body = json.dumps({"event": "job.succeeded"}).encode()
        h = W.headers(self.SECRET, body)
        self.assertTrue(W.verify(self.SECRET, body, h["X-Cutforge-Timestamp"],
                                 h["X-Cutforge-Signature"]))

    def test_a_tampered_body_fails(self):
        body = json.dumps({"event": "job.succeeded"}).encode()
        h = W.headers(self.SECRET, body)
        self.assertFalse(W.verify(self.SECRET, body + b" ", h["X-Cutforge-Timestamp"],
                                  h["X-Cutforge-Signature"]))

    def test_a_replay_after_the_window_fails(self):
        body = b'{"event":"job.succeeded"}'
        h = W.headers(self.SECRET, body, timestamp=1_000_000)
        self.assertFalse(W.verify(self.SECRET, body, h["X-Cutforge-Timestamp"],
                                  h["X-Cutforge-Signature"], now=1_000_000 + 400))

    def test_the_wrong_secret_fails(self):
        body = b'{"event":"job.succeeded"}'
        h = W.headers(self.SECRET, body)
        self.assertFalse(W.verify("other", body, h["X-Cutforge-Timestamp"],
                                  h["X-Cutforge-Signature"]))

    def test_a_garbage_timestamp_fails_rather_than_raising(self):
        body = b"{}"
        self.assertFalse(W.verify(self.SECRET, body, "not-a-number", "deadbeef"))


class TestPlanCorpus(unittest.TestCase):
    """§7.1 — the model claim gets something to measure, without a model.

    A recorded corpus of (request, plan, outcome) makes the 80% first-attempt
    target checkable by replay: an accepted plan must validate clean, and a
    rejected one must not.
    """

    def setUp(self):
        self.corpus = json.loads((GOLDEN / "plan_corpus.json").read_text())

    def test_every_accepted_plan_validates(self):
        for entry in self.corpus["plans"]:
            if entry["outcome"] == "accepted":
                self.assertEqual(P.validate(entry["plan"], FPS), [], entry["id"])

    def test_every_rejected_plan_fails(self):
        for entry in self.corpus["plans"]:
            if entry["outcome"] == "rejected":
                self.assertNotEqual(P.validate(entry["plan"], FPS), [], entry["id"])

    def test_the_first_attempt_rate_is_computable(self):
        plans = self.corpus["plans"]
        accepted_first = sum(1 for p in plans if p["outcome"] == "accepted"
                             and p.get("attempt", 1) == 1)
        self.assertGreater(accepted_first / len(plans), 0.0)
        self.assertLessEqual(accepted_first / len(plans), 1.0)

    def test_the_corpus_declares_where_it_came_from(self):
        # a corpus recorded from the template planner is not evidence about a model
        self.assertIn("source", self.corpus)
        self.assertNotEqual(self.corpus["source"], "production model")


if __name__ == "__main__":
    unittest.main(verbosity=2)
