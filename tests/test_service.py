"""§15, §17, §18 — the runtime, executed rather than described.

v2.0's list said the engine had never run as a service. This is the smallest
service that can be wrong in the same ways: idempotency across a retry, a hold
with a deadline, cancellation reaching a terminal state, and a tenant that
cannot see another tenant's job.
"""
import json
import time
import unittest
import urllib.error
import urllib.request

import auth as A
import service as S
import store as St


def call(url, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json",
                                              **(headers or {})})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")


class TestService(unittest.TestCase):
    def setUp(self):
        self.store = St.Store(':memory:')
        self.tokens = A.Tokens()
        self.tokens.issue("tok_a", "tnt_test")
        self.tokens.issue("tok_other", "tnt_other")
        self.tokens.issue("tok_admin", "tnt_test", role="admin")
        self.server = S.Server(self.store, self.tokens).__enter__()
        self.url = self.server.url

    def tearDown(self):
        self.server.__exit__(None, None, None)

    def _submit(self, key=None, tenant=None, token="tok_a"):
        headers = {"Authorization": f"Bearer {token}"}
        if key:
            headers["Idempotency-Key"] = key
        if tenant:
            headers["X-Tenant"] = tenant
        return call(f"{self.url}/v1/jobs", "POST",
                    {"kind": "render", "payload": {"prompt": "reel"}}, headers)

    def test_a_job_is_accepted_and_readable(self):
        code, body = self._submit()
        self.assertEqual(code, 202)
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}",
                         headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(code, 200)
        self.assertEqual(job["state"], "queued")

    def test_the_same_key_returns_the_same_job(self):
        # §15.1: a retried submission cannot double-charge or double-insert
        _, first = self._submit(key="7c1e-9a")
        code, second = self._submit(key="7c1e-9a")
        self.assertEqual(code, 200)
        self.assertEqual(first["job_id"], second["job_id"])

    def test_another_tenant_gets_a_404(self):
        # §14.5: 404, not 403 — a 403 discloses existence
        _, body = self._submit()
        code, _ = call(f"{self.url}/v1/jobs/{body['job_id']}",
                       headers={"Authorization": "Bearer tok_other"})
        self.assertEqual(code, 404)

    def test_a_hold_expires_to_failed_not_delivered(self):
        # §8.5: a timeout is not consent
        _, body = self._submit()
        self.store.transition(body["job_id"], "awaiting_input", hold_deadline=time.time() + 0.2)
        time.sleep(0.25)
        _, job = call(f"{self.url}/v1/jobs/{body['job_id']}",
                         headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"], "HOLD_EXPIRED")

    def test_an_answer_resumes_the_job(self):
        _, body = self._submit()
        self.store.transition(body["job_id"], "awaiting_input", hold_deadline=time.time() + 60)
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}/answer", "POST",
                         {"answer": "confirm"},
                         headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(code, 200)
        self.assertEqual(job["state"], "running")

    def test_accepting_a_degraded_result_is_recorded(self):
        # §8.5: the only route to a degraded output, and it is visible
        _, body = self._submit()
        self.store.transition(body["job_id"], "awaiting_input", hold_deadline=time.time() + 60)
        _, job = call(f"{self.url}/v1/jobs/{body['job_id']}/answer", "POST",
                      {"answer": "accept_degraded"},
                      headers={"Authorization": "Bearer tok_a"})
        self.assertTrue(job["degraded"])

    def test_cancellation_is_terminal(self):
        _, body = self._submit()
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}", "DELETE",
                         headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(code, 200)
        self.assertEqual(job["state"], "cancelled")
        # a cancelled job cannot be revived by a later transition
        self.store.transition(body["job_id"], "running")
        _, again = call(f"{self.url}/v1/jobs/{body['job_id']}",
                         headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(again["state"], "cancelled")

    def test_no_credential_is_401(self):
        code, body = call(f"{self.url}/v1/jobs", "POST", {"kind": "render"})
        self.assertEqual(code, 401)
        self.assertEqual(body["error"]["code"], "UNAUTHENTICATED")

    def test_a_tenant_header_cannot_reach_another_tenant(self):
        # v2.4 believed X-Tenant; §14.5 says the token decides
        code, body = self._submit(tenant="tnt_other")
        self.assertEqual(code, 403)
        self.assertEqual(body["error"]["code"], "TENANT_OVERRIDE_FORBIDDEN")

    def test_an_admin_may_override_the_tenant(self):
        code, _ = self._submit(tenant="tnt_other", token="tok_admin")
        self.assertEqual(code, 202)

    def test_metrics_are_exposed(self):
        self._submit()
        import urllib.request
        with urllib.request.urlopen(f"{self.url}/metrics") as r:
            text = r.read().decode()
        self.assertIn("cutforge_queue_depth", text)
        self.assertIn('cutforge_jobs_total{state="queued"} 1', text)

    def test_a_rate_limited_tenant_is_refused_with_retry_after(self):
        # §16.1: the concurrency cap delays; a rate limit refuses
        self.server.buckets.capacity = 2
        self.server.buckets.state.clear()
        self.assertEqual(self._submit()[0], 202)
        self.assertEqual(self._submit()[0], 202)
        code, body = self._submit()
        self.assertEqual(code, 429)
        self.assertEqual(body["error"]["code"], "RATE_LIMITED")
        self.assertGreaterEqual(body["error"]["retry_after"], 1)

    def test_an_unknown_job_is_404(self):
        code, _ = call(f"{self.url}/v1/jobs/job_missing",
                       headers={"Authorization": "Bearer tok_a"})
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
