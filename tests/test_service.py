"""§15, §17, §18 — the runtime, executed rather than described.

v2.0's list said the engine had never run as a service. This is the smallest
service that can be wrong in the same ways: idempotency across a retry, a hold
with a deadline, cancellation reaching a terminal state, and a tenant that
cannot see another tenant's job.
"""
import json
import unittest
import urllib.error
import urllib.request

import service as S


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
        self.store = S.JobStore(hold_seconds=0.2)
        self.server = S.Server(self.store).__enter__()
        self.url = self.server.url

    def tearDown(self):
        self.server.__exit__(None, None, None)

    def _submit(self, key=None, tenant=None):
        headers = {"Idempotency-Key": key} if key else {}
        if tenant:
            headers["X-Tenant"] = tenant
        return call(f"{self.url}/v1/jobs", "POST",
                    {"kind": "render", "payload": {"prompt": "reel"}}, headers)

    def test_a_job_is_accepted_and_readable(self):
        code, body = self._submit()
        self.assertEqual(code, 202)
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}")
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
                       headers={"X-Tenant": "tnt_other"})
        self.assertEqual(code, 404)

    def test_a_hold_expires_to_failed_not_delivered(self):
        # §8.5: a timeout is not consent
        _, body = self._submit()
        self.store.transition("tnt_test", body["job_id"], "awaiting_input",
                              hold_question={"q": "is this the CEO?"})
        import time
        time.sleep(0.25)
        _, job = call(f"{self.url}/v1/jobs/{body['job_id']}")
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"], "HOLD_EXPIRED")

    def test_an_answer_resumes_the_job(self):
        _, body = self._submit()
        self.store.transition("tnt_test", body["job_id"], "awaiting_input")
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}/answer", "POST",
                         {"answer": "confirm"})
        self.assertEqual(code, 200)
        self.assertEqual(job["state"], "running")

    def test_accepting_a_degraded_result_is_recorded(self):
        # §8.5: the only route to a degraded output, and it is visible
        _, body = self._submit()
        self.store.transition("tnt_test", body["job_id"], "awaiting_input")
        _, job = call(f"{self.url}/v1/jobs/{body['job_id']}/answer", "POST",
                      {"answer": "accept_degraded"})
        self.assertTrue(job["degraded"])

    def test_cancellation_is_terminal(self):
        _, body = self._submit()
        code, job = call(f"{self.url}/v1/jobs/{body['job_id']}", "DELETE")
        self.assertEqual(code, 200)
        self.assertEqual(job["state"], "cancelled")
        # a cancelled job cannot be revived by a later transition
        self.store.transition("tnt_test", body["job_id"], "running")
        _, again = call(f"{self.url}/v1/jobs/{body['job_id']}")
        self.assertEqual(again["state"], "cancelled")

    def test_an_unknown_job_is_404(self):
        code, _ = call(f"{self.url}/v1/jobs/job_missing")
        self.assertEqual(code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
